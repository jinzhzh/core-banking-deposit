"""
交易仓储接口

定义交易记录的持久化操作抽象，支持按账户、日期范围、交易类型等维度查询。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.models.transaction import Transaction


class TransactionRepository(ABC):
    """交易仓储抽象接口"""

    @abstractmethod
    def save(self, transaction: Transaction) -> Transaction:
        """
        保存交易记录

        Args:
            transaction: 待保存的交易实体

        Returns:
            保存后的交易实体

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        根据交易ID查找交易记录

        Args:
            transaction_id: 交易唯一标识

        Returns:
            找到的交易实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_account(self, account_id: str) -> List[Transaction]:
        """
        根据账户ID查找该账户的所有交易记录

        Args:
            account_id: 账户唯一标识

        Returns:
            该账户的交易记录列表
        """
        ...

    @abstractmethod
    def find_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Transaction]:
        """
        根据日期范围查找交易记录

        Args:
            start_date: 开始日期（含）
            end_date: 结束日期（含）

        Returns:
            指定日期范围内的交易记录列表
        """
        ...

    @abstractmethod
    def find_by_type(self, transaction_type: str) -> List[Transaction]:
        """
        根据交易类型查找交易记录

        Args:
            transaction_type: 交易类型标识

        Returns:
            指定类型的交易记录列表
        """
        ...
