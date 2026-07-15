"""
分录仓储接口

定义会计分录的持久化操作抽象，支持按交易、日期、科目代码等维度查询。
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.models.journal import JournalEntry


class JournalRepository(ABC):
    """分录仓储抽象接口"""

    @abstractmethod
    def save(self, entry: JournalEntry) -> JournalEntry:
        """
        保存会计分录

        Args:
            entry: 待保存的分录实体

        Returns:
            保存后的分录实体

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_by_id(self, entry_id: str) -> Optional[JournalEntry]:
        """
        根据分录ID查找分录

        Args:
            entry_id: 分录唯一标识

        Returns:
            找到的分录实体，未找到返回None
        """
        ...

    @abstractmethod
    def find_by_transaction_id(self, transaction_id: str) -> List[JournalEntry]:
        """
        根据交易ID查找关联的所有分录

        Args:
            transaction_id: 交易唯一标识

        Returns:
            与该交易关联的分录列表
        """
        ...

    @abstractmethod
    def find_by_date(self, target_date: date) -> List[JournalEntry]:
        """
        根据日期查找当日所有分录

        Args:
            target_date: 目标日期

        Returns:
            指定日期的分录列表
        """
        ...

    @abstractmethod
    def find_by_account_code(self, account_code: str) -> List[JournalEntry]:
        """
        根据会计科目代码查找分录

        Args:
            account_code: 会计科目代码

        Returns:
            包含该科目的分录列表
        """
        ...
