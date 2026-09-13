"""Task 199 — one subject's capability flows, in a nav-sized payload.

197 measured the surface it tried and rejected it: `summary.flows` on `architecture_overview`
made an agent buy the whole overview to read one 4-file trace, and answered with *every* flow, so
a question about one request claimed six files belonging to other requests (`ratio 0.53`,
`precision 0.944`, `unexpected 6`). Both defects were the surface's — which is what this replaces.

The ground truth here was **hand-read from the fixture source before this tool existed**
(199 Scope 3) and is written out in the ticket's working doc; the assertions below are that
reading, not a recording of what the tool happened to return.
"""

from __future__ import annotations

import importlib.util
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from code_atlas.onboarding.dataset import build_dataset
from code_atlas.onboarding.flows import Flow, FlowStep
from code_atlas.store import GraphStore
from code_atlas.tools import trace_capability
from code_atlas.tools.nav_result import (
    REASON_NAME_NOT_QUALIFIED,
    REASON_NO_MATCHES,
    REASON_NO_SUCH_SYMBOL,
    REASON_NOT_INDEXED,
    REASON_OK,
)
from code_atlas.tools.trace_capability import (
    SUBJECT_MODULE,
    SUBJECT_PATH,
    SUBJECT_QNAME,
    _participates,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests" / "fixtures" / "php" / "onboarding"
HARNESS = REPO / "scripts" / "tokens_to_answer.py"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not (REPO / "adapters" / "php" / "vendor" / "autoload.php").is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

ENTRY = "\\Shop\\Controllers\\InvoiceController::index"

# The hand-read trace (working doc, Phase 0). Five hops, read from the fixture source by hand.
# The hand-read reading listed FIVE files, including `lib/Clock.php`. The model answers four, and
# the tool is right: `flows.py` traces one PATH to a sink, and `Clock::now` is called from two
# hops on the path without lying on it. The ticket says "from entry to the data it writes" —
# a path, not a reachable set. The discrepancy is recorded in the working doc rather than resolved
# by quietly editing the reading to match the output.
EXPECTED_FILES = {
    "controllers/InvoiceController.php",
    "services/InvoiceService.php",
    "repositories/InvoiceRepository.php",
    "models/Invoice.php",
}
REACHED_BUT_NOT_ON_THE_PATH = "lib/Clock.php"
# The six 197 wrongly claimed. Every one is reachable by `grep Invoice`, and none belongs to THIS
# request: three are other entries, one is required-but-never-called, two are unreferenced.
OTHER_REQUEST_FILES = {
    "jobs/ReminderJob.php",
    "reports/InvoiceReport.php",
    "legacy/RetiredExporter.php",
    "views/invoice_page.php",
    "config/settings.php",
}

# AC2: the whole payload, nothing aggregate. A new key here is a decision, never a drift.
ENVELOPE_KEYS = {
    "index_root",
    "indexed",
    "reason",
    "results",
    "subject",
    "subject_kind",
    "truncated",
}
FLOW_KEYS = {"seed", "seed_file", "module", "ended", "sink", "steps", "layers"}
OPTIONAL_ENVELOPE_KEYS = {"subsumed", "try_instead"}
STEP_KEYS = {"qname", "file", "layer", "kind", "tier"}


def _harness():
    spec = importlib.util.spec_from_file_location("tokens_to_answer", HARNESS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def fixture_index(tmp_path_factory: pytest.TempPathFactory):
    """The onboarding fixture, built the way the 121 harness builds it — same input as the gate."""
    harness = _harness()
    workdir = tmp_path_factory.mktemp("trace_capability")
    root = harness.prepare_fixture_root(FIXTURE, workdir)
    return harness.build_index(root, workdir / "graph.db", harness._DEFAULT_PHP)


def _files(payload: dict) -> set[str]:
    return {
        str(step["file"])
        for flow in payload["results"]
        for step in flow["steps"]
    } | {str(flow["seed_file"]) for flow in payload["results"]}


# --------------------------------------------------------------------------- the proving test


@needs_php
def test_one_request_is_traced_without_the_other_requests_files(fixture_index) -> None:
    """Proving test (R6.5). The half 197 could not pass is the second assertion, not the first.

    Observed red before this tool existed: no surface answered a per-subject flow question at all;
    the one 197 tried returned every flow and claimed 6 files belonging to other requests.
    """
    payload = trace_capability.create(fixture_index)(qname=ENTRY)

    assert payload["reason"] == REASON_OK
    assert _files(payload) == EXPECTED_FILES
    assert not _files(payload) & OTHER_REQUEST_FILES
    assert REACHED_BUT_NOT_ON_THE_PATH not in _files(payload)


@needs_php
def test_the_traced_hops_are_the_hand_read_ones_in_order(fixture_index) -> None:
    """The five hops, as read from the source before the tool existed."""
    payload = trace_capability.create(fixture_index)(qname=ENTRY)
    flows = payload["results"]

    assert len(flows) == 1, f"one entry, one path to the data; got {len(flows)}"
    assert payload["subsumed"] == 1, "the prefix path is dropped and the drop is reported"
    qnames = [str(step["qname"]) for step in flows[0]["steps"]]
    assert qnames[0] == ENTRY
    assert "\\Shop\\Services\\InvoiceService::recent" in qnames
    assert "\\Shop\\Repositories\\InvoiceRepository::findRecent" in qnames


# ------------------------------------------------------------------- AC2 — nothing aggregate


@needs_php
def test_ac2_the_payload_carries_no_aggregate_the_question_did_not_ask_for(fixture_index) -> None:
    """The defect 197 measured was the envelope, so the envelope is asserted as a KEY SET."""
    payload = trace_capability.create(fixture_index)(qname=ENTRY)

    assert set(payload) - OPTIONAL_ENVELOPE_KEYS == ENVELOPE_KEYS
    for flow in payload["results"]:
        assert set(flow) <= FLOW_KEYS
        for step in flow["steps"]:
            assert set(step) == STEP_KEYS
    # The named aggregates from `architecture_overview`, each absent by name rather than by count.
    for absent in ("layers_table", "matrix", "hubs", "reachability", "modules", "mirrors", "tree"):
        assert absent not in payload


# ------------------------------------------------------- AC1 — a refusal, never an empty list


@needs_php
def test_ac1_a_subject_the_index_does_not_hold_refuses_and_routes(fixture_index) -> None:
    payload = trace_capability.create(fixture_index)(qname="\\Shop\\Nope\\Missing::gone")

    assert payload["reason"] == REASON_NO_SUCH_SYMBOL
    assert payload["results"] == []
    assert payload["try_instead"] == "search_symbol"


@needs_php
def test_ac1_a_subject_that_joins_no_flow_refuses_rather_than_answering_empty(
    fixture_index,
) -> None:
    """`config/settings.php` is indexed and referenced by nothing — a real no-flow subject (182)."""
    payload = trace_capability.create(fixture_index)(path="config/settings.php")

    assert payload["reason"] == REASON_NO_MATCHES
    assert payload["results"] == []
    assert payload["try_instead"] == "architecture_overview"


def test_naming_no_subject_or_several_is_refused_not_guessed(tmp_path: Path) -> None:
    config = db_config(tmp_path)
    tool = trace_capability.create(config)

    assert tool()["reason"] == REASON_NAME_NOT_QUALIFIED
    assert tool(qname="\\A", path="a.php")["reason"] == REASON_NAME_NOT_QUALIFIED


def test_an_unbuilt_index_says_so_with_the_same_keys(tmp_path: Path) -> None:
    payload = trace_capability.create(db_config(tmp_path))(qname="\\A")

    assert payload["indexed"] is False
    assert payload["reason"] == REASON_NOT_INDEXED
    assert set(payload) == ENVELOPE_KEYS


# ------------------ the discrimination the ticket is about, which its own fixture cannot show


def _two_request_repo(tmp_path: Path):
    """Two entries sharing one service, so one request's answer can exclude the other's file.

    **The onboarding fixture cannot prove this.** Its four flow seeds are all the same controller —
    `ReminderJob`, `InvoiceReport` and `RetiredExporter` sit in `jobs/`, `reports/` and `legacy/`,
    none of which reads as an entry layer. So "every flow" and "this request's flows" are the same
    set there, and returning every flow passes any assertion made against it. 199's stated second
    defect needs two requests to be visible at all.
    """
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "controllers/InvoiceController.php",
            [
                node(
                    "Class", "InvoiceController", "\\App\\InvoiceController",
                    "controllers/InvoiceController.php",
                )
            ],
            [
                edge(
                    "CALLS",
                    "\\App\\InvoiceController",
                    "\\App\\Shared",
                    "controllers/InvoiceController.php",
                    target_qname="\\App\\Shared",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            "controllers/ReportController.php",
            [
                node(
                    "Class", "ReportController", "\\App\\ReportController",
                    "controllers/ReportController.php",
                )
            ],
            [
                edge(
                    "CALLS",
                    "\\App\\ReportController",
                    "\\App\\Shared",
                    "controllers/ReportController.php",
                    target_qname="\\App\\Shared",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            "services/Shared.php",
            [node("Class", "Shared", "\\App\\Shared", "services/Shared.php")],
            [
                edge(
                    "CALLS",
                    "\\App\\Shared",
                    "\\App\\Row",
                    "services/Shared.php",
                    target_qname="\\App\\Row",
                )
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            "models/Row.php",
            [node("Class", "Row", "\\App\\Row", "models/Row.php")],
            [],
            root=tmp_path,
        )
    return config


def test_one_request_s_answer_excludes_the_other_request_s_entry(tmp_path: Path) -> None:
    """The defect 199 names, made reproducible: two entries, one shared service.

    Returning every flow — 197's `summary.flows` behaviour — puts `ReportController.php` in the
    answer to a question about the invoice request. Filtering by subject does not.
    """
    config = _two_request_repo(tmp_path)
    payload = trace_capability.create(config)(qname="\\App\\InvoiceController")

    assert payload["reason"] == REASON_OK
    files = _files(payload)
    assert "controllers/InvoiceController.php" in files
    assert "services/Shared.php" in files
    assert "controllers/ReportController.php" not in files, (
        "a question about ONE request must not claim the other request's entry"
    )


# --------------------------------------------- the three subject kinds, and exact membership


@needs_php
def test_a_file_subject_matches_a_middle_hop_and_returns_the_WHOLE_flow(fixture_index) -> None:
    """W3: participation is membership, so a middle hop answers with the flow it belongs to.

    `services/InvoiceService.php` is not a seed. The answer still starts at the controller, because
    a suffix would be a second notion of a flow.
    """
    payload = trace_capability.create(fixture_index)(path="services/InvoiceService.php")

    assert payload["reason"] == REASON_OK
    assert payload["subject_kind"] == SUBJECT_PATH
    # Two flows, and NOT because one is redundant: the graph carries this request at two
    # granularities — a symbol trace over CALLS and a file trace over INCLUDES. Both start at the
    # controller. Suppressing one would need a "same request, two granularities" notion the model
    # does not have, which is the second notion of a flow the ticket forbids.
    seeds = {str(flow["seed"]) for flow in payload["results"]}
    assert seeds == {ENTRY, "controllers/InvoiceController.php"}
    for flow in payload["results"]:
        first = flow["steps"][0]
        assert str(first["qname"]) in {ENTRY, "controllers/InvoiceController.php"}, (
            "a middle-hop subject must answer with the WHOLE flow, never a suffix from itself"
        )


@needs_php
def test_membership_is_exact_never_a_shared_path_segment(fixture_index) -> None:
    """`deepest-wins-is-not-a-membership-test` (130, 131, 197) — a prefix must NOT match.

    `services` is a real directory segment of a real hop's file. A prefix or deepest-wins predicate
    would match the flow; exact equality must not.
    """
    payload = trace_capability.create(fixture_index)(path="services")

    assert payload["reason"] == REASON_NO_SUCH_SYMBOL
    assert payload["results"] == []


def _flow(seed: str, module: str | None, *steps: tuple[str, str]) -> Flow:
    return Flow(
        seed=seed,
        seed_file=steps[0][1],
        signal="declared",
        module=module,
        steps=tuple(
            FlowStep(qname=q, file=f, layer="Services", kind="CALLS", tier="RESOLVED")
            for q, f in steps
        ),
        ended="sink",
        sink=steps[-1][0],
        walk_truncated=False,
    )


def test_the_module_subject_matches_on_the_flow_s_own_module(fixture_index_unused=None) -> None:
    """W2: `Flow.module` carries the owner, so no reverse module->files lookup exists or is needed.

    Unit-tested on the predicate rather than skipped: the onboarding fixture attributes its flows to
    no business module, and a subject kind that ships with a SKIP behind it ships untested.
    """
    billing = _flow("\\Bill::run", "mod/billing", ("\\Bill::run", "mod/billing/Bill.php"))
    other = _flow("\\Ship::run", "mod/shipping", ("\\Ship::run", "mod/shipping/Ship.php"))

    assert _participates(billing, SUBJECT_MODULE, "mod/billing")
    assert not _participates(other, SUBJECT_MODULE, "mod/billing")
    # Exact, not a prefix: `mod` owns neither, and deepest-wins would claim it owns both.
    assert not _participates(billing, SUBJECT_MODULE, "mod")
    # A flow attributed to no module is never claimed by one.
    orphan = _flow("\\\\X::y", None, ("\\\\X::y", "x/X.php"))
    assert not _participates(orphan, SUBJECT_MODULE, "mod/billing")


def test_the_qname_and_path_predicates_are_exact_too() -> None:
    """The same membership rule on the other two kinds — 130/131/197's class, all three arms."""
    flow = _flow(
        "\\Shop\\A::go",
        "mod/a",
        ("\\Shop\\A::go", "controllers/A.php"),
        ("\\Shop\\B::run", "services/B.php"),
    )

    assert _participates(flow, SUBJECT_QNAME, "\\Shop\\B::run")
    assert not _participates(flow, SUBJECT_QNAME, "\\Shop\\B")
    assert _participates(flow, SUBJECT_PATH, "services/B.php")
    assert not _participates(flow, SUBJECT_PATH, "services")


# ------------------------------- R5.6 — the incomplete answer must SAY it may be incomplete


def test_a_globally_cut_flow_makes_the_answer_declare_itself_incomplete(tmp_path: Path) -> None:
    """R5.6, and the challenger's mutation: `_incomplete` returning False must be catchable.

    `build_flows` ranks every seed's flows and CUTS at a global cap, so a flow this subject takes
    part in can be missing for a reason that has nothing to do with the subject. An answer that
    reported `truncated: false` there would be a silent partial — which is exactly what the
    one-line mutation `return False` produces, and what nothing else here would notice.
    """
    config = replace(_two_request_repo(tmp_path), page_limit=1)
    tool = trace_capability.create(config)

    # The subject whose seed the cap DID trace still answers — and still says it may be partial.
    answered = tool(qname="\\App\\InvoiceController")
    assert answered["reason"] == REASON_OK
    assert answered["truncated"] is True

    # The subject whose seed the cap did NOT trace is the dangerous one: it has a flow, it is
    # indexed, and a bare `no_matches` here is a refusal that is confidently WRONG.
    refused = tool(qname="\\App\\ReportController")
    assert refused["reason"] == REASON_NO_MATCHES
    assert refused["truncated"] is True, (
        "this subject HAS a flow; the cap never traced its seed, so the zero is not proven"
    )


def test_an_uncut_answer_does_not_claim_to_be_incomplete(tmp_path: Path) -> None:
    """The other half: without a cut, `truncated` is False — or the flag says nothing at all."""
    payload = trace_capability.create(_two_request_repo(tmp_path))(qname="\\App\\InvoiceController")

    assert payload["truncated"] is False


# ------------------------------------- AC4 — one derivation, proven by agreement not by structure


@needs_php
def test_the_tool_and_the_map_agree_about_the_same_flows(fixture_index) -> None:
    """AC4's real risk is drift, and factoring alone does not prove its absence — this does.

    `flows_from_graph` is shared, but the two callers assemble its inputs separately. If they ever
    disagree, the tool would attribute a file to a different layer than the committed map does.
    """
    config = fixture_index
    with GraphStore(config.db_path) as store:
        nodes = store.node_universe()
        edge_tiers = store.dependency_edges_with_tier()
        dataset = build_dataset(
            nodes,
            [(s, t) for s, t, _tier in edge_tiers],
            files=store.counts()["files"],
            parsed=store.counts()["parsed"],
            node_kind_counts=store.node_kind_counts(),
            edge_kind_counts=store.edge_kind_counts(),
            confidence=store.edge_health()["by_tier"],  # type: ignore[arg-type]
            hubs=store.module_hubs(limit=config.page_limit),
            classes=store.largest_classes(limit=config.page_limit),
            file_symbol_counts=store.file_symbol_counts(),
            file_paths=store.file_paths(),
            path_index_max=config.path_index_max,
            declared_entry_points=config.entry_points,
            declared_stub_roots=config.stub_roots,
            file_class_counts=store.file_class_counts(),
            module_max=config.page_limit,
            flow_edges=store.flow_edges(
                __import__(
                    "code_atlas.onboarding.flows", fromlist=["FLOW_KINDS"]
                ).FLOW_KINDS
            ),
            flow_max=config.page_limit,
            flow_max_nodes=config.impact_max_nodes,
        )
    assert dataset.flows is not None
    from_map = {
        tuple((step.qname, step.file, step.layer) for step in flow.steps)
        for flow in dataset.flows.flows
        if flow.seed == ENTRY
    }
    payload = trace_capability.create(config)(qname=ENTRY)
    from_tool = {
        tuple((str(s["qname"]), str(s["file"]), str(s["layer"])) for s in flow["steps"])
        for flow in payload["results"]
    }

    # Containment, not equality: the tool drops a path that is a strict prefix of another (the map
    # keeps both, and ranks them for a reader). Every path it DOES show must be one the map shows,
    # step for step, with the same file and the same layer — that is what would catch drift.
    assert from_tool, "the tool returned nothing to compare"
    assert from_tool <= from_map, "the tool shows a path the map does not"


def test_the_subject_kinds_are_the_three_the_ticket_names() -> None:
    assert {SUBJECT_QNAME, SUBJECT_PATH, SUBJECT_MODULE} == {"qname", "path", "module"}
