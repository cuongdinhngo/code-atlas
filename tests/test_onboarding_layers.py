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


def _namespaced() -> layers.LayerAssignment:
    return assign_layers(compute_metrics(NS_NODES, NS_EDGES))


def _flat() -> layers.LayerAssignment:
    return assign_layers(compute_metrics(FLAT_NODES, FLAT_EDGES))


def test_namespaced_graph_layers_by_prefix_refined_by_direction() -> None:
    assigned = _namespaced()
    assert assigned.method == "namespace-prefix"
    # Source-like Http leads, sink-like Infra trails — prefix groups ordered by net direction.
    assert assigned.layers == ("src/Http", "src/Domain", "src/Infra")
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed == {
        "src/Http/Controller.php": ("src/Http", 0),
        "src/Domain/Service.php": ("src/Domain", 1),
        "src/Infra/Repo.php": ("src/Infra", 2),
        "src/Infra/Db.php": ("src/Infra", 2),
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
