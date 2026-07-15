"""
补偿机制

提供补偿动作的注册和执行管理。当业务操作失败时，
按逆序执行已注册的补偿动作以恢复数据一致性。
"""

from datetime import datetime
from typing import Callable, Any, Dict, List, Optional
from collections import OrderedDict


class CompensationManager:
    """
    补偿管理器

    管理补偿动作的注册和执行。支持按动作ID注册补偿函数，
    可单独执行某个补偿或按逆序执行所有已注册的补偿。
    """

    def __init__(self) -> None:
        """初始化补偿管理器"""
        # 使用有序字典保持注册顺序
        self._compensations: OrderedDict[str, Callable[[], Any]] = OrderedDict()
        self._execution_logs: List[Dict[str, Any]] = []

    def register(self, action_id: str, compensation_func: Callable[[], Any]) -> None:
        """
        注册补偿动作。

        将一个补偿函数与指定的动作ID关联。如果同一动作ID
        已注册过补偿，则覆盖之前的注册。

        参数:
            action_id: 动作唯一标识，用于后续单独执行补偿
            compensation_func: 补偿函数，无参数的可调用对象
        """
        self._compensations[action_id] = compensation_func

    def unregister(self, action_id: str) -> bool:
        """
        取消注册补偿动作。

        参数:
            action_id: 动作唯一标识

        返回:
            bool: 是否成功取消（动作ID存在则为True）
        """
        if action_id in self._compensations:
            del self._compensations[action_id]
            return True
        return False

    def compensate(self, action_id: str) -> Dict[str, Any]:
        """
        执行指定动作ID的补偿。

        参数:
            action_id: 动作唯一标识

        返回:
            dict: 执行结果，包含：
                - action_id: 动作ID
                - success: 是否成功
                - error: 错误信息（如有）
                - timestamp: 执行时间

        异常:
            ValueError: 动作ID未注册
        """
        if action_id not in self._compensations:
            raise ValueError(f"补偿动作 '{action_id}' 未注册")

        compensation_func = self._compensations[action_id]
        now = datetime.now()

        try:
            compensation_func()
            log_entry = {
                "action_id": action_id,
                "success": True,
                "error": None,
                "timestamp": now,
            }
            self._execution_logs.append(log_entry)

            # 执行成功后移除该补偿注册
            del self._compensations[action_id]

            return log_entry

        except Exception as e:
            log_entry = {
                "action_id": action_id,
                "success": False,
                "error": str(e),
                "timestamp": now,
            }
            self._execution_logs.append(log_entry)
            return log_entry

    def compensate_all(self) -> Dict[str, Any]:
        """
        按逆序执行所有已注册的补偿动作。

        按注册的逆序依次执行所有补偿。即使某个补偿失败，
        也会继续执行剩余的补偿动作。

        返回:
            dict: 执行结果汇总，包含：
                - success: 是否全部成功
                - total: 总补偿数
                - succeeded: 成功数
                - failed: 失败数
                - results: 每个补偿的执行结果列表
                - errors: 失败的错误信息列表
        """
        results: List[Dict[str, Any]] = []
        errors: List[str] = []

        # 按逆序执行所有补偿
        action_ids = list(reversed(self._compensations.keys()))

        for action_id in action_ids:
            compensation_func = self._compensations[action_id]
            now = datetime.now()

            try:
                compensation_func()
                log_entry = {
                    "action_id": action_id,
                    "success": True,
                    "error": None,
                    "timestamp": now,
                }
                results.append(log_entry)
                self._execution_logs.append(log_entry)

            except Exception as e:
                error_msg = f"补偿动作 '{action_id}' 执行失败: {str(e)}"
                errors.append(error_msg)
                log_entry = {
                    "action_id": action_id,
                    "success": False,
                    "error": str(e),
                    "timestamp": now,
                }
                results.append(log_entry)
                self._execution_logs.append(log_entry)

        # 清空已执行的补偿注册
        self._compensations.clear()

        succeeded = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        return {
            "success": failed == 0,
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
            "errors": errors,
        }

    @property
    def pending_count(self) -> int:
        """
        获取待执行的补偿动作数量。

        返回:
            int: 待执行补偿数量
        """
        return len(self._compensations)

    @property
    def pending_actions(self) -> List[str]:
        """
        获取待执行的补偿动作ID列表。

        返回:
            list: 动作ID列表（按注册顺序）
        """
        return list(self._compensations.keys())

    @property
    def execution_logs(self) -> List[Dict[str, Any]]:
        """
        获取执行日志。

        返回:
            list: 执行日志列表
        """
        return list(self._execution_logs)

    def clear(self) -> None:
        """
        清空所有已注册的补偿动作和执行日志。
        """
        self._compensations.clear()
        self._execution_logs.clear()
