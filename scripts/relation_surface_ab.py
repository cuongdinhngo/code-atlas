#!/usr/bin/env python3
"""Task 037 A/B: three relation tools vs one ``find_relations`` — decided by tokens, not taste.

The 034 harness counts ``args + response`` per call, which is **blind** to the only thing
consolidation actually trades: the tool *schema* an agent carries in context for the whole session.
Three tools ship three names, three descriptions and three parameter schemas; one ships one. So this
script measures both terms and lets the numbers decide (ticket 037 C: "held behind the benchmark").

    python scripts/relation_surface_ab.py                 # report
    python scripts/relation_surface_ab.py --json out.json  # also write the record

Surface B dispatches to the real tools, so its per-call response bytes are real, not modelled.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
# Both entries so the module imports the same whether run as a script or loaded by a test.
for _path in (_REPO, _HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import tokens_to_answer as harness  # noqa: E402

from code_atlas.config import Config  # noqa: E402
from code_atlas.tools import find_callers, find_implementations, find_references  # noqa: E402

SURFACE_A = ("find_callers", "find_references", "find_implementations")
SURFACE_B = ("find_relations",)

Relation = Literal["callers", "references", "implementations"]


def make_find_relations(config: Config) -> Callable[..., dict[str, object]]:
    """The consolidation candidate: one tool, one ``relation`` argument, three behaviours.

    Deliberately a thin dispatcher over the shipped tools — the A/B is about surface cost, so
    the responses must be real. Its docstring is as long as it has to be: a merged tool must
    document all three relations, and that prose is the cost consolidation claims to save.
    """

    callers = find_callers.create(config)
    references = find_references.create(config)
    implementations = find_implementations.create(config)

    def find_relations(
        qname: str,
        relation: Relation = "callers",
        detail_level: str = "standard",
        depth: int = 1,
        include_source: bool = False,
    ) -> dict[str, object]:
        """Relationships targeting ``qname``, selected by ``relation``.

        ``callers`` — who CALLS or NEWs it; honours ``depth`` (BFS over CALLS/NEW, RESOLVED-only
        frontier) and reports ``frontier_skipped_non_resolved`` counts.
        ``references`` — every resolved edge targeting it, any kind the resolver links.
        ``implementations`` — EXTENDS/IMPLEMENTS subtypes only.
        ``depth`` applies to ``callers`` and is ignored by the other two. ``include_source`` adds
        each site's own source line (capped) for ``callers`` and ``references``. Every response
        carries ``reason`` and ``total_count`` so an empty list is never mistaken for absence.
        """
        if relation == "callers":
            return callers(
                qname, depth=depth, detail_level=detail_level, include_source=include_source
            )
        if relation == "references":
            return references(
                qname, detail_level=detail_level, include_source=include_source
            )
        if relation == "implementations":
            return implementations(qname, detail_level=detail_level)
        raise ValueError(f"relation must be callers|references|implementations, got {relation!r}")

    return find_relations


def schema_tokens(name: str, fn: Callable[..., object]) -> int:
    """Tokens an agent carries for one tool: its name, its description, its parameter schema.

    A proxy over the same ``~4 chars/token`` estimator the 034 harness declares — sound for a
    *comparison* between two surfaces, which is all this decides.
    """
    doc = inspect.getdoc(fn) or ""
    params = {
        param.name: {
            "type": _json_type(param.annotation),
            "required": param.default is inspect.Parameter.empty,
        }
        for param in inspect.signature(fn).parameters.values()
    }
    blob = f"{name}\n{doc}\n{json.dumps(params, sort_keys=True)}"
    return harness.estimate_tokens(blob)


def _json_type(annotation: object) -> str:
    text = str(annotation)
    if "int" in text:
        return "integer"
    if "bool" in text:
        return "boolean"
    return "string"


def relation_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The committed questions whose recipe calls one of the three relation tools."""
    picked = []
    for question in questions:
        tools = [str(step["tool"]) for step in question["atlas_path"]]
        if any(tool in SURFACE_A for tool in tools):
            picked.append(question)
    return picked


def _as_relation_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rewrite a recipe's relation call into the equivalent ``find_relations`` call."""
    out = []
    for step in steps:
        tool = str(step["tool"])
        if tool not in SURFACE_A:
            out.append(step)
            continue
        args = dict(step.get("args", {}))
        args["relation"] = tool.removeprefix("find_")
        out.append({"tool": "find_relations", "args": args})
    return out


def measure(config: Config, questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-call + schema tokens for both surfaces over the same questions."""
    tools = harness.bind_tools(config)
    tools["find_relations"] = make_find_relations(config)

    a_calls = 0
    b_calls = 0
    for question in questions:
        steps = question["atlas_path"]
        a_calls += harness.run_atlas_path(tools, steps)[0]
        b_calls += harness.run_atlas_path(tools, _as_relation_steps(steps))[0]

    a_schema = sum(schema_tokens(name, tools[name]) for name in SURFACE_A)
    b_schema = sum(schema_tokens(name, tools[name]) for name in SURFACE_B)
    return {
        "questions": len(questions),
        "surface_a": {"tools": list(SURFACE_A), "schema_tokens": a_schema, "call_tokens": a_calls},
        "surface_b": {"tools": list(SURFACE_B), "schema_tokens": b_schema, "call_tokens": b_calls},
        "schema_delta": b_schema - a_schema,
        "call_delta": b_calls - a_calls,
    }


def verdict(result: dict[str, Any], *, sessions: int = 1) -> dict[str, Any]:
    """Decide, given how many relation questions one session asks.

    Schema cost is paid **once** per session; per-call cost is paid per question. So the break-even
    is where a schema saving stops covering the extra per-call argument bytes.
    """
    schema_delta = int(result["schema_delta"])
    call_delta = int(result["call_delta"])
    total_delta = schema_delta + call_delta * sessions
    if total_delta < 0:
        winner = "surface_b"
    elif total_delta > 0:
        winner = "surface_a"
    else:
        winner = "tie"
    return {
        "sessions": sessions,
        "total_delta": total_delta,
        "winner": winner,
        "break_even_calls": None if call_delta <= 0 else -schema_delta / call_delta,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=None)
    parser.add_argument("--workdir", type=Path, default=_REPO / "artifacts" / "relation-surface-ab")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--php-cmd", type=str, default=None)
    args = parser.parse_args(argv)

    questions = harness.load_questions(
        args.questions if args.questions is not None else harness._QUESTIONS
    )
    picked = relation_questions([q for q in questions if q.get("source") == "fixture"])
    if not picked:
        raise ValueError("no fixture question exercises a relation tool")

    workdir = args.workdir.expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    root = harness.prepare_fixture_root(_REPO / str(picked[0]["root"]), workdir)
    config = harness.build_index(
        root, workdir / "graph.db", args.php_cmd or harness._php_cmd_from_env()
    )

    result = measure(config, picked)
    result["verdict"] = verdict(result, sessions=len(picked))
    # One data point hides the crossover; the sweep is what the decision is actually read off.
    result["sweep"] = [verdict(result, sessions=n) for n in (1, 5, 10, 20, 50, 100)]
    print(json.dumps(result, sort_keys=True))
    if args.json is not None:
        out = args.json.expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
