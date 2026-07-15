"""
Saga事务编排

实现Saga模式的分布式事务管理。按顺序执行多个步骤，
任何步骤失败时按逆序执行已完成步骤的补偿操作，确保最终一致性。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any, List, Optional


@dataclass
class SagaStep:
    """
    Saga步骤定义

    属性:
        step_name: 步骤名称，用于日志和追踪
        action: 正向操作的可调用对象
        compensation: 补偿操作的可调用对象，用于回滚已完成的正向操作
    """

    step_name: str
    action: Callable[[], Any]
    compensation: Callable[[], Any]


@dataclass
class SagaExecutionLog:
    """
    Saga执行日志条目

    属性:
        step_name: 步骤名称
        action_type: 操作类型（"action" 或 "compensation"）
        status: 执行状态（"success" 或 "failed"）
        timestamp: 执行时间
        result: 执行结果或异常信息
    """

    step_name: str
    action_type: str
    status: str
    timestamp: datetime
    result: Optional[Any] = None
    error: Optional[str] = None


class Saga:
    """
    Saga事务编排器

    管理一组有序步骤的执行。每个步骤包含正向操作和补偿操作。
    按顺序执行所有步骤，任何步骤失败时按逆序执行已完成步骤的补偿。
    """

    def __init__(self) -> None:
        """初始化Saga编排器"""
        self._steps: List[SagaStep] = []
        self._execution_logs: List[SagaExecutionLog] = []

    def add_step(
        self,
        name: str,
        action: Callable[[], Any],
        compensation: Callable[[], Any],
    ) -> "Saga":
        """
        添加一个Saga步骤。

        参数:
            name: 步骤名称
            action: 正向操作的可调用对象
            compensation: 补偿操作的可调用对象

        返回:
            Saga: 当前Saga实例（支持链式调用）
        """
        step = SagaStep(step_name=name, action=action, compensation=compensation)
        self._steps.append(step)
        return self

    def execute(self) -> dict:
        """
        执行Saga事务。

        按顺序执行所有步骤的正向操作。如果某个步骤失败，
        则按逆序对已成功完成的步骤执行补偿操作。

        返回:
            dict: 执行结果，包含：
                - success: 是否全部成功
                - completed_steps: 成功完成的步骤数
                - total_steps: 总步骤数
                - failed_step: 失败的步骤名称（如有）
                - error: 错误信息（如有）
                - compensated: 是否执行了补偿
                - logs: 执行日志列表

        异常:
            不抛出异常，所有错误通过返回值体现
        """
        self._execution_logs = []
        completed_steps: List[SagaStep] = []
        results: List[Any] = []

        # 按顺序执行所有步骤
        for step in self._steps:
            try:
                result = step.action()
                results.append(result)
                completed_steps.append(step)

                # 记录成功日志
                self._execution_logs.append(SagaExecutionLog(
                    step_name=step.step_name,
                    action_type="action",
                    status="success",
                    timestamp=datetime.now(),
                    result=result,
                ))

            except Exception as e:
                # 记录失败日志
                self._execution_logs.append(SagaExecutionLog(
                    step_name=step.step_name,
                    action_type="action",
                    status="failed",
                    timestamp=datetime.now(),
                    error=str(e),
                ))

                # 按逆序执行已完成步骤的补偿
                compensation_errors = self._compensate(completed_steps)

                return {
                    "success": False,
                    "completed_steps": len(completed_steps),
                    "total_steps": len(self._steps),
                    "failed_step": step.step_name,
                    "error": str(e),
                    "compensated": True,
                    "compensation_errors": compensation_errors,
                    "logs": self._get_log_dicts(),
                }

        return {
            "success": True,
            "completed_steps": len(completed_steps),
            "total_steps": len(self._steps),
            "failed_step": None,
            "error": None,
            "compensated": False,
            "compensation_errors": [],
            "logs": self._get_log_dicts(),
        }

    def _compensate(self, completed_steps: List[SagaStep]) -> List[str]:
        """
        按逆序执行已完成步骤的补偿操作。

        参数:
            completed_steps: 已成功完成的步骤列表

        返回:
            list: 补偿过程中发生的错误信息列表
        """
        compensation_errors: List[str] = []

        for step in reversed(completed_steps):
            try:
                step.compensation()

                # 记录补偿成功日志
                self._execution_logs.append(SagaExecutionLog(
                    step_name=step.step_name,
                    action_type="compensation",
                    status="success",
                    timestamp=datetime.now(),
                ))

            except Exception as e:
                error_msg = f"步骤 '{step.step_name}' 补偿失败: {str(e)}"
                compensation_errors.append(error_msg)

                # 记录补偿失败日志
                self._execution_logs.append(SagaExecutionLog(
                    step_name=step.step_name,
                    action_type="compensation",
                    status="failed",
                    timestamp=datetime.now(),
                    error=str(e),
                ))

        return compensation_errors

    def _get_log_dicts(self) -> List[dict]:
        """
        将执行日志转换为字典列表。

        返回:
            list: 日志字典列表
        """
        return [
            {
                "step_name": log.step_name,
                "action_type": log.action_type,
                "status": log.status,
                "timestamp": log.timestamp,
                "result": log.result,
                "error": log.error,
            }
            for log in self._execution_logs
        ]

    @property
    def execution_logs(self) -> List[SagaExecutionLog]:
        """
        获取执行日志。

        返回:
            list: SagaExecutionLog 列表
        """
        return list(self._execution_logs)

    @property
    def steps(self) -> List[SagaStep]:
        """
        获取已注册的步骤列表。

        返回:
            list: SagaStep 列表
        """
        return list(self._steps)
