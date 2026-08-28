"""Task 189 — a twin is ranked above same-name noise, and the basis says which fact decided it.

181 implemented the basis its Scope 3 delegated, **measured it, and declined to ship it**:

    subject : src/alpha/model/member/ModelMember.php
    siblings: src/beta/model/member/ModelMember.php        <- the answer the caller wants
              src/alpha/vendor/lib000/Unrelated0.php  ... x40  <- share only the method NAME
    shared_subtree_with_subject  ->  position 1 = vendor noise, position 41 = the answer

**Nearness is the wrong axis.** A twin lives in a SIBLING region (`alpha` / `beta`) while same-name
noise lives INSIDE the subject's own region, so subtree depth rewards exactly the wrong thing.

The discriminator is a fact about the **container**, and the one container fact the core can read
for free is *the file the container is declared in*: the anchor's twin is another
`ModelMember.php`, the noise is `Unrelated0.php`. It is checkable from the `file` field every
site already publishes, so the basis costs **no new payload field** (R5.5 satisfied at zero bytes).
The container-*qname* basis the ticket proposed is implemented below as a committed counterfactual,
with what it would have cost.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from code_atlas import contract
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, find_references, impact
from code_atlas.tools.nav_result import (
    RANK_SHARED_FILE_NAME,
    RANK_SHARED_SUBTREE,
    SIBLING_DEFINITIONS,
    SIBLING_RANKED,
    SIBLING_RANKED_BY,
    UNRANKED_SIBLING_CAP,
    rank_sibling_sites,
)
from tests.test_nav_tools import (  # noqa: F401 — pytest fixtures
    db_config,
    edge,
    node,
    seed_file,
    store,
)

SUBJECT_FILE = "src/alpha/model/member/ModelMember.php"
TWIN_FILE = "src/beta/model/member/ModelMember.php"
SUBJECT_METHOD = "\\Alpha\\ModelMember::getName"
TWIN_METHOD = "\\Beta\\ModelMember::getName"
NOISE = 40


def noise_file(index: int) -> str:
    """Same-name noise, exactly as round 12 found it: inside the subject's OWN region."""
    return f"src/alpha/vendor/lib{index:03d}/Unrelated{index}.php"


def plant_the_anchor_shape(graph: GraphStore, root: Path, *, noise: int = NOISE) -> None:
    """The region layout the ticket names: one twin in a sibling region, `noise` inside this one."""
    for path, ns in ((SUBJECT_FILE, "Alpha"), (TWIN_FILE, "Beta")):
        seed_file(
            graph, path,
            [node("Method", "getName", f"\\{ns}\\ModelMember::getName", path)],
            [], root=root,
        )
    for index in range(noise):
        path = noise_file(index)
        seed_file(
            graph, path,
            [node("Method", "getName", f"\\Vendor\\Unrelated{index}::getName", path)],
            [], root=root,
        )


def sites_of(paths: list[str]) -> list[dict[str, object]]:
    return [{"file": path, "line": 1, "kind": "Method"} for path in paths]


# ── AC1: the twin ranks first ────────────────────────────────────────────────────────────────────


def test_the_real_twin_is_position_one_on_the_anchors_layout() -> None:
    """AC1 — the whole ticket, on the fixture the measurement was taken from."""
    sites = sites_of([TWIN_FILE] + [noise_file(i) for i in range(NOISE)])
    ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)

    assert basis == RANK_SHARED_FILE_NAME
    assert str(ordered[0]["file"]) == TWIN_FILE, "the answer the caller wants is FIRST"
    assert all(str(row["file"]).startswith("src/alpha/vendor/") for row in ordered[1:])


def test_the_same_fixture_put_the_twin_LAST_under_the_subtree_basis() -> None:
    """AC1's falsifier, kept as a measurement rather than a claim.

    This is 181's committed counterfactual re-run: the ordering the old basis produced, computed
    here so the improvement is a diff between two orders rather than an assertion about one.
    """
    sites = sites_of([TWIN_FILE] + [noise_file(i) for i in range(NOISE)])
    old_order = sorted(
        sorted(sites, key=lambda s: str(s["file"])),
        key=lambda s: (-_depth(SUBJECT_FILE, str(s["file"])), str(s["file"])),
    )
    assert str(old_order[0]["file"]).startswith("src/alpha/vendor/"), "same-region noise won"
    assert str(old_order[-1]["file"]) == TWIN_FILE, "and the answer was LAST"

    new_order, _ = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)
    assert str(new_order[0]["file"]) != str(old_order[0]["file"])


def _depth(left: str, right: str) -> int:
    """The subtree depth 171 ranked on, re-implemented so the counterfactual is self-contained."""
    a = PurePosixPath(left).parent.parts
    b = PurePosixPath(right).parent.parts
    depth = 0
    for x, y in zip(a, b, strict=False):
        if x != y:
            break
        depth += 1
    return depth


def test_find_callers_ranks_the_twin_first_end_to_end(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC1 through the tool that actually has a member subject — round 12's case B question."""
    plant_the_anchor_shape(store, tmp_path)
    caller = "src/alpha/model/member/Uses.php"
    seed_file(
        store, caller,
        [node("Method", "run", "\\Alpha\\Uses::run", caller)],
        [edge("CALLS", "\\Alpha\\Uses::run", SUBJECT_METHOD, caller)],
        root=tmp_path,
    )
    payload = find_callers.create(db_config(tmp_path))(SUBJECT_METHOD)

    assert payload[SIBLING_RANKED] is True
    assert payload[SIBLING_RANKED_BY] == RANK_SHARED_FILE_NAME
    sites = payload[SIBLING_DEFINITIONS]
    assert str(sites[0]["file"]) == TWIN_FILE, sites[:3]  # type: ignore[index]


def test_find_references_inherits_the_same_order(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """R6.7: one ordering site, so the second consumer needed no edit of its own."""
    plant_the_anchor_shape(store, tmp_path)
    payload = find_references.create(db_config(tmp_path))(qname=SUBJECT_METHOD)

    assert payload[SIBLING_RANKED_BY] == RANK_SHARED_FILE_NAME
    assert str(payload[SIBLING_DEFINITIONS][0]["file"]) == TWIN_FILE  # type: ignore[index]


# ── AC2: the basis names the predicate that decided the order, and it is checkable ───────────────


def test_the_basis_is_re_evaluable_from_the_published_rows_alone() -> None:
    """AC2 / R5.5: a reader with the payload can recompute the band the order was built from.

    The predicate compares `PurePosixPath(site["file"]).name` against the subject's — and both
    values are already published (`sibling_definitions[].file` and the payload's own subject). No
    field was added to make the basis checkable, which is what makes option 2's byte cost moot.
    """
    sites = sites_of([TWIN_FILE] + [noise_file(i) for i in range(3)])
    ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)
    assert basis == RANK_SHARED_FILE_NAME

    wanted = PurePosixPath(SUBJECT_FILE).name
    bands = [PurePosixPath(str(row["file"])).name == wanted for row in ordered]
    assert bands == sorted(bands, reverse=True), "the published rows re-derive the order's bands"


def test_the_basis_is_named_only_when_the_predicate_split_the_list() -> None:
    """AC2 / 180's rule: the basis is the ONE predicate the order was decided by.

    Two degenerate shapes. **All sites match** — every sibling is another `ModelMember.php`, so
    the band is uniform and nearness alone decided the order; naming the file-name basis would
    misstate what ranked it. **No site matches** — the same, from the other side.
    """
    all_match = sites_of([TWIN_FILE, "src/other/region/ModelMember.php"])
    _, basis = rank_sibling_sites(all_match, subject_file=SUBJECT_FILE)
    assert basis == RANK_SHARED_SUBTREE, "uniform band ⇒ nearness decided it, and it says so"

    none_match = sites_of([noise_file(0), noise_file(1)])
    _, basis = rank_sibling_sites(none_match, subject_file=SUBJECT_FILE)
    assert basis == RANK_SHARED_SUBTREE


def test_no_tuned_number_decides_the_basis() -> None:
    """AC2 / 161 AC1: the choice is `0 < matched < total`, so it holds at every list size."""
    for noise in (1, 2, 7, 40, 93):
        sites = sites_of([TWIN_FILE] + [noise_file(i) for i in range(noise)])
        ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)
        assert basis == RANK_SHARED_FILE_NAME, noise
        assert str(ordered[0]["file"]) == TWIN_FILE, noise


# ── AC3: Scope 3's re-examination, and the container basis the ticket proposed ───────────────────


def test_the_subtree_basis_is_kept_because_it_answers_a_DIFFERENT_question() -> None:
    """AC3 — Scope 3's verdict, as a measurement.

    `shared_subtree_with_subject` is not wrong; it answers *"which of these definitions is nearest
    me"*, which is 165's own question — a simple-name reference binds locally. Here the two
    definitions of one class sit in mirrored regions with no noise (round 12's case A), the
    file-name predicate is uniform, and nearness is both the only axis and the right one.
    """
    sites = sites_of([TWIN_FILE, "src/alpha/model/member/other/ModelMember.php"])
    ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)
    assert basis == RANK_SHARED_SUBTREE
    assert str(ordered[0]["file"]) == "src/alpha/model/member/other/ModelMember.php", (
        "nearest first — the same region, one level down, beats the mirrored region"
    )


def test_the_recorded_limit_a_near_copy_is_not_told_from_a_twin() -> None:
    """AC3's residual, pinned so it is not rediscovered: uniform file names fall back to nearness.

    Forty vendor copies all *named* `ModelMember.php` would leave the band uniform, and nearness
    would put them above the mirrored twin. The basis then says `shared_subtree_with_subject`, so
    the payload never claims a twin ranking it did not do — but the caller is not helped either.
    """
    sites = sites_of([TWIN_FILE] + [
        f"src/alpha/vendor/lib{i:03d}/ModelMember.php" for i in range(NOISE)
    ])
    ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)
    assert basis == RANK_SHARED_SUBTREE, "no false claim of a twin ranking"
    assert str(ordered[0]["file"]).startswith("src/alpha/vendor/"), "and it is still unhelpful"


def test_the_container_qname_basis_would_also_work_and_what_it_would_cost() -> None:
    """AC3/AC4 — the ticket's own proposal, implemented as a counterfactual and rejected.

    It ranks correctly. It is rejected on two costs the file-name basis does not pay:

    1. **A container's trailing name is not reachable in the core.** `contract.split_qname` splits
       at `MEMBER_SEPARATOR`, which gives `\\Alpha\\ModelMember` — the *container qname*. Getting
       `ModelMember` out of it needs the container's own native separator, and naming that is
       R1.1-barred; the alternative is one node lookup per sibling, which the ticket's own cost
       constraint forbids. Below, the split is done with a PHP separator **in the test only**.
    2. **R5.5 would force publishing it.** `definition_sites` emits `{file, line, kind}`, so a
       reader could not check a container ranking — measured below.
    """
    subject_container, _ = contract.split_qname(SUBJECT_METHOD)
    assert subject_container == "\\Alpha\\ModelMember"
    wanted = subject_container.rsplit("\\", 1)[-1]  # the R1.1-barred step, test-only

    rows = [(TWIN_METHOD, TWIN_FILE)] + [
        (f"\\Vendor\\Unrelated{i}::getName", noise_file(i)) for i in range(NOISE)
    ]
    ranked = sorted(
        rows,
        key=lambda row: (
            str(contract.split_qname(row[0])[0]).rsplit("\\", 1)[-1] != wanted, row[1]
        ),
    )
    assert ranked[0][1] == TWIN_FILE, "the container basis ranks correctly too"

    without = [{"file": path, "line": 1, "kind": "Method"} for _, path in rows]
    with_container = [
        {**site, "container_name": str(contract.split_qname(q)[0]).rsplit("\\", 1)[-1]}
        for site, (q, _) in zip(without, rows, strict=True)
    ]
    delta = len(json.dumps(with_container)) - len(json.dumps(without))
    assert delta > 1_000, (
        f"publishing the container adds {delta} B on a 41-row ranked list — 181's rule forbids "
        "capping a ranked list, so this is the honest worst case against its capped ~1.05 KB"
    )


# ── AC4: byte cost, measured against 181's capped figure ─────────────────────────────────────────


def test_the_basis_adds_no_payload_field_and_six_bytes_of_string() -> None:
    """AC4: measured against 181's capped ~1.05 KB — the whole cost is **2 bytes** of basis NAME."""
    sites = sites_of([TWIN_FILE] + [noise_file(i) for i in range(NOISE)])
    ordered, basis = rank_sibling_sites(sites, subject_file=SUBJECT_FILE)

    new_payload = {SIBLING_RANKED: True, SIBLING_RANKED_BY: basis, SIBLING_DEFINITIONS: ordered}
    old_payload = {
        SIBLING_RANKED: True,
        SIBLING_RANKED_BY: RANK_SHARED_SUBTREE,
        SIBLING_DEFINITIONS: sorted(ordered, key=lambda s: str(s["file"])),
    }
    delta = len(json.dumps(new_payload)) - len(json.dumps(old_payload))
    assert delta == len(RANK_SHARED_FILE_NAME) - len(RANK_SHARED_SUBTREE) == 2
    assert set(new_payload) == set(old_payload), "no field added, so 061 has nothing to check"


# ── AC5: 061, R4.2, R1.1 ─────────────────────────────────────────────────────────────────────────


def test_two_rankings_of_the_same_sites_are_identical(tmp_path: Path) -> None:
    """AC5 / R4.2: deterministic, and stable under a shuffled input order."""
    paths = [TWIN_FILE] + [noise_file(i) for i in range(NOISE)]
    first, basis_a = rank_sibling_sites(sites_of(paths), subject_file=SUBJECT_FILE)
    second, basis_b = rank_sibling_sites(sites_of(list(reversed(paths))), subject_file=SUBJECT_FILE)
    assert [row["file"] for row in first] == [row["file"] for row in second]
    assert basis_a == basis_b


def test_no_subject_file_still_says_it_cannot_rank(
    tmp_path: Path, store: GraphStore  # noqa: F811
) -> None:
    """AC5 / 061: 181's unranked verdict and its cap are untouched — explicitly out of scope."""
    plant_the_anchor_shape(store, tmp_path)
    payload = impact.create(db_config(tmp_path))(paths=[SUBJECT_FILE], depth=1)
    assert payload[SIBLING_RANKED] is False
    assert SIBLING_RANKED_BY not in payload
    assert len(payload[SIBLING_DEFINITIONS]) == UNRANKED_SIBLING_CAP  # type: ignore[arg-type]


def test_the_basis_names_no_language_and_reads_no_suffix() -> None:
    """AC5 / R1.1: the predicate is a POSIX path basename compare — no suffix table, no language.

    Pinned on paths whose extensions differ from each other and from PHP's: the same-named files
    band together on the *whole* basename, so nothing here knows what a `.php` is.
    """
    sites = sites_of(["pkg/beta/Widget.mod", "pkg/alpha/vendor/Other.mod"])
    ordered, basis = rank_sibling_sites(sites, subject_file="pkg/alpha/Widget.mod")
    assert basis == RANK_SHARED_FILE_NAME
    assert str(ordered[0]["file"]) == "pkg/beta/Widget.mod"
