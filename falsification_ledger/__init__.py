"""Falsification ledger: an executable, tamper-evident refutation record.

Public surface:
    protocol: Claim, Prediction, Observation, Mismatch, LedgerEntry, Ledger,
              RefutationError, Kernel
    guards:   SCOPE_DIMENSIONS, classify_falsifiability, classify_specificity,
              find_vague_terms
    symbolic: Checker, LogicalFormError, evaluate_logical_form
    audit:    merkle_root, merkle_proof, verify_proof, sign_root,
              verify_root_signature
    explorer: ClaimExplorer, diagnose, classify_residuals, Signature,
              Diagnosis, Exploration, CrossDomainPattern, PATTERNS
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
from .explorer import (
    PATTERNS,
    ClaimExplorer,
    CrossDomainPattern,
    Diagnosis,
    Exploration,
    Signature,
    classify_residuals,
    diagnose,
)
from .merkle import (
    merkle_proof,
    merkle_root,
    sign_root,
    verify_proof,
    verify_root_signature,
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
    "merkle_root",
    "merkle_proof",
    "verify_proof",
    "sign_root",
    "verify_root_signature",
    "ClaimExplorer",
    "diagnose",
    "classify_residuals",
    "Signature",
    "Diagnosis",
    "Exploration",
    "CrossDomainPattern",
    "PATTERNS",
]
