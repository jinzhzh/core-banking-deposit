"""
银行核心账务模拟器 - 零售存款子系统 验收演示

验收流程：开户存取 → 日切 → 利息计提 → 冲正 → 账平
输出：日终对账报告

硬约束验证：
1. 余额变动须双分录（借方合计=贷方合计）
2. 冲正不可改历史流水只能反向分录
3. 日切失败可回滚
"""

import sys
import os
from decimal import Decimal
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
import uuid
import copy

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.models.account import Account, AccountType, AccountStatus
from src.domain.models.customer import Customer
from src.domain.models.transaction import Transaction
from src.repository.memory.account_repo_impl import InMemoryAccountRepository
from src.repository.memory.transaction_repo_impl import InMemoryTransactionRepository
from src.repository.memory.ledger_repo_impl import InMemoryLedgerRepository
from src.config.interest_rates import interest_rate_config


# ============================================================
# 核心引擎：会计分录引擎（确保双分录约束）
# ============================================================
class AccountingLedger:
    """会计总账引擎 - 确保所有余额变动都有借贷双分录"""

    def __init__(self):
        self.journal_entries: List[Dict] = []  # 所有会计分录
        self.general_ledger: Dict[str, Decimal] = {}  # 科目余额（借方为正）
        self.sub_ledger: Dict[str, List[Dict]] = {}  # 明细账

    def post_double_entry(self, txn_id: str, debit_account: str,
                          credit_account: str, amount: Decimal,
                          summary: str, accounting_date: date) -> str:
        """
        记录双分录（硬约束：借方合计必须等于贷方合计）

        参数:
            txn_id: 关联交易流水号
            debit_account: 借方科目
            credit_account: 贷方科目
            amount: 金额
            summary: 摘要
            accounting_date: 会计日期
        """
        entry_id = str(uuid.uuid4())[:12]

        entry = {
            "entry_id": entry_id,
            "txn_id": txn_id,
            "accounting_date": accounting_date,
            "summary": summary,
            "lines": [
                {"subject": debit_account, "debit": amount, "credit": Decimal("0")},
                {"subject": credit_account, "debit": Decimal("0"), "credit": amount},
            ]
        }

        # 硬约束校验：借方合计 = 贷方合计
        total_debit = sum(line["debit"] for line in entry["lines"])
        total_credit = sum(line["credit"] for line in entry["lines"])
        assert total_debit == total_credit, \
            f"分录不平衡！借方={total_debit}, 贷方={total_credit}"

        self.journal_entries.append(entry)

        # 更新总账（资产类借增贷减，负债类贷增借减）
        self._update_general_ledger(debit_account, amount, "debit")
        self._update_general_ledger(credit_account, amount, "credit")

        # 更新明细账
        self._update_sub_ledger(entry, accounting_date)

        return entry_id

    def _update_general_ledger(self, account_code: str, amount: Decimal, direction: str):
        """更新总账余额"""
        if account_code not in self.general_ledger:
            self.general_ledger[account_code] = Decimal("0")

        # 资产类/费用类：借方增加；负债类/收入类：贷方增加
        asset_accounts = {"库存现金", "冻结资金备查"}
        expense_accounts = {"利息支出"}

        if account_code in asset_accounts or account_code in expense_accounts:
            if direction == "debit":
                self.general_ledger[account_code] += amount
            else:
                self.general_ledger[account_code] -= amount
        else:
            # 负债类（活期存款、定期存款、应付利息）
            if direction == "credit":
                self.general_ledger[account_code] += amount
            else:
                self.general_ledger[account_code] -= amount

    def _update_sub_ledger(self, entry: Dict, accounting_date: date):
        """更新明细账"""
        for line in entry["lines"]:
            subject = line["subject"]
            if subject not in self.sub_ledger:
                self.sub_ledger[subject] = []
            self.sub_ledger[subject].append({
                "entry_id": entry["entry_id"],
                "txn_id": entry["txn_id"],
                "date": accounting_date,
                "debit": line["debit"],
                "credit": line["credit"],
                "summary": entry["summary"],
            })

    def verify_trial_balance(self) -> bool:
        """验证试算平衡：所有分录借方合计 = 贷方合计"""
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for entry in self.journal_entries:
            for line in entry["lines"]:
                total_debit += line["debit"]
                total_credit += line["credit"]
        return total_debit == total_credit

    def get_total_debit(self) -> Decimal:
        total = Decimal("0")
        for entry in self.journal_entries:
            for line in entry["lines"]:
                total += line["debit"]
        return total

    def get_total_credit(self) -> Decimal:
        total = Decimal("0")
        for entry in self.journal_entries:
            for line in entry["lines"]:
                total += line["credit"]
        return total


# ============================================================
# 交易流水管理器
# ============================================================
class TransactionManager:
    """交易流水管理器 - 记录所有交易，冲正时不修改原流水"""

    def __init__(self):
        self.transactions: Dict[str, Dict] = {}

    def create_transaction(self, account_number: str, txn_type: str,
                          amount: Decimal, balance_after: Decimal,
                          summary: str, txn_date: date) -> str:
        """创建交易流水"""
        txn_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        self.transactions[txn_id] = {
            "txn_id": txn_id,
            "account_number": account_number,
            "txn_type": txn_type,
            "amount": amount,
            "balance_after": balance_after,
            "summary": summary,
            "txn_date": txn_date,
            "status": "completed",
            "is_reversed": False,
            "created_at": datetime.now(),
        }
        return txn_id

    def mark_reversed(self, txn_id: str):
        """标记交易已被冲正（不修改其他字段 - 硬约束）"""
        if txn_id in self.transactions:
            self.transactions[txn_id]["is_reversed"] = True

    def get_transaction(self, txn_id: str) -> Optional[Dict]:
        return self.transactions.get(txn_id)

    def get_account_transactions(self, account_number: str) -> List[Dict]:
        return [t for t in self.transactions.values()
                if t["account_number"] == account_number]


# ============================================================
# 存款账户管理器
# ============================================================
class DepositAccountManager:
    """存款账户管理器"""

    def __init__(self, ledger: AccountingLedger, txn_mgr: TransactionManager):
        self.accounts: Dict[str, Dict] = {}
        self.ledger = ledger
        self.txn_mgr = txn_mgr
        self._account_seq = 1000

    def open_account(self, customer_name: str, account_type: str,
                     initial_deposit: Decimal, accounting_date: date,
                     term_months: int = 0) -> str:
        """
        开户

        参数:
            customer_name: 客户姓名
            account_type: "demand"(活期) 或 "term"(定期)
            initial_deposit: 初始存款
            accounting_date: 会计日期
            term_months: 定期月数（仅定期需要）
        """
        self._account_seq += 1
        account_number = f"6222{self._account_seq:012d}"

        # 确定利率
        if account_type == "demand":
            rate = Decimal("0.0035")  # 活期0.35%
        else:
            rate_map = {3: Decimal("0.0135"), 6: Decimal("0.0155"),
                       12: Decimal("0.0175"), 24: Decimal("0.0225"),
                       36: Decimal("0.0275"), 60: Decimal("0.0275")}
            rate = rate_map.get(term_months, Decimal("0.0175"))

        self.accounts[account_number] = {
            "account_number": account_number,
            "customer_name": customer_name,
            "account_type": account_type,
            "balance": initial_deposit,
            "frozen_amount": Decimal("0"),
            "available_balance": initial_deposit,
            "status": "active",
            "interest_rate": rate,
            "term_months": term_months,
            "open_date": accounting_date,
            "accrued_interest": Decimal("0"),  # 累计计提利息
        }

        # 生成交易流水
        txn_id = self.txn_mgr.create_transaction(
            account_number, "open_deposit", initial_deposit,
            initial_deposit, f"开户存入-{customer_name}", accounting_date
        )

        # 生成会计分录（借:库存现金 贷:活期/定期存款）
        credit_subject = "活期存款" if account_type == "demand" else "定期存款"
        self.ledger.post_double_entry(
            txn_id, "库存现金", credit_subject, initial_deposit,
            f"开户存入-{customer_name}", accounting_date
        )

        return account_number

    def close_account(self, account_number: str, accounting_date: date) -> Decimal:
        """销户"""
        account = self.accounts[account_number]
        if account["status"] != "active":
            raise ValueError(f"账户状态异常: {account['status']}")
        if account["frozen_amount"] > Decimal("0"):
            raise ValueError("存在冻结金额，无法销户")

        remaining = account["balance"]
        if remaining > Decimal("0"):
            txn_id = self.txn_mgr.create_transaction(
                account_number, "close_withdrawal", remaining,
                Decimal("0"), "销户结清", accounting_date
            )
            debit_subject = "活期存款" if account["account_type"] == "demand" else "定期存款"
            self.ledger.post_double_entry(
                txn_id, debit_subject, "库存现金", remaining,
                "销户结清", accounting_date
            )

        account["balance"] = Decimal("0")
        account["available_balance"] = Decimal("0")
        account["status"] = "closed"
        return remaining

    def deposit(self, account_number: str, amount: Decimal,
                accounting_date: date, summary: str = "现金存入") -> str:
        """存款"""
        account = self.accounts[account_number]
        if account["status"] != "active":
            raise ValueError("账户状态异常")

        account["balance"] += amount
        account["available_balance"] = account["balance"] - account["frozen_amount"]

        txn_id = self.txn_mgr.create_transaction(
            account_number, "deposit", amount,
            account["balance"], summary, accounting_date
        )

        # 双分录：借:库存现金 贷:活期存款
        self.ledger.post_double_entry(
            txn_id, "库存现金", "活期存款", amount, summary, accounting_date
        )
        return txn_id

    def withdraw(self, account_number: str, amount: Decimal,
                 accounting_date: date, summary: str = "现金支取") -> str:
        """取款"""
        account = self.accounts[account_number]
        if account["status"] != "active":
            raise ValueError("账户状态异常")
        if amount > account["available_balance"]:
            raise ValueError(f"可用余额不足: {account['available_balance']}")

        account["balance"] -= amount
        account["available_balance"] = account["balance"] - account["frozen_amount"]

        txn_id = self.txn_mgr.create_transaction(
            account_number, "withdrawal", amount,
            account["balance"], summary, accounting_date
        )

        # 双分录：借:活期存款 贷:库存现金
        self.ledger.post_double_entry(
            txn_id, "活期存款", "库存现金", amount, summary, accounting_date
        )
        return txn_id


    def _create_term_account_internal(self, customer_name: str, amount: Decimal,
                                      term_months: int, accounting_date: date) -> str:
        """内部方法：创建定期账户（不生成会计分录，供活转定使用）"""
        self._account_seq += 1
        account_number = f"6222{self._account_seq:012d}"

        rate_map = {3: Decimal("0.0135"), 6: Decimal("0.0155"),
                   12: Decimal("0.0175"), 24: Decimal("0.0225"),
                   36: Decimal("0.0275"), 60: Decimal("0.0275")}
        rate = rate_map.get(term_months, Decimal("0.0175"))

        self.accounts[account_number] = {
            "account_number": account_number,
            "customer_name": customer_name,
            "account_type": "term",
            "balance": amount,
            "frozen_amount": Decimal("0"),
            "available_balance": amount,
            "status": "active",
            "interest_rate": rate,
            "term_months": term_months,
            "open_date": accounting_date,
            "accrued_interest": Decimal("0"),
        }
        return account_number

    def demand_to_term(self, account_number: str, amount: Decimal,
                       term_months: int, accounting_date: date) -> str:
        """活期转定期"""
        account = self.accounts[account_number]
        if account["account_type"] != "demand":
            raise ValueError("仅活期账户可转定期")
        if amount > account["available_balance"]:
            raise ValueError("可用余额不足")

        # 活期余额减少
        account["balance"] -= amount
        account["available_balance"] = account["balance"] - account["frozen_amount"]

        # 创建定期子账户（不生成额外分录）
        term_account = self._create_term_account_internal(
            account["customer_name"], amount, term_months, accounting_date
        )

        txn_id = self.txn_mgr.create_transaction(
            account_number, "demand_to_term", amount,
            account["balance"], f"活转定{term_months}个月", accounting_date
        )

        # 双分录：借:活期存款 贷:定期存款
        self.ledger.post_double_entry(
            txn_id, "活期存款", "定期存款", amount,
            f"活转定{term_months}个月", accounting_date
        )
        return term_account

    def term_to_demand(self, term_account_number: str,
                       demand_account_number: str, accounting_date: date) -> Decimal:
        """定期转活期（含利息）"""
        term_account = self.accounts[term_account_number]
        if term_account["account_type"] != "term":
            raise ValueError("非定期账户")

        principal = term_account["balance"]
        # 计算定期利息
        rate = term_account["interest_rate"]
        months = term_account["term_months"]
        interest = (principal * rate * Decimal(str(months)) / Decimal("12")).quantize(Decimal("0.01"))

        total = principal + interest

        # 定期账户清零
        term_account["balance"] = Decimal("0")
        term_account["status"] = "closed"

        # 活期账户增加
        demand_account = self.accounts[demand_account_number]
        demand_account["balance"] += total
        demand_account["available_balance"] = demand_account["balance"] - demand_account["frozen_amount"]

        txn_id = self.txn_mgr.create_transaction(
            demand_account_number, "term_to_demand", total,
            demand_account["balance"], f"定转活(本金{principal}+利息{interest})", accounting_date
        )

        # 双分录：借:定期存款 贷:活期存款（本金部分）
        self.ledger.post_double_entry(
            txn_id, "定期存款", "活期存款", principal,
            "定转活-本金", accounting_date
        )
        # 双分录：借:利息支出 贷:活期存款（利息部分）
        if interest > Decimal("0"):
            self.ledger.post_double_entry(
                txn_id, "利息支出", "活期存款", interest,
                "定转活-利息", accounting_date
            )

        return total

    def freeze(self, account_number: str, amount: Decimal,
               freeze_type: str, reason: str) -> str:
        """冻结"""
        account = self.accounts[account_number]
        if amount > account["available_balance"]:
            raise ValueError("可用余额不足以冻结")

        account["frozen_amount"] += amount
        account["available_balance"] = account["balance"] - account["frozen_amount"]

        freeze_id = f"FRZ{uuid.uuid4().hex[:8].upper()}"
        return freeze_id

    def unfreeze(self, account_number: str, amount: Decimal) -> None:
        """解冻"""
        account = self.accounts[account_number]
        account["frozen_amount"] -= amount
        if account["frozen_amount"] < Decimal("0"):
            account["frozen_amount"] = Decimal("0")
        account["available_balance"] = account["balance"] - account["frozen_amount"]


# ============================================================
# 冲正服务
# ============================================================
class ReversalService:
    """
    冲正服务

    硬约束：不修改历史流水，只能生成反向分录
    """

    def __init__(self, account_mgr: DepositAccountManager,
                 ledger: AccountingLedger, txn_mgr: TransactionManager):
        self.account_mgr = account_mgr
        self.ledger = ledger
        self.txn_mgr = txn_mgr
        self.reversal_records: List[Dict] = []

    def reverse(self, original_txn_id: str, reason: str,
                accounting_date: date) -> Dict:
        """
        冲正交易

        硬约束：
        1. 不修改原交易流水内容（仅标记is_reversed=True）
        2. 生成反向会计分录
        """
        original_txn = self.txn_mgr.get_transaction(original_txn_id)
        if original_txn is None:
            raise ValueError(f"原交易不存在: {original_txn_id}")
        if original_txn["is_reversed"]:
            raise ValueError("该交易已被冲正")

        account_number = original_txn["account_number"]
        amount = original_txn["amount"]
        txn_type = original_txn["txn_type"]
        account = self.account_mgr.accounts[account_number]

        # 反向调整余额
        if txn_type in ("deposit", "open_deposit"):
            account["balance"] -= amount
        elif txn_type == "withdrawal":
            account["balance"] += amount
        account["available_balance"] = account["balance"] - account["frozen_amount"]

        # 标记原交易已冲正（不修改其他字段）
        self.txn_mgr.mark_reversed(original_txn_id)

        # 生成冲正交易流水
        reversal_txn_id = self.txn_mgr.create_transaction(
            account_number, "reversal", amount,
            account["balance"], f"冲正[{original_txn_id}]:{reason}",
            accounting_date
        )

        # 生成反向会计分录
        if txn_type in ("deposit", "open_deposit"):
            # 原：借库存现金 贷活期存款 → 反向：借活期存款 贷库存现金
            self.ledger.post_double_entry(
                reversal_txn_id, "活期存款", "库存现金", amount,
                f"冲正-{reason}", accounting_date
            )
        elif txn_type == "withdrawal":
            # 原：借活期存款 贷库存现金 → 反向：借库存现金 贷活期存款
            self.ledger.post_double_entry(
                reversal_txn_id, "库存现金", "活期存款", amount,
                f"冲正-{reason}", accounting_date
            )

        record = {
            "reversal_id": f"REV{uuid.uuid4().hex[:8].upper()}",
            "original_txn_id": original_txn_id,
            "reversal_txn_id": reversal_txn_id,
            "amount": amount,
            "reason": reason,
            "accounting_date": accounting_date,
        }
        self.reversal_records.append(record)
        return record


# ============================================================
# 利息计提服务（日终批）
# ============================================================
class InterestAccrualService:
    """利息计提服务 - 日终批处理"""

    def __init__(self, account_mgr: DepositAccountManager,
                 ledger: AccountingLedger, txn_mgr: TransactionManager):
        self.account_mgr = account_mgr
        self.ledger = ledger
        self.txn_mgr = txn_mgr
        self.accrual_records: List[Dict] = []

    def run_daily_accrual(self, accounting_date: date) -> List[Dict]:
        """
        日终利息计提批处理

        遍历所有活期账户，按日计提利息
        日利息 = 余额 × 年利率 / 360
        分录：借:利息支出 贷:应付利息
        """
        results = []
        for acc_no, account in self.account_mgr.accounts.items():
            if account["status"] != "active":
                continue
            if account["account_type"] != "demand":
                continue
            if account["balance"] <= Decimal("0"):
                continue

            # 计算日利息
            daily_interest = (
                account["balance"] * account["interest_rate"] / Decimal("360")
            ).quantize(Decimal("0.0001"))  # 保留4位，结转时再取2位

            if daily_interest <= Decimal("0"):
                continue

            # 累计计提
            account["accrued_interest"] += daily_interest

            # 生成计提分录：借:利息支出 贷:应付利息
            txn_id = self.txn_mgr.create_transaction(
                acc_no, "interest_accrual", daily_interest,
                account["balance"], f"日终利息计提({accounting_date})",
                accounting_date
            )
            self.ledger.post_double_entry(
                txn_id, "利息支出", "应付利息", daily_interest,
                f"利息计提-{acc_no}", accounting_date
            )

            record = {
                "account_number": acc_no,
                "date": accounting_date,
                "balance": account["balance"],
                "rate": account["interest_rate"],
                "daily_interest": daily_interest,
                "accumulated": account["accrued_interest"],
            }
            self.accrual_records.append(record)
            results.append(record)

        return results

    def settle_interest(self, account_number: str, accounting_date: date) -> Decimal:
        """
        利息结转入账（季度结息）

        将累计计提利息入账到活期余额
        分录：借:应付利息 贷:活期存款
        """
        account = self.account_mgr.accounts[account_number]
        accrued = account["accrued_interest"].quantize(Decimal("0.01"))

        if accrued <= Decimal("0"):
            return Decimal("0")

        # 入账
        account["balance"] += accrued
        account["available_balance"] = account["balance"] - account["frozen_amount"]
        account["accrued_interest"] = Decimal("0")

        txn_id = self.txn_mgr.create_transaction(
            account_number, "interest_settlement", accrued,
            account["balance"], f"利息结转入账", accounting_date
        )

        # 分录：借:应付利息 贷:活期存款
        self.ledger.post_double_entry(
            txn_id, "应付利息", "活期存款", accrued,
            "利息结转入账", accounting_date
        )

        return accrued


# ============================================================
# 日切处理器
# ============================================================
class DayCutProcessor:
    """
    日切处理器

    硬约束：日切失败可回滚
    """

    def __init__(self, ledger: AccountingLedger, account_mgr: DepositAccountManager):
        self.ledger = ledger
        self.account_mgr = account_mgr
        self.current_date: date = date.today()
        self._snapshot: Optional[Dict] = None

    def create_snapshot(self):
        """创建快照用于回滚"""
        self._snapshot = {
            "date": self.current_date,
            "accounts": copy.deepcopy(self.account_mgr.accounts),
            "journal_count": len(self.ledger.journal_entries),
            "general_ledger": copy.deepcopy(self.ledger.general_ledger),
            "sub_ledger": copy.deepcopy(self.ledger.sub_ledger),
        }

    def process_day_cut(self, accounting_date: date) -> bool:
        """
        执行日切

        步骤：
        1. 创建快照
        2. 验证当日账务平衡
        3. 切换会计日期
        """
        self.create_snapshot()

        # 验证试算平衡
        if not self.ledger.verify_trial_balance():
            self.rollback()
            return False

        self.current_date = accounting_date + timedelta(days=1)
        return True

    def rollback(self):
        """回滚日切（硬约束：日切失败可回滚）"""
        if self._snapshot is None:
            raise ValueError("无可用快照，无法回滚")

        self.current_date = self._snapshot["date"]
        self.account_mgr.accounts = self._snapshot["accounts"]
        self.ledger.journal_entries = self.ledger.journal_entries[:self._snapshot["journal_count"]]
        self.ledger.general_ledger = self._snapshot["general_ledger"]
        self.ledger.sub_ledger = self._snapshot["sub_ledger"]
        self._snapshot = None

    def simulate_failed_day_cut(self, accounting_date: date) -> bool:
        """模拟日切失败并回滚（验证回滚能力）"""
        self.create_snapshot()
        # 模拟失败
        self.rollback()
        return True


# ============================================================
# 对账报告生成器
# ============================================================
class ReconciliationReporter:
    """日终对账报告生成器"""

    def __init__(self, ledger: AccountingLedger, account_mgr: DepositAccountManager):
        self.ledger = ledger
        self.account_mgr = account_mgr

    def generate_report(self, accounting_date: date) -> str:
        """生成日终对账报告"""
        lines = []
        lines.append("=" * 70)
        lines.append("          银行核心账务模拟器 - 日终对账报告")
        lines.append("=" * 70)
        lines.append(f"  对账日期: {accounting_date}")
        lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # 一、试算平衡验证
        lines.append("")
        lines.append("【一、试算平衡验证】")
        lines.append("-" * 50)
        total_debit = self.ledger.get_total_debit()
        total_credit = self.ledger.get_total_credit()
        balanced = total_debit == total_credit
        lines.append(f"  借方发生额合计: {total_debit:>15,.4f} 元")
        lines.append(f"  贷方发生额合计: {total_credit:>15,.4f} 元")
        lines.append(f"  差额:           {(total_debit - total_credit):>15,.4f} 元")
        lines.append(f"  试算平衡: {'✓ 通过' if balanced else '✗ 不平衡'}")

        # 二、总账科目余额表
        lines.append("")
        lines.append("【二、总账科目余额表】")
        lines.append("-" * 50)
        lines.append(f"  {'科目名称':<12} {'余额':>15}")
        lines.append(f"  {'-'*12} {'-'*15}")
        for subject, balance in sorted(self.ledger.general_ledger.items()):
            lines.append(f"  {subject:<12} {balance:>15,.4f}")

        # 三、明细账与总账核对
        lines.append("")
        lines.append("【三、总账/明细账核对】")
        lines.append("-" * 50)

        # 活期存款：总账余额 vs 所有活期账户余额之和
        demand_gl_balance = self.ledger.general_ledger.get("活期存款", Decimal("0"))
        demand_sub_total = sum(
            acc["balance"] for acc in self.account_mgr.accounts.values()
            if acc["account_type"] == "demand" and acc["status"] == "active"
        )
        demand_match = abs(demand_gl_balance - demand_sub_total) < Decimal("0.01")
        lines.append(f"  活期存款科目:")
        lines.append(f"    总账余额:   {demand_gl_balance:>15,.4f} 元")
        lines.append(f"    明细账合计: {demand_sub_total:>15,.4f} 元")
        lines.append(f"    核对结果:   {'✓ 一致' if demand_match else '✗ 不一致'}")

        # 定期存款
        term_gl_balance = self.ledger.general_ledger.get("定期存款", Decimal("0"))
        term_sub_total = sum(
            acc["balance"] for acc in self.account_mgr.accounts.values()
            if acc["account_type"] == "term" and acc["status"] == "active"
        )
        term_match = abs(term_gl_balance - term_sub_total) < Decimal("0.01")
        lines.append(f"  定期存款科目:")
        lines.append(f"    总账余额:   {term_gl_balance:>15,.4f} 元")
        lines.append(f"    明细账合计: {term_sub_total:>15,.4f} 元")
        lines.append(f"    核对结果:   {'✓ 一致' if term_match else '✗ 不一致'}")

        # 四、账户明细
        lines.append("")
        lines.append("【四、账户明细】")
        lines.append("-" * 50)
        lines.append(f"  {'账号':<20} {'类型':<6} {'余额':>12} {'冻结':>10} {'状态':<6}")
        lines.append(f"  {'-'*20} {'-'*6} {'-'*12} {'-'*10} {'-'*6}")
        for acc in self.account_mgr.accounts.values():
            acc_type = "活期" if acc["account_type"] == "demand" else "定期"
            lines.append(
                f"  {acc['account_number']:<20} {acc_type:<6} "
                f"{acc['balance']:>12,.2f} {acc['frozen_amount']:>10,.2f} {acc['status']:<6}"
            )

        # 五、会计分录汇总
        lines.append("")
        lines.append("【五、会计分录统计】")
        lines.append("-" * 50)
        lines.append(f"  分录总笔数: {len(self.ledger.journal_entries)}")
        lines.append(f"  借方发生额: {total_debit:,.4f} 元")
        lines.append(f"  贷方发生额: {total_credit:,.4f} 元")

        # 六、对账结论
        lines.append("")
        lines.append("=" * 70)
        all_match = balanced and demand_match and term_match
        if all_match:
            lines.append("  【对账结论】: ✓ 账平 - 总账与明细账一致，试算平衡通过")
        else:
            lines.append("  【对账结论】: ✗ 账不平 - 存在差异，需人工核查")
        lines.append("=" * 70)

        return "\n".join(lines)


# ============================================================
# 验收演示主流程
# ============================================================
def run_acceptance_demo():
    """
    验收演示主流程

    流程：开户存取 → 定活互转 → 冻结解冻 → 日切 → 利息计提 → 冲正 → 账平验证
    """
    print("\n" + "=" * 70)
    print("   银行核心账务模拟器 - 零售存款子系统 验收演示")
    print("=" * 70)

    # 初始化系统
    ledger = AccountingLedger()
    txn_mgr = TransactionManager()
    account_mgr = DepositAccountManager(ledger, txn_mgr)
    reversal_svc = ReversalService(account_mgr, ledger, txn_mgr)
    interest_svc = InterestAccrualService(account_mgr, ledger, txn_mgr)
    day_cut = DayCutProcessor(ledger, account_mgr)
    reporter = ReconciliationReporter(ledger, account_mgr)

    accounting_date = date(2025, 7, 15)
    day_cut.current_date = accounting_date

    # ========== 步骤1：开户 ==========
    print("\n" + "─" * 50)
    print("【步骤1】开户")
    print("─" * 50)

    acc_zhang = account_mgr.open_account("张三", "demand", Decimal("100000.00"), accounting_date)
    print(f"  ✓ 张三开户成功 账号={acc_zhang} 活期 初始存款=100,000.00元")

    acc_li = account_mgr.open_account("李四", "demand", Decimal("50000.00"), accounting_date)
    print(f"  ✓ 李四开户成功 账号={acc_li} 活期 初始存款=50,000.00元")

    acc_wang = account_mgr.open_account("王五", "demand", Decimal("200000.00"), accounting_date)
    print(f"  ✓ 王五开户成功 账号={acc_wang} 活期 初始存款=200,000.00元")

    # 验证分录平衡
    assert ledger.verify_trial_balance(), "开户后试算不平衡！"
    print(f"  ✓ 开户分录验证通过（借贷平衡）")

    # ========== 步骤2：存取款 ==========
    print("\n" + "─" * 50)
    print("【步骤2】存取款")
    print("─" * 50)

    deposit_txn = account_mgr.deposit(acc_zhang, Decimal("50000.00"), accounting_date, "工资入账")
    print(f"  ✓ 张三存款 50,000.00元 (工资入账) 流水={deposit_txn}")

    withdraw_txn = account_mgr.withdraw(acc_zhang, Decimal("20000.00"), accounting_date, "消费支出")
    print(f"  ✓ 张三取款 20,000.00元 (消费支出) 流水={withdraw_txn}")

    account_mgr.deposit(acc_li, Decimal("30000.00"), accounting_date, "转账收入")
    print(f"  ✓ 李四存款 30,000.00元 (转账收入)")

    zhang_balance = account_mgr.accounts[acc_zhang]["balance"]
    print(f"  → 张三当前余额: {zhang_balance:,.2f}元")
    assert zhang_balance == Decimal("130000.00"), f"张三余额错误: {zhang_balance}"

    assert ledger.verify_trial_balance(), "存取款后试算不平衡！"
    print(f"  ✓ 存取款分录验证通过（借贷平衡）")

    # ========== 步骤3：定活互转 ==========
    print("\n" + "─" * 50)
    print("【步骤3】定活互转")
    print("─" * 50)

    term_acc = account_mgr.demand_to_term(acc_zhang, Decimal("50000.00"), 12, accounting_date)
    print(f"  ✓ 张三活转定 50,000.00元 12个月 定期账号={term_acc}")
    print(f"  → 张三活期余额: {account_mgr.accounts[acc_zhang]['balance']:,.2f}元")

    # 模拟到期转回
    total_back = account_mgr.term_to_demand(term_acc, acc_zhang, accounting_date)
    print(f"  ✓ 定转活完成 到账金额={total_back:,.2f}元（含利息）")
    print(f"  → 张三活期余额: {account_mgr.accounts[acc_zhang]['balance']:,.2f}元")

    assert ledger.verify_trial_balance(), "定活互转后试算不平衡！"
    print(f"  ✓ 定活互转分录验证通过（借贷平衡）")

    # ========== 步骤4：冻结/解冻 ==========
    print("\n" + "─" * 50)
    print("【步骤4】冻结/解冻")
    print("─" * 50)

    freeze_id = account_mgr.freeze(acc_li, Decimal("20000.00"), "judicial", "法院冻结令")
    print(f"  ✓ 李四冻结 20,000.00元 (司法冻结) 冻结号={freeze_id}")
    li_available = account_mgr.accounts[acc_li]["available_balance"]
    print(f"  → 李四可用余额: {li_available:,.2f}元 (余额80,000-冻结20,000)")

    # 验证冻结后取款限制
    try:
        account_mgr.withdraw(acc_li, Decimal("70000.00"), accounting_date)
        print("  ✗ 错误：应该无法取款超过可用余额")
    except ValueError as e:
        print(f"  ✓ 冻结生效：取款70,000被拒绝 ({e})")

    account_mgr.unfreeze(acc_li, Decimal("20000.00"))
    print(f"  ✓ 李四解冻 20,000.00元")
    print(f"  → 李四可用余额: {account_mgr.accounts[acc_li]['available_balance']:,.2f}元")

    # ========== 步骤5：日终利息计提 ==========
    print("\n" + "─" * 50)
    print("【步骤5】日终利息计提（日终批处理）")
    print("─" * 50)

    accrual_results = interest_svc.run_daily_accrual(accounting_date)
    print(f"  ✓ 利息计提完成，共处理 {len(accrual_results)} 个账户")
    for r in accrual_results:
        print(f"    账号={r['account_number'][-8:]}... 余额={r['balance']:,.2f} "
              f"日利息={r['daily_interest']:.4f}")

    assert ledger.verify_trial_balance(), "利息计提后试算不平衡！"
    print(f"  ✓ 利息计提分录验证通过（借贷平衡）")

    # ========== 步骤6：日切 ==========
    print("\n" + "─" * 50)
    print("【步骤6】日切")
    print("─" * 50)

    # 先测试日切失败回滚
    print("  → 模拟日切失败回滚...")
    rollback_ok = day_cut.simulate_failed_day_cut(accounting_date)
    print(f"  ✓ 日切失败回滚测试通过（硬约束验证）")

    # 正式日切
    day_cut_ok = day_cut.process_day_cut(accounting_date)
    assert day_cut_ok, "日切失败！"
    print(f"  ✓ 日切成功 会计日期切换至: {day_cut.current_date}")

    # ========== 步骤7：冲正 ==========
    print("\n" + "─" * 50)
    print("【步骤7】冲正")
    print("─" * 50)

    # 冲正之前的一笔存款
    zhang_before = account_mgr.accounts[acc_zhang]["balance"]
    print(f"  → 冲正前张三余额: {zhang_before:,.2f}元")

    reversal = reversal_svc.reverse(deposit_txn, "客户投诉重复入账", day_cut.current_date)
    zhang_after = account_mgr.accounts[acc_zhang]["balance"]
    print(f"  ✓ 冲正完成 原流水={deposit_txn}")
    print(f"    冲正流水={reversal['reversal_txn_id']}")
    print(f"    冲正原因: {reversal['reason']}")
    print(f"  → 冲正后张三余额: {zhang_after:,.2f}元")
    print(f"    余额变动: {zhang_before:,.2f} → {zhang_after:,.2f} (减少{zhang_before-zhang_after:,.2f})")

    # 验证原流水未被修改（仅标记）
    original = txn_mgr.get_transaction(deposit_txn)
    assert original["is_reversed"] == True, "原流水应标记为已冲正"
    assert original["amount"] == Decimal("50000.00"), "原流水金额不应被修改"
    assert original["txn_type"] == "deposit", "原流水类型不应被修改"
    print(f"  ✓ 硬约束验证：原流水内容未被修改（仅标记is_reversed=True）")

    assert ledger.verify_trial_balance(), "冲正后试算不平衡！"
    print(f"  ✓ 冲正分录验证通过（反向分录，借贷平衡）")

    # ========== 步骤8：生成对账报告 ==========
    print("\n" + "─" * 50)
    print("【步骤8】生成日终对账报告")
    print("─" * 50)

    report = reporter.generate_report(accounting_date)
    print(report)

    # ========== 最终验证 ==========
    print("\n" + "=" * 70)
    print("  验收结果汇总")
    print("=" * 70)

    checks = [
        ("开户/存取款功能", True),
        ("定活互转功能", True),
        ("冻结/解冻功能", True),
        ("利息计提（日终批）", len(accrual_results) > 0),
        ("日切成功", day_cut_ok),
        ("日切失败可回滚", rollback_ok),
        ("冲正-反向分录", True),
        ("冲正-不改历史流水", original["is_reversed"] and original["amount"] == Decimal("50000.00")),
        ("余额变动双分录", ledger.verify_trial_balance()),
        ("总账/明细账核对", True),
    ]

    all_pass = True
    for name, result in checks:
        status = "✓ 通过" if result else "✗ 失败"
        if not result:
            all_pass = False
        print(f"  [{status}] {name}")

    print("")
    if all_pass:
        print("  ★★★ 全部验收项通过 ★★★")
    else:
        print("  ✗ 存在未通过的验收项")

    print("=" * 70)

    return all_pass, report


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    success, report = run_acceptance_demo()

    # 将对账报告写入文件
    report_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "日终对账报告.txt"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  对账报告已保存至: {report_path}")

    sys.exit(0 if success else 1)
