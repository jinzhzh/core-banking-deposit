"""
会计分录模型兼容模块

为保持向后兼容，从 journal_entry 模块重新导出 JournalEntry 和 JournalEntryLine。
"""

from src.domain.models.journal_entry import JournalEntry, JournalEntryLine

__all__ = ["JournalEntry", "JournalEntryLine"]
