"""
利率配置模块

定义活期存款利率和各期限定期存款利率。
利率以年利率表示，单位为百分比（如0.35表示0.35%）。
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict


@dataclass
class DemandRate:
    """活期存款利率"""

    # 活期存款年利率（%）
    annual_rate: Decimal = Decimal("0.35")

    def get_daily_rate(self, year_days: int = 360) -> Decimal:
        """
        获取日利率

        Args:
            year_days: 计息年天数，默认360天

        Returns:
            日利率（已除以100转换为小数）
        """
        return self.annual_rate / Decimal("100") / Decimal(str(year_days))


@dataclass
class FixedRate:
    """定期存款利率"""

    # 整存整取利率（%）
    three_month: Decimal = Decimal("1.15")  # 三个月
    six_month: Decimal = Decimal("1.35")  # 六个月
    one_year: Decimal = Decimal("1.75")  # 一年
    two_year: Decimal = Decimal("2.25")  # 二年
    three_year: Decimal = Decimal("2.75")  # 三年
    five_year: Decimal = Decimal("2.75")  # 五年

    # 零存整取、整存零取、存本取息利率（%）
    installment_one_year: Decimal = Decimal("1.35")  # 一年
    installment_three_year: Decimal = Decimal("1.55")  # 三年
    installment_five_year: Decimal = Decimal("1.55")  # 五年

    def get_rate_by_term(self, term_months: int) -> Decimal:
        """
        根据期限（月）获取对应的整存整取年利率

        Args:
            term_months: 存期月数

        Returns:
            对应期限的年利率（%）

        Raises:
            ValueError: 不支持的存期
        """
        rate_map = {
            3: self.three_month,
            6: self.six_month,
            12: self.one_year,
            24: self.two_year,
            36: self.three_year,
            60: self.five_year,
        }
        if term_months not in rate_map:
            raise ValueError(
                f"不支持的定期存款期限: {term_months}个月，"
                f"支持的期限为: {list(rate_map.keys())}"
            )
        return rate_map[term_months]


@dataclass
class PenaltyRate:
    """罚息/提前支取利率"""

    # 定期提前支取按活期利率计息
    early_withdrawal_rate: Decimal = Decimal("0.35")

    # 逾期支取（到期未取）：逾期部分按活期利率计息
    overdue_rate: Decimal = Decimal("0.35")


@dataclass
class InterestRateConfig:
    """利率配置汇总"""

    demand: DemandRate = field(default_factory=DemandRate)
    fixed: FixedRate = field(default_factory=FixedRate)
    penalty: PenaltyRate = field(default_factory=PenaltyRate)

    def get_demand_annual_rate(self) -> Decimal:
        """获取活期年利率"""
        return self.demand.annual_rate

    def get_fixed_annual_rate(self, term_months: int) -> Decimal:
        """
        获取定期年利率

        Args:
            term_months: 存期月数

        Returns:
            年利率（%）
        """
        return self.fixed.get_rate_by_term(term_months)

    def get_all_rates(self) -> Dict[str, Decimal]:
        """
        获取所有利率配置（用于展示）

        Returns:
            利率名称到利率值的映射
        """
        return {
            "活期": self.demand.annual_rate,
            "定期三个月": self.fixed.three_month,
            "定期六个月": self.fixed.six_month,
            "定期一年": self.fixed.one_year,
            "定期二年": self.fixed.two_year,
            "定期三年": self.fixed.three_year,
            "定期五年": self.fixed.five_year,
        }


# 全局利率配置单例
interest_rate_config = InterestRateConfig()
