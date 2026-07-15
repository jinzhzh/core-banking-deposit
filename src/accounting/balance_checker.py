"""
余额校验/对账模块

提供试算平衡检查、总账与明细账核对功能，
确保会计数据的完整性和一致性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict, List

from src.accounting.general_ledger import GeneralLedgerManager
from src.accounting.sub_ledger import SubLedgerManager
from src.accounting.posting_engine import PostingEngine


class ReconciliationStatus(Enum):
    """对账状态枚举"""
    BALANCED = "平衡"
    UNBALANCED = "不平衡"


@dataclass
class ReconciliationItem:
    """
    对账明细条目

    Attributes:
        account_code: 科目代码
        general_ledger_balance: 总账余额
        sub_ledger_balance: 明细账余额合计
        difference: 差异金额
        is_matched: 是否一致
    """
    account_code: str
    general_ledger_balance: Decimal = Decimal("0.00")
    sub_ledger_balance: Decimal = Decimal("0.00")
    difference: Decimal = Decimal("0.00")
    is_matched: bool = True


@dataclass
class ReconciliationResult:
    """
    对账结果

    Attributes:
        as_of_date: 对账日期
        trial_balance_status: 试算平衡状态
        trial_balance_debit_total: 试算平衡借方合计
        trial_balance_credit_total: 试算平衡贷方合计
        general_vs_sub_items: 总账与明细账核对明细
        is_all_matched: 是否全部一致
        error_messages: 错误信息列表
    """
    as_of_date: date
    trial_balance_status: ReconciliationStatus = ReconciliationStatus.BALANCED
    trial_balance_debit_total: Decimal = Decimal("0.00")
    trial_balance_credit_total: Decimal = Decimal("0.00")
    general_vs_sub_items: List[ReconciliationItem] = field(default_factory=list)
    is_all_matched: bool = True
    error_messages: List[str] = field(default_factory=list)


class BalanceChecker:
    """
    余额校验/对账类

    提供试算平衡检查和总账与明细账核对功能。
    """

    def __init__(
        self,
        posting_engine: PostingEngine,
        general_ledger_manager: GeneralLedgerManager,
        sub_ledger_manager: SubLedgerManager,
    ) -> None:
        """
        初始化余额校验器

        Args:
            posting_engine: 过账引擎实例
            general_ledger_manager: 总账管理器实例
            sub_ledger_manager: 明细账管理器实例
        """
        self._posting_engine = posting_engine
        self._gl_manager = general_ledger_manager
        self._sl_manager = sub_ledger_manager

    def check_trial_balance(self, as_of_date: date) -> bool:
        """
        检查试算平衡

        验证所有科目借方合计是否等于贷方合计。

        Args:
            as_of_date: 截止日期

        Returns:
            是否平衡（True=平衡）
        """
        trial_balance = self._gl_manager.get_trial_balance(as_of_date)
        return trial_balance.is_balanced

    def check_general_vs_sub(self, as_of_date: date) -> List[ReconciliationItem]:
        """
        总账与明细账核对

        检查每个科目的总账余额是否等于该科目下所有明细账余额之和。

        Args:
            as_of_date: 截止日期

        Returns:
            核对明细条目列表
        """
        items: List[ReconciliationItem] = []

        # 获取所有涉及的科目代码
        account_codes: set = set()
        for (code, _) in self._posting_engine.general_ledger.keys():
            account_codes.add(code)

        for code in sorted(account_codes):
            # 总账余额
            gl_balance = self._gl_manager.get_balance(code, as_of_date)
            # 明细账余额合计
            sl_balance = self._sl_manager.get_total_balance_by_code(code)
            # 差异
            difference = gl_balance - sl_balance
            is_matched = difference == Decimal("0.00")

            items.append(
                ReconciliationItem(
                    account_code=code,
                    general_ledger_balance=gl_balance,
                    sub_ledger_balance=sl_balance,
                    difference=difference,
                    is_matched=is_matched,
                )
            )

        return items

    def generate_reconciliation_result(
        self, as_of_date: date
    ) -> ReconciliationResult:
        """
        生成完整对账结果

        包含试算平衡检查和总账与明细账核对。

        Args:
            as_of_date: 对账日期

        Returns:
            对账结果对象
        """
        error_messages: List[str] = []

        # 1. 试算平衡检查
        trial_balance = self._gl_manager.get_trial_balance(as_of_date)
        if trial_balance.is_balanced:
            tb_status = ReconciliationStatus.BALANCED
        else:
            tb_status = ReconciliationStatus.UNBALANCED
            error_messages.append(
                f"试算不平衡：借方合计={trial_balance.total_debit}，"
                f"贷方合计={trial_balance.total_credit}"
            )

        # 2. 总账与明细账核对
        recon_items = self.check_general_vs_sub(as_of_date)
        all_matched = all(item.is_matched for item in recon_items)

        if not all_matched:
            for item in recon_items:
                if not item.is_matched:
                    error_messages.append(
                        f"科目{item.account_code}总账与明细账不一致："
                        f"总账余额={item.general_ledger_balance}，"
                        f"明细账余额={item.sub_ledger_balance}，"
                        f"差异={item.difference}"
                    )

        # 综合判断
        is_all_ok = trial_balance.is_balanced and all_matched

        return ReconciliationResult(
            as_of_date=as_of_date,
            trial_balance_status=tb_status,
            trial_balance_debit_total=trial_balance.total_debit,
            trial_balance_credit_total=trial_balance.total_credit,
            general_vs_sub_items=recon_items,
            is_all_matched=is_all_ok,
            error_messages=error_messages,
        )
