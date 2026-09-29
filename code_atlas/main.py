"""The MCP server: build an app for one repo, then serve it over stdio (§12).

Tools are named in branches rather than a registry — there is no second axis of change here, and
one seam is the only abstraction this codebase buys (R1.2). ``CA_TOOLS`` gates which of them is
registered; a name that is not one of them is a configuration error and fails loud (R5.3).
"""

import os
from pathlib import Path

from fastmcp import FastMCP

from code_atlas import instructions
from code_atlas.config import Config, ConfigError, load_config
from code_atlas.onboarding.layers import LayerRefiner
from code_atlas.onboarding.prose import ProseWriter
from code_atlas.onboarding.summary import Summarizer
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
) -> FastMCP:
    """One repo's server: the allowed tools, each bound to ``config``, on a fresh app.

    Query tools are wrapped by ``guard`` so a schema-version mismatch arrives as an answer with a
    next action rather than a stack trace (050); the two index-lifecycle tools answer it themselves.

    ``summarizer`` (085 seam, task 090), ``layer_refiner`` (091 seam) and ``prose_writer`` (117
    seam) are the enrichment injection points: ``None`` keeps the deterministic defaults, so the
    core never depends on an LLM (R4.1). The opt-in LLM impls are injected from **outside**
    ``code_atlas/`` (``onboarding_llm``).
    """
    names = allowed_tools(config.tools)
    # `instructions` reaches the model's system prompt; tool descriptions alone did not (300).
    server: FastMCP = FastMCP(
        SERVER_NAME, instructions=instructions.render(config, names, FIELD18_TOOLS)
    )

    def serve(name: str, tool: object) -> None:
        """Register ``tool`` under ``name``, counting every return (task 260)."""
        server.tool(fit.wrap(name, config, tool))  # type: ignore[arg-type]

    if get_index_status.NAME in names:
        serve(
            get_index_status.NAME,
            guard(get_index_status.create(config, names), config),
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


def main() -> None:
    """Entry point: resolve this working directory's configuration and serve it over stdio."""
    build_server(load_config(Path.cwd(), os.environ)).run()


if __name__ == "__main__":
    main()
