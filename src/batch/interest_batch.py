"""
利息计提批处理

在日终批处理中批量计提所有活期账户的当日利息。
计提规则：日利息 = 账户余额 × 年利率 / 360
生成会计分录：借:利息支出 贷:应付利息
"""

from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List

from src.domain.models.account import Account, AccountStatus, AccountType
from src.domain.models.interest_accrual import InterestAccrual
from src.domain.models.journal_entry import JournalEntry, JournalEntryLine
from src.config.accounting_rules import SubjectCode, accounting_rules
from src.config.interest_rates import interest_rate_config
from src.repository.interfaces.account_repo import AccountRepository

logger = logging.getLogger(__name__)


class InterestBatchProcessor:
    """
    利息计提批处理器

    负责在日终批处理中遍历所有活期账户，计算当日应计利息，
    并生成对应的利息计提分录（借:利息支出 贷:应付利息）。
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        journal_repository: Any,
        ledger_repository: Any,
    ) -> None:
        """
        初始化利息计提批处理器

        Args:
            account_repository: 账户仓储接口
            journal_repository: 分录仓储接口
            ledger_repository: 账本仓储接口
        """
        self._account_repo = account_repository
        self._journal_repo = journal_repository
        self._ledger_repo = ledger_repository

    def process(self, accounting_date: date) -> Dict[str, Any]:
        """
        批量计提所有活期账户当日利息

        遍历所有状态为正常的活期账户，逐一计算日利息并生成计提分录。

        Args:
            accounting_date: 会计日期（计提日期）

        Returns:
            计提汇总信息字典，包含：
            - total_accounts: 处理的账户总数
            - success_count: 成功计提的账户数
            - skip_count: 跳过的账户数（余额为零等）
            - fail_count: 失败的账户数
            - total_interest: 计提利息总额
            - entries: 生成的分录列表
            - errors: 错误信息列表

        Raises:
            RuntimeError: 批量处理过程中发生不可恢复的错误
        """
        logger.info(f"开始利息计提批处理，会计日期: {accounting_date}")

        # 获取所有活期账户
        all_accounts = self._account_repo.find_all()
        demand_accounts = [
            acc for acc in all_accounts
            if acc.account_type == AccountType.DEMAND
            and acc.status == AccountStatus.ACTIVE
        ]

        summary: Dict[str, Any] = {
            "accounting_date": accounting_date,
            "total_accounts": len(demand_accounts),
            "success_count": 0,
            "skip_count": 0,
            "fail_count": 0,
            "total_interest": Decimal("0.00"),
            "entries": [],
            "errors": [],
        }

        for account in demand_accounts:
            try:
                result = self.process_account(account.account_number, accounting_date)
                if result is None:
                    # 跳过（余额为零或利率为零）
                    summary["skip_count"] += 1
                else:
                    summary["success_count"] += 1
                    summary["total_interest"] += result["accrued_interest"]
                    summary["entries"].append(result["entry_id"])
            except Exception as e:
                summary["fail_count"] += 1
                error_msg = f"账户 {account.account_number} 利息计提失败: {str(e)}"
                summary["errors"].append(error_msg)
                logger.error(error_msg)

        logger.info(
            f"利息计提批处理完成，会计日期: {accounting_date}，"
            f"成功: {summary['success_count']}，"
            f"跳过: {summary['skip_count']}，"
            f"失败: {summary['fail_count']}，"
            f"计提总额: {summary['total_interest']}"
        )

        return summary

    def process_account(self, account_number: str, accounting_date: date) -> Dict[str, Any] | None:
        """
        单账户利息计提

        计算指定账户在指定日期的日利息，并生成利息计提会计分录。

        Args:
            account_number: 账号
            accounting_date: 计提日期

        Returns:
            计提结果字典，包含accrued_interest和entry_id；
            如果余额为零或利率为零则返回None

        Raises:
            ValueError: 账户不存在
        """
        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        # 余额为零则跳过
        if account.balance <= Decimal("0"):
            logger.debug(f"账户 {account_number} 余额为零，跳过计提")
            return None

        # 获取活期年利率（百分比形式，如0.35表示0.35%）
        annual_rate_percent = interest_rate_config.get_demand_annual_rate()
        # 转换为小数形式（0.35% -> 0.0035）
        annual_rate = annual_rate_percent / Decimal("100")

        if annual_rate <= Decimal("0"):
            logger.debug(f"账户 {account_number} 利率为零，跳过计提")
            return None

        # 计算日利息：余额 × 年利率 / 360
        daily_rate = annual_rate / Decimal("360")
        accrued_interest = (account.balance * daily_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if accrued_interest <= Decimal("0"):
            return None

        # 创建利息计提记录
        accrual = InterestAccrual(
            account_number=account_number,
            accrual_date=accounting_date,
            principal=account.balance,
            interest_rate=annual_rate,
            days=1,
            accrued_interest=accrued_interest,
        )

        # 生成利息计提会计分录：借:利息支出 贷:应付利息
        entry_id = str(uuid.uuid4())
        transaction_id = f"ACCRUAL-{account_number}-{accounting_date.isoformat()}"

        entry = JournalEntry(
            entry_id=entry_id,
            transaction_id=transaction_id,
            accounting_date=accounting_date,
            summary=f"活期存款利息计提-{account_number}",
        )

        # 借方：利息支出
        debit_line = JournalEntryLine(
            subject_code=SubjectCode.INTEREST_EXPENSE_DEMAND.value,
            subject_name=accounting_rules.get_subject_name(SubjectCode.INTEREST_EXPENSE_DEMAND.value),
            debit_amount=accrued_interest,
            credit_amount=Decimal("0.00"),
            auxiliary_account=account_number,
        )
        entry.add_line(debit_line)

        # 贷方：应付利息
        credit_line = JournalEntryLine(
            subject_code=SubjectCode.INTEREST_PAYABLE_DEMAND.value,
            subject_name=accounting_rules.get_subject_name(SubjectCode.INTEREST_PAYABLE_DEMAND.value),
            debit_amount=Decimal("0.00"),
            credit_amount=accrued_interest,
            auxiliary_account=account_number,
        )
        entry.add_line(credit_line)

        # 校验借贷平衡
        entry.validate()

        # 持久化分录
        self._journal_repo.save(entry)

        logger.debug(
            f"账户 {account_number} 利息计提成功，"
            f"本金: {account.balance}，日利息: {accrued_interest}"
        )

        return {
            "account_number": account_number,
            "principal": account.balance,
            "annual_rate": annual_rate,
            "accrued_interest": accrued_interest,
            "entry_id": entry_id,
            "accrual": accrual,
        }
