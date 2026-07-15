"""
利息报告生成器

根据利息计提数据生成格式化的利息计提报告，
包含各账户计提明细和合计金额。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List


class InterestReportGenerator:
    """
    利息报告生成器

    根据利息计提记录生成格式化的利息计提报告，
    展示各账户的计提明细和汇总信息。
    """

    def generate(self, accruals: List[Dict[str, Any]], report_date: date) -> str:
        """
        生成利息计提报告。

        包含各账户的计提明细（账号、本金、利率、天数、计提利息）
        以及合计金额。

        参数:
            accruals: 利息计提记录列表，每条记录包含：
                - account_number: 账号
                - principal: 本金
                - interest_rate: 年化利率
                - days: 计息天数
                - accrued_interest / interest_amount: 计提利息金额
            report_date: 报告日期

        返回:
            str: 格式化的中文文本利息计提报告
        """
        lines: List[str] = []

        # 报告标题
        lines.append("=" * 72)
        lines.append("                  利息计提报告")
        lines.append("=" * 72)
        lines.append("")

        # 基本信息
        lines.append(f"计提日期: {report_date.strftime('%Y年%m月%d日')}")
        lines.append(f"计提账户数: {len(accruals)}")
        lines.append("")

        # 明细表头
        lines.append("-" * 72)
        lines.append(
            f"{'序号':<5}{'账号':<22}{'本金':>12}"
            f"{'年利率(%)':>10}{'天数':>5}{'计提利息':>12}"
        )
        lines.append("-" * 72)

        # 逐笔明细
        total_principal = Decimal("0.00")
        total_interest = Decimal("0.00")
        valid_count = 0

        for idx, accrual in enumerate(accruals, start=1):
            account_number = accrual.get("account_number", "-")
            principal = Decimal(str(accrual.get("principal", 0)))
            interest_rate = Decimal(str(accrual.get("interest_rate", 0)))
            days = accrual.get("days", 1)
            # 兼容不同字段名
            interest = Decimal(str(
                accrual.get("accrued_interest", accrual.get("interest_amount", 0))
            ))

            # 跳过无效记录（利息为0的可能是跳过的账户）
            if interest <= Decimal("0") and principal <= Decimal("0"):
                continue

            valid_count += 1

            # 利率显示为百分比形式
            rate_display = interest_rate * Decimal("100") if interest_rate < Decimal("1") else interest_rate

            lines.append(
                f"{valid_count:<5}{account_number:<22}{principal:>12,.2f}"
                f"{rate_display:>10.4f}{days:>5}{interest:>12,.2f}"
            )

            total_principal += principal
            total_interest += interest

        # 如果没有有效记录
        if valid_count == 0:
            lines.append("    （无计提记录）")

        # 合计
        lines.append("-" * 72)
        lines.append(f"{'合计':<5}{'':<22}{total_principal:>12,.2f}")
        lines.append(f"{'':>44}计提利息合计: {total_interest:>12,.2f}")
        lines.append("")

        # 统计信息
        lines.append("-" * 72)
        lines.append("【统计信息】")
        lines.append(f"  有效计提账户数: {valid_count}")
        lines.append(f"  计提本金合计:   {total_principal:>16,.2f}")
        lines.append(f"  计提利息合计:   {total_interest:>16,.2f}")
        if total_principal > Decimal("0"):
            avg_rate = (total_interest / total_principal * Decimal("360") * Decimal("100"))
            lines.append(f"  加权平均利率:   {avg_rate:>16.4f}%")
        lines.append("")

        # 生成时间
        lines.append("-" * 72)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 72)

        return "\n".join(lines)
