"""341 — the indexed repo's own `.code-atlas.toml` cannot choose what code-atlas runs or writes.

The repo is untrusted content. Its `[adapter_cmd]` table becomes a `Popen` argv, so it is honoured
only once the user sets `CA_TRUST_PROJECT_FILE=1` somewhere the repo does not control; its
`db_path` must stay inside the repo. The environment keeps both powers unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from code_atlas.config import (
    ADAPTER_CMD_ENV,
    TRUST_PROJECT_FILE_ENV,
    ConfigError,
    config_identity,
    load_config,
)

TABLE = "[adapter_cmd]\nphp = ['sh', '-c', 'echo pwned']\n"
TRUSTED = {TRUST_PROJECT_FILE_ENV: "1"}


def _project(root: Path, text: str) -> Path:
    (root / ".code-atlas.toml").write_text(text, encoding="utf-8")
    return root


def test_an_untrusted_table_is_a_loud_error_naming_the_way_out(tmp_path: Path) -> None:
    """AC1 — red before 341: the argv was returned and handed to Popen on the next build."""
    with pytest.raises(ConfigError) as caught:
        load_config(_project(tmp_path, TABLE), {})
    message = str(caught.value)
    assert ".code-atlas.toml" in message and "php" in message
    assert TRUST_PROJECT_FILE_ENV in message and "CA_<LANG>_CMD" in message


@pytest.mark.parametrize("value", ["", "0", "true", "yes"])
def test_only_the_value_one_trusts(tmp_path: Path, value: str) -> None:
    with pytest.raises(ConfigError, match=TRUST_PROJECT_FILE_ENV):
        load_config(_project(tmp_path, TABLE), {TRUST_PROJECT_FILE_ENV: value})


def test_a_trusted_table_gives_todays_argv(tmp_path: Path) -> None:
    """AC2."""
    config = load_config(_project(tmp_path, TABLE), TRUSTED)
    assert dict(config.adapter_cmds) == {"php": ("sh", "-c", "echo pwned")}


def test_the_environment_needs_no_trust(tmp_path: Path) -> None:
    """AC3 — with no project table, `CA_<LANG>_CMD` alone launches, as before."""
    config = load_config(_project(tmp_path, "workers = 2\n"), {"CA_PHP_CMD": "php run"})
    assert dict(config.adapter_cmds) == {"php": ("php", "run")}


def test_the_environment_still_overrides_a_trusted_table(tmp_path: Path) -> None:
    """AC5 — resolution order unchanged: env beats file."""
    config = load_config(_project(tmp_path, TABLE), {**TRUSTED, "CA_PHP_CMD": "php run"})
    assert dict(config.adapter_cmds) == {"php": ("php", "run")}


def test_the_trust_variable_is_not_read_as_a_language() -> None:
    """A `*_CMD` name would have made the trust flag an adapter called `trust_project`."""
    assert ADAPTER_CMD_ENV.fullmatch(TRUST_PROJECT_FILE_ENV) is None


@pytest.mark.parametrize("raw", ["/tmp/x.db", "../x.db", "a/../../x.db", "C:/x.db", "./x.db"])
def test_a_file_db_path_outside_the_repo_is_refused(tmp_path: Path, raw: str) -> None:
    """AC4 — red before 341: an absolute value won the join and aimed SQLite anywhere."""
    with pytest.raises(ConfigError, match="repo-relative"):
        load_config(_project(tmp_path, f"db_path = {raw!r}\n"), {})


def test_a_file_db_path_inside_the_repo_and_any_env_db_path_are_accepted(tmp_path: Path) -> None:
    """AC4 — the environment may still put the index anywhere."""
    inside = load_config(_project(tmp_path, "db_path = 'idx/g.db'\n"), {})
    assert inside.db_path == tmp_path / "idx" / "g.db"
    outside = tmp_path.parent / "elsewhere.db"
    root = _project(tmp_path, "db_path = '/tmp/x.db'\n")
    env_wins = load_config(root, {"CA_DB_PATH": str(outside)})
    assert env_wins.db_path == outside


def test_trust_does_not_move_the_config_identity(tmp_path: Path) -> None:
    """The trust flag decides whether a build may run, never what it indexes (259's id stays)."""
    root = _project(tmp_path, TABLE)
    assert config_identity(root, {}) == config_identity(root, TRUSTED)
