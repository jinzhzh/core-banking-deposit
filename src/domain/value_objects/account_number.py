"""
账号值对象

封装银行账号，包含格式校验和校验位计算。
"""

from __future__ import annotations


class AccountNumber:
    """
    账号值对象（不可变）

    银行账号格式：机构代码(4位) + 账户类型(2位) + 序号(10位) + 校验位(1位)
    总长度：17位

    校验位算法：使用加权求和模10算法（类似Luhn算法）

    使用示例:
        >>> acct = AccountNumber("62201001000000011")
        >>> acct.is_valid()  # True
        >>> acct.branch_code  # "6220"
    """

    __slots__ = ("_value",)

    # 账号长度
    ACCOUNT_LENGTH = 17
    # 权重因子
    WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3, 7, 9, 1, 3, 7, 9]

    def __init__(self, value: str) -> None:
        """
        初始化账号值对象

        Args:
            value: 账号字符串

        Raises:
            ValueError: 账号格式不正确
        """
        if not value:
            raise ValueError("账号不能为空")
        if not value.isdigit():
            raise ValueError(f"账号只能包含数字: {value}")
        if len(value) != self.ACCOUNT_LENGTH:
            raise ValueError(
                f"账号长度必须为{self.ACCOUNT_LENGTH}位，当前为{len(value)}位"
            )
        if not self._validate_check_digit(value):
            raise ValueError(f"账号校验位不正确: {value}")
        object.__setattr__(self, "_value", value)

    def __setattr__(self, name: str, value) -> None:
        """禁止修改属性，确保不可变性"""
        raise AttributeError("AccountNumber对象是不可变的，不能修改属性")

    @property
    def value(self) -> str:
        """获取账号字符串"""
        return self._value

    @property
    def branch_code(self) -> str:
        """获取机构代码（前4位）"""
        return self._value[:4]

    @property
    def account_type_code(self) -> str:
        """获取账户类型代码（第5-6位）"""
        return self._value[4:6]

    @property
    def sequence(self) -> str:
        """获取序号（第7-16位）"""
        return self._value[6:16]

    @property
    def check_digit(self) -> str:
        """获取校验位（最后1位）"""
        return self._value[-1]

    @classmethod
    def _validate_check_digit(cls, account_number: str) -> bool:
        """
        校验账号的校验位

        使用加权求和模10算法：
        1. 取前16位数字
        2. 每位数字乘以对应权重
        3. 求和后对10取模
        4. 用10减去余数得到校验位（如果结果为10则取0）

        Args:
            account_number: 完整账号（含校验位）

        Returns:
            校验位是否正确
        """
        digits = [int(d) for d in account_number[:16]]
        weighted_sum = sum(d * w for d, w in zip(digits, cls.WEIGHTS))
        expected_check = (10 - (weighted_sum % 10)) % 10
        actual_check = int(account_number[-1])
        return expected_check == actual_check

    @classmethod
    def generate_check_digit(cls, partial_number: str) -> str:
        """
        为前16位账号生成校验位

        Args:
            partial_number: 前16位账号

        Returns:
            完整的17位账号（含校验位）

        Raises:
            ValueError: 输入格式不正确
        """
        if len(partial_number) != 16:
            raise ValueError("需要提供前16位账号")
        if not partial_number.isdigit():
            raise ValueError("账号只能包含数字")
        digits = [int(d) for d in partial_number]
        weighted_sum = sum(d * w for d, w in zip(digits, cls.WEIGHTS))
        check_digit = (10 - (weighted_sum % 10)) % 10
        return partial_number + str(check_digit)

    def is_valid(self) -> bool:
        """判断账号是否有效"""
        return self._validate_check_digit(self._value)

    def __eq__(self, other: object) -> bool:
        """相等比较"""
        if isinstance(other, AccountNumber):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        """哈希值"""
        return hash(self._value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"AccountNumber({self._value!r})"
