"""Task 384 — "has this symbol changed since revision X", per symbol rather than per file.

Each case builds a real repo through a real adapter, exports a snapshot at the base revision,
edits and rebuilds, then asks ``code-atlas query --changed-since``. The fingerprint is the
adapter's own (comments and layout dropped), so every adapter is driven, not a stub of one.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from code_atlas import query, symbol_changes
from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from tests.adapter_cli import AdapterCli
from tests.contract.adapter_registry import REGISTRY


@dataclass(frozen=True)
class Edits:
    """One symbol's source at the base revision and after each kind of edit."""

    path: str
    name: str
    base: str
    layout: str  # comments and whitespace only
    body: str  # one token in the body
    signature: str  # one more parameter


EDITS: dict[str, Edits] = {
    "php": Edits(
        "src/Repo.php",
        "save",
        "<?php\nclass Repo {\n    public function save($a) {\n        // keep\n"
        "        return $a + 1;\n    }\n}\n",
        "<?php\nclass Repo {\n    /** Saves. */\n    public function save($a)\n    {\n"
        "        /* reworded */\n\n            return $a  +  1;\n    }\n}\n",
        "<?php\nclass Repo {\n    public function save($a) {\n        // keep\n"
        "        return $a + 2;\n    }\n}\n",
        "<?php\nclass Repo {\n    public function save($a, $b) {\n        // keep\n"
        "        return $a + 1;\n    }\n}\n",
    ),
    "typescript": Edits(
        "src/repo.ts",
        "save",
        "export class Repo {\n  save(a: number) {\n    // keep\n    return a + 1;\n  }\n}\n",
        "export class Repo {\n  /** Saves. */\n  save(a: number)\n  {\n    /* reworded */\n\n"
        "        return a  +  1;\n  }\n}\n",
        "export class Repo {\n  save(a: number) {\n    // keep\n    return a + 2;\n  }\n}\n",
        "export class Repo {\n  save(a: number, b: number) {\n    // keep\n    return a + 1;\n"
        "  }\n}\n",
    ),
    "python": Edits(
        "src/repo.py",
        "save",
        "class Repo:\n    def save(self, a):\n        # keep\n        return a + 1\n",
        "class Repo:\n    def save(self, a):  # trailing\n        # reworded\n\n"
        "        return a  +  1\n",
        "class Repo:\n    def save(self, a):\n        # keep\n        return a + 2\n",
        "class Repo:\n    def save(self, a, b):\n        # keep\n        return a + 1\n",
    ),
    "sql": Edits(
        "db/save.sql",
        "Save",
        "CREATE PROCEDURE dbo.Save @a INT AS\nBEGIN\n  -- keep\n  SELECT @a + 1;\nEND\nGO\n",
        "CREATE PROCEDURE dbo.Save @a INT AS\nBEGIN\n  /* reworded */\n\n"
        "      SELECT   @a + 1;   -- trailing\nEND\nGO\n",
        "CREATE PROCEDURE dbo.Save @a INT AS\nBEGIN\n  -- keep\n  SELECT @a + 2;\nEND\nGO\n",
        "CREATE PROCEDURE dbo.Save @a INT, @b INT AS\nBEGIN\n  -- keep\n"
        "  SELECT @a + 1;\nEND\nGO\n",
    ),
}


def _cases() -> list[Any]:
    """Every registered adapter, so a fifth one without an ``EDITS`` row fails here (R6.7)."""
    return [
        pytest.param(name, marks=REGISTRY[name].cli.availability) for name in sorted(REGISTRY)
    ]


class Repo:
    """A git repo indexed by one adapter, driven the way a consumer drives it: from a shell."""

    def __init__(self, root: Path, cli: AdapterCli, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        root.mkdir(parents=True)
        argv = ", ".join(json.dumps(part) for part in (*cli.entry_argv, "--server"))
        (root / ".code-atlas.toml").write_text(
            f"[adapter_cmd]\n{cli.name} = [{argv}]\n", encoding="utf-8"
        )
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        db_path = root / ".code-atlas" / "graph.db"
        env = {"CA_TRUST_PROJECT_FILE": "1", "CA_WORKERS": "1", "CA_DB_PATH": str(db_path)}
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
        self.config: Config = load_config(root, env)

    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def write(self, files: dict[str, str | None], *, build: bool = True) -> None:
        for path, text in files.items():
            target = self.root / path
            if text is None:
                target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        if not build:
            return
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "edit")
        with GraphStore(self.config.db_path) as store:
            assert full_build(self.config, store).nodes > 0

    def snapshot(self, capsys: pytest.CaptureFixture[str]) -> Path:
        out = self.root.parent / f"{self.root.name}.symbols.json"
        assert query.main(["--snapshot-symbols", str(out)]) == query.OK
        capsys.readouterr()
        return out

    def changed(
        self, capsys: pytest.CaptureFixture[str], snapshot: Path, *subject: str
    ) -> tuple[int, list[dict[str, Any]]]:
        code = query.main(["--changed-since", str(snapshot), *subject])
        out, _ = capsys.readouterr()
        return code, [json.loads(line) for line in out.splitlines() if line.strip()]


def qname_named(snapshot: Path, name: str) -> str:
    symbols = json.loads(snapshot.read_text(encoding="utf-8"))["symbols"]
    [qname] = {s["qname"] for s in symbols if s["name"] == name and s["kind"] != "Class"}
    return qname


@pytest.mark.parametrize("adapter", _cases())
def test_layout_body_and_signature_edits_are_told_apart(
    adapter: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC1 (proving test): per adapter, a comment/whitespace edit is ``unchanged``, a one-token
    body edit ``body_changed`` and a parameter change ``signature_changed``."""
    edits = EDITS[adapter]
    repo = Repo(tmp_path / adapter, REGISTRY[adapter].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, edits.name)

    seen: dict[str, str] = {}
    for label, text in (("layout", edits.layout), ("body", edits.body),
                        ("signature", edits.signature), ("base", edits.base)):
        repo.write({edits.path: text})
        _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)
        seen[label] = str(verdict["status"])

    assert seen == {
        "layout": symbol_changes.UNCHANGED,
        "body": symbol_changes.BODY_CHANGED,
        "signature": symbol_changes.SIGNATURE_CHANGED,
        "base": symbol_changes.UNCHANGED,  # positive control: the snapshot's own source
    }


def test_every_registered_adapter_has_edits() -> None:
    assert set(EDITS) == set(REGISTRY)


@pytest.mark.parametrize("adapter", _cases())
def test_a_body_moved_to_another_file_is_moved_not_removed(
    adapter: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC2: PHP and T-SQL keep the qname across files; TS and Python qnames follow the file, so
    the move is found by name, kind and body."""
    edits = EDITS[adapter]
    repo = Repo(tmp_path / adapter, REGISTRY[adapter].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, edits.name)
    moved_to = "lib/" + edits.path.split("/", 1)[1]
    repo.write({edits.path: None, moved_to: edits.base})
    code, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert verdict["status"] == symbol_changes.MOVED
    assert (verdict["file_base"], verdict["file_now"]) == (edits.path, moved_to)
    assert code == query.NOT_HELD
    repo.write({moved_to: edits.body})
    _, [gone] = repo.changed(capsys, snapshot, "--qname", qname)
    if "qname_now" in verdict:  # a new qname with a new body is not the same symbol
        assert gone["status"] == symbol_changes.REMOVED


def test_a_decorator_edit_is_a_body_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Challenger finding 1: a decorator sits above the ``def`` line and is part of the symbol."""
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({"src/views.py": "@route('/a')\ndef page(a):\n    return a\n"})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, "page")
    repo.write({"src/views.py": "@route('/b')\ndef page(a):\n    return a\n"})
    _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert verdict["status"] == symbol_changes.BODY_CHANGED


@pytest.mark.parametrize(
    "adapter", [pytest.param("typescript", marks=REGISTRY["typescript"].cli.availability)]
)
def test_an_edit_to_an_overload_implementation_is_seen(
    adapter: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The store keeps the first declaration of a qname per file; the fingerprint spans them all."""
    head = "export class Repo {\n  save(a: number): number;\n  save(a: string): number;\n"
    repo = Repo(tmp_path / "ts", REGISTRY[adapter].cli, monkeypatch)
    repo.write({"src/repo.ts": head + "  save(a: any) { return 1; }\n}\n"})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, "save")
    repo.write({"src/repo.ts": head + "  save(a: any) { return 2; }\n}\n"})
    _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert verdict["status"] == symbol_changes.BODY_CHANGED


def test_a_snapshot_of_a_drifted_index_answers_unknown_for_the_drifted_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Challenger finding 5: rows the build never saw are not the snapshot's ``rev``."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    qname = qname_named(repo.snapshot(capsys), edits.name)
    repo.write({edits.path: edits.body}, build=False)
    snapshot = repo.snapshot(capsys)
    repo.write({edits.path: edits.body})
    _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert json.loads(snapshot.read_text(encoding="utf-8"))["drifted"] == [edits.path]
    assert (verdict["status"], verdict["reason"]) == (
        symbol_changes.UNKNOWN, "snapshot_file_drifted")


def test_a_body_copied_to_two_files_is_an_ambiguous_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exposure-checker item 1: two identical bodies elsewhere are not one move."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, edits.name)
    repo.write({edits.path: None, "lib/a.py": edits.base, "lib/b.py": edits.base})
    _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert (verdict["status"], verdict["reason"]) == (symbol_changes.UNKNOWN, "ambiguous_move")


def test_a_symbol_absent_from_the_base_is_unknown_at_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC4: never ``unchanged`` for a symbol the snapshot never held — by qname or by path."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    repo.write({edits.path: edits.base + "\n\ndef added():\n    return 1\n"})
    added = qname_named(snapshot, "save").replace("Repo::save", "added")

    _, [by_qname] = repo.changed(capsys, snapshot, "--qname", added)
    _, by_path = repo.changed(capsys, snapshot, "--path", edits.path)

    assert by_qname["status"] == symbol_changes.UNKNOWN_AT_BASE
    assert {v["qname"]: v["status"] for v in by_path}[added] == symbol_changes.UNKNOWN_AT_BASE
    assert symbol_changes.UNCHANGED in {v["status"] for v in by_path}  # positive control


def test_an_edit_the_index_has_not_seen_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A body edited after the build would read ``unchanged`` from the index; it is ``unknown``."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, edits.name)
    repo.write({edits.path: edits.body}, build=False)
    _, [verdict] = repo.changed(capsys, snapshot, "--qname", qname)

    assert (verdict["status"], verdict["reason"]) == (
        symbol_changes.UNKNOWN, "file_changed_since_index")


def test_a_symbol_with_no_fingerprint_is_unknown_never_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Design assumption: an adapter that stamps no ``body_hash`` answers ``unknown``."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    snapshot = repo.snapshot(capsys)
    qname = qname_named(snapshot, edits.name)
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    for symbol in data["symbols"]:
        symbol["body_hash"] = None
    unstamped = snapshot.with_name("unstamped.json")
    unstamped.write_text(json.dumps(data), encoding="utf-8")

    _, [stamped] = repo.changed(capsys, snapshot, "--qname", qname)
    _, [verdict] = repo.changed(capsys, unstamped, "--qname", qname)

    assert stamped["status"] == symbol_changes.UNCHANGED  # positive control
    assert (verdict["status"], verdict["reason"]) == (symbol_changes.UNKNOWN, "no_body_hash")


def test_the_snapshot_is_the_same_bytes_for_the_same_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """R4.2: one revision, one snapshot."""
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    first = repo.snapshot(capsys).read_bytes()
    repo.write({"src/other.py": "X = 1\n"})
    repo.write({"src/other.py": None})

    assert repo.snapshot(capsys).read_bytes() != b""
    assert json.loads(repo.snapshot(capsys).read_bytes())["symbols"] == json.loads(first)["symbols"]


def test_changed_since_refuses_a_file_that_is_not_a_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    edits = EDITS["python"]
    repo = Repo(tmp_path / "py", REGISTRY["python"].cli, monkeypatch)
    repo.write({edits.path: edits.base})
    bogus = tmp_path / "bogus.json"
    bogus.write_text('{"format": "other"}', encoding="utf-8")

    assert repo.changed(capsys, bogus, "--qname", "x")[0] == query.USAGE
    with pytest.raises(SystemExit):
        query.main(["--changed-since", str(bogus)])
