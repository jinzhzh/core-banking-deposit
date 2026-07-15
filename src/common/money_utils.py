"""
金额工具模块

使用Decimal进行精确计算，避免浮点数精度问题。
系统内部金额以"分"为单位（整数）存储，计算时转换为Decimal。
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, InvalidOperation
from typing import Union


# 常用精度量化器
PRECISION_2 = Decimal("0.01")  # 2位小数（元）
PRECISION_8 = Decimal("0.00000001")  # 8位小数（利息中间计算）


def cents_to_yuan(cents: int) -> Decimal:
    """
    分转元

    Args:
        cents: 金额（分）

    Returns:
        金额（元），Decimal类型
    """
    return Decimal(str(cents)) / Decimal("100")


def yuan_to_cents(yuan: Union[Decimal, str, float]) -> int:
    """
    元转分（四舍五入到分）

    Args:
        yuan: 金额（元）

    Returns:
        金额（分），整数
    """
    if isinstance(yuan, float):
        yuan = Decimal(str(yuan))
    elif isinstance(yuan, str):
        yuan = Decimal(yuan)

    cents = yuan * Decimal("100")
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_interest(
    principal_cents: int,
    annual_rate_percent: Decimal,
    days: int,
    year_days: int = 360,
) -> int:
    """
    计算利息

    公式：利息 = 本金 × 年利率 × 天数 / 年天数
    结果四舍五入到分。

    Args:
        principal_cents: 本金（分）
        annual_rate_percent: 年利率（%），如1.75表示1.75%
        days: 计息天数
        year_days: 年天数，默认360

    Returns:
        利息金额（分）
    """
    if principal_cents <= 0 or days <= 0:
        return 0

    principal = Decimal(str(principal_cents))
    rate = annual_rate_percent / Decimal("100")  # 转换为小数
    day_count = Decimal(str(days))
    year_day_count = Decimal(str(year_days))

    # 高精度中间计算
    interest = principal * rate * day_count / year_day_count

    # 四舍五入到分（整数）
    return int(interest.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_compound_interest(
    principal_cents: int,
    annual_rate_percent: Decimal,
    term_months: int,
    compound_frequency: int = 1,
) -> int:
    """
    计算复利（定期存款到期利息）

    对于整存整取，通常使用单利计算。此函数用于特殊复利产品。
    公式：本息 = 本金 × (1 + 年利率/复利次数) ^ (复利次数×年数)

    Args:
        principal_cents: 本金（分）
        annual_rate_percent: 年利率（%）
        term_months: 存期（月）
        compound_frequency: 每年复利次数

    Returns:
        利息金额（分）
    """
    if principal_cents <= 0 or term_months <= 0:
        return 0

    principal = Decimal(str(principal_cents))
    rate = annual_rate_percent / Decimal("100")
    years = Decimal(str(term_months)) / Decimal("12")
    freq = Decimal(str(compound_frequency))

    # 复利计算
    amount = principal * (1 + rate / freq) ** (freq * years)
    interest = amount - principal

    return int(interest.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_fixed_interest(
    principal_cents: int,
    annual_rate_percent: Decimal,
    term_months: int,
    year_days: int = 360,
) -> int:
    """
    计算定期存款利息（单利）

    公式：利息 = 本金 × 年利率 × 存期月数 / 12

    Args:
        principal_cents: 本金（分）
        annual_rate_percent: 年利率（%）
        term_months: 存期（月）
        year_days: 年天数（此参数保留兼容性，定期按月计算）

    Returns:
        利息金额（分）
    """
    if principal_cents <= 0 or term_months <= 0:
        return 0

    principal = Decimal(str(principal_cents))
    rate = annual_rate_percent / Decimal("100")
    months = Decimal(str(term_months))

    interest = principal * rate * months / Decimal("12")

    return int(interest.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def round_amount(amount: Decimal, precision: int = 2) -> Decimal:
    """
    金额四舍五入

    Args:
        amount: 金额
        precision: 小数位数

    Returns:
        四舍五入后的金额
    """
    quantizer = Decimal(10) ** -precision
    return amount.quantize(quantizer, rounding=ROUND_HALF_UP)


def truncate_amount(amount: Decimal, precision: int = 2) -> Decimal:
    """
    金额截断（向下取整）

    用于某些银行对利息的处理方式（去尾法）。

    Args:
        amount: 金额
        precision: 小数位数

    Returns:
        截断后的金额
    """
    quantizer = Decimal(10) ** -precision
    return amount.quantize(quantizer, rounding=ROUND_DOWN)


def format_amount(cents: int, show_sign: bool = False) -> str:
    """
    格式化金额显示

    将分转换为带千分位分隔符的元字符串。

    Args:
        cents: 金额（分）
        show_sign: 是否显示正负号

    Returns:
        格式化后的金额字符串，如 "1,234.56"
    """
    yuan = cents_to_yuan(abs(cents))
    formatted = f"{yuan:,.2f}"

    if show_sign:
        if cents > 0:
            return f"+{formatted}"
        elif cents < 0:
            return f"-{formatted}"
    elif cents < 0:
        return f"-{formatted}"

    return formatted


def format_amount_chinese(cents: int) -> str:
    """
    金额转中文大写

    用于凭证打印等场景。

    Args:
        cents: 金额（分）

    Returns:
        中文大写金额，如 "壹仟贰佰叁拾肆元伍角陆分"
    """
    digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
    units_int = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]

    if cents == 0:
        return "零元整"

    negative = cents < 0
    cents = abs(cents)

    yuan_part = cents // 100
    jiao = (cents % 100) // 10
    fen = cents % 10

    result = ""

    # 处理元部分
    if yuan_part > 0:
        yuan_str = str(yuan_part)
        for i, ch in enumerate(yuan_str):
            digit = int(ch)
            unit_index = len(yuan_str) - 1 - i
            if digit != 0:
                result += digits[digit] + units_int[unit_index]
            else:
                # 避免连续的零
                if result and not result.endswith("零"):
                    result += "零"
        # 去除末尾的零
        result = result.rstrip("零")
        result += "元"
    else:
        result = ""

    # 处理角分
    if jiao == 0 and fen == 0:
        result += "整"
    else:
        if jiao > 0:
            result += digits[jiao] + "角"
        elif yuan_part > 0:
            result += "零"
        if fen > 0:
            result += digits[fen] + "分"

    if negative:
        result = "负" + result

    return result


def add_amounts(*amounts: int) -> int:
    """
    安全的金额加法（防止溢出检查）

    Args:
        amounts: 多个金额（分）

    Returns:
        总和
    """
    total = sum(amounts)
    # Python整数无溢出，但检查合理性
    if abs(total) > 10**15:  # 超过10万亿
        raise OverflowError(f"金额计算结果超出合理范围: {total}")
    return total


def subtract_amount(amount1: int, amount2: int) -> int:
    """
    安全的金额减法

    Args:
        amount1: 被减数（分）
        amount2: 减数（分）

    Returns:
        差值
    """
    return add_amounts(amount1, -amount2)
