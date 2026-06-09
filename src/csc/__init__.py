"""CSC browser automation for vendor worker onboarding."""

from .automation import (
    CSCAutomation,
    CSCError,
    AuthenticationError,
    FormSubmissionError,
    WorkerInfo
)
from .spreadsheet import CSCSpreadsheetGenerator

__all__ = [
    "CSCAutomation",
    "CSCError",
    "AuthenticationError",
    "FormSubmissionError",
    "WorkerInfo",
    "CSCSpreadsheetGenerator"
]
