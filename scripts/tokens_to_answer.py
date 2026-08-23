#!/usr/bin/env python3
"""Tokens-to-answer benchmark harness (task 034 / §19 agent-first pivot).

Makes the product thesis falsifiable: for each hand-labelled question it measures the
tokens an agent spends reaching the *correct* answer two ways — via code-atlas tools vs a
grep+``Read`` baseline — and reports a per-question and aggregate ratio (higher = code-atlas
cheaper). Deterministic by design: the "agent" is a fixed recipe per question, not a live
model (R4 — no network/LLM), so the same inputs give the same rows and CI can gate on them.

Dev tooling, not core: it imports the tools but lives under ``scripts/`` (SRP). Fixture-tier
questions run against committed fixtures (needs the PHP adapter to build the index); the same
harness can run pinned public samples via ``cross_repo_validate`` — see the questions file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
for _p in (str(_REPO), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cross_repo_validate  # noqa: E402 — reuse the clone-at-SHA + php-cmd machinery (dev tooling)

from code_atlas.config import Config, load_config  # noqa: E402
from code_atlas.indexer import full_build  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from code_atlas.tokens import estimate_tokens  # noqa: E402 — one definition site (099)
from code_atlas.tools import (  # noqa: E402
    architecture_overview,
    find_callers,
    find_implementations,
    find_orphans,
    find_references,
    generate_onboarding,
    get_index_status,
    guided_tour,
    impact,
    include_graph,
    reachable_from,
    read_symbol,
    search_symbol,
)

_QUESTIONS = _REPO / "scripts" / "tokens_to_answer_questions.json"
_DEFAULT_REPORT = _REPO / "artifacts" / "tokens-to-answer-report.json"
# Deliberately not the file ci.yml uploads: a local run may name a private repo (task 045).
_DEFAULT_LOCAL_REPORT = _REPO / "artifacts" / "tokens-to-answer-local-report.json"
# CI finds its own PR comment by this marker and edits it, instead of posting a new one per push.
COMMENT_MARKER = "<!-- tokens-to-answer-report -->"
_DEFAULT_PHP = shlex.join(["php", str(_REPO / "adapters" / "php" / "index.php"), "--server"])

# The tools a recipe may call, bound per repo. get_index_status needs the servable names.
_TOOL_NAMES = (
    get_index_status.NAME,
    architecture_overview.NAME,
    guided_tour.NAME,
    generate_onboarding.NAME,
    search_symbol.NAME,
    read_symbol.NAME,
    find_callers.NAME,
    find_references.NAME,
    find_implementations.NAME,
    include_graph.NAME,
    impact.NAME,
    reachable_from.NAME,
    find_orphans.NAME,
)
_NATIVE_TOOLS = frozenset({"grep", "read_file"})


class BenchmarkRegressionError(AssertionError):
    """The tokens-to-answer gate failed: atlas got an answer wrong, or the ratio regressed."""




# Absolute paths a payload carries (071's `index_root`, `get_index_status`'s `db_path`). Their
# length is a property of where the checkout lives, so counting them verbatim would make the gate
# a function of path depth: the same code measured 0.326 at `/tmp/w` and 0.236 sixty chars deeper.
ENV_PATH_FIELDS = ("index_root", "db_path")
ENV_PATH_PLACEHOLDER = "/<root>"


def normalize_env_paths(payload: object) -> object:
    """Fixed-width stand-in for environment-dependent paths, so the count is checkout-invariant.

    Only what is *counted* is normalized; the raw response still reaches correctness matching.
    A field's presence is still paid for — adding one moves the number, moving the repo does not.
    """
    if isinstance(payload, dict):
        return {
            key: ENV_PATH_PLACEHOLDER
            if key in ENV_PATH_FIELDS and isinstance(value, str)
            else normalize_env_paths(value)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [normalize_env_paths(item) for item in payload]
    return payload


def bind_tools(config: Config) -> dict[str, Callable[..., dict[str, object]]]:
    """One repo's tool callables, keyed by name (the recipe's vocabulary)."""
    return {
        get_index_status.NAME: get_index_status.create(config, _TOOL_NAMES),
        search_symbol.NAME: search_symbol.create(config),
        read_symbol.NAME: read_symbol.create(config),
        find_callers.NAME: find_callers.create(config),
        find_references.NAME: find_references.create(config),
        find_implementations.NAME: find_implementations.create(config),
        include_graph.NAME: include_graph.create(config),
        impact.NAME: impact.create(config),
        reachable_from.NAME: reachable_from.create(config),
        find_orphans.NAME: find_orphans.create(config),
        architecture_overview.NAME: architecture_overview.create(config),
        guided_tour.NAME: guided_tour.create(config),
        generate_onboarding.NAME: generate_onboarding.create(config),
    }


def run_atlas_path(
    tools: dict[str, Callable[..., dict[str, object]]], steps: list[dict[str, Any]]
) -> tuple[int, list[dict[str, object]]]:
    """Execute the recipe's tool calls; return (tokens spent, the raw responses).

    Tokens are counted on the JSON payload (what the agent actually receives), but the
    responses are returned raw so correctness can match the *un-escaped* strings — a qname
    like ``\\App\\User`` is doubled by ``json.dumps`` and would never substring-match.
    """
    total = 0
    responses: list[dict[str, object]] = []
    for step in steps:
        fn = tools[str(step["tool"])]
        args = dict(step.get("args", {}))
        response = fn(**args)
        blob = json.dumps(normalize_env_paths(response), ensure_ascii=False, sort_keys=True)
        total += estimate_tokens(json.dumps(args, ensure_ascii=False)) + estimate_tokens(blob)
        responses.append(response)
    return total, responses


def _iter_strings(obj: object) -> list[str]:
    """Every string value/key reachable in a response, so correctness matches raw text."""
    found: list[str] = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.extend(_iter_strings(key))
            found.extend(_iter_strings(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(_iter_strings(item))
    return found


def answer_contains(responses: list[dict[str, object]], expected: list[str]) -> bool:
    """True when every expected substring appears in some string of the responses."""
    strings = _iter_strings(responses)
    return all(any(exp in text for text in strings) for exp in expected)


def _mcp_responses(responses: list[dict[str, object]]) -> list[dict[str, object]]:
    """Session recipes mix native steps; recall / CW score MCP payloads only."""
    return [
        r
        for r in responses
        if isinstance(r, dict) and str(r.get("tool", "")) not in _NATIVE_TOOLS
    ]


# Fields a payload uses as an IDENTITY (matched exactly, so a child like ``\\Dead\\Unused``
# cannot satisfy a parent ``\\Dead``) and the free-text fields where body evidence may appear as
# a substring. An onboarding answer keys its members on ``layer`` / ``module`` / ``pattern``
# rather than on a qname, so recall must know those names too (121).
IDENTITY_FIELDS = ("qname", "path", "qualified_name", "file", "layer", "module", "pattern")
FREE_TEXT_FIELDS = ("source", "snippet", "body")


def _collect_answer_text(
    payload: object, identities: set[str], free_text: list[str]
) -> None:
    """Walk a whole MCP payload, not only its ``results`` list.

    An onboarding answer carries its members under ``modules``, or nested inside ``summary``,
    so a scorer that reads one known key scores 0 there and the recall gate silently measures
    nothing — a false green (121). Recursing derives the collection instead of naming it.
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, str) and value:
                if key in IDENTITY_FIELDS:
                    identities.add(value)
                elif key in FREE_TEXT_FIELDS:
                    free_text.append(value)
                continue
            _collect_answer_text(value, identities, free_text)
        return
    if isinstance(payload, (list, tuple)):
        for item in payload:
            if isinstance(item, str):
                free_text.append(item)
            else:
                _collect_answer_text(item, identities, free_text)


def found_expected_members(
    responses: list[dict[str, object]], expected_set: list[str]
) -> list[str]:
    """Members of ``expected_set`` found in MCP answers (not native grep/read text)."""
    identities: set[str] = set()
    free_text: list[str] = []
    for response in _mcp_responses(responses):
        _collect_answer_text(response, identities, free_text)
    return [
        member
        for member in expected_set
        if member in identities or any(member in text for text in free_text)
    ]


def result_bearing_responses_empty(responses: list[dict[str, object]]) -> bool:
    """True when the last MCP response that carries ``results`` has it empty.

    Emptiness is about the answering step, not the whole path: an earlier
    ``search_symbol`` hit must not hide an empty ``find_callers`` (the round-2
    defect this metric exists to name). Native session tools are ignored.
    """
    bearing = [r for r in _mcp_responses(responses) if "results" in r]
    if not bearing:
        return False
    return not bearing[-1].get("results")


def score_recall(
    responses: list[dict[str, object]], expected_set: list[str]
) -> dict[str, Any]:
    """Recall + confidently_wrong against a complete expected set (task 055).

    ``confidently_wrong`` is reserved for an empty ``results`` answer when ground truth is
    non-empty — distinct from a partial-recall miss (some hits, not all).
    """
    if not expected_set:
        return {
            "recall": None,
            "expected_count": 0,
            "found_count": 0,
            "found": [],
            "missing": [],
            "confidently_wrong": False,
        }
    found = found_expected_members(responses, expected_set)
    missing = [m for m in expected_set if m not in found]
    empty = result_bearing_responses_empty(responses)
    confidently_wrong = empty and len(expected_set) > 0
    return {
        "recall": round(len(found) / len(expected_set), 3),
        "expected_count": len(expected_set),
        "found_count": len(found),
        "found": found,
        "missing": missing,
        "confidently_wrong": confidently_wrong,
    }


# --- Precision: what the answer claimed that ground truth does not hold (task 135) -------------
#
# Recall alone cannot see a wrong answer: every expected member plus four wrong ones scores 1.0.
# The denominator has to be the answer's OWN claimed population, and three measurements show the
# payload's identity bag is not it — `find_callers` echoes the queried `qname`, one result carries
# the same member under both `qname` and `file`, and `find_orphans` puts `unproven` beside
# `results` on purpose (R5.2's honest tiers). So the population is DECLARED per question, and an
# answer shape that legitimately returns more than it was asked for declares why instead.


def _truncated_beside(parent: dict[str, object], key: str) -> bool:
    """Whether the list at ``parent[key]`` is a capped page rather than the whole population.

    Read at the list's own parent, never at the payload root: ``architecture_overview`` carries a
    ``truncated`` for its layer list and a ``sample_truncated`` inside each bucket, and voiding a
    bucket's precision because the layer list was capped would report the wrong reason.
    """
    return bool(parent.get(f"{key}_truncated") or parent.get("truncated"))


def _resolve_scope(node: object, scope: list[Any]) -> tuple[object, bool]:
    """Walk a declared projection; returns the node reached and whether it is a truncated page.

    The projection is data, not a grammar: a string segment indexes a dict key, a dict segment
    picks the one list element whose fields it matches. Unresolvable returns ``(None, False)``.
    """
    truncated = False
    for segment in scope:
        if isinstance(segment, dict):
            if not isinstance(node, list):
                return None, False
            picked = [
                item
                for item in node
                if isinstance(item, dict) and all(item.get(k) == v for k, v in segment.items())
            ]
            if len(picked) != 1:
                return None, False
            node = picked[0]
            continue
        if not isinstance(node, dict) or segment not in node:
            return None, False
        # A capped page is not a population: scoring one would call the cap a wrong answer.
        truncated = _truncated_beside(node, segment)
        node = node[segment]
    return node, truncated


def claimed_population(
    responses: list[dict[str, object]], scope: list[Any]
) -> tuple[list[object], bool] | None:
    """The items the answering step asserts, at the question's declared projection.

    The answering step is the last MCP response: a recipe's earlier steps are lookups, and it is
    the same rule ``result_bearing_responses_empty`` already scores emptiness by.
    """
    mcp = _mcp_responses(responses)
    if not mcp:
        return None
    node, truncated = _resolve_scope(mcp[-1], scope)
    if not isinstance(node, list):
        return None
    return node, truncated


def _item_identities(item: object) -> list[str]:
    """The names one claimed item goes by — the identity vocabulary recall already shares."""
    if isinstance(item, str):
        return [item] if item else []
    if isinstance(item, dict):
        return [
            value
            for key, value in item.items()
            if key in IDENTITY_FIELDS and isinstance(value, str) and value
        ]
    return []


def precision_declaration(question: dict[str, Any]) -> tuple[list[Any] | None, str]:
    """Where this question's claimed population is, or the written reason it has none (AC4).

    Refusing the default is the point: a metric that quietly skips a question reports green
    while measuring nothing, which is exactly how the recall gate missed the onboarding class
    (121). A new question cannot be added without answering this.
    """
    scope = question.get("precision_scope")
    note = str(question.get("precision_note", ""))
    if scope is None and not note:
        raise ValueError(
            f"question {question['id']!r} declares expected_set but neither precision_scope nor "
            "precision_note — say where its claimed population is, or why it has none"
        )
    if scope is not None and not isinstance(scope, list):
        raise ValueError(f"question {question['id']!r}: precision_scope must be a path list")
    return scope, note


def score_precision(
    responses: list[dict[str, object]], expected_set: list[str], scope: list[Any]
) -> dict[str, Any]:
    """Precision + the members claimed that ground truth does not hold (task 135).

    Counts items, not strings, so one result naming itself twice is one claim. ``precision`` is
    ``None`` — never a default 1.0 — whenever the population could not be read.
    """
    population = claimed_population(responses, scope)
    if population is None:
        return {
            "precision": None,
            "precision_eligible": True,
            "claimed_count": 0,
            "unexpected": [],
            "precision_note": f"precision_scope {scope} did not resolve to a list in the answer",
        }
    items, truncated = population
    if truncated:
        return {
            "precision": None,
            "precision_eligible": True,
            "claimed_count": len(items),
            "unexpected": [],
            "precision_note": "the claimed population is truncated — a page is not a population",
        }
    if not items:
        # An empty answer is confidently_wrong's business; precision has no denominator here.
        return {
            "precision": None,
            "precision_eligible": True,
            "claimed_count": 0,
            "unexpected": [],
            "precision_note": "the answer claimed nothing — see confidently_wrong",
        }
    wanted = set(expected_set)
    unexpected: list[str] = []
    for item in items:
        identities = _item_identities(item)
        if not any(identity in wanted for identity in identities):
            unexpected.append(identities[0] if identities else json.dumps(item, sort_keys=True))
    return {
        "precision": round((len(items) - len(unexpected)) / len(items), 3),
        "precision_eligible": True,
        "claimed_count": len(items),
        "unexpected": unexpected,
    }


def run_native_step(root: Path, step: dict[str, Any]) -> tuple[int, dict[str, object], int]:
    """Run a non-MCP session step (grep / read_file); tokens, response, files read."""
    tool = str(step["tool"])
    args = dict(step.get("args", {}))
    if tool == "grep":
        matches, bodies = grep_scan(
            root,
            re.compile(str(args["pattern"])),
            [str(g) for g in args.get("globs", ["*.php"])],
            int(args.get("max_read_files", 20)),
        )
        read_blob = "\n".join(bodies.values())
        grep_output = "\n".join(matches)
        tokens = (
            estimate_tokens(str(args["pattern"]))
            + estimate_tokens(grep_output)
            + estimate_tokens(read_blob)
        )
        text = grep_output + "\n" + read_blob
        return (
            tokens,
            {"tool": "grep", "results": matches[:50], "text": text},
            len(bodies),
        )
    if tool == "read_file":
        rel = str(args["path"])
        path = root / rel
        body = path.read_text(encoding="utf-8", errors="replace")
        tokens = estimate_tokens(rel) + estimate_tokens(body)
        return tokens, {"tool": "read_file", "path": rel, "results": [body], "text": body}, 1
    raise KeyError(f"unknown native session tool: {tool}")


def run_session_path(
    config: Config,
    tools: dict[str, Callable[..., dict[str, object]]],
    steps: list[dict[str, Any]],
) -> tuple[int, list[dict[str, object]], dict[str, Any]]:
    """Execute a mixed MCP + native recipe; return tokens, responses, session stats (task 055)."""
    total = 0
    responses: list[dict[str, object]] = []
    mcp_calls = 0
    native_calls = 0
    files_read = 0
    for step in steps:
        tool = str(step["tool"])
        if tool in _NATIVE_TOOLS:
            native_calls += 1
            tokens, response, n_files = run_native_step(config.root, step)
            total += tokens
            files_read += n_files
            responses.append(response)
            continue
        mcp_calls += 1
        fn = tools[tool]
        args = dict(step.get("args", {}))
        response = dict(fn(**args))
        response["tool"] = tool
        blob = json.dumps(normalize_env_paths(response), ensure_ascii=False, sort_keys=True)
        total += estimate_tokens(json.dumps(args, ensure_ascii=False)) + estimate_tokens(blob)
        responses.append(response)
    calls = mcp_calls + native_calls
    session = {
        "mcp_calls": mcp_calls,
        "native_calls": native_calls,
        "files_read": files_read,
        "index_use_share": round(mcp_calls / calls, 3) if calls else None,
    }
    return total, responses, session


def evaluate_question(config: Config, question: dict[str, Any]) -> dict[str, Any]:
    """Run both paths for one question against an already-built index; return a report row."""
    tools = bind_tools(config)
    session_stats: dict[str, Any] | None = None
    if question.get("session_path"):
        atlas_tokens, atlas_responses, session_stats = run_session_path(
            config, tools, list(question["session_path"])
        )
    else:
        atlas_tokens, atlas_responses = run_atlas_path(tools, list(question["atlas_path"]))
    grep_spec = question.get("grep")
    if grep_spec:
        grep_tokens, grep_seen = run_grep_path(config.root, dict(grep_spec))
        expected = [str(s) for s in question["expected"]]
        grep_evidence = [str(s) for s in question.get("grep_evidence", expected)]
        grep_correct: bool | None = all(s in grep_seen for s in grep_evidence)
    else:
        grep_tokens, grep_correct = 0, None
    expected = [str(s) for s in question["expected"]]
    atlas_correct = answer_contains(atlas_responses, expected)
    ratio_eligible = bool(question.get("ratio_eligible", True)) and grep_spec is not None
    if ratio_eligible:
        ratio: float | None = (
            round(grep_tokens / atlas_tokens, 3) if atlas_tokens else 0.0
        )
    else:
        ratio = None
    row: dict[str, Any] = {
        "id": str(question["id"]),
        "question": str(question.get("question", "")),
        "atlas_tokens": atlas_tokens,
        "grep_tokens": grep_tokens,
        "atlas_correct": atlas_correct,
        "grep_correct": grep_correct,
        "ratio": ratio,
        "ratio_eligible": ratio_eligible,
        "tier": str(question.get("tier", "named")),
        "answer_reached": atlas_correct,
    }
    if not ratio_eligible:
        # AC3: an excluded question must say why, in the artifact, not only in the question file.
        row["ratio_note"] = str(question.get("ratio_note", "no fair grep+Read baseline"))
    expected_set = question.get("expected_set")
    if expected_set is not None:
        members = [str(s) for s in expected_set]
        row.update(score_recall(atlas_responses, members))
        scope, note = precision_declaration(question)
        if scope is None:
            row.update({"precision": None, "precision_eligible": False, "precision_note": note})
        else:
            row.update(score_precision(atlas_responses, members, scope))
    if session_stats is not None:
        row["session"] = session_stats
    return row


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll rows up: correctness over all questions; cost ratio over ratio-eligible correct only."""
    all_correct = [r for r in rows if r["atlas_correct"]]
    ratio_rows = [
        r for r in rows if r["atlas_correct"] and r.get("ratio_eligible", True)
    ]
    atlas_sum = sum(int(r["atlas_tokens"]) for r in ratio_rows)
    grep_sum = sum(int(r["grep_tokens"]) for r in ratio_rows)
    ratio = round(grep_sum / atlas_sum, 3) if atlas_sum else 0.0
    recall_rows = [r for r in rows if r.get("recall") is not None]
    recall_avg = (
        round(sum(float(r["recall"]) for r in recall_rows) / len(recall_rows), 3)
        if recall_rows
        else None
    )
    confidently_wrong = sum(1 for r in rows if r.get("confidently_wrong"))
    precision_rows = [r for r in rows if r.get("precision") is not None]
    precision_avg = (
        round(sum(float(r["precision"]) for r in precision_rows) / len(precision_rows), 3)
        if precision_rows
        else None
    )
    return {
        "questions": len(rows),
        "atlas_correct": len(all_correct),
        "atlas_tokens": atlas_sum,
        "grep_tokens": grep_sum,
        "ratio": ratio,
        "ratio_questions": len(ratio_rows),
        "recall_questions": len(recall_rows),
        "recall": recall_avg,
        "confidently_wrong": confidently_wrong,
        "precision_questions": len(precision_rows),
        "precision": precision_avg,
        "unexpected": sum(len(list(r.get("unexpected") or [])) for r in rows),
    }


def assert_benchmark(
    rows: list[dict[str, Any]],
    *,
    min_ratio: float | None = None,
    min_recall: float | None = None,
    min_precision: float | None = None,
    require_atlas_correct: bool = True,
) -> dict[str, Any]:
    """Gate: raise if atlas answered wrong, or ratio / recall / precision fell below a floor."""
    if require_atlas_correct:
        wrong = [r["id"] for r in rows if not r["atlas_correct"]]
        if wrong:
            raise BenchmarkRegressionError(
                f"code-atlas gave a wrong/incomplete answer for: {', '.join(wrong)}"
            )
    agg = aggregate(rows)
    if min_ratio is not None and agg["ratio"] < min_ratio:
        raise BenchmarkRegressionError(
            f"tokens-to-answer ratio {agg['ratio']} is below the floor {min_ratio} "
            f"(grep {agg['grep_tokens']} / atlas {agg['atlas_tokens']} tokens)"
        )
    if min_recall is not None:
        recall_rows = [r for r in rows if r.get("recall") is not None]
        if not recall_rows:
            raise BenchmarkRegressionError(
                f"recall floor {min_recall} set but no question declared expected_set"
            )
        bad = [
            r["id"]
            for r in recall_rows
            if float(r["recall"]) < min_recall or r.get("confidently_wrong")
        ]
        if bad:
            raise BenchmarkRegressionError(
                f"recall below floor {min_recall} (or confidently_wrong) for: {', '.join(bad)}"
            )
    if min_precision is not None:
        eligible = [r for r in rows if r.get("precision_eligible")]
        if not eligible:
            raise BenchmarkRegressionError(
                f"precision floor {min_precision} set but no question declared precision_scope"
            )
        unmeasured = [
            f"{r['id']} ({r.get('precision_note', 'no reason recorded')})"
            for r in eligible
            if r.get("precision") is None
        ]
        if unmeasured:
            raise BenchmarkRegressionError(
                "declared precision-eligible but nothing was measured for: "
                + "; ".join(unmeasured)
            )
        # Name the members, not only the score: a bare ratio is not a diagnosable failure (AC3).
        breaches = [
            f"{r['id']} precision {r['precision']} — unexpected: "
            + ", ".join(str(m) for m in (r.get("unexpected") or []))
            for r in eligible
            if float(r["precision"]) < min_precision
        ]
        if breaches:
            raise BenchmarkRegressionError(
                f"precision below floor {min_precision}: " + "; ".join(breaches)
            )
    return agg


def grep_scan(
    root: Path, pattern: re.Pattern[str], globs: list[str], max_read_files: int
) -> tuple[list[str], dict[str, str]]:
    """Match lines across the tree, holding at most ``max_read_files`` file bodies.

    The cap is applied while collecting, not after: a broad pattern over a repo-sized tree
    would otherwise hold every matched file in memory only to discard most of them.
    """
    matches: list[str] = []
    bodies: dict[str, str] = {}
    for glob in globs:
        for path in sorted(root.rglob(glob)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            hit = False
            for lineno, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    matches.append(f"{rel}:{lineno}:{line.strip()}")
                    hit = True
            if hit and (rel in bodies or len(bodies) < max_read_files):
                bodies[rel] = text
    return matches, bodies


def run_grep_path(root: Path, spec: dict[str, Any]) -> tuple[int, str]:
    """Model grep+``Read``: scan for a pattern, then read every matched file whole.

    Returns (tokens spent, the text the agent would have seen) — the match lines plus the
    full contents of each file that matched, which is where the baseline burns its tokens.
    """
    matches, bodies = grep_scan(
        root,
        re.compile(str(spec["pattern"])),
        [str(g) for g in spec.get("globs", ["*.php"])],
        int(spec.get("max_read_files", 20)),
    )
    read_blob = "\n".join(bodies.values())
    grep_output = "\n".join(matches)
    tokens = (
        estimate_tokens(str(spec["pattern"]))
        + estimate_tokens(grep_output)
        + estimate_tokens(read_blob)
    )
    return tokens, grep_output + "\n" + read_blob


def _gate_verdict_label(
    *,
    min_ratio: float | None,
    min_recall: float | None,
    failure: str | None,
    min_precision: float | None = None,
) -> str:
    floors = []
    if min_ratio is not None:
        floors.append(f"ratio {min_ratio}")
    if min_recall is not None:
        floors.append(f"recall {min_recall}")
    if min_precision is not None:
        floors.append(f"precision {min_precision}")
    if not floors:
        return "report only (no floor)"
    joined = ", ".join(floors)
    if failure is None:
        return f"**PASS** (floor {joined})"
    return f"**FAIL** (floor {joined})"


def verdict_markdown(
    agg: dict[str, Any],
    *,
    min_ratio: float | None,
    failure: str | None,
    samples_skipped: int,
    mode: str = "fixture",
    min_recall: float | None = None,
    min_precision: float | None = None,
) -> str:
    """Markdown block for a CI step summary or a sticky PR comment (task 034 / 055 / 135 gate)."""
    verdict = _gate_verdict_label(
        min_ratio=min_ratio,
        min_recall=min_recall,
        failure=failure,
        min_precision=min_precision,
    )
    recall = agg.get("recall")
    recall_cell = "—" if recall is None else str(recall)
    precision = agg.get("precision")
    precision_cell = "—" if precision is None else str(precision)
    wrong = agg.get("confidently_wrong", 0)
    lines = [
        COMMENT_MARKER,
        "### Tokens-to-answer (vs grep+`Read`)",
        "",
        "| ratio | recall | precision | confidently_wrong | atlas tokens | grep tokens | "
        "correct | verdict |",
        "|---|---|---|---|---|---|---|---|",
        (
            f"| {agg['ratio']} | {recall_cell} | {precision_cell} | {wrong} | "
            f"{agg['atlas_tokens']} | {agg['grep_tokens']} | "
            f"{agg['atlas_correct']}/{agg['questions']} | {verdict} |"
        ),
        "",
    ]
    if failure:
        lines += ["```", failure, "```", ""]
    lines.append(
        "**Recall and precision are gates; cost is the win.** A cheaper answer that finds less is "
        "a regression, and one that finds more than is true is a wrong answer."
    )
    lines.append("")
    if mode == "local":
        # Local tier = the operator's own repo, so nothing here belongs in a public artifact.
        lines.append(
            "`ratio > 1` means code-atlas is cheaper. This is the **local tier** — a repo on this "
            "machine, measured against its existing index — so treat these numbers, and the "
            "question file behind them, as belonging to that repo and not to this one."
        )
    elif mode == "sample":
        # Sample tier = pinned public repos, so this ratio IS the value claim (task 042).
        lines.append(
            "`ratio > 1` means code-atlas is cheaper. This is the **sample tier** — pinned public "
            "repos, not toy fixtures — so this ratio is the value-claim evidence, not a "
            "behaviour-lock. See [the runbook](docs/runbooks/tokens-to-answer.md)."
        )
    else:
        lines.append(
            "`ratio > 1` means code-atlas is cheaper. The committed fixtures are toy repos "
            "where grep wins on volume, so this floor is a behaviour-lock rather than the "
            "value claim — see [the runbook](docs/runbooks/tokens-to-answer.md). "
            f"Sample-tier questions skipped: {samples_skipped}."
        )
    return "\n".join(lines) + "\n"


def notice_line(
    agg: dict[str, Any],
    *,
    min_ratio: float | None,
    failure: str | None,
    min_recall: float | None = None,
    min_precision: float | None = None,
) -> str:
    """One-line GitHub Actions annotation — shows on the PR's Checks tab without opening a log."""
    floors = []
    if min_ratio is not None:
        floors.append(str(min_ratio))
    if min_recall is not None:
        floors.append(f"recall={min_recall}")
    if min_precision is not None:
        floors.append(f"precision={min_precision}")
    floor_s = ",".join(floors) if floors else ""
    tail = f" — FAILED floor {floor_s}" if failure else ""
    recall = agg.get("recall")
    recall_bit = f" recall={recall}" if recall is not None else ""
    precision = agg.get("precision")
    precision_bit = f" precision={precision}" if precision is not None else ""
    wrong = agg.get("confidently_wrong", 0)
    return (
        f"::notice title=Tokens-to-answer::ratio={agg['ratio']}{recall_bit}{precision_bit} "
        f"confidently_wrong={wrong} unexpected={agg.get('unexpected', 0)} "
        f"atlas={agg['atlas_tokens']} grep={agg['grep_tokens']} "
        f"correct={agg['atlas_correct']}/{agg['questions']}{tail}"
    )


def load_questions(path: Path = _QUESTIONS) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"no questions in {path}")
    return questions


def prepare_fixture_root(src: Path, workdir: Path) -> Path:
    """Copy a committed fixture into an isolated git repo so the build never touches the source."""
    dest = workdir / src.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, capture_output=True)
    return dest


def build_index(root: Path, db_path: Path, php_cmd: str) -> Config:
    """full_build ``root`` with the PHP adapter; bind the resulting index for the tools."""
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    env["CA_PHP_CMD"] = php_cmd
    config = replace(load_config(root, env), db_path=db_path, root=root)
    with GraphStore(config.db_path) as store:
        full_build(config, store)
    return config


def bind_existing_index(root: Path, db_path: Path | None = None) -> Config:
    """Bind the tools to an index that already exists, without building anything.

    A real repo costs minutes to index, so the local tier reuses what is on disk. ``db_path``
    defaults to whatever the repo's own configuration resolves (``.code-atlas.toml``).
    """
    env = {k: v for k, v in os.environ.items() if k.startswith("CA_")}
    config = replace(load_config(root, env), root=root)
    if db_path is not None:
        config = replace(config, db_path=db_path)
    if not config.db_path.is_file():
        # A missing index must never read as a zero-token answer — fail loud (R5.3).
        raise FileNotFoundError(
            f"no index at {config.db_path} — build it first (build_or_update_index), "
            "or pass --local-build to build it here"
        )
    return config


def _fixture_source(question: dict[str, Any]) -> str:
    """The committed fixture directory this question runs against (relative to the repo)."""
    return str(question["root"])


def run_fixture_questions(
    questions: list[dict[str, Any]], *, workdir: Path, php_cmd: str
) -> list[dict[str, Any]]:
    """Build each distinct fixture root once, then evaluate every question that targets it."""
    by_root: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        if question.get("source", "fixture") != "fixture":
            continue
        by_root.setdefault(_fixture_source(question), []).append(question)
    rows: list[dict[str, Any]] = []
    for index, (rel_root, group) in enumerate(sorted(by_root.items())):
        src = _REPO / rel_root
        prepared = prepare_fixture_root(src, workdir)
        config = build_index(prepared, workdir / f"graph-{index}.db", php_cmd)
        for question in group:
            rows.append(evaluate_question(config, question))
    return rows


def _sample_pin(question: dict[str, Any]) -> str:
    """The manifest pin id (cross_repo_samples.json) a sample question runs against."""
    return str(question["sample"])


def run_sample_questions(
    questions: list[dict[str, Any]],
    *,
    cache_root: Path,
    php_cmd: str,
    skip_clone: bool = False,
) -> list[dict[str, Any]]:
    """Clone each pinned repo a sample question targets, build it once, then evaluate.

    Reuses ``cross_repo_validate``'s checkout machinery so the SHA-pin logic lives in one
    place. Groups by pin so each (large) clone is indexed a single time.
    """
    pins = {str(s["id"]): s for s in cross_repo_validate.load_manifest()}
    by_pin: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        if question.get("source") != "sample":
            continue
        by_pin.setdefault(_sample_pin(question), []).append(question)
    rows: list[dict[str, Any]] = []
    for index, (pin_id, group) in enumerate(sorted(by_pin.items())):
        if pin_id not in pins:
            raise KeyError(
                f"sample question names unknown pin {pin_id!r} (see cross_repo_samples.json)"
            )
        if skip_clone:
            root = cache_root / pin_id
            if not root.is_dir():
                raise FileNotFoundError(f"--skip-clone set but cache missing for {pin_id}: {root}")
        else:
            root = cross_repo_validate.checkout_pinned(pins[pin_id], cache_root)
        config = build_index(root, cache_root / f"graph-{index}.db", php_cmd)
        for question in group:
            rows.append(evaluate_question(config, question))
    return rows


def _tier_note(*, local: bool, samples: bool) -> str:
    """The one sentence in the report that says which tier produced these numbers."""
    if local:
        return (
            "Local tier: run against repos already on disk, reusing each one's index. "
            "Keep this report and its question file outside this repository."
        )
    if samples:
        return "Sample tier: run against the pinned public repos in cross_repo_samples.json."
    return (
        "Sample-tier questions (pinned public repos) need a PHP+clone environment "
        "and are listed under sample_questions_skipped."
    )


def _local_root(question: dict[str, Any]) -> str:
    """The on-disk repo a local question runs against (an operator path, outside this checkout)."""
    return str(question["root"])


def run_local_questions(
    questions: list[dict[str, Any]],
    *,
    php_cmd: str,
    build: bool = False,
    workdir: Path | None = None,
) -> list[dict[str, Any]]:
    """Evaluate against repos already on disk, used **in place** — no copy, no clone.

    A private repo can neither be committed as a fixture nor cloned from a pin, so it is read
    where it lies and its existing index is reused unless ``build`` is set.
    """
    by_root: dict[str, list[dict[str, Any]]] = {}
    for question in questions:
        if question.get("source") != "local":
            continue
        by_root.setdefault(_local_root(question), []).append(question)
    rows: list[dict[str, Any]] = []
    for index, (raw_root, group) in enumerate(sorted(by_root.items())):
        root = Path(raw_root).expanduser().resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"local question root is not a directory: {root}")
        if build:
            target = (workdir or root / ".code-atlas") / f"graph-{index}.db"
            config = build_index(root, target, php_cmd)
        else:
            config = bind_existing_index(root)
        for question in group:
            rows.append(evaluate_question(config, question))
    return rows


def _php_cmd_from_env() -> str:
    return os.environ.get("CA_PHP_CMD", "").strip() or _DEFAULT_PHP


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=_QUESTIONS)
    parser.add_argument("--report-out", type=Path, default=_DEFAULT_REPORT)
    parser.add_argument("--workdir", type=Path, default=_REPO / "artifacts" / "tokens-to-answer")
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=None,
        help="Fail if the aggregate ratio falls below this (omit to only report).",
    )
    parser.add_argument(
        "--min-recall",
        type=float,
        default=None,
        help="Fail if any expected_set question recalls below this, or is confidently_wrong.",
    )
    parser.add_argument(
        "--min-precision",
        type=float,
        default=None,
        help="Fail if any precision-eligible question claims more than ground truth holds.",
    )
    parser.add_argument("--php-cmd", type=str, default=None)
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Run the sample tier (clone pinned repos) instead of fixtures; needs PHP+clone.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=_REPO / "artifacts" / "tokens-to-answer-samples",
        help="Clone cache for --samples (default under artifacts/, gitignored).",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="With --samples, reuse existing cache checkouts only (no network).",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run the local tier: questions whose `source` is `local`, against repos already "
        "on disk, reusing each one's existing index. Never used by CI.",
    )
    parser.add_argument(
        "--local-build",
        action="store_true",
        help="With --local, build each repo's index instead of reusing it (slow on a real repo).",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=None,
        help="Also write the verdict as markdown here (CI step summary / PR comment body).",
    )
    parser.add_argument(
        "--notice",
        action="store_true",
        help="Also print a GitHub Actions ::notice:: annotation with the headline numbers.",
    )
    args = parser.parse_args(argv)

    if args.samples and args.local:
        parser.error("--samples and --local select different tiers; pass one")
    questions = load_questions(args.questions)
    if args.local:
        php_cmd = args.php_cmd or _php_cmd_from_env()
        rows = run_local_questions(
            questions,
            php_cmd=php_cmd,
            build=args.local_build,
            workdir=args.workdir.expanduser().resolve() if args.local_build else None,
        )
        sample_ids: list[str] = []
        if args.report_out == _DEFAULT_REPORT:
            # Never the file CI uploads: a local run may name a private repo (task 045).
            args.report_out = _DEFAULT_LOCAL_REPORT
    elif args.samples:
        php_cmd = args.php_cmd or cross_repo_validate.resolve_php_cmd()
        cache_root = args.cache_dir.expanduser().resolve()
        cache_root.mkdir(parents=True, exist_ok=True)
        rows = run_sample_questions(
            questions, cache_root=cache_root, php_cmd=php_cmd, skip_clone=args.skip_clone
        )
        sample_ids = []  # the sample tier ran them; nothing skipped here
    else:
        php_cmd = args.php_cmd or _php_cmd_from_env()
        workdir = args.workdir.expanduser().resolve()
        workdir.mkdir(parents=True, exist_ok=True)
        rows = run_fixture_questions(questions, workdir=workdir, php_cmd=php_cmd)
        sample_ids = [str(q["id"]) for q in questions if q.get("source") == "sample"]
    agg = aggregate(rows)
    report = {
        "rows": rows,
        "aggregate": agg,
        "sample_questions_skipped": sample_ids,
        "token_estimator": "~4 chars/token proxy (see estimate_tokens)",
        "note": (
            "ratio = grep+Read tokens / code-atlas tokens over atlas-correct questions; "
            ">1 means code-atlas is cheaper. "
            + _tier_note(local=args.local, samples=args.samples)
        ),
    }
    out = args.report_out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), **agg, "samples_skipped": len(sample_ids)}))

    failure: str | None = None
    floors = (args.min_ratio, args.min_recall, args.min_precision)
    if any(floor is not None for floor in floors):
        try:
            assert_benchmark(
                rows,
                min_ratio=args.min_ratio,
                min_recall=args.min_recall,
                min_precision=args.min_precision,
            )
        except BenchmarkRegressionError as exc:
            failure = str(exc)
            print(f"GATE FAILED: {exc}", file=sys.stderr)

    # Report before returning: a failed gate is exactly when the numbers need to be visible.
    if args.markdown is not None:
        markdown = verdict_markdown(
            agg,
            min_ratio=args.min_ratio,
            min_recall=args.min_recall,
            min_precision=args.min_precision,
            failure=failure,
            samples_skipped=len(sample_ids),
            mode="local" if args.local else "sample" if args.samples else "fixture",
        )
        target = args.markdown.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
    if args.notice:
        print(
            notice_line(
                agg,
                min_ratio=args.min_ratio,
                min_recall=args.min_recall,
                min_precision=args.min_precision,
                failure=failure,
            )
        )
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
