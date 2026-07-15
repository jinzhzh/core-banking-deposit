"""
查询API

提供余额查询、可用余额查询、交易流水查询和利息明细查询等对外接口。
封装service层，统一异常处理并返回标准格式结果。
"""

from datetime import date
from typing import Optional

from src.common.exceptions import BaseError


def _success_response(data=None, message: str = "操作成功") -> dict:
    """
    构建成功响应。

    参数:
        data: 响应数据
        message: 成功消息

    返回:
        dict: 统一格式的成功响应
    """
    return {
        "success": True,
        "data": data,
        "message": message,
        "error_code": None,
    }


def _error_response(message: str, error_code: str = "UNKNOWN") -> dict:
    """
    构建错误响应。

    参数:
        message: 错误消息
        error_code: 错误码

    返回:
        dict: 统一格式的错误响应
    """
    return {
        "success": False,
        "data": None,
        "message": message,
        "error_code": error_code,
    }


class QueryAPI:
    """
    查询API类

    提供余额、可用余额、交易流水和利息明细的查询接口。
    所有方法返回统一格式的结果字典。
    """

    def __init__(self, query_service, transaction_service) -> None:
        """
        初始化查询API。

        参数:
            query_service: 查询服务实例（QueryService）
            transaction_service: 交易流水服务实例（TransactionService）
        """
        self._query_service = query_service
        self._transaction_service = transaction_service

    def get_balance(self, account_number: str) -> dict:
        """
        查询余额接口。

        查询指定账户的账面余额（不扣除冻结金额）。

        参数:
            account_number: 账户号码

        返回:
            dict: 统一格式响应，成功时data包含余额信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            balance = self._query_service.get_balance(account_number)

            return _success_response(
                data={
                    "account_number": account_number,
                    "balance": balance,
                },
                message="查询成功",
            )

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询余额失败: {str(e)}", "SYS001")

    def get_available_balance(self, account_number: str) -> dict:
        """
        查询可用余额接口。

        查询指定账户的可用余额（余额 - 冻结金额）。

        参数:
            account_number: 账户号码

        返回:
            dict: 统一格式响应，成功时data包含可用余额信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            available_balance = self._query_service.get_available_balance(
                account_number
            )

            return _success_response(
                data={
                    "account_number": account_number,
                    "available_balance": available_balance,
                },
                message="查询成功",
            )

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询可用余额失败: {str(e)}", "SYS001")

    def get_transactions(
        self,
        account_number: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        查询交易流水接口。

        查询指定账户在日期范围内的交易流水记录。

        参数:
            account_number: 账户号码
            start_date: 起始日期（可选，默认为30天前）
            end_date: 结束日期（可选，默认为今天）

        返回:
            dict: 统一格式响应，成功时data包含交易流水列表
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            # 默认查询最近30天
            if end_date is None:
                end_date = date.today()

            if start_date is None:
                from datetime import timedelta
                start_date = end_date - timedelta(days=30)

            if start_date > end_date:
                return _error_response("起始日期不能晚于结束日期", "VAL001")

            transactions = self._transaction_service.get_account_transactions(
                account_number=account_number,
                start_date=start_date,
                end_date=end_date,
            )

            return _success_response(
                data={
                    "account_number": account_number,
                    "start_date": start_date,
                    "end_date": end_date,
                    "transactions": transactions,
                    "count": len(transactions),
                },
                message="查询成功",
            )

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询交易流水失败: {str(e)}", "SYS001")

    def get_interest_detail(self, account_number: str) -> dict:
        """
        查询利息明细接口。

        查询指定账户的利息计提和结转明细。

        参数:
            account_number: 账户号码

        返回:
            dict: 统一格式响应，成功时data包含利息明细信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            interest_detail = self._query_service.get_interest_detail(
                account_number
            )

            return _success_response(data=interest_detail, message="查询成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询利息明细失败: {str(e)}", "SYS001")
