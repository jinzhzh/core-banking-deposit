"""
日期范围值对象

表示一个不可变的日期区间，支持包含判断和重叠检测。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


class DateRange:
    """
    日期范围值对象（不可变）

    表示一个闭区间 [start_date, end_date] 的日期范围。

    使用示例:
        >>> dr = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        >>> date(2024, 6, 15) in dr  # True
        >>> dr.days  # 366
    """

    __slots__ = ("_start_date", "_end_date")

    def __init__(self, start_date: date, end_date: Optional[date] = None) -> None:
        """
        初始化日期范围

        Args:
            start_date: 开始日期
            end_date: 结束日期，默认为None表示无限期（开放区间）

        Raises:
            ValueError: 结束日期早于开始日期
        """
        if not isinstance(start_date, date):
            raise TypeError("start_date必须是date类型")
        if end_date is not None:
            if not isinstance(end_date, date):
                raise TypeError("end_date必须是date类型")
            if end_date < start_date:
                raise ValueError(
                    f"结束日期不能早于开始日期: {start_date} > {end_date}"
                )
        object.__setattr__(self, "_start_date", start_date)
        object.__setattr__(self, "_end_date", end_date)

    def __setattr__(self, name: str, value) -> None:
        """禁止修改属性，确保不可变性"""
        raise AttributeError("DateRange对象是不可变的，不能修改属性")

    @property
    def start_date(self) -> date:
        """获取开始日期"""
        return self._start_date

    @property
    def end_date(self) -> Optional[date]:
        """获取结束日期"""
        return self._end_date

    @property
    def days(self) -> Optional[int]:
        """
        获取日期范围的天数（含首尾）

        Returns:
            天数，如果end_date为None则返回None
        """
        if self._end_date is None:
            return None
        return (self._end_date - self._start_date).days + 1

    @property
    def calendar_days(self) -> Optional[int]:
        """
        获取日历天数（不含首日，银行计息惯例）

        Returns:
            日历天数，如果end_date为None则返回None
        """
        if self._end_date is None:
            return None
        return (self._end_date - self._start_date).days

    def contains(self, target_date: date) -> bool:
        """
        判断指定日期是否在范围内

        Args:
            target_date: 目标日期

        Returns:
            True表示在范围内
        """
        if target_date < self._start_date:
            return False
        if self._end_date is not None and target_date > self._end_date:
            return False
        return True

    def __contains__(self, target_date: date) -> bool:
        """支持 in 运算符"""
        return self.contains(target_date)

    def overlaps(self, other: DateRange) -> bool:
        """
        判断是否与另一个日期范围重叠

        Args:
            other: 另一个日期范围

        Returns:
            True表示有重叠
        """
        # 如果任一范围是开放的（无结束日期），只要开始日期在对方范围内就重叠
        if self._end_date is None and other._end_date is None:
            return True
        if self._end_date is None:
            return other._end_date >= self._start_date
        if other._end_date is None:
            return self._end_date >= other._start_date
        # 两个闭区间的重叠判断
        return self._start_date <= other._end_date and other._start_date <= self._end_date

    def intersection(self, other: DateRange) -> Optional[DateRange]:
        """
        计算与另一个日期范围的交集

        Args:
            other: 另一个日期范围

        Returns:
            交集的DateRange，如果无交集则返回None
        """
        if not self.overlaps(other):
            return None
        start = max(self._start_date, other._start_date)
        if self._end_date is None and other._end_date is None:
            return DateRange(start, None)
        elif self._end_date is None:
            end = other._end_date
        elif other._end_date is None:
            end = self._end_date
        else:
            end = min(self._end_date, other._end_date)
        return DateRange(start, end)

    def is_open_ended(self) -> bool:
        """判断是否为开放区间（无结束日期）"""
        return self._end_date is None

    def is_expired(self) -> bool:
        """判断日期范围是否已过期"""
        if self._end_date is None:
            return False
        return date.today() > self._end_date

    def is_current(self) -> bool:
        """判断当前日期是否在范围内"""
        return self.contains(date.today())

    def extend(self, days: int) -> DateRange:
        """
        延长日期范围

        Args:
            days: 延长天数

        Returns:
            新的DateRange对象

        Raises:
            ValueError: 开放区间无法延长
        """
        if self._end_date is None:
            raise ValueError("开放区间无法延长")
        new_end = self._end_date + timedelta(days=days)
        return DateRange(self._start_date, new_end)

    def __eq__(self, other: object) -> bool:
        """相等比较"""
        if not isinstance(other, DateRange):
            return NotImplemented
        return self._start_date == other._start_date and self._end_date == other._end_date

    def __hash__(self) -> int:
        """哈希值"""
        return hash((self._start_date, self._end_date))

    def __repr__(self) -> str:
        end_str = str(self._end_date) if self._end_date else "∞"
        return f"DateRange({self._start_date} ~ {end_str})"

    def __str__(self) -> str:
        end_str = str(self._end_date) if self._end_date else "无限期"
        return f"{self._start_date} 至 {end_str}"
