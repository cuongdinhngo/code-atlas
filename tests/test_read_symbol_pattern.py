"""Task 449 — `read_symbol(pattern=…)` returns only the matching lines of a long body."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas.config import Config, load_config
from code_atlas.indexer import full_build
from code_atlas.store import GraphStore
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import read_symbol

REPO = Path(__file__).resolve().parent.parent
PHP_ENTRY = REPO / "adapters" / "php" / "index.php"
PHP_AUTOLOAD = REPO / "adapters" / "php" / "vendor" / "autoload.php"
PHP = shutil.which("php")
pytestmark = pytest.mark.skipif(
    PHP is None or not PHP_AUTOLOAD.is_file(),
    reason="needs the PHP CLI and `composer install` in adapters/php",
)
MANIFEST = REPO / "tests" / "fixtures" / "tool_manifest.json"

# Line 4 opens `long()`; its body is 400 statements, so lines 5..404, closing at 405.
BODY = [f"        $v{i} = {i};" for i in range(400)]
NEEDLES = {
    100: "        $x = $this->needle();",
    103: "        $y = 'NEEDLE';",
    300: "        needle();",
}
for at, text in NEEDLES.items():
    BODY[at - 5] = text
SOURCE = (
    "<?php\nnamespace App;\nclass Big {\n    public function long() {\n"
    + "\n".join(BODY)
    + "\n    }\n    public function many() {\n"
    + "\n".join("        needle();" for _ in range(60))
    + "\n    }\n}\n"
)


@pytest.fixture(scope="module")
def config(tmp_path_factory: pytest.TempPathFactory) -> Config:
    root = tmp_path_factory.mktemp("repo")
    (root / "src").mkdir()
    (root / "src" / "Big.php").write_text(SOURCE, encoding="utf-8")
    for args in (("init", "-q"), ("add", "-A"), ("commit", "-qm", "init")):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    built = load_config(
        root,
        {"CA_WORKERS": "1", "CA_PHP_CMD": shlex.join([str(PHP), str(PHP_ENTRY), "--server"])},
    )
    with GraphStore(built.db_path) as store:
        assert full_build(built, store).failed == 0
    return built


def test_ac1_a_pattern_returns_the_matching_lines_not_the_body(config: Config) -> None:
    tool = read_symbol.create(config)
    payload = tool("\\App\\Big::long", pattern="needle")
    assert payload["pattern_matches"] == 3
    assert payload["pattern_span"] == {"line_start": 4, "line_end": 405}
    # 100 and 103 share their context, so they merge; every line carries its absolute number.
    hunks = payload["pattern_hunks"]
    assert [(h["line_start"], h["line_end"]) for h in hunks] == [(98, 105), (298, 302)]
    assert hunks[0]["lines"][2] == "100>         $x = $this->needle();"
    assert hunks[0]["lines"][3] == "101:         $v96 = 96;"
    assert "$v200" not in json.dumps(payload)
    whole = tool("\\App\\Big::long", full_body=True)
    pattern_tokens = estimate_tokens(json.dumps(payload))
    whole_tokens = estimate_tokens(json.dumps(whole))
    # Reported against the whole-body answer (AC1): a few hundred tokens against thousands.
    print(f"449 AC1 tokens: pattern={pattern_tokens} whole_body={whole_tokens}")
    assert pattern_tokens * 5 < whole_tokens


def test_scope1_the_literal_is_case_insensitive_and_a_regex_is_opt_in(config: Config) -> None:
    tool = read_symbol.create(config)
    assert tool("\\App\\Big::long", pattern="NEEDLE")["pattern_matches"] == 3
    assert tool("\\App\\Big::long", pattern="needle()")["pattern_matches"] == 2
    regex = tool("\\App\\Big::long", pattern=r"^\s+needle\(\)", pattern_regex=True)
    assert regex["pattern_matches"] == 1


def test_scope1_a_refused_regex_names_the_rule_it_broke(config: Config) -> None:
    tool = read_symbol.create(config)
    with pytest.raises(ValueError, match="an alternation inside a repeat"):
        tool("\\App\\Big::long", pattern="(a|aa)+$", pattern_regex=True)
    with pytest.raises(ValueError, match="a backreference"):
        tool("\\App\\Big::long", pattern=r"(a)\1", pattern_regex=True)
    with pytest.raises(ValueError, match="over the 512 limit"):
        tool("\\App\\Big::long", pattern="a" * 513, pattern_regex=True)


def test_scope2_context_and_the_cap(config: Config) -> None:
    tool = read_symbol.create(config)
    tight = tool("\\App\\Big::long", pattern="needle", context=0)
    assert [len(h["lines"]) for h in tight["pattern_hunks"]] == [1, 1, 1]
    many = tool("\\App\\Big::many", pattern="needle")
    assert many["pattern_matches"] == 60
    assert many["pattern_truncated"] is True
    shown = [line for hunk in many["pattern_hunks"] for line in hunk["lines"] if ">" in line[:5]]
    assert len(shown) == 50
    assert "pattern_truncated" not in tool("\\App\\Big::long", pattern="needle")


def test_scope3_no_match_says_the_body_was_searched(config: Config) -> None:
    payload = read_symbol.create(config)("\\App\\Big::long", pattern="absent")
    assert payload["pattern_matches"] == 0
    assert payload["pattern_hunks"] == []
    assert payload["pattern_span"] == {"line_start": 4, "line_end": 405}


def test_a_line_range_narrows_the_search(config: Config) -> None:
    payload = read_symbol.create(config)(
        "\\App\\Big::long", pattern="needle", line_start=200, line_end=405
    )
    assert payload["pattern_matches"] == 1
    assert payload["pattern_span"] == {"line_start": 200, "line_end": 405}


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"pattern": ""}, "must not be empty"),
        ({"pattern": "x", "full_body": True}, "drop full_body"),
        ({"pattern": "x", "max_lines": 5}, "drop full_body"),
        ({"pattern": "x", "context": 11}, "context must be 0–10"),
        ({"context": 1}, "need a pattern"),
        ({"pattern_regex": True}, "need a pattern"),
    ],
)
def test_invalid_combinations_are_refused_at_the_entry(
    config: Config, kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        read_symbol.create(config)("\\App\\Big::long", **kwargs)


def test_scope4_the_closed_schema_lists_the_new_parameters_and_nothing_else() -> None:
    tools = json.loads(MANIFEST.read_text(encoding="utf-8"))["tools"]
    schema = next(tool for tool in tools if tool["name"] == "read_symbol")["input_schema"]
    assert schema["additionalProperties"] is False
    assert {"pattern", "pattern_regex", "context"} <= set(schema["properties"])
