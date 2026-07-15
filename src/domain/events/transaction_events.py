"""
交易相关领域事件

包括存款、取款、转账、冲正等交易事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .domain_event import DomainEvent


@dataclass
class DepositEvent(DomainEvent):
    """
    存款事件

    当资金成功存入账户时触发。
    """

    account_number: str = ""
    transaction_id: str = ""
    amount: Decimal = Decimal("0.00")
    balance_after: Decimal = Decimal("0.00")
    operator: Optional[str] = None

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "balance_after": str(self.balance_after),
            "operator": self.operator,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"DepositEvent(account={self.account_number!r}, "
            f"amount={self.amount}, "
            f"balance_after={self.balance_after})"
        )


@dataclass
class WithdrawalEvent(DomainEvent):
    """
    取款事件

    当资金成功从账户支出时触发。
    """

    account_number: str = ""
    transaction_id: str = ""
    amount: Decimal = Decimal("0.00")
    balance_after: Decimal = Decimal("0.00")
    operator: Optional[str] = None

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "balance_after": str(self.balance_after),
            "operator": self.operator,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"WithdrawalEvent(account={self.account_number!r}, "
            f"amount={self.amount}, "
            f"balance_after={self.balance_after})"
        )


@dataclass
class TransferEvent(DomainEvent):
    """
    转账事件

    当资金成功在两个账户之间转移时触发。
    """

    from_account: str = ""
    to_account: str = ""
    transaction_id: str = ""
    amount: Decimal = Decimal("0.00")
    from_balance_after: Decimal = Decimal("0.00")
    to_balance_after: Decimal = Decimal("0.00")
    operator: Optional[str] = None

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.from_account
        self.payload = {
            "from_account": self.from_account,
            "to_account": self.to_account,
            "transaction_id": self.transaction_id,
            "amount": str(self.amount),
            "from_balance_after": str(self.from_balance_after),
            "to_balance_after": str(self.to_balance_after),
            "operator": self.operator,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"TransferEvent(from={self.from_account!r}, "
            f"to={self.to_account!r}, "
            f"amount={self.amount})"
        )


@dataclass
class ReversalEvent(DomainEvent):
    """
    冲正事件

    当交易被成功冲正时触发。
    """

    account_number: str = ""
    original_transaction_id: str = ""
    reversal_transaction_id: str = ""
    amount: Decimal = Decimal("0.00")
    balance_after: Decimal = Decimal("0.00")
    reversal_reason: str = ""
    operator: Optional[str] = None

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "original_transaction_id": self.original_transaction_id,
            "reversal_transaction_id": self.reversal_transaction_id,
            "amount": str(self.amount),
            "balance_after": str(self.balance_after),
            "reversal_reason": self.reversal_reason,
            "operator": self.operator,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"ReversalEvent(account={self.account_number!r}, "
            f"original_txn={self.original_transaction_id!r}, "
            f"amount={self.amount}, "
            f"reason={self.reversal_reason!r})"
        )
