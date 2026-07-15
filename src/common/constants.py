"""
系统常量模块

定义核心银行存款系统中使用的各类常量。
"""

# ============ 系统标识 ============
SYSTEM_NAME = "核心银行存款系统"
SYSTEM_VERSION = "1.0.0"

# ============ 日期格式 ============
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT_COMPACT = "%Y%m%d"
TIME_FORMAT = "%H%M%S"

# ============ 计息常量 ============
YEAR_DAYS = 360  # 计息年天数
MONTH_DAYS = 30  # 计息月天数
QUARTER_MONTHS = 3  # 季度月数

# 结息日（每季度末月20日）
INTEREST_SETTLEMENT_DAY = 20
INTEREST_SETTLEMENT_MONTHS = [3, 6, 9, 12]  # 结息月份

# ============ 金额常量 ============
ZERO_AMOUNT = 0  # 零金额（分）
MIN_TRANSACTION_AMOUNT = 1  # 最小交易金额（分），0.01元
MAX_AMOUNT_DIGITS = 15  # 金额最大位数

# ============ 账号常量 ============
ACCOUNT_NUMBER_LENGTH = 19  # 标准账号长度
ACCOUNT_PREFIX_DEBIT = "6222"  # 借记卡前缀
ACCOUNT_PREFIX_FIXED = "6223"  # 定期存单前缀

# ============ 交易流水号 ============
TRANSACTION_ID_LENGTH = 32  # 交易流水号长度
ENTRY_ID_LENGTH = 20  # 分录编号长度

# ============ 批处理常量 ============
BATCH_SIZE_DEFAULT = 1000  # 默认批处理大小
BATCH_MAX_RETRY = 3  # 批处理最大重试次数

# ============ 定期存款期限（月） ============
FIXED_TERM_3M = 3
FIXED_TERM_6M = 6
FIXED_TERM_1Y = 12
FIXED_TERM_2Y = 24
FIXED_TERM_3Y = 36
FIXED_TERM_5Y = 60

VALID_FIXED_TERMS = [
    FIXED_TERM_3M,
    FIXED_TERM_6M,
    FIXED_TERM_1Y,
    FIXED_TERM_2Y,
    FIXED_TERM_3Y,
    FIXED_TERM_5Y,
]

# ============ 身份证常量 ============
ID_CARD_LENGTH_18 = 18  # 18位身份证
ID_CARD_LENGTH_15 = 15  # 15位身份证（旧版）

# ============ 币种 ============
CURRENCY_CNY = "CNY"  # 人民币
CURRENCY_USD = "USD"  # 美元

# ============ 默认值 ============
DEFAULT_CURRENCY = CURRENCY_CNY
DEFAULT_BRANCH = "110000"
DEFAULT_OPERATOR = "SYSTEM"
