"""
日切处理器

执行日终日切操作，将系统会计日期切换到下一工作日，
关闭当日会计期间，并生成日切标记。

硬约束：日切失败可回滚（恢复系统日期、重新打开期间）。
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import Any, Dict, Optional

from src.config.settings import SystemSettings, settings

logger = logging.getLogger(__name__)


class DayCutProcessor:
    """
    日切处理器

    负责在日终批处理中执行日切操作：
    1. 切换系统会计日期到下一工作日
    2. 关闭当日会计期间
    3. 生成日切标记

    支持回滚：日切失败时可恢复系统日期并重新打开会计期间。
    """

    def __init__(
        self,
        system_settings: Optional[SystemSettings] = None,
        batch_repository: Any = None,
    ) -> None:
        """
        初始化日切处理器

        Args:
            system_settings: 系统配置实例，默认使用全局settings
            batch_repository: 批次仓储接口，用于记录日切状态
        """
        self._settings = system_settings or settings
        self._batch_repo = batch_repository
        # 日切前的状态快照，用于回滚
        self._pre_cut_state: Optional[Dict[str, Any]] = None
        # 已关闭的会计期间记录
        self._closed_periods: Dict[str, Dict[str, Any]] = {}

    def process(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行日切

        按顺序执行以下操作：
        1. 校验当前系统日期与传入的会计日期一致
        2. 保存日切前状态快照（用于回滚）
        3. 关闭当日会计期间
        4. 计算下一工作日
        5. 切换系统会计日期
        6. 生成日切标记

        Args:
            accounting_date: 当前会计日期（即将被切换的日期）

        Returns:
            日切结果字典，包含：
            - cut_id: 日切标记ID
            - previous_date: 切换前的会计日期
            - new_date: 切换后的新会计日期
            - period_closed: 是否成功关闭会计期间
            - status: 日切状态（success/failed）

        Raises:
            ValueError: 会计日期不一致或日切条件不满足
            RuntimeError: 日切过程中发生不可恢复的错误
        """
        logger.info(f"开始日切处理，当前会计日期: {accounting_date}")

        # 校验会计日期
        if self._settings.system_date != accounting_date:
            raise ValueError(
                f"系统日期 {self._settings.system_date} 与传入的会计日期 "
                f"{accounting_date} 不一致，无法执行日切"
            )

        # 保存日切前状态快照（用于回滚）
        self._pre_cut_state = {
            "system_date": self._settings.system_date,
            "accounting_date": accounting_date,
        }

        # 如果有仓储，创建快照
        snapshot_index = None
        if self._batch_repo and hasattr(self._batch_repo, "create_snapshot"):
            snapshot_index = self._batch_repo.create_snapshot()
            self._pre_cut_state["snapshot_index"] = snapshot_index

        try:
            # 步骤1：关闭当日会计期间
            period_id = self._close_accounting_period(accounting_date)
            logger.info(f"已关闭会计期间: {accounting_date}")

            # 步骤2：计算下一工作日
            next_business_date = self._calculate_next_business_date(accounting_date)
            logger.info(f"下一工作日: {next_business_date}")

            # 步骤3：切换系统会计日期
            self._settings.advance_system_date(next_business_date)
            logger.info(f"系统日期已切换: {accounting_date} -> {next_business_date}")

            # 步骤4：生成日切标记
            cut_id = str(uuid.uuid4())
            cut_record = {
                "cut_id": cut_id,
                "previous_date": accounting_date,
                "new_date": next_business_date,
                "period_closed": True,
                "period_id": period_id,
                "status": "success",
            }

            # 持久化日切记录
            if self._batch_repo:
                self._batch_repo.save({
                    "batch_id": cut_id,
                    "batch_type": "DAY_CUT",
                    "batch_date": accounting_date,
                    "status": "SUCCESS",
                    "previous_date": accounting_date.isoformat(),
                    "new_date": next_business_date.isoformat(),
                })

            logger.info(f"日切处理完成，日切标记ID: {cut_id}")
            return cut_record

        except Exception as e:
            logger.error(f"日切处理失败: {str(e)}，准备回滚")
            # 日切失败，自动回滚
            self.rollback(accounting_date)
            raise RuntimeError(f"日切处理失败并已回滚: {str(e)}") from e

    def rollback(self, accounting_date: date) -> Dict[str, Any]:
        """
        回滚日切

        恢复系统日期到日切前的状态，重新打开已关闭的会计期间。

        Args:
            accounting_date: 需要回滚到的会计日期

        Returns:
            回滚结果字典

        Raises:
            RuntimeError: 回滚失败
        """
        logger.info(f"开始回滚日切，目标恢复日期: {accounting_date}")

        rollback_result: Dict[str, Any] = {
            "target_date": accounting_date,
            "date_restored": False,
            "period_reopened": False,
            "status": "failed",
        }

        try:
            # 恢复系统日期
            if self._pre_cut_state and self._pre_cut_state.get("system_date"):
                self._settings.system_date = self._pre_cut_state["system_date"]
                rollback_result["date_restored"] = True
                logger.info(f"系统日期已恢复: {self._settings.system_date}")
            else:
                # 直接设置为传入的会计日期
                self._settings.system_date = accounting_date
                rollback_result["date_restored"] = True
                logger.info(f"系统日期已恢复为: {accounting_date}")

            # 重新打开会计期间
            self._reopen_accounting_period(accounting_date)
            rollback_result["period_reopened"] = True
            logger.info(f"会计期间已重新打开: {accounting_date}")

            # 回滚仓储快照
            if (
                self._batch_repo
                and hasattr(self._batch_repo, "rollback")
                and self._pre_cut_state
                and "snapshot_index" in self._pre_cut_state
            ):
                self._batch_repo.rollback(self._pre_cut_state["snapshot_index"])
                logger.info("仓储快照已回滚")

            rollback_result["status"] = "success"
            logger.info(f"日切回滚完成，系统日期: {self._settings.system_date}")

        except Exception as e:
            rollback_result["error"] = str(e)
            logger.error(f"日切回滚失败: {str(e)}")
            raise RuntimeError(f"日切回滚失败: {str(e)}") from e

        finally:
            # 清除快照状态
            self._pre_cut_state = None

        return rollback_result

    def _close_accounting_period(self, accounting_date: date) -> str:
        """
        关闭会计期间

        标记指定日期的会计期间为已关闭，不再接受新的交易记账。

        Args:
            accounting_date: 要关闭的会计日期

        Returns:
            期间ID
        """
        period_id = f"PERIOD-{accounting_date.isoformat()}"
        self._closed_periods[period_id] = {
            "period_id": period_id,
            "accounting_date": accounting_date,
            "status": "CLOSED",
        }
        return period_id

    def _reopen_accounting_period(self, accounting_date: date) -> None:
        """
        重新打开会计期间

        将已关闭的会计期间重新打开，允许继续记账。

        Args:
            accounting_date: 要重新打开的会计日期
        """
        period_id = f"PERIOD-{accounting_date.isoformat()}"
        if period_id in self._closed_periods:
            self._closed_periods[period_id]["status"] = "OPEN"
        logger.debug(f"会计期间已重新打开: {period_id}")

    def _calculate_next_business_date(self, current_date: date) -> date:
        """
        计算下一工作日

        简单实现：跳过周六和周日。
        实际生产环境中应查询节假日表。

        Args:
            current_date: 当前日期

        Returns:
            下一工作日日期
        """
        next_date = current_date + timedelta(days=1)
        # 跳过周末（周六=5，周日=6）
        while next_date.weekday() in (5, 6):
            next_date += timedelta(days=1)
        return next_date

    def is_period_closed(self, accounting_date: date) -> bool:
        """
        检查指定日期的会计期间是否已关闭

        Args:
            accounting_date: 会计日期

        Returns:
            True表示已关闭，False表示仍开放
        """
        period_id = f"PERIOD-{accounting_date.isoformat()}"
        period = self._closed_periods.get(period_id)
        if period is None:
            return False
        return period["status"] == "CLOSED"
