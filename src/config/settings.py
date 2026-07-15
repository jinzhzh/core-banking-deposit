"""
全局配置模块

定义系统运行所需的全局配置参数，包括银行代码、系统日期、精度设置等。
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP


@dataclass
class SystemSettings:
    """系统全局配置"""

    # 银行基本信息
    bank_code: str = "ICBC"
    bank_name: str = "工商银行"
    branch_code: str = "110000"
    branch_name: str = "北京分行"

    # 系统日期（业务日期，由日终批处理推进）
    system_date: date = field(default_factory=date.today)

    # 金额精度设置
    amount_precision: int = 2  # 金额保留小数位数
    interest_precision: int = 8  # 利息计算中间精度
    rounding_mode: str = "ROUND_HALF_UP"  # 四舍五入模式

    # 账号规则
    account_number_length: int = 19  # 账号长度
    account_number_prefix: str = "6222"  # 账号前缀（借记卡）

    # 交易限额
    single_deposit_max: int = 5_000_000_00  # 单笔存款上限（分），500万
    single_withdraw_max: int = 2_000_000_00  # 单笔取款上限（分），200万
    daily_withdraw_max: int = 5_000_000_00  # 日累计取款上限（分），500万

    # 计息规则
    year_days: int = 360  # 计息年天数（银行惯例360天）
    month_days: int = 30  # 计息月天数

    # 最低余额
    min_balance_demand: int = 100  # 活期最低余额（分），1元
    min_balance_fixed: int = 5000  # 定期最低存入金额（分），50元

    # 系统参数
    max_retry_times: int = 3  # 最大重试次数
    transaction_timeout: int = 30  # 交易超时时间（秒）
    batch_size: int = 1000  # 批处理每批数量

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"

    def get_rounding_mode(self):
        """获取Decimal舍入模式对象"""
        return ROUND_HALF_UP

    def advance_system_date(self, new_date: date) -> None:
        """
        推进系统日期（日终批处理调用）

        Args:
            new_date: 新的系统日期
        """
        if new_date <= self.system_date:
            raise ValueError(
                f"新日期 {new_date} 必须大于当前系统日期 {self.system_date}"
            )
        self.system_date = new_date


# 全局配置单例
settings = SystemSettings()
