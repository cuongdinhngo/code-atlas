"""The security standard is binding: every row names what holds it, and that thing exists (423).

`docs/SECURITY_STANDARD.md` is one row per `SEC-*` criterion. A criterion written down but checked
by nothing regresses silently, so each row's *Verified by* is a list of typed items this file
resolves — a test that exists, a workflow step that exists, a heading that exists, or the open
ticket that will add the guard. One function, `problems`, judges a row; the planted rows below
prove it refuses each way a row can lie (R6.5).

The second half keeps `SECURITY.md` honest about what code-atlas runs: the git commands it lists are
the ones the code spawns, read from the code, never from a list kept beside it (R6.7).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pytest

from scripts.settings_drift import READERS, parse_set_item

REPO = Path(__file__).resolve().parent.parent
STANDARD = REPO / "docs" / "SECURITY_STANDARD.md"
RULES = REPO / "docs" / "ENGINEERING_RULES.md"
SECURITY_MD = REPO / "SECURITY.md"
TASKS = REPO / "docs" / "tasks"
WORKFLOWS = REPO / ".github" / "workflows"

# The standard's groups, in its order. `test_no_client_identifiers` reads this set to tell a
# criterion id from a tracker key, so a new group is added here and nowhere else.
GROUPS = ("IN", "MCP", "PI", "PL", "SC", "CT", "GV")
SEC_ID = re.compile(r"\bSEC-(" + "|".join(GROUPS) + r")-(\d{2})\b")
ROW = re.compile(r"^\|\s*SEC-")
LEVELS = ("MUST", "SHOULD")
KINDS = ("test", "ci", "doc", "open", "set", "n/a", "deferred")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
# A step's `- name:` or a job's own `name:` (four spaces in); never a workflow or artifact name.
STEP_NAME = re.compile(r"^(?:\s+- |    )name:\s*(.+?)\s*$", re.MULTILINE)
FRONTMATTER_STATUS = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)
GIT_LISTED = re.compile(r"`git (--?[a-z][a-z-]*|[a-z][a-z-]*)")


@dataclass(frozen=True)
class Row:
    id: str
    criterion: str
    level: str
    source: str
    verified_by: str

    def items(self) -> list[tuple[str, str]]:
        parsed = []
        for part in (p.strip() for p in self.verified_by.split(";")):
            kind, sep, value = part.partition(":")
            parsed.append((kind.strip(), value.strip()) if sep else (part, ""))
        return parsed


def rows(text: str | None = None) -> list[Row]:
    text = STANDARD.read_text(encoding="utf-8") if text is None else text
    found = []
    for line in text.splitlines():
        if ROW.match(line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            assert len(cells) == 5, f"a standard row needs 5 cells, has {len(cells)}: {line}"
            found.append(Row(*cells))
    return found


@cache
def _defined_tests(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return frozenset(
        n.name
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
        and n.name.startswith("test")
        and not any("skip" in ast.unparse(d) for d in n.decorator_list)
    )


@cache
def _ci_names() -> frozenset[str]:
    return frozenset(
        name.strip("'\"")
        for wf in sorted(WORKFLOWS.glob("*.y*ml"))
        for name in STEP_NAME.findall(wf.read_text(encoding="utf-8"))
    )


def _headings(path: Path) -> set[str]:
    return set(HEADING.findall(path.read_text(encoding="utf-8")))


def _task_status(number: str) -> str | None:
    found = sorted(TASKS.glob(f"{number}_*.md"))
    if not found:
        return None
    status = FRONTMATTER_STATUS.search(found[0].read_text(encoding="utf-8"))
    return status.group(1) if status else "no status"


def _item_problem(kind: str, value: str, level: str) -> str | None:
    if kind not in KINDS:
        return f"unknown item kind {kind!r} (one of {', '.join(KINDS)})"
    if kind == "test":
        file, sep, name = value.partition("::")
        path = REPO / file
        if not sep or not path.is_file():
            return f"test {value!r}: no such file"
        return None if name in _defined_tests(path) else f"test {value!r}: {file} defines no {name}"
    if kind == "ci":
        return None if value in _ci_names() else f"ci {value!r}: no workflow job or step has it"
    if kind == "doc":
        file, sep, heading = value.partition("#")
        path = REPO / file
        if not sep or not path.is_file():
            return f"doc {value!r}: no such file"
        return None if heading in _headings(path) else f"doc {value!r}: {file} has no such heading"
    if kind == "open":
        if not re.fullmatch(r"\d{3,4}", value):
            return f"open {value!r}: not a ticket number"
        status = _task_status(value)
        if status is None:
            return f"open {value}: no task file docs/tasks/{value}_*.md"
        return (
            f"open {value}: the ticket is done, so the row is held or the ticket lied"
            if (status == "done")
            else None
        )
    if kind == "set":
        item = parse_set_item(value)
        if item is None:
            return f"set {value!r}: not `<name> = <value>`"
        if item[0] in READERS:
            return None
        return f"set {item[0]!r}: scripts/settings_drift.py has no reader"
    if not value:
        return f"{kind} with no reason"
    if kind == "deferred" and level != "SHOULD":
        return f"a {level} row cannot be deferred"
    return None


def problems(row: Row) -> list[str]:
    """Everything wrong with one row, each naming the item at fault (R5.3)."""
    found = []
    if not SEC_ID.fullmatch(row.id):
        found.append(f"id {row.id!r} is not SEC-<{'|'.join(GROUPS)}>-NN")
    if row.level not in LEVELS:
        found.append(f"level {row.level!r} is not one of {LEVELS}")
    if not row.criterion or not row.source:
        found.append("criterion and source must both be written")
    items = row.items() if row.verified_by else []
    if not items:
        return [*found, "Verified by is empty"]
    found += [p for kind, value in items if (p := _item_problem(kind, value, row.level))]
    kinds = {kind for kind, _ in items}
    held = not kinds & {"open", "n/a", "deferred"}
    if held and row.level == "MUST" and not kinds & {"test", "ci"}:
        found.append("a held MUST names no test or CI step — a document alone guards nothing")
    return found


def test_the_standard_has_every_group_numbered_without_gaps() -> None:
    found = rows()
    assert len(found) > len(GROUPS), "the standard parsed to almost nothing; the reader is broken"
    ids = [r.id for r in found]
    assert len(ids) == len(set(ids)), (
        f"duplicate ids: {sorted({i for i in ids if ids.count(i) > 1})}"
    )
    by_group: dict[str, list[int]] = {}
    for row_id in ids:
        match = SEC_ID.fullmatch(row_id)
        assert match, f"{row_id} is not a SEC id of a known group"
        by_group.setdefault(match.group(1), []).append(int(match.group(2)))
    assert tuple(by_group) == GROUPS, f"groups out of order or missing: {tuple(by_group)}"
    for group, numbers in by_group.items():
        assert numbers == list(range(1, len(numbers) + 1)), (
            f"SEC-{group} skips or reorders: {numbers}"
        )


@pytest.mark.parametrize("row", rows(), ids=lambda r: r.id)
def test_every_row_names_what_holds_it(row: Row) -> None:
    assert problems(row) == [], f"{row.id}: " + "; ".join(problems(row))


HELD = "test: tests/test_security_standard.py::test_every_row_names_what_holds_it"
PLANTED = {
    "missing test": "test: tests/test_security_standard.py::test_nobody_wrote_this",
    "missing test file": "test: tests/test_nowhere.py::test_x",
    "a helper, not a test": "test: tests/test_security_standard.py::problems",
    "a workflow name, not a step": "ci: CI",
    "missing CI step": "ci: a step no workflow has",
    "missing heading": "doc: SECURITY.md#No such heading",
    "open on a done ticket": "open: 422",
    "open on a missing ticket": "open: 9999",
    "deferred MUST": "deferred: later",
    "n/a with no reason": "n/a:",
    "held MUST with only a doc": "doc: SECURITY.md#Supported versions",
    "unknown kind": "frobnicate: private vulnerability reporting",
    "a set with no value": "set: secret_scanning",
    "a set name no reader knows": "set: rulesets.main.invented = true",
    "empty": "",
}


@pytest.mark.parametrize("case", sorted(PLANTED))
def test_a_planted_row_is_refused(case: str) -> None:
    planted = Row("SEC-GV-99", "a planted criterion", "MUST", "this test", PLANTED[case])
    assert problems(planted), f"a row with {case} was accepted"


def _an_open_ticket() -> str:
    """A ticket open today: a fixed number goes stale the day it closes (423, 424)."""
    for path in sorted(TASKS.glob("[0-9][0-9][0-9]_*.md")):
        number = path.name[:3]
        if _task_status(number) not in ("done", None):
            return number
    raise AssertionError("no open ticket left to cite")


def test_a_good_row_and_a_deferred_should_are_accepted() -> None:
    assert problems(Row("SEC-GV-99", "c", "MUST", "s", HELD)) == []
    assert problems(Row("SEC-GV-99", "c", "SHOULD", "s", "deferred: no client supports it")) == []
    open_ticket = _an_open_ticket()
    assert problems(Row("SEC-GV-99", "c", "MUST", "s", f"{HELD}; open: {open_ticket}")) == []
    held_by_a_setting = f"{HELD}; set: secret_scanning = enabled"
    assert problems(Row("SEC-GV-99", "c", "MUST", "s", held_by_a_setting)) == []


def test_a_setting_alone_does_not_hold_a_must() -> None:
    """A `set:` is read by a scheduled job; the row still names the test that proves the reader."""
    assert problems(Row("SEC-GV-99", "c", "MUST", "s", "set: secret_scanning = enabled"))


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^(#+) {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"no heading {heading!r}"
    level = len(match.group(1))
    rest = text[match.end() :]
    end = re.search(rf"^#{{1,{level}}} ", rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


def test_section_9_cites_only_criteria_the_standard_has() -> None:
    section = _section(RULES.read_text(encoding="utf-8"), "9. Security")
    rules = re.findall(
        r"^- \*\*(R9\.\d+)\*\*(.*?)(?=^- \*\*R9\.|\Z)", section, re.MULTILINE | re.DOTALL
    )
    assert len(rules) >= 6, f"§9 parsed to {len(rules)} rules; the reader is broken"
    known = {r.id for r in rows()}
    for rule, body in rules:
        cited = {m.group(0) for m in SEC_ID.finditer(body)}
        assert cited, f"{rule} cites no SEC criterion"
        assert cited <= known, f"{rule} cites {sorted(cited - known)}, which the standard lacks"


SPAWNERS = frozenset({"run", "Popen", "check_output", "check_call", "call"})


NON_LITERAL = "<a subcommand not written as a literal>"


def _git_argument(call: ast.Call, path: Path) -> str | None:
    """The subcommand in `gitutil._run(root, "<cmd>", …)` or `<spawn>(["git", "<cmd>", …])`.

    A subcommand built at run time reads as `NON_LITERAL`, so the comparison fails loud on it.
    """
    in_gitutil = path.name == "gitutil.py"
    if in_gitutil and isinstance(call.func, ast.Name) and call.func.id == "_run":
        argument = call.args[1] if len(call.args) > 1 else None
    elif (
        isinstance(call.func, ast.Attribute)
        and call.func.attr in SPAWNERS
        and call.args
        and isinstance(call.args[0], ast.List)
        and len(call.args[0].elts) > 1
        and isinstance(call.args[0].elts[0], ast.Constant)
        and call.args[0].elts[0].value == "git"
    ):
        argument = call.args[0].elts[1]
        if in_gitutil and isinstance(argument, ast.Starred):
            return None  # `_run`'s own spawn: its callers above name the subcommand
        # 427: a starred `-c` hardening run precedes the subcommand; read past it.
        plain = (e for e in call.args[0].elts[1:] if not isinstance(e, ast.Starred))
        argument = next(plain, argument)
    else:
        return None
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return argument.value
    return NON_LITERAL


def _git_commands_in_code() -> set[str]:
    """Every git subcommand code-atlas spawns, read from the call sites themselves."""
    return {
        command
        for top in ("code_atlas", "release_check", "onboarding_llm")
        for path in sorted((REPO / top).rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and (command := _git_argument(node, path))
    }


def test_the_code_reader_finds_the_known_spawners() -> None:
    """Guards the guard: an empty read would make the comparison below pass on an empty list."""
    assert {"ls-files", "rev-parse", "ls-remote"} <= _git_commands_in_code()
    built = ast.parse('subprocess.run(["git", command])').body[0].value  # type: ignore[attr-defined]
    assert _git_argument(built, Path("x.py")) == NON_LITERAL


def test_security_md_names_every_git_command_code_atlas_runs() -> None:
    listed = set(
        GIT_LISTED.findall(_section(SECURITY_MD.read_text(encoding="utf-8"), "Git commands"))
    )
    spawned = _git_commands_in_code()
    assert listed == spawned, (
        f"SECURITY.md's Git commands lists {sorted(listed)}, the code runs {sorted(spawned)}: "
        f"missing {sorted(spawned - listed)}, stale {sorted(listed - spawned)}"
    )


# A module reaches the network if it imports a client library or lists remote refs over git.
NETWORK_MODULES = frozenset(
    {"requests", "httpx", "aiohttp", "socket", "http.client", "urllib.request", "anthropic"}
)
NETWORK_NAMES = {"urllib.request": frozenset({"urlopen", "Request", "build_opener"})}
LISTED_PACKAGE = re.compile(r"`([a-z_]+)/`")


def _reaches_network(tree: ast.AST, path: Path) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name in NETWORK_MODULES for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module in NETWORK_NAMES:
                if {a.name for a in node.names} & NETWORK_NAMES[node.module]:
                    return True
            elif node.module in NETWORK_MODULES:
                return True
            if any(f"{node.module}.{a.name}" in NETWORK_MODULES for a in node.names):
                return True
        if isinstance(node, ast.Call) and _git_argument(node, path) == "ls-remote":
            return True
    return False


def _network_packages() -> set[str]:
    return {
        top
        for top in ("code_atlas", "release_check", "onboarding_llm")
        for path in sorted((REPO / top).rglob("*.py"))
        if _reaches_network(ast.parse(path.read_text(encoding="utf-8")), path)
    }


def test_security_md_names_every_package_that_reaches_the_network() -> None:
    listed = set(
        LISTED_PACKAGE.findall(_section(SECURITY_MD.read_text(encoding="utf-8"), "Network calls"))
    )
    found = _network_packages()
    assert "code_atlas" not in found, "the core reaches the network (R4)"
    assert found == listed - {"code_atlas"}, (
        f"SECURITY.md's Network calls names {sorted(listed)}, the code reaches it from "
        f"{sorted(found)}"
    )
    planted = ast.parse("from urllib.request import urlopen")
    assert _reaches_network(planted, Path("x.py"))
    assert _reaches_network(ast.parse("from urllib import request"), Path("x.py"))
    for inert in ("from urllib.parse import urlparse", "from urllib.request import url2pathname"):
        assert not _reaches_network(ast.parse(inert), Path("x.py")), inert
