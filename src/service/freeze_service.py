"""
冻结/解冻服务

负责账户资金的冻结和解冻操作。
冻结后可用余额 = 账户余额 - 冻结金额。
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional
import uuid


class FreezeService:
    """冻结/解冻服务类"""

    def __init__(self, account_repository, freeze_repository):
        """
        初始化冻结/解冻服务。

        参数:
            account_repository: 账户仓储接口，负责账户数据的持久化
            freeze_repository: 冻结记录仓储接口，负责冻结数据的持久化
        """
        self._account_repo = account_repository
        self._freeze_repo = freeze_repository

    def freeze(
        self,
        account_number: str,
        amount: Decimal,
        freeze_type: str,
        reason: str,
    ) -> dict:
        """
        冻结指定金额。

        在账户上冻结指定金额，冻结后可用余额 = 余额 - 冻结金额。
        不影响账户余额本身，仅限制可用金额。

        参数:
            account_number: 账户号码
            amount: 冻结金额，必须为正数
            freeze_type: 冻结类型（如 "judicial" 司法冻结、"pledge" 质押冻结等）
            reason: 冻结原因说明

        返回:
            dict: 冻结记录信息

        异常:
            ValueError: 金额不合法或可用余额不足以冻结
        """
        # 参数校验
        if amount <= Decimal("0"):
            raise ValueError("冻结金额必须大于零")

        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        if account["status"] != "active":
            raise ValueError(f"账户 {account_number} 状态为 {account['status']}，无法冻结")

        # 检查可用余额是否足够冻结
        current_frozen = account.get("frozen_amount", Decimal("0"))
        available_balance = account["balance"] - current_frozen

        if amount > available_balance:
            raise ValueError(
                f"可用余额不足以冻结。可用余额: {available_balance}，冻结金额: {amount}"
            )

        now = datetime.now()

        # 更新账户冻结金额
        account["frozen_amount"] = current_frozen + amount
        account["updated_at"] = now
        self._account_repo.update(account)

        # 创建冻结记录
        freeze_id = str(uuid.uuid4())
        freeze_record = {
            "freeze_id": freeze_id,
            "account_number": account_number,
            "amount": amount,
            "freeze_type": freeze_type,
            "reason": reason,
            "status": "active",
            "frozen_at": now,
            "unfrozen_at": None,
            "created_at": now,
        }
        self._freeze_repo.save(freeze_record)

        return freeze_record

    def unfreeze(self, freeze_id: str) -> dict:
        """
        解冻操作。

        根据冻结记录ID解除冻结，恢复账户可用余额。

        参数:
            freeze_id: 冻结记录ID

        返回:
            dict: 解冻结果信息

        异常:
            ValueError: 冻结记录不存在或已解冻
        """
        # 查询冻结记录
        freeze_record = self._freeze_repo.find_by_id(freeze_id)
        if freeze_record is None:
            raise ValueError(f"冻结记录 {freeze_id} 不存在")

        if freeze_record["status"] != "active":
            raise ValueError(f"冻结记录 {freeze_id} 状态为 {freeze_record['status']}，无法解冻")

        now = datetime.now()
        account_number = freeze_record["account_number"]
        amount = freeze_record["amount"]

        # 查询账户并更新冻结金额
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        current_frozen = account.get("frozen_amount", Decimal("0"))
        new_frozen = current_frozen - amount
        # 防止冻结金额为负（异常保护）
        if new_frozen < Decimal("0"):
            new_frozen = Decimal("0")

        account["frozen_amount"] = new_frozen
        account["updated_at"] = now
        self._account_repo.update(account)

        # 更新冻结记录状态
        freeze_record["status"] = "released"
        freeze_record["unfrozen_at"] = now
        self._freeze_repo.update(freeze_record)

        return {
            "freeze_id": freeze_id,
            "account_number": account_number,
            "amount": amount,
            "status": "released",
            "unfrozen_at": now,
            "available_balance_after": account["balance"] - new_frozen,
        }
