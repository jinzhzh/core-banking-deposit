"""
批次仓储内存实现

使用字典作为底层存储，支持批次状态管理和检查点机制。
支持快照和回滚操作，线程安全。
"""

import copy
import threading
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from src.repository.interfaces.batch_repo import BatchRepository


class InMemoryBatchRepository(BatchRepository):
    """
    批次仓储的内存实现

    使用字典存储批次数据和检查点，支持快照和回滚（用于日切回滚场景）。
    """

    def __init__(self) -> None:
        """初始化内存仓储"""
        # 主存储：batch_id -> Dict
        self._store: Dict[str, Dict[str, Any]] = {}
        # 日期索引：date_str -> List[batch_id]
        self._date_index: Dict[str, List[str]] = {}
        # 检查点存储：batch_id -> List[Dict]（按时间顺序存储多个检查点）
        self._checkpoints: Dict[str, List[Dict[str, Any]]] = {}
        # 快照栈，用于回滚
        self._snapshots: List[Tuple[Dict, Dict]] = []
        # 线程锁
        self._lock = threading.Lock()

    def save(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """保存批次记录到内存存储"""
        with self._lock:
            batch_id = batch.get("batch_id")
            if not batch_id:
                raise ValueError("批次数据必须包含batch_id字段")

            batch_id = str(batch_id)
            self._store[batch_id] = copy.deepcopy(batch)

            # 维护日期索引
            batch_date = batch.get("batch_date", batch.get("date"))
            if batch_date:
                if isinstance(batch_date, date):
                    date_key = batch_date.isoformat()
                else:
                    date_key = str(batch_date)
                if date_key not in self._date_index:
                    self._date_index[date_key] = []
                if batch_id not in self._date_index[date_key]:
                    self._date_index[date_key].append(batch_id)

            return copy.deepcopy(batch)

    def find_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """根据批次ID查找批次记录"""
        with self._lock:
            batch = self._store.get(batch_id)
            return copy.deepcopy(batch) if batch else None

    def find_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """根据日期查找批次记录"""
        with self._lock:
            date_key = target_date.isoformat()
            batch_ids = self._date_index.get(date_key, [])
            result = []
            for bid in batch_ids:
                batch = self._store.get(bid)
                if batch:
                    result.append(copy.deepcopy(batch))
            return result

    def update_status(self, batch_id: str, status: str) -> bool:
        """更新批次状态"""
        with self._lock:
            if batch_id not in self._store:
                return False
            self._store[batch_id]["status"] = status
            return True

    def save_checkpoint(self, batch_id: str, checkpoint: Dict[str, Any]) -> bool:
        """保存批次检查点（用于断点续跑和回滚）"""
        with self._lock:
            if batch_id not in self._store:
                raise ValueError(f"批次不存在: {batch_id}")

            if batch_id not in self._checkpoints:
                self._checkpoints[batch_id] = []

            self._checkpoints[batch_id].append(copy.deepcopy(checkpoint))
            return True

    def get_checkpoint(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批次最新检查点"""
        with self._lock:
            checkpoints = self._checkpoints.get(batch_id)
            if not checkpoints:
                return None
            return copy.deepcopy(checkpoints[-1])

    def create_snapshot(self) -> int:
        """
        创建当前数据快照（用于日切回滚）

        Returns:
            快照索引编号
        """
        with self._lock:
            snapshot = (
                copy.deepcopy(self._store),
                copy.deepcopy(self._checkpoints),
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
            store, checkpoints = self._snapshots[snapshot_index]
            self._store = copy.deepcopy(store)
            self._checkpoints = copy.deepcopy(checkpoints)

            # 重建日期索引
            self._date_index.clear()
            for batch_id, batch in self._store.items():
                batch_date = batch.get("batch_date", batch.get("date"))
                if batch_date:
                    if isinstance(batch_date, date):
                        date_key = batch_date.isoformat()
                    else:
                        date_key = str(batch_date)
                    if date_key not in self._date_index:
                        self._date_index[date_key] = []
                    self._date_index[date_key].append(batch_id)

            # 丢弃该快照之后的所有快照
            self._snapshots = self._snapshots[: snapshot_index]

    def clear(self) -> None:
        """清空所有数据和快照"""
        with self._lock:
            self._store.clear()
            self._date_index.clear()
            self._checkpoints.clear()
            self._snapshots.clear()
