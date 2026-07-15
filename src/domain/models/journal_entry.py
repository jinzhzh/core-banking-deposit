"""
会计分录模型

实现复式记账的会计分录，确保每笔分录借贷平衡。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class JournalEntryLine:
    """
    分录明细行

    表示一笔会计分录中的一条借方或贷方记录。
    每行要么有借方金额，要么有贷方金额，不能同时有。
    """

    subject_code: str                   # 科目代码
    subject_name: str                   # 科目名称
    debit_amount: Decimal = Decimal("0.00")   # 借方金额
    credit_amount: Decimal = Decimal("0.00")  # 贷方金额
    auxiliary_account: Optional[str] = None    # 辅助核算（关联账号）

    def __post_init__(self) -> None:
        """初始化后校验"""
        if self.debit_amount < Decimal("0"):
            raise ValueError("借方金额不能为负数")
        if self.credit_amount < Decimal("0"):
            raise ValueError("贷方金额不能为负数")
        if self.debit_amount > Decimal("0") and self.credit_amount > Decimal("0"):
            raise ValueError("同一分录行不能同时有借方和贷方金额")
        if self.debit_amount == Decimal("0") and self.credit_amount == Decimal("0"):
            raise ValueError("借方金额和贷方金额不能同时为零")

    def is_debit(self) -> bool:
        """判断是否为借方"""
        return self.debit_amount > Decimal("0")

    def is_credit(self) -> bool:
        """判断是否为贷方"""
        return self.credit_amount > Decimal("0")

    def __repr__(self) -> str:
        side = "借" if self.is_debit() else "贷"
        amount = self.debit_amount if self.is_debit() else self.credit_amount
        return (
            f"JournalEntryLine({side}: {self.subject_code} "
            f"{self.subject_name} {amount})"
        )


@dataclass
class JournalEntry:
    """
    会计分录实体

    一笔完整的会计分录包含多条明细行，必须满足借贷平衡约束：
    所有借方金额合计 = 所有贷方金额合计（复式记账）
    """

    entry_id: str                       # 分录编号
    transaction_id: str                 # 关联的交易流水号
    accounting_date: date               # 会计日期
    summary: str                        # 摘要
    lines: List[JournalEntryLine] = field(default_factory=list)  # 分录明细列表
    created_at: datetime = field(default_factory=datetime.now)   # 创建时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        if self.lines:
            self._validate_balance()

    def add_line(self, line: JournalEntryLine) -> None:
        """
        添加分录明细行

        Args:
            line: 分录明细行
        """
        self.lines.append(line)

    def _validate_balance(self) -> None:
        """
        校验借贷平衡

        Raises:
            ValueError: 借贷不平衡
        """
        if not self.lines:
            raise ValueError("分录明细不能为空")
        total_debit = self.total_debit()
        total_credit = self.total_credit()
        if total_debit != total_credit:
            raise ValueError(
                f"借贷不平衡：借方合计={total_debit}，贷方合计={total_credit}"
            )

    def validate(self) -> None:
        """
        手动触发校验（在所有明细行添加完毕后调用）

        Raises:
            ValueError: 校验失败
        """
        self._validate_balance()

    def total_debit(self) -> Decimal:
        """计算借方合计"""
        return sum(
            (line.debit_amount for line in self.lines),
            Decimal("0.00")
        )

    def total_credit(self) -> Decimal:
        """计算贷方合计"""
        return sum(
            (line.credit_amount for line in self.lines),
            Decimal("0.00")
        )

    def is_balanced(self) -> bool:
        """检查借贷是否平衡"""
        return self.total_debit() == self.total_credit()

    def __repr__(self) -> str:
        return (
            f"JournalEntry(id={self.entry_id!r}, "
            f"txn={self.transaction_id!r}, "
            f"date={self.accounting_date}, "
            f"lines={len(self.lines)}, "
            f"balanced={self.is_balanced()})"
        )
