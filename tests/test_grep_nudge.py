"""Task 345 — a grep for a symbol gets one "ask code-atlas first" line, from adapter shapes.

The shapes are the adapters' own v13 handshakes, stamped into a real `graph.db` exactly as a build
stamps them, so the replay below exercises the store read the hook depends on.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from code_atlas.config import load_config
from code_atlas.hooks import nudge
from code_atlas.store import LAST_COMMIT_KEY, SYMBOL_SHAPES_BY_LANGUAGE_KEY, GraphStore
from tests.contract.adapter_registry import REGISTRY

NEEDS = [REGISTRY[name].cli.availability for name in ("php", "sql")]


def _git(root: Path, *command: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", *command],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _indexed(root: Path, *, current: bool = True) -> Path:
    """Shapes stamped as a build stamps them, on an index ``current`` at HEAD (377)."""
    shapes = {}
    for name in ("php", "sql"):
        meta = REGISTRY[name].cli.handshake()
        shapes[meta["name"]] = {"extensions": meta["extensions"], "shapes": meta["symbol_shapes"]}
    _git(root, "init", "-q")
    _git(root, "commit", "-q", "--allow-empty", "-m", "seed")
    with GraphStore(load_config(root).db_path) as store:
        store.set_meta(SYMBOL_SHAPES_BY_LANGUAGE_KEY, json.dumps(shapes, sort_keys=True))
        store.set_meta(LAST_COMMIT_KEY, _git(root, "rev-parse", "HEAD"))
    if not current:
        _git(root, "commit", "-q", "--allow-empty", "-m", "moved on")
    return root


def _bash(command: str) -> tuple[str, dict[str, object]]:
    return nudge.BASH_TOOL, {"command": command}


def _grep(pattern: str, **scope: str) -> tuple[str, dict[str, object]]:
    return nudge.GREP_TOOL, {"pattern": pattern, **scope}


pytestmark = [*NEEDS]


def test_anchor_shapes_fire_once_per_kind(tmp_path: Path) -> None:
    """AC1: each anchor shape fires once per kind; the same kinds again this session are silent."""
    root = _indexed(tmp_path)
    replay = [
        (_bash('grep -rn -e "->findUser(" src/'), "reference"),
        (_bash('grep -rn "findUser(" .'), "call"),
        (_bash('grep -rn "function findUser" src/'), "declaration"),
        (_bash("rg -n usp_GetUser --glob '*.sql'"), "name"),
    ]
    for (tool, tool_input), kind in replay:
        line = nudge.nudge(root, tool, tool_input, "s1")
        assert line and f"({kind})" in line, (tool_input, line)
    for (tool, tool_input), _kind in replay:
        assert nudge.nudge(root, tool, tool_input, "s1") is None
    assert nudge.nudge(root, *_bash('grep -rn -- "->findUser(" src/'), "s2")


def test_the_same_shapes_fire_unscoped_except_a_bare_name(tmp_path: Path) -> None:
    """AC1 "the same shapes unscoped": they fire — but a bare proc name alone is any literal word,
    so the literal-text clause wins and it stays silent unless scoped to .sql (W1)."""
    root = _indexed(tmp_path)
    assert "(reference)" in (nudge.nudge(root, *_bash('grep -rn "EXEC usp_GetUser" .'), "u") or "")
    assert "(declaration)" in (nudge.nudge(root, *_grep("CREATE PROCEDURE usp_GetUser"), "v") or "")
    assert nudge.nudge(root, *_bash("rg -n usp_GetUser"), "w") is None


@pytest.mark.parametrize(
    "call",
    [
        _bash('grep -rn "db_host" config/'),  # a config key
        _bash('grep -rn "# TODO" .'),  # a comment
        _grep("usp_GetUser", glob="*.php"),  # a proc name inside host-language source
        _bash("rg -n usp_GetUser -t php"),
        _bash('cat notes.md | grep "findUser("'),  # past a pipe: outside the parse surface
        _bash('find . -name "*.php" -exec grep -l "->x(" {} +'),
        _grep("->findUser(", glob="*.rb"),  # scoped to a language no adapter owns
    ],
)
def test_literal_and_out_of_surface_greps_never_fire(
    tmp_path: Path, call: tuple[str, dict[str, object]]
) -> None:
    assert nudge.nudge(_indexed(tmp_path), *call, "s1") is None


def test_a_bash_search_is_read_through_its_flags() -> None:
    """R4: the pattern is never a flag's value; globs, types and file paths scope the grep."""
    call = nudge.from_bash("grep -rn -e 'Foo::bar(' --include=*.php -A 3 src/Service.php")
    assert call == nudge.GrepCall("Foo::bar(", frozenset({".php"}))
    assert nudge.from_bash("git grep -n usp_X -- '*.sql'") == nudge.GrepCall(
        "usp_X", frozenset({".sql"})
    )
    assert nudge.from_bash("ls -la") is None


def test_each_firing_writes_its_log_line(tmp_path: Path) -> None:
    """AC4: one line per firing — time, session, adapter, kind — so a later run can count it."""
    root = _indexed(tmp_path)
    nudge.nudge(root, *_grep("->findUser("), "sess-9")
    lines = (root / ".code-atlas" / nudge.LOG_FILE).read_text(encoding="utf-8").splitlines()
    assert [line.split("\t")[1:] for line in lines] == [["sess-9", "php", "reference"]]


def test_silent_and_unwritten_without_an_index(tmp_path: Path) -> None:
    assert nudge.nudge(tmp_path, *_grep("->findUser("), "s1") is None
    assert not (tmp_path / ".code-atlas").exists()


def test_the_hook_emits_additional_context_and_always_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Plain stdout never reaches the model from PostToolUse; `additionalContext` does (spike)."""
    root = _indexed(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    payload = {"tool_name": "Grep", "tool_input": {"pattern": "->findUser("}, "session_id": "s"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert nudge.main([]) == 0
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    assert "ask the index first" in out["additionalContext"]
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert nudge.main([]) == 0


def test_a_real_build_stamps_the_shapes_the_nudge_reads(tmp_path: Path) -> None:
    """The build path end to end: handshake → `_record_meta` → graph.db → the hook's read."""
    import shlex
    import subprocess

    from code_atlas.tools.build_or_update_index import create as build_tool

    repo = Path(__file__).resolve().parent.parent
    (tmp_path / "app.py").write_text("def greet():\n    return 1\n", encoding="utf-8")
    for command in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "seed")):
        subprocess.run(
            ["git", "-c", "user.email=t@e", "-c", "user.name=t", *command],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
    adapter = shlex.join([sys.executable, str(repo / "adapters/python/index.py"), "--server"])
    config = load_config(tmp_path, {"CA_PYTHON_CMD": adapter, "CA_WORKERS": "1"})
    build_tool(config)(full=True)
    with GraphStore(config.db_path) as store:
        stamped = store.stamped_symbol_shapes()
    assert stamped["python"]["extensions"] == [".py"] and stamped["python"]["shapes"]
    line = nudge.nudge(tmp_path, *_bash("grep -rn 'def greet' ."), "s1")
    assert line and "(declaration)" in line


def test_silent_while_a_build_holds_the_lock_then_speaks(tmp_path: Path) -> None:
    """377 AC1 — red before 377: the nudge spoke over a running build."""
    from code_atlas.index_lock import try_index_write_lock

    root = _indexed(tmp_path)
    with try_index_write_lock(load_config(root).db_path) as held:
        assert held
        assert nudge.nudge(root, *_grep("->findUser("), "s1") is None
    line = nudge.nudge(root, *_grep("->findUser("), "s1")
    assert line and "(reference)" in line


def test_silent_against_a_behind_index(tmp_path: Path) -> None:
    """377 AC2 — red before 377: HEAD moved past the build and the nudge still sent agents there."""
    root = _indexed(tmp_path, current=False)
    assert nudge.nudge(root, *_grep("->findUser("), "s1") is None
    assert not (root / ".code-atlas" / nudge.STATE_FILE).exists(), "a silenced kind stays fresh"


def test_each_subagent_hears_the_nudge_once(tmp_path: Path) -> None:
    """377 AC3 — red before 377: the parent's nudge silenced every subagent of its session."""
    root = _indexed(tmp_path)
    grep = _grep("->findUser(")
    assert nudge.nudge(root, *grep, "s1")
    assert nudge.nudge(root, *grep, "s1", "agent-a")
    assert nudge.nudge(root, *grep, "s1", "agent-b")
    assert nudge.nudge(root, *grep, "s1", "agent-a") is None
    assert nudge.nudge(root, *grep, "s1") is None
    lines = (root / ".code-atlas" / nudge.LOG_FILE).read_text(encoding="utf-8").splitlines()
    assert [line.split("\t")[1] for line in lines] == ["s1", "s1/agent-a", "s1/agent-b"]


def test_the_state_file_drops_the_least_recent_key_not_the_first_by_name(tmp_path: Path) -> None:
    """377 review — red before: keys came back sorted, so a key naming first was the one dropped."""
    root = _indexed(tmp_path)
    grep = _grep("->findUser(")
    assert nudge.nudge(root, *grep, "s0")
    for n in range(nudge.KEPT_SESSIONS):
        assert nudge.nudge(root, *grep, "z", f"agent-{n:02d}")
    assert nudge.nudge(root, *grep, "a-last")
    assert nudge.nudge(root, *grep, "z", "agent-new")
    assert nudge.nudge(root, *grep, "a-last") is None, "the newest key survives whatever its name"
    assert nudge.nudge(root, *grep, "s0"), "the oldest key aged out"
    assert not list((root / ".code-atlas").glob("*.tmp")), "the atomic write leaves no temp file"


def test_a_payload_without_an_agent_keeps_todays_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """377 AC4 — no `agent_id` (or a non-string one) keys on the session alone, as before."""
    root = _indexed(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    for agent in (None, 7, ""):
        payload = {"tool_name": "Grep", "tool_input": {"pattern": "->findUser("}, "session_id": "s"}
        if agent is not None:
            payload["agent_id"] = agent
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
        assert nudge.main([]) == 0
    state = json.loads((root / ".code-atlas" / nudge.STATE_FILE).read_text(encoding="utf-8"))
    assert state == {"s": ["reference"]}
    assert capsys.readouterr().out.count("ask the index first") == 1
