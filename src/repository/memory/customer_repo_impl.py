"""
客户仓储内存实现

使用字典作为底层存储，支持快照和回滚操作。
线程安全：所有读写操作均通过threading.Lock保护。
"""

import copy
import threading
from typing import Dict, List, Optional

from src.domain.models.customer import Customer
from src.repository.interfaces.customer_repo import CustomerRepository


class InMemoryCustomerRepository(CustomerRepository):
    """
    客户仓储的内存实现

    使用字典存储客户数据，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 主存储：customer_id -> Customer
        self._store: Dict[str, Customer] = {}
        # 证件号索引：id_number -> customer_id
        self._id_number_index: Dict[str, str] = {}
        # 快照栈，用于回滚
        self._snapshots: List[Dict[str, Customer]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save(self, customer: Customer) -> Customer:
        """保存客户实体到内存存储"""
        with self._lock:
            customer_id = str(customer.customer_id)
            self._store[customer_id] = copy.deepcopy(customer)

            # 维护证件号索引
            if hasattr(customer, "id_number") and customer.id_number:
                self._id_number_index[customer.id_number] = customer_id

            return copy.deepcopy(customer)

    def find_by_id(self, customer_id: str) -> Optional[Customer]:
        """根据客户ID查找客户"""
        with self._lock:
            customer = self._store.get(customer_id)
            return copy.deepcopy(customer) if customer else None

    def find_by_id_number(self, id_number: str) -> Optional[Customer]:
        """根据证件号码查找客户"""
        with self._lock:
            customer_id = self._id_number_index.get(id_number)
            if customer_id is None:
                return None
            customer = self._store.get(customer_id)
            return copy.deepcopy(customer) if customer else None

    def find_all(self) -> List[Customer]:
        """查找所有客户"""
        with self._lock:
            return [copy.deepcopy(c) for c in self._store.values()]

    def update(self, customer: Customer) -> Customer:
        """更新客户实体"""
        with self._lock:
            customer_id = str(customer.customer_id)
            if customer_id not in self._store:
                raise ValueError(f"客户不存在: {customer_id}")

            # 更新索引（证件号可能变更）
            old_customer = self._store[customer_id]
            if hasattr(old_customer, "id_number") and old_customer.id_number:
                self._id_number_index.pop(old_customer.id_number, None)

            self._store[customer_id] = copy.deepcopy(customer)

            if hasattr(customer, "id_number") and customer.id_number:
                self._id_number_index[customer.id_number] = customer_id

            return copy.deepcopy(customer)

    def delete(self, customer_id: str) -> bool:
        """删除客户"""
        with self._lock:
            if customer_id not in self._store:
                return False

            customer = self._store.pop(customer_id)

            # 清理证件号索引
            if hasattr(customer, "id_number") and customer.id_number:
                self._id_number_index.pop(customer.id_number, None)

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
            self._id_number_index.clear()
            for customer_id, customer in self._store.items():
                if hasattr(customer, "id_number") and customer.id_number:
                    self._id_number_index[customer.id_number] = customer_id

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._store.clear()
            self._id_number_index.clear()
            self._snapshots.clear()
