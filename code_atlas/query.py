"""``code-atlas query`` — ask the read tools from a shell, with no agent in the loop (task 382).

Each call goes through this repo's own server, in process, so a shell answer is the MCP payload for
the same arguments at the same revision. Shell calls bump no fit or cost counter: those count what
an agent asked (260, 379), and one batch would drown them.

``--verify-claim`` / ``--verify-claims`` re-ask a signed claim's ``call`` at the current index and
answer ``holds``, ``changed`` (naming each key that moved) or ``unverifiable`` (task 383).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Iterable
from pathlib import Path

from fastmcp import Client, FastMCP

from code_atlas.tools import build_or_update_index, claim, generate_onboarding
from code_atlas.tools.schema_guard import SCHEMA_MISMATCH

OK = 0
FAILED = 1
USAGE = 2
# A verified claim that did not hold, so a lint step fails on it (383).
NOT_HELD = 3

HOLDS = "holds"
CHANGED = "changed"
UNVERIFIABLE = "unverifiable"

# Writers keep their own entry points and locking: code-atlas-build, the MCP tool.
REFUSED_TOOLS: frozenset[str] = frozenset({build_or_update_index.NAME, generate_onboarding.NAME})

Request = tuple[str, dict[str, object]]


class UsageError(Exception):
    """A request this command cannot ask; nothing for it reaches the index."""


def _say(message: str) -> None:
    print(f"code-atlas query: {message}", file=sys.stderr)


def _project_root() -> Path:
    raw = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(raw).resolve()


def _request(tool: object, args: object, served: tuple[str, ...], where: str) -> Request:
    if not isinstance(tool, str) or not tool:
        raise UsageError(f"{where}: `tool` must be a tool name")
    if tool in REFUSED_TOOLS:
        raise UsageError(f"{where}: {tool} writes the index; use its own entry point")
    if tool not in served:
        raise UsageError(f"{where}: unknown tool {tool!r} (served: {', '.join(served)})")
    if not isinstance(args, dict):
        raise UsageError(f"{where}: args must be a JSON object")
    return tool, args


def parse_batch(lines: Iterable[str], served: tuple[str, ...]) -> list[Request]:
    """Every line checked before any is asked, so a bad line 900 never leaves 899 half-answered."""
    requests: list[Request] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise UsageError(f"line {number}: not JSON ({error.msg})") from None
        if not isinstance(entry, dict):
            raise UsageError(f"line {number}: expected {{\"tool\": ..., \"args\": {{...}}}}")
        requests.append(
            _request(entry.get("tool"), entry.get("args", {}), served, f"line {number}")
        )
    return requests


class Rejected(Exception):
    """The tool refused the call's arguments — a usage error, or an unverifiable claim."""


async def _call(client: Client, tool: str, args: dict[str, object]) -> object:
    """One tool call; raises ``Rejected`` for a bad argument, ``RuntimeError`` for a failed read."""
    result = await client.call_tool(tool, args, raise_on_error=False)
    if result.is_error:
        text = " ".join(getattr(block, "text", "") for block in result.content).strip()
        # FastMCP reports a bad argument as a pydantic validation error; anything else
        # failed while reading the index.
        if "validation error" in text:
            raise Rejected(text)
        raise RuntimeError(text)
    return result.structured_content


async def _ask(server: FastMCP, root: Path, requests: list[Request]) -> int:
    """One client, one opened index, one payload per request in order; stops at a failed call."""
    status = OK
    # The caller's checkout is this root, as a client's declared roots would say (366).
    async with Client(server, roots=[root.as_uri()]) as client:
        for number, (tool, args) in enumerate(requests, start=1):
            try:
                payload = await _call(client, tool, args)
            except Rejected as error:
                _say(f"request {number}: {tool} rejected its arguments: {error}")
                return USAGE
            except RuntimeError as error:
                _say(f"request {number}: {tool} could not read the index: {error}")
                return FAILED
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            if isinstance(payload, dict) and payload.get("error") == SCHEMA_MISMATCH:
                status = FAILED
    return status


def _unverifiable(verdict: dict[str, object], reason: str, **detail: object) -> dict[str, object]:
    return {**verdict, "status": UNVERIFIABLE, "reason": reason, **detail}


async def _verify_one(
    client: Client, found: claim.FoundClaim, served: tuple[str, ...]
) -> dict[str, object]:
    """Re-ask one claim's ``call`` and compare what it asserts; never a ``holds`` it cannot see."""
    fields = found.fields
    tool = fields["tool"]
    then = claim.asserted(fields)
    verdict: dict[str, object] = {
        "tool": tool,
        "subject": fields.get("subject"),
        "then": then,
        "rev_then": fields.get("rev"),
    }
    if found.schema != claim.CLAIM_SCHEMA:
        return _unverifiable(
            verdict, "claim_format", format=found.schema, verifies=claim.CLAIM_SCHEMA
        )
    if tool in REFUSED_TOOLS or tool not in served:
        return _unverifiable(verdict, "tool_not_served")
    try:
        args = json.loads(fields[claim.CALL_KEY])
    except (KeyError, json.JSONDecodeError):
        return _unverifiable(verdict, "call_unreadable")
    if not isinstance(args, dict):
        return _unverifiable(verdict, "call_unreadable")
    if any(name in args for name in claim.NOT_REPLAYED):
        # A hand-edited line could otherwise make a re-run write (``reset_fit_counts``).
        return _unverifiable(verdict, "call_rejected", detail="an argument a re-run never replays")
    try:
        payload = await _call(client, tool, {**args, "sign": True})
    except Rejected as error:
        return _unverifiable(verdict, "call_rejected", detail=str(error))
    if not isinstance(payload, dict):
        return _unverifiable(verdict, "call_unreadable")
    if "error" in payload:
        # A refusal (schema mismatch, a build holding the index) answers nothing about the claim.
        return _unverifiable(verdict, str(payload["error"]))
    line = payload.get(claim.CLAIM_KEY)
    signed = claim.find_claims(line) if isinstance(line, str) else []
    if signed:
        now_fields = signed[0].fields
        now = claim.asserted(now_fields)
        rev_now: object = now_fields.get("rev")
        index_now: object = now_fields.get("index")
    else:
        # The tool signs nothing once nothing answered — a lost subject; its reason says why.
        now = {"reason": str(payload["reason"])} if payload.get("reason") else {}
        commit = payload.get("last_commit")
        rev_now = str(commit)[: claim.REV_CHARS] if commit else None
        index_now = payload.get("staleness")
    moved = claim.moved_keys(then, now)
    status = CHANGED if moved else HOLDS
    # ``index_now: behind`` says the tree answered is older than HEAD — a holds about that tree.
    verdict.update(status=status, now=now, rev_now=rev_now, index_now=index_now)
    if moved:
        verdict["changed"] = moved
    return verdict


async def _verify(
    server: FastMCP,
    root: Path,
    claims: list[tuple[str | None, claim.FoundClaim]],
    served: tuple[str, ...],
) -> int:
    """One verdict line per claim, in order; ``NOT_HELD`` when any did not hold."""
    status = OK
    async with Client(server, roots=[root.as_uri()]) as client:
        for source, found in claims:
            try:
                verdict = await _verify_one(client, found, served)
            except RuntimeError as error:
                _say(f"{found.fields['tool']} could not read the index: {error}")
                return FAILED
            if source is not None:
                verdict = {"source": f"{source}:{found.line}", **verdict}
            print(json.dumps(verdict, ensure_ascii=False), flush=True)
            if verdict["status"] != HOLDS:
                status = NOT_HELD
    return status


def _claims_in(text: str, source: str | None) -> list[tuple[str | None, claim.FoundClaim]]:
    return [(source, found) for found in claim.find_claims(text)]


def main(argv: list[str] | None = None) -> int:
    """``code-atlas query <tool> --args '<json>'`` or ``code-atlas query --batch <file.jsonl>``."""
    parser = argparse.ArgumentParser(
        prog="code-atlas query",
        description="Ask code-atlas's read tools from a shell; one JSON payload per line out.",
        epilog=(
            f"exit: {OK} answered (an empty answer with its reason included), every claim held · "
            f"{NOT_HELD} a claim changed or is unverifiable · "
            f"{USAGE} usage error · {FAILED} no readable index"
        ),
    )
    parser.add_argument("tool", nargs="?", help="the tool to ask (any served read tool)")
    parser.add_argument("--args", default="{}", help="the tool's arguments as a JSON object")
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help='one {"tool": ..., "args": {...}} per line ("-" reads stdin), answered in order',
    )
    parser.add_argument(
        "--verify-claim",
        metavar="LINE",
        help="re-run one signed claim line: holds | changed | unverifiable",
    )
    parser.add_argument(
        "--verify-claims",
        metavar="FILE",
        help='verify every claim line in a text file ("-" reads stdin); prose is skipped',
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    modes = (args.tool, args.batch, args.verify_claim, args.verify_claims)
    if sum(mode is not None for mode in modes) != 1:
        parser.error("name exactly one of a tool, --batch, --verify-claim or --verify-claims")

    try:
        from code_atlas.config import load_config
        from code_atlas.main import allowed_tools, build_server

        config = load_config(_project_root())
        served = allowed_tools(config.tools)
    except Exception as error:  # noqa: BLE001 — a broken config is an exit code, never a traceback
        _say(f"failed: {type(error).__name__}: {error}")
        return FAILED

    claims: list[tuple[str | None, claim.FoundClaim]] | None = None
    try:
        if args.verify_claim is not None:
            claims = _claims_in(args.verify_claim, None)
            if not claims:
                raise UsageError("--verify-claim: no claim line found")
            requests: list[Request] = []
        elif args.verify_claims == "-":
            claims = _claims_in(sys.stdin.read(), "-")
            requests = []
        elif args.verify_claims is not None:
            with open(args.verify_claims, encoding="utf-8") as handle:
                claims = _claims_in(handle.read(), args.verify_claims)
            requests = []
        elif args.batch is None:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError as error:
                raise UsageError(f"--args: not JSON ({error.msg})") from None
            requests = [_request(args.tool, tool_args, served, args.tool)]
        elif args.batch == "-":
            requests = parse_batch(sys.stdin, served)
        else:
            with open(args.batch, encoding="utf-8") as handle:
                requests = parse_batch(handle, served)
    except UsageError as error:
        _say(str(error))
        return USAGE
    except (OSError, UnicodeDecodeError) as error:
        _say(f"{'--batch' if args.verify_claims is None else '--verify-claims'}: {error}")
        return USAGE

    if not config.db_path.is_file():
        _say(f"no index at {config.db_path} — build one with code-atlas-build")
        return FAILED
    try:
        server = build_server(config, count=False)
        if claims is not None:
            return asyncio.run(_verify(server, config.root, claims, served))
        return asyncio.run(_ask(server, config.root, requests))
    except Exception as error:  # noqa: BLE001 — e.g. a file that is not a database
        _say(f"unreadable index at {config.db_path}: {type(error).__name__}: {error}")
        return FAILED


if __name__ == "__main__":
    raise SystemExit(main())
