"""
对账批处理

在日终批处理中执行总账与明细账的核对，
检测差异并生成对账报告。如果不平则标记异常。
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.domain.models.reconciliation import ReconciliationDifference, ReconciliationResult
from src.config.accounting_rules import SubjectCode, accounting_rules
from src.repository.interfaces.account_repo import AccountRepository
from src.repository.interfaces.ledger_repo import LedgerRepository

logger = logging.getLogger(__name__)


class BalanceChecker:
    """
    余额核对器

    负责核对总账余额与明细账（分户账）余额是否一致。
    核对逻辑：总账某科目的期末余额 = 该科目下所有分户账余额之和
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        ledger_repository: LedgerRepository,
    ) -> None:
        """
        初始化余额核对器

        Args:
            account_repository: 账户仓储接口
            ledger_repository: 账本仓储接口
        """
        self._account_repo = account_repository
        self._ledger_repo = ledger_repository

    def check(self, accounting_date: date) -> ReconciliationResult:
        """
        执行总账/明细账核对

        对所有存款类科目进行核对：
        - 总账余额来自总账分录汇总
        - 明细账余额来自各账户余额汇总

        Args:
            accounting_date: 对账日期

        Returns:
            对账结果实体
        """
        logger.info(f"开始余额核对，对账日期: {accounting_date}")

        # 需要核对的存款科目列表
        deposit_subjects = [
            SubjectCode.DEMAND_DEPOSIT.value,
        ]

        result = ReconciliationResult(
            reconciliation_date=accounting_date,
        )

        # 获取所有账户用于计算明细账汇总
        all_accounts = self._account_repo.find_all()

        for subject_code in deposit_subjects:
            # 获取总账余额
            general_balance = self._ledger_repo.get_balance(subject_code, accounting_date)

            # 计算明细账余额（所有活期账户余额之和）
            sub_balance = Decimal("0.00")
            if subject_code == SubjectCode.DEMAND_DEPOSIT.value:
                from src.domain.models.account import AccountType
                for account in all_accounts:
                    if account.account_type == AccountType.DEMAND:
                        sub_balance += account.balance

            # 记录差异
            diff = ReconciliationDifference(
                subject_code=subject_code,
                general_ledger_amount=general_balance,
                sub_ledger_amount=sub_balance,
            )
            result.add_difference(diff)

            # 更新汇总
            result.general_ledger_total += general_balance
            result.sub_ledger_total += sub_balance

        logger.info(
            f"余额核对完成，总账合计: {result.general_ledger_total}，"
            f"明细账合计: {result.sub_ledger_total}，"
            f"是否平衡: {result.is_balanced}"
        )

        return result


class ReconciliationBatchProcessor:
    """
    对账批处理器

    在日终批处理中调用BalanceChecker进行总账/明细账核对，
    生成对账报告，如果不平则标记异常。
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        ledger_repository: LedgerRepository,
        batch_repository: Any = None,
    ) -> None:
        """
        初始化对账批处理器

        Args:
            account_repository: 账户仓储接口
            ledger_repository: 账本仓储接口
            batch_repository: 批次仓储接口（可选，用于记录对账结果）
        """
        self._account_repo = account_repository
        self._ledger_repo = ledger_repository
        self._batch_repo = batch_repository
        self._balance_checker = BalanceChecker(account_repository, ledger_repository)

    def process(self, accounting_date: date) -> Dict[str, Any]:
        """
        执行日终对账

        调用BalanceChecker进行总账/明细账核对，生成对账报告。
        如果发现不平衡则标记异常并记录差异明细。

        Args:
            accounting_date: 会计日期

        Returns:
            对账结果字典，包含：
            - reconciliation_date: 对账日期
            - is_balanced: 是否平衡
            - general_ledger_total: 总账余额汇总
            - sub_ledger_total: 明细账余额汇总
            - differences: 差异列表
            - report: 对账报告文本
            - status: 对账状态（balanced/unbalanced）
            - anomaly_flag: 是否标记异常

        Raises:
            RuntimeError: 对账过程中发生不可恢复的错误
        """
        logger.info(f"开始日终对账批处理，会计日期: {accounting_date}")

        try:
            # 执行余额核对
            recon_result = self._balance_checker.check(accounting_date)

            # 构建对账报告
            report = recon_result.summary()

            # 构建返回结果
            process_result: Dict[str, Any] = {
                "reconciliation_date": accounting_date,
                "is_balanced": recon_result.is_balanced,
                "general_ledger_total": recon_result.general_ledger_total,
                "sub_ledger_total": recon_result.sub_ledger_total,
                "differences": [
                    {
                        "subject_code": d.subject_code,
                        "general_amount": d.general_ledger_amount,
                        "sub_amount": d.sub_ledger_amount,
                        "difference": d.difference_amount,
                    }
                    for d in recon_result.differences
                ],
                "report": report,
                "status": "balanced" if recon_result.is_balanced else "unbalanced",
                "anomaly_flag": not recon_result.is_balanced,
            }

            # 如果不平衡，标记异常
            if not recon_result.is_balanced:
                logger.warning(
                    f"对账不平衡！会计日期: {accounting_date}，"
                    f"总账: {recon_result.general_ledger_total}，"
                    f"明细账: {recon_result.sub_ledger_total}，"
                    f"不平衡科目: {recon_result.unmatched_subjects()}"
                )
                process_result["unmatched_subjects"] = recon_result.unmatched_subjects()

            # 持久化对账结果
            if self._batch_repo:
                self._batch_repo.save({
                    "batch_id": f"RECON-{accounting_date.isoformat()}",
                    "batch_type": "RECONCILIATION",
                    "batch_date": accounting_date,
                    "status": "BALANCED" if recon_result.is_balanced else "UNBALANCED",
                    "report": report,
                })

            logger.info(
                f"日终对账批处理完成，状态: {process_result['status']}"
            )

            return process_result

        except Exception as e:
            logger.error(f"日终对账批处理失败: {str(e)}")
            raise RuntimeError(f"对账批处理失败: {str(e)}") from e
