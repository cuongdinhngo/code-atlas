"""Task 050: a schema-version mismatch has two directions, and they need opposite actions.

An index *older* than the server is a stale cache and rebuilding it is correct. An index *newer*
than the server means this process is the stale one: the index is current, and deleting it destroys
work no one asked to lose. The old check compared with ``!=`` and printed "delete and rebuild" for
both, which is how a field session read a healthy 823 MB index as corrupt and fell back to ``grep``.

The load-bearing assertions here are on **files and payload keys**, not on message text: a wording
change must not be able to quietly restore the destructive behaviour.
"""

import asyncio
import shlex
import sys
from pathlib import Path

import pytest
from fastmcp import Client

from code_atlas.config import Config, load_config
from code_atlas.main import build_server
from code_atlas.store import (
    SCHEMA_NEWER,
    SCHEMA_OLDER,
    SCHEMA_UNRECOGNISED,
    SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
    GraphStore,
    SchemaVersionError,
)
from code_atlas.tools import build_or_update_index, get_index_status
from code_atlas.tools.schema_guard import SCHEMA_MISMATCH
from tests.test_mcp_server import CALLS, call

OLDER = "1"
NEWER = "9"
GIBBERISH = "2.0-rc1"
FAKE = Path(__file__).resolve().parent / "fixtures" / "adapter" / "fake_adapter.py"


def indexed(root: Path, version: str) -> Config:
    """A repo whose index claims ``version``, and the config that reaches it.

    Entry points are set because the reachability tools answer ``no_roots_configured`` without
    ever opening the index — a pass there would prove nothing about the mismatch.
    """
    root.mkdir(parents=True, exist_ok=True)
    config = load_config(
        root,
        {
            "CA_WORKERS": "1",
            "CA_ENTRY_POINTS": "public/*.php",
            # Task 064: empty adapter_cmds refuses the build — keep a no-op adapter for heal paths.
            "CA_FAKE_CMD": shlex.join([sys.executable, str(FAKE), "ok"]),
        },
    )
    with GraphStore(config.db_path) as store:
        store.set_meta(SCHEMA_VERSION_KEY, version)
    return config


def opened(config: Config) -> SchemaVersionError:
    """Open the index and return the refusal, so a test can assert on its fields."""
    with pytest.raises(SchemaVersionError) as raised:
        GraphStore(config.db_path)
    return raised.value


# --- the check itself knows which way it points --------------------------------------------------


def test_an_older_index_is_the_rebuildable_direction(tmp_path: Path) -> None:
    mismatch = opened(indexed(tmp_path, OLDER))

    assert mismatch.direction == SCHEMA_OLDER
    assert (mismatch.found, mismatch.expected) == (OLDER, SCHEMA_VERSION)
    assert "rebuild" in mismatch.action


def test_a_newer_index_names_this_server_as_the_stale_side(tmp_path: Path) -> None:
    """The index is fine. Saying "delete and rebuild" here is the bug this ticket exists for."""
    mismatch = opened(indexed(tmp_path, NEWER))

    assert mismatch.direction == SCHEMA_NEWER
    assert "restart" in mismatch.action
    assert "do not delete" in mismatch.action


def test_a_version_that_will_not_parse_is_never_called_older(tmp_path: Path) -> None:
    """Unrecognised is not the same as outgrown — only a provably older index may be deleted."""
    mismatch = opened(indexed(tmp_path, GIBBERISH))

    assert mismatch.direction == SCHEMA_UNRECOGNISED


def test_a_refused_open_does_not_write_to_the_database(tmp_path: Path) -> None:
    """The version is read before the DDL, so a foreign schema is never half-migrated in place."""
    config = indexed(tmp_path, NEWER)
    before = config.db_path.read_bytes()

    opened(config)

    assert config.db_path.read_bytes() == before


# --- build_or_update_index heals downward only ---------------------------------------------------


def test_the_build_still_rebuilds_an_index_it_has_outgrown(tmp_path: Path) -> None:
    config = indexed(tmp_path, OLDER)

    result = build_or_update_index.create(config)(detail_level="minimal")

    assert result["schema_rebuilt"] is True
    with GraphStore(config.db_path) as reopened:
        assert reopened.get_meta(SCHEMA_VERSION_KEY) == SCHEMA_VERSION


@pytest.mark.parametrize("version", [NEWER, GIBBERISH], ids=["newer", "unrecognised"])
def test_the_build_leaves_an_index_it_cannot_read_byte_identical(
    tmp_path: Path, version: str
) -> None:
    """Asserted on the file, not the message: this is the destructive path, bytes are the proof."""
    config = indexed(tmp_path, version)
    before = config.db_path.read_bytes()

    result = build_or_update_index.create(config)(detail_level="standard")

    assert config.db_path.read_bytes() == before
    assert result["error"] == SCHEMA_MISMATCH
    assert result["mode"] == "refused"
    assert result["schema_rebuilt"] is False


def test_a_refused_build_reports_no_counts(tmp_path: Path) -> None:
    """Zeroed counts would read as "this repo is empty", which is a different and false answer."""
    config = indexed(tmp_path, NEWER)

    result = build_or_update_index.create(config)(detail_level="standard")

    assert not {"nodes", "edges", "files", "parsed", "failed"} & set(result)
    assert "wrote" not in result and "graph" not in result


# --- get_index_status answers in both directions -------------------------------------------------


@pytest.mark.parametrize(
    ("version", "direction"),
    [(OLDER, SCHEMA_OLDER), (NEWER, SCHEMA_NEWER), (GIBBERISH, SCHEMA_UNRECOGNISED)],
    ids=["older", "newer", "unrecognised"],
)
def test_the_status_tool_answers_a_mismatch_rather_than_raising(
    tmp_path: Path, version: str, direction: str
) -> None:
    """"Call this first" has to survive the case it is most needed in."""
    config = indexed(tmp_path, version)

    status = get_index_status.create(config, ("get_index_status", "build_or_update_index"))()

    assert status["indexed"] is False
    assert status["error"] == SCHEMA_MISMATCH
    assert status["direction"] == direction
    assert (status["index_schema_version"], status["server_schema_version"]) == (
        version,
        SCHEMA_VERSION,
    )


def test_the_status_tool_suggests_a_build_only_where_a_build_is_the_fix(tmp_path: Path) -> None:
    servable = ("get_index_status", "build_or_update_index")

    older = get_index_status.create(indexed(tmp_path / "a", OLDER), servable)()
    newer = get_index_status.create(indexed(tmp_path / "b", NEWER), servable)()

    assert older["next_tool_suggestions"] == ["build_or_update_index"]
    assert newer["next_tool_suggestions"] == []


# --- every served tool answers, and none of them rebuilds ----------------------------------------


@pytest.mark.parametrize(("name", "arguments"), CALLS, ids=[name for name, _ in CALLS])
def test_every_served_tool_answers_a_mismatch_and_touches_nothing(
    tmp_path: Path, name: str, arguments: dict[str, object]
) -> None:
    """A query that silently paid for a full rebuild would be worse than the error it replaced."""
    config = indexed(tmp_path, NEWER)
    before = config.db_path.read_bytes()

    result = call(build_server(config), name, arguments)

    assert result["error"] == SCHEMA_MISMATCH, name
    assert result["action"], name
    assert config.db_path.read_bytes() == before, name


@pytest.mark.parametrize(("name", "arguments"), CALLS, ids=[name for name, _ in CALLS])
def test_a_mismatch_payload_never_carries_an_empty_result_list(
    tmp_path: Path, name: str, arguments: dict[str, object]
) -> None:
    """An empty ``results`` reads as proof of absence; the index was simply never consulted."""
    result = call(build_server(indexed(tmp_path, NEWER)), name, arguments)

    assert "results" not in result, name


def test_the_guard_leaves_the_published_input_schema_alone(tmp_path: Path) -> None:
    """Wrapping a tool must not cost a client the argument schema it calls the tool by."""

    async def schemas() -> dict[str, object]:
        async with Client(build_server(indexed(tmp_path, SCHEMA_VERSION))) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    published = asyncio.run(schemas())
    assert set(published["search_symbol"]["properties"]) >= {
        "query",
        "queries",
        "limit",
        "detail_level",
    }
    # 101 made the subject a choice of two spellings, so neither can be schema-required; the
    # tool raises when zero or both arrive. `impact` has published no required arg since M6.
    assert "required" not in published["search_symbol"]
