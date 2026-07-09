"""Falsification ledger: an executable, tamper-evident refutation record.

Public surface:
    Claim, Prediction, Observation, Mismatch, LedgerEntry, Ledger, RefutationError
"""

from .ledger import (
    SCOPE_DIMENSIONS,
    Claim,
    Ledger,
    LedgerEntry,
    Mismatch,
    Observation,
    Prediction,
    RefutationError,
    classify_falsifiability,
    classify_specificity,
    find_vague_terms,
)
from .symbolic import Checker, LogicalFormError, evaluate_logical_form

__all__ = [
    "SCOPE_DIMENSIONS",
    "Claim",
    "Ledger",
    "LedgerEntry",
    "Mismatch",
    "Observation",
    "Prediction",
    "RefutationError",
    "classify_falsifiability",
    "classify_specificity",
    "find_vague_terms",
    "Checker",
    "LogicalFormError",
    "evaluate_logical_form",
]
