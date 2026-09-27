"""What a newcomer asks first, quoted from the repo's own declared files (task 207, M12).

Everything else in the artifact is derived from the symbol graph, which is why the artifact could
describe a healthcare system as twelve layers and 24,535 modules and never say how to run its tests.
The four files a human opens on day one are the four the graph never looked at.

**Quote, never summarise.** Reading a declared file and reproducing a key or a fenced excerpt with
its path is I/O over the repo — the same thing the indexer already does. Deciding what a project is
*for* is inference and belongs to the LLM seam, outside the core (R4.1). So every fact here is
either a value lifted from a structured key or a verbatim excerpt, and every one carries the
``path:line`` it came from — a line with no source is not emitted (AC1/AC5).

**An absence is stated.** A repo that declares no test command gets a line saying so, never silence
(186's rule applied to the artifact). A malformed file degrades to a stated gap and never aborts the
build (R5.3/R5.1 posture, AC4).

Deterministic: files are read in declared order, findings are sorted, and nothing reads the clock
(R4.2). No SQL, no network, no language branch (R1.1/R1.4).
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from code_atlas.containment import resolves_inside

# The ecosystem manifests R2.1 already licenses the project to know, plus the two file *categories*
# every repo publishes for a human reader: a root README, and an agent brief. These are
# cross-ecosystem conventions, never one repo's habits (R2.2) — and all of it is overridable by the
# `project_files` knob, so a repo whose answers live elsewhere declares that instead.
MANIFESTS: tuple[str, ...] = (
    "composer.json",
    "package.json",
    "pyproject.toml",
    "Makefile",
    "docker-compose.yml",
    "docker-compose.yaml",
)
READMES: tuple[str, ...] = ("README.md", "README.rst", "README.txt", "README")
AGENT_BRIEFS: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md")
DEFAULT_PROJECT_FILES: tuple[str, ...] = MANIFESTS + READMES + AGENT_BRIEFS

#: Characters of a README paragraph reproduced as the "what it says it is" excerpt. A quote, so it
#: is bounded rather than summarised; the citation is what makes the rest reachable.
EXCERPT_CHARS = 240

#: A whole file this large is not read. A newcomer's answers live in the first screens of a
#: manifest, and an unbounded read would put a megabyte of README into a build's memory.
MAX_FILE_BYTES = 512 * 1024

_MAKE_TARGET = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\s*:(?!=)")
_YAML_KEY = re.compile(r"^(\s*)([A-Za-z0-9_.\-]+):\s*(.*)$")
_PORT = re.compile(r"^\s*-\s*[\"']?([0-9]+:[0-9]+(?:/[a-z]+)?)[\"']?\s*$")

# A script name that answers "how do I run the tests?". Matched against the DECLARED script name,
# never against a repo's directory layout — the vocabulary is the ecosystem's (R2.2). Compared
# word-wise so `run-tests` and `ci:check` are found, which an exact-match allowlist missed.
_TEST_NAMES = frozenset(
    {"test", "tests", "check", "checks", "ci", "pytest", "phpunit", "spec", "specs"}
)
_WORDS = re.compile(r"[a-z0-9]+")

__all__ = [
    "AGENT_BRIEFS",
    "DEFAULT_PROJECT_FILES",
    "EXCERPT_CHARS",
    "MANIFESTS",
    "MIN_EXCERPT_CHARS",
    "READMES",
    "Fact",
    "Orientation",
    "read_orientation",
]


@dataclass(frozen=True)
class Fact:
    """One cited answer. ``source`` is ``path`` or ``path:line`` and is never empty (AC5)."""

    kind: str
    label: str
    value: str
    source: str

    def as_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "label": self.label, "source": self.source, "value": self.value}


@dataclass(frozen=True)
class Orientation:
    """The day-one answers, the files they came from, and the ones that could not be read.

    ``facts`` empty AND ``read`` empty means no declared project file exists, and the renderer omits
    the section entirely rather than emitting an empty one (Scope 2).
    """

    facts: tuple[Fact, ...] = ()
    read: tuple[str, ...] = ()
    unreadable: tuple[tuple[str, str], ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def declared(self) -> bool:
        """Whether any declared project file was found at all."""
        return bool(self.read or self.unreadable)

    def as_dict(self) -> dict[str, object]:
        """Order-stable dict view — the dataset's byte-stability surface (R4.2)."""
        return {
            "facts": [fact.as_dict() for fact in self.facts],
            "gaps": list(self.gaps),
            "read": list(self.read),
            "unreadable": [{"path": path, "reason": reason} for path, reason in self.unreadable],
        }


def _line_of_key(text: str, name: str) -> int:
    """1-based line declaring ``name`` as a key, or 0. Never a near-miss.

    A bare ``text.find(name)`` cites the first line that merely mentions the string — on a
    ``pyproject.toml`` it resolved every script to the ``name = "code-atlas"`` line. Each spelling
    is anchored to the start of a line so a value containing the word cannot claim the citation.
    """
    quoted = re.escape(name)
    for pattern in (
        rf'^\s*"{quoted}"\s*:',  # JSON key, one per line (the pretty-printed shape)
        rf'^\s*"{quoted}"\s*=',  # TOML quoted key
        rf"^\s*{quoted}\s*=",  # TOML bare key
        rf'"{quoted}"\s*:',  # last resort: a compact one-line JSON object
    ):
        match = re.search(pattern, text, re.MULTILINE)
        if match is not None:
            return text.count("\n", 0, match.start()) + 1
    return 0


def _cite(path: str, line: int) -> str:
    """``path:line``, or bare ``path`` when no line could be established — never a guessed 1."""
    return f"{path}:{line}" if line > 0 else path


def _names_a_test(name: str) -> bool:
    """Whether a DECLARED script/target name says it runs the tests. Word-wise, not exact."""
    return bool(_TEST_NAMES.intersection(_WORDS.findall(name.lower())))


def _read_text(root: Path, name: str) -> tuple[str, str]:
    """``(text, reason)`` — exactly one is non-empty. Never raises (R5.3's posture, AC4)."""
    target = root / name
    try:
        if not target.is_file():
            return "", ""
        if not resolves_inside(root, target):
            return "", "resolves outside the repo; not read"
        if target.stat().st_size > MAX_FILE_BYTES:
            return "", f"larger than {MAX_FILE_BYTES} bytes; not read"
        return target.read_text(encoding="utf-8", errors="replace"), ""
    except OSError as exc:
        return "", f"could not be read ({type(exc).__name__})"


def _scripts(text: str, path: str, table: Mapping[str, object]) -> list[Fact]:
    """Every declared script name and its command line, verbatim. Sorted by name (R4.2)."""
    facts: list[Fact] = []
    for name in sorted(table):
        command = table[name]
        if isinstance(command, list):
            command = " && ".join(str(part) for part in command)
        if not isinstance(command, str) or not command.strip():
            continue
        kind = "test-command" if _names_a_test(name) else "command"
        facts.append(
            Fact(kind, name, command.strip(), _cite(path, _line_of_key(text, name)))
        )
    return facts


def _from_json_manifest(text: str, path: str) -> tuple[list[Fact], str]:
    """``composer.json`` / ``package.json``: scripts, and the declared runtime version."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [], f"is not valid JSON ({exc.__class__.__name__}); no facts taken from it"
    if not isinstance(data, dict):
        return [], "does not hold a JSON object; no facts taken from it"
    facts: list[Fact] = []
    scripts = data.get("scripts")
    if isinstance(scripts, dict):
        facts.extend(_scripts(text, path, scripts))
    # A declared runtime, read as a key rather than named here (R1.1: the core spells no language).
    # Composer's spec makes a `require` key WITHOUT a `/` a platform requirement -- every real
    # package is `vendor/name` -- and npm's `engines` is exactly the runtime map (R2.1).
    for holder, platform_only in (("require", True), ("engines", False)):
        section = data.get(holder)
        if not isinstance(section, dict):
            continue
        for key in sorted(section):
            if platform_only and "/" in key:
                continue
            if isinstance(section[key], str):
                facts.append(
                    Fact("runtime", key, section[key], _cite(path, _line_of_key(text, key)))
                )
    return facts, ""


def _from_pyproject(text: str, path: str) -> tuple[list[Fact], str]:
    """``pyproject.toml``: console scripts and ``requires-python``."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return [], f"is not valid TOML ({exc.__class__.__name__}); no facts taken from it"
    project = data.get("project")
    if not isinstance(project, dict):
        return [], ""
    facts: list[Fact] = []
    scripts = project.get("scripts")
    if isinstance(scripts, dict):
        facts.extend(_scripts(text, path, scripts))
    if isinstance(project.get("requires-python"), str):
        facts.append(
            Fact(
                "runtime",
                "python",
                project["requires-python"],
                _cite(path, _line_of_key(text, "requires-python")),
            )
        )
    return facts, ""


def _from_makefile(text: str, path: str) -> tuple[list[Fact], str]:
    """``Makefile``: each target name and its first recipe line, both verbatim."""
    facts: list[Fact] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = _MAKE_TARGET.match(line)
        if match is None or line.startswith("\t"):
            continue
        name = match.group(1)
        recipe = ""
        for follower in lines[index + 1 :]:
            if follower.startswith("\t"):
                recipe = follower.strip()
                break
            if follower.strip() and not follower.lstrip().startswith("#"):
                break
        kind = "test-command" if _names_a_test(name) else "command"
        facts.append(Fact(kind, f"make {name}", recipe or f"make {name}", _cite(path, index + 1)))
    return facts, ""


def _from_compose(text: str, path: str) -> tuple[list[Fact], str]:
    """``docker-compose.y*ml``: service names and published ports, from BLOCK style only.

    Deliberately not a YAML parser — there is no stdlib one and R8.2 forbids adding a dependency.
    It reads the one unambiguous shape (a top-level ``services:`` mapping of indented keys) and
    reports a gap for anything else rather than guessing, because a guessed service name is worse
    than a stated absence (R5.6).
    """
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.rstrip() in ("services:", "services: ")), -1
    )
    if start < 0:
        return [], ""
    if "&" in text or "<<:" in text or "{" in text.split("services:", 1)[1][:400]:
        return [], "uses YAML anchors or flow style, which this shallow reader does not parse"
    facts: list[Fact] = []
    service = ""
    service_line = 0
    indent = -1
    for offset, line in enumerate(lines[start + 1 :], start=start + 2):
        if line.strip() and not line[:1].isspace():
            break  # back to a top-level key: the services block is over
        match = _YAML_KEY.match(line)
        if match is not None:
            depth = len(match.group(1))
            if indent < 0:
                indent = depth
            if depth == indent:
                service, service_line = match.group(2), offset
                facts.append(Fact("service", service, "declared", _cite(path, offset)))
                continue
        port = _PORT.match(line)
        if port is not None and service:
            facts.append(
                Fact("port", service, port.group(1), _cite(path, service_line or offset))
            )
    return facts, ""


#: A prose line shorter than this is a pointer, not a description — this repo's own `CLAUDE.md` is
#: the single line ``@AGENTS.md``, and quoting that answers nothing.
MIN_EXCERPT_CHARS = 40


def _from_prose(text: str, path: str) -> tuple[list[Fact], str]:
    """A README or agent brief: the first real paragraph, quoted and bounded — never summarised."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "<!--", "=", "-", "*", "|", "```", "@")):
            continue
        if len(stripped) < MIN_EXCERPT_CHARS:
            continue
        excerpt = stripped
        if len(excerpt) > EXCERPT_CHARS:
            excerpt = excerpt[:EXCERPT_CHARS].rstrip() + "…"
        return [Fact("says", "what it says it is", excerpt, _cite(path, index + 1))], ""
    return [], ""


# One reader per declared name. A name with no reader is still recorded as read, so a repo can
# declare a file this version cannot mine and see that stated rather than silently dropped.
_READERS = {
    "composer.json": _from_json_manifest,
    "package.json": _from_json_manifest,
    "pyproject.toml": _from_pyproject,
    "Makefile": _from_makefile,
    "docker-compose.yml": _from_compose,
    "docker-compose.yaml": _from_compose,
}


def read_orientation(
    root: Path | None,
    project_files: Sequence[str] | None = None,
    *,
    max_facts: int = 0,
) -> Orientation:
    """Read the declared project files and return their cited, uninterpreted facts.

    ``project_files`` unset means :data:`DEFAULT_PROJECT_FILES`. Order is the declared order, so the
    output is a function of the declaration and the bytes on disk and nothing else (R4.2).
    ``max_facts`` caps each kind's list where it is built, so ranking precedes truncation (R5.8);
    ``0`` means uncapped.
    """
    if root is None:
        return Orientation()
    names = tuple(project_files) if project_files else DEFAULT_PROJECT_FILES
    facts: list[Fact] = []
    read: list[str] = []
    unreadable: list[tuple[str, str]] = []
    for name in names:
        text, reason = _read_text(root, name)
        if reason:
            unreadable.append((name, reason))
            continue
        if not text:
            continue
        read.append(name)
        reader = _READERS.get(name)
        if reader is not None:
            found, gap = reader(text, name)
        elif name in READMES or name in AGENT_BRIEFS or name.endswith((".md", ".rst", ".txt")):
            found, gap = _from_prose(text, name)
        else:
            found, gap = [], "is declared but this version has no reader for its shape"
        if any(fact.kind == "says" for fact in facts):
            found = [fact for fact in found if fact.kind != "says"]
        facts.extend(found)
        if gap:
            unreadable.append((name, gap))
    if max_facts > 0:
        kept: list[Fact] = []
        seen: dict[str, int] = {}
        for fact in facts:
            seen[fact.kind] = seen.get(fact.kind, 0) + 1
            if seen[fact.kind] <= max_facts:
                kept.append(fact)
        facts = kept
    return Orientation(
        facts=tuple(facts),
        read=tuple(read),
        unreadable=tuple(sorted(unreadable)),
        gaps=_gaps(facts),
    )


def _gaps(facts: Sequence[Fact]) -> tuple[str, ...]:
    """What the declared files did NOT answer. Stated, never left silent (Scope 5, AC2)."""
    kinds = {fact.kind for fact in facts}
    missing = []
    if "test-command" not in kinds:
        missing.append("no declared test command was found in the project files read")
    if "command" not in kinds and "test-command" not in kinds:
        missing.append("no declared scripts or make targets were found")
    if "service" not in kinds:
        missing.append("no declared services were found, so no run command is stated here")
    if "runtime" not in kinds:
        missing.append("no declared language runtime version was found")
    if "says" not in kinds:
        missing.append("no README or agent-brief paragraph was available to quote")
    return tuple(missing)
