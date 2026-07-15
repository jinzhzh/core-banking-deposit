"""
查询服务

提供账户余额、可用余额、对账单和利息明细等查询功能。
只读服务，不修改任何数据。
"""

from decimal import Decimal
from datetime import date
from typing import Optional, List


class QueryService:
    """查询服务类"""

    def __init__(
        self,
        account_repository,
        transaction_repository,
        interest_repository,
        freeze_repository,
    ):
        """
        初始化查询服务。

        参数:
            account_repository: 账户仓储接口
            transaction_repository: 交易流水仓储接口
            interest_repository: 利息记录仓储接口
            freeze_repository: 冻结记录仓储接口
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._interest_repo = interest_repository
        self._freeze_repo = freeze_repository

    def get_balance(self, account_number: str) -> Decimal:
        """
        查询账户余额。

        返回账户的账面余额（不扣除冻结金额）。

        参数:
            account_number: 账户号码

        返回:
            Decimal: 账户余额

        异常:
            ValueError: 账户不存在
        """
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        return account["balance"]

    def get_available_balance(self, account_number: str) -> Decimal:
        """
        查询可用余额。

        可用余额 = 账户余额 - 冻结金额。

        参数:
            account_number: 账户号码

        返回:
            Decimal: 可用余额

        异常:
            ValueError: 账户不存在
        """
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        balance = account["balance"]
        frozen_amount = account.get("frozen_amount", Decimal("0"))
        available = balance - frozen_amount

        return available

    def get_account_statement(
        self,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        查询账户对账单。

        返回指定日期范围内的交易明细、期初余额和期末余额。

        参数:
            account_number: 账户号码
            start_date: 起始日期（含）
            end_date: 结束日期（含）

        返回:
            dict: 对账单信息，包含：
                - account_number: 账户号码
                - start_date: 起始日期
                - end_date: 结束日期
                - opening_balance: 期初余额
                - closing_balance: 期末余额
                - transactions: 交易明细列表
                - total_debit: 期间借方合计
                - total_credit: 期间贷方合计

        异常:
            ValueError: 账户不存在或参数不合法
        """
        # 校验账户存在
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if start_date > end_date:
            raise ValueError("起始日期不能晚于结束日期")

        # 查询日期范围内的交易流水
        transactions = self._transaction_repo.find_by_account_and_date_range(
            account_number, start_date, end_date
        )

        # 计算期间借方和贷方合计
        total_debit = Decimal("0")  # 支出（取款、转出等）
        total_credit = Decimal("0")  # 收入（存款、转入、利息等）

        for txn in transactions:
            txn_type = txn.get("txn_type", "")
            amount = txn.get("amount", Decimal("0"))

            if txn_type in ("withdrawal", "close_withdrawal", "demand_to_term"):
                total_debit += amount
            elif txn_type in (
                "deposit",
                "open_deposit",
                "term_to_demand",
                "interest_settlement",
            ):
                total_credit += amount

        # 计算期初和期末余额
        # 期末余额为当前余额（如果 end_date 是今天）或从流水推算
        closing_balance = account["balance"]
        opening_balance = closing_balance - total_credit + total_debit

        return {
            "account_number": account_number,
            "start_date": start_date,
            "end_date": end_date,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "transactions": transactions,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "transaction_count": len(transactions),
        }

    def get_interest_detail(self, account_number: str) -> dict:
        """
        查询利息明细。

        返回账户的利息计提记录和结转记录。

        参数:
            account_number: 账户号码

        返回:
            dict: 利息明细信息，包含：
                - account_number: 账户号码
                - accrued_records: 计提记录列表
                - total_accrued: 累计计提利息
                - total_settled: 累计已结转利息
                - unsettled_interest: 未结转利息

        异常:
            ValueError: 账户不存在
        """
        # 校验账户存在
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        # 查询所有利息记录
        all_records = self._interest_repo.find_by_account(account_number)

        # 分类统计
        total_accrued = Decimal("0")
        total_settled = Decimal("0")
        unsettled_interest = Decimal("0")

        for record in all_records:
            amount = record.get("interest_amount", Decimal("0"))
            total_accrued += amount

            if record.get("settled", False):
                total_settled += amount
            else:
                unsettled_interest += amount

        return {
            "account_number": account_number,
            "account_type": account["account_type"],
            "accrued_records": all_records,
            "total_accrued": total_accrued,
            "total_settled": total_settled,
            "unsettled_interest": unsettled_interest,
            "record_count": len(all_records),
        }
