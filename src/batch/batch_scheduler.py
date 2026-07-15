"""
批处理调度器

负责编排和调度日终批处理的各个步骤，支持从检查点恢复执行。
步骤顺序：利息计提 → 日切 → 对账
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from src.batch.interest_batch import InterestBatchProcessor
from src.batch.day_cut_processor import DayCutProcessor
from src.batch.reconciliation_batch import ReconciliationBatchProcessor
from src.batch.batch_checkpoint import BatchCheckpoint
from src.config.settings import SystemSettings, settings
from src.repository.interfaces.account_repo import AccountRepository
from src.repository.interfaces.ledger_repo import LedgerRepository

logger = logging.getLogger(__name__)


class BatchScheduler:
    """
    批处理调度器

    负责按照预定义的顺序调度日终批处理的各个步骤：
    1. interest_accrual - 利息计提
    2. day_cut - 日切
    3. reconciliation - 对账

    支持从检查点恢复：如果之前的批处理中断，可以从最后一个成功的
    检查点继续执行，避免重复处理已完成的步骤。
    """

    # 调度步骤顺序
    SCHEDULE_STEPS: List[str] = [
        "interest_accrual",
        "day_cut",
        "reconciliation",
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
        初始化批处理调度器

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

        # 初始化各步骤处理器
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

    def run_day_end(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行日终批处理

        按顺序调度各步骤：利息计提 → 日切 → 对账。
        支持从检查点恢复，跳过已完成的步骤。

        Args:
            accounting_date: 会计日期

        Returns:
            调度结果字典，包含：
            - batch_id: 批次ID
            - accounting_date: 会计日期
            - steps_executed: 已执行的步骤列表
            - steps_skipped: 跳过的步骤列表（从检查点恢复时）
            - results: 各步骤执行结果
            - status: 最终状态（success/failed）
            - error: 错误信息（如有）
            - resumed_from: 恢复的检查点步骤名（如有）

        Raises:
            RuntimeError: 调度过程中发生不可恢复的错误
        """
        logger.info(f"批处理调度器启动，会计日期: {accounting_date}")

        # 生成批次ID
        batch_id = f"SCHED-{accounting_date.isoformat()}"

        # 持久化批次记录
        self._batch_repo.save({
            "batch_id": batch_id,
            "batch_type": "SCHEDULER",
            "batch_date": accounting_date,
            "status": "RUNNING",
        })

        result: Dict[str, Any] = {
            "batch_id": batch_id,
            "accounting_date": accounting_date,
            "steps_executed": [],
            "steps_skipped": [],
            "results": {},
            "status": "failed",
            "error": None,
            "resumed_from": None,
        }

        # 检查是否有检查点需要恢复
        resume_step = self._checkpoint.get_resume_step(batch_id)
        steps_to_execute = self._determine_steps(resume_step)

        if resume_step:
            result["resumed_from"] = resume_step
            # 记录跳过的步骤
            for step_name in self.SCHEDULE_STEPS:
                if step_name not in steps_to_execute:
                    result["steps_skipped"].append(step_name)
            logger.info(f"从检查点恢复，跳过已完成步骤: {result['steps_skipped']}")

        # 按顺序执行步骤
        for step_name in steps_to_execute:
            logger.info(f"调度执行步骤: {step_name}")

            try:
                step_result = self._dispatch_step(step_name, accounting_date)
                result["steps_executed"].append(step_name)
                result["results"][step_name] = {
                    "status": "success",
                    "data": step_result,
                }

                # 保存检查点
                self._checkpoint.save(batch_id, step_name, step_result)
                logger.info(f"步骤 {step_name} 调度完成")

            except Exception as e:
                error_msg = f"步骤 {step_name} 执行失败: {str(e)}"
                result["results"][step_name] = {
                    "status": "failed",
                    "error": error_msg,
                }
                result["error"] = error_msg
                result["status"] = "failed"

                # 更新批次状态
                self._batch_repo.update_status(batch_id, "FAILED")

                logger.error(f"批处理调度失败: {error_msg}")
                return result

        # 全部步骤成功
        result["status"] = "success"
        self._batch_repo.update_status(batch_id, "SUCCESS")

        # 清除检查点
        self._checkpoint.clear(batch_id)

        logger.info(
            f"批处理调度完成，会计日期: {accounting_date}，"
            f"已执行步骤: {result['steps_executed']}"
        )

        return result

    def _determine_steps(self, resume_step: Optional[str]) -> List[str]:
        """
        确定需要执行的步骤列表

        如果有检查点，则从检查点之后的步骤开始执行。

        Args:
            resume_step: 最后成功完成的步骤名称，None表示从头开始

        Returns:
            需要执行的步骤名称列表
        """
        if resume_step is None:
            return list(self.SCHEDULE_STEPS)

        # 找到检查点步骤的位置，从下一个步骤开始
        if resume_step in self.SCHEDULE_STEPS:
            idx = self.SCHEDULE_STEPS.index(resume_step)
            return self.SCHEDULE_STEPS[idx + 1:]

        # 检查点步骤不在列表中，从头开始
        logger.warning(f"检查点步骤 {resume_step} 不在调度列表中，从头开始")
        return list(self.SCHEDULE_STEPS)

    def _dispatch_step(self, step_name: str, accounting_date: date) -> Dict[str, Any]:
        """
        分发步骤到对应的处理器

        Args:
            step_name: 步骤名称
            accounting_date: 会计日期

        Returns:
            步骤执行结果

        Raises:
            RuntimeError: 步骤执行失败
            ValueError: 未知的步骤名称
        """
        if step_name == "interest_accrual":
            return self._interest_processor.process(accounting_date)
        elif step_name == "day_cut":
            return self._day_cut_processor.process(accounting_date)
        elif step_name == "reconciliation":
            return self._reconciliation_processor.process(accounting_date)
        else:
            raise ValueError(f"未知的调度步骤: {step_name}")
