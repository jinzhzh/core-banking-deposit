"""
利息计算服务

负责存款利息的计算、计提和结转。
活期按日计息（日利率 = 年利率 / 360），定期按约定利率计息。
季度结息时将计提利息入账。
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional
import uuid


class InterestService:
    """利息计算服务类"""

    def __init__(
        self,
        account_repository,
        transaction_repository,
        accounting_engine,
        interest_repository,
        interest_rate_repository,
    ):
        """
        初始化利息计算服务。

        参数:
            account_repository: 账户仓储接口
            transaction_repository: 交易流水仓储接口
            accounting_engine: 会计引擎，负责生成和记录会计分录
            interest_repository: 利息记录仓储接口，存储计提和结转记录
            interest_rate_repository: 利率仓储接口，提供活期/定期利率查询
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._accounting_engine = accounting_engine
        self._interest_repo = interest_repository
        self._interest_rate_repo = interest_rate_repository

    def calculate_daily_interest(
        self, account_number: str, calc_date: date
    ) -> Decimal:
        """
        计算单日利息。

        根据账户类型和当日余额计算单日应计利息。
        活期：日利息 = 当日余额 × 年利率 / 360
        定期：日利息 = 本金 × 约定年利率 / 360

        参数:
            account_number: 账户号码
            calc_date: 计算日期

        返回:
            Decimal: 单日利息金额（保留小数位，结转时再四舍五入）

        异常:
            ValueError: 账户不存在
        """
        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if account["status"] != "active":
            return Decimal("0")

        balance = account["balance"]
        if balance <= Decimal("0"):
            return Decimal("0")

        # 根据账户类型获取利率
        account_type = account["account_type"]
        if account_type == "demand":
            # 活期按日计息
            annual_rate = self._interest_rate_repo.get_demand_rate()
        elif account_type == "term":
            # 定期按约定利率
            annual_rate = account.get(
                "interest_rate",
                self._interest_rate_repo.get_term_rate(account.get("term_months", 12)),
            )
        else:
            return Decimal("0")

        # 日利息 = 余额 × 年利率 / 360
        daily_interest = balance * annual_rate / Decimal("360")

        return daily_interest

    def accrue_interest(self, account_number: str, accrual_date: date) -> dict:
        """
        计提利息（不入账）。

        计算指定日期的应计利息并记录到利息计提表中，
        但不实际入账到账户余额。待季度结息时统一入账。

        参数:
            account_number: 账户号码
            accrual_date: 计提日期

        返回:
            dict: 计提记录信息

        异常:
            ValueError: 账户不存在
        """
        # 计算当日利息
        daily_interest = self.calculate_daily_interest(account_number, accrual_date)

        if daily_interest <= Decimal("0"):
            return {
                "account_number": account_number,
                "accrual_date": accrual_date,
                "interest_amount": Decimal("0"),
                "status": "skipped",
            }

        now = datetime.now()

        # 创建计提记录
        accrual_record = {
            "accrual_id": str(uuid.uuid4()),
            "account_number": account_number,
            "accrual_date": accrual_date,
            "interest_amount": daily_interest,
            "status": "accrued",  # 已计提，未结转
            "settled": False,
            "created_at": now,
        }
        self._interest_repo.save(accrual_record)

        return accrual_record

    def settle_interest(self, account_number: str) -> dict:
        """
        利息结转入账（季度结息）。

        将所有未结转的计提利息汇总后入账到账户余额，
        并生成相应的会计分录。

        会计分录：
            借: 利息支出
            贷: 活期存款（或定期存款）

        参数:
            account_number: 账户号码

        返回:
            dict: 结转结果信息（包含结转利息总额等）

        异常:
            ValueError: 账户不存在或无待结转利息
        """
        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if account["status"] != "active":
            raise ValueError(f"账户 {account_number} 状态异常，无法结息")

        # 查询所有未结转的计提记录
        unsettled_records = self._interest_repo.find_unsettled_by_account(account_number)
        if not unsettled_records:
            raise ValueError(f"账户 {account_number} 无待结转的计提利息")

        # 汇总利息金额
        total_interest = sum(
            record["interest_amount"] for record in unsettled_records
        )
        # 结转时四舍五入到分
        total_interest = total_interest.quantize(Decimal("0.01"))

        if total_interest <= Decimal("0"):
            return {
                "account_number": account_number,
                "total_interest": Decimal("0"),
                "status": "no_interest",
            }

        now = datetime.now()

        # 更新账户余额
        old_balance = account["balance"]
        new_balance = old_balance + total_interest
        account["balance"] = new_balance
        account["updated_at"] = now
        self._account_repo.update(account)

        # 标记计提记录为已结转
        for record in unsettled_records:
            record["settled"] = True
            record["status"] = "settled"
            record["settled_at"] = now
            self._interest_repo.update(record)

        # 生成交易流水
        txn_id = str(uuid.uuid4())
        txn_data = {
            "txn_id": txn_id,
            "account_number": account_number,
            "txn_type": "interest_settlement",
            "amount": total_interest,
            "balance_before": old_balance,
            "balance_after": new_balance,
            "summary": "季度利息结转",
            "status": "completed",
            "created_at": now,
        }
        self._transaction_repo.save(txn_data)

        # 生成会计分录（借:利息支出 贷:活期/定期存款）
        # 硬约束：余额变动必须同时生成借贷双分录
        credit_subject = (
            "活期存款" if account["account_type"] == "demand" else "定期存款"
        )
        entries = [
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "debit",
                "subject": "利息支出",
                "amount": total_interest,
                "created_at": now,
            },
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "credit",
                "subject": credit_subject,
                "amount": total_interest,
                "created_at": now,
            },
        ]
        self._accounting_engine.post_entries(entries)

        return {
            "account_number": account_number,
            "total_interest": total_interest,
            "records_settled": len(unsettled_records),
            "balance_before": old_balance,
            "balance_after": new_balance,
            "txn_id": txn_id,
            "settled_at": now,
        }
