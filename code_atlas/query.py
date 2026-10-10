"""``code-atlas query`` — ask the read tools from a shell, with no agent in the loop (task 382).

Each call goes through this repo's own server, in process, so a shell answer is the MCP payload for
the same arguments at the same revision. Shell calls bump no fit or cost counter: those count what
an agent asked (260, 379), and one batch would drown them.
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

from code_atlas.tools import build_or_update_index, generate_onboarding
from code_atlas.tools.schema_guard import SCHEMA_MISMATCH

OK = 0
FAILED = 1
USAGE = 2

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


async def _ask(server: FastMCP, root: Path, requests: list[Request]) -> int:
    """One client, one opened index, one payload per request in order; stops at a failed call."""
    status = OK
    # The caller's checkout is this root, as a client's declared roots would say (366).
    async with Client(server, roots=[root.as_uri()]) as client:
        for number, (tool, args) in enumerate(requests, start=1):
            result = await client.call_tool(tool, args, raise_on_error=False)
            if result.is_error:
                text = " ".join(getattr(block, "text", "") for block in result.content).strip()
                # FastMCP reports a bad argument as a pydantic validation error; anything else
                # failed while reading the index.
                if "validation error" in text:
                    _say(f"request {number}: {tool} rejected its arguments: {text}")
                    return USAGE
                _say(f"request {number}: {tool} could not read the index: {text}")
                return FAILED
            payload = result.structured_content
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            if isinstance(payload, dict) and payload.get("error") == SCHEMA_MISMATCH:
                status = FAILED
    return status


def main(argv: list[str] | None = None) -> int:
    """``code-atlas query <tool> --args '<json>'`` or ``code-atlas query --batch <file.jsonl>``."""
    parser = argparse.ArgumentParser(
        prog="code-atlas query",
        description="Ask code-atlas's read tools from a shell; one JSON payload per line out.",
        epilog=(
            f"exit: {OK} answered (an empty answer with its reason included) · "
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
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if (args.tool is None) == (args.batch is None):
        parser.error("name exactly one of a tool or --batch")

    try:
        from code_atlas.config import load_config
        from code_atlas.main import allowed_tools, build_server

        config = load_config(_project_root())
        served = allowed_tools(config.tools)
    except Exception as error:  # noqa: BLE001 — a broken config is an exit code, never a traceback
        _say(f"failed: {type(error).__name__}: {error}")
        return FAILED

    try:
        if args.batch is None:
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
        _say(f"--batch: {error}")
        return USAGE

    if not config.db_path.is_file():
        _say(f"no index at {config.db_path} — build one with code-atlas-build")
        return FAILED
    try:
        return asyncio.run(_ask(build_server(config, count=False), config.root, requests))
    except Exception as error:  # noqa: BLE001 — e.g. a file that is not a database
        _say(f"unreadable index at {config.db_path}: {type(error).__name__}: {error}")
        return FAILED


if __name__ == "__main__":
    raise SystemExit(main())
