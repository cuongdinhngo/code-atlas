"""Task 212: the fourth escalation route, and the first that is about cost, not correctness.

`incremental_update` had exactly three routes to `full_build` and all three were correctness
arguments — an incomplete graph, a contract era that moved, a suffix that entered scope. Cost was
not on the list, so a delta touching a large fraction of the repo ran as a delta however much
slower than one full build it was. Measured on the anchor monorepo: 60.8 s fixed plus 0.135 s per
parsed file against a 550 s full build, so the crossover sits near 3,600 files (the task's
CROSSOVER MEASUREMENT block carries the method).

The fixtures set `CA_FULL_BUILD_CROSSOVER` to a small number so a two-file repo can cross it. That
is the knob doing its job, not a test-only path: the production default is asserted separately.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from code_atlas import contract
from code_atlas.config import DEFAULT_FULL_BUILD_CROSSOVER, load_config
from code_atlas.indexer import DELTA_TOO_LARGE, DELTA_TOO_LARGE_ROUTE, INCOMPLETE_INDEX
from code_atlas.store import BUILD_COMPLETE_KEY, BUILD_INCOMPLETE, CONTRACT_VERSION_KEY, GraphStore
from code_atlas.tools.build_or_update_index import create as build_tool

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"

ONE_ADAPTER = {"CA_WORKERS": "1", "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"])}


def _write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def _commit(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _config(root: Path, **over: object):
    env = {**ONE_ADAPTER, "CA_DB_PATH": str(root / ".code-atlas" / "graph.db")}
    return replace(load_config(root, env), **over)  # type: ignore[arg-type]


def _seeded(root: Path, files: int = 3) -> None:
    """A git repo of ``files`` indexed sources, fully built."""
    for index in range(files):
        _write(root, f"src/f{index}.aa", f"class Thing{index} {{}}\n")
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True, capture_output=True)
    _commit(root)
    build_tool(_config(root))(full=True)


def _touch(root: Path, files: int) -> None:
    """Change ``files`` indexed sources so the byte-hash tier cannot skip them, and commit."""
    for index in range(files):
        _write(root, f"src/f{index}.aa", f"class Thing{index} {{}}\n// edit {index}\n")
    _commit(root)


def test_a_delta_past_the_crossover_escalates_and_names_cost(tmp_path: Path) -> None:
    """Proving test (AC2): the fourth route fires, and the report says COST, not correctness.

    Observed red against pre-212 code, where a delta of any size ran as a delta and the payload
    carried no key at all — `mode` read `incremental` however much slower the route was.
    """
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=2)

    payload = build_tool(_config(tmp_path, full_build_crossover=2))(full=False)

    cost = payload[DELTA_TOO_LARGE]
    assert isinstance(cost, dict)
    assert cost["to_parse"] == 2, "the tier decides on the parse set, not on the git diff"
    assert cost["crossover"] == 2
    assert cost["escalated_to"] == "full"
    assert cost["route"] == DELTA_TOO_LARGE_ROUTE
    # The two numbers differ even in this fixture — 4 git-named paths, 2 files to parse — which is
    # exactly why the tier reads `to_parse` and why the report carries both (H1).
    assert cost["changed"] >= cost["to_parse"]
    assert payload["mode"] == "full", "an escalation must not be reported as an incremental"
    # AC2: distinguishable from the three correctness routes, which are absent here.
    for correctness in ("contract_change", "scope_change", "incomplete_index"):
        assert correctness not in payload


def test_a_delta_below_the_crossover_stays_a_delta(tmp_path: Path) -> None:
    """AC2's other side: the tier is a ceiling, not a new default. Byte-identical to today."""
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=2)

    payload = build_tool(_config(tmp_path, full_build_crossover=100))(full=False)

    assert DELTA_TOO_LARGE not in payload
    assert payload["mode"] == "incremental"


def test_a_correctness_escalation_takes_precedence_over_cost(tmp_path: Path) -> None:
    """AC7 / Scope 5: a correctness route outranks the cost tier — and there are TWO layers of it.

    The cost tier sits after the `hashing` phase, and all three correctness escalations are decided
    upstream of it, so the cost branch is never evaluated. A contract-era lag does not even reach
    `incremental_update`: 201 made the build tool **refuse** first, and name the in-band option. So
    the precedence this pins is the tool's refusal, with the cost key absent — the failure this
    guards against is a cost escalation masking a correctness answer, and it cannot happen at either
    layer.
    """
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=3)
    config = _config(tmp_path, full_build_crossover=1)
    with GraphStore(config.db_path) as store:
        store.set_meta(CONTRACT_VERSION_KEY, str(contract.CONTRACT_VERSION - 1))

    payload = build_tool(config)(full=False)

    assert payload["mode"] == "refused"
    assert payload["reason"] == "contract_rebuild_required"
    assert payload["performed"] is False
    assert DELTA_TOO_LARGE not in payload, "a cost tier must never mask a correctness answer"


def test_an_incomplete_index_outranks_the_cost_tier_too(tmp_path: Path) -> None:
    """AC7, the residual case: the challenger noted only the contract-era route had a COMBINED test.

    An incomplete index and an over-threshold delta hold at once. The incomplete-index route is
    decided before the `try` block the cost tier lives in, so it cannot be overtaken — but that is a
    structural argument until a fixture holds both true at the same time, which this does.
    """
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=3)
    config = _config(tmp_path, full_build_crossover=1)
    with GraphStore(config.db_path) as store:
        store.set_meta(BUILD_COMPLETE_KEY, BUILD_INCOMPLETE)

    payload = build_tool(config)(full=False)

    assert DELTA_TOO_LARGE not in payload, "a cost tier must never mask an incomplete index"
    assert payload["mode"] == "full"
    assert payload[INCOMPLETE_INDEX]["escalated_to"] == "full"


def test_the_crossover_is_its_own_knob_and_no_other_budget_moves_it(tmp_path: Path) -> None:
    """R2.3 / the 124 pattern: a named setting of its own, not a borrowed walk budget.

    `impact_max_nodes` and `orphans_max_nodes` are traversal ceilings for two tools; neither
    decides whether a build escalates. Changing them must not change this route.
    """
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=2)

    borrowed = _config(tmp_path, impact_max_nodes=1, orphans_max_nodes=1)
    assert borrowed.full_build_crossover == DEFAULT_FULL_BUILD_CROSSOVER
    payload = build_tool(borrowed)(full=False)
    assert DELTA_TOO_LARGE not in payload, "a walk budget must not decide the build route"


def test_the_tier_is_off_by_default_because_this_repo_has_no_crossover(tmp_path: Path) -> None:
    """R2.3 / AC1: the default is what the measurement supports, and it supports *disabled*.

    Measuring the anchor found the delta cheaper at every size it can reach — 213.6 s for 3,000
    changed files against a 550 s full build, with the slope collapsing to 0.0088 s/file once the
    resolve phase saturates. A non-zero default would escalate a ~220 s delta into a 550 s build,
    which is the tier making things slower. So it ships off, and a repo whose own numbers differ
    turns it on.
    """
    assert DEFAULT_FULL_BUILD_CROSSOVER == 0, (
        "0 is the disabled sentinel, and the default: config.py carries the measurement that "
        "justifies it. Move the number and the comment together, or neither"
    )
    _seeded(tmp_path, files=3)
    _touch(tmp_path, files=3)

    # Every file in the repo changed, and the default still does not escalate for cost.
    payload = build_tool(_config(tmp_path))(full=False)

    assert DELTA_TOO_LARGE not in payload
    assert payload["mode"] == "incremental"


def test_the_escalated_build_indexes_everything_the_delta_would_have_skipped(
    tmp_path: Path,
) -> None:
    """R4.2: whichever route ran, the graph is the same one a full build produces.

    The escalation is not a refusal — it runs the ordinary `full_build`, so a file the delta never
    looked at is indexed afterwards.
    """
    _seeded(tmp_path, files=3)
    _write(tmp_path, "src/late.aa", "class Late {}\n")
    _touch(tmp_path, files=2)

    config = _config(tmp_path, full_build_crossover=2)
    payload = build_tool(config)(full=False)

    assert payload[DELTA_TOO_LARGE]["escalated_to"] == "full"
    with GraphStore(config.db_path) as store:
        assert store.file_hash("src/late.aa") is not None, "the full build picked up the new file"
        assert len(store.file_paths()) == 4

    # The DISCRIMINATOR, and the assertion this test lacked: a file's presence proves nothing,
    # because the ordinary hash-gate would have picked `late.aa` up too. Only a real `full_build`
    # re-parses the files the delta had already hash-skipped, so the parse count is what separates
    # "escalated" from "silently carried on as a delta". Found by the ticket-blind challenger, which
    # replaced `raise _TooLarge` with `pass` and watched all six tests stay green.
    wrote = payload["wrote"]
    assert isinstance(wrote, dict)
    assert wrote["parsed"] == 4, (
        "a full build parses every collected file; a delta that swallowed its escalation would "
        f"parse only the changed ones, and got {wrote['parsed']}"
    )
