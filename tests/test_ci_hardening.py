"""424 — CI cannot be steered by a moved tag or a leaked token.

One function, `problems`, reads a workflow's text and names everything that breaks SEC-SC-01..04.
The real test runs it over EVERY file in `.github/workflows/` (427-C1: never a named few); each
planted workflow below proves one arm refuses its violation (R6.5).

PyYAML is not a dev dependency, so `load` reads the YAML subset the workflows use: maps, lists,
block scalars, flow lists, quoted and plain scalars, plain scalars continued on deeper lines.

It fails closed (I1): a flow mapping or sequence, an anchor, an alias or a merge key is an
unsupported shape, so a workflow the reader cannot parse faithfully is refused, never skipped.
Composite actions under `.github/actions/` are read too: pins, credentials, event expressions.

The write-scope rule: a job may hold a write permission only when its workflow has no
`pull_request` / `pull_request_target` trigger, or when the job has no `actions/checkout` step
(it then has no pull-request code on disk to run). A job that calls a reusable workflow has no
checkout of its own, so there a write scope under a pull-request trigger is refused outright.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.y*ml"))
ACTIONS = sorted((REPO / ".github" / "actions").glob("**/action.y*ml"))
DEPENDABOT = REPO / ".github" / "dependabot.yml"

USES = re.compile(r"^\s*(?:- )?uses:\s*(?P<ref>\S+)(?P<rest>.*)$", re.MULTILINE)
PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
VERSION_COMMENT = re.compile(r"^\s*#\s*v?\d+\.\d+(\.\d+)?\S*\s*$")
EVENT_IN_RUN = re.compile(r"\$\{\{[^}]*\bgithub\.(event\b|head_ref\b)")
KEY = re.compile(r"""^("[^"]*"|'[^']*'|[^\s:#'"][^:#]*?)\s*:(?:\s+(.*))?$""")
PR_TRIGGERS = {"pull_request", "pull_request_target"}


# ---- a reader for the YAML subset the workflows use -------------------------------------------


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _skip(lines: list[str], i: int) -> int:
    while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
        i += 1
    return i


def _uncomment(text: str) -> str:
    quote = ""
    for k, ch in enumerate(text):
        opens = k == 0 or text[k - 1] in " [,"
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"" and opens:
            quote = ch
        elif ch == "#" and opens:
            return text[:k].rstrip()
    return text.strip()


def _scalar(text: str) -> Any:
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(p.strip()) for p in text[1:-1].split(",") if p.strip()]
    if text == "{}":
        return {}
    if len(text) > 1 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def _value(lines: list[str], i: int, ind: int, rest: str) -> tuple[Any, int]:
    """The value after `key:` (or `- `) at indent ``ind``, starting from line ``i`` (the key's)."""
    rest = _uncomment(rest or "")
    if rest[:1] in ("|", ">"):
        j, body = i + 1, []
        while j < len(lines) and (not lines[j].strip() or _indent(lines[j]) > ind):
            body.append(lines[j])
            j += 1
        pad = min((_indent(b) for b in body if b.strip()), default=0)
        return "\n".join(b[pad:] for b in body).strip("\n"), j
    if rest:
        j, parts = i + 1, [rest]
        while j < len(lines) and (not lines[j].strip() or _indent(lines[j]) > ind):
            if lines[j].strip() and not lines[j].lstrip().startswith("#"):
                parts.append(_uncomment(lines[j].strip()))
            j += 1
        return _scalar(" ".join(parts)), j
    j = _skip(lines, i + 1)
    if j < len(lines) and (
        _indent(lines[j]) > ind or (_indent(lines[j]) == ind and lines[j].lstrip().startswith("- "))
    ):
        return _node(lines, j)
    return None, i + 1


def _node(lines: list[str], i: int) -> tuple[Any, int]:
    i = _skip(lines, i)
    ind = _indent(lines[i])
    return (_seq if lines[i].lstrip().startswith("- ") else _map)(lines, i, ind)


def _map(lines: list[str], i: int, ind: int) -> tuple[dict[str, Any], int]:
    out: dict[str, Any] = {}
    while (i := _skip(lines, i)) < len(lines) and _indent(lines[i]) == ind:
        match = KEY.match(lines[i].strip())
        if not match or lines[i].lstrip().startswith("- "):
            break
        out[_scalar(match[1])], i = _value(lines, i, ind, match[2])
    return out, i


def _seq(lines: list[str], i: int, ind: int) -> tuple[list[Any], int]:
    out: list[Any] = []
    while (i := _skip(lines, i)) < len(lines) and _indent(lines[i]) == ind:
        if not lines[i].lstrip().startswith("- "):
            break
        body = lines[i].lstrip()[2:]
        if KEY.match(body.strip()):
            lines[i] = " " * (ind + 2) + body
            item, i = _map(lines, i, ind + 2)
        else:
            item, i = _value(lines, i, ind, body)
        out.append(item)
    return out, i


def load(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    return _node(lines, 0)[0] if _skip(lines, 0) < len(lines) else {}


# ---- the judgement ----------------------------------------------------------------------------


def _triggers(doc: dict[str, Any]) -> set[str]:
    on = doc.get("on", doc.get("true"))
    if isinstance(on, str):
        return {on}
    return set(on) if isinstance(on, dict | list) else set()


def _writes(permissions: Any) -> list[str]:
    if isinstance(permissions, str):
        return [permissions] if permissions.startswith("write") else []
    return [f"{k}: {v}" for k, v in (permissions or {}).items() if v == "write"]


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in job.get("steps") or [] if isinstance(s, dict)]


def shape_problems(text: str) -> list[str]:
    """Flow collections, anchors, aliases and merge keys outside quotes and block scalars."""
    found, block = [], None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        ind = _indent(line)
        if block is not None and ind > block:
            continue
        block = None
        body = _uncomment(line.strip())
        while body.startswith("- "):
            body, ind = body[2:].strip(), ind + 2
        key = KEY.match(body)
        value = ((key[2] or "") if key else body).strip()
        if key and key[1] == "<<" or value[:1] in ("[", "{") or re.match(r"[&*][\w-]", value):
            found.append(f"[shape] line {n}: unsupported YAML shape — rewrite in block style")
        if value[:1] in ("|", ">"):
            block = ind
    return found


def _event_in(step: dict[str, Any]) -> bool:
    values = [step.get("run", "")] + list((step.get("with") or {}).values())
    return any(EVENT_IN_RUN.search(str(v)) for v in values)


def problems(text: str, action: bool = False) -> list[str]:
    """Everything wrong with one workflow (or composite action), each tagged `[arm]`."""
    found = shape_problems(text)
    for m in USES.finditer(text):
        ref = m["ref"]
        if ref.startswith("./"):
            continue
        if not PINNED.match(ref):
            found.append(f"[pin] {ref} is not owner/repo@<40-hex>")
        elif not VERSION_COMMENT.match(m["rest"]):
            found.append(f"[pin] {ref} has no `# vX.Y.Z` comment")
    doc = load(text)
    doc = doc if isinstance(doc, dict) else {}
    triggers: set[str] = set()
    jobs: dict[str, Any] = {"(action)": {"steps": (doc.get("runs") or {}).get("steps")}}
    if not action:
        if doc.get("permissions") != {"contents": "read"}:
            found.append(
                f"[permissions] top-level is {doc.get('permissions')!r}, not contents: read"
            )
        triggers = _triggers(doc)
        jobs = doc.get("jobs") or {}
    for forbidden in sorted(triggers & {"pull_request_target", "workflow_run"}):
        found.append(f"[trigger] {forbidden} is forbidden")
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue  # an unparsed shape; `[shape]` already names it
        steps = _steps(job)
        checks_out = any(str(s.get("uses", "")).startswith("actions/checkout@") for s in steps)
        calls_workflow = "uses" in job
        for write in _writes(job.get("permissions")):
            if triggers & PR_TRIGGERS and (checks_out or calls_workflow):
                found.append(f"[write-scope] job {name}: {write} beside pull-request code")
        for step in steps:
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                if (step.get("with") or {}).get("persist-credentials") != "false":
                    found.append(f"[credentials] job {name}: a checkout keeps its token")
            if _event_in(step):
                found.append(
                    f"[interpolation] job {name}: an event expression inside run: or with:"
                )
    return found


def _arm(arm: str, text: str, action: bool = False) -> list[str]:
    return [p for p in problems(text, action) if p.startswith(f"[{arm}]")]


# ---- the real workflows -----------------------------------------------------------------------


def test_the_reader_found_every_workflow_and_its_jobs() -> None:
    """Guards the guard: an empty glob or a parse to nothing would pass every arm vacuously."""
    names = {p.name for p in WORKFLOWS}
    assert {"ci.yml", "cross-repo.yml", "tokens-to-answer-sample.yml"} <= names
    assert {"codeql.yml", "scorecard.yml", "settings-drift.yml"} <= names
    for path in WORKFLOWS:
        doc = load(path.read_text(encoding="utf-8"))
        assert doc.get("jobs"), f"{path.name} parsed to no jobs"
        assert _triggers(doc), f"{path.name} parsed to no triggers"
    assert len(USES.findall(WORKFLOWS[0].read_text(encoding="utf-8"))) > 0


ARMS = ["shape", "pin", "permissions", "trigger", "write-scope", "credentials"]
EVERY_FILE = [(p, False) for p in WORKFLOWS] + [(p, True) for p in ACTIONS]


@pytest.mark.parametrize("arm", ARMS)
@pytest.mark.parametrize(("path", "action"), EVERY_FILE, ids=lambda v: getattr(v, "name", ""))
def test_every_workflow_holds_the_arm(path: Path, action: bool, arm: str) -> None:
    assert _arm(arm, path.read_text(encoding="utf-8"), action) == []


@pytest.mark.parametrize(("path", "action"), EVERY_FILE, ids=lambda v: getattr(v, "name", ""))
def test_no_run_block_interpolates_an_event_expression(path: Path, action: bool) -> None:
    assert _arm("interpolation", path.read_text(encoding="utf-8"), action) == []


def test_every_uses_is_a_full_sha_with_a_version_comment() -> None:
    total = 0
    for path in WORKFLOWS:
        text = path.read_text(encoding="utf-8")
        total += len(USES.findall(text))
        assert _arm("pin", text) == [], path.name
    assert total >= 20, "the pin check read almost nothing"


def test_codeql_runs_on_push_and_schedule_only() -> None:
    """H4: its `security-events: write` must never sit beside pull-request code."""
    doc = load((REPO / ".github" / "workflows" / "codeql.yml").read_text(encoding="utf-8"))
    assert _triggers(doc) == {"push", "schedule"}


# ---- planted violations (R6.5) ----------------------------------------------------------------

SHA = "a" * 40
GOOD = f"""\
on:
  pull_request:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v4.4.0
        with:
          persist-credentials: false
      - run: echo ok
"""


def _plant(old: str, new: str) -> str:
    assert old in GOOD, old
    return GOOD.replace(old, new)


PLANTED = {
    "shape": [
        _plant("on:\n  pull_request:", "on: [pull_request]"),
        _plant("contents: read", "{contents: read}").replace("permissions:\n  {", "permissions: {"),
        _plant("persist-credentials: false", "persist-credentials: &off false"),
        _plant("persist-credentials: false", "persist-credentials: *off"),
        _plant("jobs:\n", "jobs:\n  base: &base\n    runs-on: ubuntu-latest\n"),
        _plant("  build:\n", "  build:\n    <<: *base\n"),
    ],
    "pin": [
        _plant(f"@{SHA}", "@v4"),
        _plant(f"@{SHA} # v4.4.0", f"@{SHA}"),
        _plant(f"@{SHA}", "@" + "a" * 39),
    ],
    "permissions": [
        _plant("permissions:\n  contents: read\n", ""),
        _plant("contents: read", "contents: write"),
        _plant("contents: read", "contents: read\n  issues: read"),
    ],
    "trigger": [
        _plant("pull_request:", "pull_request_target:"),
        _plant("on:\n  pull_request:", "on:\n  workflow_run:\n    workflows: [CI]"),
    ],
    "write-scope": [
        _plant(
            "    runs-on: ubuntu-latest\n    steps:",
            f"    permissions:\n      issues: write\n    uses: o/r/.github/workflows/w.yml@{SHA}\n"
            "    steps:",
        ),
        _plant(
            "    runs-on: ubuntu-latest\n",
            "    runs-on: ubuntu-latest\n    permissions:\n      pull-requests: write\n",
        ),
    ],
    "credentials": [
        _plant("persist-credentials: false", "persist-credentials: true"),
        _plant("        with:\n          persist-credentials: false\n", ""),
    ],
    "interpolation": [
        _plant("echo ok", "echo ${{ github.event.pull_request.title }}"),
        _plant("echo ok", "echo ${{ github.head_ref }}"),
        _plant(
            "- run: echo ok",
            "- run: |\n          echo hi\n          echo ${{ github.event.number }}",
        ),
        _plant(
            "- run: echo ok",
            f"- uses: actions/github-script@{SHA} # v7.1.0\n"
            "        with:\n          script: |\n"
            "            core.info('${{ github.event.pull_request.title }}')",
        ),
        _plant(
            "- run: echo ok",
            f"- uses: x/y@{SHA} # v1.0.0\n        with:\n          arg: ${{{{ github.head_ref }}}}",
        ),
    ],
}


def test_the_good_workflow_is_clean() -> None:
    assert problems(GOOD) == []


@pytest.mark.parametrize(
    ("arm", "text"),
    [(arm, text) for arm, texts in PLANTED.items() for text in texts],
)
def test_a_planted_violation_is_refused(arm: str, text: str) -> None:
    assert _arm(arm, text), f"a planted {arm} violation was accepted:\n{text}"


def test_block_scalars_and_quoted_values_are_not_mistaken_for_flow_shapes() -> None:
    text = _plant(
        "- run: echo ok",
        "- run: |\n          [ -f x ] && echo '{a}' *.md &x\n"
        '      - name: "[quoted]"\n        if: ${{ !cancelled() }}',
    )
    assert _arm("shape", text) == []


COMPOSITE = f"""\
name: x
runs:
  using: composite
  steps:
    - uses: actions/checkout@{SHA} # v4.4.0
      with:
        persist-credentials: false
    - run: echo ok
      shell: bash
"""
PLANTED_ACTION = {
    "pin": COMPOSITE.replace(f"@{SHA}", "@v4"),
    "credentials": COMPOSITE.replace("persist-credentials: false", "persist-credentials: true"),
    "interpolation": COMPOSITE.replace("echo ok", "echo ${{ github.event.issue.title }}"),
    "shape": COMPOSITE.replace("using: composite", "using: {x: composite}"),
}


def test_a_composite_action_is_read_like_a_workflow() -> None:
    assert problems(COMPOSITE, action=True) == []
    for arm, text in PLANTED_ACTION.items():
        assert _arm(arm, text, action=True), f"action: a planted {arm} violation was accepted"


def test_the_actions_glob_reaches_a_nested_action_file(tmp_path: Path) -> None:
    nested = tmp_path / ".github" / "actions" / "deep" / "er" / "action.yaml"
    nested.parent.mkdir(parents=True)
    nested.write_text(COMPOSITE, encoding="utf-8")
    assert sorted((tmp_path / ".github" / "actions").glob("**/action.y*ml")) == [nested]


def test_a_write_scope_is_allowed_where_no_pull_request_code_runs() -> None:
    scheduled = GOOD.replace("pull_request:", "schedule:\n    - cron: '0 6 * * 1'")
    with_write = scheduled.replace(
        "    runs-on: ubuntu-latest\n",
        "    runs-on: ubuntu-latest\n    permissions:\n      issues: write\n",
    )
    assert _arm("write-scope", with_write) == []
    no_checkout = _plant(
        "    runs-on: ubuntu-latest\n",
        "    runs-on: ubuntu-latest\n    permissions:\n      pull-requests: write\n",
    ).replace(
        f"      - uses: actions/checkout@{SHA} # v4.4.0\n        with:\n"
        "          persist-credentials: false\n",
        "",
    )
    assert _arm("write-scope", no_checkout) == []


def test_the_reader_reads_the_shapes_the_workflows_use() -> None:
    doc = load(
        "on: [push]\njobs:\n  a:\n    steps:\n"
        "      - name: x # note\n        run: python -m x\n          -y 'z'\n"
        "      - uses: q/r@" + SHA + ' # v1.0.0\n        with:\n          k: "v"\n'
    )
    steps = doc["jobs"]["a"]["steps"]
    assert doc["on"] == ["push"]
    assert steps[0]["run"] == "python -m x -y 'z'" and steps[0]["name"] == "x"
    assert steps[1]["with"] == {"k": "v"}


# ---- Dependabot (SEC-SC-05) -------------------------------------------------------------------


def _manifest_dirs(manifest: str) -> set[str]:
    """`/adapters/<x>` for every adapter that holds ``manifest`` — derived, never hand-listed."""
    return {
        f"/{p.parent.relative_to(REPO).as_posix()}" for p in REPO.glob(f"adapters/*/{manifest}")
    }


def expected_ecosystems() -> set[tuple[str, str]]:
    return (
        {("pip", "/"), ("github-actions", "/"), ("docker", "/docker")}
        | {("npm", d) for d in _manifest_dirs("package.json")}
        | {("composer", d) for d in _manifest_dirs("composer.json")}
    )


def dependabot_problems(text: str) -> list[str]:
    doc = load(text)
    found = [] if str(doc.get("version")) == "2" else ["version is not 2"]
    seen = set()
    for entry in doc.get("updates") or []:
        key = (entry.get("package-ecosystem"), entry.get("directory"))
        seen.add(key)
        if (entry.get("schedule") or {}).get("interval") != "weekly":
            found.append(f"{key} is not weekly")
        if not entry.get("groups"):
            found.append(f"{key} has no group")
        if not (REPO / str(key[1]).lstrip("/")).is_dir():
            found.append(f"{key}: the directory does not exist")
    found += [f"{key} is missing" for key in sorted(expected_ecosystems() - seen)]
    return found


def test_dependabot_covers_every_ecosystem_and_directory() -> None:
    assert dependabot_problems(DEPENDABOT.read_text(encoding="utf-8")) == []


def test_the_expected_ecosystems_are_derived_from_the_manifests() -> None:
    expected = expected_ecosystems()
    assert {("npm", "/adapters/typescript"), ("npm", "/adapters/sql")} <= expected
    assert ("composer", "/adapters/php") in expected


def test_a_planted_dependabot_gap_is_refused() -> None:
    text = DEPENDABOT.read_text(encoding="utf-8")
    assert dependabot_problems(text.replace("composer", "nuget"))
    assert dependabot_problems(text.replace("weekly", "daily"))
    assert dependabot_problems(text.replace("/adapters/sql", "/adapters/nowhere"))
    assert dependabot_problems("version: 2\nupdates: []\n")
