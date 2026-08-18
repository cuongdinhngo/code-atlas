"""Task 084/103/104 — deterministic architectural-layer assignment.

The layer logic is pure over 083's ``GraphMetrics``, so the fixtures are plain Python — no database.
The primary path is **dominant-subtree** (104): group beneath the top-level dir holding the most
modules, keep every other top-level dir as its own layer; a **flat-namespace** graph falls back to
pure dependency direction. 104's real-shape regression fixtures (AC3) live at the file's end.
Byte-stability (R4.2) is proven by computing twice over shuffled input and byte-comparing the JSON.
"""

import dataclasses

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
# dominant subtree is "src"; its within-subtree root is "src/App", so both collapse into "Http".
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
    assert assigned.method == "dominant-subtree"
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
    # 103/AC1 regression. Controllers/ and Requests/ are sibling leaf dirs under one architectural
    # segment (Http). Under 084's deepest-parent _prefix they were TWO layers; the dominant-subtree
    # grain (within-subtree root src/App stripped) merges them into "Http".
    assigned = assign_layers(compute_metrics(DEEP_NODES, DEEP_EDGES))
    assert assigned.method == "dominant-subtree"
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
    assert assigned.method == "dominant-subtree"
    assert assigned.layers == ("web", "lib")
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed == {"web/Handler.php": "web", "lib/Db.php": "lib"}


def test_multi_segment_common_root_is_stripped_whole() -> None:
    # 103/AC4(b). The shared root can be more than one segment ("app/src"); it is stripped whole
    # before the layer segment shows; a mid-segment character prefix never leaks (R2, how-dec #1).
    assigned = assign_layers(compute_metrics(NESTED_ROOT_NODES, NESTED_ROOT_EDGES))
    assert assigned.method == "dominant-subtree"
    assert assigned.layers == ("Http", "Domain")
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed == {
        "app/src/Http/Controller.php": "Http",
        "app/src/Domain/Service.php": "Domain",
    }


def test_boundary_file_in_dominant_dir_gets_the_top_dir_layer_not_an_empty_string() -> None:
    # 104. A file directly in the dominant top dir (src/bootstrap.php) has no segment past the
    # within-subtree prefix, so it takes the top-dir name "src" — never the empty string. Unlike 103
    # (which fell the WHOLE tree back to direction on this one file), Http/Domain still split.
    assigned = assign_layers(compute_metrics(BOUNDARY_NODES, BOUNDARY_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "" not in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/bootstrap.php"] == "src"
    assert placed["src/Http/Controller.php"] == "Http"
    assert placed["src/Domain/Service.php"] == "Domain"


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


# -------------------------------------------------------------------------------------------------
# Task 104 / AC3 — real-shape regression fixtures. These are the bake-off layouts that broke C0 (the
# shipped 103) and C2 (first-two-segments). Fixture coverage NEVER closes AC2 (a real indexed repo);
# it guards the shapes AC2 would have caught, so a future refactor cannot silently reintroduce F1.

# (a) A real Laravel tree: 8 classes under app/** PLUS one routes/web.php. Under C0 the lone routes
# file empties the common prefix, so every app/** file collapses into a single "app" layer (F1).
LARAVEL_NODES = [
    ("App\\Http\\Controllers\\Api\\UserController", "app/Http/Controllers/Api/UserController.php"),
    ("App\\Http\\Controllers\\HomeController", "app/Http/Controllers/HomeController.php"),
    ("App\\Http\\Middleware\\Authenticate", "app/Http/Middleware/Authenticate.php"),
    ("App\\Models\\User", "app/Models/User.php"),
    ("App\\Models\\Invoice", "app/Models/Invoice.php"),
    ("App\\Services\\Billing", "app/Services/Billing.php"),
    ("App\\Providers\\AppServiceProvider", "app/Providers/AppServiceProvider.php"),
    ("App\\Console\\Kernel", "app/Console/Kernel.php"),
    ("routes_web", "routes/web.php"),
]
LARAVEL_EDGES = [
    ("routes_web", "App\\Http\\Controllers\\Api\\UserController"),
    ("App\\Http\\Controllers\\Api\\UserController", "App\\Services\\Billing"),
    ("App\\Services\\Billing", "App\\Models\\Invoice"),
]

# (b) Deep root: everything under src/App/**. C2 (first-two-segments) collapses it all into
# "src/App"; dominant-subtree strips the within-subtree root src/App and splits Http/Domain/Infra.
DEEP_ROOT_NODES = [
    ("App\\Http\\Kernel", "src/App/Http/Kernel.php"),
    ("App\\Domain\\Order", "src/App/Domain/Order.php"),
    ("App\\Infra\\Db", "src/App/Infra/Db.php"),
]
DEEP_ROOT_EDGES = [
    ("App\\Http\\Kernel", "App\\Domain\\Order"),
    ("App\\Domain\\Order", "App\\Infra\\Db"),
]

# (c) packages/*/src monorepo: the dominant subtree is "packages"; its within-subtree common root is
# just "packages", so the first remaining segment keeps each package (foo, bar) a distinct layer.
PKG_NODES = [
    ("Foo\\Service", "packages/foo/src/Service.php"),
    ("Foo\\Helper", "packages/foo/src/Helper.php"),
    ("Bar\\Client", "packages/bar/src/Client.php"),
]
PKG_EDGES = [("Foo\\Service", "Bar\\Client")]

# (d) A root-level file (config.php, no directory) beside app/**. It has no path segment to name a
# layer, so it lands in the explicit "(root)" layer rather than emitting the empty string.
ROOT_FILE_NODES = [
    ("config_app", "config.php"),
    ("App\\Http\\Kernel", "app/Http/Kernel.php"),
    ("App\\Models\\User", "app/Models/User.php"),
]
ROOT_FILE_EDGES = [("config_app", "App\\Http\\Kernel")]

# A count tie (dir "a" and "b" each hold 2 modules) where the dominant choice CHANGES the output:
# "a" splits into Http/Models, "b" has no sub-structure. The (-count, name) tie-break must pick "a"
# regardless of input order — a buggy insertion-order tie-break would flip to "b", and the layers
# with it, so reversing the modules is a real probe.
TIE_NODES = [
    ("A\\Http\\X", "a/Http/X.php"),
    ("A\\Models\\Y", "a/Models/Y.php"),
    ("B\\Z", "b/Z.php"),
    ("B\\W", "b/W.php"),
]
TIE_EDGES = [("A\\Http\\X", "A\\Models\\Y"), ("A\\Models\\Y", "B\\Z")]


def test_dominant_subtree_does_not_collapse_laravel_app_into_one_layer() -> None:
    # PROVING TEST (104 / AC3(a), the F1 fix). One routes/web.php outside app/** must NOT flatten
    # the whole application into a single "app" layer (the shipped-103 defect). app/** splits by its
    # second segment; routes/ stays its own layer.
    assigned = assign_layers(compute_metrics(LARAVEL_NODES, LARAVEL_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "app" not in assigned.layers
    assert {"Http", "Models", "Services", "Providers", "Console"} <= set(assigned.layers)
    assert "routes" in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["app/Http/Controllers/Api/UserController.php"] == "Http"
    assert placed["app/Models/User.php"] == "Models"
    assert placed["app/Services/Billing.php"] == "Services"
    assert placed["routes/web.php"] == "routes"


def test_deep_src_app_tree_still_splits_into_http_domain_infra() -> None:
    # 104 / AC3(b). A deep src/App/** root must split by the segment past src/App, not collapse into
    # "src" or "src/App" (the C2 failure mode).
    assigned = assign_layers(compute_metrics(DEEP_ROOT_NODES, DEEP_ROOT_EDGES))
    assert assigned.method == "dominant-subtree"
    assert set(assigned.layers) == {"Http", "Domain", "Infra"}
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/App/Http/Kernel.php"] == "Http"
    assert placed["src/App/Domain/Order.php"] == "Domain"
    assert placed["src/App/Infra/Db.php"] == "Infra"


def test_packages_monorepo_keeps_each_package_a_distinct_layer() -> None:
    # 104 / AC3(c). packages/foo and packages/bar must stay distinct layers, not merge into a single
    # "packages" layer.
    assigned = assign_layers(compute_metrics(PKG_NODES, PKG_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "packages" not in assigned.layers
    assert {"foo", "bar"} <= set(assigned.layers)
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["packages/foo/src/Service.php"] == "foo"
    assert placed["packages/bar/src/Client.php"] == "bar"


def test_root_level_file_lands_in_the_explicit_root_layer_not_empty_string() -> None:
    # 104 / AC3(d), the residual. A top-level config.php with no directory prefix gets the explicit
    # "(root)" layer, never the empty string; app/** still splits normally beside it.
    assigned = assign_layers(compute_metrics(ROOT_FILE_NODES, ROOT_FILE_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "" not in assigned.layers
    assert "(root)" in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["config.php"] == "(root)"
    assert placed["app/Http/Kernel.php"] == "Http"


def test_dominant_subtree_pipeline_is_byte_stable_across_two_runs() -> None:
    # 104 / AC4 (R4.2): the whole pipeline is byte-stable end-to-end over shuffled Laravel input.
    first = assign_layers(compute_metrics(LARAVEL_NODES, LARAVEL_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(LARAVEL_NODES)), list(reversed(LARAVEL_EDGES)))
    ).to_json()
    assert first == second


def test_dominant_subtree_tie_break_is_order_independent_at_the_assign_boundary() -> None:
    # 104 / AC4 (R4.2) + lesson 009. compute_metrics._grain already sorts modules, so shuffling its
    # INPUT cannot observe order-dependence inside assign_layers. Shuffle the modules tuple at the
    # assign_layers boundary itself, on a fixture whose OUTPUT depends on the count tie-break.
    metrics = compute_metrics(TIE_NODES, TIE_EDGES)
    shuffled = dataclasses.replace(metrics, modules=tuple(reversed(metrics.modules)))
    first, second = assign_layers(metrics), assign_layers(shuffled)
    assert first.to_json() == second.to_json()
    # "a" (alphabetically first of the tie) is dominant and splits; "b" stays one layer.
    assert {"Http", "Models", "b"} <= set(first.layers)
    assert "a" not in first.layers
