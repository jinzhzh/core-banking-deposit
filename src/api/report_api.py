"""
报告API

提供对账报告、余额报告、交易报告和利息报告等对外接口。
封装service层，统一异常处理并返回标准格式结果。
"""

from datetime import date, datetime
from decimal import Decimal

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


class ReportAPI:
    """
    报告API类

    提供对账报告、余额报告、交易报告和利息报告的生成接口。
    所有方法返回统一格式的结果字典。
    """

    def __init__(
        self,
        query_service,
        transaction_service,
        interest_service,
        account_repository,
    ) -> None:
        """
        初始化报告API。

        参数:
            query_service: 查询服务实例（QueryService）
            transaction_service: 交易流水服务实例（TransactionService）
            interest_service: 利息计算服务实例（InterestService）
            account_repository: 账户仓储实例
        """
        self._query_service = query_service
        self._transaction_service = transaction_service
        self._interest_service = interest_service
        self._account_repo = account_repository

    def get_reconciliation_report(self, report_date: date) -> dict:
        """
        获取对账报告接口。

        生成指定日期的对账报告，包含所有账户的余额汇总和交易统计。

        参数:
            report_date: 报告日期

        返回:
            dict: 统一格式响应，成功时data包含对账报告数据
        """
        try:
            if report_date is None:
                return _error_response("报告日期不能为空", "VAL001")

            if report_date > date.today():
                return _error_response("报告日期不能晚于今天", "VAL001")

            # 获取所有账户
            all_accounts = self._account_repo.find_all()

            # 统计汇总
            total_balance = Decimal("0")
            total_frozen = Decimal("0")
            active_count = 0
            closed_count = 0

            for account in all_accounts:
                if isinstance(account, dict):
                    balance = account.get("balance", Decimal("0"))
                    frozen = account.get("frozen_amount", Decimal("0"))
                    status = account.get("status", "")
                else:
                    balance = getattr(account, "balance", Decimal("0"))
                    frozen = getattr(account, "frozen_amount", Decimal("0"))
                    status = getattr(account, "status", "")

                total_balance += balance if balance else Decimal("0")
                total_frozen += frozen if frozen else Decimal("0")

                if status == "active":
                    active_count += 1
                elif status == "closed":
                    closed_count += 1

            report_data = {
                "report_date": report_date,
                "report_type": "reconciliation",
                "generated_at": datetime.now(),
                "summary": {
                    "total_accounts": len(all_accounts),
                    "active_accounts": active_count,
                    "closed_accounts": closed_count,
                    "total_balance": total_balance,
                    "total_frozen_amount": total_frozen,
                    "total_available_balance": total_balance - total_frozen,
                },
            }

            return _success_response(data=report_data, message="对账报告生成成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"生成对账报告失败: {str(e)}", "SYS001")

    def get_balance_report(self, report_date: date) -> dict:
        """
        获取余额报告接口。

        生成指定日期的余额报告，按账户类型分类统计。

        参数:
            report_date: 报告日期

        返回:
            dict: 统一格式响应，成功时data包含余额报告数据
        """
        try:
            if report_date is None:
                return _error_response("报告日期不能为空", "VAL001")

            # 获取所有账户
            all_accounts = self._account_repo.find_all()

            # 按账户类型分类统计
            demand_balance = Decimal("0")
            term_balance = Decimal("0")
            demand_count = 0
            term_count = 0

            account_details = []

            for account in all_accounts:
                if isinstance(account, dict):
                    account_type = account.get("account_type", "")
                    balance = account.get("balance", Decimal("0"))
                    status = account.get("status", "")
                    account_number = account.get("account_number", "")
                else:
                    account_type = getattr(account, "account_type", "")
                    balance = getattr(account, "balance", Decimal("0"))
                    status = getattr(account, "status", "")
                    account_number = getattr(account, "account_number", "")

                if status != "active":
                    continue

                balance = balance if balance else Decimal("0")

                if account_type == "demand":
                    demand_balance += balance
                    demand_count += 1
                elif account_type == "term":
                    term_balance += balance
                    term_count += 1

                account_details.append({
                    "account_number": account_number,
                    "account_type": account_type,
                    "balance": balance,
                })

            report_data = {
                "report_date": report_date,
                "report_type": "balance",
                "generated_at": datetime.now(),
                "summary": {
                    "demand_accounts": demand_count,
                    "demand_total_balance": demand_balance,
                    "term_accounts": term_count,
                    "term_total_balance": term_balance,
                    "total_balance": demand_balance + term_balance,
                },
                "details": account_details,
            }

            return _success_response(data=report_data, message="余额报告生成成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"生成余额报告失败: {str(e)}", "SYS001")

    def get_transaction_report(
        self,
        account_number: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        获取交易报告接口。

        生成指定账户在日期范围内的交易报告。

        参数:
            account_number: 账户号码
            start_date: 起始日期
            end_date: 结束日期

        返回:
            dict: 统一格式响应，成功时data包含交易报告数据
        """
        try:
            if not account_number or not account_number.strip():
                return _error_response("账户号码不能为空", "VAL001")

            if start_date is None or end_date is None:
                return _error_response("起始日期和结束日期不能为空", "VAL001")

            if start_date > end_date:
                return _error_response("起始日期不能晚于结束日期", "VAL001")

            # 获取对账单（包含交易明细和汇总）
            statement = self._query_service.get_account_statement(
                account_number=account_number,
                start_date=start_date,
                end_date=end_date,
            )

            report_data = {
                "report_type": "transaction",
                "generated_at": datetime.now(),
                "account_number": account_number,
                "start_date": start_date,
                "end_date": end_date,
                "opening_balance": statement.get("opening_balance"),
                "closing_balance": statement.get("closing_balance"),
                "total_debit": statement.get("total_debit"),
                "total_credit": statement.get("total_credit"),
                "transaction_count": statement.get("transaction_count", 0),
                "transactions": statement.get("transactions", []),
            }

            return _success_response(data=report_data, message="交易报告生成成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"生成交易报告失败: {str(e)}", "SYS001")

    def get_interest_report(self, report_date: date) -> dict:
        """
        获取利息报告接口。

        生成指定日期的利息报告，包含所有账户的利息计提和结转汇总。

        参数:
            report_date: 报告日期

        返回:
            dict: 统一格式响应，成功时data包含利息报告数据
        """
        try:
            if report_date is None:
                return _error_response("报告日期不能为空", "VAL001")

            # 获取所有活跃账户
            all_accounts = self._account_repo.find_all()

            total_accrued = Decimal("0")
            total_settled = Decimal("0")
            total_unsettled = Decimal("0")
            account_interest_details = []

            for account in all_accounts:
                if isinstance(account, dict):
                    status = account.get("status", "")
                    account_number = account.get("account_number", "")
                else:
                    status = getattr(account, "status", "")
                    account_number = getattr(account, "account_number", "")

                if status != "active" or not account_number:
                    continue

                try:
                    interest_detail = self._query_service.get_interest_detail(
                        account_number
                    )

                    accrued = interest_detail.get("total_accrued", Decimal("0"))
                    settled = interest_detail.get("total_settled", Decimal("0"))
                    unsettled = interest_detail.get("unsettled_interest", Decimal("0"))

                    total_accrued += accrued
                    total_settled += settled
                    total_unsettled += unsettled

                    account_interest_details.append({
                        "account_number": account_number,
                        "total_accrued": accrued,
                        "total_settled": settled,
                        "unsettled_interest": unsettled,
                    })

                except (ValueError, Exception):
                    # 跳过查询失败的账户
                    continue

            report_data = {
                "report_date": report_date,
                "report_type": "interest",
                "generated_at": datetime.now(),
                "summary": {
                    "total_accrued_interest": total_accrued,
                    "total_settled_interest": total_settled,
                    "total_unsettled_interest": total_unsettled,
                    "accounts_with_interest": len(account_interest_details),
                },
                "details": account_interest_details,
            }

            return _success_response(data=report_data, message="利息报告生成成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"生成利息报告失败: {str(e)}", "SYS001")
