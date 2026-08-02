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

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = ROOT / "adapters"
VENDOR = ADAPTERS / "php" / "vendor"

# Regexes match `.github/workflows/ci.yml` R1.1 / R2.2. Sweeps intentionally match the shell gates'
# whole-tree scope (every authored file), not a `*.php` / `*.py` subset.
LANGUAGE_BRANCH = re.compile(r"if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b")
FRAMEWORK_NAME = re.compile(r"laravel|symfony|wordpress|drupal|magento", re.IGNORECASE)
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
