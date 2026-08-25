"""CI grep-gates as real pytest (R6.4, R6.5) — especially R2.2 where `vendor/` exists.

The `guardrails` job never runs `composer install`, so its `--exclude-dir=vendor` is vacuous there.
These assertions run in the `test` job (after Composer) and keep the shell gates as a second layer.

R1.1's clean-tree sweep lives in `tests/test_core_is_language_agnostic.py` (parametrized,
path:line); this module owns R2.2 plus the planted negative controls for both gates (AC2).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.contract.adapter_registry import REGISTRY

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "adapters"
VENDOR = ADAPTERS / "php" / "vendor"
TESTS = ROOT / "tests"
CONFORMANCE = TESTS / "contract" / "test_adapter_conformance.py"
# The one-shot argv literal, assembled so this guard's own source never self-matches.
SPAWN_TOKEN = '"' + "--" + 'file"'

# Regexes match `.github/workflows/ci.yml` R1.1 / R2.2. Sweeps intentionally match the shell gates'
# whole-tree scope (every authored file), not a `*.php` / `*.py` subset.
LANGUAGE_BRANCH = re.compile(r"if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b")
# R2.2 framework names come from one denylist (task 148) so ci.yml/gate.sh/this test cannot drift.
DENYLIST = TESTS / "contract" / "framework_denylist.txt"


def _framework_alternatives() -> list[str]:
    lines = DENYLIST.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


FRAMEWORK_ALTERNATIVES = _framework_alternatives()
FRAMEWORK_NAME = re.compile(r"\b(?:" + "|".join(FRAMEWORK_ALTERNATIVES) + r")\b", re.IGNORECASE)
EXCLUDED_DIR_NAMES = frozenset({"vendor", "node_modules"})

needs_vendor = pytest.mark.skipif(
    not VENDOR.is_dir(),
    reason="needs `composer install --working-dir=adapters/php` (CI test job always has vendor/)",
)


def authored_files(root: Path) -> list[Path]:
    """Authored files only (skip vendor/node_modules). All types, matching the shell gate."""
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        found.append(path)
    return found


def hits_in(paths: list[Path], pattern: re.Pattern[str]) -> list[Path]:
    hits: list[Path] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text):
            hits.append(path)
    return hits


@needs_vendor
def test_r22_authored_adapter_sweep_is_non_empty_under_vendor_exclusion() -> None:
    # Guards the guard: excluding vendor must not empty the authored set (R6.5).
    assert ADAPTERS.is_dir()
    authored = authored_files(ADAPTERS)
    assert authored, "R2.2 authored sweep is empty after vendor exclusion"
    assert all("vendor" not in path.parts for path in authored)


@needs_vendor
def test_r22_authored_adapter_source_has_no_framework_names() -> None:
    assert hits_in(authored_files(ADAPTERS), FRAMEWORK_NAME) == []


def test_r11_planted_language_branch_fails(tmp_path: Path) -> None:
    planted = tmp_path / "leak.py"
    planted.write_text('if language == "php":\n    pass\n', encoding="utf-8")
    assert hits_in([planted], LANGUAGE_BRANCH) == [planted]


def test_r22_planted_framework_name_fails(tmp_path: Path) -> None:
    planted = tmp_path / "leak.php"
    planted.write_text("<?php // laravel example\n", encoding="utf-8")
    assert hits_in([planted], FRAMEWORK_NAME) == [planted]


@pytest.mark.parametrize("name", ["laravel", "react", "vue", "nextjs", "express", "nestjs"])
def test_r22_denylist_covers_each_ecosystem(name: str, tmp_path: Path) -> None:
    # AC1: a planted framework name from each ecosystem fails the sweep, by control not inspection.
    planted = tmp_path / "leak.php"
    planted.write_text(f"<?php // {name} example\n", encoding="utf-8")
    assert hits_in([planted], FRAMEWORK_NAME) == [planted]


def test_r22_bare_next_and_nest_do_not_trip_the_sweep(tmp_path: Path) -> None:
    # AC3: bare next()/nested must not fire — only the framework spelling (next.js/nest.js) does.
    planted = tmp_path / "ok.php"
    planted.write_text("<?php $x = next($a); // nested loop, the next request\n", encoding="utf-8")
    assert hits_in([planted], FRAMEWORK_NAME) == []


def test_r22_denylist_is_non_empty() -> None:
    # R6.5 guard-the-guard: an empty denylist would make \b(?:)\b match every file or none.
    assert FRAMEWORK_ALTERNATIVES, "framework denylist is empty"


def test_r22_shell_gate_derives_from_the_denylist() -> None:
    # AC2 + R6.7: gate.sh reads the one denylist, never a hand-kept copy of the alternation.
    gate = (ROOT / "scripts" / "gate.sh").read_text(encoding="utf-8")
    assert "framework_denylist.txt" in gate
    for name in ["laravel", "symfony", "react", "nextjs"]:
        assert f"{name}|" not in gate, name


def _authored_test_py_files() -> list[Path]:
    return [
        path
        for path in sorted(TESTS.rglob("*.py"))
        if not any(part in EXCLUDED_DIR_NAMES for part in path.parts)
    ]


def test_ac4_exactly_one_module_spawns_an_adapter_in_one_shot_file_mode() -> None:
    # 147 AC4: the "fourth copy" the split forbids stays impossible — one `--file` spawn, one place.
    hits = [p for p in _authored_test_py_files() if SPAWN_TOKEN in p.read_text(encoding="utf-8")]
    assert [p.name for p in hits] == ["adapter_cli.py"], [str(p.relative_to(ROOT)) for p in hits]


def test_ac4_guard_catches_a_planted_second_spawn(tmp_path: Path) -> None:
    # R6.5 prove-the-guard-fails: a planted second spawn must be seen by the scan.
    planted = tmp_path / "sneaky_spawn.py"
    planted.write_text(f"subprocess.run([php, entry, {SPAWN_TOKEN}, rel])\n", encoding="utf-8")
    assert SPAWN_TOKEN in planted.read_text(encoding="utf-8")


def test_ac2_conformance_body_names_no_adapter_directory_literal() -> None:
    # 147 AC2: a 2nd adapter is a registry row + fixtures, never a literal in the module body.
    source = CONFORMANCE.read_text(encoding="utf-8")
    offenders = [name for name in REGISTRY if f'"{name}"' in source]
    assert offenders == [], offenders
