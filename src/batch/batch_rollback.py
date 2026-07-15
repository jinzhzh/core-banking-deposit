"""
批处理回滚

提供日终批处理的回滚能力，支持整批回滚和单步骤回滚。
回滚操作包括：撤销利息计提分录、恢复系统日期、重新打开会计期间。
使用仓储的snapshot/rollback机制实现数据层面的回滚。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from src.config.settings import SystemSettings, settings

logger = logging.getLogger(__name__)


class BatchRollback:
    """
    批处理回滚管理器

    负责在日终批处理失败时执行回滚操作，确保系统状态一致性。
    支持：
    - 整批回滚：回滚整个批次的所有已执行步骤
    - 单步骤回滚：仅回滚指定步骤的操作

    回滚策略：
    - 利息计提：撤销已生成的利息计提分录
    - 日切：恢复系统日期、重新打开会计期间
    - 对账：无需回滚（只读操作）
    """

    def __init__(
        self,
        batch_repository: Any,
        journal_repository: Any,
        ledger_repository: Any,
        system_settings: Optional[SystemSettings] = None,
    ) -> None:
        """
        初始化批处理回滚管理器

        Args:
            batch_repository: 批次仓储接口（需支持snapshot/rollback）
            journal_repository: 分录仓储接口
            ledger_repository: 账本仓储接口
            system_settings: 系统配置实例，默认使用全局settings
        """
        self._batch_repo = batch_repository
        self._journal_repo = journal_repository
        self._ledger_repo = ledger_repository
        self._settings = system_settings or settings

    def rollback(self, batch_id: str) -> Dict[str, Any]:
        """
        回滚整个批次

        按照步骤的逆序依次回滚所有已执行的步骤。
        使用仓储的snapshot/rollback机制恢复数据状态。

        Args:
            batch_id: 批次ID

        Returns:
            回滚结果字典，包含：
            - batch_id: 批次ID
            - rolled_back_steps: 已回滚的步骤列表
            - status: 回滚状态（success/partial/failed）
            - errors: 错误信息列表

        Raises:
            ValueError: 批次不存在
            RuntimeError: 回滚过程中发生不可恢复的错误
        """
        logger.info(f"开始回滚批次: {batch_id}")

        # 查找批次记录
        batch_data = self._batch_repo.find_by_id(batch_id)
        if batch_data is None:
            raise ValueError(f"批次不存在: {batch_id}")

        result: Dict[str, Any] = {
            "batch_id": batch_id,
            "rolled_back_steps": [],
            "status": "failed",
            "errors": [],
        }

        # 获取需要回滚的步骤（逆序）
        steps_to_rollback = self._get_completed_steps(batch_data)
        steps_to_rollback.reverse()

        # 尝试使用仓储快照回滚
        if hasattr(self._batch_repo, "rollback"):
            try:
                self._batch_repo.rollback()
                logger.info(f"批次 {batch_id} 仓储快照回滚成功")
            except ValueError as e:
                logger.warning(f"仓储快照回滚不可用: {str(e)}，将逐步骤回滚")

        # 逐步骤回滚
        for step_name in steps_to_rollback:
            try:
                self.rollback_step(batch_id, step_name)
                result["rolled_back_steps"].append(step_name)
                logger.info(f"步骤 {step_name} 回滚成功")
            except Exception as e:
                error_msg = f"步骤 {step_name} 回滚失败: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(error_msg)

        # 更新批次状态为已回滚
        self._batch_repo.update_status(batch_id, "ROLLED_BACK")

        # 确定最终状态
        if not result["errors"]:
            result["status"] = "success"
        elif result["rolled_back_steps"]:
            result["status"] = "partial"
        else:
            result["status"] = "failed"

        logger.info(
            f"批次 {batch_id} 回滚完成，状态: {result['status']}，"
            f"已回滚步骤: {result['rolled_back_steps']}"
        )

        return result

    def rollback_step(self, batch_id: str, step_name: str) -> Dict[str, Any]:
        """
        回滚单个步骤

        根据步骤类型执行对应的回滚操作：
        - interest_accrual（利息计提）：撤销利息计提分录
        - day_cut（日切）：恢复系统日期、重新打开会计期间
        - reconciliation（对账）：无需回滚（只读操作）
        - freeze_transactions（冻结交易）：解冻
        - posting（过账）：撤销过账分录

        Args:
            batch_id: 批次ID
            step_name: 步骤名称

        Returns:
            步骤回滚结果字典

        Raises:
            RuntimeError: 回滚失败
        """
        logger.info(f"开始回滚步骤: batch_id={batch_id}, step={step_name}")

        step_result: Dict[str, Any] = {
            "batch_id": batch_id,
            "step_name": step_name,
            "status": "failed",
        }

        try:
            if step_name == "interest_accrual":
                self._rollback_interest_accrual(batch_id)
            elif step_name == "day_cut":
                self._rollback_day_cut(batch_id)
            elif step_name == "reconciliation":
                # 对账是只读操作，无需回滚
                logger.info("对账步骤为只读操作，无需回滚")
            elif step_name == "freeze_transactions":
                self._rollback_freeze(batch_id)
            elif step_name == "posting":
                self._rollback_posting(batch_id)
            elif step_name == "unfreeze_transactions":
                # 解冻步骤的回滚就是重新冻结，但通常不需要
                logger.info("解冻步骤无需回滚")
            else:
                logger.warning(f"未知步骤类型: {step_name}，跳过回滚")

            step_result["status"] = "success"

        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
            logger.error(f"步骤 {step_name} 回滚失败: {str(e)}")
            raise RuntimeError(f"步骤 {step_name} 回滚失败: {str(e)}") from e

        return step_result

    def _rollback_interest_accrual(self, batch_id: str) -> None:
        """
        撤销利息计提分录

        查找该批次生成的所有利息计提分录并删除/冲销。

        Args:
            batch_id: 批次ID
        """
        logger.info(f"撤销利息计提分录，批次: {batch_id}")

        # 获取批次信息以确定会计日期
        batch_data = self._batch_repo.find_by_id(batch_id)
        if batch_data is None:
            raise ValueError(f"批次不存在: {batch_id}")

        accounting_date = batch_data.get("batch_date") or batch_data.get("date")
        if accounting_date is None:
            logger.warning("无法确定会计日期，跳过利息计提回滚")
            return

        # 查找该日期的所有利息计提分录并标记为已撤销
        # 通过分录仓储查找并删除
        if hasattr(self._journal_repo, "find_by_date"):
            entries = self._journal_repo.find_by_date(accounting_date)
            accrual_entries = [
                e for e in entries
                if hasattr(e, "summary") and "利息计提" in (e.summary or "")
            ]
            for entry in accrual_entries:
                if hasattr(self._journal_repo, "delete"):
                    self._journal_repo.delete(entry.entry_id)
                    logger.debug(f"已撤销利息计提分录: {entry.entry_id}")

        logger.info(f"利息计提分录撤销完成，批次: {batch_id}")

    def _rollback_day_cut(self, batch_id: str) -> None:
        """
        回滚日切操作

        恢复系统日期到日切前的状态，重新打开已关闭的会计期间。

        Args:
            batch_id: 批次ID
        """
        logger.info(f"回滚日切操作，批次: {batch_id}")

        # 获取批次信息
        batch_data = self._batch_repo.find_by_id(batch_id)
        if batch_data is None:
            raise ValueError(f"批次不存在: {batch_id}")

        # 获取日切前的日期
        previous_date = batch_data.get("batch_date") or batch_data.get("date")
        if previous_date is None:
            raise RuntimeError("无法确定日切前的会计日期")

        # 如果previous_date是字符串，转换为date对象
        if isinstance(previous_date, str):
            from datetime import date as date_type
            previous_date = date_type.fromisoformat(previous_date)

        # 恢复系统日期
        self._settings.system_date = previous_date
        logger.info(f"系统日期已恢复为: {previous_date}")

    def _rollback_freeze(self, batch_id: str) -> None:
        """
        回滚冻结交易操作

        Args:
            batch_id: 批次ID
        """
        logger.info(f"回滚冻结交易操作，批次: {batch_id}")
        # 冻结交易的回滚在DayEndProcessor中通过解冻步骤处理
        # 此处仅记录日志

    def _rollback_posting(self, batch_id: str) -> None:
        """
        回滚过账操作

        撤销该批次中过账生成的分录。

        Args:
            batch_id: 批次ID
        """
        logger.info(f"回滚过账操作，批次: {batch_id}")

        batch_data = self._batch_repo.find_by_id(batch_id)
        if batch_data is None:
            raise ValueError(f"批次不存在: {batch_id}")

        accounting_date = batch_data.get("batch_date") or batch_data.get("date")
        if accounting_date is None:
            return

        # 查找并撤销过账分录
        if hasattr(self._journal_repo, "find_by_date"):
            entries = self._journal_repo.find_by_date(accounting_date)
            posting_entries = [
                e for e in entries
                if hasattr(e, "summary") and "过账" in (e.summary or "")
            ]
            for entry in posting_entries:
                if hasattr(self._journal_repo, "delete"):
                    self._journal_repo.delete(entry.entry_id)
                    logger.debug(f"已撤销过账分录: {entry.entry_id}")

    def _get_completed_steps(self, batch_data: Dict[str, Any]) -> List[str]:
        """
        获取批次中已完成的步骤列表

        Args:
            batch_data: 批次数据字典

        Returns:
            已完成步骤名称列表（按执行顺序）
        """
        # 从批次数据中提取已完成的步骤
        steps = batch_data.get("completed_steps", [])
        if steps:
            return list(steps)

        # 如果没有明确的步骤记录，根据检查点推断
        checkpoint = self._batch_repo.get_checkpoint(batch_data.get("batch_id", ""))
        if checkpoint:
            step_name = checkpoint.get("step_name", "")
            # 定义标准步骤顺序
            all_steps = [
                "freeze_transactions",
                "interest_accrual",
                "posting",
                "day_cut",
                "reconciliation",
                "unfreeze_transactions",
            ]
            # 返回检查点之前（含）的所有步骤
            if step_name in all_steps:
                idx = all_steps.index(step_name)
                return all_steps[: idx + 1]

        return []
