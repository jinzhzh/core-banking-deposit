"""
交易流水模型

记录账户的每一笔交易明细，是不可变的历史记录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class TransactionType(Enum):
    """交易类型枚举"""
    DEPOSIT = "DEPOSIT"             # 存款
    WITHDRAWAL = "WITHDRAWAL"       # 取款
    TRANSFER_IN = "TRANSFER_IN"     # 转入
    TRANSFER_OUT = "TRANSFER_OUT"   # 转出
    INTEREST = "INTEREST"           # 利息入账
    FEE = "FEE"                     # 手续费
    REVERSAL = "REVERSAL"           # 冲正


@dataclass
class Transaction:
    """
    交易流水实体

    记录每一笔交易的完整信息，一旦创建不可修改（不可变实体）。
    冲正操作不修改原流水，而是生成新的反向流水。
    """

    transaction_id: str                     # 流水号（全局唯一）
    account_number: str                     # 账号
    transaction_type: TransactionType       # 交易类型
    amount: Decimal                         # 交易金额（始终为正数）
    balance_after: Decimal                  # 交易后余额
    counterparty_account: Optional[str] = None  # 对手账号（转账时使用）
    summary: str = ""                       # 摘要
    transaction_time: datetime = field(default_factory=datetime.now)  # 交易时间
    operator: Optional[str] = None          # 操作员
    is_reversed: bool = False               # 是否已被冲正

    def __post_init__(self) -> None:
        """初始化后校验"""
        self._validate()

    def _validate(self) -> None:
        """校验交易数据"""
        if not self.transaction_id:
            raise ValueError("流水号不能为空")
        if not self.account_number:
            raise ValueError("账号不能为空")
        if self.amount <= Decimal("0"):
            raise ValueError("交易金额必须大于零")
        if self.balance_after < Decimal("0"):
            raise ValueError("交易后余额不能为负数")

    def mark_reversed(self) -> None:
        """
        标记该流水已被冲正

        Raises:
            ValueError: 流水已被冲正
        """
        if self.is_reversed:
            raise ValueError(f"流水 {self.transaction_id} 已被冲正，不能重复冲正")
        self.is_reversed = True

    def is_credit(self) -> bool:
        """判断是否为贷方交易（资金流入）"""
        return self.transaction_type in (
            TransactionType.DEPOSIT,
            TransactionType.TRANSFER_IN,
            TransactionType.INTEREST,
        )

    def is_debit(self) -> bool:
        """判断是否为借方交易（资金流出）"""
        return self.transaction_type in (
            TransactionType.WITHDRAWAL,
            TransactionType.TRANSFER_OUT,
            TransactionType.FEE,
        )

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.transaction_id!r}, "
            f"account={self.account_number!r}, "
            f"type={self.transaction_type.value}, "
            f"amount={self.amount}, "
            f"balance_after={self.balance_after}, "
            f"reversed={self.is_reversed})"
        )
