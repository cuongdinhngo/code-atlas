"""197 — a capability trace from one entry symbol to the data it writes.

The proving test is ``test_flow_from_entry_symbol_reaches_the_named_column``: one flow, three hops,
ending on a ``Column`` the write statement named. Everything else here holds one acceptance
criterion each, so a failure names the criterion it broke.
"""

from code_atlas import contract
from code_atlas.onboarding.flows import (
    END_BUDGET,
    END_NO_SINK,
    END_SINK,
    END_UNPROVEN_HOP,
    FLOW_KINDS,
    NO_SEEDS,
    TRUNCATED_NOTE,
    build_flows,
    seed_files,
    seed_symbols,
)

# controller -> service -> repository -> a named column. One request, end to end.
FILE_OF = {
    "App\\InvoiceController::show": "controllers/InvoiceController.php",
    "App\\InvoiceService::load": "services/InvoiceService.php",
    "App\\InvoiceRepository::find": "repositories/InvoiceRepository.php",
    "dbo.Invoice::Total": "db/invoice.sql",
    "dbo.Invoice": "db/invoice.sql",
    "App\\Lonely::run": "lib/Lonely.php",
    "App\\Dyn::call": "lib/Dyn.php",
    "App\\Mystery::hop": "lib/Mystery.php",
    "App\\Orphan::run": "weird/Orphan.php",
}
LAYER_OF = {
    "controllers/InvoiceController.php": "HTTP / Entry",
    "services/InvoiceService.php": "Services",
    "repositories/InvoiceRepository.php": "Domain / Data",
    "db/invoice.sql": "Domain / Data",
    "lib/Lonely.php": "Shared Library",
    "lib/Dyn.php": "Shared Library",
    "lib/Mystery.php": "Shared Library",
    "weird/Orphan.php": "Shared Library",
}
OWNERS = {"controllers": "invoicing", "services": "invoicing", "lib": "shared"}

SEED = ("App\\InvoiceController::show", "vocabulary")

CHAIN = [
    ("App\\InvoiceController::show", "App\\InvoiceService::load", "CALLS", "RESOLVED", 10),
    ("App\\InvoiceService::load", "App\\InvoiceRepository::find", "CALLS", "RESOLVED", 20),
    ("App\\InvoiceRepository::find", "dbo.Invoice::Total", "WRITES", "RESOLVED", 30),
]


def _build(seeds, edges, **kwargs):
    params = {"max_flows": 10, "max_nodes": 100}
    params.update(kwargs)
    return build_flows(seeds, edges, FILE_OF, LAYER_OF, OWNERS, **params)


def test_flow_from_entry_symbol_reaches_the_named_column() -> None:
    """AC1 + AC3 — the proving test: ordered steps, each with layer and reaching tier."""
    result = _build([("App\\InvoiceController::show", "vocabulary")], CHAIN)
    assert len(result.flows) == 1
    flow = result.flows[0]
    assert flow.ended == END_SINK
    assert flow.sink == "dbo.Invoice::Total"
    assert [step.qname for step in flow.steps] == [
        "App\\InvoiceController::show",
        "App\\InvoiceService::load",
        "App\\InvoiceRepository::find",
        "dbo.Invoice::Total",
    ]
    assert [step.layer for step in flow.steps][:2] == ["HTTP / Entry", "Services"]
    assert flow.steps[-1].kind == "WRITES"
    assert all(step.tier == "RESOLVED" for step in flow.steps)
    # AC4/W5 — attribution keys on the SEED's path, not the sink's.
    assert flow.module == "invoicing"


def test_a_write_that_names_no_column_targets_the_table_at_dynamic() -> None:
    """AC3's other half — 022's own split, not a guessed column list."""
    edges = CHAIN[:2] + [
        ("App\\InvoiceRepository::find", "dbo.Invoice", "WRITES", "DYNAMIC", 30),
    ]
    flow = _build([("App\\InvoiceController::show", "vocabulary")], edges).flows[0]
    assert flow.sink == "dbo.Invoice"
    assert flow.steps[-1].tier == "DYNAMIC"


def test_one_entry_symbol_per_flow_not_one_per_file() -> None:
    """W3 — a file with k entry symbols is k requests, never one combined walk."""
    dest, repo = "App\\InvoiceController::destroy", "App\\InvoiceRepository::find"
    edges = CHAIN + [(dest, repo, "CALLS", "RESOLVED", 40)]
    file_of = dict(FILE_OF)
    file_of["App\\InvoiceController::destroy"] = "controllers/InvoiceController.php"
    seeds = seed_symbols(
        ["App\\InvoiceController::show", "App\\InvoiceController::destroy"],
        [("controllers/InvoiceController.php", "vocabulary")],
        file_of,
    )
    assert len(seeds) == 2
    result = build_flows(
        seeds, edges, file_of, LAYER_OF, OWNERS, max_flows=10, max_nodes=100
    )
    assert {flow.seed for flow in result.flows} == {q for q, _ in seeds}


def test_one_flow_per_sink_when_a_seed_reaches_several() -> None:
    """W4 — k distinct sinks is k flows, each a path with exactly one end."""
    edges = CHAIN + [
        ("App\\InvoiceRepository::find", "dbo.Invoice::Status", "WRITES", "RESOLVED", 31),
    ]
    file_of = dict(FILE_OF)
    file_of["dbo.Invoice::Status"] = "db/invoice.sql"
    result = build_flows(
        [("App\\InvoiceController::show", "vocabulary")], edges, file_of, LAYER_OF, OWNERS,
        max_flows=10, max_nodes=100,
    )
    assert len(result.flows) == 2
    assert {flow.sink for flow in result.flows} == {"dbo.Invoice::Total", "dbo.Invoice::Status"}
    assert all(flow.ended == END_SINK for flow in result.flows)


def test_a_trace_that_reaches_no_sink_is_emitted_and_labelled() -> None:
    """W2a + W2b — split, never dropped; the label is asserted, not implied."""
    result = _build([("App\\Lonely::run", "vocabulary")], [])
    assert len(result.flows) == 1
    assert result.flows[0].ended == END_NO_SINK
    assert result.flows[0].sink is None


def test_a_dynamic_hop_terminates_the_trace_and_says_so() -> None:
    """C2 / R5.2 — an unprovable hop is reported, never bridged."""
    edges = [
        ("App\\Dyn::call", "App\\Mystery::hop", "CALLS", "DYNAMIC", 5),
        ("App\\Mystery::hop", "dbo.Invoice::Total", "WRITES", "RESOLVED", 6),
    ]
    flow = _build([("App\\Dyn::call", "vocabulary")], edges).flows[0]
    assert flow.ended == END_UNPROVEN_HOP
    assert flow.sink is None, "a DYNAMIC hop must not be expanded through to the sink"


def test_an_exhausted_budget_marks_every_count_an_under_estimate() -> None:
    """AC2 — 140's rule: the caveat rides on the payload that carries the defect."""
    result = _build([("App\\InvoiceController::show", "vocabulary")], CHAIN, max_nodes=1)
    assert result.walk_truncated is True
    assert result.as_dict()["walk_truncated_note"] == TRUNCATED_NOTE
    assert result.flows[0].ended == END_BUDGET


def test_no_seeds_refuses_with_a_reason_rather_than_an_empty_list() -> None:
    """AC5 — an empty list is never returned as proof that no flow exists (182's precedent)."""
    result = _build([], CHAIN)
    assert result.refused == NO_SEEDS
    assert result.flows == ()
    assert result.as_dict()["refused"] == NO_SEEDS


def test_an_uncovered_seed_lands_in_an_explicit_unattributed_bucket() -> None:
    """AC4 — an explicit bucket, never a silent drop."""
    result = _build([("App\\Orphan::run", "vocabulary")], [])
    assert result.unattributed == ("App\\Orphan::run",)
    assert result.flows[0].module is None


def test_the_cap_is_global_and_names_what_it_cut() -> None:
    """W1a + W1b — a global cap, and the cut is stated."""
    edges = CHAIN + [
        ("App\\InvoiceRepository::find", "dbo.Invoice::Status", "WRITES", "RESOLVED", 31),
    ]
    file_of = dict(FILE_OF)
    file_of["dbo.Invoice::Status"] = "db/invoice.sql"
    result = build_flows(
        [("App\\InvoiceController::show", "vocabulary")], edges, file_of, LAYER_OF, OWNERS,
        max_flows=1, max_nodes=100,
    )
    assert len(result.flows) == 1
    assert result.flows_found == 2
    assert result.flows_cut == 1


def test_identical_input_yields_identical_output() -> None:
    """AC7 / R4.2."""
    first = _build([SEED], CHAIN).as_dict()
    reversed_edges = list(reversed(CHAIN))
    second = _build([SEED], reversed_edges).as_dict()
    assert first == second


def test_flow_kinds_is_derived_from_impact_kinds_never_re_listed() -> None:
    """R6.7 — `derived-not-listed-invariant`, the handle this change was recalled against."""
    assert FLOW_KINDS == contract.IMPACT_KINDS + (contract.WRITES,)
    assert "WRITES" not in contract.IMPACT_KINDS


def test_a_test_or_vendor_path_is_never_a_request_entry() -> None:
    """130's family, on the seed axis — the guard that caught this in review.

    ``responsibility_layer`` is deepest-wins, so `tests/controllers/X` and
    `vendor/a/src/controllers/Y` both read as HTTP / Entry. 131's ``reading_seed_rank`` sinks a
    test or vendor path on ANY segment, which is why seed selection goes through it.
    """
    paths = [
        "controllers/InvoiceController.php",
        "tests/controllers/InvoiceControllerTest.php",
        "spec/handlers/YSpec.php",
        "vendor/acme/src/controllers/X.php",
        "public/index.php",
        "services/InvoiceService.php",
    ]
    picked = {path for path, _signal in seed_files(paths, [])}
    assert "controllers/InvoiceController.php" in picked
    # 131 ranks a web root with HTTP, so a front controller is an entry the old check missed.
    assert "public/index.php" in picked
    assert "tests/controllers/InvoiceControllerTest.php" not in picked
    assert "spec/handlers/YSpec.php" not in picked
    assert "vendor/acme/src/controllers/X.php" not in picked
    assert "services/InvoiceService.php" not in picked


def test_a_declared_entry_point_outranks_the_vocabulary_and_says_so() -> None:
    """119 — a flow states whether its seed was declared or read from the vocabulary."""
    rows = dict(seed_files(["controllers/A.php", "bin/cron.php"], ["bin/*.php"]))
    assert rows["bin/cron.php"] == "declared"
    assert rows["controllers/A.php"] == "vocabulary"


# AC1 (225) — a source with two RESOLVED hops to a shared node: the EARLIER-line hop (`Zebra`, line
# 5) is ALPHABETICALLY later than the later-line hop (`Alpha`, line 50). Alphabetical order and call
# order therefore disagree, so a green test proves which one the module actually uses.
_ORDER_SEED = "App\\Ctrl::act"
_ORDER_FILE = {
    "App\\Ctrl::act": "controllers/Ctrl.php",
    "App\\Zebra::z": "lib/Zebra.php",
    "App\\Alpha::a": "lib/Alpha.php",
    "App\\Repo::save": "repositories/Repo.php",
    "dbo.T::C": "db/t.sql",
}
_ORDER_LAYER = {
    "controllers/Ctrl.php": "HTTP / Entry",
    "lib/Zebra.php": "Services",
    "lib/Alpha.php": "Services",
    "repositories/Repo.php": "Domain / Data",
    "db/t.sql": "Domain / Data",
}
_ORDER_EDGES = [
    ("App\\Ctrl::act", "App\\Zebra::z", "CALLS", "RESOLVED", 5),
    ("App\\Ctrl::act", "App\\Alpha::a", "CALLS", "RESOLVED", 50),
    ("App\\Zebra::z", "App\\Repo::save", "CALLS", "RESOLVED", 8),
    ("App\\Alpha::a", "App\\Repo::save", "CALLS", "RESOLVED", 9),
    ("App\\Repo::save", "dbo.T::C", "WRITES", "RESOLVED", 12),
]


def test_call_order_by_line_differs_from_alphabetical() -> None:
    """AC1 (R6.5) — the proving test: the trace follows CALL order, not alphabetical order.

    Pre-change `_adjacency` sorts a source's hops alphabetically, so it reaches the shared node
    through `Alpha` (alphabetically first). Post-change it sorts by line, so it reaches it through
    `Zebra` (called first, at line 5). This assertion fails on the old order and passes on the new.
    """
    result = build_flows(
        [(_ORDER_SEED, "vocabulary")], _ORDER_EDGES, _ORDER_FILE, _ORDER_LAYER,
        {"controllers": "web"}, max_flows=10, max_nodes=100,
    )
    flow = result.flows[0]
    qnames = [step.qname for step in flow.steps]
    assert flow.sink == "dbo.T::C"
    assert "App\\Zebra::z" in qnames, "the earlier-LINE hop is on the path"
    assert "App\\Alpha::a" not in qnames, "the alphabetically-first hop is NOT the call order"
    # The line rides onto the step it reached (AC1's carry-through).
    zebra = next(step for step in flow.steps if step.qname == "App\\Zebra::z")
    assert zebra.line == 5


def test_the_seed_step_and_a_carried_hop_expose_their_line() -> None:
    """The line is None on the seed (nothing reached it) and the real call line on each hop."""
    flow = _build([("App\\InvoiceController::show", "vocabulary")], CHAIN).flows[0]
    assert flow.steps[0].line is None
    assert [step.line for step in flow.steps[1:]] == [10, 20, 30]
    assert flow.steps[1].as_dict()["line"] == 10


def test_two_hops_sharing_a_line_report_an_unknown_order() -> None:
    """R5 (225) — a same-line pair out of one source cannot be ordered, so the line is dropped."""
    edges = [
        ("App\\Ctrl::act", "App\\Zebra::z", "CALLS", "RESOLVED", 7),
        ("App\\Ctrl::act", "App\\Alpha::a", "CALLS", "RESOLVED", 7),
        ("App\\Alpha::a", "dbo.T::C", "WRITES", "RESOLVED", 9),
    ]
    result = build_flows(
        [(_ORDER_SEED, "vocabulary")], edges, _ORDER_FILE, _ORDER_LAYER,
        {"controllers": "web"}, max_flows=10, max_nodes=100,
    )
    flow = result.flows[0]
    hop = next(step for step in flow.steps if step.qname in ("App\\Alpha::a", "App\\Zebra::z"))
    assert hop.line is None, "a hop tied on a line with a sibling has no known order"


def test_a_declared_stub_root_is_not_a_request_entry() -> None:
    """An operator who declares a tree vendored has said it is not their surface."""
    picked = dict(seed_files(["third_party/controllers/A.php"], [], ["third_party"]))
    assert picked == {}


def test_the_seed_signal_rides_onto_the_flow() -> None:
    """The provenance survives to the payload, not just to the selection."""
    result = _build([("App\\InvoiceController::show", "declared")], CHAIN)
    assert result.flows[0].signal == "declared"
    assert result.flows[0].as_dict()["signal"] == "declared"


def test_flow_edges_returns_the_kind_and_the_winning_tier(tmp_path) -> None:
    """The new SQL had no test of its own: every other test hand-builds its rows.

    `dependency_edges_with_tier` drops the kind, which is the whole reason this method exists — so
    the kind column, the kind filter and the RESOLVED-beats-DYNAMIC roll-up are asserted against a
    real ``edges`` table rather than assumed.
    """
    from code_atlas.store import GraphStore
    from tests.test_nav_tools import db_config, edge, node, seed_file

    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/repo/R.aa",
            [node("Method", "find", "\\R::find", "app/repo/R.aa")],
            [
                edge("WRITES", "\\R::find", "T::C", "app/repo/R.aa",
                     target_qname="T::C", tier="DYNAMIC"),
                edge("WRITES", "\\R::find", "T::C", "app/repo/R.aa",
                     target_qname="T::C", tier="RESOLVED"),
                edge("CALLS", "\\R::find", "T::C", "app/repo/R.aa", target_qname="T::C"),
            ],
            root=tmp_path,
        )
        writes = store.flow_edges(("WRITES",))
        both = store.flow_edges(("WRITES", "CALLS"))

    assert writes == [("\\R::find", "T::C", "WRITES", "RESOLVED", 1)], (
        "one row per (source, target, kind); RESOLVED beats DYNAMIC; CALLS out; MIN(line)=1"
    )
    assert len(both) == 2, "the kind filter widens with the kind set, and keeps kinds distinct"
    assert store_kinds(both) == {"CALLS", "WRITES"}


def test_flow_edges_takes_the_line_of_the_winning_tier_not_the_lowest(tmp_path) -> None:
    """225 — the reported line must belong to the winning tier.

    A plain ``MIN(line)`` over the whole (source, target, kind) group would hand a RESOLVED edge the
    call line of a losing DYNAMIC row to the same target, and the trace attests order on that line.
    """
    from code_atlas.store import GraphStore
    from tests.test_nav_tools import db_config, edge, node, seed_file

    with GraphStore(db_config(tmp_path).db_path) as store:
        seed_file(
            store,
            "app/repo/R.aa",
            [node("Method", "find", "\\R::find", "app/repo/R.aa")],
            [
                edge("WRITES", "\\R::find", "T::C", "app/repo/R.aa",
                     target_qname="T::C", tier="DYNAMIC", line=5),
                edge("WRITES", "\\R::find", "T::C", "app/repo/R.aa",
                     target_qname="T::C", tier="RESOLVED", line=50),
            ],
            root=tmp_path,
        )
        rows = store.flow_edges(("WRITES",))

    assert rows == [("\\R::find", "T::C", "WRITES", "RESOLVED", 50)], (
        "the line is the RESOLVED row's (50), never the losing DYNAMIC row's (5)"
    )


def store_kinds(rows) -> set:
    """The distinct edge kinds in a flow_edges result."""
    return {kind for _s, _t, kind, _tier, _line in rows}


def test_flow_edges_is_empty_for_an_empty_kind_set(tmp_path) -> None:
    """No kinds means no query at all — never an unfiltered dump of the edge table."""
    from code_atlas.store import GraphStore
    from tests.test_nav_tools import db_config

    with GraphStore(db_config(tmp_path).db_path) as store:
        assert store.flow_edges(()) == []
