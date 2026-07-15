"""
余额报告生成器

生成各科目的余额报告，包含期初余额、本期借方发生额、
本期贷方发生额、期末余额，以及试算平衡验证。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.repository.interfaces.ledger_repo import LedgerRepository

from src.config.accounting_rules import AccountingRules, accounting_rules


class BalanceReportGenerator:
    """
    余额报告生成器

    从总账仓储中获取各科目余额数据，生成包含试算平衡验证的余额报告。
    """

    def __init__(
        self,
        ledger_repository: "LedgerRepository",
        rules: Optional[AccountingRules] = None,
    ) -> None:
        """
        初始化余额报告生成器。

        参数:
            ledger_repository: 账本仓储接口
            rules: 会计规则配置，默认使用全局配置
        """
        self._ledger_repo = ledger_repository
        self._rules = rules or accounting_rules

    def generate(self, report_date: date) -> str:
        """
        生成余额报告。

        包含各科目的期初余额、本期借方发生额、本期贷方发生额、期末余额，
        以及试算平衡验证结果。

        参数:
            report_date: 报告日期

        返回:
            str: 格式化的中文文本余额报告
        """
        lines: List[str] = []

        # 报告标题
        lines.append("=" * 72)
        lines.append("                    科目余额表")
        lines.append("=" * 72)
        lines.append(f"报告日期: {report_date.strftime('%Y年%m月%d日')}")
        lines.append("")

        # 获取各科目数据
        subject_data = self._collect_subject_data(report_date)

        # 表头
        lines.append(
            f"{'科目代码':<8}{'科目名称':<14}{'期初余额':>12}"
            f"{'借方发生额':>12}{'贷方发生额':>12}{'期末余额':>12}"
        )
        lines.append("-" * 72)

        # 汇总数据
        total_opening = Decimal("0.00")
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        total_closing = Decimal("0.00")

        for item in subject_data:
            subject_code = item["subject_code"]
            subject_name = self._rules.get_subject_name(subject_code)
            opening = item["opening_balance"]
            debit = item["debit_amount"]
            credit = item["credit_amount"]
            closing = item["closing_balance"]

            lines.append(
                f"{subject_code:<8}{subject_name:<14}"
                f"{opening:>12,.2f}{debit:>12,.2f}"
                f"{credit:>12,.2f}{closing:>12,.2f}"
            )

            total_opening += opening
            total_debit += debit
            total_credit += credit
            total_closing += closing

        # 合计行
        lines.append("-" * 72)
        lines.append(
            f"{'合计':<8}{'':<14}"
            f"{total_opening:>12,.2f}{total_debit:>12,.2f}"
            f"{total_credit:>12,.2f}{total_closing:>12,.2f}"
        )
        lines.append("")

        # 试算平衡验证
        lines.append("-" * 72)
        lines.append("【试算平衡验证】")
        lines.append("-" * 72)

        debit_balance_total = Decimal("0.00")
        credit_balance_total = Decimal("0.00")

        for item in subject_data:
            subject_code = item["subject_code"]
            closing = item["closing_balance"]
            if self._rules.is_debit_balance(subject_code):
                debit_balance_total += closing
            else:
                credit_balance_total += closing

        lines.append(f"借方余额合计: {debit_balance_total:>16,.2f}")
        lines.append(f"贷方余额合计: {credit_balance_total:>16,.2f}")

        # 试算平衡：借方发生额合计 = 贷方发生额合计
        is_balanced = total_debit == total_credit
        lines.append(f"本期借方发生额合计: {total_debit:>12,.2f}")
        lines.append(f"本期贷方发生额合计: {total_credit:>12,.2f}")

        if is_balanced:
            lines.append("试算平衡结果: 平衡 ✓")
        else:
            diff = total_debit - total_credit
            lines.append(f"试算平衡结果: 不平衡 ✗ (差额: {diff:,.2f})")

        lines.append("")
        lines.append("-" * 72)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 72)

        return "\n".join(lines)

    def _collect_subject_data(self, report_date: date) -> List[Dict[str, Any]]:
        """
        收集各科目的余额数据。

        从总账仓储中获取指定日期的各科目分录，汇总计算期初余额、
        本期借方发生额、本期贷方发生额和期末余额。

        参数:
            report_date: 报告日期

        返回:
            list: 各科目余额数据列表
        """
        subject_data: List[Dict[str, Any]] = []

        # 获取当日总账分录
        entries = self._ledger_repo.find_general_by_date(report_date)

        # 按科目汇总
        subject_map: Dict[str, Dict[str, Decimal]] = {}
        for entry in entries:
            code = entry.get("account_code", entry.get("subject_code", ""))
            if not code:
                continue

            if code not in subject_map:
                subject_map[code] = {
                    "debit_amount": Decimal("0.00"),
                    "credit_amount": Decimal("0.00"),
                }

            amount = Decimal(str(entry.get("amount", 0)))
            direction = entry.get("direction", "debit")
            if direction == "debit":
                subject_map[code]["debit_amount"] += amount
            else:
                subject_map[code]["credit_amount"] += amount

        # 对所有已知科目生成数据（包括无发生额的科目）
        all_subjects = set(self._rules.subject_names.keys()) | set(subject_map.keys())

        for code in sorted(all_subjects):
            debit = subject_map.get(code, {}).get("debit_amount", Decimal("0.00"))
            credit = subject_map.get(code, {}).get("credit_amount", Decimal("0.00"))

            # 获取期初余额（截止到前一天的余额）
            opening = self._ledger_repo.get_balance(code, report_date)
            # 期初余额应该是不含当日发生额的，这里简化处理
            # 实际期初 = 当前余额 - 当日发生额影响
            if self._rules.is_debit_balance(code):
                opening_balance = opening - debit + credit
                closing_balance = opening
            else:
                opening_balance = opening + debit - credit
                closing_balance = opening

            # 仅包含有数据的科目
            if debit > 0 or credit > 0 or opening_balance != Decimal("0.00"):
                subject_data.append({
                    "subject_code": code,
                    "opening_balance": opening_balance,
                    "debit_amount": debit,
                    "credit_amount": credit,
                    "closing_balance": closing_balance,
                })

        return subject_data
