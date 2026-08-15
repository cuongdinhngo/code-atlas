"""One definition site for the token-budget proxy (tasks 061 / 099).

Used by the write-time signal's hard cap and by the tokens-to-answer benchmark. A second copy
would drift silently, and both callers compare against the same budget — so the estimator lives
here and neither re-implements it (R6.7).
"""

from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Deterministic ~4-chars-per-token proxy — NOT a real tokenizer.

    Applied identically to every caller, so a *budget* and a *ratio* are both meaningful without a
    model dependency. Swap in a real tokenizer here without changing any caller.
    """
    if not text:
        return 0
    return -(-len(text) // 4)  # ceil division
