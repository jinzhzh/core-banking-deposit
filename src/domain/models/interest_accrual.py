"""
利息计提模型

记录每日利息计提的明细，用于日终批处理中的利息计算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class InterestAccrual:
    """
    利息计提实体

    记录某一天对某个账户的利息计提信息。
    计提利息 = 本金 × 日利率 × 天数
    日利率 = 年利率 / 360（银行惯例）
    """

    account_number: str                 # 账号
    accrual_date: date                  # 计提日期
    principal: Decimal                  # 本金（计息基数）
    interest_rate: Decimal              # 年化利率
    days: int                           # 计息天数
    accrued_interest: Decimal = Decimal("0.00")  # 计提利息金额
    is_posted: bool = False             # 是否已入账
    posted_at: datetime | None = None   # 入账时间
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间

    def __post_init__(self) -> None:
        """初始化后校验并计算利息"""
        self._validate()
        if self.accrued_interest == Decimal("0.00"):
            self.accrued_interest = self.calculate_interest()

    def _validate(self) -> None:
        """校验数据"""
        if not self.account_number:
            raise ValueError("账号不能为空")
        if self.principal < Decimal("0"):
            raise ValueError("本金不能为负数")
        if self.interest_rate < Decimal("0"):
            raise ValueError("利率不能为负数")
        if self.days < 0:
            raise ValueError("计息天数不能为负数")

    def calculate_interest(self) -> Decimal:
        """
        计算计提利息

        使用银行惯例：日利率 = 年利率 / 360
        计提利息 = 本金 × 日利率 × 天数

        Returns:
            计提利息金额（保留2位小数，四舍五入）
        """
        if self.principal == Decimal("0") or self.interest_rate == Decimal("0"):
            return Decimal("0.00")
        daily_rate = self.interest_rate / Decimal("360")
        interest = self.principal * daily_rate * Decimal(str(self.days))
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def post(self) -> None:
        """
        标记为已入账

        Raises:
            ValueError: 已经入账
        """
        if self.is_posted:
            raise ValueError(f"账号 {self.account_number} 在 {self.accrual_date} 的利息计提已入账")
        self.is_posted = True
        self.posted_at = datetime.now()

    def __repr__(self) -> str:
        return (
            f"InterestAccrual(account={self.account_number!r}, "
            f"date={self.accrual_date}, "
            f"principal={self.principal}, "
            f"rate={self.interest_rate}, "
            f"days={self.days}, "
            f"interest={self.accrued_interest}, "
            f"posted={self.is_posted})"
        )
