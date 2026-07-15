"""
存款服务

负责处理客户存款操作，包括更新账户余额、生成交易流水和会计分录。
硬约束：余额变动必须同时生成借贷双分录（借:库存现金 贷:活期存款）。
"""

from decimal import Decimal
from datetime import datetime
import uuid


class DepositService:
    """存款服务类"""

    def __init__(self, account_repository, transaction_repository, accounting_engine):
        """
        初始化存款服务。

        参数:
            account_repository: 账户仓储接口，负责账户数据的持久化
            transaction_repository: 交易流水仓储接口
            accounting_engine: 会计引擎，负责生成和记录会计分录
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._accounting_engine = accounting_engine

    def deposit(
        self,
        account_number: str,
        amount: Decimal,
        summary: str = "现金存入",
    ) -> dict:
        """
        存款操作。

        更新账户余额，生成交易流水，并生成会计分录。
        硬约束：余额变动必须同时生成借贷双分录。

        会计分录：
            借: 库存现金（资产增加）
            贷: 活期存款（负债增加）

        参数:
            account_number: 账户号码
            amount: 存款金额，必须为正数且使用 Decimal 精确计算
            summary: 摘要信息，默认为"现金存入"

        返回:
            dict: 包含交易流水信息的字典

        异常:
            ValueError: 金额不合法或账户状态异常
        """
        # 参数校验
        if not isinstance(amount, Decimal):
            raise TypeError("金额必须使用 Decimal 类型以确保精确计算")

        if amount <= Decimal("0"):
            raise ValueError("存款金额必须大于零")

        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if account["status"] != "active":
            raise ValueError(f"账户 {account_number} 状态为 {account['status']}，无法存款")

        # 更新余额
        now = datetime.now()
        old_balance = account["balance"]
        new_balance = old_balance + amount

        account["balance"] = new_balance
        account["updated_at"] = now
        self._account_repo.update(account)

        # 生成交易流水
        txn_id = str(uuid.uuid4())
        txn_data = {
            "txn_id": txn_id,
            "account_number": account_number,
            "txn_type": "deposit",
            "amount": amount,
            "balance_before": old_balance,
            "balance_after": new_balance,
            "summary": summary,
            "status": "completed",
            "created_at": now,
        }
        self._transaction_repo.save(txn_data)

        # 生成会计分录（借:库存现金 贷:活期存款）
        # 硬约束：余额变动必须同时生成借贷双分录
        entries = [
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "debit",
                "subject": "库存现金",
                "amount": amount,
                "created_at": now,
            },
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_id,
                "direction": "credit",
                "subject": "活期存款",
                "amount": amount,
                "created_at": now,
            },
        ]
        self._accounting_engine.post_entries(entries)

        return txn_data
