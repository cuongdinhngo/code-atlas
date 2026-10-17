"""Task 394 — a read names where the real code lives: overrides, aliases, test copies."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import read_symbol, search_symbol

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

FILES = {
    "src/Base.php": "<?php\nnamespace App;\nclass Base { public function render() {} }\n",
    "src/A.php": "<?php\nnamespace App;\nclass A extends Base { public function render() { } }\n",
    "src/B.php": "<?php\nnamespace App;\nclass B extends Base { public function render() { } }\n",
    "src/Plain.php": "<?php\nnamespace App;\nclass Plain { public function run() { return 3; } }\n",
    "src/Form.php": "<?php\nclass Form { public function show() { return 1; } }\n",
    "tests/StubForm.php": "<?php\nclass StubForm { public function show() {} }\n",
    "tests/bootstrap.php": "<?php\nclass_alias('StubForm', 'Form');\nfunction helper() {}\n",
    "src/helpers.php": "<?php\nfunction helper() { return 1; }\n",
}
POINTER_KEYS = ("implemented_by", "aliases", "ambiguity")


def _built(root: Path) -> Config:
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
    config = load_config(
        root, {"CA_WORKERS": "2", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])}
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


@needs_php
def test_ac1_an_empty_base_method_names_both_overrides(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = read_symbol.create(config)("\\App\\Base::render")
    assert [row["qname"] for row in payload["implemented_by"]] == [
        "\\App\\A::render",
        "\\App\\B::render",
    ]
    assert {row["file"] for row in payload["implemented_by"]} == {"src/A.php", "src/B.php"}


@needs_php
def test_ac2_an_aliased_class_names_its_test_bootstrap_stub(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = read_symbol.create(config)("\\Form")
    assert payload["aliases"] == [
        {
            "qname": "\\StubForm",
            "relation": "alias_of",
            "file": "tests/bootstrap.php",
            "line": 2,
            "test_double": True,
        }
    ]
    stub = read_symbol.create(config)("\\StubForm")
    assert [(a["qname"], a["relation"]) for a in stub["aliases"]] == [("\\Form", "aliased_as")]
    found = search_symbol.create(config)(query="StubForm")
    row = next(r for r in found["results"] if r["qname"] == "\\StubForm")
    assert row["aliases"][0]["qname"] == "\\Form"


@needs_php
def test_scope3_test_copies_answer_the_production_definition(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = read_symbol.create(config)("\\helper")
    assert payload["reason"] == "ok", payload
    assert payload["file"] == "src/helpers.php"
    assert payload["ambiguity"] == "test_copies"
    found = search_symbol.create(config)(query="helper")
    files = [r["file"] for r in found["results"] if r["qname"] == "\\helper"]
    assert files == ["src/helpers.php", "tests/bootstrap.php"]
    assert found["ambiguity"] == "test_copies"


@needs_php
def test_ac3_a_symbol_with_no_override_alias_or_copy_is_unchanged(tmp_path: Path) -> None:
    config = _built(tmp_path)
    for payload in (
        read_symbol.create(config)("\\App\\Plain::run"),
        read_symbol.create(config)("\\App\\A::render"),
        search_symbol.create(config)(query="Plain"),
    ):
        assert not set(POINTER_KEYS) & set(payload), payload
        assert all(not set(POINTER_KEYS) & set(row) for row in payload.get("results", []))


@needs_php
def test_a_method_with_a_body_carries_no_implemented_by(tmp_path: Path) -> None:
    """Scope 1 is empty or abstract bodies: a base method that does work names no overrides."""
    config = _built(tmp_path)
    (tmp_path / "src" / "Base.php").write_text(
        "<?php\nnamespace App;\nclass Base { public function render() { return helper(); } }\n",
        encoding="utf-8",
    )
    payload = read_symbol.create(config)("\\App\\Base::render")
    assert "implemented_by" not in payload, payload
