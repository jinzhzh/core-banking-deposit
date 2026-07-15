"""
主程序入口 / 应用容器

整个核心银行存款系统的组装点，负责依赖注入。
通过 BankingApplication 类统一初始化所有仓储、服务、会计引擎和批处理器，
并对外暴露各业务 API 接口。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

# 仓储层 - 内存实现
from src.repository.memory.account_repo_impl import InMemoryAccountRepository
from src.repository.memory.transaction_repo_impl import InMemoryTransactionRepository
from src.repository.memory.ledger_repo_impl import InMemoryLedgerRepository
from src.repository.memory.customer_repo_impl import InMemoryCustomerRepository
from src.repository.memory.batch_repo_impl import InMemoryBatchRepository

# 配置
from src.config.accounting_rules import AccountingRules, accounting_rules
from src.config.interest_rates import InterestRateConfig, interest_rate_config

# 服务层
from src.service.account_service import AccountService
from src.service.deposit_service import DepositService
from src.service.withdrawal_service import WithdrawalService
from src.service.transfer_service import TransferService
from src.service.freeze_service import FreezeService
from src.service.reversal_service import ReversalService
from src.service.interest_service import InterestService
from src.service.transaction_service import TransactionService
from src.service.query_service import QueryService

# 报表层
from src.report.reconciliation_report import ReconciliationReportGenerator
from src.report.balance_report import BalanceReportGenerator
from src.report.transaction_report import TransactionReportGenerator
from src.report.interest_report import InterestReportGenerator

# 批处理
from src.batch.batch_checkpoint import BatchCheckpoint


class SimpleJournalRepository:
    """
    简易凭证仓储（内存实现）

    提供会计分录的保存和按交易号查询功能。
    当 InMemoryJournalRepository 因依赖问题无法导入时作为替代方案。
    """

    def __init__(self) -> None:
        """初始化内存存储"""
        import threading
        self._store: dict = {}
        self._txn_index: dict = {}
        self._lock = threading.Lock()

    def save(self, entry) -> None:
        """
        保存会计分录。

        参数:
            entry: 分录数据（字典或实体对象）
        """
        with self._lock:
            if isinstance(entry, dict):
                entry_id = entry.get("entry_id", "")
                txn_id = entry.get("txn_id", "")
            else:
                entry_id = str(getattr(entry, "entry_id", ""))
                txn_id = str(getattr(entry, "transaction_id", ""))

            import copy
            self._store[entry_id] = copy.deepcopy(entry)

            if txn_id:
                if txn_id not in self._txn_index:
                    self._txn_index[txn_id] = []
                self._txn_index[txn_id].append(entry_id)

    def find_by_txn_id(self, txn_id: str) -> list:
        """
        根据交易流水号查询会计分录。

        参数:
            txn_id: 交易流水号

        返回:
            list: 该交易对应的会计分录列表
        """
        import copy
        with self._lock:
            entry_ids = self._txn_index.get(txn_id, [])
            result = []
            for eid in entry_ids:
                entry = self._store.get(eid)
                if entry:
                    result.append(copy.deepcopy(entry))
            return result


class AccountingEngine:
    """
    会计引擎

    封装会计分录的记账和查询操作，作为服务层与仓储层之间的桥梁。
    负责将会计分录持久化到记账本仓储中。
    """

    def __init__(self, journal_repository, ledger_repository, rules: AccountingRules) -> None:
        """
        初始化会计引擎。

        参数:
            journal_repository: 凭证仓储接口
            ledger_repository: 账本仓储接口
            rules: 会计规则配置
        """
        self._journal_repo = journal_repository
        self._ledger_repo = ledger_repository
        self._rules = rules

    def post_entries(self, entries: list) -> None:
        """
        记账：将会计分录持久化。

        参数:
            entries: 会计分录列表，每条包含 entry_id, txn_id, direction, subject, amount 等
        """
        for entry in entries:
            self._journal_repo.save(entry)
            # 同时写入总账
            self._ledger_repo.save_general_entry({
                "entry_id": entry.get("entry_id"),
                "account_code": entry.get("subject"),
                "direction": entry.get("direction"),
                "amount": entry.get("amount"),
                "entry_date": entry.get("created_at"),
                "txn_id": entry.get("txn_id"),
            })

    def get_entries_by_txn_id(self, txn_id: str) -> list:
        """
        根据交易流水号查询会计分录。

        参数:
            txn_id: 交易流水号

        返回:
            list: 该交易对应的会计分录列表
        """
        return self._journal_repo.find_by_txn_id(txn_id)


class InterestRateRepository:
    """
    利率仓储

    基于配置文件提供利率查询功能，封装利率配置的访问接口。
    """

    def __init__(self, config: InterestRateConfig) -> None:
        """
        初始化利率仓储。

        参数:
            config: 利率配置对象
        """
        self._config = config

    def get_demand_rate(self):
        """
        获取活期存款年利率（小数形式）。

        返回:
            Decimal: 活期年利率（如 0.0035 表示 0.35%）
        """
        from decimal import Decimal
        return self._config.demand.annual_rate / Decimal("100")

    def get_term_rate(self, term_months: int):
        """
        获取定期存款年利率（小数形式）。

        参数:
            term_months: 存期月数

        返回:
            Decimal: 定期年利率（如 0.0175 表示 1.75%）
        """
        from decimal import Decimal
        return self._config.fixed.get_rate_by_term(term_months) / Decimal("100")


class BankingApplication:
    """
    银行存款系统应用容器

    整个系统的组装点，负责依赖注入。初始化所有仓储（内存实现）、
    服务、会计引擎和批处理器，并对外暴露各业务 API 属性。
    """

    def __init__(self) -> None:
        """
        初始化应用容器。

        按照依赖顺序组装所有组件：
        1. 仓储层（内存实现）
        2. 配置（会计规则、利率）
        3. 会计引擎
        4. 服务层
        5. 批处理器
        6. 报表生成器
        """
        # 系统会计日期（默认为当天）
        self._system_date: date = date.today()

        # ========== 仓储层 ==========
        self._account_repo = InMemoryAccountRepository()
        self._transaction_repo = InMemoryTransactionRepository()
        self._journal_repo = SimpleJournalRepository()
        self._ledger_repo = InMemoryLedgerRepository()
        self._customer_repo = InMemoryCustomerRepository()
        self._batch_repo = InMemoryBatchRepository()

        # ========== 配置 ==========
        self._accounting_rules = accounting_rules
        self._interest_rate_config = interest_rate_config

        # ========== 利率仓储 ==========
        self._interest_rate_repo = InterestRateRepository(self._interest_rate_config)

        # ========== 会计引擎 ==========
        self._accounting_engine = AccountingEngine(
            self._journal_repo,
            self._ledger_repo,
            self._accounting_rules,
        )

        # ========== 服务层 ==========
        self._account_service = AccountService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
        )

        self._deposit_service = DepositService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
        )

        self._withdrawal_service = WithdrawalService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
        )

        self._transfer_service = TransferService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
            self._interest_rate_repo,
        )

        self._freeze_service = FreezeService(
            self._account_repo,
            self._account_repo,  # 冻结记录复用账户仓储（简化实现）
        )

        self._reversal_service = ReversalService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
            self._transaction_repo,  # 冲正记录复用交易仓储（简化实现）
        )

        self._interest_service = InterestService(
            self._account_repo,
            self._transaction_repo,
            self._accounting_engine,
            self._transaction_repo,  # 利息记录仓储（简化实现）
            self._interest_rate_repo,
        )

        self._transaction_service = TransactionService(
            self._transaction_repo,
        )

        self._query_service = QueryService(
            self._account_repo,
            self._transaction_repo,
            self._transaction_repo,  # 利息记录仓储（简化实现）
            self._account_repo,      # 冻结记录仓储（简化实现）
        )

        # ========== 批处理 ==========
        self._batch_checkpoint = BatchCheckpoint(self._batch_repo)

        # ========== 报表生成器 ==========
        self._reconciliation_report = ReconciliationReportGenerator()
        self._balance_report = BalanceReportGenerator(self._ledger_repo, self._accounting_rules)
        self._transaction_report = TransactionReportGenerator()
        self._interest_report = InterestReportGenerator()

    # ========== 对外暴露的 API 属性 ==========

    @property
    def account_service(self) -> AccountService:
        """账户服务（开户/销户）"""
        return self._account_service

    @property
    def deposit_service(self) -> DepositService:
        """存款服务"""
        return self._deposit_service

    @property
    def withdrawal_service(self) -> WithdrawalService:
        """取款服务"""
        return self._withdrawal_service

    @property
    def transfer_service(self) -> TransferService:
        """定活互转服务"""
        return self._transfer_service

    @property
    def freeze_service(self) -> FreezeService:
        """冻结/解冻服务"""
        return self._freeze_service

    @property
    def reversal_service(self) -> ReversalService:
        """冲正服务"""
        return self._reversal_service

    @property
    def interest_service(self) -> InterestService:
        """利息计算服务"""
        return self._interest_service

    @property
    def transaction_service(self) -> TransactionService:
        """交易流水服务"""
        return self._transaction_service

    @property
    def query_service(self) -> QueryService:
        """查询服务"""
        return self._query_service

    @property
    def reconciliation_report(self) -> ReconciliationReportGenerator:
        """对账报告生成器"""
        return self._reconciliation_report

    @property
    def balance_report(self) -> BalanceReportGenerator:
        """余额报告生成器"""
        return self._balance_report

    @property
    def transaction_report(self) -> TransactionReportGenerator:
        """交易报告生成器"""
        return self._transaction_report

    @property
    def interest_report(self) -> InterestReportGenerator:
        """利息报告生成器"""
        return self._interest_report

    @property
    def batch_checkpoint(self) -> BatchCheckpoint:
        """批处理检查点管理器"""
        return self._batch_checkpoint

    # ========== 系统日期管理 ==========

    def get_system_date(self) -> date:
        """
        获取当前系统会计日期。

        返回:
            date: 当前系统会计日期
        """
        return self._system_date

    def set_system_date(self, new_date: date) -> None:
        """
        设置系统会计日期（用于测试和日切操作）。

        参数:
            new_date: 新的系统会计日期

        异常:
            ValueError: 日期格式不合法
        """
        if not isinstance(new_date, date):
            raise ValueError("系统日期必须为 date 类型")
        self._system_date = new_date
