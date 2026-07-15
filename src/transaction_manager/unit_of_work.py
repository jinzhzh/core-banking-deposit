"""
工作单元（Unit of Work）

管理一组仓储的事务边界，通过快照机制实现原子性操作。
支持 with 语句，异常时自动回滚所有仓储到事务开始前的状态。
"""

from typing import List, Any


class UnitOfWork:
    """
    工作单元类

    对所有注册的仓储统一管理事务边界。
    开始事务时为每个仓储创建快照，提交时清除快照，
    回滚时将所有仓储恢复到快照状态。
    """

    def __init__(self, repositories: List[Any]) -> None:
        """
        初始化工作单元。

        参数:
            repositories: 仓储实例列表，每个仓储需支持
                          create_snapshot() 和 rollback() 方法
        """
        self._repositories = repositories
        self._snapshot_indices: List[int] = []
        self._active = False

    def begin(self) -> None:
        """
        开始事务。

        对所有仓储创建快照，记录快照索引以便后续回滚。
        如果事务已经处于活跃状态，则抛出异常。

        异常:
            RuntimeError: 事务已处于活跃状态
        """
        if self._active:
            raise RuntimeError("事务已处于活跃状态，不可重复开始")

        self._snapshot_indices = []
        for repo in self._repositories:
            index = repo.create_snapshot()
            self._snapshot_indices.append(index)

        self._active = True

    def commit(self) -> None:
        """
        提交事务。

        清除快照索引，标记事务结束。提交后数据变更生效，
        不再支持回滚。

        异常:
            RuntimeError: 没有活跃的事务
        """
        if not self._active:
            raise RuntimeError("没有活跃的事务可提交")

        # 清除快照引用，数据变更已生效
        self._snapshot_indices = []
        self._active = False

    def rollback(self) -> None:
        """
        回滚事务。

        将所有仓储恢复到事务开始前的快照状态。
        回滚后事务结束。

        异常:
            RuntimeError: 没有活跃的事务
        """
        if not self._active:
            raise RuntimeError("没有活跃的事务可回滚")

        # 逆序回滚所有仓储
        for i in range(len(self._repositories) - 1, -1, -1):
            repo = self._repositories[i]
            snapshot_index = self._snapshot_indices[i]
            repo.rollback(snapshot_index)

        self._snapshot_indices = []
        self._active = False

    @property
    def is_active(self) -> bool:
        """
        判断事务是否处于活跃状态。

        返回:
            bool: 事务是否活跃
        """
        return self._active

    def __enter__(self) -> "UnitOfWork":
        """
        进入 with 语句时自动开始事务。

        返回:
            UnitOfWork: 当前工作单元实例
        """
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        退出 with 语句时根据是否有异常决定提交或回滚。

        如果发生异常则自动回滚，否则自动提交。

        参数:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪信息

        返回:
            bool: 不抑制异常（返回 False）
        """
        if exc_type is not None:
            # 发生异常，自动回滚
            if self._active:
                self.rollback()
        else:
            # 无异常，自动提交
            if self._active:
                self.commit()

        return False
