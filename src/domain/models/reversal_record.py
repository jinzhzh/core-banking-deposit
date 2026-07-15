"""
冲正记录模型

记录交易冲正操作。冲正不修改原交易流水，而是生成一笔反向交易和反向会计分录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ReversalRecord:
    """
    冲正记录实体

    记录一次冲正操作的完整信息。
    核心原则：冲正不修改原流水，只生成反向分录。

    冲正流程：
    1. 查找原交易流水
    2. 标记原流水为已冲正
    3. 生成反向交易流水
    4. 生成反向会计分录（借贷互换）
    5. 创建冲正记录
    """

    reversal_id: str                    # 冲正编号
    original_transaction_id: str        # 原交易流水号
    reversal_transaction_id: str        # 冲正流水号（反向交易的流水号）
    reversal_reason: str                # 冲正原因
    reversal_time: datetime = field(default_factory=datetime.now)  # 冲正时间
    operator: Optional[str] = None      # 操作员
    created_at: datetime = field(default_factory=datetime.now)     # 创建时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        self._validate()

    def _validate(self) -> None:
        """校验数据"""
        if not self.reversal_id:
            raise ValueError("冲正编号不能为空")
        if not self.original_transaction_id:
            raise ValueError("原交易流水号不能为空")
        if not self.reversal_transaction_id:
            raise ValueError("冲正流水号不能为空")
        if not self.reversal_reason:
            raise ValueError("冲正原因不能为空")
        if self.original_transaction_id == self.reversal_transaction_id:
            raise ValueError("冲正流水号不能与原交易流水号相同")

    def __repr__(self) -> str:
        return (
            f"ReversalRecord(id={self.reversal_id!r}, "
            f"original_txn={self.original_transaction_id!r}, "
            f"reversal_txn={self.reversal_transaction_id!r}, "
            f"reason={self.reversal_reason!r}, "
            f"time={self.reversal_time})"
        )
