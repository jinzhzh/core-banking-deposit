"""
自定义异常体系

定义核心银行存款系统的异常层次结构，每个异常包含错误码。
"""


class BaseError(Exception):
    """系统基础异常"""

    code: str = "SYS000"
    message: str = "系统未知错误"

    def __init__(self, message: str = None, code: str = None, detail: str = None):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.detail = detail or ""
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}" + (f" ({self.detail})" if self.detail else "")


class SystemError(BaseError):
    """系统级异常（内部错误、超时等）"""
    code = "SYS001"
    message = "系统内部错误"


class DatabaseError(BaseError):
    """数据库异常"""
    code = "SYS002"
    message = "数据库操作失败"


class TimeoutError(BaseError):
    """超时异常"""
    code = "SYS003"
    message = "操作超时"


class ConfigError(BaseError):
    """配置异常"""
    code = "SYS004"
    message = "系统配置错误"


class BusinessError(BaseError):
    """业务级异常基类"""
    code = "BIZ000"
    message = "业务处理失败"


class AccountError(BusinessError):
    """账户异常基类"""
    code = "ACC000"
    message = "账户操作失败"


class AccountNotFoundError(AccountError):
    """账户不存在"""
    code = "ACC001"
    message = "账户不存在"


class AccountAlreadyExistsError(AccountError):
    """账户已存在"""
    code = "ACC002"
    message = "账户已存在"


class AccountClosedError(AccountError):
    """账户已销户"""
    code = "ACC003"
    message = "账户已销户，无法操作"


class AccountStatusError(AccountError):
    """账户状态异常"""
    code = "ACC004"
    message = "账户状态不允许此操作"


class InsufficientBalanceError(BusinessError):
    """余额不足异常"""
    code = "BAL001"
    message = "账户余额不足"

    def __init__(self, available: int = 0, required: int = 0, **kwargs):
        self.available = available
        self.required = required
        detail = f"可用余额: {available}, 需要: {required}"
        super().__init__(detail=detail, **kwargs)


class FreezeError(BusinessError):
    """冻结异常基类"""
    code = "FRZ000"
    message = "冻结操作失败"


class AccountFrozenError(FreezeError):
    """账户已冻结"""
    code = "FRZ001"
    message = "账户已被冻结，无法操作"


class FreezeAmountExceedError(FreezeError):
    """冻结金额超限"""
    code = "FRZ002"
    message = "冻结金额超过可用余额"


class UnfreezeError(FreezeError):
    """解冻异常"""
    code = "FRZ003"
    message = "解冻操作失败"


class TransactionError(BusinessError):
    """交易异常基类"""
    code = "TXN000"
    message = "交易处理失败"


class AmountInvalidError(TransactionError):
    """金额无效"""
    code = "TXN001"
    message = "交易金额无效"


class AmountExceedLimitError(TransactionError):
    """金额超限"""
    code = "TXN002"
    message = "交易金额超过限额"


class DuplicateTransactionError(TransactionError):
    """重复交易"""
    code = "TXN003"
    message = "重复交易，请勿重复提交"


class DayCutError(BusinessError):
    """日切异常基类"""
    code = "DAY000"
    message = "日切处理失败"


class DayCutInProgressError(DayCutError):
    """日切进行中"""
    code = "DAY001"
    message = "日切处理中，暂停交易"


class DayCutSequenceError(DayCutError):
    """日切顺序错误"""
    code = "DAY002"
    message = "日切步骤顺序错误"


class InterestCalcError(BusinessError):
    """计息异常"""
    code = "INT001"
    message = "利息计算失败"


class ValidationError(BusinessError):
    """参数校验异常"""
    code = "VAL001"
    message = "参数校验失败"
