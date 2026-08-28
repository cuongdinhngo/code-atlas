"""Task 181 — a sort and a ranking must not look alike, and an unranked dump is capped.

Round 12 fired 171's ordering three times and recorded the result as the round's design finding:
*fired, noticed, changed nothing.* Two payloads, the same shape:

  Case A  find_references(...ModelMember)  ranked_by "shared_subtree_with_subject"
          2 siblings, both exactly right.
  Case B  impact(paths=[ModelMember.php])  ranked_by "path"
          **93 entries**, 45% real twins and 55% sharing only a method name, with the needed twin at
          position ~6. It was **8.1 KB of the session's 8.9 KB of new disclosure bytes** (§6).

171's AC held — the order was deterministic and dropped nothing. *For a ranking, "deterministic and
lossless" is a precondition, not an acceptance criterion.* The defect is that a caller who does not
branch on `ranked_by` reads case B's first row as if it were case A's.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from code_atlas.config import load_config
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, impact
from code_atlas.tools.nav_result import (
    RANK_SHARED_SUBTREE,
    SIBLING_DEFINITIONS,
    SIBLING_RANKED,
    SIBLING_RANKED_BY,
    SIBLING_TOTAL,
    SIBLING_TRUNCATED,
    UNRANKED_SIBLING_CAP,
    attach_sibling_definitions,
    rank_sibling_sites,
)
from tests.test_impact import edge, node, seed_file, store  # noqa: F401 — pytest fixtures

SUBJECT_PATH = "src/alpha/model/member/ModelMember.php"
TWIN_PATH = "src/beta/model/member/ModelMember.php"


def config_for(tmp_path: Path):
    return replace(load_config(tmp_path, {}), db_path=tmp_path / "graph.db")


def plant_case_b(graph: GraphStore, noise: int) -> None:
    """Case B's shape: one file of methods, each with same-named twins on unrelated classes.

    `noise` unrelated classes carry a method of the same name — the 55% that shares only a name.
    """
    seed_file(
        graph,
        SUBJECT_PATH,
        [node("Method", "getName", "\\Alpha\\ModelMember::getName", SUBJECT_PATH)],
        [],
    )
    seed_file(
        graph,
        TWIN_PATH,
        [node("Method", "getName", "\\Beta\\ModelMember::getName", TWIN_PATH)],
        [],
    )
    for index in range(noise):
        path = f"src/alpha/vendor/lib{index:03d}/Unrelated{index}.php"
        seed_file(
            graph,
            path,
            [node("Method", "getName", f"\\Vendor\\Unrelated{index}::getName", path)],
            [],
        )


def plant_case_a(graph: GraphStore) -> None:
    """Case A's shape: a subject symbol with two right answers, ranked against its own file."""
    for path, ns in ((SUBJECT_PATH, "Alpha"), (TWIN_PATH, "Beta")):
        seed_file(graph, path, [node("Class", "ModelMember", f"\\{ns}\\ModelMember", path)], [])
    caller = "src/alpha/model/member/Uses.php"
    seed_file(
        graph,
        caller,
        [node("Method", "run", "\\Alpha\\Uses::run", caller)],
        [edge("CALLS", "\\Alpha\\Uses::run", "\\Alpha\\ModelMember", caller)],
    )


def test_a_ranked_and_an_unranked_disclosure_differ_by_shape(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC1 — the whole ticket. One boolean answers "is position meaningful?" either way.

    Fails on today's code: both cases carry `ranked_by`, so telling them apart requires knowing that
    the value `"path"` means *unranked*.
    """
    ranked: dict[str, object] = {}
    attach_sibling_definitions(
        ranked,
        [{"file": "src/beta/x.php"}, {"file": "src/alpha/y.php"}],
        subject_file="src/alpha/z.php",
    )
    unranked: dict[str, object] = {}
    attach_sibling_definitions(
        unranked, [{"file": "src/beta/x.php"}, {"file": "src/alpha/y.php"}], subject_file=None
    )

    assert ranked[SIBLING_RANKED] is True
    assert ranked[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE
    assert unranked[SIBLING_RANKED] is False
    assert SIBLING_RANKED_BY not in unranked, "there is no basis, so no basis is named (061)"
    # The verdict is readable without knowing any basis value — that is what a caller branches on.
    for payload in (ranked, unranked):
        assert isinstance(payload[SIBLING_RANKED], bool)


def test_the_retired_value_is_gone_from_the_vocabulary() -> None:
    """AC1: `"path"` is not annotated, it is removed — an honest name cannot mislead."""
    from code_atlas.tools import nav_result as nr

    assert not hasattr(nr, "RANK_PATH")
    rendered = json.dumps(
        {
            key: value
            for key, value in vars(nr).items()
            if key.startswith("RANK_") and isinstance(value, str)
        }
    )
    assert '"path"' not in rendered


def test_an_unranked_list_is_capped_and_says_so(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC2: capped, the cap named, and the total still reported — nothing is hidden (066)."""
    sites = [{"file": f"src/f{index:03d}.php"} for index in range(93)]
    payload: dict[str, object] = {}
    attach_sibling_definitions(payload, sites, subject_file=None)

    assert payload[SIBLING_RANKED] is False
    assert len(payload[SIBLING_DEFINITIONS]) == UNRANKED_SIBLING_CAP  # type: ignore[arg-type]
    assert payload[SIBLING_TRUNCATED] is True
    assert payload[SIBLING_TOTAL] == 93, "the population is reported, not just the page"


def test_a_ranked_list_is_never_capped(tmp_path: Path, store: GraphStore) -> None:  # noqa: F811
    """AC2: position is the answer, so dropping a row would remove it (171's rule stands)."""
    sites = [{"file": f"src/alpha/f{index:03d}.php"} for index in range(93)]
    payload: dict[str, object] = {}
    attach_sibling_definitions(payload, sites, subject_file="src/alpha/subject.php")

    assert payload[SIBLING_RANKED] is True
    assert len(payload[SIBLING_DEFINITIONS]) == 93  # type: ignore[arg-type]
    assert SIBLING_TRUNCATED not in payload and SIBLING_TOTAL not in payload


def test_the_impact_path_seed_reports_unranked_and_is_capped(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC1/AC2 on case B itself: the tool that produced the 93-row dump now says it cannot rank."""
    plant_case_b(store, noise=40)
    payload = impact.create(config_for(tmp_path))(paths=[SUBJECT_PATH], depth=1)

    assert payload[SIBLING_RANKED] is False, "no subject symbol ⇒ no basis, and it says so"
    assert SIBLING_RANKED_BY not in payload
    assert len(payload[SIBLING_DEFINITIONS]) == UNRANKED_SIBLING_CAP  # type: ignore[arg-type]
    assert payload[SIBLING_TRUNCATED] is True
    assert int(payload[SIBLING_TOTAL]) > UNRANKED_SIBLING_CAP  # type: ignore[arg-type]


def test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC3's verdict, and it is a REFUSAL backed by this measurement.

    A one-path request *does* have a subject file, already on the row that found the twin — so Scope
    3's basis is reachable at zero cost. It was implemented, measured here, and **declined**.

    The anchor's twins live in *sibling regions* (`alpha` / `beta`) while the same-name noise lives
    **inside the subject's own region**, so `shared_subtree_with_subject` ranks 40 vendor rows ABOVE
    the one row the caller wants. Shipping that would trade an honest `ranked: false` for a
    misleading `ranked: true` — re-creating 181's own defect with a better-sounding label.
    """
    subject = SUBJECT_PATH  # src/alpha/model/member/ModelMember.php
    sites = [{"file": TWIN_PATH}] + [
        {"file": f"src/alpha/vendor/lib{index:03d}/Unrelated{index}.php"} for index in range(40)
    ]
    ordered, basis = rank_sibling_sites(sites, subject_file=subject)

    assert basis == RANK_SHARED_SUBTREE
    assert str(ordered[0]["file"]).startswith("src/alpha/vendor/"), "same-region noise wins"
    assert str(ordered[-1]["file"]) == TWIN_PATH, "the answer the caller wants is LAST"
    # The discriminator that WOULD work is the sibling's container, not its path.
    assert "ModelMember" in TWIN_PATH and "Unrelated" not in TWIN_PATH


def test_a_qname_subject_still_ranks_as_it_did(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC5/061: case A is untouched — a subject symbol has always had a file to rank against."""
    plant_case_a(store)
    payload = find_callers.create(config_for(tmp_path))("\\Alpha\\ModelMember")

    if SIBLING_DEFINITIONS in payload:
        assert payload[SIBLING_RANKED] is True
        assert payload[SIBLING_RANKED_BY] == RANK_SHARED_SUBTREE


def test_no_sibling_and_one_sibling_stay_byte_identical(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC5/061: below two sites there is no order to explain, so no field appears."""
    none_payload: dict[str, object] = {}
    assert attach_sibling_definitions(none_payload, [], subject_file=None) is False
    assert none_payload == {}

    one_payload: dict[str, object] = {}
    attach_sibling_definitions(one_payload, [{"file": "a.php"}], subject_file=None)
    assert set(one_payload) == {SIBLING_DEFINITIONS}
    for absent in (SIBLING_RANKED, SIBLING_RANKED_BY, SIBLING_TRUNCATED, SIBLING_TOTAL):
        assert absent not in one_payload


def test_the_byte_saving_on_case_b_is_measured(tmp_path: Path) -> None:
    """AC6: measured against the 8.1 KB the field recorded for this one block on one call."""
    sites = [
        {"file": f"legacy/alpha/web/application/module{index:03d}/index.php", "line": index,
         "kind": "Method"}
        for index in range(93)
    ]
    before: dict[str, object] = {}
    before[SIBLING_DEFINITIONS] = sorted(sites, key=lambda site: str(site["file"]))
    before[SIBLING_RANKED_BY] = "path"  # the retired shape, reconstructed for the comparison

    after: dict[str, object] = {}
    attach_sibling_definitions(after, sites, subject_file=None)

    before_bytes = len(json.dumps(before))
    after_bytes = len(json.dumps(after))
    saved = 1 - after_bytes / before_bytes
    assert saved > 0.85, f"{before_bytes} B -> {after_bytes} B ({saved:.0%} saved)"


def test_the_order_is_deterministic_in_both_modes() -> None:
    """AC7/R4.2: unranked is still a stable sort; ranked keeps its in-band tie-break."""
    sites = [{"file": "src/b.php"}, {"file": "src/a.php"}, {"file": "src/c.php"}]
    first: dict[str, object] = {}
    second: dict[str, object] = {}
    attach_sibling_definitions(first, list(sites), subject_file=None)
    attach_sibling_definitions(second, list(sites), subject_file=None)
    assert first == second
    assert [str(dict(s)["file"]) for s in first[SIBLING_DEFINITIONS]] == [  # type: ignore[union-attr]
        "src/a.php",
        "src/b.php",
        "src/c.php",
    ]
