"""Task 006 AC1/AC2: the PHP adapter's ``--file`` output is a valid contract result for real PHP.

Every assertion here drives the real interpreter against the real parser, because that is the layer
where the claim can fail — a fake standing in for the subprocess would prove only that the fake is
consistent with itself. CI installs both, so CI is where this file is authoritative.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from code_atlas import contract

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "php"
ENTRY = ADAPTER / "index.php"
AUTOLOAD = ADAPTER / "vendor" / "autoload.php"
FIXTURES = ROOT / "tests" / "fixtures" / "php"

# AC1 says "each" of these two file shapes — the denominator every assertion below counts against.
CASES = {"namespaced": "namespaced.php", "global-underscore": "global_underscore.php"}

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not AUTOLOAD.is_file(),
    reason=f"needs the PHP CLI and `composer install` in {ADAPTER}",
)


def parse(case: str) -> dict[str, object]:
    """Run the adapter exactly as the acceptance criterion spells it, from the repo root."""
    fixture = (FIXTURES / CASES[case]).relative_to(ROOT)
    completed = subprocess.run(
        [str(PHP), str(ENTRY), "--file", str(fixture)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.count("\n") == 1, "--file emits one line and nothing else"
    return json.loads(completed.stdout)


def test_the_proof_has_something_to_run() -> None:
    # Runs without PHP: a skipped proof must not also hide a missing entry point or fixture.
    assert len(CASES) == 2
    assert ENTRY.is_file()
    for name in CASES.values():
        assert (FIXTURES / name).read_text(encoding="utf-8").startswith("<?php")


@needs_php
@pytest.mark.parametrize("case", CASES, ids=list(CASES))
def test_the_fixture_parses_to_a_valid_contract_result(case: str) -> None:
    result = parse(case)

    assert contract.validate(result) == []
    assert result["ok"] is True
    # validate() alone would pass an `ok:false` result, so an adapter that parsed nothing.
    assert result["nodes"], "a valid but empty result proves nothing"
    assert result["edges"]


@needs_php
def test_a_namespaced_file_resolves_every_name_to_a_leading_backslash_fqn() -> None:
    result = parse("namespaced")
    qnames = {node["qualified_name"] for node in result["nodes"]}

    assert {
        "\\App\\Models",
        "\\App\\Models\\Storable",
        "\\App\\Models\\User",
        "\\App\\Models\\User::save",
        "\\App\\Models\\User::$name",
        "\\App\\Models\\User::ROLE",
        "\\App\\Models\\helper",
    } <= qnames

    targets = {(edge["kind"], edge["target_raw"]) for edge in result["edges"]}
    assert ("EXTENDS", "\\App\\Models\\Base") in targets
    # The alias `use App\Contracts\Jsonable as J` must reach the import, not the local name `J`.
    assert ("IMPLEMENTS", "\\App\\Contracts\\Jsonable") in targets
    assert ("IMPORTS", "\\App\\Contracts\\Jsonable") in targets
    assert ("NEW", "\\App\\Models\\User") in targets


@needs_php
def test_a_global_underscore_file_keeps_its_underscores_and_carries_no_namespace() -> None:
    result = parse("global-underscore")
    qnames = {node["qualified_name"] for node in result["nodes"]}

    assert {"\\Foo_Bar_Baz", "\\Foo_Bar_Baz::fetchRow", "\\foo_helper"} <= qnames
    assert not [node for node in result["nodes"] if node["kind"] == "Namespace"]
    # One separator means the name sits directly in the global namespace, underscores and all.
    assert all(qname.count("\\") == 1 for qname in qnames if qname.startswith("\\"))

    targets = {(edge["kind"], edge["target_raw"]) for edge in result["edges"]}
    assert ("EXTENDS", "\\Legacy_Table") in targets
    assert ("CALLS", "\\Legacy_Registry::get") in targets
    assert ("INCLUDES", "Legacy/Registry.php") in targets


@needs_php
def test_every_class_like_kind_the_visitor_maps_is_actually_emitted() -> None:
    # A dispatch entry no fixture reaches is untested code, not coverage (LESSONS 002).
    kinds = {node["kind"] for node in parse("namespaced")["nodes"]}
    assert {"Class", "Interface", "Trait", "Enum"} <= kinds


@needs_php
def test_a_declared_type_survives_whatever_shape_it_was_written_in() -> None:
    # A scalar hint reported as null is indistinguishable from no hint at all — silent data loss.
    nodes = {node["qualified_name"]: node for node in parse("namespaced")["nodes"]}
    assert [param["type"] for param in nodes["\\App\\Models\\User::rename"]["params"]] == [
        "string",
        "?int",
    ]
    assert [param["type"] for param in nodes["\\App\\Models\\User::save"]["params"]] == [
        "\\App\\Models\\Repo"
    ]


@needs_php
def test_a_missing_runtime_fails_loud_and_never_as_a_parse_result(tmp_path: Path) -> None:
    # R5.3: copied away from its vendor/, the entry point must refuse rather than emit ok:false.
    stray = tmp_path / "index.php"
    stray.write_text(ENTRY.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [str(PHP), str(stray), "--file", str((FIXTURES / CASES["namespaced"]).relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "composer install" in completed.stderr


@needs_php
@pytest.mark.parametrize("case", CASES, ids=list(CASES))
def test_every_edge_is_bare_and_no_guess_is_recorded_as_resolved(case: str) -> None:
    # R3.3 and R5.2: the adapter never links across files, and never dresses a guess as certain.
    for edge in parse(case)["edges"]:
        assert "target_qname" not in edge
        assert edge["target_raw"]

    calls = [edge for edge in parse("namespaced")["edges"] if edge["kind"] == "CALLS"]
    assert [edge["confidence_tier"] for edge in calls] == ["HEURISTIC"]


@needs_php
@pytest.mark.parametrize("case", CASES, ids=list(CASES))
def test_the_same_file_parses_to_the_same_bytes(case: str) -> None:
    # R4.2: nothing in the emitted result may depend on wall-clock, iteration order, or a path hash.
    assert json.dumps(parse(case), sort_keys=True) == json.dumps(parse(case), sort_keys=True)
