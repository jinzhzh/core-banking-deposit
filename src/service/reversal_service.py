"""
冲正服务

负责对已完成的交易进行冲正操作。
硬约束：不修改原交易流水（只标记已冲正），生成反向会计分录和冲正记录。
"""

from decimal import Decimal
from datetime import datetime
import uuid


class ReversalService:
    """冲正服务类"""

    def __init__(
        self,
        account_repository,
        transaction_repository,
        accounting_engine,
        reversal_repository,
    ):
        """
        初始化冲正服务。

        参数:
            account_repository: 账户仓储接口
            transaction_repository: 交易流水仓储接口
            accounting_engine: 会计引擎，负责生成和记录会计分录
            reversal_repository: 冲正记录仓储接口
        """
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._accounting_engine = accounting_engine
        self._reversal_repo = reversal_repository

    def reverse_transaction(
        self,
        original_txn_id: str,
        reason: str,
        operator: str,
    ) -> dict:
        """
        冲正操作。

        对指定的原始交易进行冲正。
        硬约束：
        1. 不修改原交易流水，仅将其标记为"已冲正"状态
        2. 生成反向会计分录（原借方变贷方，原贷方变借方）
        3. 生成冲正记录

        参数:
            original_txn_id: 原始交易流水ID
            reason: 冲正原因
            operator: 操作员编号

        返回:
            dict: 冲正结果信息

        异常:
            ValueError: 原始交易不存在或已被冲正
        """
        # 查询原始交易
        original_txn = self._transaction_repo.find_by_id(original_txn_id)
        if original_txn is None:
            raise ValueError(f"原始交易 {original_txn_id} 不存在")

        if original_txn.get("status") == "reversed":
            raise ValueError(f"原始交易 {original_txn_id} 已被冲正，不可重复冲正")

        if original_txn.get("status") != "completed":
            raise ValueError(
                f"原始交易 {original_txn_id} 状态为 {original_txn.get('status')}，"
                f"仅已完成的交易可以冲正"
            )

        now = datetime.now()
        account_number = original_txn["account_number"]
        amount = original_txn["amount"]
        original_txn_type = original_txn["txn_type"]

        # 查询账户
        account = self._account_repo.find_by_account_number(account_number)
        if account is None:
            raise ValueError(f"账户 {account_number} 不存在")

        # 根据原始交易类型反向调整余额
        if original_txn_type in ("deposit", "open_deposit"):
            # 原存款冲正：余额减少
            if account["balance"] < amount:
                raise ValueError("账户余额不足，无法完成冲正")
            account["balance"] -= amount
        elif original_txn_type in ("withdrawal", "close_withdrawal"):
            # 原取款冲正：余额增加
            account["balance"] += amount
        else:
            # 其他类型根据 balance_before 和 balance_after 推断方向
            balance_before = original_txn.get("balance_before", Decimal("0"))
            balance_after = original_txn.get("balance_after", Decimal("0"))
            diff = balance_after - balance_before
            account["balance"] -= diff

        account["updated_at"] = now
        self._account_repo.update(account)

        # 硬约束：不修改原交易流水，仅标记状态为已冲正
        original_txn["status"] = "reversed"
        original_txn["reversed_at"] = now
        original_txn["reversal_reason"] = reason
        self._transaction_repo.update(original_txn)

        # 生成冲正交易流水
        reversal_txn_id = str(uuid.uuid4())
        reversal_txn_data = {
            "txn_id": reversal_txn_id,
            "account_number": account_number,
            "txn_type": "reversal",
            "original_txn_id": original_txn_id,
            "amount": amount,
            "balance_after": account["balance"],
            "summary": f"冲正交易 {original_txn_id}：{reason}",
            "status": "completed",
            "operator": operator,
            "created_at": now,
        }
        self._transaction_repo.save(reversal_txn_data)

        # 查询原始会计分录并生成反向分录
        original_entries = self._accounting_engine.get_entries_by_txn_id(original_txn_id)
        reversal_entries = []
        for entry in original_entries:
            # 反向：原借方变贷方，原贷方变借方
            reversed_direction = (
                "credit" if entry["direction"] == "debit" else "debit"
            )
            reversal_entries.append({
                "entry_id": str(uuid.uuid4()),
                "txn_id": reversal_txn_id,
                "original_entry_id": entry["entry_id"],
                "direction": reversed_direction,
                "subject": entry["subject"],
                "amount": entry["amount"],
                "is_reversal": True,
                "created_at": now,
            })

        # 如果没有查到原始分录，根据交易类型生成标准反向分录
        if not reversal_entries:
            reversal_entries = self._generate_default_reversal_entries(
                reversal_txn_id, original_txn_type, amount, now
            )

        self._accounting_engine.post_entries(reversal_entries)

        # 生成冲正记录
        reversal_record = {
            "reversal_id": str(uuid.uuid4()),
            "original_txn_id": original_txn_id,
            "reversal_txn_id": reversal_txn_id,
            "account_number": account_number,
            "amount": amount,
            "reason": reason,
            "operator": operator,
            "status": "completed",
            "created_at": now,
        }
        self._reversal_repo.save(reversal_record)

        return {
            "reversal_id": reversal_record["reversal_id"],
            "original_txn_id": original_txn_id,
            "reversal_txn_id": reversal_txn_id,
            "account_number": account_number,
            "amount": amount,
            "reason": reason,
            "operator": operator,
            "balance_after": account["balance"],
            "completed_at": now,
        }

    def _generate_default_reversal_entries(
        self,
        reversal_txn_id: str,
        original_txn_type: str,
        amount: Decimal,
        now: datetime,
    ) -> list:
        """
        根据原始交易类型生成默认的反向会计分录。

        当无法查询到原始分录时，根据交易类型推断标准分录并反向。

        参数:
            reversal_txn_id: 冲正交易流水ID
            original_txn_type: 原始交易类型
            amount: 金额
            now: 当前时间

        返回:
            list: 反向会计分录列表
        """
        entries = []

        if original_txn_type in ("deposit", "open_deposit"):
            # 原分录：借:库存现金 贷:活期存款 → 反向：借:活期存款 贷:库存现金
            entries = [
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": reversal_txn_id,
                    "direction": "debit",
                    "subject": "活期存款",
                    "amount": amount,
                    "is_reversal": True,
                    "created_at": now,
                },
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": reversal_txn_id,
                    "direction": "credit",
                    "subject": "库存现金",
                    "amount": amount,
                    "is_reversal": True,
                    "created_at": now,
                },
            ]
        elif original_txn_type in ("withdrawal", "close_withdrawal"):
            # 原分录：借:活期存款 贷:库存现金 → 反向：借:库存现金 贷:活期存款
            entries = [
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": reversal_txn_id,
                    "direction": "debit",
                    "subject": "库存现金",
                    "amount": amount,
                    "is_reversal": True,
                    "created_at": now,
                },
                {
                    "entry_id": str(uuid.uuid4()),
                    "txn_id": reversal_txn_id,
                    "direction": "credit",
                    "subject": "活期存款",
                    "amount": amount,
                    "is_reversal": True,
                    "created_at": now,
                },
            ]

        return entries
