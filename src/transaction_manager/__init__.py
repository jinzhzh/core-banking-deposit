"""
事务管理层

提供工作单元（Unit of Work）、Saga事务编排和补偿机制，
确保跨仓储操作的数据一致性。
"""

from src.transaction_manager.unit_of_work import UnitOfWork
from src.transaction_manager.saga import Saga, SagaStep
from src.transaction_manager.compensation import CompensationManager

__all__ = [
    "UnitOfWork",
    "Saga",
    "SagaStep",
    "CompensationManager",
]
