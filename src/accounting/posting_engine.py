"""
过账引擎模块

负责将已校验的会计分录过账到总账和明细账，
更新总账的借方/贷方累计和期末余额，更新明细账的逐笔记录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from src.domain.models.journal_entry import JournalEntry, JournalEntryLine


@dataclass
class GeneralLedgerRecord:
    """
    总账记录

    按科目代码+会计日期汇总的总账条目。

    Attributes:
        account_code: 科目代码
        accounting_date: 会计日期
        debit_total: 借方累计
        credit_total: 贷方累计
        balance: 期末余额（借方累计 - 贷方累计，负债类科目取反）
    """
    account_code: str
    accounting_date: date
    debit_total: Decimal = Decimal("0.00")
    credit_total: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")


@dataclass
class SubLedgerRecord:
    """
    明细账记录

    逐笔记录的明细账条目。

    Attributes:
        account_code: 科目代码
        account_number: 辅助核算账号（客户账号）
        entry_id: 分录编号
        transaction_id: 交易流水号
        accounting_date: 会计日期
        summary: 摘要
        debit_amount: 借方金额
        credit_amount: 贷方金额
        balance: 余额（逐笔更新）
    """
    account_code: str
    account_number: str
    entry_id: str
    transaction_id: str
    accounting_date: date
    summary: str
    debit_amount: Decimal = Decimal("0.00")
    credit_amount: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")


class PostingEngine:
    """
    过账引擎

    将会计分录过账到总账和明细账。
    - 过账时更新总账的借方/贷方累计和期末余额
    - 过账时更新明细账的逐笔记录
    """

    def __init__(self) -> None:
        """初始化过账引擎，创建总账和明细账存储"""
        # 总账存储：key = (科目代码, 会计日期)
        self._general_ledger: Dict[tuple, GeneralLedgerRecord] = {}
        # 明细账存储：key = (科目代码, 辅助核算账号)，value = 记录列表
        self._sub_ledger: Dict[tuple, List[SubLedgerRecord]] = {}
        # 已过账分录ID集合，防止重复过账
        self._posted_entries: set = set()

    @property
    def general_ledger(self) -> Dict[tuple, GeneralLedgerRecord]:
        """获取总账数据"""
        return self._general_ledger

    @property
    def sub_ledger(self) -> Dict[tuple, List[SubLedgerRecord]]:
        """获取明细账数据"""
        return self._sub_ledger

    def post(self, journal_entry: JournalEntry) -> None:
        """
        将单笔分录过账到总账和明细账

        Args:
            journal_entry: 已校验的会计分录

        Raises:
            ValueError: 分录借贷不平衡或已过账
        """
        # 校验分录借贷平衡
        if not journal_entry.is_balanced():
            raise ValueError(
                f"分录 {journal_entry.entry_id} 借贷不平衡，无法过账"
            )

        # 防止重复过账
        if journal_entry.entry_id in self._posted_entries:
            raise ValueError(
                f"分录 {journal_entry.entry_id} 已过账，不可重复过账"
            )

        # 逐行过账
        for line in journal_entry.lines:
            self._post_to_general_ledger(line, journal_entry.accounting_date)
            self._post_to_sub_ledger(line, journal_entry)

        # 记录已过账
        self._posted_entries.add(journal_entry.entry_id)

    def batch_post(self, entries: List[JournalEntry]) -> List[str]:
        """
        批量过账

        Args:
            entries: 会计分录列表

        Returns:
            成功过账的分录ID列表

        Raises:
            ValueError: 任一分录过账失败时抛出异常
        """
        posted_ids: List[str] = []
        for entry in entries:
            self.post(entry)
            posted_ids.append(entry.entry_id)
        return posted_ids

    def _post_to_general_ledger(
        self, line: JournalEntryLine, accounting_date: date
    ) -> None:
        """
        将分录行过账到总账

        更新对应科目+日期的借方累计、贷方累计和期末余额。

        Args:
            line: 分录明细行
            accounting_date: 会计日期
        """
        key = (line.subject_code, accounting_date)

        if key not in self._general_ledger:
            self._general_ledger[key] = GeneralLedgerRecord(
                account_code=line.subject_code,
                accounting_date=accounting_date,
            )

        record = self._general_ledger[key]
        record.debit_total += line.debit_amount
        record.credit_total += line.credit_amount
        # 余额 = 借方累计 - 贷方累计（资产类为正，负债类为负表示有余额）
        record.balance = record.debit_total - record.credit_total

    def _post_to_sub_ledger(
        self, line: JournalEntryLine, journal_entry: JournalEntry
    ) -> None:
        """
        将分录行过账到明细账

        逐笔记录并更新余额。

        Args:
            line: 分录明细行
            journal_entry: 所属会计分录
        """
        account_number = line.auxiliary_account or ""
        key = (line.subject_code, account_number)

        if key not in self._sub_ledger:
            self._sub_ledger[key] = []

        # 计算当前余额
        records = self._sub_ledger[key]
        prev_balance = records[-1].balance if records else Decimal("0.00")
        new_balance = prev_balance + line.debit_amount - line.credit_amount

        sub_record = SubLedgerRecord(
            account_code=line.subject_code,
            account_number=account_number,
            entry_id=journal_entry.entry_id,
            transaction_id=journal_entry.transaction_id,
            accounting_date=journal_entry.accounting_date,
            summary=journal_entry.summary,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            balance=new_balance,
        )
        records.append(sub_record)

    def is_posted(self, entry_id: str) -> bool:
        """
        判断分录是否已过账

        Args:
            entry_id: 分录编号

        Returns:
            是否已过账
        """
        return entry_id in self._posted_entries

    def get_posted_count(self) -> int:
        """获取已过账分录总数"""
        return len(self._posted_entries)
