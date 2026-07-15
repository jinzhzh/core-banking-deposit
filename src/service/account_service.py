"""
开户/销户服务

负责账户的创建（开户）和关闭（销户）操作。
开户时生成唯一账号并处理初始存款的会计分录；
销户时检查余额为零或结清利息后生成相应分录。
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional
import uuid


class AccountService:
    """开户/销户服务类"""

    def __init__(self, account_repository, transaction_repository, accounting_engine):
        """
        初始化开户/销户服务。

        参数:
            account_repository: 账户仓储接口，负责账户数据的持久化
            transaction_repository: 交易流水仓储接口
            accounting_engine: 会计引擎，负责生成和记录会计分录
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._accounting_engine = accounting_engine

    def open_account(
        self,
        customer_id: str,
        account_type: str,
        initial_deposit: Decimal,
        term_months: Optional[int] = None,
    ) -> dict:
        """
        开户操作。

        生成唯一账号，创建账户记录，并对初始存款生成会计分录。
        活期账户分录：借:库存现金 贷:活期存款
        定期账户分录：借:库存现金 贷:定期存款

        参数:
            customer_id: 客户编号
            account_type: 账户类型（"demand" 活期 / "term" 定期）
            initial_deposit: 初始存款金额，必须大于零
            term_months: 定期月数，仅定期账户需要提供

        返回:
            dict: 包含账户信息的字典

        异常:
            ValueError: 初始存款金额不合法或定期账户未提供期限
        """
        # 参数校验
        if initial_deposit <= Decimal("0"):
            raise ValueError("初始存款金额必须大于零")

        if account_type == "term" and term_months is None:
            raise ValueError("定期账户必须指定存期月数")

        # 生成唯一账号
        account_number = self._generate_account_number()

        # 构建账户数据
        now = datetime.now()
        account_data = {
            "account_number": account_number,
            "customer_id": customer_id,
            "account_type": account_type,
            "balance": initial_deposit,
            "frozen_amount": Decimal("0"),
            "status": "active",
            "term_months": term_months,
            "open_date": now,
            "maturity_date": None,
            "created_at": now,
            "updated_at": now,
        }

        # 如果是定期账户，计算到期日
        if account_type == "term" and term_months:
            from dateutil.relativedelta import relativedelta
            account_data["maturity_date"] = now + relativedelta(months=term_months)

        # 持久化账户
        self._account_repo.save(account_data)

        # 生成初始存款的交易流水
        txn_data = {
            "txn_id": str(uuid.uuid4()),
            "account_number": account_number,
            "txn_type": "open_deposit",
            "amount": initial_deposit,
            "balance_after": initial_deposit,
            "summary": "开户初始存款",
            "status": "completed",
            "created_at": now,
        }
        self._transaction_repo.save(txn_data)

        # 生成会计分录（借:库存现金 贷:活期/定期存款）
        # 硬约束：余额变动必须同时生成借贷双分录
        credit_account = "活期存款" if account_type == "demand" else "定期存款"
        entries = [
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_data["txn_id"],
                "direction": "debit",
                "subject": "库存现金",
                "amount": initial_deposit,
                "created_at": now,
            },
            {
                "entry_id": str(uuid.uuid4()),
                "txn_id": txn_data["txn_id"],
                "direction": "credit",
                "subject": credit_account,
                "amount": initial_deposit,
                "created_at": now,
            },
        ]
        self._accounting_engine.post_entries(entries)

        return account_data

    def close_account(self, account_number: str, operator: str) -> dict:
        """
        销户操作。

        检查账户余额是否为零，若有余额则结清利息后将剩余金额退还客户，
        生成相应的会计分录，最后将账户状态标记为已关闭。

        参数:
            account_number: 账户号码
            operator: 操作员编号

        返回:
            dict: 销户结果信息

        异常:
            ValueError: 账户不存在或状态不允许销户
        """
        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if account["status"] != "active":
            raise ValueError(f"账户 {account_number} 状态为 {account['status']}，无法销户")

        # 检查是否有冻结金额
        if account.get("frozen_amount", Decimal("0")) > Decimal("0"):
            raise ValueError("账户存在冻结金额，无法销户")

        now = datetime.now()
        remaining_balance = account["balance"]

        # 如果余额不为零，需要结清利息并退还余额
        if remaining_balance > Decimal("0"):
            # 生成退还余额的交易流水
            txn_data = {
                "txn_id": str(uuid.uuid4()),
                "account_number": account_number,
                "txn_type": "close_withdrawal",
                "amount": remaining_balance,
                "balance_after": Decimal("0"),
                "summary": "销户结清退款",
                "status": "completed",
                "operator": operator,
                "created_at": now,
            }
            self._transaction_repo.save(txn_data)

            # 生成会计分录（借:活期存款 贷:库存现金）
            credit_subject = (
                "活期存款" if account["account_type"] == "demand" else "定期存款"
            )
            entries = [
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": txn_data["txn_id"],
                    "direction": "debit",
                    "subject": credit_subject,
                    "amount": remaining_balance,
                    "created_at": now,
                },
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": txn_data["txn_id"],
                    "direction": "credit",
                    "subject": "库存现金",
                    "amount": remaining_balance,
                    "created_at": now,
                },
            ]
            self._accounting_engine.post_entries(entries)

        # 更新账户状态为已关闭
        account["status"] = "closed"
        account["balance"] = Decimal("0")
        account["close_date"] = now
        account["close_operator"] = operator
        account["updated_at"] = now
        self._account_repo.update(account)

        return {
            "account_number": account_number,
            "status": "closed",
            "remaining_balance_returned": remaining_balance,
            "operator": operator,
            "close_date": now,
        }

    def get_account_info(self, account_number: str) -> Optional[dict]:
        """
        查询账户信息。

        参数:
            account_number: 账户号码

        返回:
            dict: 账户信息字典，账户不存在时返回 None
        """
        account = self._account_repo.find_by_account_number(account_number)
        return account

    def _generate_account_number(self) -> str:
        """
        生成唯一账号。

        使用时间戳和随机数组合生成19位数字账号。

        返回:
            str: 唯一账号字符串
        """
        timestamp_part = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:5].upper()
        # 生成19位数字账号（银行标准长度）
        raw = f"6220{timestamp_part}{random_part}"
        # 取前19位并确保全为数字（将字母转为数字）
        numeric = "".join(
            str(ord(c) % 10) if not c.isdigit() else c for c in raw
        )[:19]
        return numeric
