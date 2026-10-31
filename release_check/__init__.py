"""The plugin's release check — is a newer tagged release out? (task 405)

PLAN §19 re-opened: an install whose halves agree on an old release was told by nothing. A
release is a ``vX.Y.Z`` tag (381), so the newest one is read with ``git ls-remote --tags``. That is
a network call, so this lives **outside the core** (R4.1), the way ``onboarding_llm/`` does.

Two modes, one per ``SessionStart`` hook, so a session never waits on the network:

- ``--fetch <remote>`` (async): when the cached answer is older than a day, list the remote's tags
  and cache the newest release.
- ``--expect-version <X.Y.Z>`` (sync): read the cache only; when its release is newer than the
  plugin's own, say so on screen (``systemMessage``) and to the agent (``additionalContext``).

Both modes first load the project's config, so an index git tracks (420) keeps them silent (427).
The tag listing runs hardened (``gitutil``) from the cache directory, not the indexed repo.

**Cardinal rule:** exits 0 and prints nothing on stdout on any failure — offline, no ``git``, a
timeout, an unreadable cache. ``CA_RELEASE_CHECK=0`` turns both modes off.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from code_atlas import gitutil
from code_atlas.hooks.state import EXPECT_FLAG, PREFIX, UPGRADING_POINTER

FETCH_FLAG = "--fetch"
OPT_OUT = "CA_RELEASE_CHECK"
SCREEN_EVENT = "SessionStart"
CHECK_INTERVAL_S = 24 * 60 * 60
# The async hook's own timeout is 60 s; the listing gives up well inside it.
FETCH_TIMEOUT_S = 30
TAG = re.compile(r"refs/tags/v(\d+)\.(\d+)\.(\d+)$")


def cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "code-atlas" / "release.json"


def _release(version: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def newest_tag(listing: str) -> str | None:
    """The highest ``vX.Y.Z`` in ``git ls-remote --tags`` output, as ``X.Y.Z``."""
    found = [tuple(int(n) for n in m.groups()) for m in map(TAG.search, listing.splitlines()) if m]
    return ".".join(map(str, max(found))) if found else None


def _read_cache() -> dict[str, object] | None:
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def fetch(remote: str, *, now: float | None = None) -> str | None:
    """Refresh the cache once it is a day old: the newest release, or ``None`` if not refreshed."""
    now = time.time() if now is None else now
    cached = _read_cache()
    checked = cached.get("checked_at") if cached else None
    if isinstance(checked, int | float) and now - checked < CHECK_INTERVAL_S:
        return None
    # Record the attempt first, so an offline machine retries daily rather than every session.
    _write_cache({"checked_at": int(now), "latest": cached.get("latest") if cached else None})
    # 427: hardened, and from the cache directory, never the indexed repo's working tree.
    hardening = [part for setting in gitutil.HARDENED_CONFIG for part in ("-c", setting)]
    done = subprocess.run(
        ["git", *hardening, "ls-remote", "--tags", "--refs", remote],
        capture_output=True,
        text=True,
        timeout=FETCH_TIMEOUT_S,
        env=gitutil.git_env(),
        cwd=cache_path().parent,
        check=True,
    )
    latest = newest_tag(done.stdout)
    if latest is None:
        return None
    _write_cache({"checked_at": int(now), "latest": latest, "remote": remote})
    return latest


def _write_cache(record: dict[str, object]) -> None:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".tmp")
    partial.write_text(json.dumps(record), encoding="utf-8")
    partial.replace(path)


def release_line(expected: str) -> str | None:
    """The line naming a newer cached release, or ``None`` when the plugin is current."""
    cached = _read_cache()
    latest = cached.get("latest") if cached else None
    if not isinstance(latest, str):
        return None
    newer, mine = _release(latest), _release(expected)
    if newer is None or mine is None or newer <= mine:
        return None
    return f"{PREFIX}release {latest} is out, this plugin is {expected} - {UPGRADING_POINTER}"


def _flag(args: list[str], flag: str) -> str | None:
    if flag in args and args.index(flag) + 1 < len(args):
        return args[args.index(flag) + 1]
    return None


def _require_project_index() -> None:
    """Raise unless the project's index loads; git tracking it is refused here (420, 427)."""
    from code_atlas.config import load_config

    load_config(Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-release-check``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if os.environ.get(OPT_OUT, "").strip() in {"0", "false", "no"}:
        return 0
    try:
        _require_project_index()
        remote = _flag(args, FETCH_FLAG)
        if remote:
            fetch(remote)
            return 0
        expected = _flag(args, EXPECT_FLAG)
        payload = json.load(sys.stdin)
        if not expected or payload.get("hook_event_name") != SCREEN_EVENT:
            return 0
        line = release_line(expected)
    except Exception as error:
        # A failed check must never break the session start it rides on.
        print(f"code-atlas release check skipped: {type(error).__name__}", file=sys.stderr)
        return 0
    if line:
        context = {"hookEventName": SCREEN_EVENT, "additionalContext": line}
        print(json.dumps({"systemMessage": line, "hookSpecificOutput": context}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
