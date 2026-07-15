"""
分录引擎模块

负责创建各类业务场景的会计分录，确保每笔分录借贷平衡。
支持存款、取款、利息计提、利息结转、活转定、定转活、冲正、开户、销户等业务。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional
import uuid

from src.domain.models.journal_entry import JournalEntry, JournalEntryLine
from src.accounting.chart_of_accounts import (
    CASH,
    DEMAND_DEPOSIT,
    TERM_DEPOSIT,
    INTEREST_PAYABLE,
    INTEREST_EXPENSE,
)


class JournalEngine:
    """
    分录引擎

    负责根据业务场景创建标准会计分录。
    硬约束：每笔分录必须借方合计=贷方合计，否则抛出异常。
    """

    def __init__(self, accounting_date: Optional[date] = None) -> None:
        """
        初始化分录引擎

        Args:
            accounting_date: 会计日期，默认为当天
        """
        self._accounting_date = accounting_date or date.today()

    @property
    def accounting_date(self) -> date:
        """获取当前会计日期"""
        return self._accounting_date

    @accounting_date.setter
    def accounting_date(self, value: date) -> None:
        """设置会计日期"""
        self._accounting_date = value

    def _generate_entry_id(self) -> str:
        """生成唯一分录编号"""
        return f"JE-{uuid.uuid4().hex[:12].upper()}"

    def _validate_amount(self, amount: Decimal) -> None:
        """
        校验金额有效性

        Args:
            amount: 金额

        Raises:
            ValueError: 金额无效
        """
        if not isinstance(amount, Decimal):
            raise TypeError(f"金额必须为Decimal类型，当前类型: {type(amount)}")
        if amount <= Decimal("0"):
            raise ValueError(f"金额必须大于零，当前值: {amount}")

    def _build_entry(
        self, summary: str, txn_id: str, lines: list
    ) -> JournalEntry:
        """
        构建分录并校验借贷平衡

        Args:
            summary: 摘要
            txn_id: 交易流水号
            lines: 分录明细行列表

        Returns:
            校验通过的会计分录

        Raises:
            ValueError: 借贷不平衡
        """
        entry = JournalEntry(
            entry_id=self._generate_entry_id(),
            transaction_id=txn_id,
            accounting_date=self._accounting_date,
            summary=summary,
            lines=lines,
        )
        # JournalEntry的__post_init__已做借贷平衡校验
        return entry

    def create_deposit_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建存款分录

        借：库存现金
        贷：活期存款

        Args:
            account_number: 客户账号
            amount: 存款金额
            txn_id: 交易流水号

        Returns:
            存款会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=CASH.code,
                subject_name=CASH.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(f"存款-账号{account_number}", txn_id, lines)

    def create_withdrawal_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建取款分录

        借：活期存款
        贷：库存现金

        Args:
            account_number: 客户账号
            amount: 取款金额
            txn_id: 交易流水号

        Returns:
            取款会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=CASH.code,
                subject_name=CASH.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(f"取款-账号{account_number}", txn_id, lines)

    def create_interest_accrual_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建利息计提分录

        借：利息支出
        贷：应付利息

        Args:
            account_number: 客户账号
            amount: 计提利息金额
            txn_id: 交易流水号

        Returns:
            利息计提会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=INTEREST_EXPENSE.code,
                subject_name=INTEREST_EXPENSE.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=INTEREST_PAYABLE.code,
                subject_name=INTEREST_PAYABLE.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"利息计提-账号{account_number}", txn_id, lines
        )

    def create_interest_settle_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建利息结转分录

        借：应付利息
        贷：活期存款

        Args:
            account_number: 客户账号
            amount: 结转利息金额
            txn_id: 交易流水号

        Returns:
            利息结转会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=INTEREST_PAYABLE.code,
                subject_name=INTEREST_PAYABLE.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"利息结转-账号{account_number}", txn_id, lines
        )

    def create_term_deposit_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建活转定分录

        借：活期存款
        贷：定期存款

        Args:
            account_number: 客户账号
            amount: 转存金额
            txn_id: 交易流水号

        Returns:
            活转定会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=TERM_DEPOSIT.code,
                subject_name=TERM_DEPOSIT.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"活转定-账号{account_number}", txn_id, lines
        )

    def create_term_withdraw_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建定转活分录

        借：定期存款
        贷：活期存款

        Args:
            account_number: 客户账号
            amount: 转出金额
            txn_id: 交易流水号

        Returns:
            定转活会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=TERM_DEPOSIT.code,
                subject_name=TERM_DEPOSIT.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"定转活-账号{account_number}", txn_id, lines
        )

    def create_reversal_entry(
        self, original_entry: JournalEntry, txn_id: str
    ) -> JournalEntry:
        """
        创建冲正分录（反向分录）

        将原始分录的借贷方向互换，生成冲正分录。

        Args:
            original_entry: 原始会计分录
            txn_id: 冲正交易流水号

        Returns:
            冲正会计分录
        """
        reversal_lines = []
        for line in original_entry.lines:
            reversal_lines.append(
                JournalEntryLine(
                    subject_code=line.subject_code,
                    subject_name=line.subject_name,
                    debit_amount=line.credit_amount,
                    credit_amount=line.debit_amount,
                    auxiliary_account=line.auxiliary_account,
                )
            )
        return self._build_entry(
            f"冲正-原分录{original_entry.entry_id}", txn_id, reversal_lines
        )

    def create_account_open_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建开户存入分录

        借：库存现金
        贷：活期存款

        Args:
            account_number: 新开客户账号
            amount: 开户存入金额
            txn_id: 交易流水号

        Returns:
            开户存入会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=CASH.code,
                subject_name=CASH.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"开户存入-账号{account_number}", txn_id, lines
        )

    def create_account_close_entry(
        self, account_number: str, amount: Decimal, txn_id: str
    ) -> JournalEntry:
        """
        创建销户支出分录

        借：活期存款
        贷：库存现金

        Args:
            account_number: 销户客户账号
            amount: 销户支出金额
            txn_id: 交易流水号

        Returns:
            销户支出会计分录
        """
        self._validate_amount(amount)
        lines = [
            JournalEntryLine(
                subject_code=DEMAND_DEPOSIT.code,
                subject_name=DEMAND_DEPOSIT.name,
                debit_amount=amount,
                credit_amount=Decimal("0.00"),
                auxiliary_account=account_number,
            ),
            JournalEntryLine(
                subject_code=CASH.code,
                subject_name=CASH.name,
                debit_amount=Decimal("0.00"),
                credit_amount=amount,
                auxiliary_account=account_number,
            ),
        ]
        return self._build_entry(
            f"销户支出-账号{account_number}", txn_id, lines
        )
