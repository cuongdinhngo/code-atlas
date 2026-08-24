"""Task 118 — module facts via read-through feed the 085 summarizer seam."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from code_atlas.onboarding.artifact import (
    NO_DOCBLOCK,
    OUTPUT_DIR,
    ModulePage,
    page_relpath,
    render_module,
)
from code_atlas.onboarding.metrics import NodeMetric
from code_atlas.onboarding.module_facts import module_facts, signature_for
from code_atlas.onboarding.summary import NodeFacts, StructuralSummarizer
from code_atlas.store import GraphStore
from code_atlas.tools import architecture_overview, generate_onboarding
from onboarding_llm.summarizer import _prompt
from tests.test_nav_tools import db_config, edge, node, seed_file

DOC = "/** Handles billing for the screen. */\n"


def test_module_facts_read_docblock_and_signature(tmp_path: Path) -> None:
    """AC2: the summary source is the file's own leading doc comment."""
    path = "src/Billing.aa"
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{DOC}class Billing {{\n}}\n", encoding="utf-8")
    row = node("Class", "Billing", "\\Billing", path)
    row["line_start"] = 2
    metric = NodeMetric(path, 0, 0, "isolated")
    facts = module_facts(tmp_path, path, metric, [row])
    assert facts.signature == "class Billing"
    assert "Handles billing" in facts.doc


def test_render_module_never_shows_summary_none_for_missing_docblock() -> None:
    """AC3: absence is attributed to the file, not rendered as ``(none)``."""
    page = ModulePage(
        file="x.aa",
        relpath=page_relpath("x.aa"),
        layer="core",
        rank=0,
        role="standalone",
        docline="",
        rationale="entry",
        scc=(),
        index=1,
        of=1,
        outgoing=(),
        incoming=(),
        fan_in=0,
        fan_out=0,
    )
    text = render_module(page, max_results=50)
    assert NO_DOCBLOCK in text
    assert "## Summary\n\n(none)" not in text


def test_isolation_rule_respects_non_empty_docline(tmp_path: Path) -> None:
    """AC5: a docline can keep an edgeless module off the isolated list."""
    config = db_config(tmp_path)
    path = "scripts/alone.aa"
    row = node("Class", "Alone", "\\Alone", path)
    row["line_start"] = 2
    with GraphStore(config.db_path) as store:
        seed_file(store, path, [row], [], root=tmp_path)
    (tmp_path / path).write_text(f"{DOC}class Alone {{\n}}\n", encoding="utf-8")
    payload = generate_onboarding.create(config)()
    assert payload["isolated_modules"] == 0
    page = (_out(tmp_path) / "modules" / f"{path}.md").read_text(encoding="utf-8")
    assert "Handles billing" in page


def test_llm_prompt_receives_non_empty_doc_and_signature() -> None:
    """AC4: the 090 implementer is fed real facts at the seam."""
    metric = NodeMetric("app/Foo.php", 1, 2, "mixed")
    loaded = NodeFacts("class Foo", "The user model.", metric)
    base = StructuralSummarizer().summarize(loaded)
    prompt = _prompt(loaded, base)
    assert "class Foo" in prompt
    assert "The user model." in prompt
    assert "Docblock: (none)" not in prompt


def test_generate_onboarding_module_page_carries_read_through_summary(tmp_path: Path) -> None:
    """End-to-end: a file docblock reaches the module page summary."""
    config = db_config(tmp_path)
    path = "src/A.aa"
    row = node("Class", "A", "\\A", path)
    row["line_start"] = 2
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            path,
            [row],
            [edge("CALLS", "\\A", "\\B", path, target_qname="\\B")],
            root=tmp_path,
        )
        seed_file(
            store,
            "src/B.aa",
            [node("Class", "B", "\\B", "src/B.aa")],
            [],
            root=tmp_path,
        )
    (tmp_path / path).write_text(f"{DOC}class A {{\n}}\n", encoding="utf-8")
    generate_onboarding.create(config)()
    text = (_out(tmp_path) / "modules" / f"{path}.md").read_text(encoding="utf-8")
    assert "Handles billing" in text
    summary_block = text.split("## Summary", 1)[1].split("##", 1)[0]
    assert NO_DOCBLOCK not in summary_block


def test_signature_for_includes_params() -> None:
    row = node("Method", "save", "\\Repo::save", "a.php")
    row["params"] = "x, y"
    assert signature_for(row) == "method save(x, y)"


def _out(root: Path) -> Path:
    return root / OUTPUT_DIR


def _seed_many(config, root: Path, count: int) -> None:
    """``count`` documented single-class modules, each with one edge onto the next."""
    with GraphStore(config.db_path) as store:
        for index in range(count):
            path = f"src/mod{index}/File{index}.aa"
            row = node("Class", f"C{index}", f"\\C{index}", path)
            row["line_start"] = 2
            seed_file(
                store,
                path,
                [row],
                [edge("CALLS", f"\\C{index}", f"\\C{(index + 1) % count}", path,
                      target_qname=f"\\C{(index + 1) % count}")],
                root=root,
            )
            (root / path).write_text(f"{DOC}class C{index} {{\n}}\n", encoding="utf-8")


def test_overview_read_through_is_bounded_to_the_page_it_renders(tmp_path: Path) -> None:
    """The read-through load must scale with the rendered page, not with the whole index.

    Eager-loading every indexed file cost one query per file — five times the tool's own two
    graph loads at 30k files — to feed at most ``max_results`` rows, and billed it to
    ``minimal`` as well, which 061 designates the cheap path.
    """
    config = replace(db_config(tmp_path), max_results=3)
    _seed_many(config, tmp_path, 24)
    seen: list[str] = []
    real = GraphStore.nodes_by_file_all

    def spy(self: GraphStore, path: str):
        seen.append(path)
        return real(self, path)

    overview = architecture_overview.create(config)
    with patch.object(GraphStore, "nodes_by_file_all", spy):
        for level in ("minimal", "standard"):
            seen.clear()
            overview(detail_level=level)
            assert seen == [], f"{level} paid for read-through it never renders: {len(seen)}"
        seen.clear()
        payload = overview(detail_level="verbose")
    assert len(payload["modules"]) == 3
    assert seen == [row["module"] for row in payload["modules"]]


def test_overview_feeds_the_seam_the_docblock_it_read(tmp_path: Path) -> None:
    """The bounded load still reaches the 085 seam with real facts, not empty strings."""
    config = replace(db_config(tmp_path), max_results=3)
    _seed_many(config, tmp_path, 8)
    captured: list[NodeFacts] = []

    class Recording(StructuralSummarizer):
        def summarize(self, facts: NodeFacts):
            captured.append(facts)
            return super().summarize(facts)

    architecture_overview.create(config, summarizer=Recording())(detail_level="verbose")
    assert len(captured) == 3
    assert all("Handles billing" in fact.doc for fact in captured)
    assert all(fact.signature.startswith("class C") for fact in captured)
