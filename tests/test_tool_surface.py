"""428 — the tool surface is honest, closed, quiet on stdout and stdio-only (SEC-MCP-01..05, 07).

Every arm reads the **live** server's `list_tools()` (427-C1), never `TOOL_NAMES` alone, so a tool
registered outside the annotation table is still judged. Each arm was seen red on the base commit.
Error hygiene records which path answers what: a bad argument and an unreadable index come back as
`isError` results; a repo with no index answers an ordinary `reason: not_indexed` payload.
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import queue
import re
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, get_args
from unittest import mock

import pytest
from fastmcp import Client

from code_atlas.config import ConfigError, load_config
from code_atlas.contract import ARG_SELECTORS
from code_atlas.main import (
    MAX_STRING_LENGTH,
    TOOL_NAMES,
    build_server,
    close_schema,
    tool_annotations,
)
from code_atlas.tools.find_callers import ArgSelector

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
WRITERS = {"build_or_update_index", "generate_onboarding"}
STDIO_TIMEOUT = 90.0


def _fake_env(mode: str = "ok") -> dict[str, str]:
    return {"CA_WORKERS": "2", "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), mode])}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.aa").write_text("alpha\n")
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "first"]):
        subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            cwd=tmp_path, check=True, capture_output=True,
        )  # fmt: skip
    return tmp_path


def _server(root: Path) -> Any:
    return build_server(load_config(root, _fake_env()))


def _listed(server: Any) -> list[Any]:
    async def once() -> list[Any]:
        async with Client(server) as client:
            return list(await client.list_tools())

    return asyncio.run(once())


def _call(server: Any, name: str, arguments: dict[str, object]) -> tuple[bool, str]:
    """(is_error, text) of one call, never raising on a tool error."""

    async def once() -> tuple[bool, str]:
        async with Client(server) as client:
            result = await client.call_tool(name, arguments, raise_on_error=False)
            return result.is_error, " ".join(getattr(c, "text", "") for c in result.content)

    return asyncio.run(once())


# --- AC1: annotations ----------------------------------------------------------------------------


def test_the_served_list_is_every_tool(repo: Path) -> None:
    assert sorted(t.name for t in _listed(_server(repo))) == sorted(TOOL_NAMES)


def test_every_served_tool_declares_honest_annotations(repo: Path) -> None:
    for tool in _listed(_server(repo)):
        hints = tool.annotations
        assert hints is not None, f"{tool.name} declares no annotations"
        if tool.name in WRITERS:
            assert (hints.readOnlyHint, hints.destructiveHint, hints.idempotentHint) == (
                False,
                False,
                True,
            ), tool.name
        else:
            assert (hints.readOnlyHint, hints.openWorldHint) == (True, False), tool.name


def test_a_tool_missing_from_the_table_is_a_startup_error() -> None:
    with pytest.raises(ConfigError, match="no declared annotations"):
        tool_annotations("a_tool_nobody_declared")


# --- AC2: closed schemas -------------------------------------------------------------------------

_UNBOUNDED = "free string without enum, const or maxLength"


def schema_offences(node: Any, where: str) -> list[str]:
    """Independent of `close_schema`: what a client could still send through this schema."""
    if not isinstance(node, dict):
        return [f"{where}: not a schema object"]
    found = [f"{where}: {key}" for key in ("$ref", "oneOf", "allOf", "not") if key in node]
    if node.get("type") == "object":
        if node.get("additionalProperties") is not False:
            found.append(f"{where}: object without additionalProperties: false")
        for field, sub in node.get("properties", {}).items():
            found += schema_offences(sub, f"{where}.{field}")
    if node.get("type") == "array":
        found += schema_offences(node.get("items"), f"{where}[]")
    if node.get("type") == "string" and not any(k in node for k in ("enum", "const", "maxLength")):
        found.append(f"{where}: {_UNBOUNDED}")
    for branch in node.get("anyOf", ()):
        found += schema_offences(branch, f"{where}|")
    return found


def test_every_input_schema_is_closed(repo: Path) -> None:
    offences = [
        line for t in _listed(_server(repo)) for line in schema_offences(t.inputSchema, t.name)
    ]
    assert offences == []


def test_the_walk_sees_an_open_schema() -> None:
    """Planted control: an open object, an unbounded string and a `$ref` are each named."""
    planted = {
        "type": "object",
        "properties": {
            "q": {"type": "string"},
            "inner": {"type": "object", "properties": {}},
            "r": {"$ref": "#/$defs/x"},
        },
    }
    found = " ".join(schema_offences(planted, "t"))
    assert _UNBOUNDED in found and "additionalProperties" in found and "$ref" in found


def test_a_free_string_is_bounded_and_a_closed_domain_is_an_enum(repo: Path) -> None:
    tools = {t.name: t.inputSchema for t in _listed(_server(repo))}
    qname = tools["read_symbol"]["properties"]["qname"]
    assert qname["maxLength"] == MAX_STRING_LENGTH
    detail = tools["read_symbol"]["properties"]["detail_level"]
    assert detail["enum"] == ["minimal", "standard"]
    arg_is = tools["find_callers"]["properties"]["arg_is"]["anyOf"][0]
    assert arg_is["enum"] == list(ARG_SELECTORS)


def test_arg_is_literal_is_the_contract_set() -> None:
    assert get_args(ArgSelector) == ARG_SELECTORS


@pytest.mark.parametrize(
    "schema",
    [
        {"$ref": "#/$defs/x"},
        {"oneOf": [{"type": "string"}]},
        {"type": "object", "properties": {"x": {"allOf": []}}},
        {"type": "tuple"},
        {"description": "no type"},
    ],
)
def test_a_node_the_pass_does_not_understand_raises(schema: dict[str, object]) -> None:
    with pytest.raises(ConfigError):
        close_schema(schema)


def test_close_schema_closes_nested_objects_and_array_items() -> None:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"xs": {"type": "array", "items": {"type": "string"}}},
    }
    close_schema(schema)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["xs"]["items"]["maxLength"] == MAX_STRING_LENGTH


# --- strict input: an unknown argument is refused ------------------------------------------------


def test_an_unknown_argument_is_refused_as_an_error(repo: Path) -> None:
    is_error, text = _call(_server(repo), "search_symbol", {"query": "a", "not_a_parameter": 1})
    assert is_error and "not_a_parameter" in text


def test_a_wrongly_typed_argument_is_refused_not_coerced(repo: Path) -> None:
    is_error, _ = _call(_server(repo), "search_symbol", {"query": "a", "limit": "10"})
    assert is_error


# --- AC4: error hygiene --------------------------------------------------------------------------

_ABS_PATH = re.compile(r"(?<![\w.])/(?:[\w.\-]+/)+[\w.\-]*")


def hygiene_offences(text: str, root: Path) -> list[str]:
    found = ["Traceback"] if "Traceback" in text else []
    found += [p for p in _ABS_PATH.findall(text) if not p.startswith(str(root))]
    return found


def test_the_hygiene_check_sees_a_leak(tmp_path: Path) -> None:
    """Planted control: a traceback and a foreign absolute path are both named."""
    leaked = 'Traceback (most recent call last):\n  File "/usr/lib/python3/x.py", line 1'
    assert hygiene_offences(leaked, tmp_path) == ["Traceback", "/usr/lib/python3/x.py"]
    assert hygiene_offences(f"under {tmp_path}/src/a.aa", tmp_path) == []


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("search_symbol", {"query": "a", "limit": "not-a-number"}),
        ("find_callers", {"qname": "x", "arg_position": 1, "arg_is": "no-such-selector"}),
        ("read_symbol", {"qname": 5}),
    ],
)
def test_a_bad_argument_is_an_iserror_without_internals(
    repo: Path, name: str, arguments: dict[str, object]
) -> None:
    is_error, text = _call(_server(repo), name, arguments)
    assert is_error and text
    assert hygiene_offences(text, repo) == []


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("search_symbol", {"query": "a"}),
        ("get_index_status", {}),
        ("file_outline", {"path": "src/a.aa"}),
        ("build_or_update_index", {}),
    ],
)
def test_an_unreadable_index_is_an_iserror_without_internals(
    repo: Path, name: str, arguments: dict[str, object]
) -> None:
    server = _server(repo)
    db = load_config(repo, _fake_env()).db_path
    db.parent.mkdir(parents=True, exist_ok=True)
    db.write_bytes(b"this is not a sqlite database" * 200)
    is_error, text = _call(server, name, arguments)
    assert is_error, text
    assert hygiene_offences(text, repo) == []


def test_a_tool_raising_reaches_the_client_masked(repo: Path) -> None:
    """The exception text of a tool body never reaches the client (mask_error_details)."""
    server = _server(repo)
    secret = "/srv/secret/location/leak.py"
    assert not _call(server, "build_or_update_index", {})[0]
    with mock.patch("sqlite3.connect", side_effect=OSError(secret)):
        is_error, text = _call(server, "search_symbol", {"query": "a"})
    assert is_error and secret not in text


def test_a_repo_with_no_index_answers_a_payload_not_an_error(repo: Path) -> None:
    """Recorded: the answer path says `reason: not_indexed` as data; it is not an isError."""
    is_error, text = _call(_server(repo), "search_symbol", {"query": "a"})
    assert not is_error
    assert json.loads(text)["reason"] == "not_indexed"
    assert "Traceback" not in text


# --- AC5: stdout is MCP only ---------------------------------------------------------------------


def _rpc(id_: int | None, method: str, params: dict[str, object]) -> str:
    message: dict[str, object] = {"jsonrpc": "2.0", "method": method, "params": params}
    if id_ is not None:
        message["id"] = id_
    return json.dumps(message) + "\n"


def _stdio_session(repo: Path, adapter_mode: str) -> tuple[list[str], str]:
    """Run one stdio session; returns every stdout line and the stderr text."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "code_atlas.main"],
        cwd=repo,
        env={**os.environ, **_fake_env(adapter_mode), "PYTHONPATH": str(REPO)},
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )  # fmt: skip
    assert proc.stdin and proc.stdout and proc.stderr
    lines: queue.Queue[str | None] = queue.Queue()
    stderr_text: list[str] = []
    threading.Thread(
        target=lambda: ([lines.put(line) for line in proc.stdout], lines.put(None)), daemon=True
    ).start()
    threading.Thread(target=lambda: stderr_text.append(proc.stderr.read()), daemon=True).start()
    seen: list[str] = []

    def until(id_: int) -> None:
        while True:
            line = lines.get(timeout=STDIO_TIMEOUT)
            assert line is not None, f"stdout closed before response {id_}: {seen}"
            seen.append(line)
            if json.loads(line).get("id") == id_:
                return

    try:
        proc.stdin.write(
            _rpc(
                1,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "0"},
                },
            )  # fmt: skip
        )
        proc.stdin.flush()
        until(1)
        proc.stdin.write(_rpc(None, "notifications/initialized", {}))
        proc.stdin.write(_rpc(2, "tools/list", {}))
        proc.stdin.flush()
        until(2)
        proc.stdin.write(_rpc(3, "tools/call", {"name": "build_or_update_index", "arguments": {}}))
        proc.stdin.flush()
        until(3)
        proc.stdin.close()
        while (line := lines.get(timeout=STDIO_TIMEOUT)) is not None:
            seen.append(line)
        proc.wait(timeout=STDIO_TIMEOUT)
    finally:
        proc.kill()
        proc.wait()
    return seen, "".join(stderr_text)


@pytest.mark.parametrize("adapter_mode", ["ok", "chatty-stderr", "not-json-handshake"])
def test_stdout_carries_only_json_rpc_frames(repo: Path, adapter_mode: str) -> None:
    """An adapter that shouts on stderr or speaks junk on stdout never reaches the client's pipe."""
    seen, _ = _stdio_session(repo, adapter_mode)
    assert len(seen) >= 3
    for line in seen:
        frame = json.loads(line)
        assert frame["jsonrpc"] == "2.0", line
        assert "id" in frame or "method" in frame, line
    assert not any("WWWW" in line for line in seen)


def test_the_frame_check_sees_junk() -> None:
    """Planted control: a bare print on stdout is not a JSON-RPC frame."""
    with pytest.raises(json.JSONDecodeError):
        json.loads("hello from a stray print()\n")


# --- AC6: stdio only (SEC-MCP-01) ----------------------------------------------------------------

_SERVER_TRANSPORT = re.compile(r"(^|\.)(sse|streamable_http|http)(\.|$)|(^|_)(sse|http)(_|$)")
_TRANSPORT_PACKAGES = ("fastmcp", "mcp")
_NON_STDIO_RUNNERS = frozenset(
    {
        "run_http", "run_http_async", "run_sse", "run_sse_async",
        "run_streamable_http", "run_streamable_http_async",
    }
)  # fmt: skip


def transport_offences(source: str, name: str = "<source>") -> list[str]:
    """`.run(transport=…)` other than "stdio", and any fastmcp/mcp HTTP or SSE server import."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in _NON_STDIO_RUNNERS:
                found.append(f"{name}:{node.lineno}: .{attr}() is not stdio")
            for kw in node.keywords if attr in ("run", "run_async") else ():
                stdio = isinstance(kw.value, ast.Constant) and kw.value.value == "stdio"
                if kw.arg == "transport" and not stdio:
                    found.append(f"{name}:{node.lineno}: run(transport=…) is not stdio")
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
        for module in modules:
            root, _, rest = module.partition(".")
            if root in _TRANSPORT_PACKAGES and _SERVER_TRANSPORT.search(rest):
                found.append(f"{name}:{node.lineno}: imports {module}")
    return found


def test_no_http_or_sse_transport_under_code_atlas() -> None:
    offences = [
        line
        for path in sorted((REPO / "code_atlas").rglob("*.py"))
        for line in transport_offences(path.read_text(encoding="utf-8"), path.name)
    ]
    assert offences == []


@pytest.mark.parametrize(
    "source",
    [
        'server.run(transport="http")',
        'server.run(transport="sse", port=8000)',
        "server.run(transport=chosen)",
        "server.run_http_async()",
        "server.run_sse()",
        "from fastmcp.server.http import create_streamable_http_app",
        "from mcp.server.sse import SseServerTransport",
        "from mcp.server.streamable_http import StreamableHTTPServerTransport",
        "import mcp.server.sse",
    ],
)
def test_the_transport_guard_sees_a_planted_offence(source: str) -> None:
    assert transport_offences(source), source


@pytest.mark.parametrize(
    "source",
    [
        "server.run()",
        'server.run(transport="stdio")',
        "from fastmcp import FastMCP",
        "from fastmcp.tools import FunctionTool",
    ],
)
def test_the_transport_guard_passes_stdio(source: str) -> None:
    assert transport_offences(source) == []
