"""211 — tour population is ranked but never grouped.

Proving test: community detection over the import graph groups files that share RESOLVED edges,
while HEURISTIC-only files stay separate (AC5), path vocabulary still wins when it fires (AC4),
and two runs over identical input produce byte-identical output (AC1).
"""

from __future__ import annotations

import json
from pathlib import Path

from code_atlas.onboarding.community import COMMUNITY_PREFIX, assign_communities
from code_atlas.onboarding.layers import UNCATEGORISED, assign_layers
from code_atlas.onboarding.metrics import compute_metrics
from code_atlas.onboarding.steps import build_steps
from code_atlas.onboarding.tour import ordered_stops
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_generate_onboarding import _out
from tests.test_nav_tools import db_config, edge, node, seed_file


def _tiers(
    resolved: list[tuple[str, str]],
    heuristic: list[tuple[str, str]] = (),
) -> list[tuple[str, str, str]]:
    return [(s, t, "RESOLVED") for s, t in resolved] + [(s, t, "HEURISTIC") for s, t in heuristic]


def test_two_runs_are_byte_identical() -> None:
    """AC1 — identical input yields identical output (R4.2)."""
    files = ["a.php", "b.php", "c.php", "d.php"]
    edges = _tiers([("a.php", "b.php"), ("b.php", "c.php")])
    first = assign_communities(files, edges)
    second = assign_communities(files, edges)
    assert dict(first) == dict(second)


def test_resolved_edges_form_one_community() -> None:
    """Files connected by RESOLVED edges share a label."""
    files = ["a.php", "b.php", "c.php"]
    edges = _tiers([("a.php", "b.php"), ("b.php", "c.php")])
    result = assign_communities(files, edges)
    # All three should share a label because a→b and b→c connects them.
    assert result["a.php"] == result["b.php"] == result["c.php"]


def test_heuristic_only_cluster_stays_separate(  # AC5
) -> None:
    """A cluster connected only by HEURISTIC edges is not merged with RESOLVED communities."""
    # x.php and y.php share a RESOLVED edge — they form community A.
    # z.php connects to x.php via HEURISTIC only — it should not join community A.
    files = ["x.php", "y.php", "z.php"]
    edges = _tiers(resolved=[("x.php", "y.php")], heuristic=[("x.php", "z.php")])
    result = assign_communities(files, edges)
    assert result["x.php"] == result["y.php"], "RESOLVED pair must share a community"
    assert result["z.php"] != result["x.php"], (
        "HEURISTIC-only connection must not join the RESOLVED community"
    )


def test_heuristic_connects_two_singletons() -> None:
    """Two files with no RESOLVED edges can be grouped by a HEURISTIC edge (pass 2)."""
    files = ["p.php", "q.php"]
    edges = _tiers(resolved=[], heuristic=[("p.php", "q.php")])
    result = assign_communities(files, edges)
    assert result["p.php"] == result["q.php"]


def test_community_label_is_path_derived_not_bare_integer(  # AC3
) -> None:
    """Community labels carry a path stem, never a bare integer."""
    files = ["app/Foo.php", "app/Bar.php"]
    edges = _tiers([("app/Foo.php", "app/Bar.php")])
    result = assign_communities(files, edges)
    label = result["app/Foo.php"]
    assert label.startswith(COMMUNITY_PREFIX), f"expected Community/ prefix, got {label!r}"
    suffix = label[len(COMMUNITY_PREFIX):]
    assert not suffix.isdigit(), f"label suffix must not be a bare integer; got {suffix!r}"


def test_community_is_named_after_the_most_connected_member() -> None:
    """Scope 1 — hub stem, not alphabetical first. Hub.php has degree 2; Alpha.php has 1."""
    files = ["z/Alpha.php", "z/Hub.php", "z/Other.php"]
    edges = _tiers([("z/Hub.php", "z/Alpha.php"), ("z/Hub.php", "z/Other.php")])
    result = assign_communities(files, edges)
    assert result["z/Alpha.php"] == f"{COMMUNITY_PREFIX}Hub"
    assert result["z/Hub.php"] == result["z/Other.php"] == result["z/Alpha.php"]


def test_two_communities_sharing_a_stem_keep_distinct_labels() -> None:
    """A mirrored tree gives two communities the same representative stem; labels must still differ.

    One label for both would merge unrelated bands in the tour and union their layers in the
    crossings finding — the two `Db.php` hubs below are exactly 211's `legacy/alpha`/`legacy/beta` case.
    """
    files = [
        "legacy/alpha/Db.php",
        "legacy/alpha/Order.php",
        "legacy/beta/Db.php",
        "legacy/beta/Order.php",
    ]
    edges = _tiers(
        [("legacy/alpha/Db.php", "legacy/alpha/Order.php"), ("legacy/beta/Db.php", "legacy/beta/Order.php")]
    )
    result = assign_communities(files, edges)
    alpha, beta = result["legacy/alpha/Db.php"], result["legacy/beta/Db.php"]
    assert result["legacy/alpha/Order.php"] == alpha, "the alpha pair is one community"
    assert result["legacy/beta/Order.php"] == beta, "the beta pair is one community"
    assert alpha != beta, f"distinct communities must not share the label {alpha!r}"
    assert alpha.startswith(COMMUNITY_PREFIX) and beta.startswith(COMMUNITY_PREFIX)


def test_dynamic_edges_do_not_join_singletons() -> None:
    """Pass 2 is HEURISTIC only — DYNAMIC is not community evidence."""
    files = ["p.php", "q.php"]
    edges = [("p.php", "q.php", "DYNAMIC")]
    result = assign_communities(files, edges)
    assert result["p.php"] != result["q.php"]


def test_isolated_file_has_its_own_community() -> None:
    """A file with no edges is its own singleton community."""
    files = ["solo.php"]
    result = assign_communities(files, _tiers([]))
    assert "solo.php" in result
    label = result["solo.php"]
    assert label.startswith(COMMUNITY_PREFIX)


def test_community_assignment_excludes_non_tour_files() -> None:
    """Files not in the `files` list do not appear in the result, even if named in edges."""
    files = ["a.php", "b.php"]
    edges = _tiers([("a.php", "c.php")])  # c.php is not in the tour
    result = assign_communities(files, edges)
    assert "c.php" not in result
    assert "a.php" in result and "b.php" in result


def _steps(files: list[str], edges: list[tuple[str, str]], community_of: dict[str, str]):
    nodes = [("Class", f) for f in files]
    metrics = compute_metrics(nodes, edges)
    assignment = assign_layers(metrics)
    stops = ordered_stops(files, edges, [files[0]])
    return assignment, build_steps(
        stops, assignment, metrics, edges, [files[0]], community_of=community_of
    )


def test_path_vocabulary_wins_where_it_fires() -> None:
    """AC4 — a Domain / Data path keeps that layer even when community_of maps it elsewhere."""
    models = [f"app/Models/M{i}.php" for i in range(6)]
    controllers = [f"app/Http/C{i}.php" for i in range(6)]
    files = models + controllers
    edges = [(controllers[i], models[i]) for i in range(6)]
    community_of = {f: f"{COMMUNITY_PREFIX}override" for f in files}
    assignment, steps = _steps(files, edges, community_of)
    by_file = {m.module: m.layer for m in assignment.modules}
    assert {by_file[f] for f in models} == {"Domain / Data"}
    titles = {step.title.split(" (")[0] for step in steps}
    assert "Domain / Data" in titles
    # Vocabulary-hit files must not be retitled as a community.
    named = [s for s in steps if any(m in models for m in s.modules)]
    assert named
    assert all(not s.title.startswith(COMMUNITY_PREFIX) for s in named)


def test_uncategorised_files_take_the_community_label() -> None:
    """Uncategorised files (no vocabulary hit) are labelled by community, not Uncategorised."""
    named = [f"app/Models/M{i}.php" for i in range(5)]
    silent = [f"src/widget/W{i}.php" for i in range(5)]
    files = named + silent
    edges = [(named[i], silent[i]) for i in range(5)]
    community_of = {f: f"{COMMUNITY_PREFIX}widget" for f in silent}
    assignment, steps = _steps(files, edges, community_of)
    by_file = {m.module: m.layer for m in assignment.modules}
    assert {by_file[f] for f in silent} == {UNCATEGORISED}
    titles = {step.title.split(" (")[0] for step in steps}
    assert UNCATEGORISED not in titles
    assert any(t.startswith(COMMUNITY_PREFIX) for t in titles)


def test_generate_onboarding_groups_qname_edges_into_file_communities(
    tmp_path: Path,
) -> None:
    """Production wiring: dependency_edges_with_tier is qnames; communities must still form."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        for i in range(4):
            path = f"src/pack/A{i}.aa"
            qname = f"\\Pack\\A{i}"
            nxt = f"\\Pack\\A{i + 1}" if i < 3 else None
            edges = (
                [edge("CALLS", qname, nxt, path, target_qname=nxt)] if nxt else []
            )
            seed_file(store, path, [node("Class", f"A{i}", qname, path)], edges, root=tmp_path)
        for i in range(3):
            path = f"app/Models/M{i}.aa"
            qname = f"\\App\\M{i}"
            seed_file(store, path, [node("Class", f"M{i}", qname, path)], [], root=tmp_path)
    payload = generate_onboarding.create(config)()
    artifact = json.loads(
        (tmp_path / ".code-atlas" / "onboarding" / "artifact.json").read_text(
            encoding="utf-8"
        )
    )
    tour = (_out(tmp_path) / "tour.md").read_text(encoding="utf-8")
    assert payload["indexed"] is True
    titles = [step["title"] for step in artifact["steps"]]
    assert any(title.startswith(COMMUNITY_PREFIX) for title in titles)
    assert UNCATEGORISED not in titles
    assert "Community/" in tour
    assert "community_crossings" in artifact["summary"]


def test_community_crossing_is_ranked_and_rendered(tmp_path: Path) -> None:
    """A RESOLVED chain through Model → widget → controller surfaces the straddling community."""
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/Models/M.aa",
            [node("Class", "M", "\\App\\M", "app/Models/M.aa")],
            [
                edge(
                    "CALLS",
                    "\\App\\M",
                    "\\App\\W",
                    "app/Models/M.aa",
                    target_qname="\\App\\W",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            "src/widget/W.aa",
            [node("Class", "W", "\\App\\W", "src/widget/W.aa")],
            [
                edge(
                    "CALLS",
                    "\\App\\W",
                    "\\App\\C",
                    "src/widget/W.aa",
                    target_qname="\\App\\C",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            "app/controllers/C.aa",
            [node("Class", "C", "\\App\\C", "app/controllers/C.aa")],
            [],
            root=tmp_path,
        )
    generate_onboarding.create(config)()
    artifact = json.loads(
        (tmp_path / ".code-atlas" / "onboarding" / "artifact.json").read_text(
            encoding="utf-8"
        )
    )
    overview = (_out(tmp_path) / "overview.md").read_text(encoding="utf-8")
    crossings = artifact["summary"]["community_crossings"]
    assert crossings
    layers = set(crossings[0]["layers"])
    assert {"Domain / Data", "HTTP / Entry"} <= layers
    assert "## Community / layer disagreement" in overview
