"""Which references in agent-facing docs still resolve against the code (438).

An agent reads ``CLAUDE.md``, skills and docs as true, and nothing checks them. This module reads a
corpus of markdown files, pulls out the references they make — file paths, symbols written whole,
bare names in code spans — and gives each exactly one state with a reason: ``ok``, ``moved`` (a
successor), ``gone``, ``never_existed``, ``ambiguous`` or ``unknown``. An unknown is never folded
into ``ok`` (R5.6). Language-free: what a symbol looks like comes from each adapter's ``qualified``
shape, stored at build (R1.1). Read-only: git is read through ``gitutil``; nothing is written.
"""

from __future__ import annotations

import dataclasses
import posixpath
import re
import tempfile
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config
from code_atlas.containment import read_text, resolves_inside, safe_write
from code_atlas.contract import MEMBER_SEPARATOR, QUALIFIED_SHAPE
from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore, Row
from code_atlas.tools.symbol_pointers import (
    DEFINITION_LIVE,
    declared_precedence,
    definition_states,
)

# Priority classes, most authoritative first; `archive` is reported, never counted (439's line).
INSTRUCTION, MEMORY, REFERENCE, ARCHIVE = "instruction", "memory", "reference", "archive"
CLASSES: tuple[str, ...] = (INSTRUCTION, MEMORY, REFERENCE, ARCHIVE)
COUNTED_CLASSES: tuple[str, ...] = (INSTRUCTION, MEMORY, REFERENCE)
DEFAULT_GLOBS: Mapping[str, tuple[str, ...]] = {
    INSTRUCTION: (
        "**/CLAUDE.md",
        "**/AGENTS.md",
        ".claude/rules/**",
        ".claude/skills/**",
        ".cursor/rules/**",
        ".github/copilot-instructions.md",
    ),
    MEMORY: (),
    REFERENCE: ("docs/**", "wiki/**", "*.wiki/**"),
    ARCHIVE: (),
}
DOC_SUFFIXES = frozenset({".md", ".mdc", ".markdown"})

OK, MOVED, GONE, NEVER_EXISTED, AMBIGUOUS, UNKNOWN = (
    "ok", "moved", "gone", "never_existed", "ambiguous", "unknown"
)
STATES: tuple[str, ...] = (MOVED, GONE, NEVER_EXISTED, AMBIGUOUS, UNKNOWN, OK)
PATH, SYMBOL, NAME = "path", "symbol", "name"
CODE_SPAN, FENCE, LINK, PROSE = "code_span", "fence", "link", "prose"

DEFAULT_LIMIT = 200
MAX_REF_CHARS = 512
MAX_LIMIT = 1000
CANDIDATE_CAP = 5
# Wall-clock git may spend on history questions per run; past it a row is `unknown`, counted.
HISTORY_BUDGET_S = 12.0
GIT_CALL_CAP_S = 5.0
# A file suffix a doc names as a path, beside the ones the index read.
_DOC_FILE_SUFFIXES = frozenset(
    {"md", "mdc", "json", "toml", "yaml", "yml", "txt", "sh", "cfg", "ini", "lock", "xml", "html",
     "css", "csv", "env", "conf", "dockerfile", "mk", "gradle"}
)
_SHELL_LANGS = frozenset({"sh", "bash", "shell", "console", "zsh", "shell-session", "powershell"})
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*([\w+-]*)")
_SPAN = re.compile(r"(`+)(.+?)\1")
_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_LINE_SUFFIX = re.compile(r"(?::\d+(?:[-:]\d+)*|#L\d+(?:-L?\d+)?)$")
_IDENTIFIER = re.compile(r"^[A-Za-z_][\w]*$")
_WORD_RUN = re.compile(r"[\w$#@]+")
_UNSAFE = re.compile(r"[\s*?{}<>|^~`'\"]|://")
_TRIM = "`'\".,;:!?()[]{}*_"


@dataclass(frozen=True, slots=True)
class Mention:
    """One reference string as a doc wrote it, and where — never the prose around it (429)."""

    file: str
    line: int
    doc_class: str
    context: str  # the line's shape: list_item · table_cell · heading · quote · prose · fence
    origin: str  # code_span · fence · link · prose
    ref: str


@dataclass(slots=True)
class Corpus:
    """The files read, by class, and what each class's globs were."""

    files: dict[str, str] = field(default_factory=dict)  # path -> class
    globs: dict[str, tuple[str, ...]] = field(default_factory=dict)
    commands: dict[str, int] = field(default_factory=dict)  # class -> command lines counted


def class_globs(config: Config) -> dict[str, tuple[str, ...]]:
    """Each class's globs: the toml's when set (430: globs, never a command), else the default."""
    configured = {
        INSTRUCTION: config.refs_instruction,
        MEMORY: config.refs_memory,
        REFERENCE: config.refs_reference,
        ARCHIVE: config.refs_archive,
    }
    return {name: configured[name] or DEFAULT_GLOBS[name] for name in CLASSES}


def glob_regex(glob: str) -> re.Pattern[str]:
    """A path glob: ``**`` spans directories, ``*`` and ``?`` stay inside one."""
    out = ""
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif glob.startswith("**", i):
            out += ".*"
            i += 2
        elif glob[i] == "*":
            out += "[^/]*"
            i += 1
        elif glob[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(glob[i])
            i += 1
    return re.compile(out + r"\Z")


def classify(path: str, globs: Mapping[str, Sequence[str]]) -> str | None:
    """The class a doc belongs to: `archive` wins (report-only), then the most authoritative."""
    for name in (ARCHIVE, *COUNTED_CLASSES):
        if any(glob_regex(glob).match(path) for glob in globs.get(name, ())):
            return name
    return None


def collect(config: Config, only: Sequence[str] = ()) -> Corpus:
    """The corpus: tracked and untracked, non-ignored markdown files a class's globs name.

    ``only`` (CLI globs) narrows the files; a file no class names is then `reference`.
    """
    globs = class_globs(config)
    listed = gitutil.ls_files(config.root)
    paths = list(listed or ()) + list(gitutil.ls_untracked(config.root) or ())
    if listed is None:
        paths = [p.relative_to(config.root).as_posix() for p in config.root.rglob("*.md")]
    corpus = Corpus(globs=globs)
    narrow = [glob_regex(glob) for glob in only]
    for path in sorted(set(paths)):
        if Path(path).suffix.lower() not in DOC_SUFFIXES:
            continue
        if narrow and not any(regex.match(path) for regex in narrow):
            continue
        found = classify(path, globs) or (REFERENCE if narrow else None)
        if found is not None:
            corpus.files[path] = found
    return corpus


def _context(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return "heading"
    if stripped.startswith("|"):
        return "table_cell"
    if stripped.startswith(">"):
        return "quote"
    if _LIST_ITEM.match(line):
        return "list_item"
    return "prose"


def extract(path: str, doc_class: str, text: str) -> tuple[list[Mention], int]:
    """Every candidate reference in a markdown text, and how many command lines it holds."""
    mentions: list[Mention] = []
    commands = 0
    fence: tuple[str, str] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        opened = _FENCE.match(line)
        if fence is not None:
            if opened and opened.group(1).startswith(fence[0][0]) and len(opened.group(1)) >= len(
                fence[0]
            ):
                fence = None
                continue
            shell = fence[1].lower() in _SHELL_LANGS
            if shell and line.strip() and not line.lstrip().startswith("#"):
                commands += 1
            for word in re.split(r"[\s()\[\]{},;=\"']+", line):
                mentions.append(Mention(path, number, doc_class, "fence", FENCE, word))
            continue
        if opened:
            fence = (opened.group(1), opened.group(2))
            continue
        context = _context(line)
        rest = line
        for span in _SPAN.finditer(line):
            body = span.group(2).strip()
            if body.startswith("$ ") or " " in body:
                commands += 1  # a span with a space is a command or a code fragment, never one ref
                continue
            mentions.append(Mention(path, number, doc_class, context, CODE_SPAN, body))
        rest = _SPAN.sub(" ", rest)
        for link in _LINK.finditer(rest):
            mentions.append(Mention(path, number, doc_class, context, LINK, link.group(1)))
        rest = _LINK.sub(" ", rest)
        for word in rest.split():
            mentions.append(Mention(path, number, doc_class, context, PROSE, word))
    return mentions, commands


@dataclass(frozen=True, slots=True)
class Shapes:
    """The adapters' `qualified` shapes and the suffixes the index read, from the build's meta."""

    qualified: tuple[tuple[re.Pattern[str], frozenset[str]], ...]
    suffixes: frozenset[str]

    @classmethod
    def from_store(cls, store: GraphStore) -> Shapes:
        found: list[tuple[re.Pattern[str], frozenset[str]]] = []
        for entry in store.stamped_symbol_shapes().values():
            extensions = frozenset(str(e).lower() for e in _listed(entry.get("extensions")))
            for shape in _listed(entry.get("shapes")):
                if isinstance(shape, dict) and shape.get("kind") == QUALIFIED_SHAPE:
                    try:
                        found.append((re.compile(str(shape.get("pattern", ""))), extensions))
                    except re.error:
                        continue
        stored = store.get_meta(INDEXED_SUFFIXES_KEY) or ""
        suffixes = frozenset(s.lstrip(".").lower() for s in stored.split(",") if s)
        return cls(tuple(found), suffixes)

    def qualified_suffixes(self, ref: str) -> frozenset[str] | None:
        """The suffixes of the adapters whose shape names ``ref``, or None when none does."""
        hits = [ext for pattern, ext in self.qualified if pattern.match(ref)]
        return frozenset().union(*hits) if hits else None


def kind_of(raw: str, origin: str, shapes: Shapes) -> tuple[str, str] | None:
    """The cleaned reference and its kind, or None when the string is no reference."""
    ref = raw.strip().strip(_TRIM) if origin == PROSE else raw.strip()
    call = ref.endswith("()")
    ref = ref.removesuffix("()").rstrip(".,;:")
    if origin == LINK:
        ref = ref.split("#", 1)[0]
    ref = _LINE_SUFFIX.sub("", ref).removeprefix("./")
    if not ref or len(ref) > MAX_REF_CHARS or _UNSAFE.search(ref):
        return None
    if ref.startswith(("/", "-", "$", "#", "@", "mailto:")):
        return None
    last = ref.rstrip("/").rsplit("/", 1)[-1]
    suffix = last.rsplit(".", 1)[-1].lower() if "." in last.strip(".") else ""
    if "/" in ref or (suffix and (suffix in shapes.suffixes or suffix in _DOC_FILE_SUFFIXES)):
        return ref, PATH
    if origin == LINK:
        return None
    if shapes.qualified_suffixes(ref) is not None:
        return ref, SYMBOL
    if origin == CODE_SPAN and _IDENTIFIER.match(ref) and (call or len(ref) > 2):
        return ref + ("()" if call else ""), NAME
    return None


@dataclass(frozen=True, slots=True)
class _DirIndex:
    """Every directory history names, built once per run: a lookup, never a scan per reference."""

    added: frozenset[str]
    deleted: Mapping[str, tuple[str, str]]  # dir -> its newest file deletion
    renamed: Mapping[str, set[str | None]]  # old dir -> the dirs its files moved to

    @classmethod
    def build(cls, history: gitutil.PathHistory, added: frozenset[str]) -> _DirIndex:
        dirs: set[str] = set()
        for path in added:
            dirs.update(_parents(path))
        deleted: dict[str, tuple[str, str]] = {}
        for path, seen in history.deleted.items():
            for parent in _parents(path):
                deleted.setdefault(parent, seen)
        renamed: dict[str, set[str | None]] = {}
        for old, new in history.renamed.items():
            for parent in _parents(old):
                tail = old[len(parent) + 1:]
                renamed.setdefault(parent, set()).add(
                    new[: -len(tail) - 1] if new.endswith("/" + tail) else None
                )
        return cls(frozenset(dirs), deleted, renamed)


def _by_basename(paths: Iterable[str]) -> dict[str, list[str]]:
    """Files and the directories that hold them, by last segment."""
    index: dict[str, set[str]] = {}
    for path in paths:
        index.setdefault(path.rsplit("/", 1)[-1], set()).add(path)
        for parent in _parents(path):
            index.setdefault(parent.rsplit("/", 1)[-1], set()).add(parent)
    return {name: sorted(found) for name, found in index.items()}


def _parents(path: str) -> Iterator[str]:
    while "/" in path:
        path = path.rsplit("/", 1)[0]
        yield path


@dataclass(slots=True)
class Verdict:
    state: str
    reason: str
    detail: dict[str, object] = field(default_factory=dict)


class Resolver:
    """Answers one reference at a time; history is read once per run and only when needed."""

    def __init__(
        self, config: Config, store: GraphStore, shapes: Shapes, budget_s: float = HISTORY_BUDGET_S
    ) -> None:
        self.config = config
        self.budget_s = budget_s
        self.store = store
        self.shapes = shapes
        self.precedence = declared_precedence(store)
        self._history: gitutil.PathHistory | None | bool = False
        self._added: frozenset[str] | None | bool = False
        self._doc_revs: dict[str, tuple[str, str] | None] = {}
        self.skipped_external = 0
        self._dirs: _DirIndex | None = None
        self._tracked: Mapping[str, list[str]] | None = None
        self._added_by_name: Mapping[str, list[str]] | None = None
        self._spent = 0.0
        self.budget_spent = 0

    # ----------------------------------------------------------------- shared
    def _exists(self, rel: str) -> bool:
        target = self.config.root / rel
        return target.exists() and resolves_inside(self.config.root, target)

    def _git_budget(self) -> float | None:
        left = self.budget_s - self._spent
        if left <= 0:
            self.budget_spent += 1
            return None
        return min(left, GIT_CALL_CAP_S)

    def _clock(self, started: float) -> None:
        self._spent += time.monotonic() - started

    def history(self) -> gitutil.PathHistory | None:
        if self._history is False:
            budget = self._git_budget()
            started = time.monotonic()
            found = gitutil.path_history(self.config.root, timeout=budget) if budget else None
            self._clock(started)
            self._history = found
        return self._history if isinstance(self._history, gitutil.PathHistory) else None

    def added(self) -> frozenset[str] | None:
        if self._added is False:
            budget = self._git_budget()
            started = time.monotonic()
            found = gitutil.paths_ever_added(self.config.root, timeout=budget) if budget else None
            self._clock(started)
            self._added = found
        return self._added if isinstance(self._added, frozenset) else None

    def doc_rev(self, doc: str) -> tuple[str, str] | None:
        if doc not in self._doc_revs:
            budget = self._git_budget()
            started = time.monotonic()
            found = (
                gitutil.last_commit_of(self.config.root, doc, timeout=budget) if budget else None
            )
            self._clock(started)
            self._doc_revs[doc] = found
        return self._doc_revs[doc]

    # ----------------------------------------------------------------- paths
    def path(self, ref: str, doc: str) -> Verdict:
        here = posixpath.dirname(doc)
        tries = list(dict.fromkeys(
            p for p in (posixpath.normpath(ref.rstrip("/")),
                        posixpath.normpath(posixpath.join(here, ref.rstrip("/"))))
            if p != "." and not p.startswith("../") and p != ".."
        ))
        if not tries:
            return Verdict(UNKNOWN, "outside_the_repo")
        for rel in tries:
            if self._exists(rel):
                return Verdict(OK, "exists", {"path": rel})
        # A monorepo doc names paths from its subproject's root: a unique tracked ending is that.
        under = self._ending(tries[0], self._tracked_index())
        if len(under) == 1 and self._exists(under[0]):
            return Verdict(OK, "under_a_subproject", {"path": under[0]})
        if len(under) > 1:
            return Verdict(
                AMBIGUOUS, "several_paths_end_so", {"candidate_paths": under[:CANDIDATE_CAP]}
            )
        history, added = self.history(), self.added()
        if history is None or added is None:
            return Verdict(UNKNOWN, "no_git_history")
        for rel in tries:
            found = self._path_in_history(rel, history, added)
            if found is not None:
                return _path_replacement(found, ref, rel, here)
        for rel in self._ending(tries[0], self._added_index(added))[:CANDIDATE_CAP]:
            found = self._path_in_history(rel, history, added)
            if found is not None:
                return found
        return Verdict(NEVER_EXISTED, "no_branch_ever_held_it")

    def _tracked_index(self) -> Mapping[str, list[str]]:
        if self._tracked is None:
            self._tracked = _by_basename(gitutil.ls_files(self.config.root) or ())
        return self._tracked

    def _added_index(self, added: frozenset[str]) -> Mapping[str, list[str]]:
        if self._added_by_name is None:
            self._added_by_name = _by_basename(added)
        return self._added_by_name

    @staticmethod
    def _ending(rel: str, index: Mapping[str, list[str]]) -> list[str]:
        """The paths whose trailing segments are ``rel`` — a bare file name matches its name."""
        return sorted(
            p for p in index.get(rel.rsplit("/", 1)[-1], ()) if p == rel or p.endswith("/" + rel)
        )

    def _path_in_history(
        self, rel: str, history: gitutil.PathHistory, added: frozenset[str]
    ) -> Verdict | None:
        successor, hops = rel, 0
        while successor in history.renamed and hops < 50:
            successor, hops = history.renamed[successor], hops + 1
        if hops and self._exists(successor):
            return Verdict(MOVED, "git_rename", {"successor": successor})
        moved_dirs = self._moved_dirs(rel, history)
        if len(moved_dirs) == 1:
            return Verdict(MOVED, "git_rename", {"successor": moved_dirs[0]})
        if moved_dirs:
            # Its files went to several places: moved, and no one successor to patch to.
            return Verdict(MOVED, "git_rename_split", {"successors": moved_dirs[:CANDIDATE_CAP]})
        dirs = self._dir_index(history, added)
        gone = history.deleted.get(successor) or dirs.deleted.get(rel)
        if gone is not None:
            return Verdict(GONE, "deleted", {"last_seen_rev": gone[0][:12], "last_seen": gone[1]})
        if hops:
            sha, day = history.renamed_at.get(rel, ("", ""))
            return Verdict(GONE, "renamed_then_removed", {"last_seen_rev": sha[:12] or None,
                                                          "last_seen": day or None})
        if rel in added or rel in dirs.added:
            return Verdict(UNKNOWN, "only_on_another_branch")
        return None

    def _dir_index(self, history: gitutil.PathHistory, added: frozenset[str]) -> _DirIndex:
        if self._dirs is None:
            self._dirs = _DirIndex.build(history, added)
        return self._dirs

    def _moved_dirs(self, rel: str, history: gitutil.PathHistory) -> list[str]:
        added = self.added() or frozenset()
        targets = self._dir_index(history, added).renamed.get(rel, set())
        if None in targets:
            return []  # a file left the folder under another name: not a folder move
        return sorted(t for t in targets if t and self._exists(t))

    # ----------------------------------------------------------------- symbols
    def _matches(self, ref: str, last: str) -> list[Row]:
        # A doc writes `mod.Class.method`; the contract joins a member with MEMBER_SEPARATOR.
        cut = len(ref) - len(last)
        spellings = [ref]
        if cut > 0 and not ref[:cut].endswith(MEMBER_SEPARATOR):
            spellings.append(ref[:cut].rstrip(":\\./->") + MEMBER_SEPARATOR + last)
        rows = [
            row
            for spelling in spellings
            for name in dict.fromkeys((last, last.lstrip("$"), "$" + last.lstrip("$")))
            for row in self.store.nodes_by_qname_endswith(name, spelling, limit=50)
            if _ends_on_boundary(str(row["qualified_name"]), spelling)
        ]
        return list({str(row["id"]): row for row in rows}.values())

    def _external(self, ref: str) -> bool:
        """A dotted name whose first part names nothing indexed — `os.path` — is not this repo's."""
        head = re.match(r"[\w$#@]+[^\w$#@]+", ref)
        if head is None:
            return False
        prefix = head.group(0)
        seps = {c for c in ref if not _is_word(c)}
        return not self.store.qname_prefix_exists([prefix, *(c + prefix for c in seps)])

    def symbol(self, ref: str, kind: str, doc: str) -> Verdict | None:
        bare = ref.removesuffix("()")
        last = (_WORD_RUN.findall(bare) or [bare])[-1]
        if kind == NAME:
            rows = list(self.store.nodes_by_name(bare, limit=50))
        else:
            rows = self._matches(bare, last)
        if rows:
            return self._found(rows)
        if kind == NAME and not ref.endswith("()"):
            return None  # a word in backticks that names nothing indexed is not a reference
        if kind == SYMBOL:
            # Before the external test: `Repo.gone` starts on no qname, but `Repo` is indexed.
            container = bare[: len(bare) - len(last)].rstrip(":\\./->")
            owners = self._matches(container, (_WORD_RUN.findall(container) or [""])[-1]) if (
                container
            ) else []
            if owners:
                detail: dict[str, object] = {"container": str(owners[0]["qualified_name"])}
                seen = self._last_change(last, path=str(owners[0]["file_path"]))
                found = seen if isinstance(seen, tuple) else (None, None)
                detail.update(last_seen_rev=found[0][:12] if found[0] else None, last_seen=found[1])
                return Verdict(GONE, "missing_on_live_container", detail)
            if self._external(bare):
                self.skipped_external += 1  # `os.path`: counted, so a vanished package is seen
                return None
        moved = self._moved_by_body(bare, last, kind, doc)
        if moved is not None:
            return moved
        budget = self._git_budget()
        if budget is None:
            return Verdict(UNKNOWN, "history_budget_spent")
        started = time.monotonic()
        named = gitutil.files_naming(self.config.root, last, "HEAD", timeout=budget)
        self._clock(started)
        if named is None:
            return Verdict(UNKNOWN, "history_unanswered")
        mentioned = [f for f in named if self._is_code(f)]
        if mentioned:
            return Verdict(UNKNOWN, "mentioned_not_indexed", {"files_naming_it": len(mentioned)})
        seen = self._last_change(last, path=None)
        if seen is None:
            return Verdict(UNKNOWN, "history_unanswered")
        if seen is False:
            return Verdict(NEVER_EXISTED, "no_commit_ever_named_it")
        return Verdict(GONE, "removed", {"last_seen_rev": seen[0][:12], "last_seen": seen[1]})

    def _is_code(self, path: str) -> bool:
        """A file the index reads as code — a doc naming a symbol is not the symbol."""
        suffix = Path(path).suffix.lower()
        if self.shapes.suffixes:
            return suffix.lstrip(".") in self.shapes.suffixes
        return suffix not in DOC_SUFFIXES

    def _found(self, rows: Sequence[Row]) -> Verdict:
        qnames = list(dict.fromkeys(str(row["qualified_name"]) for row in rows))
        sites = [_site(row) for row in rows[:CANDIDATE_CAP]]
        if len(qnames) > 1:
            return Verdict(AMBIGUOUS, "several_symbols", {"candidates": sites})
        if len(rows) == 1:
            return Verdict(OK, "indexed", {"site": sites[0]})
        states = definition_states(rows, self.precedence, complete=len(rows) < 50)
        live = [s for s in states if s["state"] == DEFINITION_LIVE]
        if live:
            return Verdict(OK, "live_definition", {"site": _site(live[0])})
        return Verdict(AMBIGUOUS, "several_definitions", {"candidates": sites})

    def _last_change(
        self, needle: str, *, path: str | None
    ) -> tuple[str, str] | None | Literal[False]:
        budget = self._git_budget()
        if budget is None:
            return None
        started = time.monotonic()
        try:
            return gitutil.last_change_of(
                self.config.root, needle, every_ref=path is None, timeout=budget, path=path,
                suffixes=sorted(self.shapes.suffixes),
            )
        finally:
            self._clock(started)

    def _moved_by_body(self, ref: str, last: str, kind: str, doc: str) -> Verdict | None:
        """A unique same-name definition elsewhere, hashing as the body the doc saw (384)."""
        candidates = list(self.store.nodes_by_name(last, limit=3))
        if len({str(row["qualified_name"]) for row in candidates}) != 1:
            return None
        now = _body_hash(candidates[0])
        seen = self.doc_rev(doc)
        budget = self._git_budget()
        if now is None or seen is None or budget is None:
            return None
        rev = seen[0]
        started = time.monotonic()
        files = gitutil.files_naming(self.config.root, last, rev, timeout=budget) or ()
        suffixes = self.shapes.qualified_suffixes(ref) if kind == SYMBOL else None
        files = tuple(
            f for f in files
            if self._is_code(f) and (suffixes is None or Path(f).suffix.lower() in suffixes)
        )[:CANDIDATE_CAP]
        old = self._old_hashes(rev, files, ref if kind == SYMBOL else last)
        self._clock(started)
        if now in old:
            site = _site(candidates[0])
            detail: dict[str, object] = {"successor": site["qname"], "site": site}
            form = _symbol_form(str(site["qname"]), ref, last)
            if form is not None:
                detail["replacement"] = form
            return Verdict(MOVED, "body_hash", detail)
        if old:
            # Same name elsewhere, another body: moved and edited, or a namesake — never gone.
            return Verdict(AMBIGUOUS, "same_name_elsewhere_body_changed",
                           {"candidates": [_site(candidates[0])], "last_seen_rev": rev[:12],
                            "last_seen": seen[1]})
        return None

    def _old_hashes(self, rev: str, files: Sequence[str], ref: str) -> set[str]:
        from code_atlas.indexer import parse_files

        if not files:
            return set()
        with tempfile.TemporaryDirectory(prefix="code-atlas-refs-") as scratch:
            root = Path(scratch)
            for rel in files:
                text = gitutil.blob_at(self.config.root, rev, rel)
                if text is None:
                    continue
                try:
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    safe_write(root / rel, text, root=root)
                except (OSError, UnicodeError):
                    continue  # an old blob that is not text: its body stays unknown
            parsed = parse_files(dataclasses.replace(self.config, root=root), list(files))
        found: set[str] = set()
        for result in parsed.values():
            if result is None or not result[1].ok:
                continue
            for node in result[1].nodes:
                qname = str(node.get("qualified_name", ""))
                named = str(node.get("name")) == ref or _ends_on_boundary(qname, ref)
                extra = node.get("extra")
                hashed = extra.get("body_hash") if isinstance(extra, dict) else None
                if named and isinstance(hashed, str):
                    found.add(hashed)
        return found


def _listed(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _ends_on_boundary(qname: str, ref: str) -> bool:
    """``qname`` is ``ref`` or ends with it at a separator: `\\App\\Foo` for `App\\Foo`."""
    if qname == ref:
        return True
    return len(qname) > len(ref) and qname.endswith(ref) and not _is_word(qname[-len(ref) - 1])


def _is_word(ch: str) -> bool:
    return ch.isalnum() or ch in "_$#@"


def _site(row: Mapping[str, object] | Row) -> dict[str, object]:
    return {"qname": row["qualified_name"], "file": row["file_path"], "line": row["line_start"]}


def _body_hash(row: Row) -> str | None:
    import json

    raw = row.get("extra")
    try:
        extra = json.loads(raw) if isinstance(raw, str) and raw else {}
    except ValueError:
        return None
    value = extra.get("body_hash") if isinstance(extra, dict) else None
    return value if isinstance(value, str) else None


def _rows(
    config: Config, store: GraphStore, corpus: Corpus, resolver: Resolver
) -> Iterator[dict[str, object]]:
    seen: dict[tuple[str, str, str], tuple[str, Verdict | None]] = {}
    for doc, doc_class in corpus.files.items():
        try:
            text = read_text(config.root, config.root / doc, errors="replace")
        except (OSError, ValueError):
            yield {"file": doc, "line": 0, "class": doc_class, "context": "file",
                   "ref": doc, "ref_kind": PATH, "state": UNKNOWN, "reason": "unreadable_doc"}
            continue
        mentions, commands = extract(doc, doc_class, text)
        corpus.commands[doc_class] = corpus.commands.get(doc_class, 0) + commands
        lines_seen: set[tuple[int, str]] = set()
        for mention in mentions:
            cleaned = kind_of(mention.ref, mention.origin, resolver.shapes)
            if cleaned is None:
                continue
            ref, kind = cleaned
            if (mention.line, ref) in lines_seen:
                continue
            key = (ref, kind, posixpath.dirname(doc) if kind == PATH else doc)
            if key not in seen:
                seen[key] = _resolve(resolver, ref, kind, doc)
            kind, verdict = seen[key]
            if verdict is None:
                continue
            # A prose word is a reference only on an exact hit, never a stale guess.
            if mention.origin == PROSE and verdict.state != OK:
                continue
            if mention.origin == FENCE and kind == NAME:
                continue
            lines_seen.add((mention.line, ref))
            yield {
                "file": doc, "line": mention.line, "class": doc_class, "context": mention.context,
                "origin": mention.origin, "ref": ref, "ref_kind": kind,
                "state": verdict.state, "reason": verdict.reason, **verdict.detail,
            }


def _resolve(resolver: Resolver, ref: str, kind: str, doc: str) -> tuple[str, Verdict | None]:
    """One reference's kind and verdict. `threading.Lock` reads like a file and never was one:
    a slash-less path no branch held, in a symbol's shape, is asked again as a symbol."""
    if kind != PATH:
        return kind, resolver.symbol(ref, kind, doc)
    verdict = resolver.path(ref, doc)
    if verdict.state == NEVER_EXISTED and "/" not in ref:
        if resolver.shapes.qualified_suffixes(ref) is not None:
            return SYMBOL, resolver.symbol(ref, SYMBOL, doc)
    return kind, verdict


@dataclass(slots=True)
class Scan:
    """Every row the corpus yields, before any filter or cap — what patches and counts read."""

    corpus: Corpus
    matched: int
    resolver: Resolver
    rows: list[dict[str, object]]


def scan(
    config: Config,
    store: GraphStore,
    *,
    globs: Sequence[str] = (),
    classes: Sequence[str] = (),
    budget_s: float = HISTORY_BUDGET_S,
) -> Scan:
    """Read the corpus and resolve every reference once, sorted by class, state, file, line."""
    corpus = collect(config, globs)
    matched = len(corpus.files)
    if classes:
        corpus.files = {p: c for p, c in corpus.files.items() if c in classes}
    resolver = Resolver(config, store, Shapes.from_store(store), budget_s)
    rows = list(_rows(config, store, corpus, resolver))
    order = {name: n for n, name in enumerate(CLASSES)}
    rank = {name: n for n, name in enumerate(STATES)}
    rows.sort(key=lambda r: (order[str(r["class"])], rank[str(r["state"])], r["file"], r["line"]))
    for row in rows:
        _annotate(row)
    return Scan(corpus, matched, resolver, rows)


def verify_refs(
    config: Config,
    store: GraphStore,
    *,
    globs: Sequence[str] = (),
    classes: Sequence[str] = (),
    states: Sequence[str] = (),
    limit: int = DEFAULT_LIMIT,
) -> dict[str, object]:
    """Every reference the corpus makes, one state each; summaries count every row."""
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be 1..{MAX_LIMIT}, got {limit}")
    unknown = [s for s in states if s not in STATES]
    if unknown:
        raise ValueError(f"unknown state {unknown[0]!r}; one of {', '.join(STATES)}")
    return summarize(scan(config, store, globs=globs, classes=classes), states=states, limit=limit)


def summarize(
    found: Scan, *, states: Sequence[str] = (), limit: int = DEFAULT_LIMIT
) -> dict[str, object]:
    """The payload: counts over every row, then the rows a state filter keeps, capped."""
    corpus, rows = found.corpus, found.rows
    by_class: dict[str, dict[str, int]] = {}
    by_file: dict[str, dict[str, int]] = {}
    ready: dict[str, int] = {}
    for row in rows:
        for bucket, key in ((by_class, str(row["class"])), (by_file, str(row["file"]))):
            counts = bucket.setdefault(key, {state: 0 for state in STATES})
            counts[str(row["state"])] += 1
        if row.get("patch_ready"):
            ready[str(row["class"])] = ready.get(str(row["class"]), 0) + 1
    kept = [row for row in rows if not states or row["state"] in states]
    if not corpus.files:
        reason = "class_filter_left_no_file" if found.matched else "no_file_matched"
    elif not found.resolver.shapes.qualified:
        # No build stamped a symbol shape: every symbol a doc names went unread, never resolved.
        reason = "symbols_unchecked_no_index"
    elif not rows:
        reason = "no_references"
    elif not kept:
        reason = "state_filter_left_no_row"
    else:
        reason = "ok"
    return {
        "reason": reason,
        "files_read": len(corpus.files),
        "total_count": len(kept),
        "returned": min(limit, len(kept)),
        "truncated": len(kept) > limit,
        "limit": limit,
        "states": list(states),
        "by_class": by_class,
        "patch_ready": ready,
        "commands": corpus.commands,
        "files": [
            {"file": path, "class": corpus.files[path], **counts}
            for path, counts in sorted(by_file.items())
        ],
        "history_budget_spent": found.resolver.budget_spent,
        "skipped_as_external": found.resolver.skipped_external,
        "rows": kept[:limit],
        "corpus_globs": {name: list(globs) for name, globs in corpus.globs.items()},
        "untrusted_fields": list(UNTRUSTED),
    }


# The cheapest correction a row that is not ok carries when no patch can (439).
HINTS: Mapping[str, str] = {
    GONE: "remove the reference, or name what replaced it",
    NEVER_EXISTED: "no branch ever held it: correct the spelling or remove it",
    AMBIGUOUS: "name one of the candidates in full",
    MOVED: "several successors: name the one meant",
}


def _annotate(row: dict[str, object]) -> None:
    """``patch_ready`` on a moved row with one successor and an in-place form; a hint otherwise.
    An archive row is never patched: it records what was true then."""
    state = row["state"]
    if state == MOVED and "replacement" in row and row["class"] != ARCHIVE:
        row["patch_ready"] = True
    elif state in HINTS and not (state == MOVED and "replacement" in row):
        row["hint"] = (
            HINTS[str(state)]
            if state != MOVED or "successors" in row
            else ("no in-place form: replace it by hand with the successor")
        )


def _path_replacement(found: Verdict, ref: str, rel: str, here: str) -> Verdict:
    """A moved path's successor written the way the doc wrote the reference: from the repo root,
    or relative to the doc's folder; a trailing ``/`` kept."""
    successor = found.detail.get("successor")
    if found.state != MOVED or not isinstance(successor, str):
        return found
    rooted = posixpath.normpath(ref.rstrip("/"))
    form = successor if rel == rooted else posixpath.relpath(successor, here or ".")
    if ref.endswith("/"):
        form += "/"
    return dataclasses.replace(found, detail={**found.detail, "replacement": form})


def _symbol_form(qname: str, ref: str, last: str) -> str | None:
    """The successor's qname in the doc's spelling: its member separator and leading backslash."""
    form = qname if ref.startswith("\\") else qname.lstrip("\\")
    cut = len(ref) - len(last)
    sep = ref[:cut][len(ref[:cut].rstrip(":\\./->")) :] if cut > 0 else ""
    member = MEMBER_SEPARATOR + last
    if sep and sep != MEMBER_SEPARATOR and form.endswith(member):
        form = form[: -len(member)] + sep + last
    return form if form.endswith(last) and form != ref else None


# ----------------------------------------------------------------- patches (439)
_BEFORE_WORD = re.compile(r"[\w/\\.$-]")
_AFTER_WORD = re.compile(r"[\w/\\]|\.\w")
PATCH_CONTEXT = 3


@dataclass(slots=True)
class Patch:
    """One file's unified diff and the rows it carries; rows it could not place are skipped."""

    doc_class: str
    file: str
    diff: str
    rows: int


def _bounded(line: str, ref: str) -> list[int]:
    """Where ``ref`` stands whole on a line: not inside a longer path or name."""
    found, start = [], line.find(ref)
    while start != -1:
        before = line[start - 1] if start else ""
        after = line[start + len(ref) : start + len(ref) + 2]
        if not (before and _BEFORE_WORD.match(before)) and not _AFTER_WORD.match(after):
            found.append(start)
        start = line.find(ref, start + 1)
    return found


def _replaced(line: str, ref: str, form: str) -> str | None:
    spots = _bounded(line, ref)
    for start in reversed(spots):
        line = line[:start] + form + line[start + len(ref) :]
    return line if spots else None


def patches(config: Config, rows: Sequence[Mapping[str, object]]) -> tuple[list[Patch], int]:
    """Unified diffs, per priority class then file, that swap each patch-ready reference for its
    successor and change nothing else; and how many rows no longer stand on their line."""
    by_file: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        if row.get("patch_ready"):
            by_file.setdefault(str(row["file"]), []).append(row)
    order = {name: n for n, name in enumerate(CLASSES)}
    out: list[Patch] = []
    skipped = 0
    ranked = sorted(by_file.items(), key=lambda kv: (order[str(kv[1][0]["class"])], kv[0]))
    for doc, edits in ranked:
        try:
            text = read_text(config.root, config.root / doc, errors="strict")
        except (OSError, ValueError):
            skipped += len(edits)
            continue
        old = text.splitlines(keepends=True)
        new = list(old)
        placed = 0
        for edit in edits:
            index = int(str(edit["line"])) - 1
            line = (
                _replaced(new[index], str(edit["ref"]), str(edit["replacement"]))
                if (0 <= index < len(new))
                else None
            )
            if line is None:
                skipped += 1
                continue
            new[index] = line
            placed += 1
        if placed:
            out.append(Patch(str(edits[0]["class"]), doc, unified_diff(doc, old, new), placed))
    return out, skipped


def unified_diff(path: str, old: Sequence[str], new: Sequence[str]) -> str:
    """A ``git apply``-able diff of two same-length line lists (only lines change, never count)."""
    changed = [n for n, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    groups: list[list[int]] = []
    for n in changed:
        if groups and n - groups[-1][-1] <= 2 * PATCH_CONTEXT:
            groups[-1].append(n)
        else:
            groups.append([n])
    out = [f"diff --git a/{path} b/{path}\n", f"--- a/{path}\n", f"+++ b/{path}\n"]
    for group in groups:
        lo = max(0, group[0] - PATCH_CONTEXT)
        hi = min(len(old), group[-1] + PATCH_CONTEXT + 1)
        out.append(f"@@ -{lo + 1},{hi - lo} +{lo + 1},{hi - lo} @@\n")
        for n in range(lo, hi):
            if n in group:
                out += [_diff_line("-", old[n]), _diff_line("+", new[n])]
            else:
                out.append(_diff_line(" ", old[n]))
    return "".join(out)


def _diff_line(mark: str, line: str) -> str:
    if line.endswith("\n"):
        return mark + line
    return f"{mark}{line}\n\\ No newline at end of file\n"


# ----------------------------------------------------------------- session line (439)
# A session start cannot wait on the run's full history budget: past this, rows are unknown.
SESSION_BUDGET_S = 3.0
STALE: tuple[str, ...] = (MOVED, GONE, NEVER_EXISTED, AMBIGUOUS)


def session_line(config: Config, store: GraphStore) -> str | None:
    """One count-only line, the instruction class first; ``None`` when every reference resolves.
    Archive files are not read — they never count."""
    found = scan(config, store, classes=COUNTED_CLASSES, budget_s=SESSION_BUDGET_S)
    stale = {name: 0 for name in COUNTED_CLASSES}
    unknown = ready = 0
    for row in found.rows:
        name = str(row["class"])
        if row["state"] in STALE:
            stale[name] += 1
        elif row["state"] == UNKNOWN:
            unknown += 1
        if name == INSTRUCTION and row.get("patch_ready"):
            ready += 1
    others = stale[MEMORY] + stale[REFERENCE]
    if not (stale[INSTRUCTION] or others or unknown):
        return None
    line = f"code-atlas: {stale[INSTRUCTION]} refs in instruction files no longer resolve"
    if ready:
        line += f" ({ready} moved — patch ready)"
    line += f"; {others} in other docs"
    if unknown:
        line += f"; {unknown} unchecked (unknown, not ok)"
    return line + " — `code-atlas query --verify-refs --format md`."


# Doc-derived and repo-derived text in the payload: data, never instructions (429).
UNTRUSTED: tuple[str, ...] = (
    "rows[].ref",
    "rows[].file",
    "rows[].path",
    "rows[].successor",
    "rows[].successors",
    "rows[].replacement",
    "rows[].container",
    "rows[].site.*",
    "rows[].candidate_paths",
    "rows[].candidates[].*",
    "files[].file",
)


def markdown(answer: Mapping[str, object]) -> str:
    """The same answer as a table a human reads; reference strings only, never prose."""
    head = [
        f"# verify_refs — {answer['total_count']} references in {answer['files_read']} files",
        "",
        "| class | " + " | ".join(STATES) + " |",
        "|---|" + "---|" * len(STATES),
    ]
    by_class = answer.get("by_class") or {}
    assert isinstance(by_class, dict)
    for name in CLASSES:
        if name in by_class:
            head.append(f"| {name} | " + " | ".join(str(by_class[name][s]) for s in STATES) + " |")
    head += ["", "| file:line | class | state | reference | successor / reason |"]
    head.append("|---|---|---|---|---|")
    rows = answer.get("rows") or []
    assert isinstance(rows, list)
    for row in rows:
        if row["state"] == OK:
            continue
        hint = row.get("successor") or row.get("hint") or row.get("reason")
        site = row.get("site")
        if row["state"] == MOVED and isinstance(site, dict):
            hint = f"{hint} ({site.get('file')}:{site.get('line')})"
        cells = [f"{row['file']}:{row['line']}", row["class"], row["state"], f"`{row['ref']}`"]
        cells.append(hint)
        head.append("| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |")
    if answer.get("truncated"):
        head += ["", f"_truncated at {answer['limit']} of {answer['total_count']} rows_"]
    return "\n".join(head) + "\n"
