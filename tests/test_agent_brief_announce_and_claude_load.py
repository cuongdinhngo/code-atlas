"""Task 270 — announce the agent brief and offer Claude Code's AGENTS.md import (never write)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402

from code_atlas.main import TOOL_NAMES  # noqa: E402

README = REPO / "README.md"
RUNBOOK = REPO / "docs" / "runbooks" / "onboarding-a-repo.md"
# Tool-shaped tokens in prose (snake_case identifiers the surface could name).
_TOOLISH = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")


def test_write_agent_brief_flag_is_announced_in_readme_and_runbook() -> None:
    """AC1: the flag appears where a user looks — README and the onboarding runbook."""
    assert "--write-agent-brief" in README.read_text(encoding="utf-8")
    assert "--write-agent-brief" in RUNBOOK.read_text(encoding="utf-8")


def test_readme_brief_subsection_names_no_tool_the_generator_lacks() -> None:
    """AC1 / R6.7: any TOOL_NAMES token in the README brief subsection must be on which_tool."""
    text = README.read_text(encoding="utf-8")
    start = text.index("### Agent brief (optional)")
    end = text.index("\n## ", start + 1)
    section = text[start:end]
    mapped = set(gen_skill.recognition_lines_by_tool())
    surface = set(TOOL_NAMES)
    hits = sorted({m.group(1) for m in _TOOLISH.finditer(section)} & surface)
    drift = [t for t in hits if t not in mapped]
    assert not drift, f"README brief names tools not on which_tool map: {drift}"


def test_setup_project_without_flag_prints_offer(tmp_path: Path) -> None:
    """AC2: PROJECT given without --write-agent-brief names the flag on the closing screen."""
    project = tmp_path / "proj"
    project.mkdir()
    done = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "setup.py"), str(project), "--no-adapter"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "--write-agent-brief" in done.stdout
    assert "AGENTS.md" in done.stdout


def test_missing_agents_import_prints_offer_and_leaves_claude_md_identical(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: CLAUDE.md without @AGENTS.md → print the import line; file bytes unchanged."""
    claude = tmp_path / "CLAUDE.md"
    original = "# Consumer repo\n\nNo import yet.\n"
    claude.write_text(original, encoding="utf-8")
    gen_skill.write_agent_brief(tmp_path)
    out = capsys.readouterr().out
    assert gen_skill.CLAUDE_IMPORT_OFFER in out
    assert gen_skill.AGENTS_IMPORT_LINE in out
    assert claude.read_text(encoding="utf-8") == original


def test_existing_agents_import_is_silent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: CLAUDE.md already importing AGENTS.md → no offer line."""
    (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    gen_skill.write_agent_brief(tmp_path)
    out = capsys.readouterr().out
    assert gen_skill.CLAUDE_IMPORT_OFFER not in out


def test_no_claude_md_is_silent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No CLAUDE.md → nothing to offer; AGENTS.md still written."""
    path = gen_skill.write_agent_brief(tmp_path)
    out = capsys.readouterr().out
    assert gen_skill.CLAUDE_IMPORT_OFFER not in out
    assert path.is_file()


def test_import_in_claude_local_md_is_silent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC3: the offer names CLAUDE.local.md, so an import living there must silence it."""
    (tmp_path / "CLAUDE.md").write_text("# team rules\n", encoding="utf-8")
    (tmp_path / "CLAUDE.local.md").write_text("@AGENTS.md\n", encoding="utf-8")
    gen_skill.write_agent_brief(tmp_path)
    assert gen_skill.CLAUDE_IMPORT_OFFER not in capsys.readouterr().out
