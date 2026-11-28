"""Which references in agent-facing docs still resolve against the code (438).

An agent reads ``CLAUDE.md``, skills and docs as true, and nothing checks them. This module reads a
corpus of markdown files, pulls out the references they make — file paths, symbols written whole,
bare names in code spans — and gives each exactly one state with a reason: ``ok``, ``moved`` (a
successor), ``gone``, ``never_existed``, ``ambiguous`` or ``unknown``. An unknown is never folded
into ``ok`` (R5.6). Language-free: what a symbol looks like comes from each adapter's ``qualified``
shape, stored at build (R1.1). Read-only: git is read through ``gitutil``; nothing is written.

Each row is ``strong`` or ``weak``; the surfaces count the *actionable* set — a ``moved`` or
``gone`` strong row outside the archive (443). Bare names stay in the full export only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import posixpath
import re
import tempfile
import time
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from code_atlas import gitutil
from code_atlas.config import Config, ConfigError
from code_atlas.containment import read_bytes, read_text, resolves_inside, safe_write
from code_atlas.contract import (
    CALLABLE_KINDS,
    COLUMN_KIND,
    HIDDEN_MODIFIERS,
    MEMBER_SEPARATOR,
    QUALIFIED_SHAPE,
    TOP_LEVEL_KINDS,
    TYPE_KINDS,
    VALUE_KINDS,
    VISIBILITY_MODIFIERS,
    join_qname,
    split_qname,
)
from code_atlas.resolver import ancestry, declared_class
from code_atlas.store import INDEXED_SUFFIXES_KEY, LAST_COMMIT_KEY, GraphStore, Row
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
    MEMORY: (),  # unset = the host's project memory folder (`memory_dir`), never a repo choice
    REFERENCE: ("docs/**", "wiki/**", "*.wiki/**"),
    ARCHIVE: (),
}
DOC_SUFFIXES = frozenset({".md", ".mdc", ".markdown"})

OK, MOVED, GONE, NEVER_EXISTED, AMBIGUOUS, UNKNOWN = (
    "ok", "moved", "gone", "never_existed", "ambiguous", "unknown"
)
STATES: tuple[str, ...] = (MOVED, GONE, NEVER_EXISTED, AMBIGUOUS, UNKNOWN, OK)
# A marked reference whose target is absent; counted only where markers are configured (460).
PLANNED = "planned"
PLANNED_BUT_EXISTS = "planned_but_exists"
ALL_STATES: tuple[str, ...] = (*STATES[:-1], PLANNED, OK)
PATH, SYMBOL, NAME = "path", "symbol", "name"
CODE_SPAN, FENCE, LINK, PROSE = "code_span", "fence", "link", "prose"

DEFAULT_LIMIT = 200
# The default answer: an actionable summary and this many actionable rows (443).
DEFAULT_ROWS = 20
STRONG, WEAK = "strong", "weak"
STRENGTHS: tuple[str, ...] = (STRONG, WEAK)
ACTIONABLE_STATES: tuple[str, ...] = ("moved", "gone")
# A path the tree or git history answered is a real path, however the doc wrote it.
_PATH_FOUND = frozenset(
    {"exists", "under_a_subproject", "git_rename", "git_rename_split", "deleted",
     "renamed_then_removed", "exists_in_memory", "missing_from_memory"}
)
# Memory files live in the host's per-project folder, outside the repo; rows name them so (443).
MEMORY_PREFIX = "<agent-memory>/"
MAX_REF_CHARS = 512
MAX_LIMIT = 1000
CANDIDATE_CAP = 5
# Wall-clock git may spend on history questions per run; past it a row is `unknown`, counted.
HISTORY_BUDGET_S = 12.0
GIT_CALL_CAP_S = 5.0
# A deliberate full run gets more: the export a baseline is diffed against, and the summary a build
# stores in the background. Rows past either are still `unknown`, counted (443).
EXPORT_BUDGET_S = 1800.0
SUMMARY_BUDGET_S = 120.0
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
# A container of these kinds holds a value, so a member written after it is a member of its type.
_TYPED_KINDS = frozenset((*VALUE_KINDS, *CALLABLE_KINDS))
_MAX_SEGMENTS = 8
# A row whose container was matched only by a member's name (457).
MEMBER_NAME = "member_name"


@dataclass(frozen=True, slots=True)
class Mention:
    """One reference string as a doc wrote it, and where — never the prose around it (429)."""

    file: str
    line: int
    doc_class: str
    context: str  # the line's shape: list_item · table_cell · heading · quote · prose · fence
    origin: str  # code_span · fence · link · prose
    ref: str
    marked: bool = False  # the line carries a configured planned marker (460)


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
    check_globs(only, "globs")
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
        if not in_repo(path):
            continue  # a repo path may never claim the host-memory namespace (SEC-IN-03)
        found = classify(path, globs) or (REFERENCE if narrow else None)
        if found is not None:
            corpus.files[path] = found
    folder = memory_dir(config) if config.refs_memory is None and not narrow else None
    for name in _memory_files(folder) if folder is not None else ():
        corpus.files[MEMORY_PREFIX + name] = MEMORY
    return corpus


def memory_dir(config: Config) -> Path:
    """Claude Code's memory folder for this repo, chosen by the host, never the repo (SEC-IN-03)."""
    home = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(config.root.resolve()))
    return Path(home) / "projects" / slug / "memory"


def _memory_files(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.suffix.lower() in DOC_SUFFIXES and p.is_file() and resolves_inside(folder, p)
    )


def in_repo(doc: str) -> bool:
    """Whether a corpus file is the repo's own (patchable, with git history) or host memory."""
    return not doc.startswith(MEMORY_PREFIX)


def _doc_text(config: Config, doc: str) -> str:
    if in_repo(doc):
        return read_text(config.root, config.root / doc, errors="replace")
    folder = memory_dir(config)
    return read_text(folder, folder / doc.removeprefix(MEMORY_PREFIX), errors="replace")


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


def extract(
    path: str, doc_class: str, text: str, markers: Sequence[str] = ()
) -> tuple[list[Mention], int]:
    """Every candidate reference in a markdown text, and how many command lines it holds; a mention
    on a line carrying a configured planned marker is `marked` (460)."""
    mentions: list[Mention] = []
    commands = 0
    fence: tuple[str, str] | None = None
    # Lines end at "\n" only, as git counts them: U+2028 or a form feed is not a line break.
    for number, line in enumerate(text.split("\n"), start=1):
        marked = any(k in line for k in markers)
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
                mentions.append(Mention(path, number, doc_class, "fence", FENCE, word, marked))
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
            mentions.append(Mention(path, number, doc_class, context, CODE_SPAN, body, marked))
        rest = _SPAN.sub(" ", rest)
        for link in _LINK.finditer(rest):
            mentions.append(Mention(path, number, doc_class, context, LINK, link.group(1), marked))
        rest = _LINK.sub(" ", rest)
        for word in rest.split():
            mentions.append(Mention(path, number, doc_class, context, PROSE, word, marked))
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
        self._parents: Mapping[str, tuple[str, ...]] | None = None
        self._types: dict[str, list[str]] = {}
        self._member_heads: dict[str, bool] = {}
        self._suffixes: frozenset[str] | None = None

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
        if not in_repo(doc):
            return None  # host memory has no git history
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
    def _tries(self, ref: str, doc: str) -> list[str]:
        here = posixpath.dirname(doc) if in_repo(doc) else ""
        return list(dict.fromkeys(
            p for p in (posixpath.normpath(ref.rstrip("/")),
                        posixpath.normpath(posixpath.join(here, ref.rstrip("/"))))
            if p != "." and not p.startswith("../") and p != ".."
        ))

    def _in_tree(self, ref: str, doc: str) -> Verdict | None:
        """What the checkout alone answers — no git history; None when it does not hold the path."""
        tries = self._tries(ref, doc)
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
        return None

    def path(self, ref: str, doc: str) -> Verdict:
        found = self._in_tree(ref, doc)
        if found is not None:
            return found
        tries = self._tries(ref, doc)
        here = posixpath.dirname(doc) if in_repo(doc) else ""
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

    def names_a_file(self, ref: str) -> bool:
        """``ref`` is one slash-less name whose last segment is, case kept, a file suffix the index,
        the doc set or a tracked file carries — so `threading.Lock` is not one (458)."""
        name, dot, suffix = ref.rpartition(".")
        if "/" in ref or not dot or not name or not suffix:
            return False
        if self._suffixes is None:
            # A suffix only the tree knows counts once two files carry it: `Dockerfile.dev` alone
            # must not turn `Settings.dev` into a path.
            seen = Counter(
                n.rpartition(".")[2] for n in self._tracked_index() if "." in n.strip(".")
            )
            tracked = {suffix for suffix, files in seen.items() if files > 1 and len(suffix) > 1}
            self._suffixes = frozenset(self.shapes.suffixes | _DOC_FILE_SUFFIXES | tracked)
        return suffix in self._suffixes

    def memory_link(self, ref: str, doc: str) -> Verdict:
        """A link in a memory file, read in that file's folder of the memory dir, then by the repo's
        rules; in neither is `gone` (the note was deleted). One leaving the folder is repo-only."""
        folder = memory_dir(self.config)
        here = posixpath.dirname(doc.removeprefix(MEMORY_PREFIX))
        rel = posixpath.normpath(posixpath.join(here, ref.rstrip("/")))
        if posixpath.isabs(rel) or rel in (".", "..") or rel.startswith("../"):
            return self.path(ref, doc)  # outside the memory folder (SEC-IN-03)
        target = folder / rel
        if resolves_inside(folder, target) and target.exists():
            return Verdict(OK, "exists_in_memory", {"path": MEMORY_PREFIX + rel})
        # A memory file has no git history: the checkout answers, never a rename lookup.
        found = self._in_tree(ref, doc)
        return found or Verdict(GONE, "missing_from_memory", {"path": MEMORY_PREFIX + rel})

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
            return Verdict(GONE, "deleted", {"last_seen_rev": gone[0][:12], "last_seen": gone[1],
                                             "nearest_existing": self._nearest(rel)})
        if hops:
            sha, day = history.renamed_at.get(rel, ("", ""))
            return Verdict(GONE, "renamed_then_removed", {"last_seen_rev": sha[:12] or None,
                                                          "last_seen": day or None})
        if rel in added or rel in dirs.added:
            return Verdict(UNKNOWN, "only_on_another_branch")
        return None

    def _nearest(self, rel: str) -> str | None:
        """The deepest folder of a removed path that still exists: where its replacement may sit."""
        return next((parent for parent in _parents(rel) if self._exists(parent)), None)

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
            found = self._found(rows)
            if found.state == OK and all(str(row["kind"]) == COLUMN_KIND for row in rows):
                return dataclasses.replace(found, reason="table_column")  # `jobs.series_id` (457)
            return found
        if kind == NAME and not ref.endswith("()"):
            return None  # a word in backticks that names nothing indexed is not a reference
        if kind == SYMBOL:
            # Before the external test: `Repo.gone` starts on no qname, but `Repo` is indexed.
            container = bare[: len(bare) - len(last)].rstrip(":\\./->")
            owners = self._matches(container, (_WORD_RUN.findall(container) or [""])[-1]) if (
                container
            ) else []
            walked: Row | Verdict | None = None
            if owners:
                walked = self._one_owner(owners)
            elif container:
                walked = self._walk(container)
            if isinstance(walked, Verdict):
                return self._by_head(bare, walked)
            if walked is not None:
                return self._by_head(bare, self._member(bare, last, kind, doc, walked))
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

    def _member(self, bare: str, last: str, kind: str, doc: str, owner: Row) -> Verdict:
        """A member its live container does not declare: inherited is ok, a body found elsewhere
        is moved, and gone needs git to show it left the container's file (443). A value or a
        callable is first replaced by its declared type (456)."""
        if str(owner["kind"]) in _TYPED_KINDS:
            typed = self._through_type(owner, last)
            if isinstance(typed, Verdict):
                return typed
            owner = typed
        container = str(owner["qualified_name"])
        found = self._declared_on(container, last, own=False)
        if found is not None:
            return Verdict(OK, "inherited", {"site": _site(found)})
        moved = self._moved_by_body(bare, last, kind, doc)
        if moved is not None and moved.state == MOVED:
            return moved
        detail: dict[str, object] = {"container": container}
        seen = self._last_change(last, path=str(owner["file_path"]))
        if seen is None:
            return Verdict(UNKNOWN, "history_budget_spent", detail)
        if seen is False:
            # Never in its file: magic, an unindexed parent, or a typo — not a removal.
            return Verdict(UNKNOWN, "not_declared_on_container", detail)
        detail.update(last_seen_rev=seen[0][:12], last_seen=seen[1])
        return Verdict(GONE, "missing_on_live_container", detail)

    def _declared_on(self, container: str, last: str, *, own: bool) -> Row | None:
        """``last`` declared on ``container`` (when ``own``) or the nearest ancestor."""
        for ancestor in self._ancestry(container)[0 if own else 1:]:
            spelling = ancestor + MEMBER_SEPARATOR + last
            for row in self.store.nodes_by_qname_endswith(last, spelling, limit=5):
                if str(row["qualified_name"]) in {spelling, "\\" + spelling.lstrip("\\")}:
                    return row
        return None

    def _type_of(self, owner: Row) -> list[str]:
        """The class-like types a value or callable is declared as: ``extra.type`` read as the
        resolver reads it, else the types its annotation references. Two or more is no answer."""
        qname = str(owner["qualified_name"])
        if qname not in self._types:
            found: list[str] = []
            container, member = split_qname(qname)
            if container is not None:
                lineage = self._ancestry(container)
                declared = self.store.declared_types([join_qname(a, member) for a in lineage])
                named = declared_class(container, member, lineage, declared)
                rows = self.store.nodes_by_qualified_names([named], limit=1) if named else {}
                if named and any(str(r["kind"]) in TYPE_KINDS for r in rows.get(named, [])):
                    found = [named]
            if not found and _references_name_the_type(owner):
                found = self.store.referenced_types(qname, TYPE_KINDS, limit=5)
            self._types[qname] = found
        return self._types[qname]

    def _through_type(self, owner: Row, last: str) -> Verdict | Row:
        """``last`` on the type ``owner`` holds: ok with the site, the type node to keep asking, or
        unknown when the type is absent or not one class (R5.6) — never gone."""
        detail: dict[str, object] = {"container": str(owner["qualified_name"])}
        types = self._type_of(owner)
        if len(types) != 1:
            if types:
                return Verdict(UNKNOWN, "several_container_types", {**detail, "types": types})
            # A function has no members: the word after it names something else (457).
            callable_ = str(owner["kind"]) in CALLABLE_KINDS
            return Verdict(UNKNOWN, "container_is_callable" if callable_ else "untyped_container",
                           detail)
        found = self._declared_on(types[0], last, own=True)
        if found is not None:
            return Verdict(OK, "via_declared_type", {"site": _site(found), "type": types[0]})
        rows = self.store.nodes_by_qualified_names(types, limit=1).get(types[0], [])
        return rows[0] if rows else Verdict(UNKNOWN, "untyped_container", detail)

    def _by_head(self, bare: str, verdict: Verdict) -> Verdict:
        """Marked when the doc's first word is lowercase and matches only values or callables by
        their last segment — `run`, `jobs` in prose: a weak row whatever its state (457)."""
        head = (_WORD_RUN.findall(bare) or [""])[0]
        if not head[:1].islower():
            return verdict
        if head not in self._member_heads:
            rows = self._matches(head, head)
            # A package or class match keeps the row strong: only values and callables mark it.
            self._member_heads[head] = bool(rows) and all(
                str(r["kind"]) in _TYPED_KINDS for r in rows
            )
        if self._member_heads[head]:
            marked = {**verdict.detail, "matched_by": MEMBER_NAME}
            return dataclasses.replace(verdict, detail=marked)
        return verdict

    def _one_owner(self, rows: Sequence[Row]) -> Row | Verdict:
        """The first match, unless the typed matches hold different types: no answer (R5.6)."""
        typed = [row for row in rows if str(row["kind"]) in _TYPED_KINDS]
        if typed and str(rows[0]["kind"]) in _TYPED_KINDS:
            types = sorted({found for row in typed for found in self._type_of(row)})
            if len(types) > 1:
                return Verdict(UNKNOWN, "several_container_types",
                               {"container": str(rows[0]["qualified_name"]), "types": types})
        return rows[0]

    def _walk(self, container: str, depth: int = 0) -> Row | Verdict | None:
        """The node a dotted container no qname names (`a.b.c`): its head's member, read on the
        head's type segment by segment; unknown at the first untyped one, None when it breaks."""
        word = (_WORD_RUN.findall(container) or [""])[-1]
        rows = self._matches(container, word) if depth else []
        if rows:
            return self._one_owner(rows)
        head = container[: len(container) - len(word)].rstrip(":\\./->")
        if not head or not word or depth >= _MAX_SEGMENTS:
            return None
        parent = self._walk(head, depth + 1)
        if parent is None or isinstance(parent, Verdict):
            return parent
        if str(parent["kind"]) not in _TYPED_KINDS:
            return self._declared_on(str(parent["qualified_name"]), word, own=True)
        typed = self._through_type(parent, word)
        if isinstance(typed, Verdict) and typed.state == OK:
            site = typed.detail["site"]
            if not isinstance(site, dict):
                return None
            hit = self.store.nodes_by_qualified_names([str(site["qname"])], limit=1)
            return next(iter(hit.get(str(site["qname"]), [])), None)
        return typed if isinstance(typed, Verdict) else None

    def _ancestry(self, container: str) -> list[str]:
        if self._parents is None:
            self._parents = self.store.hierarchy_parents()
        return ancestry(container, self._parents)

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


def _references_name_the_type(owner: Row) -> bool:
    """A value's annotation edges name only its type; a callable's name its parameters' and
    decorators' too, so they answer only for one that declares a return and takes nothing."""
    if str(owner["kind"]) in VALUE_KINDS:
        return True
    return bool(_extra(owner).get("type")) and not _listed(_json(owner.get("params")))


def _json(raw: object) -> object:
    try:
        return json.loads(raw) if isinstance(raw, str) and raw else raw
    except ValueError:
        return None


def _extra(row: Mapping[str, object] | Row) -> dict[str, object]:
    found = _json(row.get("extra"))
    return found if isinstance(found, dict) else {}


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
    seen: dict[tuple[str, ...], tuple[str, Verdict | None]] = {}
    rank = {name: n for n, name in enumerate(CLASSES)}
    # Instruction files first: the shared git budget is spent where a stale line costs most (443).
    ordered = sorted(corpus.files.items(), key=lambda item: (rank[item[1]], item[0]))
    for doc, doc_class in ordered:
        try:
            text = _doc_text(config, doc)
        except (OSError, ValueError):
            yield {"file": doc, "line": 0, "class": doc_class, "context": "file",
                   "ref": doc, "ref_kind": PATH, "state": UNKNOWN, "reason": "unreadable_doc"}
            continue
        mentions, commands = extract(doc, doc_class, text, config.refs_planned_markers or ())
        corpus.commands[doc_class] = corpus.commands.get(doc_class, 0) + commands
        lines_seen: set[tuple[int, str]] = set()
        for mention in mentions:
            cleaned = kind_of(mention.ref, mention.origin, resolver.shapes)
            if cleaned is None:
                continue
            ref, kind = cleaned
            if (mention.line, ref) in lines_seen:
                continue
            # A link in host memory names a note beside it first (459).
            memory_link = kind == PATH and mention.origin == LINK and not in_repo(doc)
            key = (ref, kind, posixpath.dirname(doc) if kind == PATH else doc, str(memory_link))
            if key not in seen:
                seen[key] = (
                    (PATH, resolver.memory_link(ref, doc)) if memory_link
                    else _resolve(resolver, ref, kind, doc)
                )
            kind, verdict = seen[key]
            if verdict is None:
                continue
            # A prose word is a reference only on an exact hit, never a stale guess.
            if mention.origin == PROSE and verdict.state != OK:
                continue
            if mention.origin == FENCE and kind == NAME:
                continue
            lines_seen.add((mention.line, ref))
            if mention.marked:
                verdict = _planned(verdict)
            yield {
                "file": doc, "line": mention.line, "class": doc_class, "context": mention.context,
                "origin": mention.origin, "ref": ref, "ref_kind": kind,
                "state": verdict.state, "reason": verdict.reason, **verdict.detail,
            }


def _planned(verdict: Verdict) -> Verdict:
    """A marked reference: absent is `planned`, present is a marker to drop, and an unsettled or
    moved one keeps its own state (460)."""
    if verdict.state == OK:
        return dataclasses.replace(verdict, reason=PLANNED_BUT_EXISTS)
    if verdict.state in (NEVER_EXISTED, GONE):
        return dataclasses.replace(verdict, state=PLANNED)
    return verdict


def _resolve(resolver: Resolver, ref: str, kind: str, doc: str) -> tuple[str, Verdict | None]:
    """One reference's kind and verdict: a slash-less path no branch held, in a symbol's shape, is
    asked again as a symbol (`threading.Lock`); one ending in a file suffix (`atoms.json`) stays a
    path unless that symbol is `ok` or external (458)."""
    file_name = resolver.names_a_file(ref)
    if kind != PATH and not file_name:
        return kind, resolver.symbol(ref, kind, doc)
    verdict = resolver.path(ref, doc)
    if verdict.state == NEVER_EXISTED and "/" not in ref:
        if resolver.shapes.qualified_suffixes(ref) is not None:
            found = resolver.symbol(ref, SYMBOL, doc)
            if not file_name or found is None or found.state == OK:
                return SYMBOL, found
    return PATH, verdict


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
    rank = {name: n for n, name in enumerate(ALL_STATES)}
    rows.sort(key=lambda r: (order[str(r["class"])], rank[str(r["state"])], r["file"], r["line"]))
    for row in rows:
        row["strength"] = strength(row)
        row["actionable"] = is_actionable(row)
        _annotate(row)
    return Scan(corpus, matched, resolver, rows)


def strength(row: Mapping[str, object]) -> str:
    """`strong`: a path git or the tree knows, a path with a folder and a suffix written as code, or
    an adapter-shaped symbol written as code. Everything else — bare names, prose — is `weak`."""
    kind, origin, ref = row.get("ref_kind"), row.get("origin"), str(row.get("ref", ""))
    if kind == PATH:
        if row.get("reason") in _PATH_FOUND:
            return STRONG
        last = ref.rstrip("/").rsplit("/", 1)[-1]
        anchored = "/" in ref.rstrip("/") and "." in last.strip(".")
        return STRONG if anchored and origin in (CODE_SPAN, FENCE, LINK) else WEAK
    if row.get("matched_by") == MEMBER_NAME:
        return WEAK
    return STRONG if kind == SYMBOL and origin in (CODE_SPAN, FENCE) else WEAK


UNCHECKED_STATES: tuple[str, ...] = (UNKNOWN, AMBIGUOUS, NEVER_EXISTED)


def is_unchecked(row: Mapping[str, object]) -> bool:
    """A strong row the scan could not settle: never `ok`, never actionable, always counted."""
    return (
        row.get("state") in UNCHECKED_STATES
        and row.get("strength") == STRONG
        and row.get("class") != ARCHIVE
    )


def is_actionable(row: Mapping[str, object]) -> bool:
    """Moved or gone, strong, not archive: what a surface counts and a fix rate divides by."""
    return (
        row.get("state") in ACTIONABLE_STATES
        and row.get("strength") == STRONG
        and row.get("class") != ARCHIVE
    )


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
    check_limit(limit)
    check_filters(states, ())
    return summarize(scan(config, store, globs=globs, classes=classes), states=states, limit=limit)


def check_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be 1..{MAX_LIMIT}, got {limit}")


def check_filters(states: Sequence[str], strengths: Sequence[str]) -> None:
    for given, known, name in ((states, ALL_STATES, "state"), (strengths, STRENGTHS, "strength")):
        unknown = [s for s in given if s not in known]
        if unknown:
            raise ValueError(f"unknown {name} {unknown[0]!r}; one of {', '.join(known)}")


def counted(row: Mapping[str, object], strengths: Sequence[str]) -> bool:
    """A reference doc's weak rows stay out of every summary unless a strength filter asks."""
    if strengths:
        return row.get("strength") in strengths
    return row.get("class") != REFERENCE or row.get("strength") == STRONG


def summarize(
    found: Scan,
    *,
    states: Sequence[str] = (),
    strengths: Sequence[str] = (),
    limit: int = DEFAULT_LIMIT,
    actionable: bool = False,
) -> dict[str, object]:
    """The payload: counts over every counted row, then the rows the filters keep, capped.

    ``actionable`` answers only moved/gone strong rows, instruction class first (the default)."""
    corpus, rows = found.corpus, found.rows
    marked = bool(found.resolver.config.refs_planned_markers)
    counted_states = ALL_STATES if marked else STATES
    by_class: dict[str, dict[str, int]] = {}
    acted: dict[str, dict[str, int]] = {}
    files: dict[str, int] = {}
    ready: dict[str, int] = {}
    unchecked: dict[str, int] = {}
    weak_hidden = 0
    for row in rows:
        name = str(row["class"])
        if not counted(row, strengths):
            weak_hidden += 1
            continue
        by_class.setdefault(name, {state: 0 for state in counted_states})[str(row["state"])] += 1
        if is_unchecked(row):
            unchecked[name] = unchecked.get(name, 0) + 1
        if row.get("actionable"):
            bucket = acted.setdefault(name, {state: 0 for state in ACTIONABLE_STATES})
            bucket[str(row["state"])] += 1
            files[str(row["file"])] = files.get(str(row["file"]), 0) + 1
        if row.get("patch_ready"):
            ready[name] = ready.get(name, 0) + 1
    if actionable:
        kept = [row for row in rows if row.get("actionable")]
    else:
        kept = [r for r in rows if counted(r, strengths) and (not states or r["state"] in states)]
    if not corpus.files:
        reason = "class_filter_left_no_file" if found.matched else "no_file_matched"
    elif not found.resolver.shapes.qualified:
        # No build stamped a symbol shape: every symbol a doc names went unread, never resolved.
        reason = "symbols_unchecked_no_index"
    elif not rows:
        reason = "no_references"
    elif not kept:
        if not actionable:
            reason = "state_filter_left_no_row"
        else:
            reason = "nothing_actionable_but_unchecked" if unchecked else "nothing_actionable"
    else:
        reason = "ok"
    ranked = sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))
    extra: dict[str, object] = {}
    untrusted = list(UNTRUSTED)
    if marked:
        # Their own field: the page below holds only actionable rows by default (460).
        drops = [r for r in rows if r.get("reason") == PLANNED_BUT_EXISTS and counted(r, strengths)]
        extra["markers_to_drop"] = len(drops)
        extra["markers_to_drop_rows"] = [
            {k: r[k] for k in ("file", "line", "ref")} for r in drops[:limit]
        ]
        untrusted += ["markers_to_drop_rows[].file", "markers_to_drop_rows[].ref"]
    return {
        **extra,
        "reason": reason,
        "files_read": len(corpus.files),
        "total_count": len(kept),
        "returned": min(limit, len(kept)),
        "truncated": len(kept) > limit,
        "limit": limit,
        "states": list(states),
        "strengths": list(strengths),
        "actionable": {name: acted[name] for name in CLASSES if name in acted},
        "actionable_total": sum(sum(c.values()) for c in acted.values()),
        "by_class": by_class,
        "unchecked": {name: unchecked[name] for name in CLASSES if name in unchecked},
        "weak_rows_not_counted": weak_hidden,
        "patch_ready": ready,
        "commands": corpus.commands,
        "files": [{"file": path, "actionable": n} for path, n in ranked[:limit]],
        "files_total": len(ranked),
        "history_budget_spent": found.resolver.budget_spent,
        "skipped_as_external": found.resolver.skipped_external,
        "rows": kept[:limit],
        "corpus_globs": {name: list(globs) for name, globs in corpus.globs.items()},
        "untrusted_fields": untrusted,
    }


# ----------------------------------------------------------------- undocumented exports (461)
# A caller's globs reach a regex: bounded in count, length and wildcards, so none can hang (461).
# Only `*` backtracks; `?` and `[` compile to one character each, so they need no cap.
MAX_GLOBS, MAX_GLOB_CHARS, MAX_GLOB_STARS = 20, 200, 8


def check_globs(globs: Sequence[str], name: str) -> None:
    """Refuse a glob list a caller could make expensive; the toml's go through the config."""
    if len(globs) > MAX_GLOBS:
        raise ValueError(f"{name}: at most {MAX_GLOBS} globs, got {len(globs)}")
    for glob in globs:
        if len(glob) > MAX_GLOB_CHARS or glob.count("*") > MAX_GLOB_STARS:
            raise ValueError(
                f"{name}: a glob is at most {MAX_GLOB_CHARS} characters and {MAX_GLOB_STARS} '*'"
            )


UNDOCUMENTED_UNTRUSTED: tuple[str, ...] = ("rows[].symbol", "rows[].file", "paths[]", "docs[]")


def undocumented(
    config: Config,
    store: GraphStore,
    paths: Sequence[str],
    *,
    docs: Sequence[str] = (),
    limit: int = DEFAULT_LIMIT,
    every: bool = False,
) -> dict[str, object]:
    """Top-level symbols under ``paths`` that no doc reference resolves to (461): `verify_refs` the
    other way. A doc naming the symbol, one of its candidates, or its file counts as naming it."""
    check_limit(limit)
    if not paths:
        raise ValueError("undocumented needs at least one path glob")
    check_globs(paths, "undocumented")
    check_globs(docs, "docs")
    found = scan(config, store, globs=docs)
    named: set[str] = set()
    files: set[str] = set()
    for row in found.rows:
        if row.get("ref_kind") == PATH and row["state"] == OK:
            files.add(str(row.get("path")))
        for site in [row.get("site"), *_listed(row.get("candidates"))]:
            if isinstance(site, dict) and row["state"] in (OK, AMBIGUOUS):
                named.add(str(site.get("qname")))
    allowed = _allowlist(config)
    candidates = _top_level(store, paths)
    languages = store.file_languages()
    seen_visibility = {
        languages.get(str(r["file_path"]), "") for r in candidates
        if VISIBILITY_MODIFIERS & set(_modifiers(r))
    }
    public = [r for r in candidates if not HIDDEN_MODIFIERS & set(_modifiers(r))]
    unnamed = [r for r in public if str(r["qualified_name"]) not in named | allowed]
    rows = [
        {"symbol": str(r["qualified_name"]), "file": r["file_path"], "line": r["line_start"],
         "kind": r["kind"]}
        for r in unnamed
        if str(r["file_path"]) not in files
    ]
    if not candidates:
        reason = "no_symbol_under_paths"
    elif not found.corpus.files:
        reason = "no_docs_read"  # every export reads undocumented because no doc was read
    elif not rows:
        reason = "every_export_documented"
    else:
        reason = "ok"
    unaware = sorted({languages.get(str(r["file_path"]), "") for r in candidates} - seen_visibility)
    return {
        "reason": reason,
        "paths": list(paths),
        "docs": list(docs),
        "docs_read": len(found.corpus.files),
        "candidates": len(candidates),
        "allowlisted": len({str(r["qualified_name"]) for r in candidates} & allowed),
        # Unnamed themselves, documented only because a doc names their file.
        "documented_by_file": len(unnamed) - len(rows),
        "total_count": len(rows),
        "returned": len(rows) if every else min(limit, len(rows)),
        "truncated": not every and len(rows) > limit,
        "limit": limit,
        "rows": rows if every else rows[:limit],  # `every`: the uncapped export a shell streams
        # No visibility word on any candidate in these languages: every one read public.
        "coverage": {"visibility_not_emitted": [lang for lang in unaware if lang]},
        "untrusted_fields": list(UNDOCUMENTED_UNTRUSTED),
    }


def _top_level(store: GraphStore, paths: Sequence[str]) -> list[Row]:
    """Non-test symbols of the export kinds in files the globs match, not inside another symbol; a
    glob starting `!` leaves its files out (`!**/*.test.ts`): the core names no test file itself."""
    keep = [glob for glob in paths if not glob.startswith("!")]
    drop = [glob_regex(glob[1:]) for glob in paths if glob.startswith("!")]
    if not keep:
        raise ValueError("undocumented needs a path glob that is not an exclusion")
    regexes = [glob_regex(glob) for glob in keep]
    found: dict[object, Row] = {}
    matched: dict[str, bool] = {}
    for glob in keep:
        prefix = re.split(r"[*?\[]", glob, maxsplit=1)[0]
        for row in store.nodes_of_kinds_under(TOP_LEVEL_KINDS, prefix):
            path = str(row["file_path"])
            if path not in matched:  # each file matched once, not once per symbol
                matched[path] = any(r.match(path) for r in regexes) and not any(
                    r.match(path) for r in drop
                )
            if matched[path]:
                found.setdefault(row["id"], row)
    rows = list(found.values())
    containers = {c for r in rows if (c := split_qname(str(r["qualified_name"]))[0]) is not None}
    held = store.nodes_by_qualified_names(sorted(containers), limit=1)
    holders = {*TOP_LEVEL_KINDS, *CALLABLE_KINDS, *VALUE_KINDS}
    nested = {c for c, hits in held.items() if any(str(h["kind"]) in holders for h in hits)}
    return sorted(
        (r for r in rows if split_qname(str(r["qualified_name"]))[0] not in nested),
        key=lambda r: (str(r["file_path"]), int(str(r["line_start"])), str(r["qualified_name"])),
    )


def _modifiers(row: Row) -> list[str]:
    raw = row.get("modifiers")
    try:
        found = json.loads(raw) if isinstance(raw, str) and raw else raw
    except ValueError:
        return []
    return [str(m) for m in found] if isinstance(found, list) else []


def _allowlist(config: Config) -> set[str]:
    """The qnames `refs_undocumented_allow` names; a named file that cannot be read is a config
    error, never an empty list (R5.3)."""
    if config.refs_undocumented_allow is None:
        return set()
    try:
        text = read_text(config.root, config.root / config.refs_undocumented_allow)
    except (OSError, ValueError) as error:
        raise ConfigError(f"refs_undocumented_allow: cannot read it: {error}") from error
    lines = (line.split("#", 1)[0].strip() for line in text.splitlines())
    return {line for line in lines if line}


def undocumented_markdown(answer: Mapping[str, object]) -> str:
    """The same answer as a table a human reads."""
    head = [
        f"# undocumented — {answer['total_count']} of {answer['candidates']} exports no doc names",
        "", "| file:line | kind | symbol |", "|---|---|---|",
    ]
    rows = answer.get("rows") or []
    assert isinstance(rows, list)
    head += [f"| {r['file']}:{r['line']} | {r['kind']} | `{r['symbol']}` |" for r in rows]
    if answer.get("truncated"):
        head += ["", f"_truncated at {answer['limit']} of {answer['total_count']} rows_"]
    return "\n".join(head) + "\n"


# ----------------------------------------------------------------- export and diff (443)
EXPORT_KEYS: tuple[str, ...] = ("class", "file", "line", "ref", "ref_kind", "origin", "state",
                                "reason", "strength", "actionable")


def export_rows(found: Scan) -> Iterator[dict[str, object]]:
    """Every row, uncapped, with its diff key first — the private baseline R4 diffs against."""
    for row in found.rows:
        yield {"key": [row["class"], row["file"], row["ref"]],
               **{k: row.get(k) for k in EXPORT_KEYS},
               **{k: v for k, v in row.items() if k not in EXPORT_KEYS}}


def diff_exports(
    old: Iterable[Mapping[str, object]], new: Iterable[Mapping[str, object]]
) -> dict[str, object]:
    """Fixed / new / unchanged actionable rows per class between two exports, keyed by
    (class, file, ref) and counted with multiplicity, so a moved line is never a fix."""
    def bag(rows: Iterable[Mapping[str, object]]) -> dict[tuple[str, ...], int]:
        out: dict[tuple[str, ...], int] = {}
        for row in rows:
            if row.get("actionable"):
                key = tuple(str(part) for part in _listed(row.get("key")))
                out[key] = out.get(key, 0) + 1
        return out

    before, after = bag(old), bag(new)
    by_class: dict[str, dict[str, int]] = {}
    for key in set(before) | set(after):
        counts = by_class.setdefault(key[0], {"baseline": 0, "fixed": 0, "new": 0, "unchanged": 0})
        was, now = before.get(key, 0), after.get(key, 0)
        counts["baseline"] += was
        counts["fixed"] += max(0, was - now)
        counts["new"] += max(0, now - was)
        counts["unchanged"] += min(was, now)
    keys = ("baseline", "fixed", "new", "unchanged")
    total = {k: sum(c[k] for c in by_class.values()) for k in keys}
    return {"by_class": {name: by_class[name] for name in CLASSES if name in by_class},
            "total": total,
            "fix_rate": round(total["fixed"] / total["baseline"], 4) if total["baseline"] else None}


# The cheapest correction a row that is not ok carries when no patch can (439).
HINTS: Mapping[str, str] = {
    GONE: "remove the reference, or name what replaced it",
    NEVER_EXISTED: "no branch ever held it: correct the spelling or remove it",
    AMBIGUOUS: "name one of the candidates in full",
    MOVED: "several successors: name the one meant",
}


def _annotate(row: dict[str, object]) -> None:
    """``patch_ready`` on an actionable moved row with one successor and an in-place form; a hint
    otherwise. An archive row is never patched: it records what was true then."""
    state = row["state"]
    if state == MOVED and "replacement" in row and row.get("actionable"):
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
        if row.get("patch_ready") and in_repo(str(row["file"])):  # host memory: an edit, no diff
            by_file.setdefault(str(row["file"]), []).append(row)
    order = {name: n for n, name in enumerate(CLASSES)}
    out: list[Patch] = []
    skipped = 0
    ranked = sorted(by_file.items(), key=lambda kv: (order[str(kv[1][0]["class"])], kv[0]))
    for doc, edits in ranked:
        try:
            # The bytes as they are: CRLF kept, so the diff matches what `git apply` reads.
            text = read_bytes(config.root, config.root / doc).decode("utf-8")
        except (OSError, ValueError):
            skipped += len(edits)
            continue
        old = text.split("\n")
        old = [line + "\n" for line in old[:-1]] + ([old[-1]] if old[-1] else [])
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


# ----------------------------------------------------------------- session line (439, 443)
# The actionable summary a build stores, so a session start reads counts and never scans docs.
SUMMARY_KEY = "refs_summary"


def docs_fingerprint(config: Config) -> str:
    """Which corpus files exist and how big and how new each is: a stat per file, never a read."""
    digest = hashlib.sha256()
    folder = memory_dir(config)
    for doc in sorted(collect(config).files):
        path = config.root / doc if in_repo(doc) else folder / doc.removeprefix(MEMORY_PREFIX)
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(f"{doc}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()[:16]


def index_generation(store: GraphStore) -> str:
    """HEAD the index was built at, and its files' count and newest write: a refresh moves it."""
    return f"{store.get_meta(LAST_COMMIT_KEY) or ''}@{store.files_stamp()}"


def store_summary(
    config: Config, store: GraphStore, *, budget_s: float = SUMMARY_BUDGET_S
) -> dict[str, object]:
    """Scan once and store the actionable counts with the index generation and the docs' stamp."""
    generation = index_generation(store)
    stamp = docs_fingerprint(config)
    held = stored_summary(store)
    if held is not None and held.get("generation") == generation and held.get("docs") == stamp:
        return held  # nothing moved: the stored counts still answer
    found = scan(config, store, classes=COUNTED_CLASSES, budget_s=budget_s)
    acted = {name: {state: 0 for state in ACTIONABLE_STATES} for name in COUNTED_CLASSES}
    ready = {name: 0 for name in COUNTED_CLASSES}
    unknown = 0
    for row in found.rows:
        name = str(row["class"])
        if row.get("actionable"):
            acted[name][str(row["state"])] += 1
        ready[name] += 1 if row.get("patch_ready") else 0
        if row["state"] == UNKNOWN and row.get("strength") == STRONG and name != REFERENCE:
            unknown += 1
    summary: dict[str, object] = {"generation": generation, "docs": stamp, "actionable": acted,
                                  "patch_ready": ready, "unknown": unknown}
    store.set_meta(SUMMARY_KEY, json.dumps(summary, sort_keys=True))
    return summary


def stored_summary(store: GraphStore) -> dict[str, object] | None:
    raw = store.get_meta(SUMMARY_KEY)
    try:
        held = json.loads(raw) if raw else None
    except ValueError:
        return None
    return held if isinstance(held, dict) else None


def session_line(config: Config, store: GraphStore, *, generation: str | None = None) -> str | None:
    """One count-only line from the stored summary, instruction class first; ``None`` when nothing
    is actionable. It never reads or resolves a doc — a stat per file stamps them (443)."""
    generation = index_generation(store) if generation is None else generation
    held = stored_summary(store)
    if held is None:
        return "code-atlas: doc references not scanned for this index yet — the next refresh scans."
    acted = held.get("actionable")
    ready = held.get("patch_ready")
    if not isinstance(acted, dict) or not isinstance(ready, dict):
        return None

    def total(name: str) -> int:
        counts = acted.get(name)
        return sum(int(v) for v in counts.values()) if isinstance(counts, dict) else 0
    first, others = total(INSTRUCTION), total(MEMORY) + total(REFERENCE)
    held_unknown = held.get("unknown")
    unknown = held_unknown if isinstance(held_unknown, int) else 0
    if not (first or others or unknown):
        line = None
    else:
        line = f"code-atlas: {first} refs in instruction files moved or gone"
        if ready.get(INSTRUCTION):
            line += f" ({ready[INSTRUCTION]} patch ready)"
        line += f"; {others} in other docs"
        if unknown:
            line += f"; {unknown} unchecked (unknown, not ok)"
    stale = []
    if held.get("generation") != generation:
        stale.append("index moved")
    if held.get("docs") != docs_fingerprint(config):
        stale.append("docs changed")
    if stale:
        line = (line or "code-atlas: no actionable doc reference") + (
            f" ({' and '.join(stale)} since last scan)")
    return None if line is None else line + " — `code-atlas query --verify-refs --format md`."


# Doc-derived and repo-derived text in the payload: data, never instructions (429).
UNTRUSTED: tuple[str, ...] = (
    "rows[].ref",
    "rows[].file",
    "rows[].path",
    "rows[].successor",
    "rows[].successors",
    "rows[].replacement",
    "rows[].container",
    "rows[].type",
    "rows[].types",
    "rows[].site.*",
    "rows[].candidate_paths",
    "rows[].candidates[].*",
    "rows[].nearest_existing",
    "files[].file",
)


def markdown(answer: Mapping[str, object]) -> str:
    """The same answer as a table a human reads; reference strings only, never prose."""
    columns = ALL_STATES if "markers_to_drop" in answer else STATES
    head = [
        f"# verify_refs — {answer['total_count']} references in {answer['files_read']} files",
        "",
        "| class | " + " | ".join(columns) + " |",
        "|---|" + "---|" * len(columns),
    ]
    by_class = answer.get("by_class") or {}
    assert isinstance(by_class, dict)
    for name in CLASSES:
        if name in by_class:
            head.append(f"| {name} | " + " | ".join(str(by_class[name][s]) for s in columns) + " |")
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
    drop = answer.get("markers_to_drop_rows") or []
    if isinstance(drop, list) and drop:
        total = answer.get("markers_to_drop")
        head += ["", f"## markers to drop — {total} (planned_but_exists)", ""]
        head += [f"- {r['file']}:{r['line']} `{r['ref']}`" for r in drop]
    if answer.get("truncated"):
        head += ["", f"_truncated at {answer['limit']} of {answer['total_count']} rows_"]
    return "\n".join(head) + "\n"
