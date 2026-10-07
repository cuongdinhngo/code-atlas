"""Is the caller in another checkout of this repository than the one the index was built at? (366)

A stdio server's root is fixed at launch, so only the client can say where its agent works: MCP
``roots``. ``CallerRoots`` asks for them on every call — the agent may move between checkouts, and
FastMCP never hands ``roots/list_changed`` to middleware — and the query guard labels any answer
about a commit the caller's checkout is not at. Same-checkout callers pay no git at all.
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

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.store import LAST_COMMIT_KEY, read_meta_readonly
from code_atlas.tools.nav_result import REASON_REF_MISMATCH

# None: the call did not come through MCP (a test, a hook); (): the client reports no roots.
CALLER_ROOTS: contextvars.ContextVar[tuple[Path, ...] | None] = contextvars.ContextVar(
    "caller_roots", default=None
)
REF_CHECK_FIELD = "ref_check"
REF_CHECK_NO_ROOTS = "client_reported_no_roots"
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
    """Expose the client's roots to each tool call; a session that timed out is not asked again."""

    def __init__(self) -> None:
        self._silent: weakref.WeakSet[Any] = weakref.WeakSet()

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        token = CALLER_ROOTS.set(await self._roots(context))
        try:
            return await call_next(context)
        finally:
            CALLER_ROOTS.reset(token)

    async def _roots(self, context: MiddlewareContext[Any]) -> tuple[Path, ...] | None:
        ctx = context.fastmcp_context
        if ctx is None:
            return None
        session = ctx.session
        if session in self._silent:
            return ()
        listed: list[Any] = []
        with anyio.move_on_after(ROOTS_TIMEOUT_S) as scope:
            try:
                listed = await ctx.list_roots()
            except Exception:  # noqa: BLE001 — a client without the capability raises at once
                listed = []
        if scope.cancelled_caught:
            self._silent.add(session)
        paths = (_path(str(root.uri)) for root in listed)
        return tuple(path for path in paths if path is not None)


def _path(uri: str) -> Path | None:
    """A ``file:`` URI as a local path — drive letters and UNC hosts included — else None."""
    parsed = urlparse(uri)
    if parsed.scheme != "file" or not parsed.path:
        return None
    local = url2pathname(parsed.path)
    if parsed.netloc and parsed.netloc != "localhost":
        local = f"//{parsed.netloc}{local}"
    return Path(local)


# Root path → (top level, shared git dir). A miss is not cached: a directory may become a checkout.
_CHECKOUTS: dict[Path, tuple[Path, Path]] = {}


def _checkout(path: Path) -> tuple[Path, Path] | None:
    key = path.resolve()
    found = _CHECKOUTS.get(key)
    if found is None:
        found = gitutil.checkout_identity(key)
        if found is not None:
            _CHECKOUTS[key] = found
    return found


def find_mismatch(config: Config, roots: tuple[Path, ...]) -> RefMismatch | None:
    """The first root that is another checkout of this repository, at a commit the index is not.

    A root that is the index root itself means the caller can see that checkout: no check. Git
    runs only past that test, so the common case costs nothing; a worktree caller pays one
    ``rev-parse`` per call, so a commit made there is seen at once.
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
        built = read_meta_readonly(config.db_path, LAST_COMMIT_KEY)
        head = gitutil.head_commit(theirs[0])
        if built is None or head is None or head == built:
            continue
        return RefMismatch(caller_root=str(theirs[0]), caller_commit=head, index_commit=built)
    return None


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
