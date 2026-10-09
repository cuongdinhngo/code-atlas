"""Task 170 — the divergence check runs on every answer, and its verdict is legible.

164 froze `_LOADED_BUILD_ID` at import and round 11 verified that half **non-circularly** (`/proc` +
`stat` + `git reflog`, never the stamp). The other half never fired: `server_identity` sat behind an
unconditional `@lru_cache(maxsize=1)`, so the comparison ran **once** and a swap after the first
payload was structurally unreportable. Round 11 §0.a: for the last 12 minutes of that session the
checkout genuinely differed from the process and no payload said so — *"harmless here only
because the delta was a docs-only commit. The harmlessness was luck of the delta, not a property
of the design."*

And §12.c is the second half of the finding: *"a reader cannot distinguish 'no divergence detected'
from 'divergence not checked.'"* 061's omit-when-empty rule is right for a **value** and wrong for a
**verdict**.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from time import perf_counter

import pytest

from code_atlas import build_info
from code_atlas.tools import nav_result as nr


@pytest.fixture(autouse=True)
def clean_memo() -> Iterator[None]:
    """Reset before AND after: the memo is process-global; a patched state must not outlive it."""
    build_info.reset_identity_cache()
    yield
    build_info.reset_identity_cache()


def test_a_swap_after_the_first_answer_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 — the whole ticket. The first answer is clean; the disk then moves; the next says so.

    This fails on today's code: the `lru_cache` returns the first dict forever, so the second answer
    is byte-identical to the first no matter what the disk does.
    """
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: False)

    # State 1: the disk matches what the process loaded.
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: False)
    first = build_info.server_identity()
    assert first["stale_process"] is False
    assert first["build"] == "abcdef1"

    # State 2: a loaded module's content changed under the running process.
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "n3wc0de")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: True)
    second = build_info.server_identity()

    assert second["stale_process"] is True, "the swap must be reportable AFTER the first answer"
    assert second["build"] == "l0aded1", "the build still names the code the process loaded (164)"
    assert second["repo_head"] == "abcdef1"


def test_the_probe_is_what_notices_not_a_re_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: the content hash runs only when the cheap fingerprint moved, never per payload."""
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    hashed: list[int] = []

    def counting_hash() -> str:
        hashed.append(1)
        return "l0aded1"

    monkeypatch.setattr(build_info, "_content_build_id", counting_hash)
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: False)

    for _ in range(20):
        build_info.server_identity()
    assert len(hashed) == 1, "twenty answers, one hash walk"

    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: True)
    build_info.server_identity()
    assert len(hashed) == 2, "the fingerprint moved, so the hash re-ran exactly once"


def test_a_matching_payload_says_checked_not_nothing() -> None:
    """AC2 — §12.c's half: the matching case is a positive verdict, not an absence."""
    prov = build_info.server_provenance()
    assert "server_stale_process" in prov, "silence cannot be the clean answer (170)"
    assert prov["server_stale_process"] in (True, False)
    # `repo_head` is context for a divergence; it stays conditional (061).
    if prov["server_stale_process"] is False:
        assert "server_repo_head" not in prov


def test_both_cases_are_pinned_on_a_real_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: pinned for the matching AND the diverged case, on a payload a tool actually returns."""
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: False)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")

    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: False)
    clean = nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False)
    assert clean["server_stale_process"] is False
    assert "server_repo_head" not in clean

    monkeypatch.setattr(build_info, "_content_build_id", lambda: "n3wc0de")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: True)
    stale = nr.nav_result("Foo", [], detail_level="standard", index_root="/r", truncated=False)
    assert stale["server_stale_process"] is True
    assert stale["server_repo_head"] == "abcdef1"
    assert stale["server_build"] == "l0aded1"


def test_the_probe_state_is_never_part_of_the_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC6/R4.2: mtimes are probe state only — the same artifact must name the same build.

    Two hosts check out the same commit at different times, so their mtimes differ by construction.
    If a timestamp reached the id, a retro could not compare two quoted lines. Driven by forcing the
    probe to fire on every call, so the identity is recomputed and would carry a timestamp if it
    could.
    """
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: True)

    early = build_info.server_identity()
    late = build_info.server_identity()

    assert early == late, "identical content, recomputed twice, identical answer"
    rendered = json.dumps(early)
    assert "mtime" not in rendered
    for stamp in build_info._probe_state.values():
        assert str(stamp[0]) not in rendered, "no mtime reached the payload"


def test_the_probe_reads_the_modules_this_process_really_loaded() -> None:
    """The probe is not a stub: it registers this package's own loaded modules, with real stamps."""
    build_info._loaded_modules_changed()
    state = build_info._probe_state

    assert "code_atlas.build_info" in state
    assert "code_atlas.store" in state, "the probe covers every loaded module, not just its own"
    assert len(state) > 5, f"only {len(state)} modules registered — the probe is not probing"
    for mtime_ns, size in state.values():
        assert mtime_ns > 0 and size > 0


def test_a_newly_imported_module_is_not_a_divergence() -> None:
    """A lazily-imported module must not read as a swap, or the hash walk runs on every import."""
    build_info.reset_identity_cache()
    assert build_info._loaded_modules_changed() is False, "the first look registers, never reports"
    assert build_info._loaded_modules_changed() is False, "and nothing moved between the two"


def test_a_real_content_change_to_a_loaded_module_is_seen() -> None:
    """The probe's own falsifiability: a changed stamp for an already-seen module reports True."""
    build_info.reset_identity_cache()
    build_info._loaded_modules_changed()
    previous = build_info._probe_state["code_atlas.build_info"]
    build_info._probe_state["code_atlas.build_info"] = (previous[0] - 1, previous[1] + 1)

    assert build_info._loaded_modules_changed() is True
    assert build_info._loaded_modules_changed() is False, "reported once, then re-registered"


def test_a_vanished_module_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Naming the build must never raise — the rule `_capture_loaded_build_id` already follows."""
    real_stat = os.stat
    seen: list[int] = []

    def flaky_stat(path: object, *args: object, **kwargs: object) -> object:
        seen.append(1)
        if len(seen) == 2:
            raise OSError("vanished between the walk and the stat")
        return real_stat(path, *args, **kwargs)  # type: ignore[arg-type]

    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info.os, "stat", flaky_stat)
    build_info._loaded_modules_changed()
    assert len(build_info._probe_state) > 5, "the probe skipped the vanished file and kept going"


def test_the_wheel_path_still_names_a_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC5 (125): no checkout ⇒ the loaded content id, and now a verdict beside it."""
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    ident = build_info.server_identity()

    assert ident["version"]
    assert len(str(ident["build"])) == 7
    assert "stale_process" in ident, "the wheel path is checked too, and says so"


def test_the_dirty_axis_is_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC5: `+dirty` is orthogonal and unchanged — a dirty worktree that MATCHES is not stale."""
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: True)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: False)

    ident = build_info.server_identity()
    assert ident["build"] == "abcdef1" + build_info.DIRTY_SUFFIX
    assert ident["stale_process"] is False, "dirty is a worktree axis, not a process axis"


def test_the_added_per_call_cost_is_an_order_below_the_hash_walk() -> None:
    """AC3: a margin against the hash walk this replaces per payload.

    Measured with all 73 modules imported: probe **0.174 ms**, hash **1.73 ms** — 10x here, and
    ~36x against the 6.35 ms walk 164 recorded on the maintainer's host. The margin is asserted at
    4x rather than 10x because 10x is exactly where this host sits, and a guard on its own boundary
    fails for the wrong reason. An earlier draft swept `rglob("*.py")` and managed only ~1.9x, which
    is why the probe reads `sys.modules` — the working doc records that rejection.
    """
    build_info._loaded_modules_changed()

    started = perf_counter()
    for _ in range(500):
        build_info._loaded_modules_changed()
    probe_ms = (perf_counter() - started) / 500 * 1000

    started = perf_counter()
    for _ in range(5):
        build_info._content_build_id()
    hash_ms = (perf_counter() - started) / 5 * 1000

    # The margin is the guard, and it is machine-independent: both figures are measured here,
    # on this host. The absolute 0.5 ms ceiling that used to sit beside it failed on GitHub's
    # shared runner at 0.52-0.58 ms while the 4x margin held — a guard on its own boundary,
    # failing for the wrong reason, which this docstring already warned about.
    assert probe_ms * 4 < hash_ms, f"probe {probe_ms:.4f} ms vs hash {hash_ms:.4f} ms"

    started = perf_counter()
    for _ in range(500):
        build_info.server_provenance()
    per_call_ms = (perf_counter() - started) / 500 * 1000
    # The same margin, on the same subject: a stamped payload costs the probe, not the walk it
    # replaced. Asserted against `hash_ms` from this run for the reason above — the absolute 0.5 ms
    # ceiling here failed the runner at 0.60 ms with the walk still 5x away.
    assert per_call_ms * 4 < hash_ms, (
        f"{per_call_ms:.4f} ms per stamped payload vs hash {hash_ms:.4f} ms"
    )


def test_the_memo_is_one_entry_however_many_swaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """A live probe must not grow state per swap over a long-running process."""
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")
    monkeypatch.setattr(build_info, "_loaded_modules_changed", lambda: True)

    before = len(build_info._probe_state)
    for _ in range(50):
        build_info.server_identity()
    assert len(build_info._probe_state) == before, "one entry per module, not per swap"


def test_a_swap_before_the_second_answer_is_reported_by_the_real_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """374 AC4: the anchor's `server_stale_process: false` after `uv tool upgrade`.

    The tests above stub the probe, so none saw that the first identity left it unseeded: the second
    call seeded it with the swapped stamps and reported no change, then and forever after.
    """
    loaded = tmp_path / "loaded.py"
    loaded.write_text("x = 1\n", encoding="utf-8")
    module = type(sys)("code_atlas._swapped_by_an_upgrade")
    module.__file__ = str(loaded)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "l0aded1")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "l0aded1")

    assert build_info.server_identity()["stale_process"] is False  # the first payload
    loaded.write_text("x = 2  # the upgraded release\n", encoding="utf-8")
    monkeypatch.setattr(build_info, "_content_build_id", lambda: "n3wc0de")

    assert build_info.server_identity()["stale_process"] is True
    assert build_info.server_identity()["stale_process"] is True
