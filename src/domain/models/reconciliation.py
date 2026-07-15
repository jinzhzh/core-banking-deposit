"""
对账模型

实现总账与明细账的对账逻辑，检测差异并生成对账报告。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List


@dataclass
class ReconciliationDifference:
    """
    对账差异记录

    记录总账与明细账之间的差异明细。
    """

    subject_code: str                   # 科目代码
    general_ledger_amount: Decimal      # 总账金额
    sub_ledger_amount: Decimal          # 明细账金额
    difference_amount: Decimal = Decimal("0.00")  # 差异金额

    def __post_init__(self) -> None:
        """初始化后计算差异"""
        self.difference_amount = self.general_ledger_amount - self.sub_ledger_amount

    def is_matched(self) -> bool:
        """判断是否一致（无差异）"""
        return self.difference_amount == Decimal("0")

    def __repr__(self) -> str:
        return (
            f"ReconciliationDifference(subject={self.subject_code!r}, "
            f"general={self.general_ledger_amount}, "
            f"sub={self.sub_ledger_amount}, "
            f"diff={self.difference_amount})"
        )


@dataclass
class ReconciliationResult:
    """
    对账结果实体

    汇总某一会计日期的对账结果，包括总账和明细账的余额汇总及差异列表。
    """

    reconciliation_date: date           # 对账日期
    general_ledger_total: Decimal = Decimal("0.00")  # 总账余额汇总
    sub_ledger_total: Decimal = Decimal("0.00")      # 明细账余额汇总
    differences: List[ReconciliationDifference] = field(default_factory=list)  # 差异列表
    is_balanced: bool = True            # 是否平衡

    def __post_init__(self) -> None:
        """初始化后判断是否平衡"""
        self._check_balance()

    def _check_balance(self) -> None:
        """检查总账与明细账是否平衡"""
        if self.differences:
            self.is_balanced = all(d.is_matched() for d in self.differences)
        else:
            self.is_balanced = (self.general_ledger_total == self.sub_ledger_total)

    def add_difference(self, difference: ReconciliationDifference) -> None:
        """
        添加差异记录

        Args:
            difference: 差异记录
        """
        self.differences.append(difference)
        self._check_balance()

    def total_difference(self) -> Decimal:
        """计算总差异金额"""
        return sum(
            (abs(d.difference_amount) for d in self.differences),
            Decimal("0.00")
        )

    def unmatched_subjects(self) -> List[str]:
        """获取不平衡的科目代码列表"""
        return [d.subject_code for d in self.differences if not d.is_matched()]

    def summary(self) -> str:
        """
        生成对账摘要

        Returns:
            对账结果的文字描述
        """
        status = "平衡" if self.is_balanced else "不平衡"
        lines = [
            f"对账日期: {self.reconciliation_date}",
            f"总账余额汇总: {self.general_ledger_total}",
            f"明细账余额汇总: {self.sub_ledger_total}",
            f"对账结果: {status}",
            f"差异笔数: {len([d for d in self.differences if not d.is_matched()])}",
        ]
        if not self.is_balanced:
            lines.append(f"总差异金额: {self.total_difference()}")
            lines.append(f"不平衡科目: {', '.join(self.unmatched_subjects())}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"ReconciliationResult(date={self.reconciliation_date}, "
            f"general_total={self.general_ledger_total}, "
            f"sub_total={self.sub_ledger_total}, "
            f"balanced={self.is_balanced}, "
            f"differences={len(self.differences)})"
        )
