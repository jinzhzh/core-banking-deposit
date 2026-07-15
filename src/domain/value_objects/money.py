"""
金额值对象

不可变的金额表示，支持加减比较运算，确保金额计算的精确性。
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from functools import total_ordering


@total_ordering
class Money:
    """
    金额值对象（不可变）

    封装金额和币种，提供安全的算术运算。
    使用Decimal确保精确计算，避免浮点数精度问题。

    使用示例:
        >>> m1 = Money(Decimal("100.00"))
        >>> m2 = Money(Decimal("50.50"))
        >>> m3 = m1 + m2  # Money(150.50, CNY)
        >>> m1 > m2  # True
    """

    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Decimal | str | int | float, currency: str = "CNY") -> None:
        """
        初始化金额值对象

        Args:
            amount: 金额数值
            currency: 币种代码，默认CNY

        Raises:
            ValueError: 金额格式不正确
            TypeError: 金额类型不支持
        """
        if isinstance(amount, float):
            # 避免浮点数精度问题，先转为字符串
            amount = Decimal(str(amount))
        elif isinstance(amount, (int, str)):
            try:
                amount = Decimal(str(amount))
            except InvalidOperation:
                raise ValueError(f"无效的金额格式: {amount}")
        elif not isinstance(amount, Decimal):
            raise TypeError(f"不支持的金额类型: {type(amount)}")

        # 保留2位小数
        object.__setattr__(self, "_amount", amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        object.__setattr__(self, "_currency", currency.upper())

    @property
    def amount(self) -> Decimal:
        """获取金额数值"""
        return self._amount

    @property
    def currency(self) -> str:
        """获取币种"""
        return self._currency

    def __setattr__(self, name: str, value) -> None:
        """禁止修改属性，确保不可变性"""
        raise AttributeError("Money对象是不可变的，不能修改属性")

    def __add__(self, other: Money) -> Money:
        """加法运算"""
        self._check_currency(other)
        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: Money) -> Money:
        """减法运算"""
        self._check_currency(other)
        return Money(self._amount - other._amount, self._currency)

    def __mul__(self, multiplier: Decimal | int | float) -> Money:
        """乘法运算（金额 × 系数）"""
        if isinstance(multiplier, (int, float)):
            multiplier = Decimal(str(multiplier))
        return Money(self._amount * multiplier, self._currency)

    def __rmul__(self, multiplier: Decimal | int | float) -> Money:
        """右乘法运算"""
        return self.__mul__(multiplier)

    def __neg__(self) -> Money:
        """取负"""
        return Money(-self._amount, self._currency)

    def __abs__(self) -> Money:
        """取绝对值"""
        return Money(abs(self._amount), self._currency)

    def __eq__(self, other: object) -> bool:
        """相等比较"""
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other._amount and self._currency == other._currency

    def __lt__(self, other: Money) -> bool:
        """小于比较"""
        self._check_currency(other)
        return self._amount < other._amount

    def __hash__(self) -> int:
        """哈希值"""
        return hash((self._amount, self._currency))

    def __bool__(self) -> bool:
        """布尔值（非零为True）"""
        return self._amount != Decimal("0.00")

    def _check_currency(self, other: Money) -> None:
        """
        检查币种是否一致

        Raises:
            ValueError: 币种不一致
        """
        if self._currency != other._currency:
            raise ValueError(
                f"币种不一致，无法运算: {self._currency} vs {other._currency}"
            )

    def is_positive(self) -> bool:
        """判断是否为正数"""
        return self._amount > Decimal("0")

    def is_negative(self) -> bool:
        """判断是否为负数"""
        return self._amount < Decimal("0")

    def is_zero(self) -> bool:
        """判断是否为零"""
        return self._amount == Decimal("0.00")

    @classmethod
    def zero(cls, currency: str = "CNY") -> Money:
        """
        创建零金额

        Args:
            currency: 币种

        Returns:
            零金额的Money对象
        """
        return cls(Decimal("0.00"), currency)

    def __repr__(self) -> str:
        return f"Money({self._amount}, {self._currency})"

    def __str__(self) -> str:
        return f"{self._currency} {self._amount:,.2f}"
