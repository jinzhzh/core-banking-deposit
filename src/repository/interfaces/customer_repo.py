"""
客户仓储接口

定义客户实体的持久化操作抽象，包括增删改查等基本操作。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.customer import Customer


class CustomerRepository(ABC):
    """客户仓储抽象接口"""

    @abstractmethod
    def save(self, customer: Customer) -> Customer:
        """
        保存客户实体

        Args:
            customer: 待保存的客户实体

        Returns:
            保存后的客户实体

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_by_id(self, customer_id: str) -> Optional[Customer]:
        """
        根据客户ID查找客户

        Args:
            customer_id: 客户唯一标识

        Returns:
            找到的客户实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_id_number(self, id_number: str) -> Optional[Customer]:
        """
        根据证件号码查找客户

        Args:
            id_number: 客户证件号码（如身份证号）

        Returns:
            找到的客户实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_all(self) -> List[Customer]:
        """
        查找所有客户

        Returns:
            所有客户实体列表
        """
        ...

    @abstractmethod
    def update(self, customer: Customer) -> Customer:
        """
        更新客户实体

        Args:
            customer: 待更新的客户实体

        Returns:
            更新后的客户实体

        Raises:
            RepositoryError: 客户不存在或更新失败时抛出
        """
        ...

    @abstractmethod
    def delete(self, customer_id: str) -> bool:
        """
        删除客户

        Args:
            customer_id: 待删除的客户ID

        Returns:
            删除成功返回True，客户不存在返回False
        """
        ...
