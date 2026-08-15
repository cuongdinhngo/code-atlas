"""Task 099 — the line that rides along with a file read, and the silence around it.

The field named three decisions made without calling code-atlas; all three wanted one line at the
moment of a ``Read`` or a ``Write``, and none wanted a tool call. §3 also named exactly where an
interruption *destroys* value, so the silence rule carries as many tests as the signal does — and
a positive-fire test keeps those negatives from passing vacuously (093-C3).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from code_atlas.hooks.signal import MIN_SYMBOLS, TOKEN_BUDGET, main, signal
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tokens import estimate_tokens
from tests.test_incremental import committed, config_for

# One file with enough symbols to earn a line — the field's case held 9.
WIDE = "# symbol: alpha\n# symbol: beta\n# symbol: gamma\n# symbol: delta\n# symbol: epsilon\n"
NARROW = "# symbol: only\n"


def _indexed(tmp_path: Path, files: dict[str, str]) -> None:
    committed(tmp_path, files)
    config = config_for(tmp_path)
    with GraphStore(config.db_path) as store:
        full_build(config, store)


def test_read_signal_names_the_symbols_within_the_budget(tmp_path: Path) -> None:
    """Proving (AC2): one call pins **both** bounds — ≤ TOKEN_BUDGET tokens and < 1 s."""
    files = {f"src/f{i:03d}.aa": WIDE for i in range(200)}
    _indexed(tmp_path, files)

    started = time.monotonic()
    line = signal(tmp_path, "Read", "src/f000.aa")
    elapsed = time.monotonic() - started

    assert line is not None
    assert estimate_tokens(line) <= TOKEN_BUDGET
    assert elapsed < 1.0, f"read signal took {elapsed:.3f}s"
    assert "src/f000.aa" in line
    assert "alpha:" in line


def test_a_wide_file_is_truncated_and_says_how_many_it_dropped(tmp_path: Path) -> None:
    """The cap is enforced, not documented (061) — an over-budget file loses symbols."""
    body = "".join(f"# symbol: symbol_with_a_long_name_{i:03d}\n" for i in range(60))
    _indexed(tmp_path, {"src/wide.aa": body})
    line = signal(tmp_path, "Read", "src/wide.aa")
    assert line is not None
    assert estimate_tokens(line) <= TOKEN_BUDGET
    assert "more" in line, "a truncated line must say how many symbols it did not show"


def test_write_signal_warns_that_a_new_path_is_untracked(tmp_path: Path) -> None:
    """AC3: the second signal, met at creation rather than an hour later (092)."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    line = signal(tmp_path, "Write", "src/brand_new.aa")
    assert line is not None
    assert "untracked" in line
    # 092 shipped `not_indexed`; the ticket's older text said `no_such_symbol`.
    assert "not_indexed" in line
    assert "no_such_symbol" not in line


def test_silent_on_a_tool_that_is_not_read_or_write(tmp_path: Path) -> None:
    """§3: probe output and ~40 CI shell results are where a line destroys value."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    assert signal(tmp_path, "Bash", "src/a.aa") is None
    assert signal(tmp_path, "Grep", "src/a.aa") is None


def test_silent_when_writing_a_file_that_already_exists(tmp_path: Path) -> None:
    """§3: 'every Write during authoring' — the create signal must not fire on an edit."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    assert signal(tmp_path, "Write", "src/a.aa") is None


def test_silent_on_a_file_with_too_few_symbols(tmp_path: Path) -> None:
    """A line for a two-symbol file is chrome; MIN_SYMBOLS is the floor."""
    _indexed(tmp_path, {"src/narrow.aa": NARROW})
    assert signal(tmp_path, "Read", "src/narrow.aa") is None


def test_silent_when_the_path_is_not_indexed_or_outside_the_project(tmp_path: Path) -> None:
    _indexed(tmp_path, {"src/a.aa": WIDE})
    assert signal(tmp_path, "Read", "src/never_indexed.aa") is None
    assert signal(tmp_path, "Read", "/etc/hosts") is None


def test_silent_when_there_is_no_index(tmp_path: Path) -> None:
    """The signal never builds — with no index it says nothing rather than making one (C3)."""
    committed(tmp_path, {"src/a.aa": WIDE})
    assert signal(tmp_path, "Read", "src/a.aa") is None
    assert not (tmp_path / ".code-atlas" / "graph.db").exists()


def test_the_silence_rule_is_not_vacuous(tmp_path: Path) -> None:
    """Prove the guard (093-C3): the negatives above mean nothing if nothing ever fires."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    assert signal(tmp_path, "Read", "src/a.aa") is not None
    assert signal(tmp_path, "Write", "src/fresh.aa") is not None


def test_a_drifted_file_still_answers_and_says_the_index_may_be_behind(tmp_path: Path) -> None:
    """C3: answer from the index as-is; never block on freshness, never rebuild."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    (tmp_path / "src" / "a.aa").write_text(WIDE + "# symbol: added\n", encoding="utf-8")
    line = signal(tmp_path, "Read", "src/a.aa")
    assert line is not None
    assert "index may be behind" in line


def test_hook_stdin_payload_and_always_exit_zero(tmp_path: Path) -> None:
    """The host calls it as a hook: tool_name + tool_input.file_path on stdin, exit 0 always."""
    _indexed(tmp_path, {"src/a.aa": WIDE})
    script = (
        "import json,sys;"
        "from code_atlas.hooks.signal import main;"
        "sys.exit(main([]))"
    )
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "src/a.aa"}})
    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(tmp_path), "PYTHONPATH": str(
            Path(__file__).resolve().parent.parent
        )},
    )
    assert done.returncode == 0
    assert "src/a.aa defines" in done.stdout


def test_malformed_stdin_is_silent_and_still_exits_zero(tmp_path: Path) -> None:
    """A broken signal must never break the read it rides along with."""
    assert main(["Nonsense", "src/a.aa"]) == 0
    assert MIN_SYMBOLS >= 1


def test_the_write_signal_is_a_pre_tool_use_signal(tmp_path: Path) -> None:
    """Create-vs-edit is decided by whether the path exists, so the event choice is not free.

    Wired as PostToolUse the file always exists by the time the hook runs, and the signal is silent
    by construction — which is correct behaviour for an edit and useless for a create. The README
    tells a host to wire ``Write`` at PreToolUse for exactly this reason.
    """
    _indexed(tmp_path, {"src/a.aa": WIDE})
    fresh = "src/made_by_the_agent.aa"
    assert signal(tmp_path, "Write", fresh) is not None  # PreToolUse: not on disk yet
    (tmp_path / fresh).write_text(WIDE, encoding="utf-8")
    assert signal(tmp_path, "Write", fresh) is None  # PostToolUse: indistinguishable from an edit


def test_a_wide_file_that_fits_nothing_still_reads_cleanly(tmp_path: Path) -> None:
    """The truncation line must never start with a stray comma."""
    body = "".join(f"# symbol: {'x' * 90}{i:03d}\n" for i in range(20))
    _indexed(tmp_path, {"src/huge.aa": body})
    line = signal(tmp_path, "Read", "src/huge.aa")
    assert line is not None
    assert ", ," not in line and "— , " not in line
    assert estimate_tokens(line) <= TOKEN_BUDGET
