"""
日期工具模块

提供计息天数计算、工作日判断、会计期间计算等功能。
银行计息规则：按实际天数计息，年按360天计算。
"""

from datetime import date, timedelta
from typing import List, Tuple

from .constants import (
    YEAR_DAYS,
    MONTH_DAYS,
    INTEREST_SETTLEMENT_DAY,
    INTEREST_SETTLEMENT_MONTHS,
)


def calculate_interest_days(start_date: date, end_date: date) -> int:
    """
    计算计息天数

    银行计息规则：算头不算尾（含起始日，不含到期日）。
    即存入当天计息，取出当天不计息。

    Args:
        start_date: 起息日（含）
        end_date: 截止日（不含）

    Returns:
        计息天数

    Raises:
        ValueError: 日期参数无效
    """
    if end_date < start_date:
        raise ValueError(
            f"截止日期 {end_date} 不能早于起息日期 {start_date}"
        )
    return (end_date - start_date).days


def calculate_fixed_maturity_date(start_date: date, term_months: int) -> date:
    """
    计算定期存款到期日

    按月计算到期日，如果到期月没有对应日期则取该月最后一天。

    Args:
        start_date: 存入日期
        term_months: 存期（月）

    Returns:
        到期日期
    """
    year = start_date.year + (start_date.month + term_months - 1) // 12
    month = (start_date.month + term_months - 1) % 12 + 1
    day = start_date.day

    # 处理月末日期（如1月31日存3个月，到期为4月30日）
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(day, max_day)

    return date(year, month, day)


def is_working_day(check_date: date) -> bool:
    """
    判断是否为工作日

    简化实现：周一至周五为工作日，不考虑法定节假日调休。
    生产环境应接入节假日日历服务。

    Args:
        check_date: 待判断日期

    Returns:
        True为工作日，False为非工作日
    """
    # weekday(): 0=周一, 6=周日
    return check_date.weekday() < 5


def get_next_working_day(from_date: date) -> date:
    """
    获取下一个工作日

    Args:
        from_date: 起始日期

    Returns:
        下一个工作日
    """
    next_day = from_date + timedelta(days=1)
    while not is_working_day(next_day):
        next_day += timedelta(days=1)
    return next_day


def get_previous_working_day(from_date: date) -> date:
    """
    获取上一个工作日

    Args:
        from_date: 起始日期

    Returns:
        上一个工作日
    """
    prev_day = from_date - timedelta(days=1)
    while not is_working_day(prev_day):
        prev_day -= timedelta(days=1)
    return prev_day


def is_interest_settlement_date(check_date: date) -> bool:
    """
    判断是否为结息日

    活期存款结息日为每季度末月的20日（3/20、6/20、9/20、12/20）。

    Args:
        check_date: 待判断日期

    Returns:
        True为结息日
    """
    return (
        check_date.month in INTEREST_SETTLEMENT_MONTHS
        and check_date.day == INTEREST_SETTLEMENT_DAY
    )


def get_next_settlement_date(from_date: date) -> date:
    """
    获取下一个结息日

    Args:
        from_date: 起始日期

    Returns:
        下一个结息日
    """
    for month in INTEREST_SETTLEMENT_MONTHS:
        settlement_date = date(from_date.year, month, INTEREST_SETTLEMENT_DAY)
        if settlement_date > from_date:
            return settlement_date

    # 如果当年所有结息日都已过，返回下一年第一个结息日
    return date(
        from_date.year + 1,
        INTEREST_SETTLEMENT_MONTHS[0],
        INTEREST_SETTLEMENT_DAY,
    )


def get_previous_settlement_date(from_date: date) -> date:
    """
    获取上一个结息日

    Args:
        from_date: 起始日期

    Returns:
        上一个结息日
    """
    for month in reversed(INTEREST_SETTLEMENT_MONTHS):
        settlement_date = date(from_date.year, month, INTEREST_SETTLEMENT_DAY)
        if settlement_date < from_date:
            return settlement_date

    # 如果当年所有结息日都在之后，返回上一年最后一个结息日
    return date(
        from_date.year - 1,
        INTEREST_SETTLEMENT_MONTHS[-1],
        INTEREST_SETTLEMENT_DAY,
    )


def get_accounting_period(check_date: date) -> Tuple[str, int]:
    """
    获取会计期间

    返回会计年度和会计月份。

    Args:
        check_date: 日期

    Returns:
        (会计年度字符串, 会计月份) 如 ("2024", 3)
    """
    return str(check_date.year), check_date.month


def get_quarter(check_date: date) -> int:
    """
    获取季度

    Args:
        check_date: 日期

    Returns:
        季度（1-4）
    """
    return (check_date.month - 1) // 3 + 1


def get_quarter_dates(year: int, quarter: int) -> Tuple[date, date]:
    """
    获取季度起止日期

    Args:
        year: 年份
        quarter: 季度（1-4）

    Returns:
        (季度起始日, 季度结束日)
    """
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3

    import calendar
    start_date = date(year, start_month, 1)
    end_day = calendar.monthrange(year, end_month)[1]
    end_date = date(year, end_month, end_day)

    return start_date, end_date


def calculate_months_between(start_date: date, end_date: date) -> int:
    """
    计算两个日期之间的完整月数

    Args:
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        完整月数
    """
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    # 如果结束日的日期小于起始日的日期，则不算完整月
    if end_date.day < start_date.day:
        months -= 1
    return max(0, months)


def get_month_end(check_date: date) -> date:
    """
    获取月末日期

    Args:
        check_date: 日期

    Returns:
        该月最后一天
    """
    import calendar
    last_day = calendar.monthrange(check_date.year, check_date.month)[1]
    return date(check_date.year, check_date.month, last_day)


def is_month_end(check_date: date) -> bool:
    """
    判断是否为月末

    Args:
        check_date: 日期

    Returns:
        True为月末
    """
    return check_date == get_month_end(check_date)


def is_year_end(check_date: date) -> bool:
    """
    判断是否为年末（12月31日）

    Args:
        check_date: 日期

    Returns:
        True为年末
    """
    return check_date.month == 12 and check_date.day == 31
