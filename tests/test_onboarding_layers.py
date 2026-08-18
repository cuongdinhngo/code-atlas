"""Task 084 — deterministic architectural-layer assignment.

The layer logic is pure over 083's ``GraphMetrics``, so the fixtures are plain Python — no database.
AC3 needs two paths proven: a **namespaced** graph layered by prefix-refined-by-direction, and a
**flat-namespace** graph falling back to pure dependency direction. Byte-stability (AC1a, R4.2) is
proven by computing twice over shuffled input and byte-comparing the JSON.
"""

from code_atlas.onboarding import layers
from code_atlas.onboarding.layers import LAYER_METHODS, assign_layers
from code_atlas.onboarding.metrics import DIRECTION_LABELS, compute_metrics

# Namespaced: Http → Domain → Infra(Repo → Db). Distinct parent dirs → the primary prefix path.
NS_NODES = [
    ("App\\Http\\Controller", "src/Http/Controller.php"),
    ("App\\Domain\\Service", "src/Domain/Service.php"),
    ("App\\Infra\\Repo", "src/Infra/Repo.php"),
    ("App\\Infra\\Db", "src/Infra/Db.php"),
]
NS_EDGES = [
    ("App\\Http\\Controller", "App\\Domain\\Service"),
    ("App\\Domain\\Service", "App\\Infra\\Repo"),
    ("App\\Infra\\Repo", "App\\Infra\\Db"),
]

# Flat: same dependency chain, every file at the root → one prefix → the direction fallback.
FLAT_NODES = [
    ("Controller", "Controller.php"),
    ("Service", "Service.php"),
    ("Repo", "Repo.php"),
    ("Db", "Db.php"),
]
FLAT_EDGES = [
    ("Controller", "Service"),
    ("Service", "Repo"),
    ("Repo", "Db"),
]

# Flat chain plus an edge-less orphan → exercises the fourth fallback band, which the pure
# source/mixed/sink chain above never reaches.
FLAT_WITH_ISOLATED_NODES = [*FLAT_NODES, ("Orphan", "Orphan.php")]

# ≥3-deep: two sibling leaf dirs (Controllers, Requests) under ONE architectural segment (Http). The
# common root is "src/App"; 103 groups by the first segment past it, so both collapse into "Http".
DEEP_NODES = [
    ("App\\Http\\Controllers\\UserController", "src/App/Http/Controllers/UserController.php"),
    ("App\\Http\\Requests\\UserRequest", "src/App/Http/Requests/UserRequest.php"),
    ("App\\Domain\\User", "src/App/Domain/User.php"),
]
DEEP_EDGES = [
    ("App\\Http\\Controllers\\UserController", "App\\Http\\Requests\\UserRequest"),
    ("App\\Http\\Requests\\UserRequest", "App\\Domain\\User"),
]

# No shared directory prefix — two unrelated top-level dirs. Common prefix is empty, so each first
# segment is its own layer (no fragmentation: these ARE different top-level areas).
SPLIT_NODES = [("Web\\Handler", "web/Handler.php"), ("Lib\\Db", "lib/Db.php")]
SPLIT_EDGES = [("Web\\Handler", "Lib\\Db")]

# A multi-segment common root ("app/src") that must be stripped whole before the layer segment.
NESTED_ROOT_NODES = [
    ("Http\\Controller", "app/src/Http/Controller.php"),
    ("Domain\\Service", "app/src/Domain/Service.php"),
]
NESTED_ROOT_EDGES = [("Http\\Controller", "Domain\\Service")]

# A boundary file directly in the common-root dir (src/bootstrap.php) beside namespaced dirs. It has
# no segment past the common root, so the conservative trigger falls back to direction rather than
# emitting an empty/sentinel layer (ASSUMED-1, task 103).
BOUNDARY_NODES = [
    ("Bootstrap", "src/bootstrap.php"),
    ("Http\\Controller", "src/Http/Controller.php"),
    ("Domain\\Service", "src/Domain/Service.php"),
]
BOUNDARY_EDGES = [
    ("Bootstrap", "Http\\Controller"),
    ("Http\\Controller", "Domain\\Service"),
]


def _namespaced() -> layers.LayerAssignment:
    return assign_layers(compute_metrics(NS_NODES, NS_EDGES))


def _flat() -> layers.LayerAssignment:
    return assign_layers(compute_metrics(FLAT_NODES, FLAT_EDGES))


def test_namespaced_graph_layers_by_prefix_refined_by_direction() -> None:
    assigned = _namespaced()
    assert assigned.method == "common-root-segment"
    # Common root "src" stripped; the first remaining segment is the architectural layer. Source-
    # like Http leads, sink-like Infra trails — groups ordered by net direction.
    assert assigned.layers == ("Http", "Domain", "Infra")
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed == {
        "src/Http/Controller.php": ("Http", 0),
        "src/Domain/Service.php": ("Domain", 1),
        "src/Infra/Repo.php": ("Infra", 2),
        "src/Infra/Db.php": ("Infra", 2),
    }


def test_flat_namespace_falls_back_to_dependency_direction() -> None:
    assigned = _flat()
    assert assigned.method == "dependency-direction-fallback"
    assert assigned.layers == ("source", "mixed", "sink")
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed == {
        "Controller.php": ("source", 0),
        "Service.php": ("mixed", 1),
        "Repo.php": ("mixed", 1),
        "Db.php": ("sink", 2),
    }


def test_deep_tree_collapses_sibling_leaf_dirs_into_one_layer() -> None:
    # PROVING TEST (103/AC1). Controllers/ and Requests/ are sibling leaf dirs under one
    # architectural segment (Http). Under 084's deepest-parent _prefix they were TWO layers; the
    # common-root-segment grain (root src/App stripped) merges them into "Http" — fails on 084.
    assigned = assign_layers(compute_metrics(DEEP_NODES, DEEP_EDGES))
    assert assigned.method == "common-root-segment"
    assert assigned.layers == ("Http", "Domain")
    # Asserted on layer AND rank (AC1): source-like Http leads (rank 0), sink-like Domain trails.
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed["src/App/Http/Controllers/UserController.php"] == ("Http", 0)
    assert placed["src/App/Http/Requests/UserRequest.php"] == ("Http", 0)
    assert placed["src/App/Domain/User.php"] == ("Domain", 1)


def test_no_shared_prefix_makes_each_top_dir_a_layer() -> None:
    # 103/AC4(a). Empty common prefix → the first segment of each path is the layer; two unrelated
    # top-level dirs stay two layers (not fragmentation — they ARE different areas).
    assigned = assign_layers(compute_metrics(SPLIT_NODES, SPLIT_EDGES))
    assert assigned.method == "common-root-segment"
    assert assigned.layers == ("web", "lib")
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed == {"web/Handler.php": "web", "lib/Db.php": "lib"}


def test_multi_segment_common_root_is_stripped_whole() -> None:
    # 103/AC4(b). The shared root can be more than one segment ("app/src"); it is stripped whole
    # before the layer segment shows; a mid-segment character prefix never leaks (R2, how-dec #1).
    assigned = assign_layers(compute_metrics(NESTED_ROOT_NODES, NESTED_ROOT_EDGES))
    assert assigned.method == "common-root-segment"
    assert assigned.layers == ("Http", "Domain")
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed == {
        "app/src/Http/Controller.php": "Http",
        "app/src/Domain/Service.php": "Domain",
    }


def test_boundary_file_forces_direction_fallback_not_an_empty_layer() -> None:
    # 103/AC4(c), ASSUMED-1 (conservative). A file directly in the common-root dir (bootstrap.php)
    # has no segment past the root, so the tree does not split cleanly → fallback. No layer here
    # is the empty string or a sentinel; every layer is a real direction band.
    assigned = assign_layers(compute_metrics(BOUNDARY_NODES, BOUNDARY_EDGES))
    assert assigned.method == "dependency-direction-fallback"
    assert "" not in assigned.layers
    assert set(assigned.layers) <= set(DIRECTION_LABELS)
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/bootstrap.php"] in DIRECTION_LABELS


def test_single_module_falls_back_cleanly_with_no_empty_layer() -> None:
    # 103/AC4(c). One module can never yield >= 2 groups, so it falls back to direction — never an
    # empty layer key. An edge-less lone module reads as isolated.
    assigned = assign_layers(compute_metrics([("Solo", "src/Solo.php")], []))
    assert assigned.method == "dependency-direction-fallback"
    assert "" not in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/Solo.php"] == "isolated"


def test_deep_layers_are_byte_stable_across_two_runs() -> None:
    # 103/AC2 + lesson 009: prove the NEW common-prefix code is order-independent, not only the old
    # 2-deep path. Shuffling input must not change a byte of the serialised deep-tree assignment.
    first = assign_layers(compute_metrics(DEEP_NODES, DEEP_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(DEEP_NODES)), list(reversed(DEEP_EDGES)))
    ).to_json()
    assert first == second


def test_isolated_module_lands_in_the_last_fallback_band() -> None:
    # The source/mixed/sink chain never produces an "isolated" node, so the fourth band's rank was
    # only set-pinned, never proven. An edge-less orphan lands it last (entry → foundation order).
    assigned = assign_layers(compute_metrics(FLAT_WITH_ISOLATED_NODES, FLAT_EDGES))
    assert assigned.method == "dependency-direction-fallback"
    assert assigned.layers == ("source", "mixed", "sink", "isolated")
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed["Orphan.php"] == ("isolated", 3)


def test_layers_are_byte_stable_across_two_runs() -> None:
    first = assign_layers(compute_metrics(NS_NODES, NS_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(NS_NODES)), list(reversed(NS_EDGES)))
    ).to_json()
    assert first == second


def test_every_emitted_method_comes_from_the_exported_set() -> None:
    used = {_namespaced().method, _flat().method}
    assert used <= set(LAYER_METHODS)


def test_layer_methods_are_derived_not_listed() -> None:
    # The guard can fail: add a member to LAYER_METHODS without a producing branch (or vice versa)
    # and the set equality breaks (R6.7 / derived-not-listed-invariant).
    produced = {_namespaced().method, _flat().method}
    assert produced == set(LAYER_METHODS)


def test_fallback_bands_are_derived_from_direction_labels() -> None:
    # The fallback order must cover every metrics label: a label unplaced here would KeyError in
    # _by_direction. Deriving the set from DIRECTION_LABELS makes that a red pin, not a crash.
    assert set(layers._FALLBACK_ORDER) == set(DIRECTION_LABELS)
    assert {m.layer for m in _flat().modules} <= set(DIRECTION_LABELS)
