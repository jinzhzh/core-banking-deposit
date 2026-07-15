"""
枚举模块

定义系统中使用的所有枚举类型。
"""

from enum import Enum, IntEnum, unique


@unique
class AccountStatus(str, Enum):
    """账户状态"""

    NORMAL = "NORMAL"          # 正常
    FROZEN = "FROZEN"          # 冻结
    DORMANT = "DORMANT"        # 睡眠（长期无交易）
    CLOSED = "CLOSED"          # 已销户
    PENDING = "PENDING"        # 待激活


@unique
class AccountType(str, Enum):
    """账户类型"""

    DEMAND = "DEMAND"          # 活期存款
    FIXED = "FIXED"            # 定期存款（整存整取）
    FIXED_INSTALLMENT = "FIXED_INSTALLMENT"  # 零存整取
    NOTIFY = "NOTIFY"          # 通知存款


@unique
class TransactionType(str, Enum):
    """交易类型"""

    DEPOSIT = "DEPOSIT"                # 存款
    WITHDRAWAL = "WITHDRAWAL"          # 取款
    TRANSFER_OUT = "TRANSFER_OUT"      # 转账转出
    TRANSFER_IN = "TRANSFER_IN"        # 转账转入
    INTEREST_SETTLE = "INTEREST_SETTLE"  # 结息
    FIXED_OPEN = "FIXED_OPEN"          # 定期开户
    FIXED_MATURE = "FIXED_MATURE"      # 定期到期
    FIXED_EARLY_WITHDRAW = "FIXED_EARLY_WITHDRAW"  # 定期提前支取
    FREEZE = "FREEZE"                  # 冻结
    UNFREEZE = "UNFREEZE"              # 解冻
    ACCOUNT_OPEN = "ACCOUNT_OPEN"      # 开户
    ACCOUNT_CLOSE = "ACCOUNT_CLOSE"    # 销户


@unique
class EntryDirection(str, Enum):
    """分录方向（借贷方向）"""

    DEBIT = "D"    # 借方
    CREDIT = "C"   # 贷方


@unique
class FreezeType(str, Enum):
    """冻结类型"""

    JUDICIAL = "JUDICIAL"      # 司法冻结
    RISK = "RISK"              # 风控冻结
    MANUAL = "MANUAL"          # 人工冻结
    SYSTEM = "SYSTEM"          # 系统冻结（如日切）
    LOSS_REPORT = "LOSS_REPORT"  # 挂失冻结


@unique
class BatchStatus(str, Enum):
    """批次状态"""

    PENDING = "PENDING"        # 待处理
    RUNNING = "RUNNING"        # 处理中
    SUCCESS = "SUCCESS"        # 处理成功
    FAILED = "FAILED"          # 处理失败
    PARTIAL = "PARTIAL"        # 部分成功
    CANCELLED = "CANCELLED"    # 已取消


@unique
class DayCutStep(str, Enum):
    """日切步骤"""

    STOP_TRANSACTION = "STOP_TRANSACTION"    # 停止交易
    INTEREST_ACCRUAL = "INTEREST_ACCRUAL"    # 计提利息
    INTEREST_SETTLE = "INTEREST_SETTLE"      # 结息处理
    FIXED_MATURE = "FIXED_MATURE"            # 定期到期处理
    ACCOUNT_CHECK = "ACCOUNT_CHECK"          # 账务核对
    DATE_ADVANCE = "DATE_ADVANCE"            # 日期切换
    RESUME_TRANSACTION = "RESUME_TRANSACTION"  # 恢复交易


@unique
class Currency(str, Enum):
    """币种"""

    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元
    EUR = "EUR"  # 欧元
    GBP = "GBP"  # 英镑
    JPY = "JPY"  # 日元


@unique
class Gender(str, Enum):
    """性别"""

    MALE = "M"      # 男
    FEMALE = "F"    # 女
    UNKNOWN = "U"   # 未知


@unique
class IdType(str, Enum):
    """证件类型"""

    ID_CARD = "ID_CARD"            # 身份证
    PASSPORT = "PASSPORT"          # 护照
    MILITARY = "MILITARY"          # 军官证
    HK_MACAO = "HK_MACAO"         # 港澳通行证
    TAIWAN = "TAIWAN"              # 台湾通行证
    OTHER = "OTHER"                # 其他


@unique
class FixedDepositTerm(IntEnum):
    """定期存款期限（月）"""

    THREE_MONTH = 3
    SIX_MONTH = 6
    ONE_YEAR = 12
    TWO_YEAR = 24
    THREE_YEAR = 36
    FIVE_YEAR = 60
