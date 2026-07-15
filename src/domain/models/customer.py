"""
客户模型

定义银行客户的基本信息实体。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class IdType(Enum):
    """证件类型枚举"""
    ID_CARD = "ID_CARD"                 # 身份证
    PASSPORT = "PASSPORT"               # 护照
    MILITARY_ID = "MILITARY_ID"         # 军官证
    HK_MACAO_PASS = "HK_MACAO_PASS"    # 港澳通行证
    BUSINESS_LICENSE = "BUSINESS_LICENSE"  # 营业执照（对公）


@dataclass
class Customer:
    """
    客户实体

    存储银行客户的基本身份信息和联系方式。
    """

    customer_id: str                    # 客户ID（系统生成的唯一标识）
    name: str                           # 客户姓名/名称
    id_type: IdType                     # 证件类型
    id_number: str                      # 证件号码
    phone: str                          # 手机号码
    address: Optional[str] = None       # 联系地址
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        self._validate()

    def _validate(self) -> None:
        """校验客户数据"""
        if not self.customer_id:
            raise ValueError("客户ID不能为空")
        if not self.name:
            raise ValueError("客户姓名不能为空")
        if not self.id_number:
            raise ValueError("证件号码不能为空")
        if not self.phone:
            raise ValueError("手机号码不能为空")
        if self.id_type == IdType.ID_CARD and len(self.id_number) != 18:
            raise ValueError("身份证号码必须为18位")
        if not self._validate_phone(self.phone):
            raise ValueError("手机号码格式不正确")

    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """校验手机号格式（中国大陆11位手机号）"""
        return len(phone) == 11 and phone.isdigit() and phone.startswith("1")

    def update_phone(self, new_phone: str) -> None:
        """
        更新手机号

        Args:
            new_phone: 新手机号

        Raises:
            ValueError: 手机号格式不正确
        """
        if not self._validate_phone(new_phone):
            raise ValueError("手机号码格式不正确")
        self.phone = new_phone
        self.updated_at = datetime.now()

    def update_address(self, new_address: str) -> None:
        """
        更新地址

        Args:
            new_address: 新地址
        """
        self.address = new_address
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"Customer(customer_id={self.customer_id!r}, "
            f"name={self.name!r}, "
            f"id_type={self.id_type.value}, "
            f"phone={self.phone!r})"
        )
