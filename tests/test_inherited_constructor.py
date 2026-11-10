"""Task 450 — `Child::__construct` reads its inherited constructor, and `new Child` calls it."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers, read_symbol

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
pytestmark = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

FILES = {
    "src/Base.php": (
        "<?php\nnamespace App;\nclass Base {\n"
        "    public function __construct($x) { $this->x = $x; }\n}\n"
    ),
    "src/Child.php": "<?php\nnamespace App;\nclass Child extends Base {}\n",
    "src/Grand.php": "<?php\nnamespace App;\nclass Grand extends Child {}\n",
    "src/Own.php": (
        "<?php\nnamespace App;\nclass Own extends Base {\n"
        "    public function __construct() { parent::__construct(1); }\n}\n"
    ),
    "src/Gone.php": "<?php\nnamespace App;\nclass Gone extends \\Vendor\\Missing {}\n",
    "src/Use.php": (
        "<?php\nnamespace App;\nclass Make {\n"
        "    public function base() { return new Base(1); }\n"
        "    public function child() { return new Child(2); }\n"
        "    public function grand() { return new Grand(3); }\n"
        "    public function own() { return new Own(); }\n}\n"
    ),
}


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    for rel, body in FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def test_ac1_read_symbol_answers_the_inherited_constructor(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Child::__construct")
    assert payload["reason"] == "ok"
    assert payload["qname"] == "\\App\\Base::__construct"
    assert payload["inherited_from"] == "\\App\\Base"
    assert payload["asked"] == "\\App\\Child::__construct"
    assert "$this->x = $x" in str(payload["source"])


def test_ac1_a_grandchild_reaches_the_nearest_constructor(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Grand::__construct", detail_level="minimal")
    assert payload["inherited_from"] == "\\App\\Base"


def test_ac1_find_callers_lists_the_subclass_new_sites(config: Config) -> None:
    payload = find_callers.create(config)("\\App\\Base::__construct", detail_level="minimal")
    rows = {str(row["qname"]): row for row in payload["results"]}
    assert "via_subclass" not in rows["\\App\\Make::base"]
    assert rows["\\App\\Make::child"]["via_subclass"] == "\\App\\Child"
    assert rows["\\App\\Make::grand"]["via_subclass"] == "\\App\\Grand"
    assert rows["\\App\\Make::child"]["confidence_tier"] == "RESOLVED"
    assert "\\App\\Make::own" not in rows


def test_ac2_a_class_with_its_own_constructor_is_unchanged(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Own::__construct")
    assert payload["qname"] == "\\App\\Own::__construct"
    assert "inherited_from" not in payload
    callers = find_callers.create(config)("\\App\\Own::__construct", detail_level="minimal")
    assert [str(row["qname"]) for row in callers["results"]] == ["\\App\\Make::own"]


def test_scope3_an_unlinked_ancestor_is_never_a_confident_absence(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Gone::__construct")
    assert payload["reason"] == "no_such_symbol"
    assert payload["ancestry_unresolved"] == ["\\Vendor\\Missing"]


def test_a_member_that_is_not_the_constructor_is_not_inherited_here(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Child::other")
    assert payload["reason"] == "no_such_symbol"
    assert "inherited_from" not in payload and "ancestry_unresolved" not in payload


# Challenger F1: a used trait's constructor is the class's own, so it beats the parent's.
TRAITS = {
    **FILES,
    "src/T.php": "<?php\nnamespace App;\ntrait T {\n    public function __construct() {}\n}\n",
    "src/U.php": "<?php\nnamespace App;\ntrait U {\n    public function __construct() {}\n}\n",
    "src/X.php": "<?php\nnamespace App;\nclass X extends Base {\n    use T;\n}\n",
    "src/Y.php": "<?php\nnamespace App;\nclass Y extends Base {\n    use T, U;\n}\n",
    "src/MakeX.php": (
        "<?php\nnamespace App;\nclass MakeX {\n"
        "    public function x() { return new X(); }\n}\n"
    ),
}


def test_challenger_a_used_traits_constructor_wins_over_the_parents(tmp_path: Path) -> None:
    for rel, body in TRAITS.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(body, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
    built = load_config(
        tmp_path,
        {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    tool = read_symbol.create(built)
    assert tool("\\App\\X::__construct")["inherited_from"] == "\\App\\T"
    # Two traits that both supply one: no single answer, and no guess at the parent's.
    assert "inherited_from" not in tool("\\App\\Y::__construct")
    base = find_callers.create(built)("\\App\\Base::__construct", detail_level="minimal")
    assert "\\App\\MakeX::x" not in {str(row["qname"]) for row in base["results"]}
    trait = find_callers.create(built)("\\App\\T::__construct", detail_level="minimal")
    rows = {str(row["qname"]): row for row in trait["results"]}
    assert rows["\\App\\MakeX::x"]["via_subclass"] == "\\App\\X"
