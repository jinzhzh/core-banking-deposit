"""
交易仓储内存实现

使用字典作为底层存储，支持快照和回滚操作。
线程安全：所有读写操作均通过threading.Lock保护。
"""

import copy
import threading
from datetime import datetime
from typing import Dict, List, Optional

from src.domain.models.transaction import Transaction
from src.repository.interfaces.transaction_repo import TransactionRepository


class InMemoryTransactionRepository(TransactionRepository):
    """
    交易仓储的内存实现

    使用字典存储交易数据，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 主存储：transaction_id -> Transaction
        self._store: Dict[str, Transaction] = {}
        # 账户索引：account_id -> List[transaction_id]
        self._account_index: Dict[str, List[str]] = {}
        # 快照栈，用于回滚
        self._snapshots: List[Dict[str, Transaction]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save(self, transaction: Transaction) -> Transaction:
        """保存交易记录到内存存储"""
        with self._lock:
            transaction_id = str(transaction.transaction_id)
            self._store[transaction_id] = copy.deepcopy(transaction)

            # 维护账户索引
            if hasattr(transaction, "account_id") and transaction.account_id:
                account_id = str(transaction.account_id)
                if account_id not in self._account_index:
                    self._account_index[account_id] = []
                if transaction_id not in self._account_index[account_id]:
                    self._account_index[account_id].append(transaction_id)

            return copy.deepcopy(transaction)

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """根据交易ID查找交易记录"""
        with self._lock:
            transaction = self._store.get(transaction_id)
            return copy.deepcopy(transaction) if transaction else None

    def find_by_account(self, account_id: str) -> List[Transaction]:
        """根据账户ID查找该账户的所有交易记录"""
        with self._lock:
            transaction_ids = self._account_index.get(account_id, [])
            result = []
            for tid in transaction_ids:
                transaction = self._store.get(tid)
                if transaction:
                    result.append(copy.deepcopy(transaction))
            return result

    def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Transaction]:
        """根据日期范围查找交易记录"""
        with self._lock:
            result = []
            for transaction in self._store.values():
                # 假设交易实体有 transaction_date 或 created_at 属性
                txn_date = getattr(
                    transaction, "transaction_date",
                    getattr(transaction, "created_at", None)
                )
                if txn_date and start_date <= txn_date <= end_date:
                    result.append(copy.deepcopy(transaction))
            return result

    def find_by_type(self, transaction_type: str) -> List[Transaction]:
        """根据交易类型查找交易记录"""
        with self._lock:
            result = []
            for transaction in self._store.values():
                txn_type = getattr(transaction, "transaction_type", None)
                # 支持枚举类型和字符串类型的比较
                if txn_type is not None:
                    type_value = txn_type.value if hasattr(txn_type, "value") else str(txn_type)
                    if type_value == transaction_type:
                        result.append(copy.deepcopy(transaction))
            return result

    def create_snapshot(self) -> int:
        """
        创建当前数据快照（用于日切回滚）

        Returns:
            快照索引编号
        """
        with self._lock:
            snapshot = copy.deepcopy(self._store)
            self._snapshots.append(snapshot)
            return len(self._snapshots) - 1

    def rollback(self, snapshot_index: Optional[int] = None) -> None:
        """
        回滚到指定快照

        Args:
            snapshot_index: 快照索引，为None时回滚到最近一次快照
        """
        with self._lock:
            if not self._snapshots:
                raise ValueError("没有可用的快照进行回滚")

            if snapshot_index is None:
                snapshot_index = len(self._snapshots) - 1

            if snapshot_index < 0 or snapshot_index >= len(self._snapshots):
                raise ValueError(f"无效的快照索引: {snapshot_index}")

            # 恢复数据
            self._store = copy.deepcopy(self._snapshots[snapshot_index])

            # 重建账户索引
            self._account_index.clear()
            for transaction_id, transaction in self._store.items():
                if hasattr(transaction, "account_id") and transaction.account_id:
                    account_id = str(transaction.account_id)
                    if account_id not in self._account_index:
                        self._account_index[account_id] = []
                    self._account_index[account_id].append(transaction_id)

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._store.clear()
            self._account_index.clear()
            self._snapshots.clear()
