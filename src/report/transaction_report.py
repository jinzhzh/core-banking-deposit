"""
交易报告生成器

根据账户的交易流水生成格式化的交易明细报告，
包含账号、期间、逐笔交易明细和期末余额。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List


class TransactionReportGenerator:
    """
    交易报告生成器

    根据指定账户和日期范围内的交易流水，生成格式化的交易明细报告。
    """

    # 交易类型中文映射
    TXN_TYPE_NAMES: Dict[str, str] = {
        "deposit": "存款",
        "withdrawal": "取款",
        "open_deposit": "开户存款",
        "close_withdrawal": "销户取款",
        "demand_to_term": "活期转定期",
        "term_to_demand": "定期转活期",
        "interest_settlement": "利息结转",
        "reversal": "冲正",
        "transfer_in": "转入",
        "transfer_out": "转出",
    }

    def generate(
        self,
        account_number: str,
        transactions: List[Dict[str, Any]],
        start_date: date,
        end_date: date,
    ) -> str:
        """
        生成交易明细报告。

        包含账号、查询期间、逐笔交易明细和期末余额。

        参数:
            account_number: 账户号码
            transactions: 交易流水列表（按时间正序排列）
            start_date: 起始日期
            end_date: 结束日期

        返回:
            str: 格式化的中文文本交易明细报告
        """
        lines: List[str] = []

        # 报告标题
        lines.append("=" * 76)
        lines.append("                      交易明细报告")
        lines.append("=" * 76)
        lines.append("")

        # 基本信息
        lines.append(f"账    号: {account_number}")
        lines.append(
            f"查询期间: {start_date.strftime('%Y年%m月%d日')} "
            f"至 {end_date.strftime('%Y年%m月%d日')}"
        )
        lines.append(f"交易笔数: {len(transactions)}")
        lines.append("")

        # 交易明细表头
        lines.append("-" * 76)
        lines.append(
            f"{'序号':<5}{'交易日期':<12}{'交易类型':<10}"
            f"{'摘要':<14}{'金额':>12}{'余额':>12}"
        )
        lines.append("-" * 76)

        # 逐笔交易明细
        final_balance = Decimal("0.00")
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for idx, txn in enumerate(transactions, start=1):
            txn_time = txn.get("created_at", txn.get("transaction_time"))
            if isinstance(txn_time, datetime):
                date_str = txn_time.strftime("%Y-%m-%d")
            elif isinstance(txn_time, date):
                date_str = txn_time.strftime("%Y-%m-%d")
            else:
                date_str = str(txn_time)[:10] if txn_time else "-"

            txn_type = txn.get("txn_type", txn.get("transaction_type", ""))
            type_name = self.TXN_TYPE_NAMES.get(txn_type, txn_type)

            summary = txn.get("summary", "")
            if len(summary) > 10:
                summary = summary[:10] + "…"

            amount = txn.get("amount", Decimal("0"))
            balance_after = txn.get("balance_after", Decimal("0"))

            # 判断借贷方向
            if txn_type in ("withdrawal", "close_withdrawal", "demand_to_term", "transfer_out"):
                amount_str = f"-{amount:,.2f}"
                total_debit += amount
            else:
                amount_str = f"+{amount:,.2f}"
                total_credit += amount

            lines.append(
                f"{idx:<5}{date_str:<12}{type_name:<10}"
                f"{summary:<14}{amount_str:>12}"
                f"{balance_after:>12,.2f}"
            )

            final_balance = balance_after

        # 汇总
        lines.append("-" * 76)
        lines.append(f"期间收入合计: {total_credit:>12,.2f}")
        lines.append(f"期间支出合计: {total_debit:>12,.2f}")
        lines.append(f"期末余额:     {final_balance:>12,.2f}")
        lines.append("")

        # 生成时间
        lines.append("-" * 76)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 76)

        return "\n".join(lines)
