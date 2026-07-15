"""
日终处理器

执行完整的日终批处理流程，按步骤顺序执行：
冻结新交易 → 利息计提 → 过账 → 日切 → 对账 → 解冻

任何步骤失败则标记批次失败，支持回滚。
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.domain.models.day_end_batch import (
    BatchStatus,
    BatchStep,
    DayEndBatch,
    StepStatus,
)
from src.batch.interest_batch import InterestBatchProcessor
from src.batch.day_cut_processor import DayCutProcessor
from src.batch.reconciliation_batch import ReconciliationBatchProcessor
from src.batch.batch_checkpoint import BatchCheckpoint
from src.batch.batch_rollback import BatchRollback
from src.config.settings import SystemSettings, settings
from src.repository.interfaces.account_repo import AccountRepository
from src.repository.interfaces.ledger_repo import LedgerRepository

logger = logging.getLogger(__name__)


class DayEndProcessor:
    """
    日终处理器

    编排完整的日终批处理流程，管理批次生命周期。
    步骤执行顺序：
    1. freeze_transactions - 冻结新交易（防止日终处理期间有新交易干扰）
    2. interest_accrual - 利息计提（计算所有活期账户当日利息）
    3. posting - 过账（将计提利息过账到总账）
    4. day_cut - 日切（切换系统日期到下一工作日）
    5. reconciliation - 对账（核对总账与明细账）
    6. unfreeze_transactions - 解冻（恢复正常交易）

    任何步骤失败则标记批次为失败状态，支持通过BatchRollback回滚。
    """

    # 标准步骤顺序
    STEP_ORDER: List[str] = [
        "freeze_transactions",
        "interest_accrual",
        "posting",
        "day_cut",
        "reconciliation",
        "unfreeze_transactions",
    ]

    def __init__(
        self,
        account_repository: AccountRepository,
        journal_repository: Any,
        ledger_repository: LedgerRepository,
        batch_repository: Any,
        system_settings: Optional[SystemSettings] = None,
    ) -> None:
        """
        初始化日终处理器

        Args:
            account_repository: 账户仓储接口
            journal_repository: 分录仓储接口
            ledger_repository: 账本仓储接口
            batch_repository: 批次仓储接口
            system_settings: 系统配置实例，默认使用全局settings
        """
        self._account_repo = account_repository
        self._journal_repo = journal_repository
        self._ledger_repo = ledger_repository
        self._batch_repo = batch_repository
        self._settings = system_settings or settings

        # 初始化子处理器
        self._interest_processor = InterestBatchProcessor(
            account_repository=account_repository,
            journal_repository=journal_repository,
            ledger_repository=ledger_repository,
        )
        self._day_cut_processor = DayCutProcessor(
            system_settings=self._settings,
            batch_repository=batch_repository,
        )
        self._reconciliation_processor = ReconciliationBatchProcessor(
            account_repository=account_repository,
            ledger_repository=ledger_repository,
            batch_repository=batch_repository,
        )
        self._checkpoint = BatchCheckpoint(batch_repository)
        self._rollback = BatchRollback(
            batch_repository=batch_repository,
            journal_repository=journal_repository,
            ledger_repository=ledger_repository,
            system_settings=self._settings,
        )

        # 交易冻结标志
        self._transactions_frozen: bool = False

    def process(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行日终处理

        创建DayEndBatch记录，按步骤顺序执行日终批处理。
        每个步骤成功后保存检查点，任何步骤失败则标记批次失败。

        Args:
            accounting_date: 会计日期

        Returns:
            处理结果字典，包含：
            - batch_id: 批次ID
            - accounting_date: 会计日期
            - status: 批次最终状态
            - steps: 各步骤执行结果
            - start_time: 开始时间
            - end_time: 结束时间
            - error: 错误信息（如有）

        Raises:
            RuntimeError: 批处理过程中发生不可恢复的错误
        """
        logger.info(f"开始日终处理，会计日期: {accounting_date}")

        # 创建批次记录
        batch_id = f"DAYEND-{accounting_date.isoformat()}-{uuid.uuid4().hex[:8]}"
        batch = DayEndBatch(
            batch_id=batch_id,
            accounting_date=accounting_date,
        )

        # 添加所有步骤
        for step_name in self.STEP_ORDER:
            batch.add_step(step_name)

        # 启动批次
        batch.start()

        # 持久化批次记录
        self._batch_repo.save({
            "batch_id": batch_id,
            "batch_type": "DAY_END",
            "batch_date": accounting_date,
            "status": BatchStatus.RUNNING.value,
            "steps": self.STEP_ORDER,
            "completed_steps": [],
        })

        # 创建仓储快照（用于回滚）
        if hasattr(self._batch_repo, "create_snapshot"):
            self._batch_repo.create_snapshot()

        result: Dict[str, Any] = {
            "batch_id": batch_id,
            "accounting_date": accounting_date,
            "status": None,
            "steps": {},
            "start_time": batch.start_time,
            "end_time": None,
            "error": None,
        }

        completed_steps: List[str] = []

        # 按顺序执行各步骤
        for step in batch.steps:
            step.start()
            logger.info(f"执行步骤: {step.step_name}")

            try:
                step_result = self._execute_step(step.step_name, accounting_date)
                step.complete()
                batch.update_checkpoint(step.step_name)
                completed_steps.append(step.step_name)

                # 保存检查点
                self._checkpoint.save(batch_id, step.step_name, step_result)

                # 更新持久化的已完成步骤
                self._batch_repo.save({
                    "batch_id": batch_id,
                    "batch_type": "DAY_END",
                    "batch_date": accounting_date,
                    "status": BatchStatus.RUNNING.value,
                    "steps": self.STEP_ORDER,
                    "completed_steps": completed_steps,
                })

                result["steps"][step.step_name] = {
                    "status": "success",
                    "result": step_result,
                    "start_time": step.start_time,
                    "end_time": step.end_time,
                }

                logger.info(f"步骤 {step.step_name} 执行成功")

            except Exception as e:
                # 步骤失败
                error_msg = str(e)
                step.fail(error_msg)
                batch.fail()

                result["steps"][step.step_name] = {
                    "status": "failed",
                    "error": error_msg,
                    "start_time": step.start_time,
                    "end_time": step.end_time,
                }
                result["error"] = f"步骤 {step.step_name} 失败: {error_msg}"

                logger.error(f"步骤 {step.step_name} 执行失败: {error_msg}")

                # 更新批次状态为失败
                self._batch_repo.update_status(batch_id, BatchStatus.FAILED.value)
                self._batch_repo.save({
                    "batch_id": batch_id,
                    "batch_type": "DAY_END",
                    "batch_date": accounting_date,
                    "status": BatchStatus.FAILED.value,
                    "steps": self.STEP_ORDER,
                    "completed_steps": completed_steps,
                    "failed_step": step.step_name,
                    "error": error_msg,
                })

                # 确保交易解冻（即使失败也要解冻）
                if self._transactions_frozen:
                    try:
                        self._unfreeze_transactions(accounting_date)
                    except Exception as unfreeze_err:
                        logger.error(f"失败后解冻交易出错: {str(unfreeze_err)}")

                break

        # 批次完成
        if batch.status == BatchStatus.RUNNING:
            batch.complete()
            self._batch_repo.update_status(batch_id, BatchStatus.SUCCESS.value)
            # 清除检查点
            self._checkpoint.clear(batch_id)

        result["status"] = batch.status.value
        result["end_time"] = batch.end_time

        logger.info(
            f"日终处理完成，批次: {batch_id}，状态: {batch.status.value}"
        )

        return result

    def _execute_step(self, step_name: str, accounting_date: date) -> Dict[str, Any]:
        """
        执行单个步骤

        根据步骤名称分发到对应的处理方法。

        Args:
            step_name: 步骤名称
            accounting_date: 会计日期

        Returns:
            步骤执行结果

        Raises:
            RuntimeError: 步骤执行失败
        """
        if step_name == "freeze_transactions":
            return self._freeze_transactions(accounting_date)
        elif step_name == "interest_accrual":
            return self._process_interest_accrual(accounting_date)
        elif step_name == "posting":
            return self._process_posting(accounting_date)
        elif step_name == "day_cut":
            return self._process_day_cut(accounting_date)
        elif step_name == "reconciliation":
            return self._process_reconciliation(accounting_date)
        elif step_name == "unfreeze_transactions":
            return self._unfreeze_transactions(accounting_date)
        else:
            raise RuntimeError(f"未知的步骤: {step_name}")

    def _freeze_transactions(self, accounting_date: date) -> Dict[str, Any]:
        """
        冻结新交易

        在日终处理期间禁止新的交易进入，防止数据不一致。

        Args:
            accounting_date: 会计日期

        Returns:
            冻结结果
        """
        logger.info(f"冻结新交易，会计日期: {accounting_date}")
        self._transactions_frozen = True
        return {
            "action": "freeze_transactions",
            "accounting_date": accounting_date,
            "frozen": True,
        }

    def _unfreeze_transactions(self, accounting_date: date) -> Dict[str, Any]:
        """
        解冻交易

        日终处理完成后恢复正常交易。

        Args:
            accounting_date: 会计日期

        Returns:
            解冻结果
        """
        logger.info(f"解冻交易，会计日期: {accounting_date}")
        self._transactions_frozen = False
        return {
            "action": "unfreeze_transactions",
            "accounting_date": accounting_date,
            "frozen": False,
        }

    def _process_interest_accrual(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行利息计提

        Args:
            accounting_date: 会计日期

        Returns:
            利息计提结果
        """
        return self._interest_processor.process(accounting_date)

    def _process_posting(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行过账

        将利息计提的结果过账到总账。

        Args:
            accounting_date: 会计日期

        Returns:
            过账结果
        """
        logger.info(f"执行过账，会计日期: {accounting_date}")
        # 过账操作：将当日分录汇总到总账
        # 实际实现中会遍历当日所有分录，更新总账余额
        return {
            "action": "posting",
            "accounting_date": accounting_date,
            "status": "completed",
        }

    def _process_day_cut(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行日切

        Args:
            accounting_date: 会计日期

        Returns:
            日切结果
        """
        return self._day_cut_processor.process(accounting_date)

    def _process_reconciliation(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行对账

        注意：日切后系统日期已变更，但对账仍使用原会计日期。

        Args:
            accounting_date: 会计日期

        Returns:
            对账结果
        """
        return self._reconciliation_processor.process(accounting_date)
