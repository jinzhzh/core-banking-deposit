"""
总账管理模块

提供总账余额查询、期间汇总和试算平衡表功能。
总账按科目+日期汇总，支持按日期范围查询。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from src.accounting.posting_engine import PostingEngine, GeneralLedgerRecord


@dataclass
class PeriodSummary:
    """
    期间汇总结果

    Attributes:
        account_code: 科目代码
        start_date: 起始日期
        end_date: 结束日期
        opening_balance: 期初余额
        debit_total: 期间借方合计
        credit_total: 期间贷方合计
        closing_balance: 期末余额
    """
    account_code: str
    start_date: date
    end_date: date
    opening_balance: Decimal = Decimal("0.00")
    debit_total: Decimal = Decimal("0.00")
    credit_total: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")


@dataclass
class TrialBalanceItem:
    """
    试算平衡表条目

    Attributes:
        account_code: 科目代码
        debit_total: 借方合计
        credit_total: 贷方合计
        balance: 余额（借方合计 - 贷方合计）
    """
    account_code: str
    debit_total: Decimal = Decimal("0.00")
    credit_total: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")


@dataclass
class TrialBalance:
    """
    试算平衡表

    Attributes:
        as_of_date: 截止日期
        items: 各科目的试算平衡条目
        total_debit: 所有科目借方合计
        total_credit: 所有科目贷方合计
        is_balanced: 是否平衡
    """
    as_of_date: date
    items: List[TrialBalanceItem]
    total_debit: Decimal = Decimal("0.00")
    total_credit: Decimal = Decimal("0.00")
    is_balanced: bool = True


class GeneralLedgerManager:
    """
    总账管理类

    基于过账引擎的总账数据，提供余额查询、期间汇总和试算平衡表功能。
    """

    def __init__(self, posting_engine: PostingEngine) -> None:
        """
        初始化总账管理器

        Args:
            posting_engine: 过账引擎实例（数据来源）
        """
        self._posting_engine = posting_engine

    def get_balance(self, account_code: str, as_of_date: date) -> Decimal:
        """
        获取科目在指定日期的累计余额

        汇总该科目在指定日期及之前所有日期的借方和贷方，计算余额。

        Args:
            account_code: 科目代码
            as_of_date: 截止日期

        Returns:
            科目余额（借方累计 - 贷方累计）
        """
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for (code, record_date), record in self._posting_engine.general_ledger.items():
            if code == account_code and record_date <= as_of_date:
                total_debit += record.debit_total
                total_credit += record.credit_total

        return total_debit - total_credit

    def get_period_summary(
        self, account_code: str, start_date: date, end_date: date
    ) -> PeriodSummary:
        """
        获取科目在指定期间的汇总信息

        Args:
            account_code: 科目代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            期间汇总结果
        """
        # 计算期初余额（start_date之前的累计）
        opening_balance = Decimal("0.00")
        for (code, record_date), record in self._posting_engine.general_ledger.items():
            if code == account_code and record_date < start_date:
                opening_balance += record.debit_total - record.credit_total

        # 计算期间发生额
        period_debit = Decimal("0.00")
        period_credit = Decimal("0.00")
        for (code, record_date), record in self._posting_engine.general_ledger.items():
            if code == account_code and start_date <= record_date <= end_date:
                period_debit += record.debit_total
                period_credit += record.credit_total

        # 期末余额 = 期初余额 + 期间借方 - 期间贷方
        closing_balance = opening_balance + period_debit - period_credit

        return PeriodSummary(
            account_code=account_code,
            start_date=start_date,
            end_date=end_date,
            opening_balance=opening_balance,
            debit_total=period_debit,
            credit_total=period_credit,
            closing_balance=closing_balance,
        )

    def get_trial_balance(self, as_of_date: date) -> TrialBalance:
        """
        生成试算平衡表

        汇总所有科目截止指定日期的借方合计和贷方合计，
        检查所有科目借方合计之和是否等于贷方合计之和。

        Args:
            as_of_date: 截止日期

        Returns:
            试算平衡表
        """
        # 按科目汇总
        account_totals: Dict[str, Dict[str, Decimal]] = {}

        for (code, record_date), record in self._posting_engine.general_ledger.items():
            if record_date <= as_of_date:
                if code not in account_totals:
                    account_totals[code] = {
                        "debit": Decimal("0.00"),
                        "credit": Decimal("0.00"),
                    }
                account_totals[code]["debit"] += record.debit_total
                account_totals[code]["credit"] += record.credit_total

        # 构建试算平衡表条目
        items: List[TrialBalanceItem] = []
        grand_debit = Decimal("0.00")
        grand_credit = Decimal("0.00")

        for code, totals in sorted(account_totals.items()):
            debit = totals["debit"]
            credit = totals["credit"]
            items.append(
                TrialBalanceItem(
                    account_code=code,
                    debit_total=debit,
                    credit_total=credit,
                    balance=debit - credit,
                )
            )
            grand_debit += debit
            grand_credit += credit

        is_balanced = grand_debit == grand_credit

        return TrialBalance(
            as_of_date=as_of_date,
            items=items,
            total_debit=grand_debit,
            total_credit=grand_credit,
            is_balanced=is_balanced,
        )
