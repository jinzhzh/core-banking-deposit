"""
账户模型

定义存款账户的核心实体，包括活期账户和定期账户。
账户是存款业务的聚合根，管理余额、冻结和状态变更。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class AccountType(Enum):
    """账户类型枚举"""
    DEMAND = "DEMAND"       # 活期存款
    FIXED = "FIXED"         # 定期存款


class AccountStatus(Enum):
    """账户状态枚举"""
    ACTIVE = "ACTIVE"           # 正常
    FROZEN = "FROZEN"           # 冻结
    DORMANT = "DORMANT"         # 久悬
    CLOSED = "CLOSED"           # 已销户


@dataclass
class Account:
    """
    存款账户实体（聚合根）

    管理账户的余额、冻结金额和状态。
    余额关系：可用余额 = 余额 - 冻结金额
    """

    account_number: str                         # 账号
    customer_id: str                            # 客户ID
    account_type: AccountType                   # 账户类型（活期/定期）
    status: AccountStatus = AccountStatus.ACTIVE  # 账户状态
    balance: Decimal = Decimal("0.00")          # 账户余额（账面余额）
    available_balance: Decimal = Decimal("0.00")  # 可用余额
    frozen_amount: Decimal = Decimal("0.00")    # 冻结金额
    open_date: date = field(default_factory=date.today)  # 开户日期
    close_date: Optional[date] = None           # 销户日期
    currency: str = "CNY"                       # 币种
    interest_rate: Decimal = Decimal("0.00")    # 利率（年化，如0.0035表示0.35%）
    maturity_date: Optional[date] = None        # 定期到期日（仅定期账户）
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        self._validate()

    def _validate(self) -> None:
        """校验账户数据完整性"""
        if self.balance < Decimal("0"):
            raise ValueError("账户余额不能为负数")
        if self.frozen_amount < Decimal("0"):
            raise ValueError("冻结金额不能为负数")
        if self.frozen_amount > self.balance:
            raise ValueError("冻结金额不能超过账户余额")
        if self.account_type == AccountType.FIXED and self.maturity_date is None:
            # 定期账户必须设置到期日
            pass  # 开户时可能尚未设置，由业务层保证
        self.available_balance = self.balance - self.frozen_amount

    def deposit(self, amount: Decimal) -> None:
        """
        存入资金

        Args:
            amount: 存入金额，必须大于零

        Raises:
            ValueError: 金额不合法或账户状态不允许
        """
        if amount <= Decimal("0"):
            raise ValueError("存入金额必须大于零")
        if self.status == AccountStatus.CLOSED:
            raise ValueError("已销户账户不能存入资金")
        self.balance += amount
        self.available_balance = self.balance - self.frozen_amount
        self.updated_at = datetime.now()

    def withdraw(self, amount: Decimal) -> None:
        """
        支出资金

        Args:
            amount: 支出金额，必须大于零且不超过可用余额

        Raises:
            ValueError: 金额不合法、余额不足或账户状态不允许
        """
        if amount <= Decimal("0"):
            raise ValueError("支出金额必须大于零")
        if self.status == AccountStatus.CLOSED:
            raise ValueError("已销户账户不能支出资金")
        if self.status == AccountStatus.FROZEN:
            raise ValueError("冻结账户不能支出资金")
        if amount > self.available_balance:
            raise ValueError(
                f"可用余额不足，当前可用余额: {self.available_balance}，"
                f"请求支出: {amount}"
            )
        self.balance -= amount
        self.available_balance = self.balance - self.frozen_amount
        self.updated_at = datetime.now()

    def freeze(self, amount: Decimal) -> None:
        """
        冻结资金

        Args:
            amount: 冻结金额，必须大于零且不超过可用余额

        Raises:
            ValueError: 金额不合法或可用余额不足
        """
        if amount <= Decimal("0"):
            raise ValueError("冻结金额必须大于零")
        if self.status == AccountStatus.CLOSED:
            raise ValueError("已销户账户不能冻结资金")
        if amount > self.available_balance:
            raise ValueError(
                f"可用余额不足以冻结，当前可用余额: {self.available_balance}，"
                f"请求冻结: {amount}"
            )
        self.frozen_amount += amount
        self.available_balance = self.balance - self.frozen_amount
        if self.available_balance == Decimal("0") and self.frozen_amount > Decimal("0"):
            self.status = AccountStatus.FROZEN
        self.updated_at = datetime.now()

    def unfreeze(self, amount: Decimal) -> None:
        """
        解冻资金

        Args:
            amount: 解冻金额，必须大于零且不超过已冻结金额

        Raises:
            ValueError: 金额不合法或超过已冻结金额
        """
        if amount <= Decimal("0"):
            raise ValueError("解冻金额必须大于零")
        if amount > self.frozen_amount:
            raise ValueError(
                f"解冻金额超过已冻结金额，当前冻结: {self.frozen_amount}，"
                f"请求解冻: {amount}"
            )
        self.frozen_amount -= amount
        self.available_balance = self.balance - self.frozen_amount
        if self.status == AccountStatus.FROZEN and self.frozen_amount == Decimal("0"):
            self.status = AccountStatus.ACTIVE
        self.updated_at = datetime.now()

    def check_available_balance(self, amount: Decimal) -> bool:
        """
        检查可用余额是否充足

        Args:
            amount: 需要检查的金额

        Returns:
            True 表示可用余额充足，False 表示不足
        """
        return self.available_balance >= amount

    def close(self) -> None:
        """
        销户

        Raises:
            ValueError: 账户余额不为零或存在冻结
        """
        if self.balance != Decimal("0"):
            raise ValueError("账户余额不为零，无法销户")
        if self.frozen_amount != Decimal("0"):
            raise ValueError("账户存在冻结金额，无法销户")
        self.status = AccountStatus.CLOSED
        self.close_date = date.today()
        self.updated_at = datetime.now()

    def is_active(self) -> bool:
        """判断账户是否处于正常状态"""
        return self.status == AccountStatus.ACTIVE

    def is_fixed_matured(self) -> bool:
        """判断定期账户是否已到期"""
        if self.account_type != AccountType.FIXED:
            return False
        if self.maturity_date is None:
            return False
        return date.today() >= self.maturity_date

    def __repr__(self) -> str:
        return (
            f"Account(account_number={self.account_number!r}, "
            f"type={self.account_type.value}, "
            f"status={self.status.value}, "
            f"balance={self.balance}, "
            f"available={self.available_balance}, "
            f"frozen={self.frozen_amount})"
        )
