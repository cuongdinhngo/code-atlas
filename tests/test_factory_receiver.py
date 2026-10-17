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
from tests.ts_adapter_cli import ENTRY as TS_ENTRY
from tests.ts_adapter_cli import NODE, needs_node

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
        "    /** @return \\App\\Pager */\n"
        "    public static function pager() { return new Pager(); }\n"
        "    /** Not @return Mailer as a tag, only prose. */\n"
        "    public static function prose() { return new Pager(); }\n"
        "}\n"
    ),
    "src/User.php": (
        "<?php\nnamespace App;\nclass User {\n"
        "    public function native() { $m = Factory::make(); $m->send(); }\n"
        "    public function documented() { $m = Factory::legacy(); $m->attach(); }\n"
        "    public function untyped($x) { $x->send(); }\n"
        "    public function qualified() { $p = Factory::pager(); $p->attach(); }\n"
        "    public function described() { $q = Factory::prose(); $q->attach(); }\n"
        "}\n"
    ),
}


def _built(root: Path, extra: dict[str, str] | None = None) -> Config:
    for rel, body in {**FILES, **(extra or {})}.items():
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
            **(
                {"CA_TYPESCRIPT_CMD": shlex.join([str(NODE), str(TS_ENTRY), "--server"])}
                if any(rel.endswith(".ts") for rel in extra or {})
                else {}
            ),
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
    assert _rows(pager) == [("\\App\\User::qualified", "HEURISTIC")]


@needs_php
def test_challenger_a_qualified_return_and_prose_name_the_right_class(tmp_path: Path) -> None:
    """`@return \\App\\Pager` resolves as written; `@return` inside prose is not a tag."""
    config = _built(tmp_path)
    mailer = _rows(find_callers.create(config)("\\App\\Mailer::attach", detail_level="minimal"))
    assert ("\\App\\User::qualified", "HEURISTIC") not in mailer
    assert ("\\App\\User::described", "HEURISTIC") not in mailer


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


@needs_php
@needs_node
def test_challenger_another_languages_same_name_call_is_not_counted(tmp_path: Path) -> None:
    config = _built(tmp_path, {"web/app.ts": "export function go(x: any) { x.send(); }\n"})
    payload = find_callers.create(config)("\\App\\Mailer::send", detail_level="minimal")
    assert payload["unresolved_receivers"] == 1, payload


# Review fixes: the factory declared in the caller's own file, and `null|X` read as `X|null`.
BUILDER = {
    "src/Builder.php": (
        "<?php\nnamespace App;\nclass Builder {\n"
        "    /** @return Mailer */\n"
        "    private function buildMailer() { return new Mailer(); }\n"
        "    /** @return null|Pager */\n"
        "    public static function maybePager() { return null; }\n"
        "    public function run() { $m = $this->buildMailer(); $m->attach(); }\n"
        "    public function stat() { $p = self::maybePager(); $p->attach(); }\n"
        "}\n"
    ),
}


@needs_php
def test_review_a_same_file_docblock_factory_types_the_local(tmp_path: Path) -> None:
    config = _built(tmp_path, BUILDER)
    mailer = _rows(find_callers.create(config)("\\App\\Mailer::attach", detail_level="minimal"))
    assert ("\\App\\Builder::run", "HEURISTIC") in mailer
    assert ("\\App\\Builder::stat", "HEURISTIC") not in mailer
    pager = _rows(find_callers.create(config)("\\App\\Pager::attach", detail_level="minimal"))
    assert ("\\App\\Builder::stat", "HEURISTIC") in pager


@needs_php
def test_review_the_count_is_unlinked_only_and_honours_exclude_tests(tmp_path: Path) -> None:
    test_file = "<?php\nclass UserTest {\n    function t($y) { $y->send(); }\n}\n"
    extra = {"tests/UserTest.php": test_file}
    config = _built(tmp_path, extra)
    tool = find_callers.create(config)
    assert tool("\\App\\Mailer::send", detail_level="minimal")["unresolved_receivers"] == 2
    payload = tool("\\App\\Mailer::send", detail_level="minimal", exclude_tests=True)
    assert payload["unresolved_receivers"] == 1, payload
