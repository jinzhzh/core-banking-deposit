"""
批处理检查点

用于日终批处理的断点续跑机制。在每个步骤成功完成后保存检查点，
当批处理因异常中断时，可从最后一个成功的检查点恢复执行。
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, Optional

from src.repository.interfaces.batch_repo import BatchRepository


class BatchCheckpoint:
    """
    批处理检查点管理器

    负责保存、加载和清除批处理检查点数据，
    支持日终批处理在失败后从断点恢复执行。
    """

    def __init__(self, batch_repository: BatchRepository) -> None:
        """
        初始化检查点管理器

        Args:
            batch_repository: 批次仓储接口，用于持久化检查点数据
        """
        self._batch_repo = batch_repository

    def save(self, batch_id: str, step_name: str, state_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存检查点

        在某个步骤成功完成后调用，记录当前执行进度和状态数据，
        以便后续从该点恢复执行。

        Args:
            batch_id: 批次ID
            step_name: 当前完成的步骤名称
            state_data: 可选的状态数据（如已处理的账户列表、中间结果等）

        Returns:
            保存成功返回True

        Raises:
            ValueError: 批次不存在时抛出
        """
        checkpoint_data = {
            "step_name": step_name,
            "saved_at": datetime.now().isoformat(),
            "state_data": copy.deepcopy(state_data) if state_data else {},
        }
        return self._batch_repo.save_checkpoint(batch_id, checkpoint_data)

    def load(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        加载检查点

        获取指定批次的最新检查点数据，用于断点续跑时确定恢复位置。

        Args:
            batch_id: 批次ID

        Returns:
            检查点数据字典，包含step_name和state_data；
            如果没有检查点则返回None
        """
        return self._batch_repo.get_checkpoint(batch_id)

    def clear(self, batch_id: str) -> bool:
        """
        清除检查点

        批处理全部成功完成后调用，清除该批次的所有检查点数据。

        Args:
            batch_id: 批次ID

        Returns:
            清除成功返回True，批次不存在返回False
        """
        # 通过保存一个空的终止检查点来标记清除
        clear_data = {
            "step_name": "__CLEARED__",
            "saved_at": datetime.now().isoformat(),
            "state_data": {"cleared": True},
        }
        try:
            self._batch_repo.save_checkpoint(batch_id, clear_data)
            return True
        except ValueError:
            return False

    def get_resume_step(self, batch_id: str) -> Optional[str]:
        """
        获取恢复执行的起始步骤名称

        根据检查点确定应该从哪个步骤之后继续执行。

        Args:
            batch_id: 批次ID

        Returns:
            最后成功完成的步骤名称；如果没有检查点则返回None
        """
        checkpoint = self.load(batch_id)
        if checkpoint is None:
            return None
        step_name = checkpoint.get("step_name")
        if step_name == "__CLEARED__":
            return None
        return step_name
