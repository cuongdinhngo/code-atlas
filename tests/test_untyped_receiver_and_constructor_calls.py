"""Task 362 — calls the graph could not link to their method, made reachable or explained.

A variable typed in an *included* file reaches a method call only through the include graph, so a
same-named unresolved site in a file that shares an include with a file constructing the subject's
class is a proximity candidate (never ``ok``). A constructor's callers are the ``new`` sites of its
class. A ``$this->m()`` that names its method in another case stays unlinked, and the test says so.
"""

from __future__ import annotations

import shlex
import sqlite3
import subprocess

import pytest

from code_atlas.config import Config, load_config
from code_atlas.contract import CONSTRUCTOR_FLAG
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers
from code_atlas.tools.nav_result import REASON_OK, REASON_PROXIMITY_CANDIDATES
from tests.php_adapter_cli import ENTRY, PHP, needs_php

pytestmark = needs_php

FILES = {
    # Two classes declare the method, so a bare call to it cannot be linked by name alone.
    "lib/a/Editor.php": "<?php\nclass Editor { public function getStartDate() { return 1; } }\n",
    "lib/b/Planner.php": "<?php\nclass Planner { public function getStartDate() { return 2; } }\n",
    # The variable is typed in the included file and called in the includer (and vice versa).
    "views/setup.php": "<?php\n$editor = new Editor();\n",
    "reports/daily.php": "<?php\ninclude '../views/setup.php';\necho $editor->getStartDate();\n",
    "views/shell.php": "<?php\n$editor = new Editor();\ninclude 'part.php';\n",
    "views/part.php": "<?php\necho $editor->getStartDate();\n",
    # Same file, top level: already typed by the adapter before 362 (AC1).
    "views/inline.php": "<?php\n$o = new Planner();\necho $o->getStartDate();\n",
    "lib/FormBuilder.php": (
        "<?php\nclass FormBuilder {\n    public function __construct($type) {}\n}\n"
        "class Child extends FormBuilder {\n"
        "    public function __construct() { parent::__construct('child'); }\n}\n"
    ),
    "lib/Legacy.php": "<?php\nclass Legacy {\n    public function __CONSTRUCT() {}\n}\n",
    "forms/make.php": "<?php\n$f = new FormBuilder('nurse');\n$g = new FormBuilder($kind);\n",
    # One twin names its method in another case than its own call (AC3).
    "aus/Widget.php": (
        "<?php\nclass AusWidget {\n    public function validate() {}\n"
        "    public function run() { $this->validate(); }\n}\n"
    ),
    "nz/Widget.php": (
        "<?php\nclass NzWidget {\n    public function Validate() {}\n"
        "    public function run() { $this->validate(); }\n}\n"
    ),
}


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    for rel, body in FILES.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def _sources(answer: dict[str, object]) -> list[str]:
    return sorted(str(hit["qname"]) for hit in answer["results"])  # type: ignore[union-attr]


def test_a_same_file_top_level_variable_already_links(config: Config) -> None:
    """AC1 — `$o = new Planner(); $o->getStartDate();` in one view is a linked caller."""
    answer = find_callers.create(config)("\\Planner::getStartDate")
    assert answer["reason"] == REASON_OK
    assert _sources(answer) == ["views/inline.php"]


def test_a_variable_typed_in_an_included_file_reaches_its_method(config: Config) -> None:
    """Scope 1/4 — both include directions qualify the site; the other class's file does not."""
    answer = find_callers.create(config)("\\Editor::getStartDate")
    assert answer["reason"] == REASON_PROXIMITY_CANDIDATES, answer
    assert _sources(answer) == ["reports/daily.php", "views/part.php"]
    assert all(hit["candidate_of"] == "\\Editor::getStartDate" for hit in answer["results"])
    assert all(hit["confidence_tier"] == "HEURISTIC" for hit in answer["results"])


def test_a_site_whose_includes_construct_another_class_is_no_candidate(config: Config) -> None:
    """The include graph narrows: `$editor` sites are not offered as `Planner`'s callers."""
    answer = find_callers.create(config)("\\Planner::getStartDate")
    assert "reports/daily.php" not in _sources(answer)
    assert "views/part.php" not in _sources(answer)


def test_constructor_callers_are_the_new_sites_of_its_class(config: Config) -> None:
    """AC2 — every `new FormBuilder(...)` and a direct `parent::__construct`; arg_is filters."""
    tool = find_callers.create(config)
    every = tool("\\FormBuilder::__construct")
    assert every["reason"] == REASON_OK, every
    assert _sources(every) == ["\\Child::__construct", "forms/make.php"]
    literal = tool("\\FormBuilder::__construct", arg_position=1, arg_is="string")
    assert _sources(literal) == ["\\Child::__construct", "forms/make.php"]
    assert literal["total_count"] == 2
    variable = tool("\\FormBuilder::__construct", arg_position=1, arg_is="null")
    assert variable["total_count"] == 0


def test_the_adapter_marks_a_constructor_case_insensitively(config: Config) -> None:
    """The flag the core keys on comes from the language spec, `__construct` in any case."""
    conn = sqlite3.connect(config.db_path)
    rows = conn.execute(
        "SELECT qualified_name FROM nodes WHERE kind = 'Method' AND "
        "json_extract(extra, '$." + CONSTRUCTOR_FLAG + "') = 1 ORDER BY qualified_name"
    ).fetchall()
    conn.close()
    assert [row[0] for row in rows] == [
        "\\Child::__construct",
        "\\FormBuilder::__construct",
        "\\Legacy::__CONSTRUCT",
    ]


def test_a_twin_naming_its_method_in_another_case_stays_unlinked(config: Config) -> None:
    """AC3 — reproduced and documented: PHP members are case-insensitive, the resolver is not."""
    tool = find_callers.create(config)
    assert _sources(tool("\\AusWidget::validate")) == ["\\AusWidget::run"]
    assert tool("\\NzWidget::Validate")["total_count"] == 0
    conn = sqlite3.connect(config.db_path)
    unlinked = conn.execute(
        "SELECT target_raw, target_qname FROM edges WHERE source_qname = '\\NzWidget::run'"
        " AND kind = 'CALLS'"
    ).fetchall()
    conn.close()
    assert unlinked == [("\\NzWidget::validate", None)]



def test_a_truncated_constructor_page_spreads_over_every_caller(config: Config) -> None:
    """Challenger F2 — the subtree spread reads the same targets as the rows and the count."""
    answer = find_callers.create(config)("\\FormBuilder::__construct", limit=1)
    assert answer["truncated"] is True
    assert answer["total_count"] == 2
    spread = answer["result_subtrees"]
    assert sum(spread.values()) == 3  # Child's parent::__construct + the two `new` lines
    assert set(spread) == {"forms", "lib"}
