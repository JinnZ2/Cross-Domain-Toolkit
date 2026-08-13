"""merkle.py -- audit certificates over a ledger's recorded history. stdlib only.

The hash chain makes history tamper-evident, but checking it costs the whole
ledger: to believe entry #4,317 you replay every entry before it. That is fine
for the ledger's owner and useless for a third party, who now needs the entire
record -- including rows that may be none of their business -- to verify one.

A Merkle tree fixes the asymmetry. Hash the entries pairwise up to a single
`root`, and any one entry can then be proved to belong to that root with a path
of `log2(n)` sibling hashes. An auditor holding only the root, the entry, and its
path can check membership without seeing anything else, and without trusting the
holder.

    root  = merkle_root(hashes)
    proof = merkle_proof(hashes, index)
    verify_proof(leaf, index, proof, root)   -> bool

This upgrades the ledger's claim from "trust us, the chain verifies" to "here is
a certificate, check it yourself." It does not add secrecy (the leaf hashes are
the ledger's own entry hashes) and it does not add non-repudiation -- see
`sign_root` for that boundary.

ODD NODES. A level with an odd count promotes its last node unchanged rather
than duplicating it. Duplication is the classic CVE-2012-2459 shape, where two
distinct trees collapse to one root; promotion has no such ambiguity.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import List, Optional, Sequence, Tuple

# A proof step: (sibling hash, is_the_sibling_on_the_left).
ProofStep = Tuple[str, bool]


def _pair(left: str, right: str) -> str:
    """Hash two child hashes into their parent."""
    return hashlib.sha256((left + right).encode("utf-8")).hexdigest()


def _levels(leaves: Sequence[str]) -> List[List[str]]:
    """Build every level of the tree, leaves first, root last."""
    if not leaves:
        return []
    levels = [list(leaves)]
    while len(levels[-1]) > 1:
        below = levels[-1]
        up: List[str] = []
        for i in range(0, len(below) - 1, 2):
            up.append(_pair(below[i], below[i + 1]))
        if len(below) % 2:            # odd tail: promote, never duplicate
            up.append(below[-1])
        levels.append(up)
    return levels


def merkle_root(leaves: Sequence[str]) -> Optional[str]:
    """The root committing to every leaf, or None for an empty sequence."""
    levels = _levels(leaves)
    return levels[-1][0] if levels else None


def merkle_proof(leaves: Sequence[str], index: int) -> List[ProofStep]:
    """The sibling path proving `leaves[index]` belongs to `merkle_root(leaves)`.

    Each step is (sibling_hash, sibling_is_left). A promoted odd node has no
    sibling at that level and contributes no step.
    """
    if not 0 <= index < len(leaves):
        raise IndexError(f"leaf index {index} out of range for {len(leaves)} leaves")
    proof: List[ProofStep] = []
    for level in _levels(leaves)[:-1]:      # every level below the root
        if index == len(level) - 1 and len(level) % 2:
            index //= 2                      # promoted unchanged; no sibling
            continue
        if index % 2:
            proof.append((level[index - 1], True))
        else:
            proof.append((level[index + 1], False))
        index //= 2
    return proof


def verify_proof(leaf: str, index: int, proof: Sequence[ProofStep],
                 root: str) -> bool:
    """Check a leaf against a root using only the sibling path.

    This is the auditor's side: it never sees the other entries, only hashes.
    """
    if index < 0:
        return False
    running = leaf
    for sibling, sibling_is_left in proof:
        running = (_pair(sibling, running) if sibling_is_left
                   else _pair(running, sibling))
    return hmac.compare_digest(running, root)


def sign_root(root: str, key: bytes) -> str:
    """HMAC-SHA256 over a root, for the non-repudiation boundary.

    The README's threat model is honest that the chain is tamper-*evident*, not
    tamper-*proof*: whoever can rewrite the file can recompute every hash. A
    signature over the root closes that only as far as the key is held by
    someone other than the author.

    stdlib gives us `hmac`, which is symmetric: a verifier needs the same key
    the signer used, so this proves authorship to a *counterparty*, not to the
    public. Asymmetric signing (ed25519), which would prove it to anyone, needs
    a dependency this toolkit does not take -- keep the key with the auditor, or
    reach for a real signing library outside the stdlib constraint.
    """
    return hmac.new(key, root.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_root_signature(root: str, signature: str, key: bytes) -> bool:
    """Constant-time check of a `sign_root` signature."""
    return hmac.compare_digest(sign_root(root, key), signature)
