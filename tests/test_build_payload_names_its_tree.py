"""Task 079: every ``build_or_update_index`` outcome names the tree it wrote (``index_root``).

071 put ``index_root`` on every nav payload so an answer names its tree; the build tool — the one
payload where the tree matters most, because a build is a *write* — was the only one without it,
carrying ``db_path`` instead. Round 4 verified the field on 8 of 8 nav payloads and found it absent
on all 4 build payloads. This suite **enumerates** the build outcomes (success full/minimal,
incremental, busy, schema-refused, no-adapter, empty-suffix) rather than sampling one, so the field
is a reliable process fingerprint, not a per-branch accident. It also pins the ``db_path`` verdict
(KEEP — a write names its target) and the 077 fold-in (``last_ref`` beside ``last_commit``).
"""

from __future__ import annotations

import shlex
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.tools.build_or_update_index import NO_USABLE_ADAPTER, REFUSED, create
from tests.test_busy_build_staleness import busy_while_locked
from tests.test_incremental import committed, fake_env
from tests.test_schema_version_recovery import NEWER, indexed
from tests.test_staleness_scope import SOURCE, build_index

FAKE = Path(__file__).resolve().parent / "fixtures" / "adapter" / "fake_adapter.py"


def _working_config(root: Path) -> Config:
    committed(root, {SOURCE: "<?php class A {}\n", "README.md": "docs\n"})
    db = root / ".code-atlas" / "graph.db"
    return load_config(root, {**fake_env(workers=1), "CA_DB_PATH": str(db)})


# --- one producer per outcome; each returns the payload for that build outcome --------------------


def _full_standard(root: Path) -> dict[str, object]:
    return create(_working_config(root))(full=True, detail_level="standard")


def _full_minimal(root: Path) -> dict[str, object]:
    return create(_working_config(root))(full=True, detail_level="minimal")


def _incremental(root: Path) -> dict[str, object]:
    config = _working_config(root)
    create(config)(full=True)  # first build stamps last_commit so the next runs incremental
    return create(config)(full=False)


def _busy(root: Path) -> dict[str, object]:
    committed(root, {SOURCE: "<?php class A {}\n", "README.md": "docs\n"})
    db_path = build_index(root)
    return busy_while_locked(load_config(root, {**fake_env(workers=1), "CA_DB_PATH": str(db_path)}))


def _schema_refused(root: Path) -> dict[str, object]:
    return create(indexed(root, NEWER))(detail_level="standard")


def _no_adapter(root: Path) -> dict[str, object]:
    committed(root, {SOURCE: "<?php class A {}\n"})
    db = root / ".code-atlas" / "graph.db"
    return create(load_config(root, {"CA_WORKERS": "1", "CA_DB_PATH": str(db)}))(full=True)


def _empty_suffix(root: Path) -> dict[str, object]:
    committed(root, {SOURCE: "<?php class A {}\n"})
    db = root / ".code-atlas" / "graph.db"
    env = {
        "CA_WORKERS": "1",
        "CA_DB_PATH": str(db),
        "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "empty-extensions"]),
    }
    return create(load_config(root, env))(full=True)


OUTCOMES: dict[str, Callable[[Path], dict[str, object]]] = {
    "full_standard": _full_standard,
    "full_minimal": _full_minimal,
    "incremental": _incremental,
    "busy": _busy,
    "schema_refused": _schema_refused,
    "no_adapter": _no_adapter,
    "empty_suffix": _empty_suffix,
}


@pytest.mark.parametrize("name", list(OUTCOMES), ids=list(OUTCOMES))
def test_every_build_outcome_names_its_tree(tmp_path: Path, name: str) -> None:
    """Proving test (AC1): every enumerated build outcome carries ``index_root`` == the source root.

    Fails pre-079: the field is absent on success/busy/refused and the no-adapter/empty-suffix paths
    raise instead of returning a payload. Passes post-079 on all seven.
    """
    root = tmp_path / name
    root.mkdir()

    payload = OUTCOMES[name](root)

    assert "index_root" in payload, f"{name} has no index_root"
    assert payload["index_root"] == str(root.resolve()), name


def test_the_enumeration_covers_every_shape_not_a_sample() -> None:
    """AC1 guard: the outcome set is the full matrix — success, busy, and every refusal path."""
    assert set(OUTCOMES) == {
        "full_standard",
        "full_minimal",
        "incremental",
        "busy",
        "schema_refused",
        "no_adapter",
        "empty_suffix",
    }


def test_the_two_adapter_refusals_are_payloads_naming_the_tree(tmp_path: Path) -> None:
    """079/Q1: no-adapter and empty-suffix refuse as a fingerprinted payload, not a raise."""
    for name in ("no_adapter", "empty_suffix"):
        root = tmp_path / name
        root.mkdir()
        payload = OUTCOMES[name](root)
        assert payload["mode"] == REFUSED, name
        assert payload["reason"] == NO_USABLE_ADAPTER, name
        assert payload["performed"] is False, name
        assert payload["detail"], name  # the specifics live here, not in the reason (061)


# --- db_path verdict (AC2): KEEP — a build is a write, and db_path names its target ---------------


def test_db_path_is_kept_on_the_write_payloads(tmp_path: Path) -> None:
    """AC2: the recorded verdict is KEEP; db_path rides beside index_root on the write payloads.

    index_root (source tree) and db_path (write target) are different facts. 061 stripped db_path
    from *nav* answers as dead weight; on a build it is the one place it earns its bytes.
    """
    std = _full_standard(tmp_path / "std")
    assert "db_path" in std and "index_root" in std

    busy = _busy(tmp_path / "busy")
    assert "db_path" in busy and "index_root" in busy

    refused = _schema_refused(tmp_path / "schema")
    assert "db_path" in refused and "index_root" in refused

    no_adapter = _no_adapter(tmp_path / "noadapter")
    assert "db_path" in no_adapter and "index_root" in no_adapter


def test_standard_success_names_the_revision_too(tmp_path: Path) -> None:
    """077 fold-in: a build that names the directory also names the revision (last_ref)."""
    std = _full_standard(tmp_path / "rev")
    assert "last_commit" in std
    assert "last_ref" in std  # the revision half — omitted, never null, only for a pre-077 index


def test_minimal_success_stays_cheap_but_still_fingerprinted(tmp_path: Path) -> None:
    """index_root is the fingerprint on both levels; the revision detail rides with the commit."""
    minimal = _full_minimal(tmp_path / "min")
    assert "index_root" in minimal
    assert "last_commit" not in minimal  # cheap path unchanged (061)
    assert "last_ref" not in minimal
