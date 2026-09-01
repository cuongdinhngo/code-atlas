"""The committed `contrib/` artifacts equal what their generator produces (task 200, AC1).

`which_tool` maps every question onto a tool and lives in the one channel a model never sees (081).
200 emits it as an Agent Skill — and a hand-kept copy of a surface is exactly how 036's
PHP-only hook filter rotted across two adapter launches. R6.7: derive it or check it;
never re-type it.

The two mutation controls below are R6.5's *observe the guard failing*: a comparison nobody has seen
go red proves only that two things were read.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402


@pytest.mark.parametrize("path", sorted(gen_skill.GENERATED, key=lambda p: p.name))
def test_the_committed_artifact_equals_its_generator_output(path: Path) -> None:
    wanted = gen_skill.GENERATED[path]()
    assert path.read_text(encoding="utf-8") == wanted, (
        f"{path.relative_to(REPO)} has drifted from its source — "
        "run `python scripts/gen_skill.py --write`"
    )


def test_mutating_the_committed_side_is_caught(tmp_path: Path) -> None:
    # R6.5 control a: a stale committed file must be red, not merely present.
    mutated = gen_skill.render_skill().replace("get_index_status", "get_index_statuz", 1)
    assert mutated != gen_skill.render_skill()
    assert mutated != gen_skill.SKILL_PATH.read_text(encoding="utf-8")


def test_mutating_the_source_side_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    # R6.5 control b: a tool added to the server must move the skill, or the guard reads nothing.
    monkeypatch.setattr(gen_skill, "TOOL_NAMES", (*gen_skill.TOOL_NAMES, "a_new_tool"))
    assert gen_skill.render_skill() != gen_skill.SKILL_PATH.read_text(encoding="utf-8")
    assert "a_new_tool" in gen_skill.render_skill()


def test_the_recognition_map_covers_every_served_tool() -> None:
    """The skill may not describe a surface the server does not serve — nor miss one it does."""
    mapped = gen_skill.recognition_map()
    missing = [name for name in gen_skill.TOOL_NAMES if not any(name in line for line in mapped)]
    assert not missing, f"tools served but absent from the recognition map: {missing}"
