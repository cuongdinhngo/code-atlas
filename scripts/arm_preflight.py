#!/usr/bin/env python3
"""Prove a 074 benchmark arm is the arm it claims to be, before and after each cell.

The 2026-08-27 run bought one $5.58 granted cell that was not granted: all 22 code-atlas tools
arrived as a `deferred_tools_delta` attachment — names without schemas — the session never called
`ToolSearch`, and it made 0 index calls in 68. That is a fact about tool delivery, not about the
index, and the protocol had no way to catch it except by spending the money first.

Two modes, both cheap:

    python scripts/arm_preflight.py probe --mcp-config granted.json --repo /path/to/anchor
    python scripts/arm_preflight.py audit cell1.jsonl --arm granted

`probe` runs one throwaway coached session against the granted config and reports whether a
code-atlas tool was reachable at all, and whether it took a `ToolSearch` to reach it. It is a
DELIVERY test, not a cell: the coaching is deliberate and it is never scored. `audit` reads a
counted cell's saved transcript and applies the two arm rules — a granted cell with 0 index calls
is `void`, a denied cell with any index call is contaminated.

Protocol: `docs/benchmarks/074_mechanism-question.md`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

ATLAS_PREFIX = "mcp__code-atlas__"
TOOL_SEARCH = "ToolSearch"
STATUS_TOOL = f"{ATLAS_PREFIX}get_index_status"

# The "Product under test" rows a cell is not comparable without (protocol, 2026-09-18).
STATUS_FIELDS = ("server_build", "server_version", "staleness", "dirty_indexed_files", "indexed")

# Coaching is correct here and nowhere else: the probe asks whether the tool can be called at all,
# so it names the tool and the escape hatch. A counted cell gets neither.
PROBE_PROMPT = (
    "Call the code-atlas get_index_status tool and quote its raw result verbatim. "
    "Use no other tool to answer. If its schema is not loaded, load it with ToolSearch first "
    "and say that you had to."
)

# The reachability probe names no tool and no escape hatch: it asks whether an ordinary
# navigation question reaches the index on its own. Not the frozen question, and never scored.
REACH_PROMPT = (
    "Explain how this codebase routes an incoming request to the code that produces the response. "
    "Name the mechanism and cite file:line for each step. Do not modify anything."
)

READ_ONLY_TOOLS = ("Read", "Grep", "Glob", "ToolSearch", "mcp__code-atlas")

EXIT_OK = 0
EXIT_DEFERRED = 1
EXIT_VOID = 2


def iter_tool_uses(blob: object) -> list[str]:
    """Every `tool_use` name anywhere in the structure — the envelope differs by output format."""
    found: list[str] = []
    if isinstance(blob, dict):
        if blob.get("type") == "tool_use" and isinstance(blob.get("name"), str):
            found.append(blob["name"])
        for value in blob.values():
            found.extend(iter_tool_uses(value))
    elif isinstance(blob, list):
        for item in blob:
            found.extend(iter_tool_uses(item))
    return found


def parse_transcript(text: str) -> list[str]:
    """Tool-call names in order, from `--output-format json` or newline-delimited `stream-json`."""
    stripped = text.strip()
    if not stripped:
        return []
    try:
        return iter_tool_uses(json.loads(stripped))
    except json.JSONDecodeError:
        pass
    names: list[str] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            names.extend(iter_tool_uses(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return names


def find_status(blob: object) -> dict[str, object] | None:
    """The `get_index_status` payload, wherever the transcript envelope buried it."""
    if isinstance(blob, dict):
        if "server_build" in blob and "staleness" in blob:
            return blob
        for value in blob.values():
            if isinstance(value, str) and "server_build" in value:
                try:
                    inner = json.loads(value)
                except json.JSONDecodeError:
                    continue
                if isinstance(inner, dict):
                    return inner
            hit = find_status(value)
            if hit is not None:
                return hit
    elif isinstance(blob, list):
        for item in blob:
            hit = find_status(item)
            if hit is not None:
                return hit
    return None


def status_from_transcript(text: str) -> dict[str, object] | None:
    """Same two envelopes `parse_transcript` handles, looking for the status payload instead."""
    for chunk in (text.strip(), *text.strip().splitlines()):
        if not chunk.strip():
            continue
        try:
            hit = find_status(json.loads(chunk))
        except json.JSONDecodeError:
            continue
        if hit is not None:
            return hit
    return None


def classify(names: list[str], arm: str, coached: bool = True) -> tuple[int, str]:
    """The two arm rules the 2026-08-27 abort earned, applied to one cell's tool-call sequence.

    `coached=False` is the reachability probe: there, `ToolSearch` before the first index call is
    the arm working, not failing — the session found the tools with no prompting.
    """
    atlas = [n for n in names if n.startswith(ATLAS_PREFIX)]
    if not coached:
        if not atlas:
            return EXIT_VOID, (
                f"UNREACHABLE — an uncoached session made 0 code-atlas calls in {len(names)} tool "
                "calls. Deferred delivery does block the arm; there is no granted arm to buy."
            )
        searched = TOOL_SEARCH in names[: names.index(atlas[0])]
        how = f"via `{TOOL_SEARCH}`" if searched else "with resident schemas"
        return EXIT_OK, (
            f"REACHABLE {how} — an uncoached session made {len(atlas)} code-atlas call(s) in "
            f"{len(names)} tool calls. Deferred delivery is not disqualifying on its own."
        )
    if arm == "denied":
        if atlas:
            return EXIT_VOID, f"CONTAMINATED — denied arm made {len(atlas)} code-atlas call(s)"
        return EXIT_OK, f"denied arm clean — 0 code-atlas calls in {len(names)} tool calls"
    if not atlas:
        return EXIT_VOID, (
            f"VOID — granted arm made 0 code-atlas calls in {len(names)} tool calls. "
            "Not a datapoint; fix tool delivery before spending another cell."
        )
    first_atlas = names.index(atlas[0])
    if TOOL_SEARCH in names[:first_atlas]:
        return EXIT_DEFERRED, (
            f"DEFERRED DELIVERY — {len(atlas)} code-atlas call(s), but `{TOOL_SEARCH}` ran first. "
            "Schemas are not resident; an uncoached cell may never reach the tools."
        )
    return EXIT_OK, f"granted arm live — {len(atlas)} code-atlas call(s) in {len(names)} tool calls"


def render(
    names: list[str],
    arm: str,
    status: dict[str, object] | None = None,
    coached: bool = True,
) -> tuple[int, str]:
    """The report is the evidence pasted into the protocol's results table, so it counts by name."""
    code, verdict = classify(names, arm, coached)
    lines = [f"arm: {arm}", f"tool calls: {len(names)}"]
    for name, count in sorted(Counter(names).items()):
        lines.append(f"  {count:>3}  {name}")
    if status is not None:
        lines.append("index (record these — a cell without them is not comparable):")
        for field in STATUS_FIELDS:
            lines.append(f"  {field}: {status.get(field, '<absent>')}")
    lines.append(f"VERDICT: {verdict}")
    return code, "\n".join(lines)


def run_probe(
    mcp_config: Path,
    repo: Path,
    model: str | None,
    save: Path | None,
    uncoached: bool = False,
) -> tuple[int, str]:
    """One throwaway session — the cheapest thing that can say whether the arm exists at all."""
    argv = [
        "claude", "-p", REACH_PROMPT if uncoached else PROBE_PROMPT,
        "--output-format", "stream-json", "--verbose",
        "--mcp-config", str(mcp_config), "--strict-mcp-config",
        "--allowed-tools", *(READ_ONLY_TOOLS if uncoached else (STATUS_TOOL, TOOL_SEARCH)),
        "--disallowed-tools", "Edit", "Write", "Bash",
        "--max-turns", "30" if uncoached else "6",
    ]
    if model:
        argv += ["--model", model]
    proc = subprocess.run(argv, cwd=repo, capture_output=True, text=True)
    if save:
        save.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0 and not proc.stdout.strip():
        return EXIT_VOID, f"probe failed to run (rc={proc.returncode})\n{proc.stderr.strip()}"
    code, report = render(
        parse_transcript(proc.stdout),
        "granted",
        status_from_transcript(proc.stdout),
        coached=not uncoached,
    )
    kind = "reachability probe (uncoached)" if uncoached else "probe"
    return code, f"{kind} against {mcp_config} in {repo}\n{report}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)

    probe = sub.add_parser("probe", help="prove the granted arm's tools arrive callable")
    probe.add_argument("--mcp-config", type=Path, required=True)
    probe.add_argument("--repo", type=Path, default=Path.cwd())
    probe.add_argument("--model", default=None)
    probe.add_argument("--save", type=Path, default=None, help="write the raw transcript here")
    probe.add_argument(
        "--uncoached",
        action="store_true",
        help="ask an ordinary navigation question instead: does the arm get reached unprompted?",
    )

    audit = sub.add_parser("audit", help="apply the arm rules to a counted cell's transcript")
    audit.add_argument("transcript", type=Path)
    audit.add_argument("--arm", choices=["granted", "denied"], required=True)

    args = parser.parse_args(argv)
    if args.mode == "probe":
        code, report = run_probe(
            args.mcp_config, args.repo, args.model, args.save, args.uncoached
        )
    else:
        raw = args.transcript.read_text(encoding="utf-8")
        code, report = render(parse_transcript(raw), args.arm, status_from_transcript(raw))
    print(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
