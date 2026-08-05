"""CA_* configuration resolution: environment → project file → defaults (§11).

Every knob is named once in :data:`KNOB_KEYS`, and its environment variable is derived from that
name by :func:`env_name`, so the three layers resolve uniformly and adding a knob is one entry. A
malformed value or an unknown project-file key raises :class:`ConfigError` rather than falling
back (R5.3).

Per-adapter launch commands are read generically: any ``CA_<LANG>_CMD`` variable becomes an entry
keyed by the lower-cased name, so no language is ever hard-coded in the core (R1.1). Each resolves
to a complete **argv** — the driver receives a ready command and never re-parses a string.
"""

import os
import re
import shlex
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

PROJECT_FILE = ".code-atlas.toml"
ADAPTER_CMD_TABLE = "adapter_cmd"
ADAPTER_CMD_ENV = re.compile(r"^CA_([A-Z0-9_]+)_CMD$")

KNOB_KEYS: tuple[str, ...] = (
    "db_path",
    "workers",
    "adapter_timeout",
    "max_results",
    "impact_depth",
    "impact_max_nodes",
    "entry_points",
    "stub_roots",
    "tools",
    "host_root",
    "container_root",
)

DEFAULT_DB_PATH = Path(".code-atlas/graph.db")
# Seconds one adapter may stay silent — booting or answering — before the build kills it (§8.1).
DEFAULT_ADAPTER_TIMEOUT = 30
DEFAULT_MAX_RESULTS = 50
DEFAULT_IMPACT_DEPTH = 2
DEFAULT_IMPACT_MAX_NODES = 500
MAX_WORKERS = 8
RESERVED_CPUS = 2


class ConfigError(Exception):
    """A bad CA_* value or project-file key — a config/programmer error, so it fails loud (R5.3)."""


@dataclass(frozen=True, slots=True)
class Config:
    """Resolved configuration. Immutable, so it flows in and is never reached out to."""

    root: Path
    db_path: Path
    workers: int
    adapter_timeout: int
    max_results: int
    impact_depth: int
    impact_max_nodes: int
    entry_points: tuple[str, ...] | None
    stub_roots: tuple[str, ...] | None
    tools: tuple[str, ...] | None
    host_root: Path | None
    container_root: Path | None
    adapter_cmds: Mapping[str, tuple[str, ...]]

    def adapter_cmd(self, lang: str) -> tuple[str, ...] | None:
        """The launch argv for one adapter, or None when none is configured for it."""
        return self.adapter_cmds.get(lang.lower())


def env_name(key: str) -> str:
    """The environment variable for a project-file key: ``db_path`` → ``CA_DB_PATH``."""
    return f"CA_{key.upper()}"


def to_adapter_path(
    path: str, host_root: Path | None, container_root: Path | None
) -> str:
    """Map an absolute host path into the container root; leave relative paths alone (§9).

    The indexer only sends repo-relative paths, so this is a no-op on the build path today. The pair
    exists for callers that pass absolute host paths when both roots are configured.
    """
    if host_root is None and container_root is None:
        return path
    # Pair validation belongs to load_config; Config always hands both or neither.
    assert host_root is not None and container_root is not None
    candidate = Path(path)
    if not candidate.is_absolute():
        return path
    try:
        relative = candidate.relative_to(host_root)
    except ValueError as error:
        raise ConfigError(
            f"path {path!r} is not under {env_name('host_root')} ({host_root})"
        ) from error
    return (container_root / relative).as_posix()


def load_config(root: Path, env: Mapping[str, str] | None = None) -> Config:
    """Resolve every knob for ``root``: environment, then the project file, then the default."""
    environ = os.environ if env is None else env
    file_values = _read_project_file(root)
    host_root = _resolve_optional_path("host_root", environ, file_values)
    container_root = _resolve_optional_path("container_root", environ, file_values)
    _validate_root_pair(host_root, container_root)
    return Config(
        root=root,
        db_path=root / _resolve("db_path", _as_path, DEFAULT_DB_PATH, environ, file_values),
        workers=_resolve("workers", _as_int, _default_workers(), environ, file_values),
        adapter_timeout=_resolve(
            "adapter_timeout", _as_int, DEFAULT_ADAPTER_TIMEOUT, environ, file_values
        ),
        max_results=_resolve("max_results", _as_int, DEFAULT_MAX_RESULTS, environ, file_values),
        impact_depth=_resolve("impact_depth", _as_int, DEFAULT_IMPACT_DEPTH, environ, file_values),
        impact_max_nodes=_resolve(
            "impact_max_nodes", _as_int, DEFAULT_IMPACT_MAX_NODES, environ, file_values
        ),
        entry_points=_resolve("entry_points", _as_entry_points, None, environ, file_values),
        stub_roots=_resolve("stub_roots", _as_stub_roots, None, environ, file_values),
        tools=_resolve("tools", _as_tools, None, environ, file_values),
        host_root=host_root,
        container_root=container_root,
        adapter_cmds=_adapter_cmds(environ, file_values),
    )


def _resolve[T](
    key: str,
    parse: Callable[[str, object], T],
    default: T,
    env: Mapping[str, str],
    file_values: Mapping[str, object],
) -> T:
    """One knob, highest layer first. The label in any error names the layer that supplied it."""
    variable = env_name(key)
    if variable in env:
        return parse(variable, env[variable])
    if key in file_values:
        return parse(f"{PROJECT_FILE}:{key}", file_values[key])
    return default


def _resolve_optional_path(
    key: str, env: Mapping[str, str], file_values: Mapping[str, object]
) -> Path | None:
    """A root path that is absent until configured — Docker mapping is off by default (§9)."""
    variable = env_name(key)
    if variable in env:
        return _as_path(variable, env[variable])
    if key in file_values:
        return _as_path(f"{PROJECT_FILE}:{key}", file_values[key])
    return None


def _validate_root_pair(host_root: Path | None, container_root: Path | None) -> None:
    """Both mapping roots or neither — a half-set pair is a config error (R5.3)."""
    if (host_root is None) == (container_root is None):
        return
    raise ConfigError(
        f"{env_name('host_root')} and {env_name('container_root')} must be set together"
    )


def _default_workers() -> int:
    """One worker per CPU less a reserve, capped, never below one (PLAN §8.1)."""
    return max(1, min((os.cpu_count() or 1) - RESERVED_CPUS, MAX_WORKERS))


def _read_project_file(root: Path) -> Mapping[str, object]:
    """Parse the optional project file; an unknown key or bad TOML is a loud error (R5.3)."""
    path = root / PROJECT_FILE
    if not path.is_file():
        return {}
    try:
        values: Mapping[str, object] = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise ConfigError(f"{path}: not valid TOML ({error})") from error

    unknown = sorted(set(values) - set(KNOB_KEYS) - {ADAPTER_CMD_TABLE})
    if unknown:
        allowed = ", ".join((*KNOB_KEYS, f"[{ADAPTER_CMD_TABLE}]"))
        raise ConfigError(
            f"{path}: unknown key(s) {', '.join(unknown)} (expected one of {allowed})"
        )
    return values


def _adapter_cmds(
    env: Mapping[str, str], file_values: Mapping[str, object]
) -> Mapping[str, tuple[str, ...]]:
    """Adapter launch commands from the project file, overridden by any ``CA_<LANG>_CMD``."""
    table = file_values.get(ADAPTER_CMD_TABLE, {})
    if not isinstance(table, dict):
        raise ConfigError(
            f"{PROJECT_FILE}:{ADAPTER_CMD_TABLE}: expected a table of <lang> = <command>"
        )

    cmds: dict[str, tuple[str, ...]] = {}
    for key in sorted(table):
        label = f"{PROJECT_FILE}:{ADAPTER_CMD_TABLE}.{key}"
        cmds[key.lower()] = _as_command(label, table[key])
    for variable in sorted(env):
        found = ADAPTER_CMD_ENV.fullmatch(variable)
        if found:
            cmds[found.group(1).lower()] = _as_command(variable, env[variable])
    return MappingProxyType(cmds)


def _as_command(label: str, raw: object) -> tuple[str, ...]:
    """A complete launch argv. A list is taken verbatim; a string is split for the host platform.

    POSIX splitting eats the backslashes of a Windows path (``C:\\bin\\tool.exe`` collapses into one
    mangled word), so the split follows the platform and the list form always wins over quoting.
    """
    if isinstance(raw, list):
        argv = tuple(_as_text(f"{label}[{index}]", word) for index, word in enumerate(raw))
    else:
        argv = tuple(shlex.split(_as_text(label, raw), posix=os.name != "nt"))
    if not argv:
        raise ConfigError(f"{label}: {raw!r} is not a command")
    return argv


def _as_path(label: str, raw: object) -> Path:
    """A path value. The caller joins it onto the repo root, where an absolute value wins."""
    return Path(_as_text(label, raw))


def _as_int(label: str, raw: object) -> int:
    """A positive integer. Accepts the string an environment gives and the int TOML gives."""
    if isinstance(raw, bool) or not isinstance(raw, int | str):
        raise ConfigError(f"{label}: {raw!r} is not an integer")
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigError(f"{label}: {raw!r} is not an integer") from error
    if value < 1:
        raise ConfigError(f"{label}: {value} is not 1 or greater")
    return value


def _as_tools(label: str, raw: object) -> tuple[str, ...] | None:
    """The tool allow-list. Blank means unrestricted; names de-duplicate with the first winning."""
    if isinstance(raw, str):
        names = raw.split(",")
    elif isinstance(raw, list):
        names = [_as_text(label, item) for item in raw]
    else:
        raise ConfigError(f"{label}: {raw!r} is not a comma-separated list of tool names")
    kept = [name.strip() for name in names if name.strip()]
    return tuple(dict.fromkeys(kept)) or None


def _as_entry_points(label: str, raw: object) -> tuple[str, ...] | None:
    """Reachability roots (file globs). Blank/unset means no roots configured (task 031)."""
    if isinstance(raw, str):
        names = raw.split(",")
    elif isinstance(raw, list):
        names = [_as_text(label, item) for item in raw]
    else:
        raise ConfigError(f"{label}: {raw!r} is not a comma-separated list of entry paths")
    kept = [name.strip() for name in names if name.strip()]
    return tuple(dict.fromkeys(kept)) or None


def _as_stub_roots(label: str, raw: object) -> tuple[str, ...] | None:
    """Dependency roots for declarations-only stub indexing. Blank/unset = off (task 039)."""
    if isinstance(raw, str):
        names = raw.split(",")
    elif isinstance(raw, list):
        names = [_as_text(label, item) for item in raw]
    else:
        raise ConfigError(f"{label}: {raw!r} is not a comma-separated list of stub roots")
    kept: list[str] = []
    for name in names:
        cleaned = name.strip().strip("/").replace("\\", "/")
        if cleaned:
            kept.append(cleaned)
    return tuple(dict.fromkeys(kept)) or None


def _as_text(label: str, raw: object) -> str:
    """A non-empty string value: an adapter command, a path, a tool name."""
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(f"{label}: {raw!r} is not a non-empty string")
    return raw
