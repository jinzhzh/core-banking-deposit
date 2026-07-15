"""
会计期间模块

管理会计期间的开启、关闭和查询，支持按月划分会计期间。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional, Tuple
import calendar


@dataclass
class PeriodInfo:
    """
    会计期间信息

    Attributes:
        year: 年份
        month: 月份
        start_date: 期间起始日期
        end_date: 期间结束日期
        is_closed: 是否已关闭
    """
    year: int
    month: int
    start_date: date
    end_date: date
    is_closed: bool = False


class AccountingPeriod:
    """
    会计期间管理类

    按自然月划分会计期间，支持期间的开启、关闭和查询。
    """

    def __init__(self) -> None:
        """初始化会计期间管理器"""
        # 已关闭的期间集合：key = (year, month)
        self._closed_periods: Dict[Tuple[int, int], bool] = {}

    def current_period(self) -> PeriodInfo:
        """
        获取当前会计期间

        Returns:
            当前会计期间信息（基于系统当前日期）
        """
        today = date.today()
        return self._build_period_info(today.year, today.month)

    def is_period_closed(self, target_date: date) -> bool:
        """
        判断指定日期所在的会计期间是否已关闭

        Args:
            target_date: 目标日期

        Returns:
            是否已关闭
        """
        key = (target_date.year, target_date.month)
        return self._closed_periods.get(key, False)

    def close_period(self, target_date: date) -> PeriodInfo:
        """
        关闭指定日期所在的会计期间

        关闭后该期间不可再进行过账操作。

        Args:
            target_date: 目标日期

        Returns:
            被关闭的期间信息

        Raises:
            ValueError: 期间已关闭或未来期间不可关闭
        """
        key = (target_date.year, target_date.month)

        # 检查是否已关闭
        if self._closed_periods.get(key, False):
            raise ValueError(
                f"会计期间 {target_date.year}年{target_date.month}月 已关闭"
            )

        # 不允许关闭未来期间
        today = date.today()
        period_end = self._get_month_end(target_date.year, target_date.month)
        if period_end > today:
            raise ValueError(
                f"会计期间 {target_date.year}年{target_date.month}月 "
                f"尚未结束，不可关闭"
            )

        # 关闭期间
        self._closed_periods[key] = True

        period_info = self._build_period_info(target_date.year, target_date.month)
        period_info.is_closed = True
        return period_info

    def get_period_dates(self, target_date: date) -> Tuple[date, date]:
        """
        获取指定日期所在会计期间的起止日期

        Args:
            target_date: 目标日期

        Returns:
            (期间起始日期, 期间结束日期) 元组
        """
        start_date = date(target_date.year, target_date.month, 1)
        end_date = self._get_month_end(target_date.year, target_date.month)
        return start_date, end_date

    def open_period(self, target_date: date) -> PeriodInfo:
        """
        重新开启已关闭的会计期间（特殊操作，需谨慎使用）

        Args:
            target_date: 目标日期

        Returns:
            被重新开启的期间信息

        Raises:
            ValueError: 期间未关闭
        """
        key = (target_date.year, target_date.month)

        if not self._closed_periods.get(key, False):
            raise ValueError(
                f"会计期间 {target_date.year}年{target_date.month}月 未关闭，无需开启"
            )

        self._closed_periods[key] = False
        return self._build_period_info(target_date.year, target_date.month)

    def get_all_closed_periods(self) -> list:
        """
        获取所有已关闭的会计期间

        Returns:
            已关闭的期间信息列表
        """
        closed = []
        for (year, month), is_closed in self._closed_periods.items():
            if is_closed:
                period_info = self._build_period_info(year, month)
                period_info.is_closed = True
                closed.append(period_info)
        return sorted(closed, key=lambda p: (p.year, p.month))

    def _build_period_info(self, year: int, month: int) -> PeriodInfo:
        """
        构建期间信息对象

        Args:
            year: 年份
            month: 月份

        Returns:
            期间信息对象
        """
        start_date = date(year, month, 1)
        end_date = self._get_month_end(year, month)
        is_closed = self._closed_periods.get((year, month), False)

        return PeriodInfo(
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
            is_closed=is_closed,
        )

    @staticmethod
    def _get_month_end(year: int, month: int) -> date:
        """
        获取指定年月的最后一天

        Args:
            year: 年份
            month: 月份

        Returns:
            该月最后一天的日期
        """
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, last_day)
