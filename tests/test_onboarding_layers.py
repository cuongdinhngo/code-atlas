"""Task 084/103/104/110 — deterministic architectural-layer assignment.

The layer logic is pure over 083's ``GraphMetrics``, so the fixtures are plain Python — no database.
The PRIMARY path is **responsibility** (110): group each module by the deepest directory segment
that names a role (``Uncategorised`` when none does). When that yields < 2 layers the assignment
falls back to **dominant-subtree** (104, 105 — group beneath the top dir with the most dependency
mass), then to pure **dependency-direction** (084) for a flat namespace. The fallback fixtures below
deliberately use directory names that match NO responsibility keyword, so they still exercise the
fallback they were written for. Byte-stability (R4.2) is proven by computing twice over shuffled
input and byte-comparing the JSON.
"""

import dataclasses

from code_atlas.onboarding import layers
from code_atlas.onboarding.layers import (
    LAYER_METHODS,
    RESPONSIBILITY_KEYWORDS,
    UNCATEGORISED,
    assign_layers,
    layer_description,
)
from code_atlas.onboarding.metrics import DIRECTION_LABELS, compute_metrics

# ------------------------------------------------------------------------------------------------
# Responsibility path (110) — the PRIMARY grouping. Fixtures whose directory segments name a
# responsibility keyword.

# controller / model / view under one parent → three responsibility layers, not one directory group.
RESP_NODES = [
    ("A", "app/x/controller/a.aa"),
    ("B", "app/x/model/b.aa"),
    ("C", "app/x/view/c.aa"),
]
RESP_EDGES = [("A", "B"), ("B", "C")]

# Deepest-wins: an OUTER segment ("service") also matches, but the INNER ("controller") must win.
DEEPEST_NODES = [
    ("S", "app/service/controller/x.aa"),
    ("M", "app/model/y.aa"),
]
DEEPEST_EDGES = [("S", "M")]

# A broad, real-shape spread across many responsibilities plus one unmatched dir → Uncategorised.
REAL_NODES = [
    ("c", "src/controllers/Home.aa"),
    ("s", "src/services/Billing.aa"),
    ("m", "src/models/User.aa"),
    ("v", "resources/views/home.aa"),
    ("j", "src/jobs/SendMail.aa"),
    ("r", "src/reports/Monthly.aa"),
    ("cfg", "config/app.aa"),
    ("ven", "vendor/pkg/x.aa"),
    ("t", "tests/unit/UserTest.aa"),
    ("misc", "misc/thing/x.aa"),
]
REAL_EDGES = [("c", "s"), ("s", "m"), ("j", "s"), ("r", "m")]

# ------------------------------------------------------------------------------------------------
# Fallback fixtures — directory names chosen to match NO responsibility keyword (see docstring).

# Namespaced: Http → Domain → Infra(Repo → Db). Distinct parent dirs → the dominant-subtree path.
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

# Flat chain plus an edge-less orphan → exercises the fourth fallback band.
FLAT_WITH_ISOLATED_NODES = [*FLAT_NODES, ("Orphan", "Orphan.php")]

# ≥3-deep: two sibling leaf dirs (Ingress, Requests — neither a keyword) under one segment (Http).
# The dominant subtree is "src"; its within-subtree root is "src/App", so both collapse into "Http".
DEEP_NODES = [
    ("App\\Http\\Ingress\\UserController", "src/App/Http/Ingress/UserController.php"),
    ("App\\Http\\Requests\\UserRequest", "src/App/Http/Requests/UserRequest.php"),
    ("App\\Domain\\User", "src/App/Domain/User.php"),
]
DEEP_EDGES = [
    ("App\\Http\\Ingress\\UserController", "App\\Http\\Requests\\UserRequest"),
    ("App\\Http\\Requests\\UserRequest", "App\\Domain\\User"),
]

# No shared directory prefix — two unrelated top-level dirs (neither a keyword).
SPLIT_NODES = [("Web\\Handler", "web/Handler.php"), ("Toolkit\\Db", "toolkit/Db.php")]
SPLIT_EDGES = [("Web\\Handler", "Toolkit\\Db")]

# A multi-segment common root ("app/src") that must be stripped whole before the layer segment.
NESTED_ROOT_NODES = [
    ("Http\\Controller", "app/src/Http/Controller.php"),
    ("Domain\\Service", "app/src/Domain/Service.php"),
]
NESTED_ROOT_EDGES = [("Http\\Controller", "Domain\\Service")]

# A boundary file directly in the common-root dir (src/bootstrap.php) beside namespaced dirs.
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


def _responsibility() -> layers.LayerAssignment:
    return assign_layers(compute_metrics(RESP_NODES, RESP_EDGES))


# ------------------------------------------------------------------------------------------------
# Responsibility path (110)


def test_responsibility_groups_controller_model_view_into_three_layers() -> None:
    # PROVING TEST (110 / AC1, R6.5). Under today's dominant-subtree code these three share the
    # "app"/"x" directory and collapse into ONE layer; responsibility splits them by segment.
    assigned = _responsibility()
    assert assigned.method == "responsibility"
    assert set(assigned.layers) == {"HTTP / Entry", "Domain / Data", "Views"}
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["app/x/controller/a.aa"] == "HTTP / Entry"
    assert placed["app/x/model/b.aa"] == "Domain / Data"
    assert placed["app/x/view/c.aa"] == "Views"


def test_deepest_segment_wins_over_an_outer_match() -> None:
    # 110 / AC2. `app/service/controller/x` matches both "service" and "controller"; the deepest
    # segment (controller → HTTP / Entry) wins, so the file is NOT filed under Services.
    assigned = assign_layers(compute_metrics(DEEPEST_NODES, DEEPEST_EDGES))
    assert assigned.method == "responsibility"
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["app/service/controller/x.aa"] == "HTTP / Entry"
    assert "Services" not in assigned.layers


def test_real_spread_maps_to_named_layers_with_uncategorised_reported() -> None:
    # 110. A broad tree lands in the ratified responsibility layers; an unmatched dir is reported as
    # Uncategorised, not hidden (a naming-debt signal).
    assigned = assign_layers(compute_metrics(REAL_NODES, REAL_EDGES))
    assert assigned.method == "responsibility"
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/controllers/Home.aa"] == "HTTP / Entry"
    assert placed["src/services/Billing.aa"] == "Services"
    assert placed["src/models/User.aa"] == "Domain / Data"
    assert placed["resources/views/home.aa"] == "Views"
    assert placed["src/jobs/SendMail.aa"] == "Background Jobs"
    assert placed["src/reports/Monthly.aa"] == "Integration / Reporting"
    assert placed["config/app.aa"] == "Config / Migration"
    assert placed["vendor/pkg/x.aa"] == "Vendor / Framework"
    assert placed["tests/unit/UserTest.aa"] == "Tests"
    assert placed["misc/thing/x.aa"] == UNCATEGORISED


def test_every_assigned_layer_has_a_nonempty_description() -> None:
    # 110 / AC3. Every layer a run can emit — responsibility layers, direction bands, root, and any
    # refiner rename — resolves to a non-empty description, so 109's C3 is real, not vacuous.
    for assigned in (_responsibility(), _flat(), _namespaced()):
        for layer in assigned.layers:
            assert layer_description(layer).strip()
    assert layer_description("some future LLM name").strip()  # structural default is non-empty


def test_responsibility_is_byte_stable_across_two_runs() -> None:
    first = assign_layers(compute_metrics(REAL_NODES, REAL_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(REAL_NODES)), list(reversed(REAL_EDGES)))
    ).to_json()
    assert first == second


def test_vocabulary_names_no_repo_product_or_framework() -> None:
    # 110 / AC5. The R2.2 grep-gate denylists these names; the vocabulary must contain none,
    # and every keyword must be lowercase (segment matching lowercases before comparing).
    denylist = {"laravel", "symfony", "wordpress", "drupal", "magento"}
    assert not (set(RESPONSIBILITY_KEYWORDS) & denylist)
    assert all(word == word.lower() for word in RESPONSIBILITY_KEYWORDS)


# ------------------------------------------------------------------------------------------------
# Dominant-subtree fallback (104, 105)


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


def test_deep_tree_collapses_sibling_leaf_dirs_into_one_layer() -> None:
    # 103/AC1 regression. Ingress/ and Requests/ are sibling leaf dirs under one segment (Http). The
    # dominant-subtree grain (within-subtree root src/App stripped) merges them into "Http".
    assigned = assign_layers(compute_metrics(DEEP_NODES, DEEP_EDGES))
    assert assigned.method == "dominant-subtree"
    assert assigned.layers == ("Http", "Domain")
    placed = {m.module: (m.layer, m.rank) for m in assigned.modules}
    assert placed["src/App/Http/Ingress/UserController.php"] == ("Http", 0)
    assert placed["src/App/Http/Requests/UserRequest.php"] == ("Http", 0)
    assert placed["src/App/Domain/User.php"] == ("Domain", 1)


def test_no_shared_prefix_makes_each_top_dir_a_layer() -> None:
    # 103/AC4(a). Empty common prefix → the first segment of each path is the layer; two unrelated
    # top-level dirs stay two layers.
    assigned = assign_layers(compute_metrics(SPLIT_NODES, SPLIT_EDGES))
    assert assigned.method == "dominant-subtree"
    assert assigned.layers == ("web", "toolkit")
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed == {"web/Handler.php": "web", "toolkit/Db.php": "toolkit"}


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
    # within-subtree prefix, so it takes the top-dir name "src" — never the empty string.
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
    # 103/AC2 + lesson 009: prove the common-prefix code is order-independent, not only the 2-deep
    # path. Shuffling input must not change a byte of the serialised deep-tree assignment.
    first = assign_layers(compute_metrics(DEEP_NODES, DEEP_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(DEEP_NODES)), list(reversed(DEEP_EDGES)))
    ).to_json()
    assert first == second


# ------------------------------------------------------------------------------------------------
# Direction fallback (084)


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


# ------------------------------------------------------------------------------------------------
# Method derivation (three methods since 110)


def test_every_emitted_method_comes_from_the_exported_set() -> None:
    used = {_responsibility().method, _namespaced().method, _flat().method}
    assert used <= set(LAYER_METHODS)


def test_layer_methods_are_derived_not_listed() -> None:
    # The guard can fail: add a member to LAYER_METHODS without a producing branch (or vice versa)
    # and the set equality breaks (R6.7 / derived-not-listed-invariant).
    produced = {_responsibility().method, _namespaced().method, _flat().method}
    assert produced == set(LAYER_METHODS)


def test_fallback_bands_are_derived_from_direction_labels() -> None:
    # The fallback order must cover every metrics label: a label unplaced here would KeyError in
    # _by_direction. Deriving the set from DIRECTION_LABELS makes that a red pin, not a crash.
    assert set(layers._FALLBACK_ORDER) == set(DIRECTION_LABELS)
    assert {m.layer for m in _flat().modules} <= set(DIRECTION_LABELS)


# -------------------------------------------------------------------------------------------------
# Task 104 / 105 / AC3 — dominant-subtree regression fixtures (dirs chosen to match NO keyword, so
# the fallback they guard still fires). These are the bake-off layouts that broke C0 and C2.

# (a) 105's mass-heavy rewrite: a flat, edge-less "settings" dir out-COUNTS a connected source tree,
# so the old file-count rule elected it and collapsed the source tree; graph mass keeps the source
# tree dominant and splits it. None of these dir names is a responsibility keyword.
MASS_NODES = [
    ("App\\Ingress\\PublicV1\\UserController", "app/Ingress/PublicV1/UserController.php"),
    ("App\\Ingress\\HomeController", "app/Ingress/HomeController.php"),
    ("App\\Records\\User", "app/Records/User.php"),
    ("App\\Records\\Invoice", "app/Records/Invoice.php"),
    ("App\\Ops\\Billing", "app/Ops/Billing.php"),
    ("App\\Providers\\AppServiceProvider", "app/Providers/AppServiceProvider.php"),
    ("App\\Boot\\Kernel", "app/Boot/Kernel.php"),
    ("settings_app", "settings/app.php"),
    ("settings_auth", "settings/auth.php"),
    ("settings_cache", "settings/cache.php"),
    ("settings_database", "settings/database.php"),
    ("settings_mail", "settings/mail.php"),
    ("settings_queue", "settings/queue.php"),
    ("settings_services", "settings/services.php"),
    ("settings_session", "settings/session.php"),
]
MASS_EDGES = [
    ("App\\Ingress\\PublicV1\\UserController", "App\\Ops\\Billing"),
    ("App\\Ingress\\HomeController", "App\\Records\\User"),
    ("App\\Ops\\Billing", "App\\Records\\Invoice"),
    ("App\\Providers\\AppServiceProvider", "App\\Ops\\Billing"),
    ("App\\Boot\\Kernel", "App\\Ops\\Billing"),
]

# (b) Deep root: all under src/App/**. dominant-subtree strips src/App and splits Http/Domain.
DEEP_ROOT_NODES = [
    ("App\\Http\\Kernel", "src/App/Http/Kernel.php"),
    ("App\\Domain\\Order", "src/App/Domain/Order.php"),
    ("App\\Infra\\Db", "src/App/Infra/Db.php"),
]
DEEP_ROOT_EDGES = [
    ("App\\Http\\Kernel", "App\\Domain\\Order"),
    ("App\\Domain\\Order", "App\\Infra\\Db"),
]

# (c) packages/*/src monorepo: dominant subtree "packages" keeps each package (foo, bar) a layer.
PKG_NODES = [
    ("Foo\\Service", "packages/foo/src/Service.php"),
    ("Foo\\Helper", "packages/foo/src/Helper.php"),
    ("Bar\\Client", "packages/bar/src/Client.php"),
]
PKG_EDGES = [("Foo\\Service", "Bar\\Client")]

# (d) A root-level file (init.php, no directory) beside app/**; lands in the "(root)" layer.
ROOT_FILE_NODES = [
    ("init_app", "init.php"),
    ("App\\Http\\Kernel", "app/Http/Kernel.php"),
    ("App\\Records\\User", "app/Records/User.php"),
]
ROOT_FILE_EDGES = [("init_app", "App\\Http\\Kernel")]

# A mass tie where the dominant choice CHANGES the output: "a" splits into Http/Records, "b" has no
# sub-structure. The (-mass, -count, name) tie-break must pick "a" regardless of input order.
TIE_NODES = [
    ("A\\Http\\X", "a/Http/X.php"),
    ("A\\Records\\Y", "a/Records/Y.php"),
    ("B\\Z", "b/Z.php"),
    ("B\\W", "b/W.php"),
]
TIE_EDGES = [("A\\Http\\X", "A\\Records\\Y"), ("B\\Z", "B\\W")]

# An index with nodes but NO resolved edges: every dir has mass 0, so the tie-break falls back to
# module count — populous zzz/ (2 files) dominates and splits, not the alphabetically-first aaa/.
EDGELESS_NODES = [
    ("Zzz\\Http\\A", "zzz/Http/A.php"),
    ("Zzz\\Records\\B", "zzz/Records/B.php"),
    ("Aaa\\C", "aaa/C.php"),
]
EDGELESS_EDGES: list[tuple[str, str]] = []


def test_dominant_subtree_survives_a_flat_dir_with_more_files() -> None:
    # PROVING TEST (105 / AC3(a), the F1 fix). settings/** out-COUNTS app/** (8 files vs 7) but has
    # no edges, so the old file-count rule elects settings/ and collapses app/**. Graph mass keeps
    # app/ dominant: it splits by its 2nd segment while settings/ stays one layer.
    assigned = assign_layers(compute_metrics(MASS_NODES, MASS_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "app" not in assigned.layers
    assert {"Ingress", "Records", "Ops", "Providers", "Boot"} <= set(assigned.layers)
    assert "settings" in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["app/Ingress/PublicV1/UserController.php"] == "Ingress"
    assert placed["app/Records/User.php"] == "Records"
    assert placed["app/Ops/Billing.php"] == "Ops"
    assert placed["settings/app.php"] == "settings"


def test_deep_src_app_tree_still_splits_into_http_domain_infra() -> None:
    # 104 / AC3(b). A deep src/App/** root must split by the segment past src/App.
    assigned = assign_layers(compute_metrics(DEEP_ROOT_NODES, DEEP_ROOT_EDGES))
    assert assigned.method == "dominant-subtree"
    assert set(assigned.layers) == {"Http", "Domain", "Infra"}
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["src/App/Http/Kernel.php"] == "Http"
    assert placed["src/App/Domain/Order.php"] == "Domain"
    assert placed["src/App/Infra/Db.php"] == "Infra"


def test_packages_monorepo_keeps_each_package_a_distinct_layer() -> None:
    # 104 / AC3(c). packages/foo and packages/bar must stay distinct layers.
    assigned = assign_layers(compute_metrics(PKG_NODES, PKG_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "packages" not in assigned.layers
    assert {"foo", "bar"} <= set(assigned.layers)
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["packages/foo/src/Service.php"] == "foo"
    assert placed["packages/bar/src/Client.php"] == "bar"


def test_root_level_file_lands_in_the_explicit_root_layer_not_empty_string() -> None:
    # 104 / AC3(d), the residual. A top-level init.php with no directory prefix gets the explicit
    # "(root)" layer, never the empty string; app/** still splits normally beside it.
    assigned = assign_layers(compute_metrics(ROOT_FILE_NODES, ROOT_FILE_EDGES))
    assert assigned.method == "dominant-subtree"
    assert "" not in assigned.layers
    assert "(root)" in assigned.layers
    placed = {m.module: m.layer for m in assigned.modules}
    assert placed["init.php"] == "(root)"
    assert placed["app/Http/Kernel.php"] == "Http"


def test_dominant_subtree_pipeline_is_byte_stable_across_two_runs() -> None:
    # 104 / AC4 (R4.2): the whole pipeline is byte-stable end-to-end over shuffled input.
    first = assign_layers(compute_metrics(MASS_NODES, MASS_EDGES)).to_json()
    second = assign_layers(
        compute_metrics(list(reversed(MASS_NODES)), list(reversed(MASS_EDGES)))
    ).to_json()
    assert first == second


def test_dominant_subtree_tie_break_is_order_independent_at_the_assign_boundary() -> None:
    # 104 / AC4 (R4.2) + lesson 009. Shuffle the modules tuple at the assign_layers boundary itself,
    # on a fixture whose OUTPUT depends on the mass tie-break (105).
    metrics = compute_metrics(TIE_NODES, TIE_EDGES)
    shuffled = dataclasses.replace(metrics, modules=tuple(reversed(metrics.modules)))
    first, second = assign_layers(metrics), assign_layers(shuffled)
    assert first.to_json() == second.to_json()
    assert {"Http", "Records", "b"} <= set(first.layers)
    assert "a" not in first.layers


def test_edgeless_index_falls_back_to_module_count_not_alphabetical() -> None:
    # 105 review F2. No resolved edges → every dir has mass 0; the tie-break falls back to module
    # count, so populous zzz/ dominates and splits rather than an alphabetical pick electing aaa/.
    assigned = assign_layers(compute_metrics(EDGELESS_NODES, EDGELESS_EDGES))
    assert assigned.method == "dominant-subtree"
    assert {"Http", "Records"} <= set(assigned.layers)
    assert "zzz" not in assigned.layers
