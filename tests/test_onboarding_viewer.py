"""Task 089: generate_onboarding emits a self-contained offline HTML viewer (PHASE3 §4).

The page must open from the filesystem with no server, no CDN, and no fetch — so the generator
embeds the 088 artifact. CI asserts that shape and determinism, not visual polish.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from code_atlas.config import Config
from code_atlas.onboarding.artifact import OUTPUT_DIR, VIEWER_NAME
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_guided_tour import LEAF, ROUTES, A, B, _cycle_repo
from tests.test_nav_tools import db_config, edge, node, seed_file


def _html(root: Path) -> str:
    return (root / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")


def _payload(html: str) -> dict[str, object]:
    match = re.search(
        r'<script type="application/json" id="payload">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match is not None
    found = json.loads(match.group(1))
    assert isinstance(found, dict)
    return found


def test_generate_onboarding_writes_a_self_contained_offline_viewer(tmp_path: Path) -> None:
    """Proving test: one HTML file, no network, layers + tour + pages, light/dark, stable."""
    config = _cycle_repo(tmp_path)
    tool = generate_onboarding.create(config)
    payload = tool()
    html = _html(tmp_path)

    assert f"{OUTPUT_DIR}/{VIEWER_NAME}" in payload["results"]
    assert html.startswith("<!DOCTYPE html>")
    assert "prefers-color-scheme" in html
    assert "color-scheme" in html
    assert "connect-src 'none'" in html
    assert "<script src" not in html
    assert "fetch(" not in html
    assert "http://" not in html
    assert "https://" not in html
    low = html.lower()
    assert "cdn" not in low
    for lang in ("php", "javascript", "typescript", "csharp", "roslyn", "nikic"):
        assert lang not in low

    data = _payload(html)
    stops = [str(row["file"]) for row in data["stops"]]  # type: ignore[index]
    assert stops[0] == ROUTES
    assert set(stops[1:3]) == {A, B}
    assert stops[-1] == LEAF
    files = {str(row["file"]) for row in data["pages"]}  # type: ignore[index]
    assert files == {ROUTES, A, B, LEAF}
    layers = data["layers"]
    assert isinstance(layers, list) and layers
    assert data["truncated"] is False

    second = tool()
    assert payload == second
    assert _html(tmp_path) == html


def test_viewer_is_refused_when_the_tree_is_not_ours(tmp_path: Path) -> None:
    """index.html without a manifest is someone else's file (088-C1 / 050)."""
    config = _cycle_repo(tmp_path)
    foreign = tmp_path / OUTPUT_DIR / VIEWER_NAME
    foreign.parent.mkdir(parents=True, exist_ok=True)
    foreign.write_text("<!DOCTYPE html><title>hand</title>\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not written by generate_onboarding"):
        generate_onboarding.create(config)()

    assert foreign.read_text(encoding="utf-8") == "<!DOCTYPE html><title>hand</title>\n"


def test_unbuilt_generate_does_not_write_a_viewer(tmp_path: Path) -> None:
    generate_onboarding.create(db_config(tmp_path))()
    assert not (tmp_path / OUTPUT_DIR / VIEWER_NAME).exists()


# A directory named ``a<`` holding ``script>…`` makes the path STRING carry ``</script>`` — the
# one input that can end the JSON block early and leave the rest as live markup.
BREAKOUT_FILE = "a</script><img src=x onerror=alert(1)>.aa"


def _breakout_repo(tmp_path: Path) -> Config:
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            BREAKOUT_FILE,
            [node("Class", "X", "\\X", BREAKOUT_FILE)],
            [edge("CALLS", "\\X", "\\Z", BREAKOUT_FILE, target_qname="\\Z")],
            root=tmp_path,
        )
        seed_file(store, "z.aa", [node("Class", "Z", "\\Z", "z.aa")], [], root=tmp_path)
    return config


def test_a_repo_path_cannot_break_out_of_the_payload_script_tag(tmp_path: Path) -> None:
    """Made to fail: drop the ``<`` escape in ``render_viewer`` and this test goes red."""
    generate_onboarding.create(_breakout_repo(tmp_path))()
    html = _html(tmp_path)

    assert html.count("</script>") == 2, "only the two template script tags may close"
    assert "<img src=x onerror" not in html
    data = _payload(html)
    files = {str(row["file"]) for row in data["pages"]}  # type: ignore[index]
    assert BREAKOUT_FILE in files, "the path is still readable, just not executable"


def test_the_viewer_degrades_without_scripting_and_declares_its_language(
    tmp_path: Path,
) -> None:
    """A blank page is not an offline viewer: say where the markdown is."""
    generate_onboarding.create(_cycle_repo(tmp_path))()
    html = _html(tmp_path)

    assert '<html lang="en">' in html
    assert "<noscript" in html
    assert "overview.md" in html and "tour.md" in html


def test_the_viewer_names_the_modules_it_has_no_page_for(tmp_path: Path) -> None:
    """107: the embedded payload carries the suppressed list, so the page cannot imply coverage.

    The stop list still holds every module; the viewer already answers a stop with no page
    ("No page for this stop."), so a suppressed module is visible, not a dead link.
    """
    from tests.test_generate_onboarding import _sparse_repo

    config = _sparse_repo(tmp_path)
    generate_onboarding.create(config)()
    html = _html(tmp_path)
    payload = _payload(html)

    isolated = [f"scripts/s{index:02d}.aa" for index in range(3)]
    assert payload["isolated"] == isolated
    assert [page["file"] for page in payload["pages"]] == ["src/A.aa", "src/B.aa"]
    assert {stop["file"] for stop in payload["stops"]} == set(isolated) | {
        "src/A.aa",
        "src/B.aa",
    }
    assert "no page (isolated, no summary): " in html
    assert "No page for this stop." in html
