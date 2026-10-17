"""Task 393 — a call on what a factory returned links, and untyped receivers are counted."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import find_callers

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)

# Two classes declare `send` and `attach`, so no bare-name fallback can stand in for the type.
FILES = {
    "src/Mailer.php": (
        "<?php\nnamespace App;\nclass Mailer {\n"
        "    public function send() {}\n    public function attach() {}\n}\n"
    ),
    "src/Pager.php": (
        "<?php\nnamespace App;\nclass Pager {\n"
        "    public function send() {}\n    public function attach() {}\n}\n"
    ),
    "src/Factory.php": (
        "<?php\nnamespace App;\nclass Factory {\n"
        "    public static function make(): Mailer { return new Mailer(); }\n"
        "    /** @return Mailer */\n"
        "    public static function legacy() { return new Mailer(); }\n"
        "}\n"
    ),
    "src/User.php": (
        "<?php\nnamespace App;\nclass User {\n"
        "    public function native() { $m = Factory::make(); $m->send(); }\n"
        "    public function documented() { $m = Factory::legacy(); $m->attach(); }\n"
        "    public function untyped($x) { $x->send(); }\n"
        "}\n"
    ),
}


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
        root,
        {
            "CA_WORKERS": "2",
            "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"]),
        },
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def _rows(payload: dict[str, object]) -> list[tuple[str, str]]:
    rows = payload["results"]
    assert isinstance(rows, list)
    return [(str(row["qname"]), str(row["confidence_tier"])) for row in rows]


@needs_php
def test_ac1_a_native_return_type_types_the_local(tmp_path: Path) -> None:
    """The native type was linked before 393 and stays RESOLVED (AC3: no tier moves)."""
    payload = find_callers.create(_built(tmp_path))("\\App\\Mailer::send", detail_level="minimal")
    assert ("\\App\\User::native", "RESOLVED") in _rows(payload)


@needs_php
def test_ac2_a_return_docblock_types_the_local_at_heuristic(tmp_path: Path) -> None:
    config = _built(tmp_path)
    payload = find_callers.create(config)("\\App\\Mailer::attach", detail_level="minimal")
    assert _rows(payload) == [("\\App\\User::documented", "HEURISTIC")]
    pager = find_callers.create(config)("\\App\\Pager::attach", detail_level="minimal")
    assert _rows(pager) == []


@needs_php
def test_scope3_untyped_receivers_are_counted(tmp_path: Path) -> None:
    """`$x->send()` names no class: whichever `send` it links to by name, the answer says so."""
    config = _built(tmp_path)
    for subject in ("\\App\\Pager::send", "\\App\\Mailer::send"):
        payload = find_callers.create(config)(subject, detail_level="minimal")
        assert payload["unresolved_receivers"] == 1, payload


@needs_php
def test_ac3_a_subject_with_no_such_site_carries_no_count(tmp_path: Path) -> None:
    payload = find_callers.create(_built(tmp_path))("\\App\\Factory::make", detail_level="minimal")
    assert "unresolved_receivers" not in payload
