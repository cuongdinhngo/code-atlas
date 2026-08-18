"""The MCP server: build an app for one repo, then serve it over stdio (§12).

Tools are named in branches rather than a registry — there is no second axis of change here, and
one seam is the only abstraction this codebase buys (R1.2). ``CA_TOOLS`` gates which of them is
registered; a name that is not one of them is a configuration error and fails loud (R5.3).
"""

import os
from pathlib import Path

from fastmcp import FastMCP

from code_atlas.config import Config, ConfigError, load_config
from code_atlas.tools import (
    architecture_overview,
    build_or_update_index,
    explain_path,
    file_outline,
    find_callers,
    find_implementations,
    find_orphans,
    find_references,
    find_view_data,
    get_index_status,
    guided_tour,
    impact,
    include_graph,
    prompts,
    reachable_from,
    read_symbol,
    search_symbol,
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
    reachable_from.NAME,
    find_orphans.NAME,
    explain_path.NAME,
    architecture_overview.NAME,
    guided_tour.NAME,
)


def build_server(config: Config) -> FastMCP:
    """One repo's server: the allowed tools, each bound to ``config``, on a fresh app.

    Query tools are wrapped by ``guard`` so a schema-version mismatch arrives as an answer with a
    next action rather than a stack trace (050); the two index-lifecycle tools answer it themselves.
    """
    names = allowed_tools(config.tools)
    server: FastMCP = FastMCP(SERVER_NAME)
    if get_index_status.NAME in names:
        server.tool(get_index_status.create(config, names))
    if build_or_update_index.NAME in names:
        server.tool(build_or_update_index.create(config))
    if search_symbol.NAME in names:
        server.tool(guard(search_symbol.create(config)))
    if file_outline.NAME in names:
        server.tool(guard(file_outline.create(config)))
    if read_symbol.NAME in names:
        server.tool(guard(read_symbol.create(config)))
    if find_callers.NAME in names:
        server.tool(guard(find_callers.create(config)))
    if find_references.NAME in names:
        server.tool(guard(find_references.create(config)))
    if find_implementations.NAME in names:
        server.tool(guard(find_implementations.create(config)))
    if find_view_data.NAME in names:
        server.tool(guard(find_view_data.create(config)))
    if include_graph.NAME in names:
        server.tool(guard(include_graph.create(config)))
    if impact.NAME in names:
        server.tool(guard(impact.create(config)))
    if reachable_from.NAME in names:
        server.tool(guard(reachable_from.create(config)))
    if find_orphans.NAME in names:
        server.tool(guard(find_orphans.create(config)))
    if explain_path.NAME in names:
        server.tool(guard(explain_path.create(config)))
    if architecture_overview.NAME in names:
        server.tool(guard(architecture_overview.create(config)))
    if guided_tour.NAME in names:
        server.tool(guard(guided_tour.create(config)))
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


def main() -> None:
    """Entry point: resolve this working directory's configuration and serve it over stdio."""
    build_server(load_config(Path.cwd(), os.environ)).run()


if __name__ == "__main__":
    main()
