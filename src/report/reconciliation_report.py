"""
对账报告生成器

根据对账结果生成格式化的日终对账报告文本，包含总账余额汇总、
明细账余额汇总、差异明细和对账结论。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.models.reconciliation import ReconciliationResult, ReconciliationDifference


class ReconciliationReportGenerator:
    """
    对账报告生成器

    根据对账结果生成格式化的中文文本报告，用于日终对账环节。
    """

    def generate(self, reconciliation_result: ReconciliationResult, accounting_date: date) -> str:
        """
        生成对账报告文本。

        根据对账结果生成包含总账余额汇总、明细账余额汇总、差异明细
        和对账结论的完整报告。

        参数:
            reconciliation_result: 对账结果对象
            accounting_date: 会计日期

        返回:
            str: 格式化的中文文本报告字符串
        """
        lines: List[str] = []

        # 报告标题
        lines.append("=" * 60)
        lines.append("              日终对账报告")
        lines.append("=" * 60)
        lines.append("")

        # 对账日期
        lines.append(f"对账日期: {accounting_date.strftime('%Y年%m月%d日')}")
        lines.append("")

        # 总账余额汇总表
        lines.append("-" * 60)
        lines.append("【总账余额汇总表】")
        lines.append("-" * 60)
        lines.append(self._format_general_ledger_summary(reconciliation_result))
        lines.append("")

        # 明细账余额汇总表
        lines.append("-" * 60)
        lines.append("【明细账余额汇总表】")
        lines.append("-" * 60)
        lines.append(self._format_sub_ledger_summary(reconciliation_result))
        lines.append("")

        # 差异明细
        lines.append("-" * 60)
        lines.append("【差异明细】")
        lines.append("-" * 60)
        lines.append(self._format_differences(reconciliation_result))
        lines.append("")

        # 对账结论
        lines.append("-" * 60)
        lines.append("【对账结论】")
        lines.append("-" * 60)
        if reconciliation_result.is_balanced:
            lines.append("结论: 账平")
            lines.append("总账与明细账核对一致，无差异。")
        else:
            lines.append("结论: 不平")
            unmatched = reconciliation_result.unmatched_subjects()
            lines.append(f"存在 {len(unmatched)} 个科目不平衡。")
            lines.append(f"总差异金额: {reconciliation_result.total_difference()}")
            lines.append(f"不平衡科目: {', '.join(unmatched)}")
        lines.append("")

        # 生成时间
        lines.append("-" * 60)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _format_general_ledger_summary(self, result: ReconciliationResult) -> str:
        """
        格式化总账余额汇总信息。

        参数:
            result: 对账结果对象

        返回:
            str: 格式化的总账汇总文本
        """
        lines: List[str] = []
        lines.append(f"{'科目代码':<12}{'总账余额':>20}")
        lines.append("-" * 32)

        if result.differences:
            for diff in result.differences:
                lines.append(
                    f"{diff.subject_code:<12}{diff.general_ledger_amount:>20,.2f}"
                )
            lines.append("-" * 32)

        lines.append(f"{'合计':<12}{result.general_ledger_total:>20,.2f}")
        return "\n".join(lines)

    def _format_sub_ledger_summary(self, result: ReconciliationResult) -> str:
        """
        格式化明细账余额汇总信息。

        参数:
            result: 对账结果对象

        返回:
            str: 格式化的明细账汇总文本
        """
        lines: List[str] = []
        lines.append(f"{'科目代码':<12}{'明细账余额':>20}")
        lines.append("-" * 32)

        if result.differences:
            for diff in result.differences:
                lines.append(
                    f"{diff.subject_code:<12}{diff.sub_ledger_amount:>20,.2f}"
                )
            lines.append("-" * 32)

        lines.append(f"{'合计':<12}{result.sub_ledger_total:>20,.2f}")
        return "\n".join(lines)

    def _format_differences(self, result: ReconciliationResult) -> str:
        """
        格式化差异明细信息。

        参数:
            result: 对账结果对象

        返回:
            str: 格式化的差异明细文本
        """
        unmatched = [d for d in result.differences if not d.is_matched()]

        if not unmatched:
            return "无差异"

        lines: List[str] = []
        lines.append(
            f"{'科目代码':<12}{'总账金额':>16}{'明细账金额':>16}{'差异金额':>16}"
        )
        lines.append("-" * 60)

        for diff in unmatched:
            lines.append(
                f"{diff.subject_code:<12}"
                f"{diff.general_ledger_amount:>16,.2f}"
                f"{diff.sub_ledger_amount:>16,.2f}"
                f"{diff.difference_amount:>16,.2f}"
            )

        return "\n".join(lines)
