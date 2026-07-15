"""
日志工具模块

提供统一的日志格式和日志记录器配置。
支持控制台输出和文件输出，包含交易追踪ID。
"""

import logging
import os
import sys
import threading
from datetime import datetime
from typing import Optional


# 线程本地存储，用于存放交易追踪信息
_thread_local = threading.local()


class TransactionContextFilter(logging.Filter):
    """
    交易上下文过滤器

    在日志记录中自动添加交易追踪ID和操作员信息。
    """

    def filter(self, record):
        record.transaction_id = getattr(_thread_local, "transaction_id", "-")
        record.operator = getattr(_thread_local, "operator", "SYSTEM")
        record.branch_code = getattr(_thread_local, "branch_code", "000000")
        return True


class BankingFormatter(logging.Formatter):
    """
    银行系统专用日志格式化器

    格式：时间 | 级别 | 机构 | 操作员 | 交易ID | 模块 | 消息
    """

    def __init__(self):
        fmt = (
            "%(asctime)s | %(levelname)-5s | %(branch_code)s | "
            "%(operator)s | %(transaction_id)s | %(name)s | %(message)s"
        )
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)


def setup_logger(
    name: str = "core_banking",
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_file: 日志文件路径，None则不输出到文件
        enable_console: 是否输出到控制台

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 添加上下文过滤器
    context_filter = TransactionContextFilter()
    logger.addFilter(context_filter)

    formatter = BankingFormatter()

    # 控制台输出
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        logger.addHandler(console_handler)

    # 文件输出
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.FileHandler(
            log_file, encoding="utf-8", mode="a"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        logger.addHandler(file_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    """
    获取模块日志记录器

    Args:
        module_name: 模块名称

    Returns:
        日志记录器
    """
    return logging.getLogger(f"core_banking.{module_name}")


def set_transaction_context(
    transaction_id: str = None,
    operator: str = None,
    branch_code: str = None,
) -> None:
    """
    设置当前线程的交易上下文

    在交易开始时调用，日志中会自动包含这些信息。

    Args:
        transaction_id: 交易流水号
        operator: 操作员ID
        branch_code: 机构代码
    """
    if transaction_id is not None:
        _thread_local.transaction_id = transaction_id
    if operator is not None:
        _thread_local.operator = operator
    if branch_code is not None:
        _thread_local.branch_code = branch_code


def clear_transaction_context() -> None:
    """清除当前线程的交易上下文"""
    _thread_local.transaction_id = "-"
    _thread_local.operator = "SYSTEM"
    _thread_local.branch_code = "000000"


class TransactionContext:
    """
    交易上下文管理器

    用法:
        with TransactionContext(transaction_id="TXN001", operator="OP01"):
            logger.info("处理交易")
            # 日志中自动包含交易ID和操作员
    """

    def __init__(
        self,
        transaction_id: str = None,
        operator: str = None,
        branch_code: str = None,
    ):
        self.transaction_id = transaction_id
        self.operator = operator
        self.branch_code = branch_code
        self._previous_context = {}

    def __enter__(self):
        # 保存之前的上下文
        self._previous_context = {
            "transaction_id": getattr(_thread_local, "transaction_id", "-"),
            "operator": getattr(_thread_local, "operator", "SYSTEM"),
            "branch_code": getattr(_thread_local, "branch_code", "000000"),
        }
        set_transaction_context(
            transaction_id=self.transaction_id,
            operator=self.operator,
            branch_code=self.branch_code,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复之前的上下文
        set_transaction_context(**self._previous_context)
        return False


# 初始化根日志记录器
_root_logger = setup_logger()
