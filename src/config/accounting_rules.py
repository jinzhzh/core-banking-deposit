"""
会计规则配置模块

定义会计科目映射和借贷方向规则。
遵循银行会计准则，存款为负债类科目（贷方增加，借方减少）。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class SubjectCode(str, Enum):
    """会计科目代码"""

    # 资产类科目
    CASH = "1001"  # 库存现金
    CENTRAL_BANK_DEPOSIT = "1002"  # 存放中央银行款项
    INTERBANK_DEPOSIT = "1003"  # 存放同业款项
    LOAN_SHORT_TERM = "1301"  # 短期贷款
    LOAN_MEDIUM_TERM = "1302"  # 中期贷款
    LOAN_LONG_TERM = "1303"  # 长期贷款

    # 负债类科目 - 存款
    DEMAND_DEPOSIT = "2001"  # 活期存款
    FIXED_DEPOSIT_3M = "2002"  # 定期存款-三个月
    FIXED_DEPOSIT_6M = "2003"  # 定期存款-六个月
    FIXED_DEPOSIT_1Y = "2004"  # 定期存款-一年
    FIXED_DEPOSIT_2Y = "2005"  # 定期存款-二年
    FIXED_DEPOSIT_3Y = "2006"  # 定期存款-三年
    FIXED_DEPOSIT_5Y = "2007"  # 定期存款-五年

    # 负债类科目 - 应付利息
    INTEREST_PAYABLE_DEMAND = "2101"  # 应付活期存款利息
    INTEREST_PAYABLE_FIXED = "2102"  # 应付定期存款利息

    # 损益类科目
    INTEREST_EXPENSE_DEMAND = "6001"  # 活期存款利息支出
    INTEREST_EXPENSE_FIXED = "6002"  # 定期存款利息支出

    # 过渡科目
    INTERNAL_TRANSFER = "3001"  # 内部往来


class DebitCredit(str, Enum):
    """借贷方向"""

    DEBIT = "D"  # 借方
    CREDIT = "C"  # 贷方


@dataclass
class AccountingEntry:
    """会计分录模板"""

    subject_code: str  # 科目代码
    direction: DebitCredit  # 借贷方向
    description: str  # 摘要说明


@dataclass
class AccountingRuleItem:
    """单条会计规则（一笔交易对应的借贷分录）"""

    debit_subject: str  # 借方科目
    credit_subject: str  # 贷方科目
    description: str  # 规则说明


@dataclass
class AccountingRules:
    """会计规则配置"""

    # 科目名称映射
    subject_names: Dict[str, str] = field(default_factory=lambda: {
        "1001": "库存现金",
        "1002": "存放中央银行款项",
        "1003": "存放同业款项",
        "2001": "活期存款",
        "2002": "定期存款-三个月",
        "2003": "定期存款-六个月",
        "2004": "定期存款-一年",
        "2005": "定期存款-二年",
        "2006": "定期存款-三年",
        "2007": "定期存款-五年",
        "2101": "应付活期存款利息",
        "2102": "应付定期存款利息",
        "6001": "活期存款利息支出",
        "6002": "定期存款利息支出",
        "3001": "内部往来",
    })

    # 科目余额方向（True=借方余额，False=贷方余额）
    subject_balance_direction: Dict[str, bool] = field(default_factory=lambda: {
        "1001": True,   # 资产类-借方余额
        "1002": True,
        "1003": True,
        "2001": False,  # 负债类-贷方余额
        "2002": False,
        "2003": False,
        "2004": False,
        "2005": False,
        "2006": False,
        "2007": False,
        "2101": False,
        "2102": False,
        "6001": True,   # 损益类（费用）-借方余额
        "6002": True,
    })

    def get_deposit_rule(self, is_fixed: bool = False, term_months: int = 0) -> AccountingRuleItem:
        """
        获取存款交易的会计规则

        存款交易：借-库存现金/银行存款，贷-客户存款

        Args:
            is_fixed: 是否定期存款
            term_months: 定期存款期限（月）

        Returns:
            会计规则项
        """
        if is_fixed:
            credit_subject = self._get_fixed_deposit_subject(term_months)
            return AccountingRuleItem(
                debit_subject=SubjectCode.CASH.value,
                credit_subject=credit_subject,
                description=f"客户定期存款（{term_months}个月）",
            )
        return AccountingRuleItem(
            debit_subject=SubjectCode.CASH.value,
            credit_subject=SubjectCode.DEMAND_DEPOSIT.value,
            description="客户活期存款",
        )

    def get_withdrawal_rule(self, is_fixed: bool = False, term_months: int = 0) -> AccountingRuleItem:
        """
        获取取款交易的会计规则

        取款交易：借-客户存款，贷-库存现金/银行存款

        Args:
            is_fixed: 是否定期存款
            term_months: 定期存款期限（月）

        Returns:
            会计规则项
        """
        if is_fixed:
            debit_subject = self._get_fixed_deposit_subject(term_months)
            return AccountingRuleItem(
                debit_subject=debit_subject,
                credit_subject=SubjectCode.CASH.value,
                description=f"客户定期取款（{term_months}个月）",
            )
        return AccountingRuleItem(
            debit_subject=SubjectCode.DEMAND_DEPOSIT.value,
            credit_subject=SubjectCode.CASH.value,
            description="客户活期取款",
        )

    def get_interest_accrual_rule(self, is_fixed: bool = False) -> AccountingRuleItem:
        """
        获取计提利息的会计规则

        计提利息：借-利息支出，贷-应付利息

        Args:
            is_fixed: 是否定期存款

        Returns:
            会计规则项
        """
        if is_fixed:
            return AccountingRuleItem(
                debit_subject=SubjectCode.INTEREST_EXPENSE_FIXED.value,
                credit_subject=SubjectCode.INTEREST_PAYABLE_FIXED.value,
                description="计提定期存款利息",
            )
        return AccountingRuleItem(
            debit_subject=SubjectCode.INTEREST_EXPENSE_DEMAND.value,
            credit_subject=SubjectCode.INTEREST_PAYABLE_DEMAND.value,
            description="计提活期存款利息",
        )

    def get_interest_settlement_rule(self, is_fixed: bool = False) -> AccountingRuleItem:
        """
        获取结息的会计规则

        结息（利息入账）：借-应付利息，贷-客户存款

        Args:
            is_fixed: 是否定期存款

        Returns:
            会计规则项
        """
        if is_fixed:
            return AccountingRuleItem(
                debit_subject=SubjectCode.INTEREST_PAYABLE_FIXED.value,
                credit_subject=SubjectCode.DEMAND_DEPOSIT.value,
                description="定期存款结息转活期",
            )
        return AccountingRuleItem(
            debit_subject=SubjectCode.INTEREST_PAYABLE_DEMAND.value,
            credit_subject=SubjectCode.DEMAND_DEPOSIT.value,
            description="活期存款结息",
        )

    def get_transfer_rule(self) -> AccountingRuleItem:
        """
        获取转账交易的会计规则

        转账：借-付款方活期存款，贷-收款方活期存款

        Returns:
            会计规则项
        """
        return AccountingRuleItem(
            debit_subject=SubjectCode.DEMAND_DEPOSIT.value,
            credit_subject=SubjectCode.DEMAND_DEPOSIT.value,
            description="活期转账",
        )

    def _get_fixed_deposit_subject(self, term_months: int) -> str:
        """
        根据期限获取定期存款科目代码

        Args:
            term_months: 存期月数

        Returns:
            科目代码
        """
        term_subject_map = {
            3: SubjectCode.FIXED_DEPOSIT_3M.value,
            6: SubjectCode.FIXED_DEPOSIT_6M.value,
            12: SubjectCode.FIXED_DEPOSIT_1Y.value,
            24: SubjectCode.FIXED_DEPOSIT_2Y.value,
            36: SubjectCode.FIXED_DEPOSIT_3Y.value,
            60: SubjectCode.FIXED_DEPOSIT_5Y.value,
        }
        return term_subject_map.get(term_months, SubjectCode.FIXED_DEPOSIT_1Y.value)

    def get_subject_name(self, code: str) -> str:
        """
        获取科目名称

        Args:
            code: 科目代码

        Returns:
            科目名称
        """
        return self.subject_names.get(code, f"未知科目({code})")

    def is_debit_balance(self, code: str) -> bool:
        """
        判断科目是否为借方余额

        Args:
            code: 科目代码

        Returns:
            True为借方余额，False为贷方余额
        """
        return self.subject_balance_direction.get(code, True)


# 全局会计规则单例
accounting_rules = AccountingRules()
