"""
账本仓储接口

定义总账和分户账的持久化操作抽象，支持记账、查询和余额获取。
"""

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional


class LedgerRepository(ABC):
    """账本仓储抽象接口"""

    @abstractmethod
    def save_general_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存总账分录

        Args:
            entry: 总账分录数据字典，包含科目代码、借贷方向、金额等

        Returns:
            保存后的总账分录数据

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def save_sub_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存分户账分录

        Args:
            entry: 分户账分录数据字典，包含账户ID、借贷方向、金额等

        Returns:
            保存后的分户账分录数据

        Raises:
            RepositoryError: 保存失败时抛出
        """
        ...

    @abstractmethod
    def find_general_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """
        根据日期查找总账分录

        Args:
            target_date: 目标日期

        Returns:
            指定日期的总账分录列表
        """
        ...

    @abstractmethod
    def find_sub_by_account(self, account_id: str) -> List[Dict[str, Any]]:
        """
        根据账户ID查找分户账分录

        Args:
            account_id: 账户唯一标识

        Returns:
            该账户的分户账分录列表
        """
        ...

    @abstractmethod
    def get_balance(self, account_code: str, target_date: Optional[date] = None) -> Decimal:
        """
        获取指定科目的余额

        Args:
            account_code: 会计科目代码
            target_date: 截止日期，为None时返回最新余额

        Returns:
            指定科目的余额
        """
        ...
