"""
会计引擎模块

提供核心银行存款系统的会计处理功能，包括：
- 科目表管理
- 分录引擎
- 过账引擎
- 总账管理
- 明细账管理
- 余额校验/对账
- 会计期间管理
"""

from src.accounting.chart_of_accounts import AccountCode, ChartOfAccounts
from src.accounting.journal_engine import JournalEngine
from src.accounting.posting_engine import PostingEngine
from src.accounting.general_ledger import GeneralLedgerManager
from src.accounting.sub_ledger import SubLedgerManager
from src.accounting.balance_checker import BalanceChecker, ReconciliationResult
from src.accounting.accounting_period import AccountingPeriod

__all__ = [
    "AccountCode",
    "ChartOfAccounts",
    "JournalEngine",
    "PostingEngine",
    "GeneralLedgerManager",
    "SubLedgerManager",
    "BalanceChecker",
    "ReconciliationResult",
    "AccountingPeriod",
]
