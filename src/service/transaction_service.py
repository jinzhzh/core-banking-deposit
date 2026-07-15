"""
交易流水服务

负责交易流水的创建和查询操作。
提供统一的交易流水管理接口。
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List
import uuid


class TransactionService:
    """交易流水服务类"""

    def __init__(self, transaction_repository):
        """
        初始化交易流水服务。

        参数:
            transaction_repository: 交易流水仓储接口
        """
        self._transaction_repo = transaction_repository

    def create_transaction(
        self,
        account_number: str,
        txn_type: str,
        amount: Decimal,
        balance_before: Optional[Decimal] = None,
        balance_after: Optional[Decimal] = None,
        summary: str = "",
        related_account_number: Optional[str] = None,
        operator: Optional[str] = None,
    ) -> dict:
        """
        创建交易流水。

        生成唯一交易流水ID并持久化交易记录。

        参数:
            account_number: 账户号码
            txn_type: 交易类型（deposit/withdrawal/transfer/reversal/interest_settlement等）
            amount: 交易金额，使用 Decimal 精确计算
            balance_before: 交易前余额（可选）
            balance_after: 交易后余额（可选）
            summary: 交易摘要
            related_account_number: 关联账户号码（转账类交易使用）
            operator: 操作员编号（可选）

        返回:
            dict: 交易流水记录

        异常:
            ValueError: 参数不合法
        """
        if not account_number:
            raise ValueError("账户号码不能为空")

        if not txn_type:
            raise ValueError("交易类型不能为空")

        if amount is None or amount < Decimal("0"):
            raise ValueError("交易金额不能为负数")

        now = datetime.now()
        txn_id = str(uuid.uuid4())

        txn_data = {
            "txn_id": txn_id,
            "account_number": account_number,
            "txn_type": txn_type,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "summary": summary,
            "related_account_number": related_account_number,
            "operator": operator,
            "status": "completed",
            "created_at": now,
        }

        self._transaction_repo.save(txn_data)

        return txn_data

    def get_transaction(self, txn_id: str) -> Optional[dict]:
        """
        查询单笔交易流水。

        参数:
            txn_id: 交易流水ID

        返回:
            dict: 交易流水记录，不存在时返回 None
        """
        if not txn_id:
            raise ValueError("交易流水ID不能为空")

        return self._transaction_repo.find_by_id(txn_id)

    def get_account_transactions(
        self,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> List[dict]:
        """
        查询账户在指定日期范围内的交易流水。

        参数:
            account_number: 账户号码
            start_date: 起始日期（含）
            end_date: 结束日期（含）

        返回:
            list: 交易流水记录列表，按时间正序排列

        异常:
            ValueError: 参数不合法
        """
        if not account_number:
            raise ValueError("账户号码不能为空")

        if start_date > end_date:
            raise ValueError("起始日期不能晚于结束日期")

        transactions = self._transaction_repo.find_by_account_and_date_range(
            account_number, start_date, end_date
        )

        return transactions
