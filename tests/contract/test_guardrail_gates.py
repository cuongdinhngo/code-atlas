"""CI grep-gates as real pytest (R6.4, R6.5) — especially R2.2 where `vendor/` exists.

The `guardrails` job never runs `composer install`, so its `--exclude-dir=vendor` is vacuous there.
These assertions run in the `test` job (after Composer) and keep the shell gates as a second layer.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "code_atlas"
ADAPTERS = ROOT / "adapters"

# Verbatim with `.github/workflows/ci.yml` R1.1 / R2.2.
LANGUAGE_BRANCH = re.compile(r"if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b")
FRAMEWORK_NAME = re.compile(r"laravel|symfony|wordpress|drupal|magento", re.IGNORECASE)
EXCLUDED_DIR_NAMES = frozenset({"vendor", "node_modules"})


def authored_files(root: Path, pattern: str) -> list[Path]:
    """Walk authored source only — skip vendored trees (R6.5)."""
    found: list[Path] = []
    for path in sorted(root.rglob(pattern)):
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.is_file():
            found.append(path)
    return found


def hits_in(paths: list[Path], pattern: re.Pattern[str]) -> list[Path]:
    return [path for path in paths if pattern.search(path.read_text(encoding="utf-8"))]


def test_r22_authored_adapter_sweep_is_non_empty_under_vendor_exclusion() -> None:
    # Guards the guard: excluding vendor must not empty the authored set (R6.5).
    assert ADAPTERS.is_dir()
    assert (ADAPTERS / "php" / "vendor").is_dir(), "composer install must have populated vendor/"
    authored = authored_files(ADAPTERS, "*.php")
    assert authored, "R2.2 authored sweep is empty after vendor exclusion"
    assert all("vendor" not in path.parts for path in authored)


def test_r22_authored_adapter_source_has_no_framework_names() -> None:
    authored = authored_files(ADAPTERS, "*.php")
    assert hits_in(authored, FRAMEWORK_NAME) == []


def test_r11_core_has_no_language_branch() -> None:
    modules = authored_files(CORE, "*.py")
    assert modules
    assert hits_in(modules, LANGUAGE_BRANCH) == []


def test_r11_planted_language_branch_fails(tmp_path: Path) -> None:
    planted = tmp_path / "leak.py"
    planted.write_text('if language == "php":\n    pass\n', encoding="utf-8")
    assert hits_in([planted], LANGUAGE_BRANCH) == [planted]


def test_r22_planted_framework_name_fails(tmp_path: Path) -> None:
    planted = tmp_path / "leak.php"
    planted.write_text("<?php // laravel example\n", encoding="utf-8")
    assert hits_in([planted], FRAMEWORK_NAME) == [planted]
