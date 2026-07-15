"""
冻结记录模型

记录账户资金冻结和解冻的完整历史。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class FreezeType(Enum):
    """冻结类型枚举"""
    JUDICIAL = "JUDICIAL"       # 司法冻结
    INTERNAL = "INTERNAL"       # 内部冻结（如风控）


class FreezeStatus(Enum):
    """冻结状态枚举"""
    ACTIVE = "ACTIVE"           # 冻结中
    RELEASED = "RELEASED"       # 已解冻
    EXPIRED = "EXPIRED"         # 已过期


@dataclass
class FreezeRecord:
    """
    冻结记录实体

    记录一次资金冻结操作的完整信息，包括冻结和解冻。
    """

    freeze_id: str                      # 冻结编号
    account_number: str                 # 账号
    freeze_amount: Decimal              # 冻结金额
    freeze_type: FreezeType             # 冻结类型（司法/内部）
    freeze_reason: str                  # 冻结原因
    freeze_time: datetime = field(default_factory=datetime.now)  # 冻结时间
    unfreeze_time: Optional[datetime] = None  # 解冻时间
    status: FreezeStatus = FreezeStatus.ACTIVE  # 状态
    operator: Optional[str] = None      # 操作员
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        self._validate()

    def _validate(self) -> None:
        """校验数据"""
        if not self.freeze_id:
            raise ValueError("冻结编号不能为空")
        if not self.account_number:
            raise ValueError("账号不能为空")
        if self.freeze_amount <= Decimal("0"):
            raise ValueError("冻结金额必须大于零")
        if not self.freeze_reason:
            raise ValueError("冻结原因不能为空")

    def release(self, operator: Optional[str] = None) -> None:
        """
        解冻

        Args:
            operator: 操作员

        Raises:
            ValueError: 当前状态不允许解冻
        """
        if self.status != FreezeStatus.ACTIVE:
            raise ValueError(f"冻结记录 {self.freeze_id} 当前状态为 {self.status.value}，无法解冻")
        self.status = FreezeStatus.RELEASED
        self.unfreeze_time = datetime.now()
        if operator:
            self.operator = operator

    def expire(self) -> None:
        """
        标记为过期

        Raises:
            ValueError: 当前状态不允许标记过期
        """
        if self.status != FreezeStatus.ACTIVE:
            raise ValueError(f"冻结记录 {self.freeze_id} 当前状态为 {self.status.value}，无法标记过期")
        self.status = FreezeStatus.EXPIRED
        self.unfreeze_time = datetime.now()

    def is_active(self) -> bool:
        """判断是否仍在冻结中"""
        return self.status == FreezeStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"FreezeRecord(id={self.freeze_id!r}, "
            f"account={self.account_number!r}, "
            f"amount={self.freeze_amount}, "
            f"type={self.freeze_type.value}, "
            f"status={self.status.value})"
        )
