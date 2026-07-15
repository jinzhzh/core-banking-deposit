"""
账本模型

包含总账和明细账（分户账）的记录实体。
总账按科目汇总，明细账按账户逐笔记录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class GeneralLedgerEntry:
    """
    总账分录

    按科目和会计日期汇总的账本记录，记录期初余额、本期发生额和期末余额。
    期末余额 = 期初余额 + 本期借方 - 本期贷方（资产类科目）
    或 期末余额 = 期初余额 - 本期借方 + 本期贷方（负债类科目）
    """

    subject_code: str                   # 科目代码
    accounting_date: date               # 会计日期
    opening_balance: Decimal = Decimal("0.00")  # 期初余额
    debit_amount: Decimal = Decimal("0.00")     # 本期借方发生额
    credit_amount: Decimal = Decimal("0.00")    # 本期贷方发生额
    closing_balance: Decimal = Decimal("0.00")  # 期末余额

    def __post_init__(self) -> None:
        """初始化后校验"""
        if self.debit_amount < Decimal("0"):
            raise ValueError("本期借方发生额不能为负数")
        if self.credit_amount < Decimal("0"):
            raise ValueError("本期贷方发生额不能为负数")

    def add_debit(self, amount: Decimal) -> None:
        """
        增加借方发生额

        Args:
            amount: 借方金额
        """
        if amount <= Decimal("0"):
            raise ValueError("借方金额必须大于零")
        self.debit_amount += amount
        self._recalculate_closing()

    def add_credit(self, amount: Decimal) -> None:
        """
        增加贷方发生额

        Args:
            amount: 贷方金额
        """
        if amount <= Decimal("0"):
            raise ValueError("贷方金额必须大于零")
        self.credit_amount += amount
        self._recalculate_closing()

    def _recalculate_closing(self) -> None:
        """
        重新计算期末余额

        默认按负债类科目计算（存款为银行负债）：
        期末余额 = 期初余额 - 本期借方 + 本期贷方
        """
        self.closing_balance = (
            self.opening_balance - self.debit_amount + self.credit_amount
        )

    def __repr__(self) -> str:
        return (
            f"GeneralLedgerEntry(subject={self.subject_code!r}, "
            f"date={self.accounting_date}, "
            f"opening={self.opening_balance}, "
            f"debit={self.debit_amount}, "
            f"credit={self.credit_amount}, "
            f"closing={self.closing_balance})"
        )


@dataclass
class SubLedgerEntry:
    """
    明细账（分户账）分录

    按账户逐笔记录的明细账本，关联具体的交易流水。
    """

    account_number: str                 # 账号
    subject_code: str                   # 科目代码
    accounting_date: date               # 会计日期
    transaction_id: str                 # 交易流水号
    debit_amount: Decimal = Decimal("0.00")   # 借方金额
    credit_amount: Decimal = Decimal("0.00")  # 贷方金额
    balance: Decimal = Decimal("0.00")        # 余额（该账户在该科目下的余额）

    def __post_init__(self) -> None:
        """初始化后校验"""
        if self.debit_amount < Decimal("0"):
            raise ValueError("借方金额不能为负数")
        if self.credit_amount < Decimal("0"):
            raise ValueError("贷方金额不能为负数")
        if not self.account_number:
            raise ValueError("账号不能为空")
        if not self.transaction_id:
            raise ValueError("交易流水号不能为空")

    def __repr__(self) -> str:
        return (
            f"SubLedgerEntry(account={self.account_number!r}, "
            f"subject={self.subject_code!r}, "
            f"date={self.accounting_date}, "
            f"txn={self.transaction_id!r}, "
            f"debit={self.debit_amount}, "
            f"credit={self.credit_amount}, "
            f"balance={self.balance})"
        )
