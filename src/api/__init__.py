"""
API层

提供核心银行存款系统的统一对外接口。
所有API方法返回统一格式的结果字典，封装service层并处理异常。

返回格式：
    {
        "success": bool,
        "data": ...,
        "message": str,
        "error_code": str
    }
"""

from src.api.account_api import AccountAPI
from src.api.transaction_api import TransactionAPI
from src.api.batch_api import BatchAPI
from src.api.query_api import QueryAPI
from src.api.report_api import ReportAPI

__all__ = [
    "AccountAPI",
    "TransactionAPI",
    "BatchAPI",
    "QueryAPI",
    "ReportAPI",
]
