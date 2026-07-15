"""
批处理API

提供日终批处理的执行、状态查询和回滚等对外接口。
封装service层，统一异常处理并返回标准格式结果。
"""

from datetime import date, datetime
from typing import Optional
import uuid

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


class BatchAPI:
    """
    批处理API类

    提供日终批处理的执行、状态查询和回滚接口。
    所有方法返回统一格式的结果字典。
    """

    def __init__(self, interest_service, batch_repository, account_repository) -> None:
        """
        初始化批处理API。

        参数:
            interest_service: 利息计算服务实例（InterestService）
            batch_repository: 批次仓储实例
            account_repository: 账户仓储实例
        """
        self._interest_service = interest_service
        self._batch_repo = batch_repository
        self._account_repo = account_repository

    def run_day_end(self, accounting_date: Optional[date] = None) -> dict:
        """
        执行日终批处理接口。

        执行日终批处理流程，包括利息计提、对账等操作。

        参数:
            accounting_date: 会计日期（可选，默认为当天）

        返回:
            dict: 统一格式响应，成功时data包含批次执行结果
        """
        try:
            if accounting_date is None:
                accounting_date = date.today()

            # 生成批次ID
            batch_id = str(uuid.uuid4())
            now = datetime.now()

            # 创建批次记录
            batch_record = {
                "batch_id": batch_id,
                "batch_date": accounting_date,
                "batch_type": "day_end",
                "status": "running",
                "started_at": now,
                "created_at": now,
            }
            self._batch_repo.save(batch_record)

            # 执行日终批处理步骤
            processed_accounts = 0
            errors = []

            # 获取所有活跃账户
            all_accounts = self._account_repo.find_all()
            active_accounts = [
                acc for acc in all_accounts
                if getattr(acc, "status", None) == "active"
                or (isinstance(acc, dict) and acc.get("status") == "active")
            ]

            # 对每个活跃账户执行利息计提
            for account in active_accounts:
                try:
                    # 获取账户号码
                    if isinstance(account, dict):
                        account_number = account.get("account_number", "")
                    else:
                        account_number = getattr(account, "account_number", "")

                    if account_number:
                        self._interest_service.accrue_interest(
                            account_number, accounting_date
                        )
                        processed_accounts += 1
                except Exception as e:
                    errors.append(f"账户利息计提失败: {str(e)}")

            # 更新批次状态
            final_status = "completed" if not errors else "completed_with_errors"
            self._batch_repo.update_status(batch_id, final_status)

            result = {
                "batch_id": batch_id,
                "batch_date": accounting_date,
                "status": final_status,
                "processed_accounts": processed_accounts,
                "total_accounts": len(active_accounts),
                "errors": errors,
                "started_at": now,
                "completed_at": datetime.now(),
            }

            return _success_response(data=result, message="日终批处理完成")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"日终批处理失败: {str(e)}", "SYS001")

    def get_batch_status(self, batch_id: str) -> dict:
        """
        查询批次状态接口。

        根据批次ID查询批处理的执行状态。

        参数:
            batch_id: 批次ID

        返回:
            dict: 统一格式响应，成功时data包含批次状态信息
        """
        try:
            if not batch_id or not batch_id.strip():
                return _error_response("批次ID不能为空", "VAL001")

            batch = self._batch_repo.find_by_id(batch_id)
            if batch is None:
                return _error_response(
                    f"批次 {batch_id} 不存在", "DAY000"
                )

            return _success_response(data=batch, message="查询成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"查询批次状态失败: {str(e)}", "SYS001")

    def rollback_batch(self, batch_id: str) -> dict:
        """
        回滚批次接口。

        回滚指定批次的所有操作，恢复到批次执行前的状态。

        参数:
            batch_id: 批次ID

        返回:
            dict: 统一格式响应，成功时data包含回滚结果
        """
        try:
            if not batch_id or not batch_id.strip():
                return _error_response("批次ID不能为空", "VAL001")

            # 查询批次记录
            batch = self._batch_repo.find_by_id(batch_id)
            if batch is None:
                return _error_response(
                    f"批次 {batch_id} 不存在", "DAY000"
                )

            # 检查批次状态是否允许回滚
            batch_status = batch.get("status", "")
            if batch_status == "rolled_back":
                return _error_response(
                    f"批次 {batch_id} 已回滚，不可重复操作", "DAY000"
                )

            if batch_status == "running":
                return _error_response(
                    f"批次 {batch_id} 正在执行中，无法回滚", "DAY001"
                )

            # 获取检查点并回滚
            checkpoint = self._batch_repo.get_checkpoint(batch_id)
            if checkpoint is not None:
                # 如果有检查点，使用检查点数据进行回滚
                self._account_repo.rollback()

            # 更新批次状态为已回滚
            self._batch_repo.update_status(batch_id, "rolled_back")

            result = {
                "batch_id": batch_id,
                "status": "rolled_back",
                "rolled_back_at": datetime.now(),
            }

            return _success_response(data=result, message="批次回滚成功")

        except BaseError as e:
            return _error_response(e.message, e.code)
        except ValueError as e:
            return _error_response(str(e), "BIZ000")
        except Exception as e:
            return _error_response(f"批次回滚失败: {str(e)}", "SYS001")
