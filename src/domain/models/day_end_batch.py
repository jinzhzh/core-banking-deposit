"""
日终批次模型

管理日终批处理的执行状态和步骤，支持断点续跑和回滚。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional


class BatchStatus(Enum):
    """批次状态枚举"""
    PENDING = "PENDING"             # 待处理
    RUNNING = "RUNNING"             # 处理中
    SUCCESS = "SUCCESS"             # 成功
    FAILED = "FAILED"               # 失败
    ROLLED_BACK = "ROLLED_BACK"     # 已回滚


class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "PENDING"             # 待处理
    RUNNING = "RUNNING"             # 处理中
    SUCCESS = "SUCCESS"             # 成功
    FAILED = "FAILED"               # 失败
    SKIPPED = "SKIPPED"             # 已跳过


@dataclass
class BatchStep:
    """
    批处理步骤

    记录日终批处理中每个步骤的执行状态。
    """

    step_name: str                      # 步骤名称
    status: StepStatus = StepStatus.PENDING  # 步骤状态
    start_time: Optional[datetime] = None    # 开始时间
    end_time: Optional[datetime] = None      # 结束时间
    error_message: Optional[str] = None      # 错误信息

    def start(self) -> None:
        """标记步骤开始执行"""
        self.status = StepStatus.RUNNING
        self.start_time = datetime.now()

    def complete(self) -> None:
        """标记步骤执行成功"""
        self.status = StepStatus.SUCCESS
        self.end_time = datetime.now()

    def fail(self, error_message: str) -> None:
        """
        标记步骤执行失败

        Args:
            error_message: 错误信息
        """
        self.status = StepStatus.FAILED
        self.end_time = datetime.now()
        self.error_message = error_message

    def skip(self) -> None:
        """标记步骤跳过"""
        self.status = StepStatus.SKIPPED

    def duration_seconds(self) -> Optional[float]:
        """计算步骤执行耗时（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def __repr__(self) -> str:
        return (
            f"BatchStep(name={self.step_name!r}, "
            f"status={self.status.value})"
        )


@dataclass
class DayEndBatch:
    """
    日终批次实体

    管理一次日终批处理的完整生命周期，包括：
    - 利息计提
    - 到期处理
    - 总账轧差
    - 对账
    - 日切

    支持检查点机制，失败后可从断点续跑。
    """

    batch_id: str                       # 批次号
    accounting_date: date               # 会计日期
    status: BatchStatus = BatchStatus.PENDING  # 批次状态
    start_time: Optional[datetime] = None      # 开始时间
    end_time: Optional[datetime] = None        # 结束时间
    steps: List[BatchStep] = field(default_factory=list)  # 处理步骤列表
    checkpoint: Optional[str] = None    # 检查点（最后成功的步骤名）
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间

    def __post_init__(self) -> None:
        """初始化后校验"""
        if not self.batch_id:
            raise ValueError("批次号不能为空")

    def add_step(self, step_name: str) -> BatchStep:
        """
        添加处理步骤

        Args:
            step_name: 步骤名称

        Returns:
            新创建的步骤对象
        """
        step = BatchStep(step_name=step_name)
        self.steps.append(step)
        return step

    def start(self) -> None:
        """开始执行批次"""
        if self.status not in (BatchStatus.PENDING, BatchStatus.FAILED):
            raise ValueError(f"批次 {self.batch_id} 当前状态为 {self.status.value}，无法启动")
        self.status = BatchStatus.RUNNING
        self.start_time = datetime.now()

    def complete(self) -> None:
        """标记批次执行成功"""
        self.status = BatchStatus.SUCCESS
        self.end_time = datetime.now()

    def fail(self) -> None:
        """标记批次执行失败"""
        self.status = BatchStatus.FAILED
        self.end_time = datetime.now()

    def rollback(self) -> None:
        """标记批次已回滚"""
        if self.status != BatchStatus.FAILED:
            raise ValueError(f"批次 {self.batch_id} 当前状态为 {self.status.value}，只有失败的批次才能回滚")
        self.status = BatchStatus.ROLLED_BACK

    def update_checkpoint(self, step_name: str) -> None:
        """
        更新检查点

        Args:
            step_name: 最后成功完成的步骤名
        """
        self.checkpoint = step_name

    def get_current_step(self) -> Optional[BatchStep]:
        """获取当前正在执行的步骤"""
        for step in self.steps:
            if step.status == StepStatus.RUNNING:
                return step
        return None

    def get_next_step(self) -> Optional[BatchStep]:
        """获取下一个待执行的步骤"""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None

    def get_failed_step(self) -> Optional[BatchStep]:
        """获取失败的步骤"""
        for step in self.steps:
            if step.status == StepStatus.FAILED:
                return step
        return None

    def resume_from_checkpoint(self) -> Optional[BatchStep]:
        """
        从检查点恢复，返回下一个需要执行的步骤

        Returns:
            下一个待执行的步骤，如果没有则返回None
        """
        if self.checkpoint is None:
            return self.get_next_step()

        found_checkpoint = False
        for step in self.steps:
            if step.step_name == self.checkpoint:
                found_checkpoint = True
                continue
            if found_checkpoint and step.status in (StepStatus.PENDING, StepStatus.FAILED):
                return step
        return None

    def __repr__(self) -> str:
        return (
            f"DayEndBatch(id={self.batch_id!r}, "
            f"date={self.accounting_date}, "
            f"status={self.status.value}, "
            f"steps={len(self.steps)}, "
            f"checkpoint={self.checkpoint!r})"
        )
