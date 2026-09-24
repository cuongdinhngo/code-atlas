"""The adapter contract: vocabulary, version, and validation — the single source of truth (§4).

Every adapter emits this vocabulary and every core module imports it from here; nothing else
re-declares a kind or field list (R3.2). Adapters emit **bare** edges — ``target_raw`` is required,
``target_qname`` is filled later by the resolver (R3.3).

Qualified names follow CONVENTION §3. A container keeps its native separator (``\\Ns\\Class``,
``module``, ``src/user.ts``) and a member is joined onto it with ``MEMBER_SEPARATOR``::

    \\Ns\\Class        \\Ns\\Class::method       \\Ns\\Class::$prop      \\Ns\\Class::CONST
    \\ns\\func         src/user.ts::User::save   module.Class::method

``File`` nodes use the repo-relative path as their qualified name.

An adapter opens the stream by announcing itself once — the **handshake** of §4.1, validated by
:func:`validate_meta` — so the core never carries a table of who owns which file suffix.
"""

import re
from typing import Literal, get_args

# v9: `Table`, `Column` and `WRITES` join the vocabulary for SQL tier 2 (022). R3.1's literal
# trigger fires — kinds moved — so the bump is owed. The three words join no existing named subset
# below, so a repo with no SQL adapter sees identical rows from every tool (`test_sql_tier2_
# vocabulary_is_opt_in.py`); what it does pay is the one full rebuild any bump forces.
# v10: `ForeignKey` (236). A foreign-key constraint is a schema object, not a second definition of
# the table it sits on — a distinct kind lets `search_symbol` separate a table's DDL site from a
# constraint on it (R5.6), so the correct FK answer is no longer re-derived. R3.1/R3.5 owe the bump.
# v11: `ALTERS` (321). A file's DDL changing an object is not a write to its columns, so it is a
# word of its own rather than a `WRITES` that would enrol every migration as a writer.
# v12: `DELETES` (328). A statement that removes rows is not a writer of those columns — same
# trap 321 met for DDL — so it is a word of its own rather than a `WRITES` enroling every deleter.
CONTRACT_VERSION = 12

# Ordered Literal is the typing SSoT; NODE_KINDS is derived so schemas cannot drift (R3.2 / 056).
NodeKind = Literal[
    "File",
    "Namespace",
    "Class",
    "Interface",
    "Trait",
    "Enum",
    "Function",
    "Method",
    "Property",
    "ClassConst",
    "Const",
    # v9 (022): a database object and its member. A table keeps its native separator (`dbo.Trans`)
    # and a column joins on with MEMBER_SEPARATOR (`dbo.Trans::ChangeUser`), exactly as a property
    # does — so the qname convention did not move, only the vocabulary.
    "Table",
    "Column",
    # v10 (236): a foreign-key constraint, addressable in its own right. Its qname joins the owning
    # table like a member (`dbo.MemberType::FK_x`); the child/referenced tables and columns ride
    # `extra`, since NODE_FIELDS is frozen.
    "ForeignKey",
]
NODE_KINDS: tuple[str, ...] = get_args(NodeKind)

# Node-kind subsets the 117 abstraction headline reads — consumers import these, never re-list the
# kinds (the same rule CALLER_KINDS/IMPL_KINDS carry below). A named subset of an existing
# vocabulary is not a vocabulary change, so CONTRACT_VERSION is untouched (R3).
TYPE_KINDS: tuple[str, ...] = ("Class", "Interface", "Trait", "Enum")
CALLABLE_KINDS: tuple[str, ...] = ("Function", "Method")

EDGE_KINDS: tuple[str, ...] = (
    "CONTAINS",
    "EXTENDS",
    "IMPLEMENTS",
    "USES_TRAIT",
    "CALLS",
    "NEW",
    "IMPORTS",
    "INCLUDES",
    "REFERENCES",
    "ALIASES",
    "PROVIDES_VIEW_DATA",
    # v9 (022): a routine assigns a column. Targets the Column when the statement names it; targets
    # the Table at DYNAMIC when it writes columns it does not name — the writer is a fact even where
    # the column list is not, and a guessed list would be worse than an honest one (R5.6).
    "WRITES",
    # v11 (321): a file's DDL changes a Table or Function. RESOLVED when the statement is literal;
    # DYNAMIC when the name was read out of a string the file executes — a claim, never a fact.
    "ALTERS",
    # v12 (328): a routine removes rows from a Table. Never a Column list — the statement names
    # none to write — so check_column_defaults keeps reading WRITES only.
    "DELETES",
)

# Resolver (§8.2) looks these up by FQN; new EDGE_KINDS must opt in here (not silently join).
FQN_EDGE_KINDS: frozenset[str] = frozenset(
    {
        "EXTENDS", "IMPLEMENTS", "USES_TRAIT", "CALLS", "NEW", "ALIASES", "REFERENCES", "WRITES",
        "ALTERS", "DELETES",
    }
)
# DYNAMIC rows the resolver still links: their target is a name the adapter read, not an unknown
# callee (094 / 321). Every other DYNAMIC row names nothing linkable and is skipped.
DYNAMIC_LINKED_KINDS: tuple[str, ...] = ("REFERENCES", "ALTERS")

# Path-shaped edges: the target is a FILE, so the resolver looks it up among File qnames instead of
# by FQN. The kinds differ only in how ``target_raw`` names that file, and the contract states which
# — the resolver reads a declaration, never the shape of a string (188 / R5.2).
PATH_TARGET_BASIS: dict[str, str] = {
    # A textual include names a file relative to the including file's own directory.
    "INCLUDES": "includer-relative",
    # A module specifier the adapter already resolved against the filesystem (155). Where it names
    # nothing indexed — an unresolvable specifier, or a symbol import like `use A\\B\\C` — the
    # lookup simply misses and the edge stays bare, which is the whole discriminator.
    "IMPORTS": "repo-relative",
}
PATH_EDGE_KINDS: tuple[str, ...] = tuple(PATH_TARGET_BASIS)

# Named semantic subsets for nav tools (§12) — consumers import these; do not re-list kinds.
CALLER_KINDS: tuple[str, ...] = ("CALLS", "NEW")
IMPL_KINDS: tuple[str, ...] = ("EXTENDS", "IMPLEMENTS")
# Class-diagram ancestry (144) — inheritance FQN edges only; not CALLS/NEW/ALIASES.
INHERIT_KINDS: tuple[str, ...] = ("EXTENDS", "IMPLEMENTS", "USES_TRAIT")
# Contained members a class box lists (144).
CLASS_MEMBER_KINDS: tuple[str, ...] = ("Method", "Property", "ClassConst")
# Class / Interface — subjects that emit EXTENDS/IMPLEMENTS (285 / IMPL_KINDS).
SUPERTYPE_SUBJECT_KINDS: tuple[str, ...] = ("Class", "Interface")
# Schema container whose members ride CONTAINS — kind branch, never language (248 / R1.1).
TABLE_KIND = "Table"
COLUMN_KIND = "Column"
CONTAINS = "CONTAINS"
# find_references language-emits reader (186/232): the kinds "this language never emits that
# relation" is asked over. Honesty across *unlinked* inbound edges uses the full EDGE_KINDS
# vocabulary instead (255), so a Table with unlinked WRITES is not a bare no_matches.
UNMODELLED_REFERENCE_KINDS: tuple[str, ...] = ("REFERENCES", "IMPORTS")

# Evidence that an inbound relation exists but went unmeasured (255): every contract kind except
# the containment spine. CONTAINS is stored unlinked for every declared member, so it names every
# subject and can never separate a genuine zero from an unmeasured relation.
UNLINKED_EVIDENCE_KINDS: tuple[str, ...] = tuple(k for k in EDGE_KINDS if k != CONTAINS)

# Subject kind → inbound evidence kinds (264). Derived from NODE_KINDS × UNLINKED_EVIDENCE_KINDS —
# not a hand-kept table (R6.7). Uniform today because the contract encodes no per-subject target
# set; a new NODE_KIND auto-joins. contract_version does not bump (named subset of existing words).
INBOUND_KINDS_BY_SUBJECT: dict[str, tuple[str, ...]] = {
    kind: UNLINKED_EVIDENCE_KINDS for kind in NODE_KINDS
}


def inbound_kinds_for(subject_kind: str) -> tuple[str, ...]:
    """Inbound edge kinds that can falsify a genuine empty answer for ``subject_kind`` (264)."""
    return INBOUND_KINDS_BY_SUBJECT.get(subject_kind, ())

# Impact engine (§12 / M6) — incoming-edge walk weights (callers / subtypes / includers).
IMPACT_KIND_WEIGHTS: dict[str, float] = {
    "CALLS": 1.0,
    "NEW": 1.0,
    "EXTENDS": 0.9,
    "IMPLEMENTS": 0.9,
    "INCLUDES": 0.8,
    # A module dependency is a file-level dependency, so it carries the include weight (188): a
    # lower one would rank a real module edge below a same-file call, a higher one would outrank a
    # direct caller. Contributed nothing before 188 — no IMPORTS edge was ever linked.
    "IMPORTS": 0.8,
}
IMPACT_KINDS: tuple[str, ...] = tuple(IMPACT_KIND_WEIGHTS)

# The one write edge, named once so consumers spell it in a single place (PROVIDES_VIEW_DATA
# precedent below). A bare string is not a named subset, so tier 2 stays opt-in (022 AC3).
WRITES = "WRITES"
ALTERS = "ALTERS"
DELETES = "DELETES"

# Ordered Literal is the typing SSoT, NODE_KINDS' rule applied to the tier a tool now takes as a
# parameter (251): a bare `str` publishes no choice in the MCP input schema, so the vocabulary would
# be discoverable only by triggering the error. Derived, never re-listed (R3.2).
ConfidenceTier = Literal["RESOLVED", "HEURISTIC", "DYNAMIC"]
CONFIDENCE_TIERS: tuple[str, ...] = get_args(ConfidenceTier)

NODE_FIELDS: tuple[str, ...] = (
    "kind",
    "name",
    "qualified_name",
    "file_path",
    "line_start",
    "line_end",
    "modifiers",
    "params",
    "is_test",
    "extra",
)

EDGE_FIELDS: tuple[str, ...] = (
    "kind",
    "source_qname",
    "target_qname",
    "target_raw",
    "file_path",
    "line",
    "confidence_tier",
    "args",
    "arg_keys",
)

# One entry per argument at a CALLS/NEW site, in source order (contract v3, task 049).
# JSON ``null`` means "not a literal" — a variable, a call, any expression the parser saw but did
# not evaluate. A string is one of ARG_LITERALS: the *category*, never the value.
ARG_LITERALS: tuple[str, ...] = ("null", "true", "false", "number", "string", "array")
# Parallel to ``args`` (contract v5, task 063): per-arg ``null`` or a list of top-level string
# keys from an array literal. Absent field / null slot = keys not captured (pre-v5 indexes).
ARG_KEYS_FIELD = "arg_keys"
# Reserved ``args`` selectors that are not literals: fewer arguments than asked for, and "present
# but not a literal". Kept apart from ARG_LITERALS so neither list can shadow the other.
ARG_ABSENT = "absent"
ARG_DYNAMIC = "dynamic"
ARG_SELECTORS: tuple[str, ...] = (*ARG_LITERALS, ARG_ABSENT, ARG_DYNAMIC)

RESULT_FIELDS: tuple[str, ...] = ("path", "ok", "nodes", "edges", "error")

# The handshake an adapter announces itself with, before any result (§4.1).
META_FIELDS: tuple[str, ...] = ("name", "extensions", "capabilities", "contract_version")

# The optional ones carry a default or stay NULL in the store (PLAN §10; target_qname per §8.2).
REQUIRED_NODE_FIELDS: tuple[str, ...] = (
    "kind",
    "name",
    "qualified_name",
    "file_path",
    "line_start",
)
REQUIRED_EDGE_FIELDS: tuple[str, ...] = (
    "kind",
    "source_qname",
    "target_raw",
    "file_path",
    "line",
)
REQUIRED_RESULT_FIELDS: tuple[str, ...] = ("path", "ok")
# Capabilities are optional by definition (R1.6); the other three identify the adapter.
REQUIRED_META_FIELDS: tuple[str, ...] = ("name", "extensions", "contract_version")

# Advertised, never required: an absent flag is legal and the core degrades without it (R1.6).
Capabilities = dict[str, bool]
# semantic_types (task 311): a file-at-a-time local type table backs member-call receivers
# (annotations / `new X` / assignments — not an external checker). Adapters that ship that table
# declare it; adapters that do not must not.
KNOWN_CAPABILITIES: tuple[str, ...] = (
    "semantic_types",
    "params",
    "args",
    "modifiers",
    "declared_types",
    "inheritance",
)

# ``extra`` / tool-payload key for declarations-only stub nodes (task 039). Not a contract bump.
STUB_FLAG = "stub"
# Tool-payload key for edges emitted from CA_INDIRECTION_RULES (task 040). Not a contract bump.
RULE_FLAG = "rule"
# File.extra key: resolution strategies the graph does not model (279). Not a contract bump.
UNMODELLED_RESOLUTION = "unmodelled_resolution"
# Strategy token under UNMODELLED_RESOLUTION — registered class autoload (language-standard API).
RESOLUTION_AUTOLOAD = "autoload"
# Strategy token — runtime module load the graph cannot name: non-literal `import()`/`require()`,
# `importlib`/`__import__` (294/295).
RESOLUTION_DYNAMIC_IMPORT = "dynamic_import"
# Strategy token — string-executed SQL (sp_executesql / EXEC @var) (296).
RESOLUTION_DYNAMIC_SQL = "dynamic_sql"
# Every strategy token, one registry (318): the brief's refusal gate reads it; a stamp an adapter
# emits outside it is a test failure. Grouping shipped tokens — not a contract bump.
UNMODELLED_RESOLUTION_STRATEGIES: tuple[str, ...] = (
    RESOLUTION_AUTOLOAD,
    RESOLUTION_DYNAMIC_IMPORT,
    RESOLUTION_DYNAMIC_SQL,
)

# Synthetic target_raw for PROVIDES_VIEW_DATA (task 062) — not an FQN; never resolved.
VIEW_DATA_PREFIX = "viewdata:"
PROVIDES_VIEW_DATA = "PROVIDES_VIEW_DATA"

MEMBER_SEPARATOR = "::"

# A ``target_raw`` may name the type of a member instead of a type directly (137): the receiver of
# ``\A::m()::plus`` is whatever ``\A::m`` was declared to return. Adapters emit it when the file
# names the member but not its type, which is the ordinary case for a call into another file — a
# single file cannot know all targets (R3.3), and the graph already holds the declared type.
TYPE_OF_SUFFIX = "()"

# What a declared type may say instead of naming one: the type that declared the member, and the
# type it was called on. Every language with inheritance has both, so the contract fixes the two
# words here — the same way it already fixes USES_TRAIT — and the core reads them from here.
RELATIVE_TYPE_DECLARING = "self"
RELATIVE_TYPE_RECEIVER = "static"
RELATIVE_TYPES: tuple[str, ...] = (RELATIVE_TYPE_DECLARING, RELATIVE_TYPE_RECEIVER)


def type_of(member_qname: str) -> str:
    """The reference that means "the declared type of ``member_qname``"."""
    return member_qname + TYPE_OF_SUFFIX


def split_type_of(reference: str) -> str | None:
    """The member whose type ``reference`` names, or None when it names a type directly."""
    if not reference.endswith(TYPE_OF_SUFFIX):
        return None
    return reference[: -len(TYPE_OF_SUFFIX)]


def split_qname(qname: str) -> tuple[str | None, str]:
    """Split a qualified name at its last member separator into (container, member).

    The container is None for a name with no member part (a class, function, or file).
    """
    container, separator, member = qname.rpartition(MEMBER_SEPARATOR)
    if not separator:
        return None, qname
    return container, member


def join_qname(container: str, member: str) -> str:
    """Join a container qualified name and a member name into one qualified name."""
    return f"{container}{MEMBER_SEPARATOR}{member}"


# Single-character separators containers use natively (CONVENTION §3). The member join is always
# MEMBER_SEPARATOR; agents often guess the last join as one of these instead (249).
_CONTAINER_SEPARATORS = frozenset({".", "\\", "/"})


def member_separator_variant(query: str) -> str | None:
    """Spell the last container separator as the member join, or None when no retry applies.

    Only the last ``.`` / ``\\`` / ``/`` moves — the member is always the final segment. Already
    carrying ``::`` as that last join, or having no separator at all, yields None (249).
    """
    i = len(query) - 1
    while i >= 0:
        ch = query[i]
        if ch in _CONTAINER_SEPARATORS:
            variant = f"{query[:i]}{MEMBER_SEPARATOR}{query[i + 1 :]}"
            return variant if variant != query else None
        if ch == ":" and i > 0 and query[i - 1] == ":":
            return None
        i -= 1
    return None


# Naming-convention splitter for zero-overlap guesses (253). Camel / Pascal / snake / kebab — not a
# language fact (R1.1 / R2). Short and ultra-common verb crumbs stay out so ``get`` cannot flood.
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NAME_SEP = re.compile(r"[_\-.\s:/\\]+")
_TOKEN_STOP = frozenset({"get", "set", "new", "add", "the", "and", "for", "with", "from"})
_TOKEN_MIN_LEN = 4
TOKEN_CANDIDATE_K = 5


def name_tokens(query: str) -> tuple[str, ...]:
    """Lowercase identifier tokens from a guessed name; empty when nothing significant remains."""
    if not query.strip():
        return ()
    spaced = _CAMEL_BOUNDARY.sub(" ", query.strip())
    out: list[str] = []
    seen: set[str] = set()
    for part in _NAME_SEP.split(spaced):
        token = part.strip().lower()
        if len(token) < _TOKEN_MIN_LEN or token in _TOKEN_STOP or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return tuple(out)


def validate(result: object) -> list[str]:
    """Check one adapter result against the contract; return error messages, empty when valid.

    Returns instead of raising so the indexer can set ``parsed_ok=0`` for a bad file and keep the
    stream going (R5.1), while the conformance tests assert an empty list. The input is untrusted
    JSON from a subprocess, so it may be any shape at all.
    """
    if not isinstance(result, dict):
        return [_wrong_type("result", result, "an object")]

    errors = _check_keys("result", result, RESULT_FIELDS, REQUIRED_RESULT_FIELDS)
    if "path" in result and not isinstance(result["path"], str):
        errors.append(_wrong_type("result.path", result["path"], "a repo-relative path string"))
    if "ok" in result and not isinstance(result["ok"], bool):
        errors.append(_wrong_type("result.ok", result["ok"], "a boolean"))

    if result.get("ok") is False:
        return errors + _check_failed_result(result)

    for name, fields, required, kinds, label in (
        ("nodes", NODE_FIELDS, REQUIRED_NODE_FIELDS, NODE_KINDS, "node kind"),
        ("edges", EDGE_FIELDS, REQUIRED_EDGE_FIELDS, EDGE_KINDS, "edge kind"),
    ):
        rows = result.get(name)
        if not isinstance(rows, list):
            errors.append(_wrong_type(f"result.{name}", rows, "a list"))
            continue
        for index, row in enumerate(rows):
            errors += _check_row(f"{name}[{index}]", row, fields, required, kinds, label)
    return errors


def validate_meta(meta: object) -> list[str]:
    """Check one adapter handshake against the contract; return error messages, empty when valid.

    The core reads everything it knows about an adapter from here — the name, the suffixes it owns,
    the optionals it offers — so a malformed handshake is a loud startup failure, not a bad file.
    """
    if not isinstance(meta, dict):
        return [_wrong_type("meta", meta, "an object")]

    errors = _check_keys("meta", meta, META_FIELDS, REQUIRED_META_FIELDS)
    if "name" in meta and (not isinstance(meta["name"], str) or not meta["name"].strip()):
        errors.append(_wrong_type("meta.name", meta["name"], "a non-empty string"))
    if "extensions" in meta:
        errors += _check_extensions(meta["extensions"])
    if "capabilities" in meta:
        errors += _check_capabilities(meta["capabilities"])
    version = meta.get("contract_version")
    if "contract_version" in meta and (isinstance(version, bool) or not isinstance(version, int)):
        errors.append(_wrong_type("meta.contract_version", version, "an integer"))
    return errors


def _check_extensions(extensions: object) -> list[str]:
    """Suffixes are how a file reaches its adapter, so an empty or malformed list is fatal."""
    if not isinstance(extensions, list) or not extensions:
        return [_wrong_type("meta.extensions", extensions, "a non-empty list of file suffixes")]
    return [
        _wrong_type(f"meta.extensions[{index}]", suffix, "a suffix string starting with '.'")
        for index, suffix in enumerate(extensions)
        if not isinstance(suffix, str) or not suffix.startswith(".") or len(suffix) < 2
    ]


def _check_capabilities(capabilities: object) -> list[str]:
    """Flags are booleans; an unknown flag is legal, so the core can meet a richer adapter."""
    if not isinstance(capabilities, dict):
        return [_wrong_type("meta.capabilities", capabilities, "an object of flag -> boolean")]
    return [
        _wrong_type(f"meta.capabilities.{flag}", value, "a boolean")
        for flag, value in capabilities.items()
        if not isinstance(value, bool)
    ]


def _check_failed_result(result: dict[str, object]) -> list[str]:
    """A failed parse needs an error string and contributes no rows (R5.1)."""
    errors = []
    error = result.get("error")
    if not isinstance(error, str) or not error:
        errors.append(_wrong_type("result.error", error, "a non-empty string when ok is false"))
    for name in ("nodes", "edges"):
        if result.get(name):
            errors.append(
                _wrong_type(f"result.{name}", result[name], "absent or empty when ok is false")
            )
    return errors


def _check_row(
    path: str,
    row: object,
    fields: tuple[str, ...],
    required: tuple[str, ...],
    kinds: tuple[str, ...],
    label: str,
) -> list[str]:
    """Check one node or edge: its key set, its kind, and its confidence tier when present."""
    if not isinstance(row, dict):
        return [_wrong_type(path, row, "an object")]

    errors = _check_keys(path, row, fields, required)
    if "kind" in row and row["kind"] not in kinds:
        errors.append(_not_allowed(f"{path}.kind", row["kind"], label, kinds))
    if "confidence_tier" in row and row["confidence_tier"] not in CONFIDENCE_TIERS:
        errors.append(
            _not_allowed(
                f"{path}.confidence_tier",
                row["confidence_tier"],
                "confidence tier",
                CONFIDENCE_TIERS,
            )
        )
    if "args" in row:
        errors += _check_args(path, row["args"])
    if ARG_KEYS_FIELD in row:
        errors += _check_arg_keys(path, row[ARG_KEYS_FIELD], row.get("args"))
    return errors


def _check_args(path: str, args: object) -> list[str]:
    """``args`` is a list; each entry is null or one of ARG_LITERALS (never a literal's value)."""
    if args is None:
        return []
    if not isinstance(args, list):
        return [_wrong_type(f"{path}.args", args, "a list of argument literals or nulls")]
    return [
        _not_allowed(f"{path}.args[{index}]", entry, "argument literal", ARG_LITERALS)
        for index, entry in enumerate(args)
        if entry is not None and entry not in ARG_LITERALS
    ]


def _check_arg_keys(path: str, arg_keys: object, args: object) -> list[str]:
    """``arg_keys`` is a list parallel to ``args``: null or a list of strings per position."""
    if arg_keys is None:
        return []
    if not isinstance(arg_keys, list):
        return [_wrong_type(f"{path}.arg_keys", arg_keys, "a list of key lists or nulls")]
    errors: list[str] = []
    if isinstance(args, list) and len(arg_keys) != len(args):
        errors.append(
            f"{path}.arg_keys: length {len(arg_keys)} must match args length {len(args)}"
        )
    for index, entry in enumerate(arg_keys):
        if entry is None:
            continue
        if not isinstance(entry, list):
            errors.append(
                _wrong_type(f"{path}.arg_keys[{index}]", entry, "a list of strings or null")
            )
            continue
        for key_index, key in enumerate(entry):
            if not isinstance(key, str):
                errors.append(
                    _wrong_type(f"{path}.arg_keys[{index}][{key_index}]", key, "a string")
                )
    return errors


def _check_keys(
    path: str, mapping: dict[str, object], fields: tuple[str, ...], required: tuple[str, ...]
) -> list[str]:
    """Report missing required keys, then keys outside the contract vocabulary."""
    errors = [
        _missing(f"{path}.{field}", f"one of the required fields {', '.join(required)}")
        for field in required
        if field not in mapping
    ]
    errors += [
        _not_allowed(f"{path}.{key}", key, "contract field", fields)
        for key in mapping
        if key not in fields
    ]
    return errors


def _not_allowed(path: str, value: object, label: str, allowed: tuple[str, ...]) -> str:
    return f"{path}: {value!r} is not an allowed {label} (expected one of {', '.join(allowed)})"


def _missing(path: str, expected: str) -> str:
    return f"{path}: missing (expected {expected})"


def _wrong_type(path: str, value: object, expected: str) -> str:
    return f"{path}: {type(value).__name__} (expected {expected})"
