"""
校验器模块

提供金额校验、账号校验、身份证校验等通用校验功能。
"""

import re
from typing import Optional

from .exceptions import ValidationError, AmountInvalidError, AmountExceedLimitError
from .constants import (
    ACCOUNT_NUMBER_LENGTH,
    ID_CARD_LENGTH_18,
    ID_CARD_LENGTH_15,
    MIN_TRANSACTION_AMOUNT,
    MAX_AMOUNT_DIGITS,
)


def validate_amount(
    amount: int,
    min_amount: int = MIN_TRANSACTION_AMOUNT,
    max_amount: Optional[int] = None,
    field_name: str = "金额",
) -> None:
    """
    校验交易金额

    金额以分为单位存储，必须为正整数。

    Args:
        amount: 金额（分）
        min_amount: 最小金额（分）
        max_amount: 最大金额（分），None表示不限制
        field_name: 字段名称（用于错误提示）

    Raises:
        AmountInvalidError: 金额无效
        AmountExceedLimitError: 金额超限
    """
    if not isinstance(amount, int):
        raise AmountInvalidError(
            message=f"{field_name}必须为整数（分）",
            detail=f"实际类型: {type(amount).__name__}",
        )

    if amount <= 0:
        raise AmountInvalidError(
            message=f"{field_name}必须大于零",
            detail=f"实际值: {amount}",
        )

    if amount < min_amount:
        raise AmountInvalidError(
            message=f"{field_name}不能小于最小限额",
            detail=f"最小: {min_amount}分, 实际: {amount}分",
        )

    if len(str(amount)) > MAX_AMOUNT_DIGITS:
        raise AmountInvalidError(
            message=f"{field_name}位数超限",
            detail=f"最大{MAX_AMOUNT_DIGITS}位, 实际: {len(str(amount))}位",
        )

    if max_amount is not None and amount > max_amount:
        raise AmountExceedLimitError(
            message=f"{field_name}超过限额",
            detail=f"限额: {max_amount}分, 实际: {amount}分",
        )


def validate_account_number(account_number: str) -> None:
    """
    校验银行账号

    规则：
    - 必须为纯数字
    - 长度为标准账号长度（19位）
    - 必须以有效前缀开头

    Args:
        account_number: 银行账号

    Raises:
        ValidationError: 账号格式不正确
    """
    if not account_number:
        raise ValidationError(
            message="账号不能为空",
            code="VAL002",
        )

    if not account_number.isdigit():
        raise ValidationError(
            message="账号必须为纯数字",
            code="VAL002",
            detail=f"账号: {account_number[:4]}****",
        )

    if len(account_number) != ACCOUNT_NUMBER_LENGTH:
        raise ValidationError(
            message=f"账号长度必须为{ACCOUNT_NUMBER_LENGTH}位",
            code="VAL002",
            detail=f"实际长度: {len(account_number)}",
        )

    valid_prefixes = ("6222", "6223", "6224", "6225")
    if not account_number.startswith(valid_prefixes):
        raise ValidationError(
            message="账号前缀无效",
            code="VAL002",
            detail=f"前缀: {account_number[:4]}",
        )

    # Luhn校验（银行卡校验位）
    if not _luhn_check(account_number):
        raise ValidationError(
            message="账号校验位错误",
            code="VAL002",
        )


def validate_id_card(id_card: str) -> None:
    """
    校验身份证号码

    支持18位身份证号码校验，包括：
    - 长度校验
    - 格式校验（前17位数字，最后一位数字或X）
    - 地区码校验
    - 出生日期校验
    - 校验码校验

    Args:
        id_card: 身份证号码

    Raises:
        ValidationError: 身份证号码格式不正确
    """
    if not id_card:
        raise ValidationError(
            message="身份证号码不能为空",
            code="VAL003",
        )

    id_card = id_card.upper().strip()

    if len(id_card) == ID_CARD_LENGTH_15:
        raise ValidationError(
            message="不支持15位身份证号码，请使用18位",
            code="VAL003",
        )

    if len(id_card) != ID_CARD_LENGTH_18:
        raise ValidationError(
            message=f"身份证号码长度必须为{ID_CARD_LENGTH_18}位",
            code="VAL003",
            detail=f"实际长度: {len(id_card)}",
        )

    # 格式校验：前17位数字，最后一位数字或X
    pattern = r"^\d{17}[\dX]$"
    if not re.match(pattern, id_card):
        raise ValidationError(
            message="身份证号码格式错误",
            code="VAL003",
        )

    # 地区码校验（前两位为省级行政区划代码）
    valid_province_codes = {
        "11", "12", "13", "14", "15",  # 京津冀晋蒙
        "21", "22", "23",              # 辽吉黑
        "31", "32", "33", "34", "35", "36", "37",  # 沪苏浙皖闽赣鲁
        "41", "42", "43", "44", "45", "46",        # 豫鄂湘粤桂琼
        "50", "51", "52", "53", "54",              # 渝川黔滇藏
        "61", "62", "63", "64", "65",              # 陕甘青宁新
        "71", "81", "82",                          # 台港澳
    }
    if id_card[:2] not in valid_province_codes:
        raise ValidationError(
            message="身份证号码地区码无效",
            code="VAL003",
        )

    # 出生日期校验
    birth_str = id_card[6:14]
    if not _validate_birth_date(birth_str):
        raise ValidationError(
            message="身份证号码出生日期无效",
            code="VAL003",
        )

    # 校验码校验
    if not _verify_id_card_checksum(id_card):
        raise ValidationError(
            message="身份证号码校验码错误",
            code="VAL003",
        )


def _luhn_check(number: str) -> bool:
    """
    Luhn算法校验

    Args:
        number: 待校验的数字字符串

    Returns:
        校验是否通过
    """
    digits = [int(d) for d in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10 == 0


def _validate_birth_date(birth_str: str) -> bool:
    """
    校验出生日期字符串

    Args:
        birth_str: 8位日期字符串，格式YYYYMMDD

    Returns:
        日期是否有效
    """
    from datetime import date

    try:
        year = int(birth_str[:4])
        month = int(birth_str[4:6])
        day = int(birth_str[6:8])
        birth_date = date(year, month, day)
        # 出生日期不能在未来，也不能太早
        if birth_date > date.today() or year < 1900:
            return False
        return True
    except (ValueError, TypeError):
        return False


def _verify_id_card_checksum(id_card: str) -> bool:
    """
    校验18位身份证校验码

    Args:
        id_card: 18位身份证号码

    Returns:
        校验码是否正确
    """
    # 加权因子
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    # 校验码对照表
    check_codes = "10X98765432"

    total = sum(int(id_card[i]) * weights[i] for i in range(17))
    remainder = total % 11
    expected = check_codes[remainder]

    return id_card[17] == expected
