"""The two arm rules the 2026-08-27 abort earned, held by a test instead of by a prose bullet.

That run bought one $5.58 granted cell in which all 22 code-atlas tools arrived as names without
schemas, `ToolSearch` was never called, and the session made 0 index calls in 68 — a native-tools
session wearing the granted arm's label. The protocol now refuses that cell, and refusing it is
arithmetic over a transcript, so it is tested here rather than trusted to a reader.

Nothing repo-identifying is involved: these are tool-call sequences, which is all `audit` reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.arm_preflight import (
    EXIT_DEFERRED,
    EXIT_OK,
    EXIT_VOID,
    classify,
    parse_transcript,
    probe_argv,
    status_from_transcript,
)

ATLAS = "mcp__code-atlas__find_callers"
STATUS = "mcp__code-atlas__get_index_status"


def _stream(*names: str) -> str:
    """A `--output-format stream-json` transcript carrying one `tool_use` per assistant line."""
    lines = []
    for name in names:
        block = {"type": "tool_use", "id": f"t{len(lines)}", "name": name, "input": {}}
        lines.append(json.dumps({"type": "assistant", "message": {"content": [block]}}))
    return "\n".join(lines)


def test_granted_cell_with_zero_index_calls_is_void() -> None:
    """The 2026-08-27 shape verbatim: a granted arm that never reached a tool is not a datapoint."""
    code, verdict = classify(["Grep", "Read", "Bash"], "granted")
    assert code == EXIT_VOID
    assert "VOID" in verdict


def test_tool_search_before_the_first_index_call_is_deferred_delivery() -> None:
    code, verdict = classify(["ToolSearch", ATLAS], "granted")
    assert code == EXIT_DEFERRED
    assert "DEFERRED DELIVERY" in verdict


def test_resident_schemas_pass() -> None:
    code, verdict = classify(["Read", ATLAS, ATLAS], "granted")
    assert code == EXIT_OK
    assert "granted arm live" in verdict


def test_tool_search_after_the_arm_is_already_live_does_not_demote_it() -> None:
    """Only a `ToolSearch` *preceding* the first index call says the schemas were absent."""
    code, _ = classify([ATLAS, "ToolSearch", ATLAS], "granted")
    assert code == EXIT_OK


@pytest.mark.parametrize("names", [[ATLAS], ["Grep", STATUS]])
def test_any_index_call_contaminates_the_denied_arm(names: list[str]) -> None:
    code, verdict = classify(names, "denied")
    assert code == EXIT_VOID
    assert "CONTAMINATED" in verdict


def test_denied_arm_with_native_tools_only_is_clean() -> None:
    code, verdict = classify(["Grep", "Read"], "denied")
    assert code == EXIT_OK
    assert "clean" in verdict


def test_parses_both_output_envelopes() -> None:
    """`--output-format json` is one object, `stream-json` is one per line; both are accepted."""
    assert parse_transcript(_stream("ToolSearch", ATLAS)) == ["ToolSearch", ATLAS]
    single = json.dumps({"result": [{"content": [{"type": "tool_use", "name": ATLAS}]}]})
    assert parse_transcript(single) == [ATLAS]
    assert parse_transcript("   ") == []


def test_status_is_recovered_from_the_stringified_tool_result() -> None:
    """The payload arrives as a JSON string inside `content`, which is where the cell's build is."""
    payload = json.dumps({"server_build": "66b5af2", "staleness": "current", "indexed": True})
    line = json.dumps({"type": "user", "message": {"content": [{"content": payload}]}})
    status = status_from_transcript(line)
    assert status is not None
    assert status["server_build"] == "66b5af2"
    assert status["staleness"] == "current"


def test_status_absent_is_none_not_a_guess() -> None:
    assert status_from_transcript(_stream("Grep")) is None


def test_uncoached_tool_search_then_index_is_reachable_not_deferred() -> None:
    """The 2026-09-19 triage's open question: coached, this is exit 1; uncoached, it is the pass."""
    names = ["Glob", "ToolSearch", ATLAS, "Read"]
    assert classify(names, "granted")[0] == EXIT_DEFERRED
    code, verdict = classify(names, "granted", coached=False)
    assert code == EXIT_OK
    assert "REACHABLE via" in verdict


def test_uncoached_zero_index_calls_is_the_verdict_that_blocks_the_run() -> None:
    """No coaching, no index call: deferred delivery really does cost the arm. Say it plainly."""
    code, verdict = classify(["Grep", "Read", "Read"], "granted", coached=False)
    assert code == EXIT_VOID
    assert "UNREACHABLE" in verdict


def test_uncoached_resident_schemas_report_how_the_arm_was_reached() -> None:
    """`REACHABLE with resident schemas` and `REACHABLE via ToolSearch` are different findings."""
    _, verdict = classify([ATLAS, "Read"], "granted", coached=False)
    assert "with resident schemas" in verdict


def test_append_system_prompt_is_opt_in_and_leaves_default_uncoached_argv_alone() -> None:
    """Harness contrast must not rewrite the default reachability probe into a coached one."""
    cfg = Path("granted.json")
    plain = probe_argv(cfg, model=None, uncoached=True)
    assert "--append-system-prompt" not in plain
    with_brief = probe_argv(cfg, model=None, uncoached=True, append_system_prompt="brief body")
    assert with_brief[with_brief.index("--append-system-prompt") + 1] == "brief body"
    # Same REACH_PROMPT either way — the flag adds context, it does not rename the tool.
    assert plain[2] == with_brief[2]


def test_a_held_out_question_replaces_the_prompt_and_runs_the_uncoached_harness() -> None:
    """#392's flaw: the only question asked was the sentence the fix copied into the brief."""
    cfg = Path("granted.json")
    argv = probe_argv(cfg, model=None, question="Which code decides what runs for a given job?")
    assert argv[2] == "Which code decides what runs for a given job?"
    # Held-out implies uncoached: read-only tools and the 30-turn budget, not the coached pair.
    assert argv[argv.index("--max-turns") + 1] == "30"
    assert "Grep" in argv and STATUS not in argv


def test_the_coached_delivery_probe_is_unchanged_when_no_question_is_given() -> None:
    """The delivery test still names its tool — held-out mode must not rewrite that arm."""
    argv = probe_argv(Path("granted.json"), model=None)
    assert "get_index_status" in argv[2]
    assert argv[argv.index("--max-turns") + 1] == "6"
