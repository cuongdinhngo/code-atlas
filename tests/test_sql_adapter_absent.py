"""A repo that never configures the SQL adapter is byte-identical to one that could not.

AC4 / task 061.
"""

from __future__ import annotations

from code_atlas.config import ADAPTER_CMD_ENV
from code_atlas.config import _adapter_cmds as adapter_cmds


def test_no_sql_command_means_no_sql_adapter() -> None:
    """`.sql` reaches an adapter only through a launch command; with none, the language is gone."""
    assert dict(adapter_cmds({}, {})) == {}


def test_the_env_convention_names_no_language() -> None:
    """R1.1: the core learns SQL from the generic `CA_<LANG>_CMD` pattern, never from a literal."""
    cmds = adapter_cmds({"CA_SQL_CMD": "node adapters/sql/index.js --server"}, {})
    assert cmds["sql"] == ("node", "adapters/sql/index.js", "--server")
    # The very same pattern admits any language — nothing in the core spells one.
    assert ADAPTER_CMD_ENV.fullmatch("CA_SQL_CMD") is not None
    assert dict(adapter_cmds({"CA_COBOL_CMD": "x"}, {})).keys() == {"cobol"}
