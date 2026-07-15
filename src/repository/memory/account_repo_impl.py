"""
账户仓储内存实现

使用字典作为底层存储，支持快照和回滚操作。
线程安全：所有读写操作均通过threading.Lock保护。
"""

import copy
import threading
from typing import Dict, List, Optional

from src.domain.models.account import Account
from src.repository.interfaces.account_repo import AccountRepository


class InMemoryAccountRepository(AccountRepository):
    """
    账户仓储的内存实现

    使用字典存储账户数据，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 主存储：account_id -> Account
        self._store: Dict[str, Account] = {}
        # 账号索引：account_number -> account_id
        self._account_number_index: Dict[str, str] = {}
        # 客户索引：customer_id -> List[account_id]
        self._customer_index: Dict[str, List[str]] = {}
        # 快照栈，用于回滚
        self._snapshots: List[Dict[str, Account]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save(self, account: Account) -> Account:
        """保存账户实体到内存存储"""
        with self._lock:
            account_id = str(account.account_id)
            self._store[account_id] = copy.deepcopy(account)

            # 维护账号索引
            if hasattr(account, "account_number") and account.account_number:
                self._account_number_index[account.account_number] = account_id

            # 维护客户索引
            if hasattr(account, "customer_id") and account.customer_id:
                customer_id = str(account.customer_id)
                if customer_id not in self._customer_index:
                    self._customer_index[customer_id] = []
                if account_id not in self._customer_index[customer_id]:
                    self._customer_index[customer_id].append(account_id)

            return copy.deepcopy(account)

    def find_by_id(self, account_id: str) -> Optional[Account]:
        """根据账户ID查找账户"""
        with self._lock:
            account = self._store.get(account_id)
            return copy.deepcopy(account) if account else None

    def find_by_account_number(self, account_number: str) -> Optional[Account]:
        """根据账号查找账户"""
        with self._lock:
            account_id = self._account_number_index.get(account_number)
            if account_id is None:
                return None
            account = self._store.get(account_id)
            return copy.deepcopy(account) if account else None

    def find_by_customer_id(self, customer_id: str) -> List[Account]:
        """根据客户ID查找该客户下所有账户"""
        with self._lock:
            account_ids = self._customer_index.get(customer_id, [])
            result = []
            for aid in account_ids:
                account = self._store.get(aid)
                if account:
                    result.append(copy.deepcopy(account))
            return result

    def find_all(self) -> List[Account]:
        """查找所有账户"""
        with self._lock:
            return [copy.deepcopy(acc) for acc in self._store.values()]

    def update(self, account: Account) -> Account:
        """更新账户实体"""
        with self._lock:
            account_id = str(account.account_id)
            if account_id not in self._store:
                raise ValueError(f"账户不存在: {account_id}")

            # 更新索引（账号可能变更）
            old_account = self._store[account_id]
            if hasattr(old_account, "account_number") and old_account.account_number:
                self._account_number_index.pop(old_account.account_number, None)

            self._store[account_id] = copy.deepcopy(account)

            if hasattr(account, "account_number") and account.account_number:
                self._account_number_index[account.account_number] = account_id

            return copy.deepcopy(account)

    def delete(self, account_id: str) -> bool:
        """删除账户"""
        with self._lock:
            if account_id not in self._store:
                return False

            account = self._store.pop(account_id)

            # 清理账号索引
            if hasattr(account, "account_number") and account.account_number:
                self._account_number_index.pop(account.account_number, None)

            # 清理客户索引
            if hasattr(account, "customer_id") and account.customer_id:
                customer_id = str(account.customer_id)
                if customer_id in self._customer_index:
                    self._customer_index[customer_id] = [
                        aid for aid in self._customer_index[customer_id]
                        if aid != account_id
                    ]

            return True

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

            # 重建索引
            self._account_number_index.clear()
            self._customer_index.clear()
            for account_id, account in self._store.items():
                if hasattr(account, "account_number") and account.account_number:
                    self._account_number_index[account.account_number] = account_id
                if hasattr(account, "customer_id") and account.customer_id:
                    customer_id = str(account.customer_id)
                    if customer_id not in self._customer_index:
                        self._customer_index[customer_id] = []
                    self._customer_index[customer_id].append(account_id)

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._store.clear()
            self._account_number_index.clear()
            self._customer_index.clear()
            self._snapshots.clear()
