"""
交易API

提供存款、取款、定活互转、冲正、冻结/解冻等交易操作的对外接口。
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


class TransactionAPI:
    """
    交易API类

    提供存款、取款、定活互转、冲正、冻结和解冻的接口。
    所有方法返回统一格式的结果字典。
    """

    def __init__(
        self,
        deposit_service,
        withdrawal_service,
        transfer_service,
        reversal_service,
        freeze_service,
    ) -> None:
        """
        初始化交易API。

        参数:
            deposit_service: 存款服务实例（DepositService）
            withdrawal_service: 取款服务实例（WithdrawalService）
            transfer_service: 定活互转服务实例（TransferService）
            reversal_service: 冲正服务实例（ReversalService）
            freeze_service: 冻结/解冻服务实例（FreezeService）
        """
        self._deposit_service = deposit_service
        self._withdrawal_service = withdrawal_service
        self._transfer_service = transfer_service
        self._reversal_service = reversal_service
        self._freeze_service = freeze_service

    def deposit(
        self,
        account_number: str,
        amount: Decimal,
        summary: Optional[str] = None,
    ) -> dict:
        """
        存款接口。

        向指定账户存入资金。

        参数:
            account_number: 账户号码
            amount: 存款金额
            summary: 摘要信息（可选，默认"现金存入"）

        返回:
            dict: 统一格式响应，成功时data包含交易流水信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return _error_response("存款金额格式无效", "VAL001")

            if amount <= Decimal("0"):
                return _error_response("存款金额必须大于零", "TXN001")

            kwargs = {"account_number": account_number, "amount": amount}
            if summary is not None:
                kwargs["summary"] = summary

            txn_data = self._deposit_service.deposit(**kwargs)

            return _success_response(data=txn_data, message="存款成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"存款失败: {str(e)}", "SYS001")

    def withdraw(
        self,
        account_number: str,
        amount: Decimal,
        summary: Optional[str] = None,
    ) -> dict:
        """
        取款接口。

        从指定账户取出资金。

        参数:
            account_number: 账户号码
            amount: 取款金额
            summary: 摘要信息（可选，默认"现金支取"）

        返回:
            dict: 统一格式响应，成功时data包含交易流水信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return _error_response("取款金额格式无效", "VAL001")

            if amount <= Decimal("0"):
                return _error_response("取款金额必须大于零", "TXN001")

            kwargs = {"account_number": account_number, "amount": amount}
            if summary is not None:
                kwargs["summary"] = summary

            txn_data = self._withdrawal_service.withdraw(**kwargs)

            return _success_response(data=txn_data, message="取款成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"取款失败: {str(e)}", "SYS001")

    def demand_to_term(
        self,
        account_number: str,
        amount: Decimal,
        term_months: int,
    ) -> dict:
        """
        活期转定期接口。

        将活期账户中的指定金额转为定期存款。

        参数:
            account_number: 活期账户号码
            amount: 转存金额
            term_months: 定期月数

        返回:
            dict: 统一格式响应，成功时data包含定期子账户信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return _error_response("转存金额格式无效", "VAL001")

            if amount <= Decimal("0"):
                return _error_response("转存金额必须大于零", "TXN001")

            if not isinstance(term_months, int) or term_months <= 0:
                return _error_response("定期月数必须为正整数", "VAL001")

            result = self._transfer_service.demand_to_term(
                account_number=account_number,
                amount=amount,
                term_months=term_months,
            )

            return _success_response(data=result, message="活期转定期成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"活期转定期失败: {str(e)}", "SYS001")

    def term_to_demand(self, term_account_number: str) -> dict:
        """
        定期转活期接口。

        将定期子账户的本金和利息转入对应的活期账户。

        参数:
            term_account_number: 定期子账户号码

        返回:
            dict: 统一格式响应，成功时data包含转出结果信息
        """
        try:
            if not term_account_number or not term_account_number.strip():
                return _error_response("定期账户号码不能为空", "VAL001")

            result = self._transfer_service.term_to_demand(
                term_account_number=term_account_number
            )

            return _success_response(data=result, message="定期转活期成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"定期转活期失败: {str(e)}", "SYS001")

    def reverse(self, transaction_id: str, reason: str) -> dict:
        """
        冲正接口。

        对指定的已完成交易进行冲正操作。

        参数:
            transaction_id: 原始交易流水ID
            reason: 冲正原因

        返回:
            dict: 统一格式响应，成功时data包含冲正结果信息
        """
        try:
            if not transaction_id or not transaction_id.strip():
                return _error_response("交易流水ID不能为空", "VAL001")

            if not reason or not reason.strip():
                return _error_response("冲正原因不能为空", "VAL001")

            result = self._reversal_service.reverse_transaction(
                original_txn_id=transaction_id,
                reason=reason,
                operator="SYSTEM",
            )

            return _success_response(data=result, message="冲正成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"冲正失败: {str(e)}", "SYS001")

    def freeze(
        self,
        account_number: str,
        amount: Decimal,
        freeze_type: str,
        reason: str,
    ) -> dict:
        """
        冻结接口。

        冻结指定账户的指定金额。

        参数:
            account_number: 账户号码
            amount: 冻结金额
            freeze_type: 冻结类型（如 "judicial" 司法冻结、"pledge" 质押冻结）
            reason: 冻结原因

        返回:
            dict: 统一格式响应，成功时data包含冻结记录信息
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return _error_response("冻结金额格式无效", "VAL001")

            if amount <= Decimal("0"):
                return _error_response("冻结金额必须大于零", "TXN001")

            if not freeze_type or not freeze_type.strip():
                return _error_response("冻结类型不能为空", "VAL001")

            if not reason or not reason.strip():
                return _error_response("冻结原因不能为空", "VAL001")

            result = self._freeze_service.freeze(
                account_number=account_number,
                amount=amount,
                freeze_type=freeze_type,
                reason=reason,
            )

            return _success_response(data=result, message="冻结成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"冻结失败: {str(e)}", "SYS001")

    def unfreeze(self, freeze_id: str) -> dict:
        """
        解冻接口。

        根据冻结记录ID解除冻结。

        参数:
            freeze_id: 冻结记录ID

        返回:
            dict: 统一格式响应，成功时data包含解冻结果信息
        """
        try:
            if not freeze_id or not freeze_id.strip():
                return _error_response("冻结记录ID不能为空", "VAL001")

            result = self._freeze_service.unfreeze(freeze_id=freeze_id)

            return _success_response(data=result, message="解冻成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except (ValueError, TypeError) as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"解冻失败: {str(e)}", "SYS001")
