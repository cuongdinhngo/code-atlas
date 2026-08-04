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
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from code_atlas.config import Config, load_config  # noqa: E402
from code_atlas.indexer import full_build  # noqa: E402
from code_atlas.store import GraphStore  # noqa: E402
from code_atlas.tools import (  # noqa: E402
    find_callers,
    find_implementations,
    find_references,
    get_index_status,
    include_graph,
    read_symbol,
    search_symbol,
)

_QUESTIONS = _REPO / "scripts" / "tokens_to_answer_questions.json"
_DEFAULT_REPORT = _REPO / "artifacts" / "tokens-to-answer-report.json"
_DEFAULT_PHP = shlex.join(["php", str(_REPO / "adapters" / "php" / "index.php"), "--server"])

# The tools a recipe may call, bound per repo. get_index_status needs the servable names.
_TOOL_NAMES = (
    get_index_status.NAME,
    search_symbol.NAME,
    read_symbol.NAME,
    find_callers.NAME,
    find_references.NAME,
    find_implementations.NAME,
    include_graph.NAME,
)


class BenchmarkRegressionError(AssertionError):
    """The tokens-to-answer gate failed: atlas got an answer wrong, or the ratio regressed."""


def estimate_tokens(text: str) -> int:
    """Deterministic ~4-chars-per-token proxy — NOT a real tokenizer.

    Applied identically to both paths, so the *ratio* is meaningful without a model
    dependency. Swap in a real tokenizer later without changing any caller.
    """
    if not text:
        return 0
    return -(-len(text) // 4)  # ceil division


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
        blob = json.dumps(response, ensure_ascii=False, sort_keys=True)
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


def run_grep_path(root: Path, spec: dict[str, Any]) -> tuple[int, str]:
    """Model grep+``Read``: scan for a pattern, then read every matched file whole.

    Returns (tokens spent, the text the agent would have seen) — the match lines plus the
    full contents of each file that matched, which is where the baseline burns its tokens.
    """
    pattern = re.compile(str(spec["pattern"]))
    globs = [str(g) for g in spec.get("globs", ["*.php"])]
    max_files = int(spec.get("max_read_files", 20))
    matches: list[str] = []
    read_files: dict[str, str] = {}
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
            if hit:
                read_files[rel] = text
    read_blob = "\n".join(list(read_files.values())[:max_files])
    grep_output = "\n".join(matches)
    tokens = (
        estimate_tokens(str(spec["pattern"]))
        + estimate_tokens(grep_output)
        + estimate_tokens(read_blob)
    )
    return tokens, grep_output + "\n" + read_blob


def evaluate_question(config: Config, question: dict[str, Any]) -> dict[str, Any]:
    """Run both paths for one question against an already-built index; return a report row."""
    tools = bind_tools(config)
    atlas_tokens, atlas_responses = run_atlas_path(tools, list(question["atlas_path"]))
    grep_tokens, grep_seen = run_grep_path(config.root, dict(question["grep"]))
    expected = [str(s) for s in question["expected"]]
    grep_evidence = [str(s) for s in question.get("grep_evidence", expected)]
    atlas_correct = answer_contains(atlas_responses, expected)
    grep_correct = all(s in grep_seen for s in grep_evidence)
    ratio = round(grep_tokens / atlas_tokens, 3) if atlas_tokens else 0.0
    return {
        "id": str(question["id"]),
        "question": str(question.get("question", "")),
        "atlas_tokens": atlas_tokens,
        "grep_tokens": grep_tokens,
        "atlas_correct": atlas_correct,
        "grep_correct": grep_correct,
        "ratio": ratio,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll rows up over the questions code-atlas answered correctly (the fair comparison set)."""
    correct = [r for r in rows if r["atlas_correct"]]
    atlas_sum = sum(int(r["atlas_tokens"]) for r in correct)
    grep_sum = sum(int(r["grep_tokens"]) for r in correct)
    ratio = round(grep_sum / atlas_sum, 3) if atlas_sum else 0.0
    return {
        "questions": len(rows),
        "atlas_correct": len(correct),
        "atlas_tokens": atlas_sum,
        "grep_tokens": grep_sum,
        "ratio": ratio,
    }


def assert_benchmark(
    rows: list[dict[str, Any]], *, min_ratio: float, require_atlas_correct: bool = True
) -> dict[str, Any]:
    """Gate: raise if atlas answered anything wrong, or the aggregate ratio fell below the floor."""
    if require_atlas_correct:
        wrong = [r["id"] for r in rows if not r["atlas_correct"]]
        if wrong:
            raise BenchmarkRegressionError(
                f"code-atlas gave a wrong/incomplete answer for: {', '.join(wrong)}"
            )
    agg = aggregate(rows)
    if agg["ratio"] < min_ratio:
        raise BenchmarkRegressionError(
            f"tokens-to-answer ratio {agg['ratio']} is below the floor {min_ratio} "
            f"(grep {agg['grep_tokens']} / atlas {agg['atlas_tokens']} tokens)"
        )
    return agg


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
    parser.add_argument("--php-cmd", type=str, default=None)
    args = parser.parse_args(argv)

    questions = load_questions(args.questions)
    sample_ids = [str(q["id"]) for q in questions if q.get("source") == "sample"]
    workdir = args.workdir.expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    php_cmd = args.php_cmd or _php_cmd_from_env()

    rows = run_fixture_questions(questions, workdir=workdir, php_cmd=php_cmd)
    agg = aggregate(rows)
    report = {
        "rows": rows,
        "aggregate": agg,
        "sample_questions_skipped": sample_ids,
        "token_estimator": "~4 chars/token proxy (see estimate_tokens)",
        "note": (
            "ratio = grep+Read tokens / code-atlas tokens over atlas-correct questions; "
            ">1 means code-atlas is cheaper. Sample-tier questions (pinned public repos) "
            "need a PHP+clone environment and are listed under sample_questions_skipped."
        ),
    }
    out = args.report_out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), **agg, "samples_skipped": len(sample_ids)}))

    if args.min_ratio is not None:
        try:
            assert_benchmark(rows, min_ratio=args.min_ratio)
        except BenchmarkRegressionError as exc:
            print(f"GATE FAILED: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
