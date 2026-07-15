"""
账户仓储接口

定义账户聚合根的持久化操作抽象，包括增删改查等基本操作。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.account import Account


class AccountRepository(ABC):
    """账户仓储抽象接口"""

    @abstractmethod
    def save(self, account: Account) -> Account:
        """
        保存账户实体

        Args:
            account: 待保存的账户实体

        Returns:
            保存后的账户实体（可能包含生成的ID等信息）

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_by_id(self, account_id: str) -> Optional[Account]:
        """
        根据账户ID查找账户

        Args:
            account_id: 账户唯一标识

        Returns:
            找到的账户实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_account_number(self, account_number: str) -> Optional[Account]:
        """
        根据账号查找账户

        Args:
            account_number: 银行账号

        Returns:
            找到的账户实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_customer_id(self, customer_id: str) -> List[Account]:
        """
        根据客户ID查找该客户下所有账户

        Args:
            customer_id: 客户唯一标识

        Returns:
            该客户名下的账户列表
        """
        ...

    @abstractmethod
    def find_all(self) -> List[Account]:
        """
        查找所有账户

        Returns:
            所有账户实体列表
        """
        ...

    @abstractmethod
    def update(self, account: Account) -> Account:
        """
        更新账户实体

        Args:
            account: 待更新的账户实体

        Returns:
            更新后的账户实体

        Raises:
            RepositoryError: 账户不存在或更新失败时抛出
        """
        ...

    @abstractmethod
    def delete(self, account_id: str) -> bool:
        """
        删除账户

        Args:
            account_id: 待删除的账户ID

        Returns:
            删除成功返回True，账户不存在返回False
        """
        ...
