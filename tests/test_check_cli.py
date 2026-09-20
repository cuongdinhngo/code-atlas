"""Task 303: ``code-atlas-check`` composes impact + rules + architecture drift."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from code_atlas import check
from code_atlas.config import load_config
from code_atlas.onboarding.artifact import MANIFEST_NAME, OUTPUT_DIR
from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore
from code_atlas.tools import check_architecture_rules, impact
from code_atlas.tools.generate_onboarding import (
    assemble_onboarding_snapshot,
    manifest_dict_for,
)
from tests.test_architecture_rules import _transitive_repo

REPO = Path(__file__).resolve().parent.parent


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _git_repo(root: Path) -> str:
    """Init repo, commit planted files, return HEAD sha used as an automatic base parent."""
    _git(root, "init", "-q", ".")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    _git(root, "branch", "-M", "main")
    return head


def _write_baseline(config) -> None:
    assembled = assemble_onboarding_snapshot(config)
    assert assembled is not None
    out = Path(config.root) / OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    payload = manifest_dict_for(assembled, config)
    (out / MANIFEST_NAME).write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _prepare(
    tmp_path: Path,
    *,
    heuristic_last: bool = False,
    policies: list[dict] | None = None,
):
    """The shared Change Assurance fixture; ``policies`` also plants a 307 budget file."""
    config = _transitive_repo(tmp_path, heuristic_last=heuristic_last)
    # run_check loads config from disk — plant the project file and default db location.
    db_default = tmp_path / ".code-atlas" / "graph.db"
    db_default.parent.mkdir(parents=True, exist_ok=True)
    if config.db_path.resolve() != db_default.resolve():
        shutil.move(str(config.db_path), str(db_default))
    policy_line = ""
    if policies is not None:
        policy_line = 'architecture_policy = "policy.json"\n'
        (tmp_path / "policy.json").write_text(
            json.dumps({"version": 1, "policies": policies}, indent=2) + "\n",
            encoding="utf-8",
        )
    (tmp_path / ".code-atlas.toml").write_text(
        'architecture_rules = ["rules.json"]\n' + policy_line,
        encoding="utf-8",
    )
    with GraphStore(db_default) as store:
        store.set_meta(INDEXED_SUFFIXES_KEY, ".aa")
    _git_repo(tmp_path)
    config = load_config(tmp_path)
    _write_baseline(config)
    return config


def test_ac8_red_first_fail_on_confirmed_before_report_only(tmp_path: Path) -> None:
    """AC8 — confirmed fixture fails the opt-in gate; same fixture is green in report mode."""
    _prepare(tmp_path)
    code_fail, result_fail = check.run_check(
        tmp_path, base_override="main", fail_on_confirmed=True, skip_build=True
    )
    assert code_fail == check.CONFIRMED_VIOLATIONS
    assert result_fail["confirmed_count"] == 1
    code_ok, result_ok = check.run_check(
        tmp_path, base_override="main", fail_on_confirmed=False, skip_build=True
    )
    assert code_ok == check.OK
    assert result_ok["mode"] == "report_only"
    assert result_ok["confirmed_count"] == 1
    assert "CONFIRMED" in check.render_text(result_ok)


def test_ac2_default_report_mode_shows_confirmed_and_exits_zero(tmp_path: Path) -> None:
    """AC2 — confirmed violation rendered; default exit success; reason report_only."""
    _prepare(tmp_path)
    code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert code == check.OK
    assert result["reason"] == check.REASON_REPORT_ONLY
    assert result["confirmed_count"] == 1
    text = check.render_text(result)
    assert "domain-must-not-reach-http" in text
    assert "CONFIRMED" in text


def test_ac3_fail_on_confirmed_and_candidate_only(tmp_path: Path) -> None:
    """AC3 — confirmed → exit 2; candidate-only does not."""
    confirmed = tmp_path / "confirmed"
    candidate = tmp_path / "candidate"
    confirmed.mkdir()
    candidate.mkdir()
    _prepare(confirmed)
    _prepare(candidate, heuristic_last=True)
    code_c, _ = check.run_check(
        confirmed, base_override="main", fail_on_confirmed=True, skip_build=True
    )
    assert code_c == check.CONFIRMED_VIOLATIONS
    code_h, result_h = check.run_check(
        candidate, base_override="main", fail_on_confirmed=True, skip_build=True
    )
    assert code_h == check.OK
    assert result_h["confirmed_count"] == 0
    assert result_h["candidate_count"] == 1
    # Impact/page truncation must not flip a candidate-only gate to operational (challenger F1).
    assert result_h["reason"] != "truncated_evidence"


def test_ac4_missing_rules_is_operational(tmp_path: Path) -> None:
    """AC4 — capability_not_configured is non-success, never a clean report."""
    _prepare(tmp_path)
    (tmp_path / ".code-atlas.toml").write_text("# no architecture_rules\n", encoding="utf-8")
    code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert code == check.OPERATIONAL
    assert result["reason"] == "capability_not_configured"


def test_ac4_missing_baseline_is_snapshot_not_found(tmp_path: Path) -> None:
    """AC4 — missing architecture baseline → snapshot_not_found, not 'no change'."""
    _prepare(tmp_path)
    (tmp_path / OUTPUT_DIR / MANIFEST_NAME).unlink()
    code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert code == check.OPERATIONAL
    assert result["reason"] == "snapshot_not_found"


def test_ac4_unresolved_base(tmp_path: Path) -> None:
    """AC4 — base_not_resolved when --base cannot be derived."""
    _prepare(tmp_path)
    code, result = check.run_check(tmp_path, base_override="no-such-ref-xyz", skip_build=True)
    assert code == check.OPERATIONAL
    assert result["reason"] == check.REASON_BASE_NOT_RESOLVED


def test_ac1_parity_with_underlying_tools(tmp_path: Path) -> None:
    """AC1 — impact + rules rows match direct factory calls at the same revision."""
    config = _prepare(tmp_path)
    code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert code == check.OK
    direct_rules = check_architecture_rules.create(config)()
    assert result["architecture_rules"]["total_count"] == direct_rules["total_count"]
    assert result["architecture_rules"]["results"] == direct_rules["results"]
    paths = result["changed_indexed"]
    direct_impact = impact.create(config)(paths=list(paths) if paths else None, sign=True)
    assert result["impact"].get("claim") == direct_impact.get("claim")
    assert result["impact"].get("total_count") == direct_impact.get("total_count")
    assert result["impact"].get("results") == direct_impact.get("results")


def test_ac5_dirty_unindexed_disclosed(tmp_path: Path) -> None:
    """AC5 — dirty unindexed docs are disclosed; they do not invent graph impact seeds."""
    _prepare(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("dirty doc\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-qm", "docs")
    # Dirty it after committing so it reaches the change set through the working tree.
    readme.write_text("dirty doc changed\n", encoding="utf-8")
    code, result = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert code == check.OK
    assert "README.md" in result["changed_paths"]
    assert "README.md" in result["dirty_unindexed"]
    assert "README.md" not in result["changed_indexed"]


def test_ac6_deterministic_dual_render(tmp_path: Path) -> None:
    """AC6 — two runs → byte-identical JSON; text/JSON both from the same object."""
    _prepare(tmp_path)
    _, a = check.run_check(tmp_path, base_override="main", skip_build=True)
    _, b = check.run_check(tmp_path, base_override="main", skip_build=True)
    assert check.render_json(a) == check.render_json(b)
    text = check.render_text(a)
    assert str(a["confirmed_count"]) in text
    assert a["base"] is not None
    # JSON round-trip preserves counts the text also shows.
    parsed = json.loads(check.render_json(a))
    assert parsed["confirmed_count"] == a["confirmed_count"]
    assert "CONFIRMED" in text


def test_ac7_no_second_pipeline_import_guard() -> None:
    """AC7 — check.py imports the existing factories rather than re-declaring graph walks."""
    source = (REPO / "code_atlas" / "check.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    joined = "\n".join(sorted(imported))
    assert "code_atlas.tools.impact" in joined
    assert "check_architecture_rules" in joined
    assert "diff_architecture" in joined
    assert "code_atlas.tools.build_or_update_index.create" in joined
    # Must not open a raw SQL walk of its own.
    assert "SELECT " not in source


def test_console_script_registered() -> None:
    """Entry point lands beside code-atlas-build."""
    pyproject = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]
    assert scripts["code-atlas-check"] == "code_atlas.check:main"
    # Installed dist may lag editable; the pyproject pin is the contract.


def test_cli_json_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--json`` emits the result object on stdout."""
    _prepare(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    code = check.main(["--base", "main", "--json", "--skip-build"])
    assert code == check.OK
