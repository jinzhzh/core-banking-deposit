"""
仓储接口定义子模块

定义所有仓储层的抽象接口，供上层服务依赖注入使用。
"""

from src.repository.interfaces.account_repo import AccountRepository
from src.repository.interfaces.transaction_repo import TransactionRepository
from src.repository.interfaces.journal_repo import JournalRepository
from src.repository.interfaces.ledger_repo import LedgerRepository
from src.repository.interfaces.customer_repo import CustomerRepository
from src.repository.interfaces.batch_repo import BatchRepository

__all__ = [
    "AccountRepository",
    "TransactionRepository",
    "JournalRepository",
    "LedgerRepository",
    "CustomerRepository",
    "BatchRepository",
]
