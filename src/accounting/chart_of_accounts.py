"""
科目表模块

定义银行零售存款业务相关的会计科目，包括科目代码、名称、类型和借贷方向。
提供科目表管理类，支持科目查询和校验。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class AccountType(Enum):
    """科目类型枚举"""
    ASSET = "资产"
    LIABILITY = "负债"
    PROFIT_LOSS = "损益"


class DebitCreditDirection(Enum):
    """借贷方向枚举：表示余额增加的方向"""
    DEBIT = "借方"
    CREDIT = "贷方"


@dataclass(frozen=True)
class AccountCode:
    """
    会计科目

    Attributes:
        code: 科目代码
        name: 科目名称
        account_type: 科目类型（资产/负债/损益）
        direction: 借贷方向（余额增加方向）
    """
    code: str
    name: str
    account_type: AccountType
    direction: DebitCreditDirection

    def __repr__(self) -> str:
        return (
            f"AccountCode(code={self.code!r}, name={self.name!r}, "
            f"type={self.account_type.value}, direction={self.direction.value})"
        )


# 预定义科目常量
CASH = AccountCode(
    code="1001",
    name="库存现金",
    account_type=AccountType.ASSET,
    direction=DebitCreditDirection.DEBIT,
)

DEMAND_DEPOSIT = AccountCode(
    code="2001",
    name="活期存款",
    account_type=AccountType.LIABILITY,
    direction=DebitCreditDirection.CREDIT,
)

TERM_DEPOSIT = AccountCode(
    code="2002",
    name="定期存款",
    account_type=AccountType.LIABILITY,
    direction=DebitCreditDirection.CREDIT,
)

INTEREST_PAYABLE = AccountCode(
    code="2003",
    name="应付利息",
    account_type=AccountType.LIABILITY,
    direction=DebitCreditDirection.CREDIT,
)

INTEREST_EXPENSE = AccountCode(
    code="2004",
    name="利息支出",
    account_type=AccountType.PROFIT_LOSS,
    direction=DebitCreditDirection.DEBIT,
)

FROZEN_FUNDS = AccountCode(
    code="3001",
    name="冻结资金",
    account_type=AccountType.ASSET,
    direction=DebitCreditDirection.DEBIT,
)


class ChartOfAccounts:
    """
    科目表管理类

    管理所有会计科目，提供查询、注册和校验方法。
    初始化时自动加载银行零售存款业务的预定义科目。
    """

    def __init__(self) -> None:
        """初始化科目表，加载预定义科目"""
        self._accounts: Dict[str, AccountCode] = {}
        # 加载预定义科目
        self._load_default_accounts()

    def _load_default_accounts(self) -> None:
        """加载预定义的银行零售存款科目"""
        default_accounts = [
            CASH,
            DEMAND_DEPOSIT,
            TERM_DEPOSIT,
            INTEREST_PAYABLE,
            INTEREST_EXPENSE,
            FROZEN_FUNDS,
        ]
        for account in default_accounts:
            self._accounts[account.code] = account

    def register(self, account: AccountCode) -> None:
        """
        注册新科目

        Args:
            account: 要注册的科目对象

        Raises:
            ValueError: 科目代码已存在
        """
        if account.code in self._accounts:
            raise ValueError(f"科目代码 {account.code} 已存在")
        self._accounts[account.code] = account

    def get_by_code(self, code: str) -> AccountCode:
        """
        根据科目代码查询科目

        Args:
            code: 科目代码

        Returns:
            对应的科目对象

        Raises:
            KeyError: 科目代码不存在
        """
        if code not in self._accounts:
            raise KeyError(f"科目代码 {code} 不存在")
        return self._accounts[code]

    def get_by_name(self, name: str) -> Optional[AccountCode]:
        """
        根据科目名称查询科目

        Args:
            name: 科目名称

        Returns:
            对应的科目对象，未找到返回None
        """
        for account in self._accounts.values():
            if account.name == name:
                return account
        return None

    def get_by_type(self, account_type: AccountType) -> List[AccountCode]:
        """
        根据科目类型查询所有科目

        Args:
            account_type: 科目类型

        Returns:
            该类型下的所有科目列表
        """
        return [
            acc for acc in self._accounts.values()
            if acc.account_type == account_type
        ]

    def get_all(self) -> List[AccountCode]:
        """
        获取所有科目

        Returns:
            所有已注册科目的列表
        """
        return list(self._accounts.values())

    def exists(self, code: str) -> bool:
        """
        判断科目代码是否存在

        Args:
            code: 科目代码

        Returns:
            是否存在
        """
        return code in self._accounts

    def __len__(self) -> int:
        """返回科目总数"""
        return len(self._accounts)

    def __repr__(self) -> str:
        return f"ChartOfAccounts(accounts={len(self._accounts)})"
