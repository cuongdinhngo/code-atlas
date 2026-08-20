"""Task 086: the ``architecture_overview`` tool over a fixture repo (§12, PHASE3 §4).

Proving path is the tool itself — the layer maths is 084/103/104's suite; what is unproven until
here is that a caller receives the layers, the crossings and the conventions (071 ``index_root``,
033/065 reason + ``total_count``, 061 ``detail_level``) in one payload. The fixture uses the
language-neutral ``.aa`` suffix, so nothing in the proof knows which language produced the rows
(AC2).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from code_atlas.config import Config
from code_atlas.onboarding.summary import NodeFacts, Summary
from code_atlas.store import GraphStore
from code_atlas.tools import architecture_overview
from code_atlas.tools.nav_result import (
    REASON_NO_MATCHES,
    REASON_NOT_INDEXED,
    REASON_OK,
)
from tests.test_nav_tools import db_config, edge, node, seed_file

HTTP = "app/Http/UserController.aa"
MODEL = "app/Models/User.aa"
ACCOUNT = "app/Models/Account.aa"
SERVICE = "app/Services/Billing.aa"
ROUTES = "routes/web.aa"


def _fixture_repo(tmp_path: Path) -> Config:
    """A repo whose directories name responsibilities (models, services, routes) plus ``app/Http``,
    which matches no keyword and reads Uncategorised (110).

    The ``app/Http`` controller depends on Models and Services; routes/ depends on it, so ordering
    is decided by dependency direction. Account -> User is an INTRA-layer edge (Domain / Data) on
    purpose: without one, "a crossing is never same-layer" cannot fail.
    """
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            HTTP,
            [node("Class", "UserController", "\\App\\Http\\UserController", HTTP)],
            [
                edge("CALLS", "\\App\\Http\\UserController", "\\App\\Models\\User", HTTP,
                     target_qname="\\App\\Models\\User"),
                edge("CALLS", "\\App\\Http\\UserController", "\\App\\Services\\Billing", HTTP,
                     target_qname="\\App\\Services\\Billing"),
            ],
            root=tmp_path,
        )
        seed_file(
            store, MODEL, [node("Class", "User", "\\App\\Models\\User", MODEL)], [], root=tmp_path
        )
        seed_file(
            store,
            ACCOUNT,
            [node("Class", "Account", "\\App\\Models\\Account", ACCOUNT)],
            [
                edge("CALLS", "\\App\\Models\\Account", "\\App\\Models\\User", ACCOUNT,
                     target_qname="\\App\\Models\\User"),
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            SERVICE,
            [node("Class", "Billing", "\\App\\Services\\Billing", SERVICE)],
            [
                edge("CALLS", "\\App\\Services\\Billing", "\\App\\Models\\User", SERVICE,
                     target_qname="\\App\\Models\\User"),
            ],
            root=tmp_path,
        )
        seed_file(
            store,
            ROUTES,
            [node("Function", "web", "\\web", ROUTES)],
            [
                edge("CALLS", "\\web", "\\App\\Http\\UserController", ROUTES,
                     target_qname="\\App\\Http\\UserController"),
            ],
            root=tmp_path,
        )
    return config


def _layers(payload: dict[str, object]) -> list[str]:
    rows = payload["results"]
    assert isinstance(rows, list)
    return [str(row["layer"]) for row in rows]


# --- AC3 · the proving test ----------------------------------------------------------------------


def test_architecture_overview_reports_the_known_layer_split_of_a_fixture_repo(
    tmp_path: Path,
) -> None:
    """Proving test: the known split reaches the caller, ordered, counted and named."""
    overview = architecture_overview.create(_fixture_repo(tmp_path))()

    assert overview["indexed"] is True
    assert overview["reason"] == REASON_OK
    assert overview["method"] == "responsibility"
    # controllers/models/services/routes name responsibilities; app/Http itself matches no keyword
    # and reads Uncategorised — reported, not hidden (110).
    assert set(_layers(overview)) == {"HTTP / Entry", "Uncategorised", "Services", "Domain / Data"}
    assert "app" not in _layers(overview)
    assert overview["total_count"] == 4
    assert _layers(overview)[-1] == "Domain / Data"  # pure sink: nothing it depends on
    assert {"source": "Services", "target": "Domain / Data", "count": 1} in (
        overview["cross_layer_edges"]
    )
    assert {"source": "HTTP / Entry", "target": "Uncategorised", "count": 1} in (
        overview["cross_layer_edges"]
    )
    # Account -> User lives inside Domain / Data; a crossing carrying it is not a crossing list.
    for crossing in overview["cross_layer_edges"]:
        assert crossing["source"] != crossing["target"]


# --- AC3 · payload shape at every detail level ---------------------------------------------------


def test_minimal_omits_the_costly_blocks_and_verbose_adds_the_module_rows(tmp_path: Path) -> None:
    """061: the cheap path stays cheap; the unbounded list rides ``verbose`` alone."""
    config = _fixture_repo(tmp_path)

    minimal = architecture_overview.create(config)(detail_level="minimal")
    assert "summary" not in minimal and "cross_layer_edges" not in minimal
    assert "modules" not in minimal
    assert set(minimal["results"][0]) == {"layer", "description", "rank", "modules"}

    standard = architecture_overview.create(config)(detail_level="standard")
    assert set(standard["results"][0]) == {
        "layer", "description", "rank", "modules", "fan_in", "fan_out", "entry_points"
    }
    assert standard["summary"] == {
        "layers": 4,
        "modules": 5,
        "symbols": 5,
        "module_entry_points": 2,
        "cross_layer_edges": len(standard["cross_layer_edges"]),
        "method": "responsibility",
    }
    assert standard["cross_layer_edges_truncated"] is False
    assert "modules" not in standard

    verbose = architecture_overview.create(config)(detail_level="verbose")
    assert verbose["modules_truncated"] is False and verbose["modules_offset"] == 0
    assert sorted(row["module"] for row in verbose["modules"]) == sorted(
        [HTTP, MODEL, ACCOUNT, SERVICE, ROUTES]
    )
    # Layer order, not path order: rank 0 leads, so a capped page starts at the entry layer.
    assert [row["rank"] for row in verbose["modules"]] == sorted(
        row["rank"] for row in verbose["modules"]
    )
    http_row = next(row for row in verbose["modules"] if row["module"] == HTTP)
    assert http_row["layer"] == "Uncategorised" and http_row["direction"] == "mixed"
    assert http_row["role"] == "connector"  # through the 085 seam, not a local table


def test_every_outcome_carries_the_payload_conventions(tmp_path: Path) -> None:
    """071 + 033/065: ``index_root``, a reason and a count on every answer, including the zeroes."""
    config = _fixture_repo(tmp_path)
    for level in ("minimal", "standard", "verbose"):
        payload = architecture_overview.create(config)(detail_level=level)
        assert payload["index_root"] == config.index_root
        assert payload["reason"] == REASON_OK
        assert payload["total_count"] == len(payload["results"])


def test_an_unbuilt_index_is_not_the_same_answer_as_an_empty_one(tmp_path: Path) -> None:
    """033/065: absence of an index and an index holding nothing are different facts."""
    unbuilt = architecture_overview.create(db_config(tmp_path))()
    assert unbuilt == {
        "indexed": False,
        "results": [],
        "truncated": False,
        "reason": REASON_NOT_INDEXED,
        "total_count": 0,
        "index_root": db_config(tmp_path).index_root,
    }
    assert not (tmp_path / "graph.db").exists()  # a read tool must not create the index

    config = db_config(tmp_path)
    with GraphStore(config.db_path):
        pass
    empty = architecture_overview.create(config)()
    assert empty["indexed"] is True and empty["reason"] == REASON_NO_MATCHES
    assert empty["results"] == [] and empty["total_count"] == 0


# --- AC3 · the caps and the seam ------------------------------------------------------------------


def test_the_module_page_is_capped_and_offset_reaches_the_rest(tmp_path: Path) -> None:
    """The cap is honest AND escapable: no layer's modules are unreachable (057 paging idiom)."""
    config = replace(_fixture_repo(tmp_path), max_results=2)
    tool = architecture_overview.create(config)

    first = tool(detail_level="verbose")
    assert len(first["modules"]) == 2
    assert first["modules_truncated"] is True and first["modules_offset"] == 0

    # The two flags are independent: 4 layers fit under a cap of 4, the 5 modules do not — so a
    # cut module page must NOT be reported as a cut layer list (the pre-fix conflation).
    roomy = architecture_overview.create(replace(_fixture_repo(tmp_path), max_results=4))
    page = roomy(detail_level="verbose")
    assert page["truncated"] is False and page["total_count"] == 4
    assert page["modules_truncated"] is True

    walked = []
    for offset in (0, 2, 4):
        page = tool(detail_level="verbose", offset=offset)
        assert page["modules_offset"] == offset
        walked += [row["module"] for row in page["modules"]]
    assert sorted(walked) == sorted([HTTP, MODEL, ACCOUNT, SERVICE, ROUTES])
    assert {row["layer"] for row in tool(detail_level="verbose", offset=4)["modules"]} <= {
        "Domain / Data"
    }
    assert tool(detail_level="verbose", offset=4)["modules_truncated"] is False


def test_the_layer_list_and_the_crossings_are_capped_like_every_other_tool(
    tmp_path: Path,
) -> None:
    """A layer is a SUBdirectory of the dominant tree, so neither list is small by construction."""
    config = replace(_fixture_repo(tmp_path), max_results=2)
    standard = architecture_overview.create(config)(detail_level="standard")

    assert len(standard["results"]) == 2
    assert standard["truncated"] is True  # `truncated` describes `results` (nav_result convention)
    assert standard["total_count"] == 4  # the count is the full layer count, before the cap
    assert len(standard["cross_layer_edges"]) <= 2
    assert standard["cross_layer_edges_truncated"] is (
        standard["summary"]["cross_layer_edges"] > 2
    )


def test_offset_is_refused_outside_verbose_and_when_negative(tmp_path: Path) -> None:
    """Fail loud on a bad argument rather than silently answering a different question (R5.3)."""
    tool = architecture_overview.create(_fixture_repo(tmp_path))

    for bad in ({"offset": -1}, {"offset": 1, "detail_level": "standard"}):
        try:
            tool(**bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad} was accepted")


def test_an_injected_summarizer_reaches_the_module_rows_through_the_085_seam(
    tmp_path: Path,
) -> None:
    """R1.2: 090 plugs an LLM impl in here, so prove the seam is the path, not a local table."""

    class Loud:
        def summarize(self, facts: NodeFacts) -> Summary:
            return Summary(facts.metric.key, "", "", "injected")

    verbose = architecture_overview.create(_fixture_repo(tmp_path), Loud())(detail_level="verbose")

    assert {row["role"] for row in verbose["modules"]} == {"injected"}


def test_the_default_summarizer_is_deterministic_across_calls(tmp_path: Path) -> None:
    """R4.2: identical input, byte-identical payload — the property the whole core is held to."""
    config = _fixture_repo(tmp_path)
    first = architecture_overview.create(config)(detail_level="verbose")
    second = architecture_overview.create(config)(detail_level="verbose")

    assert first == second
