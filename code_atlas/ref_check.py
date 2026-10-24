"""Is the caller in another checkout of this repository than the one the index was built at? (366)

A stdio server's root is fixed at launch, so only the client can say where its agent works: MCP
``roots``. ``CallerRoots`` asks for them on every call — the agent may move between checkouts, and
FastMCP never hands ``roots/list_changed`` to middleware — and the query guard labels any answer
about a commit the caller's checkout is not at. A same-checkout caller pays no git, only one
``roots/list`` round trip per call; a client that never declared ``roots`` is not asked.
"""

from __future__ import annotations

import contextvars
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import url2pathname

import anyio
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from mcp.types import ClientCapabilities, RootsCapability

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.store import LAST_COMMIT_KEY, read_meta_readonly
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_OK,
    REASON_REF_MISMATCH,
)

# An answer read through the caller's worktree (389) — named here, where the relabel skips it.
OVERLAY_FIELD = "overlay"
OVERLAY_WORKTREE = "worktree"
# None: the call did not come through MCP (a test, a hook); a str: why the check could not run.
CALLER_ROOTS: contextvars.ContextVar[tuple[Path, ...] | str | None] = contextvars.ContextVar(
    "caller_roots", default=None
)
REF_CHECK_FIELD = "ref_check"
REF_CHECK_NO_ROOTS = "client_reported_no_roots"
REF_CHECK_UNDECLARED = "client_declared_no_roots"
REF_CHECK_TIMED_OUT = "client_roots_timed_out"
REF_CHECK_FAILED = "client_roots_failed"
# Reasons about the rows, which a mismatch explains; any other reason (an input refusal) stays.
_RELABELLED = frozenset({REASON_OK, REASON_NO_MATCHES, REASON_NO_SUCH_SYMBOL, REASON_NOT_INDEXED})
REASON_AT_INDEX_FIELD = "reason_at_index"
ROUTE = "build an index inside that checkout (a per-worktree index, CA_DB_PATH under it)"
# A client that never answers roots/list must not hold a tool call hostage; once is enough.
ROOTS_TIMEOUT_S = 2.0


@dataclass(frozen=True, slots=True)
class RefMismatch:
    caller_root: str
    caller_commit: str
    index_commit: str


class CallerRoots(Middleware):
    """Expose the client's roots to each tool call.

    A session that timed out or failed is not asked again; one without ``roots`` is never asked.
    """

    def __init__(self) -> None:
        self._silent: weakref.WeakKeyDictionary[Any, str] = weakref.WeakKeyDictionary()

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        token = CALLER_ROOTS.set(await self._roots(context))
        try:
            return await call_next(context)
        finally:
            CALLER_ROOTS.reset(token)

    async def _roots(self, context: MiddlewareContext[Any]) -> tuple[Path, ...] | str | None:
        ctx = context.fastmcp_context
        if ctx is None:
            return None
        session = ctx.session
        if not session.check_client_capability(ClientCapabilities(roots=RootsCapability())):
            return REF_CHECK_UNDECLARED
        if session in self._silent:
            return self._silent[session]
        listed: list[Any] = []
        with anyio.move_on_after(ROOTS_TIMEOUT_S) as scope:
            try:
                listed = await ctx.list_roots()
            except Exception:  # noqa: BLE001 — e.g. method-not-found despite the declared capability
                self._silent[session] = REF_CHECK_FAILED
                return REF_CHECK_FAILED
        if scope.cancelled_caught:
            self._silent[session] = REF_CHECK_TIMED_OUT
            return REF_CHECK_TIMED_OUT
        paths = (_path(str(root.uri)) for root in listed)
        return tuple(path for path in paths if path is not None) or REF_CHECK_NO_ROOTS


def _path(uri: str) -> Path | None:
    """A ``file:`` URI as a local path — drive letters and UNC hosts included — else None."""
    parsed = urlparse(uri)
    if parsed.scheme != "file" or not parsed.path:
        return None
    local = url2pathname(parsed.path)
    if parsed.netloc and parsed.netloc != "localhost":
        local = f"//{parsed.netloc}{local}"
    return Path(local)


# Root path → (top level, shared git dir). A miss is not cached: a directory may become a checkout;
# an entry whose HEAD no longer reads (a removed worktree) is dropped.
_CHECKOUTS: dict[Path, tuple[Path, Path]] = {}


def _checkout(path: Path) -> tuple[Path, Path] | None:
    key = path.resolve()
    found = _CHECKOUTS.get(key)
    if found is None:
        found = gitutil.checkout_identity(key)
        if found is not None:
            _CHECKOUTS[key] = found
    return found


def other_checkout(config: Config, roots: tuple[Path, ...]) -> tuple[Path, str] | None:
    """The first root, in client order, that checks out this repository decides (366 X2).

    The index root among the roots: none, and no git. Another checkout of the same repository:
    its top level and HEAD. A later root never decides; one ``rev-parse`` per call.
    """
    index_root = config.root.resolve()
    if any(root.resolve() == index_root for root in roots):
        return None
    mine = _checkout(index_root)
    if mine is None:
        return None
    for root in roots:
        theirs = _checkout(root)
        if theirs is None or theirs[1] != mine[1]:
            continue
        if theirs[0] == mine[0]:
            return None
        head = gitutil.head_commit(theirs[0])
        if head is None:
            _CHECKOUTS.pop(root.resolve(), None)
            continue  # a removed worktree checks out nothing: the next root decides
        return theirs[0], head
    return None


def find_mismatch(config: Config, roots: tuple[Path, ...]) -> RefMismatch | None:
    """Another checkout of this repository at another commit than the built one (366)."""
    found = other_checkout(config, roots)
    if found is None:
        return None
    built = read_meta_readonly(config.db_path, LAST_COMMIT_KEY)
    if built is None or found[1] == built:
        return None
    return RefMismatch(caller_root=str(found[0]), caller_commit=found[1], index_commit=built)


def require_caller_root(config: Config, caller_root: str | None) -> Path | None:
    """A per-call ``caller_root`` (408), validated as a root is; a bad one fails loud (R5.3).

    It must be an absolute directory inside a checkout sharing the index root's git directory —
    the index checkout itself included. Anything else raises ``ValueError`` naming why, so a
    refused root never answers about the index checkout as if it were the caller's.
    """
    if caller_root is None:
        return None
    path = Path(caller_root)
    if not caller_root or not path.is_absolute():
        raise ValueError(f"caller_root must be an absolute path, got {caller_root!r}")
    if not path.is_dir():
        raise ValueError(f"caller_root {caller_root!r} is not a directory")
    if path.resolve() == config.root.resolve():
        return path
    mine = _checkout(config.root.resolve())
    if mine is None:
        raise ValueError(
            f"caller_root {caller_root!r} refused: the index root is not a git checkout, "
            "so no other checkout of it can be read"
        )
    theirs = _checkout(path)
    if theirs is None:
        raise ValueError(f"caller_root {caller_root!r} is not inside a git checkout")
    if theirs[1] != mine[1]:
        raise ValueError(
            f"caller_root {caller_root!r} is a checkout of another repository than the index root"
        )
    if theirs[0] != mine[0] and gitutil.head_commit(theirs[0]) is None:
        # A worktree whose HEAD no longer reads would answer about the index checkout instead.
        raise ValueError(f"caller_root {caller_root!r} is a checkout whose HEAD does not resolve")
    return path


def caller_checkout(config: Config, caller_root: Path | None = None) -> Path | None:
    """The caller's other checkout of this repository, from its roots or ``CA_CALLER_ROOT`` (389).

    ``CA_CALLER_ROOT`` answers only when the client reported no roots: a client that names its
    checkout is never overruled by the server's environment. A per-call ``caller_root`` (408)
    stands in for the roots of that one call.
    """
    roots = CALLER_ROOTS.get() if caller_root is None else (caller_root,)
    if isinstance(roots, tuple):
        found = other_checkout(config, roots)
    elif config.caller_root is not None:
        found = other_checkout(config, (config.caller_root,))
    else:
        return None
    return None if found is None else found[0]


def attach_ref_check(
    answer: dict[str, object],
    config: Config,
    *,
    status: bool,
    caller_root: Path | None = None,
) -> dict[str, object]:
    """Label an answer about another commit than the caller's checkout; status also names the route.

    A navigation answer keeps its rows: an ok, empty or not-found ``reason`` becomes
    ``ref_mismatch`` and moves to ``reason_at_index``; an input refusal keeps its reason. The commit
    fields are always added. No MCP context or a matching HEAD: unchanged (AC2). A validated
    per-call ``caller_root`` replaces the roots for this answer (408).
    """
    roots = CALLER_ROOTS.get() if caller_root is None else (caller_root,)
    if roots is None or not isinstance(answer, dict) or "error" in answer:
        return answer
    if answer.get(OVERLAY_FIELD) == OVERLAY_WORKTREE:
        return answer  # 389: the caller's own checkout answered, so nothing is about another ref
    if isinstance(roots, str):
        if status:
            answer[REF_CHECK_FIELD] = roots
        return answer
    found = find_mismatch(config, roots)
    if found is None:
        return answer
    if status:
        summary = answer.get("summary")
        if isinstance(summary, str):
            answer["summary"] = (
                f"{summary} — {REASON_REF_MISMATCH}: built at {found.index_commit[:7]}, "
                f"{found.caller_root} is at {found.caller_commit[:7]} — {ROUTE}"
            )
    elif answer.get("reason", REASON_OK) in _RELABELLED:
        if "reason" in answer:
            answer[REASON_AT_INDEX_FIELD] = answer["reason"]
        answer["reason"] = REASON_REF_MISMATCH
    answer["index_commit"] = found.index_commit
    answer["caller_commit"] = found.caller_commit
    answer["caller_root"] = found.caller_root
    return answer
