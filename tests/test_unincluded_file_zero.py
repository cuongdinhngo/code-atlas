"""Task 363 — a file nothing includes is a confident zero when no unlinked include could name it.

``relationship_not_modelled`` fired whenever any unlinked include *contained* the basename, so
`old_screen.php` or `../other/screen.php` kept a copy nobody includes from reading as unused. An
unlinked include now blocks the zero only when its path tail could be this file's.
"""

from __future__ import annotations

import dataclasses
import shlex
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tools import include_graph
from code_atlas.tools.nav_result import REASON_NO_MATCHES, REASON_RELATIONSHIP_NOT_MODELLED
from tests.php_adapter_cli import ENTRY, PHP, needs_php

pytestmark = needs_php

USED = "app/views/screen.php"
UNUSED = "app/legacy/screen.php"
BASE = {
    USED: "<?php\necho 'used';\n",
    UNUSED: "<?php\necho 'unused';\n",
    "app/views/old_screen.php": "<?php\necho 'old';\n",
    # Resolves to USED. The other two mention the basename but cannot be UNUSED.
    "app/views/tabs.php": "<?php\ninclude 'screen.php';\ninclude 'old_screen.php';\n",
    "app/reports/run.php": "<?php\ninclude '../missing/screen.php';\n",
}


def _build(root: Path, files: dict[str, str]) -> Config:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    config = load_config(
        root, {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(ENTRY), "--server"])}
    )
    with GraphStore(config.db_path) as store:
        assert full_build(config, store).failed == 0
    return config


def test_a_copy_nothing_can_include_is_a_confident_zero(tmp_path: Path) -> None:
    """AC1 — the unused copy answers no_matches, authoritative, and names the included copy."""
    config = _build(tmp_path, BASE)
    answer = include_graph.create(config)(UNUSED, direction="imported_by")
    assert answer["reason"] == REASON_NO_MATCHES, answer
    assert answer["authoritative"] is True
    assert answer["same_basename_included"] == [USED]
    assert "unlinked_includes" not in answer


def test_a_dynamic_include_of_the_basename_reverts_the_zero(tmp_path: Path) -> None:
    """AC2 — `include $dir . '/screen.php'` could be this file: not ok, and the site is listed."""
    files = dict(BASE)
    files["app/cron/job.php"] = "<?php\ninclude $dir . '/screen.php';\n"
    config = _build(tmp_path, files)
    answer = include_graph.create(config)(UNUSED, direction="imported_by")
    assert answer["reason"] == REASON_RELATIONSHIP_NOT_MODELLED
    assert answer["unlinked_includes"] == [
        {"file": "app/cron/job.php", "line": 2, "target_raw": "/screen.php"}
    ]


def test_a_relative_tail_that_fits_this_file_still_blocks_the_zero(tmp_path: Path) -> None:
    """An unlinked `../legacy/screen.php` whose tail fits this copy blocks the zero."""
    files = dict(BASE)
    files["tools/fix.php"] = "<?php\ninclude '../legacy/screen.php';\n"
    config = _build(tmp_path, files)
    answer = include_graph.create(config)(UNUSED, direction="imported_by")
    assert answer["reason"] == REASON_RELATIONSHIP_NOT_MODELLED


def test_a_file_with_an_includer_answers_as_before(tmp_path: Path) -> None:
    """AC3 — the included copy lists its includer, unchanged."""
    config = _build(tmp_path, BASE)
    answer = include_graph.create(config)(USED, direction="imported_by")
    assert [hit["path"] for hit in answer["results"]] == ["app/views/tabs.php"]
    assert "same_basename_included" not in answer


@pytest.mark.parametrize(
    ("target_raw", "fits"),
    [
        ("screen.php", True),
        ("'../legacy/screen.php'", True),
        ("dirname(__DIR__) . '/legacy/screen.php'", True),
        ("/screen.php", True),
        ("../views/screen.php", False),
        ("old_screen.php", False),
        ("'screen.php.bak'", False),
        ("(dynamic)", False),
    ],
)
def test_only_a_tail_that_could_be_this_path_fits(target_raw: str, fits: bool) -> None:
    """The include-text test the zero turns on — literal as written, quotes and heads included."""
    from code_atlas.tools.include_graph import _tail_fits

    assert _tail_fits(target_raw, UNUSED) is fits


def test_a_cut_listing_or_an_unindexed_subject_is_never_a_positive_zero(tmp_path: Path) -> None:
    """R5.6 — a zero is attested only for an indexed file over a listing that was read whole."""
    files = dict(BASE)
    files["app/a.php"] = "<?php\ninclude '../nowhere/screen.php';\n"
    files["app/b.php"] = "<?php\ninclude '../elsewhere/screen.php';\n"
    config = _build(tmp_path, files)
    narrow = dataclasses.replace(config, page_limit=1)
    answer = include_graph.create(narrow)(UNUSED, direction="imported_by")
    assert "authoritative" not in answer
    ghost = include_graph.create(config)("app/ghost/screen.php", direction="imported_by")
    assert "authoritative" not in ghost
