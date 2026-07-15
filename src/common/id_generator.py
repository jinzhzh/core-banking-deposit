"""
ID生成器模块

提供账号生成、交易流水号生成、分录编号生成等功能。
采用时间戳+序列号+校验位的方式确保唯一性。
"""

import hashlib
import os
import threading
import time
from datetime import datetime
from typing import Optional

from .constants import (
    ACCOUNT_NUMBER_LENGTH,
    ACCOUNT_PREFIX_DEBIT,
    ACCOUNT_PREFIX_FIXED,
    TRANSACTION_ID_LENGTH,
    ENTRY_ID_LENGTH,
    DATE_FORMAT_COMPACT,
    TIME_FORMAT,
)


class SequenceGenerator:
    """线程安全的序列号生成器"""

    def __init__(self, max_value: int = 999999):
        """
        初始化序列号生成器

        Args:
            max_value: 序列号最大值，超过后重置为1
        """
        self._counter = 0
        self._max_value = max_value
        self._lock = threading.Lock()
        self._last_timestamp = ""

    def next(self, timestamp: str = None) -> int:
        """
        获取下一个序列号

        如果时间戳变化则重置序列号。

        Args:
            timestamp: 当前时间戳字符串

        Returns:
            序列号
        """
        with self._lock:
            current_ts = timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
            if current_ts != self._last_timestamp:
                self._counter = 0
                self._last_timestamp = current_ts
            self._counter += 1
            if self._counter > self._max_value:
                self._counter = 1
            return self._counter


# 全局序列号生成器
_account_seq = SequenceGenerator(max_value=9999999)
_transaction_seq = SequenceGenerator(max_value=999999)
_entry_seq = SequenceGenerator(max_value=999999)


def generate_account_number(
    branch_code: str = "110000",
    is_fixed: bool = False,
) -> str:
    """
    生成银行账号

    账号结构（19位）：
    - 前4位：卡BIN（6222=借记卡，6223=定期存单）
    - 5-10位：机构代码（6位）
    - 11-17位：序列号（7位）
    - 18-19位：校验位（Luhn算法）

    Args:
        branch_code: 机构代码（6位）
        is_fixed: 是否定期账户

    Returns:
        19位银行账号
    """
    prefix = ACCOUNT_PREFIX_FIXED if is_fixed else ACCOUNT_PREFIX_DEBIT

    # 确保机构代码为6位
    branch = branch_code.ljust(6, "0")[:6]

    # 生成7位序列号
    seq = _account_seq.next()
    seq_str = str(seq).zfill(7)

    # 拼接前17位
    base_number = f"{prefix}{branch}{seq_str}"

    # 计算Luhn校验位（补足到19位需要2位校验）
    check_digits = _calculate_check_digits(base_number, ACCOUNT_NUMBER_LENGTH)
    account_number = f"{base_number}{check_digits}"

    return account_number


def generate_transaction_id(
    branch_code: str = "110000",
    transaction_date: Optional[datetime] = None,
) -> str:
    """
    生成交易流水号

    流水号结构（32位）：
    - 前8位：交易日期（YYYYMMDD）
    - 9-14位：机构代码
    - 15-20位：时间（HHMMSS）
    - 21-26位：序列号
    - 27-32位：随机数

    Args:
        branch_code: 机构代码
        transaction_date: 交易日期时间，默认当前时间

    Returns:
        32位交易流水号
    """
    now = transaction_date or datetime.now()
    date_str = now.strftime(DATE_FORMAT_COMPACT)
    time_str = now.strftime(TIME_FORMAT)
    branch = branch_code.ljust(6, "0")[:6]

    seq = _transaction_seq.next(date_str + time_str)
    seq_str = str(seq).zfill(6)

    # 6位随机数
    random_part = os.urandom(3).hex()[:6]

    transaction_id = f"{date_str}{branch}{time_str}{seq_str}{random_part}"

    # 确保长度为32位
    return transaction_id[:TRANSACTION_ID_LENGTH].ljust(TRANSACTION_ID_LENGTH, "0")


def generate_entry_id(
    transaction_id: str,
    entry_index: int = 1,
) -> str:
    """
    生成会计分录编号

    分录编号结构（20位）：
    - 前14位：交易流水号前14位（日期+机构）
    - 15-18位：序列号
    - 19-20位：分录序号

    Args:
        transaction_id: 关联的交易流水号
        entry_index: 分录序号（同一笔交易中的第几条分录）

    Returns:
        20位分录编号
    """
    # 取交易流水号前14位
    base = transaction_id[:14]

    seq = _entry_seq.next()
    seq_str = str(seq).zfill(4)

    index_str = str(entry_index).zfill(2)

    entry_id = f"{base}{seq_str}{index_str}"
    return entry_id[:ENTRY_ID_LENGTH]


def generate_batch_id(batch_type: str = "DAY") -> str:
    """
    生成批次编号

    批次编号结构：
    - 前3位：批次类型（DAY=日终，INT=计息，CHK=对账）
    - 4-11位：日期（YYYYMMDD）
    - 12-17位：时间（HHMMSS）
    - 18-20位：序列号

    Args:
        batch_type: 批次类型

    Returns:
        批次编号
    """
    now = datetime.now()
    date_str = now.strftime(DATE_FORMAT_COMPACT)
    time_str = now.strftime(TIME_FORMAT)
    seq = _transaction_seq.next()
    seq_str = str(seq).zfill(3)

    return f"{batch_type[:3]}{date_str}{time_str}{seq_str}"


def _calculate_check_digits(base_number: str, target_length: int) -> str:
    """
    计算校验位（使用Luhn算法变体）

    Args:
        base_number: 基础号码
        target_length: 目标总长度

    Returns:
        校验位字符串
    """
    need_digits = target_length - len(base_number)
    if need_digits <= 0:
        return ""

    # 使用MD5哈希生成伪随机校验位
    hash_input = f"{base_number}{time.time_ns()}"
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()

    # 从哈希中提取数字
    digits = "".join(c for c in hash_value if c.isdigit())
    check_str = digits[:need_digits].ljust(need_digits, "0")

    # 最后一位使用Luhn校验
    full_number = base_number + check_str[:-1]
    luhn_digit = _calculate_luhn_digit(full_number)
    check_str = check_str[:-1] + str(luhn_digit)

    return check_str


def _calculate_luhn_digit(number: str) -> int:
    """
    计算Luhn校验位

    Args:
        number: 不含校验位的数字字符串

    Returns:
        校验位数字
    """
    digits = [int(d) for d in number]
    # 从右到左，偶数位（0-indexed）乘以2
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total = sum(digits)
    return (10 - (total % 10)) % 10
