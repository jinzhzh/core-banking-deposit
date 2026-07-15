"""
批次仓储接口

定义批处理任务（如日终批量、日切等）的持久化操作抽象，
支持批次状态管理和检查点机制。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional


class BatchRepository(ABC):
    """批次仓储抽象接口"""

    @abstractmethod
    def save(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存批次记录

        Args:
            batch: 批次数据字典，包含批次ID、类型、状态、日期等

        Returns:
            保存后的批次数据

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        根据批次ID查找批次记录

        Args:
            batch_id: 批次唯一标识

        Returns:
            找到的批次数据字典，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        根据日期查找批次记录

        Args:
            target_date: 目标日期

        Returns:
            指定日期的批次记录列表
        """
        ...

    @abstractmethod
    def update_status(self, batch_id: str, status: str) -> bool:
        """
        更新批次状态

        Args:
            batch_id: 批次唯一标识
            status: 新的批次状态

        Returns:
            更新成功返回True，批次不存在返回False
        """
        ...

    @abstractmethod
    def save_checkpoint(self, batch_id: str, checkpoint: Dict[str, Any]) -> bool:
        """
        保存批次检查点（用于断点续跑和回滚）

        Args:
            batch_id: 批次唯一标识
            checkpoint: 检查点数据，包含已处理进度、状态快照等

        Returns:
            保存成功返回True

        Raises:
            RepositoryError: 批次不存在时抛出
        """
        ...

    @abstractmethod
    def get_checkpoint(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        获取批次最新检查点

        Args:
            batch_id: 批次唯一标识

        Returns:
            最新检查点数据字典，无检查点返回None
        """
        ...
