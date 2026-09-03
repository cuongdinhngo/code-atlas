"""207 — the artifact answers a newcomer's first questions, quoted and cited.

Every assertion reads the EMITTED `overview.md`, never a payload dict (R6.9 / LESSONS 127-C1).
The malformed-manifest fixture is checked failing first: with the degradation removed it raises,
which is what makes AC4's guard a guard (R6.5).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from code_atlas.onboarding.artifact import H_ORIENTATION, MANIFEST_NAME, OUTPUT_DIR, OVERVIEW_NAME
from code_atlas.onboarding.orientation import (
    DEFAULT_PROJECT_FILES,
    MIN_EXCERPT_CHARS,
    read_orientation,
)
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from tests.test_nav_tools import db_config, edge, node, seed_file

COMPOSER = """{
  "name": "acme/demo",
  "require": {
    "php-does-not-appear-here": "^1.0",
    "ext-json": "*",
    "acme/lib": "^1.0"
  },
  "scripts": {
    "test": "phpunit --colors",
    "serve": "serve -t public"
  }
}
"""

COMPOSE = """services:
  web:
    image: some-proxy
    ports:
      - "8080:80"
"""

MAKEFILE = "up:\n\tcompose up -d\n"

README = (
    "# Acme Demo\n\nAcme Demo is the ordering service that fronts the warehouse API for the "
    "retail estate.\n"
)


def _repo(tmp_path: Path, files: dict[str, str] | None = None) -> object:
    """An indexed two-module repo, plus whatever declared project files the test wants.

    A mapping, not kwargs: `docker-compose.yml` is not a Python identifier.
    """
    config = db_config(tmp_path)
    with GraphStore(config.db_path) as store:
        seed_file(
            store,
            "app/Http/C.aa",
            [node("Class", "C", "\\App\\C", "app/Http/C.aa")],
            [edge("CALLS", "\\App\\C", "\\App\\M", "app/Http/C.aa", target_qname="\\App\\M")],
            root=tmp_path,
        )
        seed_file(
            store,
            "app/Models/M.aa",
            [node("Class", "M", "\\App\\M", "app/Models/M.aa")],
            [],
            root=tmp_path,
        )
    for name, text in (files or {}).items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return config


def _overview(root: Path) -> str:
    return (root / OUTPUT_DIR / OVERVIEW_NAME).read_text(encoding="utf-8")


def test_the_overview_opens_with_the_orientation_section(tmp_path: Path) -> None:
    """AC1 — above the aggregates, and every line carries the path it came from."""
    config = _repo(tmp_path, {"composer.json": COMPOSER, "README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert H_ORIENTATION in overview
    assert overview.index(H_ORIENTATION) < overview.index("## Summary"), "not above the aggregates"
    assert "Acme Demo is the ordering service" in overview
    assert "`README.md:3`" in overview


def test_a_declared_test_command_is_reproduced_verbatim(tmp_path: Path) -> None:
    """AC2, first half — the command as written, not a paraphrase."""
    config = _repo(tmp_path, {"composer.json": COMPOSER})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert "How to run the tests" in overview
    assert "`test`: `phpunit --colors` — `composer.json:9`" in overview


def test_a_repo_declaring_no_test_command_says_so(tmp_path: Path) -> None:
    """AC2, second half — an absence is stated, never silent (186's rule)."""
    config = _repo(tmp_path, {"README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert "no declared test command was found in the project files read" in overview
    assert "How to run the tests" not in overview


def test_a_named_sample_appears_beside_the_count_that_claims_it(tmp_path: Path) -> None:
    """AC3 / Scope 4 — the sample was in the dataset since 113 and no renderer printed it."""
    config = _repo(tmp_path, {"README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert "  - for example: " in overview, "a bucket count still names nothing the reader can open"
    assert "`app/Http/C.aa`" in overview


def test_a_malformed_manifest_degrades_to_a_stated_gap(tmp_path: Path) -> None:
    """AC4 — deliberately broken JSON must not abort the build (R5.3's posture)."""
    config = _repo(tmp_path, {"composer.json": '{"scripts": {"test": ', "README.md": README})
    payload = generate_onboarding.create(config)()  # type: ignore[arg-type]
    assert payload["indexed"] is True, "the build aborted on a consumer repo's broken manifest"
    overview = _overview(tmp_path)
    assert "`composer.json` is not valid JSON" in overview
    assert "no facts taken from it" in overview


def test_a_compose_file_it_cannot_parse_states_that_rather_than_guessing(tmp_path: Path) -> None:
    """R5.6 — a guessed service name is worse than a stated absence."""
    anchored = "x-base: &base\n  image: shared\nservices:\n  web:\n    <<: *base\n"
    config = _repo(tmp_path, {"docker-compose.yml": anchored, "README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    assert "which this shallow reader does not parse" in overview
    assert "Declared services" not in overview


def test_every_orientation_line_resolves_to_a_source_or_is_a_stated_gap(tmp_path: Path) -> None:
    """AC5, asserted at the consumer — no sentence is generated from an uncited value."""
    config = _repo(
        tmp_path,
        {
            "composer.json": COMPOSER,
            "docker-compose.yml": COMPOSE,
            "Makefile": MAKEFILE,
            "README.md": README,
        },
    )
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    overview = _overview(tmp_path)
    section = overview.split(H_ORIENTATION, 1)[1].split("## Summary", 1)[0]
    gaps = ("no declared", "no README", "read:", "not valid", "shallow reader", "more, not shown")
    for line in section.splitlines():
        if not line.startswith("- "):
            continue
        if any(marker in line for marker in gaps):
            continue
        assert re.search(r"— `[^`]+`$", line), f"uncited orientation line: {line!r}"


def test_a_repo_with_no_declared_project_files_omits_the_section(tmp_path: Path) -> None:
    """AC6 — the section is omitted, not emitted empty, and nothing else moves."""
    config = _repo(tmp_path)
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    with_none = _overview(tmp_path)
    assert H_ORIENTATION not in with_none
    assert with_none.startswith("# Architecture overview\n\n## Summary")


def test_two_runs_over_one_tree_are_byte_identical(tmp_path: Path) -> None:
    """R4.2 — file order and excerpt boundaries are a function of the bytes on disk."""
    config = _repo(tmp_path, {"composer.json": COMPOSER, "Makefile": MAKEFILE, "README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    first = _overview(tmp_path)
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    assert _overview(tmp_path) == first


def test_the_declared_list_is_a_setting_not_a_hardcoded_sweep(tmp_path: Path) -> None:
    """Scope 2 — `project_files` overrides the ecosystem default, and the default is documented."""
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    (tmp_path / "composer.json").write_text(COMPOSER, encoding="utf-8")
    only_readme = read_orientation(tmp_path, ("README.md",))
    assert only_readme.read == ("README.md",)
    assert not any(fact.kind == "test-command" for fact in only_readme.facts)
    both = read_orientation(tmp_path, None)
    assert set(both.read) == {"README.md", "composer.json"}
    assert "composer.json" in DEFAULT_PROJECT_FILES


def test_a_pointer_is_not_quoted_as_a_description(tmp_path: Path) -> None:
    """A one-line agent brief that merely imports another file answers nothing."""
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    orientation = read_orientation(tmp_path, ("CLAUDE.md",))
    assert orientation.read == ("CLAUDE.md",)
    assert not any(fact.kind == "says" for fact in orientation.facts)
    assert MIN_EXCERPT_CHARS > len("@AGENTS.md")


def test_a_citation_names_the_key_line_not_the_first_line_mentioning_it(tmp_path: Path) -> None:
    """A bare `find` cited every pyproject script to the `name = ...` line. Anchored now."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "widget"\nrequires-python = ">=3.12"\n\n'
        '[project.scripts]\nwidget = "widget.cli:main"\n',
        encoding="utf-8",
    )
    facts = {f.label: f.source for f in read_orientation(tmp_path, ("pyproject.toml",)).facts}
    assert facts["widget"] == "pyproject.toml:6", facts
    assert facts["python"] == "pyproject.toml:3", facts


def test_the_dataset_and_the_viewer_carry_the_same_orientation(tmp_path: Path) -> None:
    """R1.8 / R3.5 — one field, three readers; the version moved, so the viewer moved with it."""
    from code_atlas.onboarding.artifact import VIEWER_NAME
    from code_atlas.onboarding.dataset import DATASET_VERSION

    config = _repo(tmp_path, {"composer.json": COMPOSER, "README.md": README})
    generate_onboarding.create(config)()  # type: ignore[arg-type]
    manifest = json.loads(
        (tmp_path / OUTPUT_DIR / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert manifest["version"] == DATASET_VERSION
    kinds = {row["kind"] for row in manifest["orientation"]["facts"]}
    assert {"says", "test-command"} <= kinds
    assert manifest["orientation"]["read"] == ["composer.json", "README.md"]
    html = (tmp_path / OUTPUT_DIR / VIEWER_NAME).read_text(encoding="utf-8")
    assert 'id="startHere"' in html, "no element for the day-one line to render into"
    assert 'put("startHere",' in html, "nothing writes the day-one line into that element"


def test_the_documented_knob_table_lists_every_knob() -> None:
    """The config table in `TOOLS.md` declares itself exhaustive, and has been missed by hand.

    A hand-maintained list beside its source rots at the speed of the source (R6.7,
    `derived-not-listed-invariant`); 212's review found this same table missing a new knob, the
    fourth such miss recorded in the token ledger. Derived here so there is no fifth.
    """
    from code_atlas.config import KNOB_KEYS, env_name

    tools = Path("docs/TOOLS.md").read_text(encoding="utf-8")
    missing = [key for key in KNOB_KEYS if f"`{env_name(key)}`" not in tools]
    assert not missing, f"docs/TOOLS.md's config table does not list {missing}"
    assert len(KNOB_KEYS) > 1, "an empty knob list would pass this vacuously"
