"""
账户API

提供开户、销户、查询账户等对外接口。
封装service层，统一异常处理并返回标准格式结果。
"""

from decimal import Decimal, InvalidOperation
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


class AccountAPI:
    """
    账户API类

    提供开户、销户、查询账户和查询客户所有账户的接口。
    所有方法返回统一格式的结果字典。
    """

    def __init__(self, account_service, customer_service=None) -> None:
        """
        初始化账户API。

        参数:
            account_service: 账户服务实例（AccountService）
            customer_service: 客户服务实例（可选，用于客户信息管理）
        """
        self._account_service = account_service
        self._customer_service = customer_service

    def open_account(
        self,
        customer_name: str,
        id_number: str,
        phone: str,
        account_type: str,
        initial_deposit: Decimal,
        term_months: Optional[int] = None,
    ) -> dict:
        """
        开户接口。

        创建新账户，包括客户信息登记和账户创建。

        参数:
            customer_name: 客户姓名
            id_number: 证件号码
            phone: 手机号码
            account_type: 账户类型（"demand" 活期 / "term" 定期）
            initial_deposit: 初始存款金额
            term_months: 定期月数（仅定期账户需要）

        返回:
            dict: 统一格式响应，成功时data包含账户信息
        """
        try:
            # 参数校验
            if not customer_name or not customer_name.strip():
                return _error_response("客户姓名不能为空", "VAL001")

            if not id_number or not id_number.strip():
                return _error_response("证件号码不能为空", "VAL001")

            if not phone or not phone.strip():
                return _error_response("手机号码不能为空", "VAL001")

            if account_type not in ("demand", "term"):
                return _error_response(
                    "账户类型必须为 'demand'（活期）或 'term'（定期）",
                    "VAL001",
                )

            if not isinstance(initial_deposit, Decimal):
                try:
                    initial_deposit = Decimal(str(initial_deposit))
                except (InvalidOperation, ValueError):
                    return _error_response("初始存款金额格式无效", "VAL001")

            if initial_deposit <= Decimal("0"):
                return _error_response("初始存款金额必须大于零", "VAL001")

            if account_type == "term" and term_months is None:
                return _error_response("定期账户必须指定存期月数", "VAL001")

            # 生成客户ID（使用证件号码作为客户标识）
            customer_id = id_number

            # 调用服务层开户
            account_data = self._account_service.open_account(
                customer_id=customer_id,
                account_type=account_type,
                initial_deposit=initial_deposit,
                term_months=term_months,
            )

            return _success_response(data=account_data, message="开户成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"开户失败: {str(e)}", "SYS001")

    def close_account(self, account_number: str) -> dict:
        """
        销户接口。

        关闭指定账户，结清余额和利息。

        参数:
            account_number: 账户号码

        返回:
            dict: 统一格式响应，成功时data包含销户结果
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            result = self._account_service.close_account(
                account_number=account_number,
                operator="SYSTEM",
            )

            return _success_response(data=result, message="销户成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"销户失败: {str(e)}", "SYS001")

    def get_account(self, account_number: str) -> dict:
        """
        查询账户接口。

        根据账户号码查询账户详细信息。

        参数:
            account_number: 账户号码

        返回:
            dict: 统一格式响应，成功时data包含账户信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            account = self._account_service.get_account_info(account_number)
            if account is None:
                return _error_response(
                    f"账户 {account_number} 不存在", "ACC001"
                )

            return _success_response(data=account, message="查询成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询账户失败: {str(e)}", "SYS001")

    def get_customer_accounts(self, customer_id: str) -> dict:
        """
        查询客户所有账户接口。

        根据客户ID查询该客户名下所有账户。

        参数:
            customer_id: 客户编号

        返回:
            dict: 统一格式响应，成功时data包含账户列表
        """
        try:
            if not customer_id or not customer_id.strip():
                return _error_response("客户编号不能为空", "VAL001")

            # 通过账户仓储查询客户的所有账户
            accounts = self._account_service._account_repo.find_by_customer_id(
                customer_id
            )

            return _success_response(
                data={"customer_id": customer_id, "accounts": accounts},
                message="查询成功",
            )

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询客户账户失败: {str(e)}", "SYS001")
