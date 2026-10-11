"""Per-symbol body fingerprint (task 384): the tokens a symbol spans, comments and layout dropped.

``extra.body_hash`` lets the core answer "did this body change since revision X" without diffing
files. Opaque: equal within this adapter, never compared across languages.
"""

from __future__ import annotations

import ast
import bisect
import hashlib
import io
import tokenize
from typing import Any

BODY_HASH = "body_hash"
HASH_CHARS = 16
# A File or Namespace spans unrelated symbols; a fingerprint of one is no symbol's body.
_UNHASHED_KINDS = frozenset({"File", "Namespace"})
_DROPPED = frozenset({tokenize.COMMENT, tokenize.NL, tokenize.ENCODING, tokenize.ENDMARKER})
# Indentation is structure in Python, so its tokens stay — as markers, never as their whitespace.
_MARKERS = {tokenize.INDENT: "\x01i", tokenize.DEDENT: "\x01d", tokenize.NEWLINE: "\x01n"}


def _decorated_starts(tree: ast.Module) -> dict[int, int]:
    """``def``/``class`` line → its first decorator's line: a decorator is part of the symbol."""
    starts: dict[int, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.decorator_list:
                starts[node.lineno] = min(d.lineno for d in node.decorator_list)
    return starts


def _qname_spans(
    nodes: list[dict[str, Any]], decorated: dict[int, int]
) -> dict[str, tuple[int, int]]:
    """One span per qname: a name defined twice in a file is stored once (keep-first), so its
    fingerprint covers every definition — an edit to the later one is still seen."""
    spans: dict[str, tuple[int, int]] = {}
    for node in nodes:
        start, end = node.get("line_start"), node.get("line_end")
        if not isinstance(start, int):
            continue
        end = end if isinstance(end, int) else start
        start = decorated.get(start, start)
        low, high = spans.get(node["qualified_name"], (start, end))
        spans[node["qualified_name"]] = (min(low, start), max(high, end))
    return spans


def stamp(text: str, nodes: list[dict[str, Any]], tree: ast.Module) -> None:
    """Add ``extra.body_hash`` to every symbol node, over the tokens on its lines."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        return  # ast accepted the file; a tokenizer refusal leaves every body `unknown`
    kept = [tok for tok in tokens if tok.type not in _DROPPED]
    rows = [tok.start[0] for tok in kept]
    pieces = [_MARKERS.get(tok.type, tok.string) for tok in kept]
    decorated = _decorated_starts(tree)
    spans = _qname_spans(nodes, decorated)
    for node in nodes:
        start, end = node.get("line_start"), node.get("line_end")
        if node.get("kind") in _UNHASHED_KINDS or not isinstance(start, int):
            continue
        start, end = spans[node["qualified_name"]]
        span = pieces[bisect.bisect_left(rows, start) : bisect.bisect_right(rows, end)]
        digest = hashlib.sha256("\x00".join(span).encode("utf-8")).hexdigest()[:HASH_CHARS]
        node["extra"] = {**(node.get("extra") or {}), BODY_HASH: digest}
