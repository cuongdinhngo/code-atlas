"""Is the caller in another checkout of this repository than the one the index was built at? (366)

A stdio server's root is fixed at launch, so only the client can say where its agent works: MCP
``roots``. ``CallerRoots`` reads them once per session and exposes them to the call; the query
guard then labels any answer about a commit the caller's checkout is not at.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import anyio
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.store import LAST_COMMIT_KEY, GraphStore
from code_atlas.tools.nav_result import REASON_REF_MISMATCH

# None: the call did not come through MCP (a test, a hook); (): the client reports no roots.
CALLER_ROOTS: contextvars.ContextVar[tuple[Path, ...] | None] = contextvars.ContextVar(
    "caller_roots", default=None
)
REF_CHECK_FIELD = "ref_check"
REF_CHECK_NO_ROOTS = "client_reported_no_roots"
REASON_AT_INDEX_FIELD = "reason_at_index"
ROUTE = "build an index inside that checkout (a per-worktree index, CA_DB_PATH under it)"
# A client that never answers roots/list must not hold a tool call hostage.
ROOTS_TIMEOUT_S = 5.0
_ROOTS_CHANGED = "notifications/roots/list_changed"


@dataclass(frozen=True, slots=True)
class RefMismatch:
    caller_root: str
    caller_commit: str
    index_commit: str


class CallerRoots(Middleware):
    """Read the client's roots once per session and expose them to each tool call."""

    def __init__(self) -> None:
        self._by_session: dict[int, tuple[Path, ...]] = {}

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        token = CALLER_ROOTS.set(await self._roots(context))
        try:
            return await call_next(context)
        finally:
            CALLER_ROOTS.reset(token)

    async def on_notification(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        if context.method == _ROOTS_CHANGED:
            self._by_session.clear()
        return await call_next(context)

    async def _roots(self, context: MiddlewareContext[Any]) -> tuple[Path, ...] | None:
        ctx = context.fastmcp_context
        if ctx is None:
            return None
        key = id(ctx.session)
        if key not in self._by_session:
            listed: list[Any] = []
            with anyio.move_on_after(ROOTS_TIMEOUT_S) as scope:
                try:
                    listed = await ctx.list_roots()
                except Exception:  # noqa: BLE001 — a client without the capability raises
                    listed = []
            if scope.cancelled_caught:
                return None
            paths = (_path(str(root.uri)) for root in listed)
            self._by_session[key] = tuple(path for path in paths if path is not None)
        return self._by_session[key]


def _path(uri: str) -> Path | None:
    parsed = urlparse(uri)
    return Path(unquote(parsed.path)) if parsed.scheme == "file" and parsed.path else None


# Root path → (top level, shared git dir), or None outside a repo: neither changes under a session.
_CHECKOUTS: dict[Path, tuple[Path, Path] | None] = {}


def _checkout(path: Path) -> tuple[Path, Path] | None:
    key = path.resolve()
    if key not in _CHECKOUTS:
        _CHECKOUTS[key] = gitutil.checkout_identity(key)
    return _CHECKOUTS[key]


def find_mismatch(config: Config, roots: tuple[Path, ...]) -> RefMismatch | None:
    """The first root that is another checkout of this repository, at a commit the index is not.

    A root that is the index root itself means the caller can see that checkout: no check. Git
    runs only past that test, so the common case (the agent works in the index root) costs nothing.
    """
    index_root = config.root.resolve()
    if any(root.resolve() == index_root for root in roots):
        return None
    mine = _checkout(index_root)
    if mine is None:
        return None
    for root in roots:
        theirs = _checkout(root)
        if theirs is None or theirs[1] != mine[1] or theirs[0] == mine[0]:
            continue
        built = _built_commit(config)
        head = gitutil.head_commit(theirs[0])
        if built is None or head is None or head == built:
            return None
        return RefMismatch(caller_root=str(theirs[0]), caller_commit=head, index_commit=built)
    return None


def _built_commit(config: Config) -> str | None:
    if not config.db_path.is_file():
        return None
    with GraphStore(config.db_path) as store:
        return store.get_meta(LAST_COMMIT_KEY)


def attach_ref_check(
    answer: dict[str, object], config: Config, *, status: bool
) -> dict[str, object]:
    """Label an answer about another commit than the caller's checkout; status also names the route.

    A navigation answer keeps its rows: ``reason`` becomes ``ref_mismatch`` and the reason it had
    at the index moves to ``reason_at_index``. No MCP context or a matching HEAD: unchanged (AC2).
    """
    roots = CALLER_ROOTS.get()
    if roots is None or not isinstance(answer, dict):
        return answer
    if not roots:
        if status:
            answer[REF_CHECK_FIELD] = REF_CHECK_NO_ROOTS
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
    else:
        if "reason" in answer:
            answer[REASON_AT_INDEX_FIELD] = answer["reason"]
        answer["reason"] = REASON_REF_MISMATCH
    answer["index_commit"] = found.index_commit
    answer["caller_commit"] = found.caller_commit
    answer["caller_root"] = found.caller_root
    return answer
