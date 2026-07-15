"""
账户相关领域事件

包括开户、销户、冻结、解冻等账户生命周期事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from .domain_event import DomainEvent


@dataclass
class AccountOpenedEvent(DomainEvent):
    """
    开户事件

    当新账户成功创建时触发。
    """

    account_number: str = ""
    customer_id: str = ""
    account_type: str = ""
    currency: str = "CNY"
    interest_rate: Decimal = Decimal("0.00")
    open_date: Optional[date] = None

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "customer_id": self.customer_id,
            "account_type": self.account_type,
            "currency": self.currency,
            "interest_rate": str(self.interest_rate),
            "open_date": str(self.open_date) if self.open_date else None,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"AccountOpenedEvent(account={self.account_number!r}, "
            f"customer={self.customer_id!r}, "
            f"type={self.account_type!r})"
        )


@dataclass
class AccountClosedEvent(DomainEvent):
    """
    销户事件

    当账户成功销户时触发。
    """

    account_number: str = ""
    customer_id: str = ""
    close_date: Optional[date] = None
    reason: str = ""

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "customer_id": self.customer_id,
            "close_date": str(self.close_date) if self.close_date else None,
            "reason": self.reason,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"AccountClosedEvent(account={self.account_number!r}, "
            f"close_date={self.close_date})"
        )


@dataclass
class AccountFrozenEvent(DomainEvent):
    """
    账户冻结事件

    当账户资金被冻结时触发。
    """

    account_number: str = ""
    freeze_id: str = ""
    freeze_amount: Decimal = Decimal("0.00")
    freeze_type: str = ""
    freeze_reason: str = ""

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "freeze_id": self.freeze_id,
            "freeze_amount": str(self.freeze_amount),
            "freeze_type": self.freeze_type,
            "freeze_reason": self.freeze_reason,
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"AccountFrozenEvent(account={self.account_number!r}, "
            f"amount={self.freeze_amount}, "
            f"type={self.freeze_type!r})"
        )


@dataclass
class AccountUnfrozenEvent(DomainEvent):
    """
    账户解冻事件

    当账户资金被解冻时触发。
    """

    account_number: str = ""
    freeze_id: str = ""
    unfreeze_amount: Decimal = Decimal("0.00")

    def __post_init__(self) -> None:
        self.aggregate_type = "Account"
        self.aggregate_id = self.account_number
        self.payload = {
            "account_number": self.account_number,
            "freeze_id": self.freeze_id,
            "unfreeze_amount": str(self.unfreeze_amount),
        }
        super().__post_init__()

    def __repr__(self) -> str:
        return (
            f"AccountUnfrozenEvent(account={self.account_number!r}, "
            f"amount={self.unfreeze_amount})"
        )
