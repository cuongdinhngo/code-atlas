"""Task 125 — every payload can name the server build, not just the index schema."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from code_atlas.build_info import server_identity
from code_atlas.config import load_config
from code_atlas.tools import get_index_status, impact
from code_atlas.tools.get_index_status import NAME as STATUS
from tests.test_claim_signing import SUBJECT, configured, fields, indexed_repo

REPO = Path(__file__).resolve().parent.parent
RUNTIME_DOCKERFILE = REPO / "docker" / "Dockerfile.runtime"
RUNTIME_TAG = "code-atlas-server-test-125"


def test_standard_status_reports_server_version_and_build(tmp_path: Path) -> None:
    """AC1: ``get_index_status(standard)`` names the running server."""
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"")
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    status = get_index_status.create(config, (STATUS,))(detail_level="standard")

    ident = server_identity()
    assert status["server_version"] == ident["version"]
    assert status["server_build"] == ident["build"]
    assert re.fullmatch(r"[0-9a-f]{7}(\+dirty)?", str(status["server_build"]))


def test_minimal_status_carries_server_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """223 AC4: cheapest tier keeps identity fields; empty next_tool_suggestions is omitted."""
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.resolve()))
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True)
    db_path.write_bytes(b"")
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    minimal = get_index_status.create(config, (STATUS,))(detail_level="minimal")

    assert "server_version" in minimal
    assert "server_build" in minimal
    assert "server_stale_process" in minimal
    assert "next_tool_suggestions" not in minimal  # current+indexed → empty → omitted


def test_server_identity_is_stable_across_calls() -> None:
    """AC5 / R4.2: derived once from the artifact, never from a clock."""
    first = server_identity()
    second = server_identity()
    assert first == second
    assert first["build"] == second["build"]


def test_content_hash_distinguishes_two_package_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: two builds of the same declared version differ when the package bytes differ.

    Drives ``build_info._content_build_id`` itself — a digest re-implemented in the test would
    pass unchanged if the shipped one were replaced by a constant.
    """
    from code_atlas import build_info

    pkg_a = tmp_path / "pkg_a" / "code_atlas"
    pkg_b = tmp_path / "pkg_b" / "code_atlas"
    for pkg in (pkg_a, pkg_b):
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg_a / "probe.py").write_text("A = 1\n", encoding="utf-8")
    (pkg_b / "probe.py").write_text("A = 2\n", encoding="utf-8")

    def build_id_of(root: Path) -> str:
        monkeypatch.setattr(build_info, "_PACKAGE_ROOT", root)
        return build_info._content_build_id()

    first, second = build_id_of(pkg_a), build_id_of(pkg_b)
    assert first != second
    assert len(first) == len(second) == build_info.BUILD_ID_CHARS
    assert build_id_of(pkg_a) == first  # same bytes, same id (R4.2)


def test_claim_line_carries_server_and_build(tmp_path: Path) -> None:
    """AC4: a signed claim names the server alongside the index revision."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    line = fields(impact.create(config)(qnames=[SUBJECT], sign=True))
    ident = server_identity()

    assert line["server"] == ident["version"]
    assert line["build"] == ident["build"]


def test_claims_from_two_builds_are_textually_distinguishable(tmp_path: Path) -> None:
    """AC4: a third party can tell which build produced each quoted line."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)

    with patch(
        "code_atlas.tools.claim.server_identity",
        return_value={"version": "0.1.0", "build": "aaaaaaa"},
    ):
        first = fields(impact.create(config)(qnames=[SUBJECT], sign=True))
    with patch(
        "code_atlas.tools.claim.server_identity",
        return_value={"version": "0.1.0", "build": "bbbbbbb"},
    ):
        second = fields(impact.create(config)(qnames=[SUBJECT], sign=True))

    assert first["build"] != second["build"]
    assert first["server"] == second["server"] == "0.1.0"


def test_build_id_without_git_uses_content_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC2 path: no ``.git`` ⇒ content hash still names the build (wheel / runtime image)."""
    from code_atlas import build_info

    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info, "_git_root", lambda: None)
    ident = build_info.server_identity()
    build_info.reset_identity_cache()
    assert ident["version"]
    assert len(ident["build"]) == 7


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker not on PATH")
def test_runtime_image_reports_server_build() -> None:
    """AC2: the shipped runtime container exposes server identity, not only dev checkouts."""
    subprocess.run(
        [
            "docker",
            "build",
            "-f",
            str(RUNTIME_DOCKERFILE),
            "-t",
            RUNTIME_TAG,
            str(REPO),
        ],
        check=True,
        timeout=600,
    )
    probe = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            RUNTIME_TAG,
            "-c",
            "from code_atlas.build_info import server_identity; "
            "import json; print(json.dumps(server_identity()))",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    ident = json.loads(probe.stdout)
    assert ident["version"]
    assert len(ident["build"]) == 7


def test_retro_template_records_server_build_from_status() -> None:
    """AC6: round 7 can answer §0.a from one ``get_index_status`` call."""
    text = (REPO / "docs" / "runbooks" / "field-retro.md").read_text(encoding="utf-8")
    assert "0.a" in text
    assert "server_version" in text
    assert "server_build" in text
    assert "get_index_status" in text


def test_dirty_checkout_is_not_reported_as_its_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """125: a modified tree must not answer under the clean commit's id.

    The retro reads the build id to say which code answered. A checkout with uncommitted
    changes is not the commit it sits on, so quoting that commit is the same wrong-subject
    error this ticket exists to remove.
    """
    from code_atlas import build_info

    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")

    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: False)
    clean = build_info._git_build_id()
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: True)
    dirty = build_info._git_build_id()
    # git unable to answer is not evidence of a dirty tree.
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: None)
    unknown = build_info._git_build_id()

    assert clean == "abcdef1"
    assert dirty == "abcdef1+dirty"
    assert unknown == clean
    assert dirty != clean


def test_missing_package_metadata_does_not_break_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naming the build is a diagnostic; it must degrade, not raise (cf. gitutil's None)."""
    from code_atlas import build_info

    def absent(name: str) -> str:
        raise build_info.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(build_info.importlib.metadata, "version", absent)
    assert build_info._package_version() == build_info.UNKNOWN_VERSION


def test_stale_process_when_loaded_differs_from_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """164 AC1: a process whose loaded code differs from HEAD's content reports the loaded id.

    Simulates the divergence a `git pull` under a running server causes — without a real pull —
    by pinning the frozen loaded id below the current disk content. The build must be the loaded
    id, `stale_process` must be true, and the repo HEAD must ride alongside as context.
    """
    from code_atlas import build_info

    build_info.reset_identity_cache()
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "0ldc0de")
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")

    ident = build_info.server_identity()
    build_info.reset_identity_cache()

    assert ident["build"] == "0ldc0de"
    assert ident["stale_process"] is True
    assert ident["repo_head"] == "abcdef1"
    assert ident["build"] != ident["repo_head"]

    prov = build_info.server_provenance()
    assert prov["server_stale_process"] is True
    assert prov["server_repo_head"] == "abcdef1"
    assert prov["server_stale_action"] == build_info.SERVER_STALE_ACTION
    assert prov["server_stale_differs"] == list(build_info.SERVER_STALE_DIFFERS)
    assert prov["server_stale_impact"] in (
        build_info.STALE_IMPACT_UNCHANGED,
        build_info.STALE_IMPACT_CHANGED,
    )
    assert prov["server_build_kind"] == build_info.BUILD_KIND_CONTENT_HASH


def test_matching_process_carries_the_verdict_and_no_divergence_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """164 AC2 / 061, widened by 170: the verdict rides, the divergence CONTEXT does not.

    164 omitted `stale_process` on the matching branch, which made "checked and matching" identical
    to "never checked" — round 11 §12.c could not tell them apart. `server_repo_head` stays
    conditional: it is context for a divergence, meaningless without one.
    """
    from code_atlas import build_info

    build_info.reset_identity_cache()
    # Force the matching branch: loaded id equals the current content id, git commit present.
    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", build_info._content_build_id())
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")
    monkeypatch.setattr(build_info.gitutil, "working_tree_dirty", lambda root: False)

    prov = build_info.server_provenance()
    build_info.reset_identity_cache()

    assert set(prov) == {"server_version", "server_build", "server_stale_process"}
    assert prov["server_stale_process"] is False, "the verdict, not silence (170)"
    assert prov["server_build"] == "abcdef1"


def test_stale_process_is_deterministic_across_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """164 AC4 / R4.2: the diverged id derives from the loaded artifact, not a clock."""
    from code_atlas import build_info

    monkeypatch.setattr(build_info, "_LOADED_BUILD_ID", "0ldc0de")
    monkeypatch.setattr(build_info, "_git_root", lambda: tmp_path)
    monkeypatch.setattr(build_info.gitutil, "head_commit", lambda root: "abcdef1234567890")

    build_info.reset_identity_cache()
    first = build_info.server_identity()
    build_info.reset_identity_cache()
    second = build_info.server_identity()
    build_info.reset_identity_cache()
    assert first == second


def test_one_time_hash_walk_is_bounded(tmp_path: Path) -> None:
    """164 AC3: the package-tree hash is a one-time, bounded cost — recorded in the task file.

    Not a wall-clock assertion (R4.2 bars a clock in the id); this pins the size of the walk so
    the recorded timing stays interpretable. The whole `code_atlas` tree is a few hundred KB.
    """
    from code_atlas import build_info

    paths = list(build_info._PACKAGE_ROOT.rglob("*.py"))
    total_bytes = sum(p.stat().st_size for p in paths)
    assert total_bytes < 5_000_000, f"package tree grew to {total_bytes} B — re-measure AC3"
