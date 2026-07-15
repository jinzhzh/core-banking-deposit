"""
分录仓储内存实现

使用字典作为底层存储，支持快照和回滚操作。
线程安全：所有读写操作均通过threading.Lock保护。
"""

import copy
import threading
from datetime import date
from typing import Dict, List, Optional

from src.domain.models.journal import JournalEntry
from src.repository.interfaces.journal_repo import JournalRepository


class InMemoryJournalRepository(JournalRepository):
    """
    分录仓储的内存实现

    使用字典存储分录数据，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 主存储：entry_id -> JournalEntry
        self._store: Dict[str, JournalEntry] = {}
        # 交易索引：transaction_id -> List[entry_id]
        self._transaction_index: Dict[str, List[str]] = {}
        # 日期索引：date_str -> List[entry_id]
        self._date_index: Dict[str, List[str]] = {}
        # 科目索引：account_code -> List[entry_id]
        self._account_code_index: Dict[str, List[str]] = {}
        # 快照栈，用于回滚
        self._snapshots: List[Dict[str, JournalEntry]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save(self, entry: JournalEntry) -> JournalEntry:
        """保存会计分录到内存存储"""
        with self._lock:
            entry_id = str(entry.entry_id)
            self._store[entry_id] = copy.deepcopy(entry)

            # 维护交易索引
            if hasattr(entry, "transaction_id") and entry.transaction_id:
                txn_id = str(entry.transaction_id)
                if txn_id not in self._transaction_index:
                    self._transaction_index[txn_id] = []
                if entry_id not in self._transaction_index[txn_id]:
                    self._transaction_index[txn_id].append(entry_id)

            # 维护日期索引
            entry_date = getattr(entry, "entry_date", getattr(entry, "created_at", None))
            if entry_date:
                if isinstance(entry_date, date):
                    date_key = entry_date.isoformat()
                else:
                    date_key = entry_date.date().isoformat() if hasattr(entry_date, "date") else str(entry_date)
                if date_key not in self._date_index:
                    self._date_index[date_key] = []
                if entry_id not in self._date_index[date_key]:
                    self._date_index[date_key].append(entry_id)

            # 维护科目索引
            if hasattr(entry, "account_code") and entry.account_code:
                code = str(entry.account_code)
                if code not in self._account_code_index:
                    self._account_code_index[code] = []
                if entry_id not in self._account_code_index[code]:
                    self._account_code_index[code].append(entry_id)

            return copy.deepcopy(entry)

    def find_by_id(self, entry_id: str) -> Optional[JournalEntry]:
        """根据分录ID查找分录"""
        with self._lock:
            entry = self._store.get(entry_id)
            return copy.deepcopy(entry) if entry else None

    def find_by_transaction_id(self, transaction_id: str) -> List[JournalEntry]:
        """根据交易ID查找关联的所有分录"""
        with self._lock:
            entry_ids = self._transaction_index.get(transaction_id, [])
            result = []
            for eid in entry_ids:
                entry = self._store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
            return result

    def find_by_date(self, target_date: date) -> List[JournalEntry]:
        """根据日期查找当日所有分录"""
        with self._lock:
            date_key = target_date.isoformat()
            entry_ids = self._date_index.get(date_key, [])
            result = []
            for eid in entry_ids:
                entry = self._store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
            return result

    def find_by_account_code(self, account_code: str) -> List[JournalEntry]:
        """根据会计科目代码查找分录"""
        with self._lock:
            entry_ids = self._account_code_index.get(account_code, [])
            result = []
            for eid in entry_ids:
                entry = self._store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
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

            # 重建所有索引
            self._transaction_index.clear()
            self._date_index.clear()
            self._account_code_index.clear()

            for entry_id, entry in self._store.items():
                # 重建交易索引
                if hasattr(entry, "transaction_id") and entry.transaction_id:
                    txn_id = str(entry.transaction_id)
                    if txn_id not in self._transaction_index:
                        self._transaction_index[txn_id] = []
                    self._transaction_index[txn_id].append(entry_id)

                # 重建日期索引
                entry_date = getattr(entry, "entry_date", getattr(entry, "created_at", None))
                if entry_date:
                    if isinstance(entry_date, date):
                        date_key = entry_date.isoformat()
                    else:
                        date_key = entry_date.date().isoformat() if hasattr(entry_date, "date") else str(entry_date)
                    if date_key not in self._date_index:
                        self._date_index[date_key] = []
                    self._date_index[date_key].append(entry_id)

                # 重建科目索引
                if hasattr(entry, "account_code") and entry.account_code:
                    code = str(entry.account_code)
                    if code not in self._account_code_index:
                        self._account_code_index[code] = []
                    self._account_code_index[code].append(entry_id)

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._store.clear()
            self._transaction_index.clear()
            self._date_index.clear()
            self._account_code_index.clear()
            self._snapshots.clear()
