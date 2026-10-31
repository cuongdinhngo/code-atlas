"""The MCP server: build an app for one repo, then serve it over stdio (§12).

Tools are named in branches rather than a registry — there is no second axis of change here, and
one seam is the only abstraction this codebase buys (R1.2). ``CA_TOOLS`` gates which of them is
registered; a name that is not one of them is a configuration error and fails loud (R5.3).
"""

import functools
import os
import sys
from collections.abc import Callable
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import FunctionTool
from mcp.types import ToolAnnotations

from code_atlas import instructions
from code_atlas.build_info import REPOSITORY_GIT, UNKNOWN_VERSION, package_version
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.index_trust import IndexTrustError
from code_atlas.onboarding.layers import LayerRefiner
from code_atlas.onboarding.prose import ProseWriter
from code_atlas.onboarding.summary import Summarizer
from code_atlas.ref_check import CallerRoots
from code_atlas.tools import (
    architecture_overview,
    build_or_update_index,
    check_architecture_rules,
    check_column_defaults,
    class_diagram,
    diff_architecture,
    explain_path,
    file_outline,
    find_callers,
    find_implementations,
    find_orphans,
    find_references,
    find_view_data,
    fit,
    generate_onboarding,
    get_index_status,
    guided_tour,
    impact,
    impact_modules,
    include_graph,
    prompts,
    reachable_from,
    read_symbol,
    search_symbol,
    subtree_dependencies,
    trace_capability,
)
from code_atlas.tools.schema_guard import guard

SERVER_NAME = "code-atlas"

# Every tool this server knows how to serve, in the order a client is offered them (§12).
TOOL_NAMES: tuple[str, ...] = (
    get_index_status.NAME,
    build_or_update_index.NAME,
    search_symbol.NAME,
    file_outline.NAME,
    read_symbol.NAME,
    find_callers.NAME,
    find_references.NAME,
    find_implementations.NAME,
    find_view_data.NAME,
    include_graph.NAME,
    impact.NAME,
    impact_modules.NAME,
    subtree_dependencies.NAME,
    reachable_from.NAME,
    find_orphans.NAME,
    explain_path.NAME,
    architecture_overview.NAME,
    guided_tour.NAME,
    trace_capability.NAME,
    generate_onboarding.NAME,
    check_architecture_rules.NAME,
    check_column_defaults.NAME,
    diff_architecture.NAME,
    class_diagram.NAME,
)

# The two tools that write (the index, the onboarding tree): idempotent, never destructive.
WRITER_TOOLS: frozenset[str] = frozenset({build_or_update_index.NAME, generate_onboarding.NAME})


def tool_annotations(name: str) -> ToolAnnotations:
    """The MCP annotations one tool declares; a tool outside ``TOOL_NAMES`` fails loud (428)."""
    if name not in TOOL_NAMES:
        raise ConfigError(f"tool {name!r} has no declared annotations: add it to TOOL_NAMES")
    if name in WRITER_TOOLS:
        return ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
    return ToolAnnotations(readOnlyHint=True, openWorldHint=False)


def refusal_is_loud(tool: Callable[..., dict[str, object]]) -> Callable[..., dict[str, object]]:
    """A ``ValueError`` a tool raises on purpose (R5.3) keeps its message; others are masked."""

    @functools.wraps(tool)
    def loud(*args: object, **kwargs: object) -> dict[str, object]:
        try:
            return tool(*args, **kwargs)
        except ValueError as refusal:
            raise ToolError(str(refusal)) from None

    return loud


# The bound on a free string (a query, a path, a qname) in a tool's input schema (428, W1).
MAX_STRING_LENGTH = 4096
_SCHEMA_KEYS = frozenset(
    {
        "type", "properties", "required", "additionalProperties", "anyOf", "enum", "const",
        "items", "default", "title", "description", "maxLength", "minLength", "minimum", "maximum",
    }
)  # fmt: skip
_SCALAR_TYPES = frozenset({"integer", "number", "boolean", "null"})


def close_schema(node: object, where: str = "input schema") -> None:
    """Close one input schema in place: no extra property, no unbounded free string (428).

    A node shape it does not know raises rather than passing unclosed (424-C1 fail-closed).
    """
    if not isinstance(node, dict):
        raise ConfigError(f"{where}: a schema node must be an object, got {type(node).__name__}")
    unknown = sorted(set(node) - _SCHEMA_KEYS)
    if unknown:
        raise ConfigError(f"{where}: cannot close a schema node carrying {', '.join(unknown)}")
    for branch in node.get("anyOf", ()):
        close_schema(branch, f"{where}/anyOf")
    kind = node.get("type")
    if kind == "object":
        node["additionalProperties"] = False
        for field, sub in node.get("properties", {}).items():
            close_schema(sub, f"{where}/{field}")
    elif kind == "array":
        close_schema(node.get("items"), f"{where}/items")
    elif kind == "string":
        if not any(key in node for key in ("enum", "const", "maxLength")):
            node["maxLength"] = MAX_STRING_LENGTH
    elif kind is None:
        if not any(key in node for key in ("anyOf", "enum", "const")):
            raise ConfigError(f"{where}: a schema node with no type, anyOf, enum or const")
    elif kind not in _SCALAR_TYPES:
        raise ConfigError(f"{where}: cannot close a schema node of type {kind!r}")


# Opt-in field-round-18 keep-list — set CA_TOOLS to this comma-join (268). Default stays TOOL_NAMES.
FIELD18_TOOLS: tuple[str, ...] = (
    get_index_status.NAME,
    search_symbol.NAME,
    read_symbol.NAME,
    find_callers.NAME,
    find_references.NAME,
    impact.NAME,
)


def build_server(
    config: Config,
    summarizer: Summarizer | None = None,
    layer_refiner: LayerRefiner | None = None,
    prose_writer: ProseWriter | None = None,
    *,
    count: bool = True,
) -> FastMCP:
    """One repo's server: the allowed tools, each bound to ``config``, on a fresh app.

    Query tools are wrapped by ``guard`` so a schema-version mismatch arrives as an answer with a
    next action rather than a stack trace (050); the two index-lifecycle tools answer it themselves.

    ``summarizer`` (085 seam, task 090), ``layer_refiner`` (091 seam) and ``prose_writer`` (117
    seam) are the enrichment injection points: ``None`` keeps the deterministic defaults, so the
    core never depends on an LLM (R4.1). The opt-in LLM impls are injected from **outside**
    ``code_atlas/`` (``onboarding_llm``).

    ``count=False`` serves the same tools without the fit/cost counters — the shell route (382),
    whose batch calls are not an agent's asks.
    """
    names = allowed_tools(config.tools)
    # `instructions` reaches the model's system prompt; tool descriptions alone did not (300).
    # A tool error reaches the client without its internals (mask); an argument the schema does not
    # name is refused, not ignored (strict) — 428.
    server: FastMCP = FastMCP(
        SERVER_NAME,
        instructions=instructions.render(config, names, FIELD18_TOOLS),
        mask_error_details=True,
        strict_input_validation=True,
    )

    server.add_middleware(CallerRoots())

    def serve(name: str, tool: Callable[..., dict[str, object]]) -> None:
        """Register ``tool`` under ``name``, counting every return (task 260).

        Every tool leaves here with its annotations and a closed input schema (428).
        """
        registered = FunctionTool.from_function(
            refusal_is_loud(fit.wrap(name, config, tool) if count else tool),
            annotations=tool_annotations(name),
        )
        if registered.name != name:
            raise ConfigError(f"tool registered as {registered.name!r}, expected {name!r}")
        close_schema(registered.parameters, f"{name} input schema")
        server.add_tool(registered)

    if get_index_status.NAME in names:
        serve(
            get_index_status.NAME,
            guard(get_index_status.create(config, names), config, status=True),
        )
    if build_or_update_index.NAME in names:
        serve(build_or_update_index.NAME, build_or_update_index.create(config))
    if search_symbol.NAME in names:
        serve(search_symbol.NAME, guard(search_symbol.create(config), config))
    if file_outline.NAME in names:
        serve(file_outline.NAME, guard(file_outline.create(config), config))
    if read_symbol.NAME in names:
        serve(read_symbol.NAME, guard(read_symbol.create(config), config))
    if find_callers.NAME in names:
        serve(find_callers.NAME, guard(find_callers.create(config), config))
    if find_references.NAME in names:
        serve(find_references.NAME, guard(find_references.create(config), config))
    if find_implementations.NAME in names:
        serve(
            find_implementations.NAME,
            guard(find_implementations.create(config), config),
        )
    if find_view_data.NAME in names:
        serve(find_view_data.NAME, guard(find_view_data.create(config), config))
    if include_graph.NAME in names:
        serve(include_graph.NAME, guard(include_graph.create(config), config))
    if impact.NAME in names:
        serve(impact.NAME, guard(impact.create(config), config))
    if impact_modules.NAME in names:
        serve(impact_modules.NAME, guard(impact_modules.create(config), config))
    if subtree_dependencies.NAME in names:
        serve(
            subtree_dependencies.NAME,
            guard(subtree_dependencies.create(config), config),
        )
    if reachable_from.NAME in names:
        serve(reachable_from.NAME, guard(reachable_from.create(config), config))
    if find_orphans.NAME in names:
        serve(find_orphans.NAME, guard(find_orphans.create(config), config))
    if explain_path.NAME in names:
        serve(explain_path.NAME, guard(explain_path.create(config), config))
    if architecture_overview.NAME in names:
        serve(
            architecture_overview.NAME,
            guard(
                architecture_overview.create(
                    config, summarizer, layer_refiner, prose_writer
                ),
                config,
            ),
        )
    if guided_tour.NAME in names:
        serve(guided_tour.NAME, guard(guided_tour.create(config), config))
    if generate_onboarding.NAME in names:
        serve(
            generate_onboarding.NAME,
            guard(
                generate_onboarding.create(
                    config, summarizer, layer_refiner, prose_writer
                ),
                config,
            ),
        )
    if check_architecture_rules.NAME in names:
        serve(
            check_architecture_rules.NAME,
            guard(check_architecture_rules.create(config), config),
        )
    if check_column_defaults.NAME in names:
        serve(
            check_column_defaults.NAME,
            guard(check_column_defaults.create(config), config),
        )
    if diff_architecture.NAME in names:
        serve(diff_architecture.NAME, guard(diff_architecture.create(config), config))
    if class_diagram.NAME in names:
        serve(class_diagram.NAME, guard(class_diagram.create(config), config))
    if trace_capability.NAME in names:
        serve(trace_capability.NAME, guard(trace_capability.create(config), config))
    prompts.register(server)
    return server


def allowed_tools(tools: tuple[str, ...] | None) -> tuple[str, ...]:
    """Resolve the ``CA_TOOLS`` allow-list against what exists; unset or blank means every tool.

    ``config.py`` validates the list's shape but cannot know tool names, so membership is checked
    here — an allow-list of typos would otherwise serve nothing and look like a working server.
    """
    if tools is None:
        return TOOL_NAMES
    unknown = sorted(set(tools) - set(TOOL_NAMES))
    if unknown:
        raise ConfigError(
            f"CA_TOOLS names unknown tool(s) {', '.join(unknown)} "
            f"(this server serves {', '.join(TOOL_NAMES)})"
        )
    return tuple(name for name in TOOL_NAMES if name in tools)


EXPECT_VERSION_FLAG = "--expect-version"


def version_refusal(expected: str | None, installed: str) -> str | None:
    """The refusal naming the one fixing command when the plugin and this server differ (427).

    An unknown installed version (a checkout, no metadata) cannot disagree, so it serves.
    """
    if expected is None or installed in (expected, UNKNOWN_VERSION):
        return None
    return (
        f"code-atlas: refusing to serve: the plugin is {expected}, this server is {installed}"
        f" — run: uv tool install --force git+{REPOSITORY_GIT}@v{expected}"
        f" (or pipx install --force git+{REPOSITORY_GIT}@v{expected})"
    )


def _expected_version(args: list[str]) -> str | None:
    if EXPECT_VERSION_FLAG in args:
        at = args.index(EXPECT_VERSION_FLAG) + 1
        return args[at] if at < len(args) else None
    return None


def main() -> None:
    """Entry point: serve this working directory over stdio, or ``code-atlas query …`` (382)."""
    if sys.argv[1:2] == ["query"]:
        from code_atlas import query

        raise SystemExit(query.main(sys.argv[2:]))
    refusal = version_refusal(_expected_version(sys.argv[1:]), package_version())
    if refusal:
        print(refusal, file=sys.stderr)
        raise SystemExit(2)
    try:
        config = load_config(Path.cwd(), os.environ)
    except IndexTrustError as refused:
        print(f"code-atlas: refusing to serve: {refused}", file=sys.stderr)
        raise SystemExit(2) from None
    build_server(config).run()


if __name__ == "__main__":
    main()
