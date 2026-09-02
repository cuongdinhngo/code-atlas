"""AC1: every CA_* knob resolves environment > project file > default (task 003, PLAN §11).

The precedence case list is checked against ``KNOB_KEYS`` so it cannot silently drift out of step
with the module it tests, and the fail-loud cases assert R5.3: a bad value never falls back to the
default.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from code_atlas.config import (
    ADAPTER_CMD_TABLE,
    KNOB_KEYS,
    PROJECT_FILE,
    Config,
    ConfigError,
    env_name,
    load_config,
    to_adapter_path,
)

FIXED_CPUS = 10
CPU_CASES = ((1, 1), (3, 1), (64, 8))


@dataclass(frozen=True)
class Knob:
    """One knob's three layers: what each layer is set to, and what it should resolve to."""

    variable: str
    file_body: str
    env_value: str
    read: Callable[[Config], object]
    from_env: Callable[[Path], object]
    from_file: Callable[[Path], object]
    from_default: Callable[[Path], object]
    companion_env: dict[str, str] = field(default_factory=dict)


KNOBS = (
    Knob(
        "CA_DB_PATH",
        'db_path = "file/graph.db"',
        "/tmp/env/graph.db",
        lambda config: config.db_path,
        lambda root: Path("/tmp/env/graph.db"),
        lambda root: root / "file/graph.db",
        lambda root: root / ".code-atlas/graph.db",
    ),
    Knob(
        "CA_WORKERS",
        "workers = 3",
        "7",
        lambda config: config.workers,
        lambda root: 7,
        lambda root: 3,
        lambda root: FIXED_CPUS - 2,
    ),
    Knob(
        "CA_ADAPTER_TIMEOUT",
        "adapter_timeout = 45",
        "12",
        lambda config: config.adapter_timeout,
        lambda root: 12,
        lambda root: 45,
        lambda root: 30,
    ),
    Knob(
        "CA_MAX_RESULTS",
        "max_results = 20",
        "99",
        lambda config: config.max_results,
        lambda root: 99,
        lambda root: 20,
        lambda root: 50,
    ),
    Knob(
        "CA_MAX_SUBJECTS",
        "max_subjects = 8",
        "12",
        lambda config: config.max_subjects,
        lambda root: 12,
        lambda root: 8,
        lambda root: 25,
    ),
    Knob(
        "CA_IMPACT_DEPTH",
        "impact_depth = 4",
        "5",
        lambda config: config.impact_depth,
        lambda root: 5,
        lambda root: 4,
        lambda root: 2,
    ),
    Knob(
        "CA_IMPACT_MAX_NODES",
        "impact_max_nodes = 90",
        "120",
        lambda config: config.impact_max_nodes,
        lambda root: 120,
        lambda root: 90,
        lambda root: 500,
    ),
    Knob(
        "CA_ORPHANS_MAX_NODES",
        "orphans_max_nodes = 90",
        "120",
        lambda config: config.orphans_max_nodes,
        lambda root: 120,
        lambda root: 90,
        lambda root: 500,
    ),
    Knob(
        "CA_FULL_BUILD_CROSSOVER",
        "full_build_crossover = 4000",
        "5000",
        lambda config: config.full_build_crossover,
        lambda root: 5000,
        lambda root: 4000,
        lambda root: 0,
    ),
    Knob(
        "CA_PATH_INDEX_MAX",
        "path_index_max = 5000",
        "8000",
        lambda config: config.path_index_max,
        lambda root: 8000,
        lambda root: 5000,
        lambda root: 20000,
    ),
    Knob(
        "CA_ENTRY_POINTS",
        'entry_points = ["public/index.php"]',
        "bin/console,src/Kernel.php",
        lambda config: config.entry_points,
        lambda root: ("bin/console", "src/Kernel.php"),
        lambda root: ("public/index.php",),
        lambda root: None,
    ),
    Knob(
        "CA_STUB_ROOTS",
        'stub_roots = ["vendor"]',
        "vendor,libs",
        lambda config: config.stub_roots,
        lambda root: ("vendor", "libs"),
        lambda root: ("vendor",),
        lambda root: None,
    ),
    Knob(
        "CA_INDIRECTION_RULES",
        'indirection_rules = ["rules/app.json"]',
        "rules/a.json,rules/b.json",
        lambda config: config.indirection_rules,
        lambda root: ("rules/a.json", "rules/b.json"),
        lambda root: ("rules/app.json",),
        lambda root: None,
    ),
    Knob(
        "CA_ARCHITECTURE_RULES",
        'architecture_rules = ["rules/arch.json"]',
        "rules/a.json,rules/b.json",
        lambda config: config.architecture_rules,
        lambda root: ("rules/a.json", "rules/b.json"),
        lambda root: ("rules/arch.json",),
        lambda root: None,
    ),
    Knob(
        "CA_TOOLS",
        'tools = ["search_symbol"]',
        "read_symbol,file_outline",
        lambda config: config.tools,
        lambda root: ("read_symbol", "file_outline"),
        lambda root: ("search_symbol",),
        lambda root: None,
    ),
    Knob(
        "CA_PHP_CMD",
        f'[{ADAPTER_CMD_TABLE}]\nphp = "runtime from-file --server"',
        "runtime from-env --server",
        lambda config: config.adapter_cmd("php"),
        lambda root: ("runtime", "from-env", "--server"),
        lambda root: ("runtime", "from-file", "--server"),
        lambda root: None,
    ),
    Knob(
        "CA_HOST_ROOT",
        'host_root = "/from-file/host"\ncontainer_root = "/from-file/container"',
        "/from-env/host",
        lambda config: config.host_root,
        lambda root: Path("/from-env/host"),
        lambda root: Path("/from-file/host"),
        lambda root: None,
        companion_env={"CA_CONTAINER_ROOT": "/from-env/container"},
    ),
    Knob(
        "CA_CONTAINER_ROOT",
        'host_root = "/from-file/host"\ncontainer_root = "/from-file/container"',
        "/from-env/container",
        lambda config: config.container_root,
        lambda root: Path("/from-env/container"),
        lambda root: Path("/from-file/container"),
        lambda root: None,
        companion_env={"CA_HOST_ROOT": "/from-env/host"},
    ),
)


@pytest.fixture
def fixed_cpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the CPU count so the CA_WORKERS default is the same on every machine (R4.2)."""
    monkeypatch.setattr(os, "cpu_count", lambda: FIXED_CPUS)


@pytest.mark.parametrize("knob", KNOBS, ids=lambda knob: knob.variable)
def test_env_beats_project_file_beats_default(
    knob: Knob, tmp_path: Path, fixed_cpus: None
) -> None:
    project_file = tmp_path / PROJECT_FILE
    env_only = {knob.variable: knob.env_value, **knob.companion_env}

    assert knob.read(load_config(tmp_path, env_only)) == knob.from_env(tmp_path)

    project_file.write_text(knob.file_body, encoding="utf-8")
    assert knob.read(load_config(tmp_path, env_only)) == knob.from_env(tmp_path)
    assert knob.read(load_config(tmp_path, {})) == knob.from_file(tmp_path)

    project_file.unlink()
    assert knob.read(load_config(tmp_path, {})) == knob.from_default(tmp_path)


def test_every_knob_has_a_precedence_case() -> None:
    # Guards the guard: dropping a knob from KNOBS would otherwise shrink AC1's coverage silently.
    covered = {knob.variable for knob in KNOBS}
    assert {env_name(key) for key in KNOB_KEYS} | {"CA_PHP_CMD"} == covered
    assert len(KNOB_KEYS) == 17


def test_env_name_is_derived_from_the_project_file_key() -> None:
    assert [env_name(key) for key in KNOB_KEYS] == [
        "CA_DB_PATH",
        "CA_WORKERS",
        "CA_ADAPTER_TIMEOUT",
        "CA_MAX_RESULTS",
        "CA_MAX_SUBJECTS",
        "CA_IMPACT_DEPTH",
        "CA_IMPACT_MAX_NODES",
        "CA_ORPHANS_MAX_NODES",
        "CA_FULL_BUILD_CROSSOVER",
        "CA_PATH_INDEX_MAX",
        "CA_ENTRY_POINTS",
        "CA_STUB_ROOTS",
        "CA_INDIRECTION_RULES",
        "CA_ARCHITECTURE_RULES",
        "CA_TOOLS",
        "CA_HOST_ROOT",
        "CA_CONTAINER_ROOT",
    ]


def test_an_absolute_db_path_wins_over_the_root(tmp_path: Path) -> None:
    config = load_config(tmp_path, {"CA_DB_PATH": "/var/atlas/graph.db"})
    assert config.db_path == Path("/var/atlas/graph.db")
    assert config.root == tmp_path


def test_an_unconfigured_adapter_has_no_command(tmp_path: Path) -> None:
    assert load_config(tmp_path, {}).adapter_cmd("php") is None


def test_any_language_resolves_without_a_core_change(tmp_path: Path) -> None:
    # R1.1: a name the core has never heard of must work by naming alone, with no branch anywhere.
    config = load_config(tmp_path, {"CA_TYPESCRIPT_CMD": "node adapter.js --server"})
    assert config.adapter_cmd("typescript") == ("node", "adapter.js", "--server")
    assert config.adapter_cmd("TypeScript") == ("node", "adapter.js", "--server")
    assert config.adapter_cmd("php") is None


def test_a_launch_command_resolves_to_the_whole_argv(tmp_path: Path) -> None:
    # PLAN §9: the configured value launches the adapter on its own — the core appends nothing.
    config = load_config(tmp_path, {"CA_EX_CMD": "docker compose exec -T svc run app --server"})
    assert config.adapter_cmd("ex") == (
        "docker",
        "compose",
        "exec",
        "-T",
        "svc",
        "run",
        "app",
        "--server",
    )


def test_a_launch_command_may_be_given_word_by_word(tmp_path: Path) -> None:
    # The list form needs no quoting rules at all, which is why it exists alongside the string.
    (tmp_path / PROJECT_FILE).write_text(
        f'[{ADAPTER_CMD_TABLE}]\nex = ["C:\\\\bin\\\\tool.exe", "app", "--server"]\n',
        encoding="utf-8",
    )
    assert load_config(tmp_path, {}).adapter_cmd("ex") == (
        "C:\\bin\\tool.exe",
        "app",
        "--server",
    )


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("posix", ("C:bintool.exe", "app")), ("nt", ("C:\\bin\\tool.exe", "app"))],
    ids=["posix-eats-the-backslashes", "windows-keeps-them"],
)
def test_a_command_string_is_split_for_the_host_platform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, expected: tuple[str, ...]
) -> None:
    # The posix case is the hazard, asserted rather than described: a Windows path loses its
    # separators, which is exactly why the list form above is the recommended shape there.
    monkeypatch.setattr(os, "name", platform)
    config = load_config(tmp_path, {"CA_EX_CMD": "C:\\bin\\tool.exe app"})
    assert config.adapter_cmd("ex") == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("read_symbol, file_outline ,read_symbol", ("read_symbol", "file_outline")),
        ("search_symbol", ("search_symbol",)),
        ("", None),
        ("  ,  ", None),
    ],
    ids=["deduplicates-first-wins", "single", "blank-is-unrestricted", "separators-only"],
)
def test_the_tool_allow_list_parses(tmp_path: Path, raw: str, expected: tuple[str, ...]) -> None:
    assert load_config(tmp_path, {"CA_TOOLS": raw}).tools == expected


@pytest.mark.parametrize(
    ("env", "body", "expected_in_message"),
    [
        ({"CA_WORKERS": "many"}, "", "CA_WORKERS"),
        ({"CA_WORKERS": "0"}, "", "not 1 or greater"),
        ({"CA_DB_PATH": ""}, "", "CA_DB_PATH"),
        ({}, "worker = 3", "unknown key(s) worker"),
        ({}, "workers = ", "not valid TOML"),
        ({}, f"[{ADAPTER_CMD_TABLE}]\nphp = 3", f"{ADAPTER_CMD_TABLE}.php"),
        ({}, f'{ADAPTER_CMD_TABLE} = "php"', ADAPTER_CMD_TABLE),
        ({}, f"[{ADAPTER_CMD_TABLE}]\nphp = []", f"{ADAPTER_CMD_TABLE}.php"),
        ({}, f'[{ADAPTER_CMD_TABLE}]\nphp = ["", "x"]', f"{ADAPTER_CMD_TABLE}.php[0]"),
        ({"CA_PHP_CMD": "   "}, "", "CA_PHP_CMD"),
        ({}, "tools = 4", "tools"),
        ({"CA_HOST_ROOT": "/only/host"}, "", "must be set together"),
        ({"CA_CONTAINER_ROOT": "/only/container"}, "", "must be set together"),
    ],
    ids=[
        "non-numeric-workers",
        "zero-workers",
        "empty-db-path",
        "unknown-project-file-key",
        "malformed-toml",
        "non-string-adapter-command",
        "adapter-cmd-not-a-table",
        "empty-adapter-argv",
        "empty-word-in-adapter-argv",
        "blank-adapter-command",
        "tools-not-a-list",
        "host-root-alone",
        "container-root-alone",
    ],
)
def test_a_bad_value_fails_loud_instead_of_falling_back(
    tmp_path: Path, env: dict[str, str], body: str, expected_in_message: str
) -> None:
    if body:
        (tmp_path / PROJECT_FILE).write_text(body, encoding="utf-8")

    with pytest.raises(ConfigError) as error:
        load_config(tmp_path, env)
    assert expected_in_message in str(error.value)


def test_to_adapter_path_rewrites_absolute_host_paths(tmp_path: Path) -> None:
    host = tmp_path / "host"
    container = Path("/app")
    relative = "src/A.php"
    assert to_adapter_path(relative, host, container) == relative
    assert to_adapter_path(str(host / relative), host, container) == "/app/src/A.php"
    assert to_adapter_path(relative, None, None) == relative
    with pytest.raises(ConfigError, match="not under"):
        to_adapter_path(str(tmp_path / "elsewhere" / relative), host, container)


@pytest.mark.parametrize(
    "raw",
    ["/etc", "../outside", "vendor/../secret", "./vendor", "a//b"],
)
def test_stub_roots_reject_non_repo_relative_paths(tmp_path: Path, raw: str) -> None:
    with pytest.raises(ConfigError, match="repo-relative"):
        load_config(tmp_path, {"CA_STUB_ROOTS": raw})


@pytest.mark.parametrize(("cpus", "expected"), CPU_CASES, ids=[f"{n}-cpus" for n, _ in CPU_CASES])
def test_the_worker_default_is_floored_and_capped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cpus: int, expected: int
) -> None:
    monkeypatch.setattr(os, "cpu_count", lambda: cpus)
    assert load_config(tmp_path, {}).workers == expected


def test_identical_input_resolves_identically(tmp_path: Path, fixed_cpus: None) -> None:
    (tmp_path / PROJECT_FILE).write_text(
        f'workers = 2\ntools = ["read_symbol"]\n[{ADAPTER_CMD_TABLE}]\nphp = "php"\n',
        encoding="utf-8",
    )
    env = {"CA_MAX_RESULTS": "10"}
    assert load_config(tmp_path, env) == load_config(tmp_path, env)


def test_the_resolved_config_is_immutable(tmp_path: Path) -> None:
    config = load_config(tmp_path, {})
    with pytest.raises(AttributeError):
        config.workers = 99  # type: ignore[misc]
