"""
领域事件基类

所有领域事件的抽象基类，定义事件的通用属性和行为。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class DomainEvent:
    """
    领域事件基类

    所有领域事件都继承此类。领域事件是不可变的，一旦创建不应修改。

    属性:
        event_id: 事件唯一标识
        event_type: 事件类型名称
        occurred_at: 事件发生时间
        aggregate_id: 聚合根ID
        aggregate_type: 聚合根类型
        payload: 事件负载数据
        metadata: 事件元数据（如操作员、来源系统等）
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    occurred_at: datetime = field(default_factory=datetime.now)
    aggregate_id: str = ""
    aggregate_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后设置事件类型"""
        if not self.event_type:
            self.event_type = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """
        将事件序列化为字典

        Returns:
            事件的字典表示
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DomainEvent:
        """
        从字典反序列化为事件

        Args:
            data: 事件的字典表示

        Returns:
            领域事件实例
        """
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data.get("event_type", ""),
            occurred_at=datetime.fromisoformat(data["occurred_at"]) if "occurred_at" in data else datetime.now(),
            aggregate_id=data.get("aggregate_id", ""),
            aggregate_type=data.get("aggregate_type", ""),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"event_id={self.event_id!r}, "
            f"type={self.event_type!r}, "
            f"aggregate={self.aggregate_id!r}, "
            f"occurred_at={self.occurred_at})"
        )
