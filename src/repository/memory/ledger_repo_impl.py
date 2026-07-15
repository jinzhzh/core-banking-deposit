"""
账本仓储内存实现

使用字典作为底层存储，支持总账和分户账的记录与查询。
支持快照和回滚操作，线程安全。
"""

import copy
import threading
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.repository.interfaces.ledger_repo import LedgerRepository


class InMemoryLedgerRepository(LedgerRepository):
    """
    账本仓储的内存实现

    使用字典分别存储总账和分户账数据，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 总账存储：entry_id -> Dict
        self._general_store: Dict[str, Dict[str, Any]] = {}
        # 分户账存储：entry_id -> Dict
        self._sub_store: Dict[str, Dict[str, Any]] = {}
        # 总账日期索引：date_str -> List[entry_id]
        self._general_date_index: Dict[str, List[str]] = {}
        # 分户账账户索引：account_id -> List[entry_id]
        self._sub_account_index: Dict[str, List[str]] = {}
        # 余额缓存：account_code -> Decimal
        self._balance_cache: Dict[str, Decimal] = {}
        # 快照栈，用于回滚（保存总账和分户账的完整状态）
        self._snapshots: List[Tuple[Dict, Dict, Dict]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save_general_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """保存总账分录到内存存储"""
        with self._lock:
            # 确保有唯一ID
            if "entry_id" not in entry:
                entry["entry_id"] = str(uuid.uuid4())

            entry_id = entry["entry_id"]
            self._general_store[entry_id] = copy.deepcopy(entry)

            # 维护日期索引
            entry_date = entry.get("entry_date", entry.get("date"))
            if entry_date:
                if isinstance(entry_date, date):
                    date_key = entry_date.isoformat()
                else:
                    date_key = str(entry_date)
                if date_key not in self._general_date_index:
                    self._general_date_index[date_key] = []
                if entry_id not in self._general_date_index[date_key]:
                    self._general_date_index[date_key].append(entry_id)

            # 更新余额缓存
            account_code = entry.get("account_code")
            if account_code:
                amount = Decimal(str(entry.get("amount", 0)))
                direction = entry.get("direction", "debit")
                if account_code not in self._balance_cache:
                    self._balance_cache[account_code] = Decimal("0")
                if direction == "debit":
                    self._balance_cache[account_code] += amount
                else:
                    self._balance_cache[account_code] -= amount

            return copy.deepcopy(entry)

    def save_sub_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """保存分户账分录到内存存储"""
        with self._lock:
            # 确保有唯一ID
            if "entry_id" not in entry:
                entry["entry_id"] = str(uuid.uuid4())

            entry_id = entry["entry_id"]
            self._sub_store[entry_id] = copy.deepcopy(entry)

            # 维护账户索引
            account_id = entry.get("account_id")
            if account_id:
                account_id = str(account_id)
                if account_id not in self._sub_account_index:
                    self._sub_account_index[account_id] = []
                if entry_id not in self._sub_account_index[account_id]:
                    self._sub_account_index[account_id].append(entry_id)

            return copy.deepcopy(entry)

    def find_general_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """根据日期查找总账分录"""
        with self._lock:
            date_key = target_date.isoformat()
            entry_ids = self._general_date_index.get(date_key, [])
            result = []
            for eid in entry_ids:
                entry = self._general_store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
            return result

    def find_sub_by_account(self, account_id: str) -> List[Dict[str, Any]]:
        """根据账户ID查找分户账分录"""
        with self._lock:
            entry_ids = self._sub_account_index.get(account_id, [])
            result = []
            for eid in entry_ids:
                entry = self._sub_store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
            return result

    def get_balance(self, account_code: str, target_date: Optional[date] = None) -> Decimal:
        """获取指定科目的余额"""
        with self._lock:
            if target_date is None:
                # 返回最新余额
                return self._balance_cache.get(account_code, Decimal("0"))

            # 按日期计算余额：遍历总账分录累计到指定日期
            balance = Decimal("0")
            for entry in self._general_store.values():
                if entry.get("account_code") != account_code:
                    continue
                entry_date = entry.get("entry_date", entry.get("date"))
                if entry_date:
                    if isinstance(entry_date, date):
                        entry_date_val = entry_date
                    else:
                        # 尝试解析字符串日期
                        from datetime import date as date_cls
                        try:
                            entry_date_val = date_cls.fromisoformat(str(entry_date))
                        except (ValueError, TypeError):
                            continue
                    if entry_date_val <= target_date:
                        amount = Decimal(str(entry.get("amount", 0)))
                        direction = entry.get("direction", "debit")
                        if direction == "debit":
                            balance += amount
                        else:
                            balance -= amount
            return balance

    def create_snapshot(self) -> int:
        """
        创建当前数据快照（用于日切回滚）

        Returns:
            快照索引编号
        """
        with self._lock:
            snapshot = (
                copy.deepcopy(self._general_store),
                copy.deepcopy(self._sub_store),
                copy.deepcopy(self._balance_cache),
            )
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
            general_store, sub_store, balance_cache = self._snapshots[snapshot_index]
            self._general_store = copy.deepcopy(general_store)
            self._sub_store = copy.deepcopy(sub_store)
            self._balance_cache = copy.deepcopy(balance_cache)

            # 重建索引
            self._general_date_index.clear()
            for entry_id, entry in self._general_store.items():
                entry_date = entry.get("entry_date", entry.get("date"))
                if entry_date:
                    if isinstance(entry_date, date):
                        date_key = entry_date.isoformat()
                    else:
                        date_key = str(entry_date)
                    if date_key not in self._general_date_index:
                        self._general_date_index[date_key] = []
                    self._general_date_index[date_key].append(entry_id)

            self._sub_account_index.clear()
            for entry_id, entry in self._sub_store.items():
                account_id = entry.get("account_id")
                if account_id:
                    account_id = str(account_id)
                    if account_id not in self._sub_account_index:
                        self._sub_account_index[account_id] = []
                    self._sub_account_index[account_id].append(entry_id)

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._general_store.clear()
            self._sub_store.clear()
            self._general_date_index.clear()
            self._sub_account_index.clear()
            self._balance_cache.clear()
            self._snapshots.clear()
