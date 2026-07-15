"""
明细账管理模块

提供明细账查询功能，支持按客户账号和日期范围查询逐笔记录，
以及获取明细账余额和按科目汇总所有明细账余额。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List

from src.accounting.posting_engine import PostingEngine, SubLedgerRecord


@dataclass
class SubLedgerBalance:
    """
    明细账余额

    Attributes:
        account_code: 科目代码
        account_number: 辅助核算账号（客户账号）
        balance: 当前余额
        debit_total: 借方累计
        credit_total: 贷方累计
    """
    account_code: str
    account_number: str
    balance: Decimal = Decimal("0.00")
    debit_total: Decimal = Decimal("0.00")
    credit_total: Decimal = Decimal("0.00")


class SubLedgerManager:
    """
    明细账管理类

    基于过账引擎的明细账数据，提供逐笔查询、余额查询和科目汇总功能。
    """

    def __init__(self, posting_engine: PostingEngine) -> None:
        """
        初始化明细账管理器

        Args:
            posting_engine: 过账引擎实例（数据来源）
        """
        self._posting_engine = posting_engine

    def get_entries(
        self,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> List[SubLedgerRecord]:
        """
        获取指定客户账号在日期范围内的明细账记录

        Args:
            account_number: 客户账号
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            明细账记录列表，按会计日期排序
        """
        results: List[SubLedgerRecord] = []

        for (code, acc_num), records in self._posting_engine.sub_ledger.items():
            if acc_num == account_number:
                for record in records:
                    if start_date <= record.accounting_date <= end_date:
                        results.append(record)

        # 按会计日期排序
        results.sort(key=lambda r: r.accounting_date)
        return results

    def get_balance(self, account_number: str) -> List[SubLedgerBalance]:
        """
        获取指定客户账号的所有科目明细账余额

        Args:
            account_number: 客户账号

        Returns:
            该账号在各科目下的余额列表
        """
        balances: List[SubLedgerBalance] = []

        for (code, acc_num), records in self._posting_engine.sub_ledger.items():
            if acc_num == account_number and records:
                # 取最后一笔记录的余额作为当前余额
                last_record = records[-1]
                # 计算借方和贷方累计
                debit_total = sum(
                    (r.debit_amount for r in records), Decimal("0.00")
                )
                credit_total = sum(
                    (r.credit_amount for r in records), Decimal("0.00")
                )
                balances.append(
                    SubLedgerBalance(
                        account_code=code,
                        account_number=acc_num,
                        balance=last_record.balance,
                        debit_total=debit_total,
                        credit_total=credit_total,
                    )
                )

        return balances

    def get_all_balances_by_code(
        self, account_code: str
    ) -> List[SubLedgerBalance]:
        """
        获取某科目下所有明细账余额汇总

        Args:
            account_code: 科目代码

        Returns:
            该科目下所有辅助核算账号的余额列表
        """
        balances: List[SubLedgerBalance] = []

        for (code, acc_num), records in self._posting_engine.sub_ledger.items():
            if code == account_code and records:
                last_record = records[-1]
                debit_total = sum(
                    (r.debit_amount for r in records), Decimal("0.00")
                )
                credit_total = sum(
                    (r.credit_amount for r in records), Decimal("0.00")
                )
                balances.append(
                    SubLedgerBalance(
                        account_code=code,
                        account_number=acc_num,
                        balance=last_record.balance,
                        debit_total=debit_total,
                        credit_total=credit_total,
                    )
                )

        return balances

    def get_total_balance_by_code(self, account_code: str) -> Decimal:
        """
        获取某科目下所有明细账余额之和

        Args:
            account_code: 科目代码

        Returns:
            该科目下所有明细账余额的合计
        """
        balances = self.get_all_balances_by_code(account_code)
        return sum((b.balance for b in balances), Decimal("0.00"))
