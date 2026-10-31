"""Session-boundary state line for a host hook — the index summary, restated when it has decayed
(task 322).

MCP ``instructions`` carry the state line once, on ``initialize``. A long session outlives it, and a
compaction drops it outright, so an agent that started a multi-minute build goes on to guess at its
health — two field retros filed the running-build signal as a missing feature. This command
restates the same line at the boundaries where the first delivery has decayed:

- ``SessionStart`` (``startup`` / ``resume`` / ``clear`` / ``compact``) — the ``compact`` source is
  the post-compaction delivery;
- ``PreCompact``, and ``PostCompact`` where a host names that event.

No other occasion earns a line (R1.2 — 099 refused a third on the same ground).

**It lifts, never recomposes:** the line is ``get_index_status(...)["summary"]``, the value
``instructions._state()`` already lifts (316/319, R6.7), plus the one field that moves minute to
minute — a running build's live phase and the route to it.

**Silent unless it changes something:** no index, or an index that is ``current`` with no build
running, no full rebuild pending and no refresh refused (a missing adapter, 355; a recorded
refusal, 401), prints nothing.

**Version skew (348, 374).** The hook table passes ``--expect-version`` and ``--expect-contract`` —
the release and contract it was generated from. The adapter checkout is the third half: each
configured adapter is launched and read for its handshake (``adapter_skew``). Every half older than
the newest is named with its fix, in the order they must run, in one line.

**On screen (381).** SessionStart stdout reaches only the agent, so a line a person must act on —
version skew, a pending rebuild, a refused refresh (401) — goes out as
JSON: ``systemMessage`` for the developer, ``additionalContext`` carrying every line for the agent.
PreCompact keeps plain text.

**Cardinal rule:** always exits 0 and never builds, reparses or takes the build lock; any error,
broken stdin or unreadable index is silence. The host is never blocked.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from code_atlas import contract
from code_atlas.build_info import MARKETPLACE_REPO, REPOSITORY_GIT
from code_atlas.tokens import estimate_tokens

# 099's 150 is a file outline; this is one sentence plus a phase, so the cap is shorter (AC5).
TOKEN_BUDGET = 90

OCCASIONS = frozenset({"SessionStart", "PreCompact", "PostCompact"})
PREFIX = "code-atlas: "
EXPECT_FLAG = "--expect-version"
EXPECT_CONTRACT_FLAG = "--expect-contract"
PLUGIN_REMOVE = "`claude plugin marketplace remove code-atlas`"
CHECKOUT_UPGRADE = "`git pull` in its checkout, then reinstall its dependencies"
# The core was installed from the adapters' own checkout, then the checkout moved: `git pull`
# can leave it where it is, so the fix names the revision instead (418).
SAME_CHECKOUT_UPGRADE = (
    "{release} in the checkout the core was installed from, or reinstall the core from it"
)
SAME_CHECKOUT_REINSTALL = (
    "`uv tool install --reinstall --from <checkout> code-atlas`: the core was installed from "
    "this checkout at another revision"
)
# The whole-install line's steps, in the order they must run (374 Scope 2).
DISCONNECT_STEP = "disconnect the server (`/mcp`)"
CHECKOUT_STEP = "`git pull` the adapter checkout, reinstall its deps"
SAME_CHECKOUT_STEP = "{release} in the adapter checkout, or reinstall the core from it"
SAME_CHECKOUT_TOOL_STEP = "`uv tool install --reinstall --from <checkout> code-atlas`"
RECONNECT_STEP = "reconnect (`/mcp`) or restart"
UPGRADING_POINTER = "run the README's *Upgrading* steps in order"


def tool_step(release: str | None) -> str:
    """The tool reinstall at a release tag — `upgrade` never moves a pin — else the README (427)."""
    if release is None:
        return UPGRADING_POINTER
    return f"`uv tool install --force git+{REPOSITORY_GIT}@v{release}`"


def plugin_step(release: str | None) -> str:
    """The marketplace re-added at a release tag, which is what moves the plugin (427)."""
    if release is None:
        return UPGRADING_POINTER
    return (
        f"{PLUGIN_REMOVE} && `claude plugin marketplace add {MARKETPLACE_REPO}#v{release}` "
        "&& `claude plugin install code-atlas@code-atlas`"
    )


def _run(step: str) -> str:
    return step if step.startswith("run ") else f"run {step}"
SCREEN_EVENT = "SessionStart"
# The numeric fields of the build's progress line (build_or_update_index's writer).
PROGRESS_COUNTS = frozenset({"done", "total", "pid", "at"})


def _verbose(argv: list[str]) -> bool:
    if "--verbose" in argv or "-v" in argv:
        return True
    return os.environ.get("CA_STATE_VERBOSE", "").strip() in {"1", "true", "yes"}


def _note(message: str, *, verbose: bool) -> None:
    if verbose:
        print(f"code-atlas state: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _build_clause(phase: str | None) -> str:
    from code_atlas.tools.get_index_status import BUILD_PROGRESS_ROUTE

    live = f" ({phase})" if phase else ""
    return f" · a build is running{live} — `{BUILD_PROGRESS_ROUTE}` reads its live phase"


def checked_progress(line: str | None) -> str | None:
    """The build's progress line only when every token is one the build writes, else ``None`` (421).

    ``phase=`` names one of ``BUILD_PHASES``; the rest are counts, a pid and an epoch.
    """
    from code_atlas.indexer import BUILD_PHASES

    if not line:
        return None
    for token in line.split(" "):
        key, _, value = token.partition("=")
        if key == "phase" and value in BUILD_PHASES:
            continue
        if key not in PROGRESS_COUNTS or not (value.isascii() and value.isdigit()):
            return None
    return line


def _release(version: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return None


def skew_line(expected: str | None, installed: str | None = None) -> str | None:
    """One line when the hooks and the installed package are different releases, else ``None``."""
    from code_atlas.build_info import UNKNOWN_VERSION, package_version

    installed = package_version() if installed is None else installed
    if not expected or installed in (expected, UNKNOWN_VERSION):
        return None
    ahead, behind = _release(installed), _release(expected)
    # The older side is the one to move; an unparseable version names both routes.
    if ahead and behind:
        fix = _run(plugin_step(installed) if ahead > behind else tool_step(expected))
    else:
        fix = f"{_run(tool_step(expected))}, or {_run(plugin_step(installed))}"
    line = f"{PREFIX}hooks expect code-atlas {expected} but {installed} is installed — {fix}"
    if estimate_tokens(line) > TOKEN_BUDGET:
        line = line.replace(fix, UPGRADING_POINTER)
    return line


def _adapter_line(adapters: Mapping[str, int], fix: str) -> str:
    named = ", ".join(f"'{key}' speaks contract v{c}" for key, c in sorted(adapters.items()))
    core = contract.CONTRACT_VERSION
    return f"{PREFIX}adapter {named} but this core speaks v{core} — {_run(fix)}"


def _whole_line(
    lagging: list[tuple[str, str]],
    newest: str,
    *,
    adapters: str,
    windows: bool,
    tool_or_plugin: bool,
) -> str:
    """Every lagging half and its step in order; past the budget, the halves and the README."""
    steps = list(dict.fromkeys(step for _, step in lagging))  # two unknown releases: one pointer
    if tool_or_plugin:
        steps = ([DISCONNECT_STEP] if windows else []) + steps + [RECONNECT_STEP]
    numbered = " ".join(f"{n}. {step}" for n, step in enumerate(steps, 1))
    halves = ", ".join(half for half, _ in lagging)
    for tail in (numbered, UPGRADING_POINTER):
        line = f"{PREFIX}{halves} lag {newest} — {tail}"
        if estimate_tokens(line) <= TOKEN_BUDGET:
            return line
    # Still too long: the checkout half is counted, not listed.
    halves = ", ".join(adapters if half.startswith("adapter ") else half for half, _ in lagging)
    return f"{PREFIX}{halves} lag {newest} — {UPGRADING_POINTER}"


def install_line(
    *,
    installed: str,
    expected: str | None,
    expected_contract: int | None,
    adapters: Mapping[str, int | None],
    windows: bool,
    same_checkout: bool = False,
) -> str | None:
    """One line naming every half older than the newest — tool, plugin, adapter checkout — or
    ``None``. An adapter that could not answer is ``None``, never a skew."""
    core = contract.CONTRACT_VERSION
    release = "check out the core's release"
    if _release(installed):
        release = f"`git checkout v{installed}`"
    checkout_upgrade, checkout_step, tool_upgrade = CHECKOUT_UPGRADE, CHECKOUT_STEP, tool_step(None)
    tool_move = None
    if same_checkout:
        tool_move = SAME_CHECKOUT_TOOL_STEP
        checkout_upgrade = SAME_CHECKOUT_UPGRADE.format(release=release)
        checkout_step = SAME_CHECKOUT_STEP.format(release=release)
        tool_upgrade = SAME_CHECKOUT_REINSTALL
    known = {key: c for key, c in adapters.items() if c is not None}
    tool, plugin = _release(installed), (_release(expected) if expected else None)
    newest = max([core, *known.values(), *([expected_contract] if expected_contract else [])])
    tool_lags = core < newest or bool(tool and plugin and plugin > tool)
    plugin_lags = bool(tool and plugin and plugin < tool) or bool(
        expected_contract and expected_contract < newest
    )
    # The release to install is known only when the other half's release or contract leads.
    plugin_leads = bool(tool and plugin and plugin > tool) or bool(
        expected_contract and core < expected_contract
    )
    tool_leads = bool(tool and plugin and plugin < tool) or bool(
        expected_contract and expected_contract < core
    )
    behind = {key: c for key, c in known.items() if c < newest}
    ahead = {key: c for key, c in known.items() if c > core}
    if not behind and not ahead and not (windows and tool_lags):
        return skew_line(expected, installed)  # tool and plugin alone: 348's line, byte for byte
    same_release = not (tool and plugin and plugin != tool)
    if same_release and not plugin_lags:
        if ahead and not behind and not windows:
            return _adapter_line(ahead, tool_upgrade)
        if behind and not tool_lags:
            return _adapter_line(behind, checkout_upgrade)
    lagging: list[tuple[str, str]] = []
    if tool_lags:
        move = tool_move or tool_step(expected if plugin_leads else None)
        lagging.append((f"tool {installed} (v{core})", move))
    if plugin_lags:
        move = plugin_step(installed if tool_leads else None)
        lagging.append((f"plugin {expected}", move))
    if behind:
        named = ", ".join(f"'{key}' v{c}" for key, c in sorted(behind.items()))
        lagging.append((f"adapter {named}", checkout_step))
    leaders = sorted(key for key, c in known.items() if c == newest)
    if newest > core and newest != expected_contract and leaders:
        newest_label = f"adapter {', '.join(repr(k) for k in leaders)} (v{newest})"
    else:
        parsed = [v for v in (installed, expected) if v and _release(v)]
        release = max(parsed, key=lambda v: _release(v) or (), default="")
        newest_label = f"{release} (v{newest})" if release else f"contract v{newest}"
    counted = f"{len(behind)} adapters"
    return _whole_line(
        lagging,
        newest_label,
        adapters=counted,
        windows=windows,
        tool_or_plugin=tool_lags or plugin_lags,
    )


def screen_lines(skew: str | None, line: str | None) -> list[str]:
    """The lines a person must act on: the install's, a pending rebuild (381 Scope 2), and a
    refresh the hook could not run (401)."""
    from code_atlas.tools.get_index_status import REBUILD_LEAD, REFRESH_REFUSED_LEAD

    acted = line and (line.startswith(PREFIX + REBUILD_LEAD) or REFRESH_REFUSED_LEAD in line)
    return [text for text in (skew, line if acted else None) if text]


def _flag(args: list[str], flag: str) -> str | None:
    if flag in args:
        index = args.index(flag)
        return args[index + 1] if index + 1 < len(args) else None
    return None


def _expected(args: list[str]) -> str | None:
    return _flag(args, EXPECT_FLAG)


def _expected_contract(args: list[str]) -> int | None:
    raw = _flag(args, EXPECT_CONTRACT_FLAG)
    return int(raw) if raw and raw.isdigit() else None


def _fit(summary: str, phase: str | None) -> str:
    """The summary is never cut; a phase too long for the budget is dropped, the route kept."""
    line = PREFIX + summary + _build_clause(phase)
    if phase and estimate_tokens(line) > TOKEN_BUDGET:
        line = PREFIX + summary + _build_clause(None)
    return line


def _install_skew(root: Path, expected: str | None, expected_contract: int | None) -> str | None:
    from code_atlas.adapter_skew import adapter_contracts, installed_from, same_checkout
    from code_atlas.build_info import package_version
    from code_atlas.config import load_config

    config = load_config(root)
    source = installed_from()
    return install_line(
        installed=package_version(),
        expected=expected,
        expected_contract=expected_contract,
        adapters=adapter_contracts(config),
        windows=os.name == "nt",
        same_checkout=any(same_checkout(cmd, source) for cmd in config.adapter_cmds.values()),
    )


def _indexed(root: Path) -> bool:
    from code_atlas.config import load_config

    db = load_config(root).db_path
    return db.is_file() and db.stat().st_size > 0


def index_settled(payload: Mapping[str, object], db: Path) -> bool:
    """``current``, no build running, no rebuild pending — the one notion both hooks read (377)."""
    from code_atlas.index_lock import build_in_progress
    from code_atlas.tools.get_index_status import (
        BUILD_IN_PROGRESS,
        COVERAGE_LOSS_PENDING,
        CURRENT,
        FULL_REBUILD_REQUIRED,
        REFRESH_REFUSED,
    )

    if bool(payload.get(BUILD_IN_PROGRESS)) or build_in_progress(db):
        return False
    # An older-era index at an unmoved HEAD still reads `current` — that one must speak (347),
    # and so must one whose refresh refuses for a missing adapter (355) or a broken one (401).
    pending = any(key in payload for key in (FULL_REBUILD_REQUIRED, COVERAGE_LOSS_PENDING))
    pending = pending or REFRESH_REFUSED in payload
    return payload.get("staleness") == CURRENT and not pending


def index_answers(root: Path) -> bool:
    """Whether "ask the index first" is good advice right now: an index exists and is settled."""
    from code_atlas.config import load_config
    from code_atlas.tools import get_index_status

    config = load_config(root)
    db = config.db_path
    if not db.is_file() or db.stat().st_size == 0:
        return False
    return index_settled(get_index_status.create(config, ())(), db)


def state_line(root: Path, *, verbose: bool = False) -> str | None:
    """The state line for this project, or ``None`` when silence is right."""
    from code_atlas.config import load_config
    from code_atlas.index_lock import build_in_progress, read_build_progress
    from code_atlas.tools import get_index_status
    from code_atlas.tools.get_index_status import BUILD_IN_PROGRESS

    config = load_config(root)
    db = config.db_path
    # An empty file would be initialised by opening it — that is a write, so it counts as absent.
    if not db.is_file() or db.stat().st_size == 0:
        _note("silent: no index", verbose=verbose)
        return None
    payload = get_index_status.create(config, ())()
    if index_settled(payload, db):
        _note("silent: index current, no build running", verbose=verbose)
        return None
    summary = str(payload["summary"])
    if not (bool(payload.get(BUILD_IN_PROGRESS)) or build_in_progress(db)):
        return PREFIX + summary
    return _fit(summary, checked_progress(read_build_progress(db)))


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``code-atlas-state`` / ``python -m code_atlas.hooks.state``."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        print(__doc__.strip(), file=sys.stderr)
        return 0
    verbose = _verbose(args)
    expected = _expected(args)
    skew: str | None = None
    event: object = None
    try:
        payload = json.load(sys.stdin)
        event = payload.get("hook_event_name") if isinstance(payload, dict) else None
        if event not in OCCASIONS:
            _note(f"silent: {event!r} is not a state occasion", verbose=verbose)
            return 0
        root = _project_root()
        if _indexed(root):
            skew = _install_skew(root, expected, _expected_contract(args))
        line = state_line(root, verbose=verbose)
    except Exception as error:
        # A broken state line must never break the session boundary it rides on.
        print(f"code-atlas state skipped: {type(error).__name__}: {error}", file=sys.stderr)
        line = None
    lines = [text for text in (skew, line) if text]
    screen = screen_lines(skew, line)
    if event == SCREEN_EVENT and screen:
        context = {"hookEventName": SCREEN_EVENT, "additionalContext": "\n".join(lines)}
        sent = {"systemMessage": "\n".join(screen), "hookSpecificOutput": context}
        print(json.dumps(sent, ensure_ascii=False))
        return 0
    for text in lines:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
