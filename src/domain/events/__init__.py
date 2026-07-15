"""
领域事件模块

包含核心银行存款系统的所有领域事件定义。
领域事件用于解耦聚合之间的通信，实现最终一致性。
"""

from .domain_event import DomainEvent
from .account_events import (
    AccountOpenedEvent,
    AccountClosedEvent,
    AccountFrozenEvent,
    AccountUnfrozenEvent,
)
from .transaction_events import (
    DepositEvent,
    WithdrawalEvent,
    TransferEvent,
    ReversalEvent,
)

__all__ = [
    "DomainEvent",
    "AccountOpenedEvent",
    "AccountClosedEvent",
    "AccountFrozenEvent",
    "AccountUnfrozenEvent",
    "DepositEvent",
    "WithdrawalEvent",
    "TransferEvent",
    "ReversalEvent",
]
