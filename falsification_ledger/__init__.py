"""Falsification ledger: an executable, tamper-evident refutation record.

Public surface:
    protocol: Claim, Prediction, Observation, Mismatch, LedgerEntry, Ledger,
              RefutationError, Kernel
    guards:   SCOPE_DIMENSIONS, classify_falsifiability, classify_specificity,
              find_vague_terms
    symbolic: Checker, LogicalFormError, evaluate_logical_form
"""

from .ledger import (
    SCOPE_DIMENSIONS,
    Claim,
    Kernel,
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
    "Kernel",
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
