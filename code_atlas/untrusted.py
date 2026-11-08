"""Which fields of a tool answer are the indexed repo's text, named once and escaped (429).

A docblock, a source slice, a symbol name or a path is written by whoever wrote the repo, and sits
in an answer beside code-atlas's own fields. ``frame`` escapes every control and format character
in the whole answer (an ANSI escape or a bidi override arrives visible, not live) and names the
repo-derived fields in ``untrusted_fields``; the server ``instructions`` say once that those are
data, never instructions. ``FIELDS`` is the one table, and a served tool missing from it is refused
at registration (R6.7).
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from code_atlas.config import ConfigError
from code_atlas.index_text import escaped, escaped_tree

UNTRUSTED_FIELDS = "untrusted_fields"
SUBJECTS = "subjects"

# A path is dotted keys; ``[]`` walks a list, ``*`` every value of an object.
_LIST = "[]"
_EACH = "*"
# Free text keeps its line breaks; every other named field is one line, so it cannot forge a second.
_MULTILINE = frozenset({"source", "call_sources", "markdown", "text", "default"})

_ROUTES = (
    "routes[].route",
    "routes[].target",
    "routes[].file",
    "routes[].when",
    "routes[].source",
)
_RECORDS = (
    "records[].id",
    "records[].title",
    "records[].url",
    "records[].attributes.*",
)
_ROWS = ("results[].qname", "results[].file")
_MISS = ("candidates[]", "untracked_path", "untracked_paths[]")
_RESOLVED = ("resolved_qname",)
_REF = ("answered_about_ref",)
_CLAIM = ("claim",)
_UNPROVEN = ("unproven[].qname", "unproven[].file")
_CALLS = ("results[].source", "results[].call_sources[]")

FIELDS: dict[str, tuple[str, ...]] = {
    "get_index_status": (
        "routes_ambiguous[].route",
        "routes_ambiguous[].target",
        "head_ref",
        "last_ref",
        "behind_because[].path",
        *_CLAIM,
    ),
    "build_or_update_index": ("last_ref", "head_ref"),
    "search_symbol": (
        *_ROWS,
        "candidates[].qname",
        "candidates[].name",
        "did_you_mean[].qname",
        "did_you_mean[].name",
        "path_excluded[]",
        *_ROUTES,
        *_REF,
    ),
    "file_outline": ("results[].qname", "results[].name", *_REF),
    "read_symbol": (
        "source",
        "file",
        "columns[].name",
        "columns[].type",
        "columns[].default",
        "params[].name",
        "params[].type",
        "supertypes[].qname",
        "supertypes[].name",
        "qname",
        "path_excluded[]",
        "ambiguous_definitions[].superseded_by.qname",
        "ambiguous_definitions[].superseded_by.file",
        *_RECORDS,
        *_MISS,
        *_REF,
    ),
    "compute": ("rows[].qname", "rows[].name", "rows[].file", "detail"),
    "find_callers": (*_ROWS, *_CALLS, *_RESOLVED, *_MISS, *_REF, *_CLAIM),
    "find_references": (*_ROWS, "results[].source", *_RECORDS, *_RESOLVED, *_MISS, *_REF, *_CLAIM),
    "find_implementations": (*_ROWS, *_RESOLVED, *_MISS, *_REF),
    "find_view_data": ("results[].key", "results[].file", "results[].qname", *_RESOLVED, *_REF),
    "include_graph": (
        "results[].path",
        "results[].file",
        "unlinked_includes[].qname",
        "unlinked_includes[].file",
        "unlinked_includes[].target_raw",
        "same_basename_included[]",
        *_REF,
    ),
    "impact": (
        *_ROWS,
        *_RECORDS,
        "records[].via",
        "resolved_qnames.*",
        *_ROUTES,
        *_MISS,
        *_REF,
        *_CLAIM,
    ),
    "impact_modules": ("results[].module", "results[].exemplar", *_CLAIM),
    "subtree_dependencies": (
        "qname",
        "subtree",
        "counterpart",
        "dependent_files[].path",
        "depended_on_paths[].path",
        *_REF,
    ),
    "reachable_from": (*_ROWS, *_UNPROVEN, "qname", "entry_points[]", *_REF),
    "find_orphans": (*_ROWS, *_UNPROVEN, "qname", "entry_points[]", *_REF),
    "explain_path": (
        "path[].source_qname",
        "path[].target_qname",
        "path[].file",
        "from_qname",
        "to_qname",
    ),
    "architecture_overview": (
        "results[].layer",
        "modules[].module",
        "modules[].layer",
        "cross_layer_edges[].source",
        "cross_layer_edges[].target",
        "summary.reachability.buckets[].sample[]",
        "summary.reachability.patterns[].pattern",
        "summary.business_modules.containers[]",
        "summary.business_modules.modules[].module",
        "summary.business_modules.modules[].label",
        "summary.business_modules.modules[].hub",
        "summary.business_modules.modules[].directories[]",
        "summary.business_modules.modules[].trees[]",
        "summary.business_modules.refused[].container",
        "summary.mirrors.pairs[].left",
        "summary.mirrors.pairs[].right",
        "summary.mirrors.pairs[].sample[]",
    ),
    "guided_tour": ("results[].file", "results[].rationale"),
    "generate_onboarding": (),
    "check_architecture_rules": (
        "results[].rule_id",
        "results[].source_file",
        "results[].forbidden_file",
        "results[].via_qname",
        "rules[].rule_id",
    ),
    "check_column_defaults": ("results[].column", "results[].default", *_RESOLVED),
    "diff_architecture": (
        "markdown",
        "message",
        "before_ref",
        "after_ref",
        "diff.caveats_before_only[].text",
        "diff.caveats_after_only[].text",
        "diff.entry_points_added[]",
        "diff.entry_points_removed[]",
        "diff.modules_added[]",
        "diff.modules_removed[]",
        "diff.hub_movements[].file",
        "diff.layer_reassignments[].file",
        "diff.layer_reassignments[].before",
        "diff.layer_reassignments[].after",
        "diff.matrix_added[].source",
        "diff.matrix_added[].target",
        "diff.matrix_removed[].source",
        "diff.matrix_removed[].target",
    ),
    "class_diagram": ("results[].qname", "markdown"),
    "trace_capability": (
        "results[].seed",
        "results[].seed_file",
        "results[].steps[].qname",
        "results[].steps[].file",
        "results[].route.route",
        "results[].route.target",
        "results[].route.file",
        "results[].route.when",
        "results[].route.source",
        "nearest_routes[]",
    ),
}


class UntrustedShapeError(TypeError):
    """A named field holds a shape ``frame`` cannot mark — refused, never passed through raw."""


def _segments(path: str) -> list[str]:
    segments: list[str] = []
    for part in path.split("."):
        if part.endswith(_LIST):
            segments.extend([part[: -len(_LIST)], _LIST])
        else:
            segments.append(part)
    return segments


def _mark(holder: Any, key: Any, segments: list[str], multiline: bool, path: str) -> bool:
    """Escape what ``holder[key]`` holds at the end of ``segments``; true when text was there."""
    node = holder[key]
    if node is None:
        return False
    if not segments:
        return _leaf(holder, key, node, multiline, path)
    head, rest = segments[0], segments[1:]
    if head == _LIST:
        if not isinstance(node, list):
            raise UntrustedShapeError(f"{path}: expected a list, got {type(node).__name__}")
        return any([_mark(node, index, rest, multiline, path) for index in range(len(node))])
    if not isinstance(node, dict):
        raise UntrustedShapeError(f"{path}: expected an object, got {type(node).__name__}")
    if head == _EACH:
        return any([_mark(node, name, rest, multiline, path) for name in list(node)])
    return head in node and _mark(node, head, rest, multiline, path)


def _leaf(holder: Any, key: Any, node: Any, multiline: bool, path: str) -> bool:
    if isinstance(node, str):
        holder[key] = escaped(node, multiline=multiline)
        return node != ""
    if isinstance(node, (int, float, bool)):
        return False
    if isinstance(node, list) and all(isinstance(item, (str, int, float, bool)) for item in node):
        holder[key] = [escaped(i, multiline=multiline) if isinstance(i, str) else i for i in node]
        return any(isinstance(item, str) and item for item in node)
    raise UntrustedShapeError(f"{path}: cannot mark a {type(node).__name__}")


def _named(answer: dict[str, Any], paths: tuple[str, ...], prefix: str) -> list[str]:
    present: list[str] = []
    for path in paths:
        segments = _segments(path)
        leaf = next(part for part in reversed(segments) if part not in (_LIST, _EACH))
        if _mark({"": answer}, "", segments, leaf in _MULTILINE, prefix + path):
            present.append(prefix + path)
    return present


def frame(name: str, answer: dict[str, object]) -> dict[str, object]:
    """``answer`` with every control escaped and the repo-derived fields it carries named."""
    paths = FIELDS[name]
    cleaned: dict[str, Any] = escaped_tree(answer)
    present = _named(cleaned, paths, "")
    subjects = cleaned.get(SUBJECTS)
    if isinstance(subjects, list):
        for subject in subjects:
            if isinstance(subject, dict):
                for path in _named(subject, paths, f"{SUBJECTS}[]."):
                    if path not in present:
                        present.append(path)
    if present:
        cleaned[UNTRUSTED_FIELDS] = present
    return cleaned


def framed(name: str, tool: Callable[..., dict[str, object]]) -> Callable[..., dict[str, object]]:
    """``tool`` whose every answer leaves through ``frame``; a tool the table lacks is refused."""
    if name not in FIELDS:
        raise ConfigError(f"tool {name!r} has no entry in untrusted.FIELDS")

    @functools.wraps(tool)
    def wrapped(*args: Any, **kwargs: Any) -> dict[str, object]:
        return frame(name, tool(*args, **kwargs))

    return wrapped
