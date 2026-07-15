"""
装饰器模块

提供事务管理、日志记录、重试机制等通用装饰器。
"""

import functools
import logging
import time
import traceback
from typing import Callable, Type, Tuple

from .exceptions import BaseError, SystemError, TimeoutError

logger = logging.getLogger(__name__)


def transaction(func: Callable) -> Callable:
    """
    事务装饰器

    确保被装饰的函数在事务上下文中执行。
    如果函数正常返回则提交事务，如果抛出异常则回滚事务。

    用法:
        @transaction
        def transfer(from_account, to_account, amount):
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tx_id = f"{func.__name__}_{int(time.time() * 1000)}"
        logger.info(f"事务开始: {tx_id}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"事务提交: {tx_id}")
            return result
        except Exception as e:
            logger.error(f"事务回滚: {tx_id}, 原因: {e}")
            raise

    return wrapper


def log_operation(operation_name: str = None) -> Callable:
    """
    日志装饰器

    记录函数的调用参数、返回值和执行时间。

    Args:
        operation_name: 操作名称，默认使用函数名

    用法:
        @log_operation("存款操作")
        def deposit(account_id, amount):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()

            # 记录入参（脱敏处理，不记录敏感字段）
            safe_args = _sanitize_args(args, kwargs)
            logger.info(f"[{name}] 开始执行, 参数: {safe_args}")

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"[{name}] 执行成功, 耗时: {elapsed:.3f}秒")
                return result
            except BaseError as e:
                elapsed = time.time() - start_time
                logger.warning(
                    f"[{name}] 业务异常, 耗时: {elapsed:.3f}秒, "
                    f"错误码: {e.code}, 信息: {e.message}"
                )
                raise
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"[{name}] 系统异常, 耗时: {elapsed:.3f}秒, "
                    f"异常: {type(e).__name__}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                raise

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    重试装饰器

    在函数执行失败时自动重试，支持指数退避。

    Args:
        max_attempts: 最大尝试次数（包含首次执行）
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型元组

    用法:
        @retry(max_attempts=3, delay=0.5, exceptions=(DatabaseError,))
        def save_to_db(data):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"[重试] {func.__name__} 已达最大重试次数 "
                            f"{max_attempts}, 最后异常: {e}"
                        )
                        raise
                    logger.warning(
                        f"[重试] {func.__name__} 第{attempt}次失败, "
                        f"{current_delay:.1f}秒后重试, 异常: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper

    return decorator


def validate_params(*validators: Callable) -> Callable:
    """
    参数校验装饰器

    在函数执行前运行指定的校验器。

    Args:
        validators: 校验函数列表，每个校验函数接收与被装饰函数相同的参数

    用法:
        @validate_params(check_amount, check_account)
        def deposit(account_id, amount):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for validator in validators:
                validator(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _sanitize_args(args: tuple, kwargs: dict) -> str:
    """
    参数脱敏处理

    对敏感字段（如密码、身份证号）进行脱敏。

    Args:
        args: 位置参数
        kwargs: 关键字参数

    Returns:
        脱敏后的参数字符串
    """
    sensitive_keys = {"password", "pin", "id_card", "id_number", "card_number"}
    safe_kwargs = {}
    for key, value in kwargs.items():
        if key.lower() in sensitive_keys:
            safe_kwargs[key] = "***"
        else:
            safe_kwargs[key] = value
    return f"args={args}, kwargs={safe_kwargs}"
