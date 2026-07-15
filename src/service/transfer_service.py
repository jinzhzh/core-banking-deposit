"""
定活互转服务

负责活期转定期和定期转活期的操作。
活期转定期时创建定期子账户；定期转活期时计算利息（到期或提前支取）。
所有转换操作均生成双向会计分录。
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional
import uuid


class TransferService:
    """定活互转服务类"""

    def __init__(
        self,
        account_repository,
        transaction_repository,
        accounting_engine,
        interest_rate_repository,
    ):
        """
        初始化定活互转服务。

        参数:
            account_repository: 账户仓储接口，负责账户数据的持久化
            transaction_repository: 交易流水仓储接口
            accounting_engine: 会计引擎，负责生成和记录会计分录
            interest_rate_repository: 利率仓储接口，提供定期利率查询
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._accounting_engine = accounting_engine
        self._interest_rate_repo = interest_rate_repository

    def demand_to_term(
        self,
        account_number: str,
        amount: Decimal,
        term_months: int,
    ) -> dict:
        """
        活期转定期。

        从活期账户扣减指定金额，创建定期子账户，并生成双向会计分录。

        会计分录：
            借: 活期存款（活期负债减少）
            贷: 定期存款（定期负债增加）

        参数:
            account_number: 活期账户号码
            amount: 转存金额，必须为正数
            term_months: 定期月数

        返回:
            dict: 包含定期子账户信息的字典

        异常:
            ValueError: 金额不合法、余额不足或账户类型不匹配
        """
        # 参数校验
        if amount <= Decimal("0"):
            raise ValueError("转存金额必须大于零")

        if term_months <= 0:
            raise ValueError("定期月数必须大于零")

        # 查询活期账户
        demand_account = self._account_repo.find_by_account_number(account_number)
        if demand_account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if demand_account["account_type"] != "demand":
            raise ValueError(f"账户 {account_number} 不是活期账户，无法执行活期转定期")

        if demand_account["status"] != "active":
            raise ValueError(f"账户 {account_number} 状态异常，无法操作")

        # 检查可用余额
        frozen_amount = demand_account.get("frozen_amount", Decimal("0"))
        available_balance = demand_account["balance"] - frozen_amount
        if amount > available_balance:
            raise ValueError(
                f"可用余额不足。可用余额: {available_balance}，转存金额: {amount}"
            )

        now = datetime.now()

        # 扣减活期账户余额
        demand_account["balance"] -= amount
        demand_account["updated_at"] = now
        self._account_repo.update(demand_account)

        # 创建定期子账户
        from dateutil.relativedelta import relativedelta

        term_account_number = self._generate_term_account_number(account_number)
        maturity_date = now + relativedelta(months=term_months)

        # 查询对应期限的定期利率
        interest_rate = self._interest_rate_repo.get_term_rate(term_months)

        term_account_data = {
            "account_number": term_account_number,
            "parent_account_number": account_number,
            "customer_id": demand_account["customer_id"],
            "account_type": "term",
            "balance": amount,
            "frozen_amount": Decimal("0"),
            "status": "active",
            "term_months": term_months,
            "interest_rate": interest_rate,
            "open_date": now,
            "maturity_date": maturity_date,
            "created_at": now,
            "updated_at": now,
        }
        self._account_repo.save(term_account_data)

        # 生成交易流水
        txn_id = str(uuid.uuid4())
        txn_data = {
            "txn_id": txn_id,
            "account_number": account_number,
            "related_account_number": term_account_number,
            "txn_type": "demand_to_term",
            "amount": amount,
            "balance_after": demand_account["balance"],
            "summary": f"活期转定期 {term_months}个月",
            "status": "completed",
            "created_at": now,
        }
        self._transaction_repo.save(txn_data)

        # 生成双向会计分录（借:活期存款 贷:定期存款）
        entries = [
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "debit",
                "subject": "活期存款",
                "amount": amount,
                "created_at": now,
            },
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "credit",
                "subject": "定期存款",
                "amount": amount,
                "created_at": now,
            },
        ]
        self._accounting_engine.post_entries(entries)

        return term_account_data

    def term_to_demand(self, term_account_number: str) -> dict:
        """
        定期转活期（到期或提前支取）。

        将定期子账户的本金和利息转入对应的活期账户。
        到期支取按约定利率计息，提前支取按活期利率计息。
        生成双向会计分录。

        会计分录（本金部分）：
            借: 定期存款
            贷: 活期存款

        会计分录（利息部分）：
            借: 利息支出
            贷: 活期存款

        参数:
            term_account_number: 定期子账户号码

        返回:
            dict: 包含转出结果信息的字典（本金、利息、是否提前支取等）

        异常:
            ValueError: 账户不存在或状态异常
        """
        # 查询定期子账户
        term_account = self._account_repo.find_by_account_number(term_account_number)
        if term_account is None:
            raise ValueError(f"定期账户 {term_account_number} 不存在")

        if term_account["account_type"] != "term":
            raise ValueError(f"账户 {term_account_number} 不是定期账户")

        if term_account["status"] != "active":
            raise ValueError(f"定期账户 {term_account_number} 状态异常，无法操作")

        # 查询对应的活期主账户
        parent_account_number = term_account.get("parent_account_number")
        if parent_account_number is None:
            raise ValueError(f"定期账户 {term_account_number} 未关联活期主账户")

        demand_account = self._account_repo.find_by_account_number(parent_account_number)
        if demand_account is None:
            raise ValueError(f"活期主账户 {parent_account_number} 不存在")

        now = datetime.now()
        principal = term_account["balance"]

        # 判断是否到期
        maturity_date = term_account.get("maturity_date")
        is_early_withdrawal = maturity_date is not None and now < maturity_date

        # 计算利息
        interest = self._calculate_term_interest(term_account, now, is_early_withdrawal)
        total_amount = principal + interest

        # 更新活期账户余额（本金 + 利息）
        demand_account["balance"] += total_amount
        demand_account["updated_at"] = now
        self._account_repo.update(demand_account)

        # 关闭定期子账户
        term_account["balance"] = Decimal("0")
        term_account["status"] = "closed"
        term_account["close_date"] = now
        term_account["updated_at"] = now
        self._account_repo.update(term_account)

        # 生成交易流水
        txn_id = str(uuid.uuid4())
        txn_data = {
            "txn_id": txn_id,
            "account_number": parent_account_number,
            "related_account_number": term_account_number,
            "txn_type": "term_to_demand",
            "amount": total_amount,
            "principal": principal,
            "interest": interest,
            "is_early_withdrawal": is_early_withdrawal,
            "balance_after": demand_account["balance"],
            "summary": "定期转活期（提前支取）" if is_early_withdrawal else "定期转活期（到期）",
            "status": "completed",
            "created_at": now,
        }
        self._transaction_repo.save(txn_data)

        # 生成双向会计分录
        entries = [
            # 本金部分：借:定期存款 贷:活期存款
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "debit",
                "subject": "定期存款",
                "amount": principal,
                "created_at": now,
            },
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "credit",
                "subject": "活期存款",
                "amount": principal,
                "created_at": now,
            },
        ]

        # 利息部分：借:利息支出 贷:活期存款
        if interest > Decimal("0"):
            entries.extend([
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": txn_id,
                    "direction": "debit",
                    "subject": "利息支出",
                    "amount": interest,
                    "created_at": now,
                },
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": txn_id,
                    "direction": "credit",
                    "subject": "活期存款",
                    "amount": interest,
                    "created_at": now,
                },
            ])

        self._accounting_engine.post_entries(entries)

        return {
            "term_account_number": term_account_number,
            "demand_account_number": parent_account_number,
            "principal": principal,
            "interest": interest,
            "total_amount": total_amount,
            "is_early_withdrawal": is_early_withdrawal,
            "demand_balance_after": demand_account["balance"],
            "completed_at": now,
        }

    def _calculate_term_interest(
        self, term_account: dict, current_time: datetime, is_early: bool
    ) -> Decimal:
        """
        计算定期存款利息。

        到期支取按约定利率计息，提前支取按活期利率计息。

        参数:
            term_account: 定期账户数据
            current_time: 当前时间
            is_early: 是否提前支取

        返回:
            Decimal: 利息金额
        """
        principal = term_account["balance"]
        open_date = term_account["open_date"]

        # 计算实际存期天数
        if isinstance(open_date, datetime):
            days_held = (current_time - open_date).days
        else:
            days_held = (current_time.date() - open_date).days

        if days_held <= 0:
            return Decimal("0")

        if is_early:
            # 提前支取按活期利率计息
            rate = self._interest_rate_repo.get_demand_rate()
        else:
            # 到期支取按约定利率计息
            rate = term_account.get(
                "interest_rate",
                self._interest_rate_repo.get_term_rate(term_account["term_months"]),
            )

        # 利息 = 本金 × 年利率 × 天数 / 360
        interest = principal * rate * Decimal(str(days_held)) / Decimal("360")
        # 保留两位小数（银行标准：四舍五入）
        interest = interest.quantize(Decimal("0.01"))

        return interest

    def _generate_term_account_number(self, parent_account_number: str) -> str:
        """
        生成定期子账户号码。

        基于主账户号码生成关联的定期子账户号码。

        参数:
            parent_account_number: 活期主账户号码

        返回:
            str: 定期子账户号码
        """
        suffix = uuid.uuid4().hex[:4]
        return f"{parent_account_number}T{suffix}"
