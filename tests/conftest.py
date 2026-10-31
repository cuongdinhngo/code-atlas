"""Suite-wide setup: a fixture's ``git add -A`` must not commit the index it built (420).

A tracked ``.code-atlas/`` is refused, as it would be in a user's repo without the ignore line.
Added through ``GIT_CONFIG_COUNT``, so the user's own global config still applies.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_HOME = tempfile.mkdtemp(prefix="code-atlas-tests-")
atexit.register(shutil.rmtree, _HOME, True)
_IGNORE = Path(_HOME) / "exclude"
_IGNORE.write_text(".code-atlas/\n", encoding="utf-8")
_INDEX = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
os.environ["GIT_CONFIG_COUNT"] = str(_INDEX + 1)
os.environ[f"GIT_CONFIG_KEY_{_INDEX}"] = "core.excludesFile"
os.environ[f"GIT_CONFIG_VALUE_{_INDEX}"] = str(_IGNORE)


@pytest.fixture(autouse=True)
def _fake_adapter_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    """The protocol fixture's `CA_FAKE_*` switches reach it; production passes no `CA_*` (430)."""
    from code_atlas import adapter

    prefixes = (*adapter.ADAPTER_ENV_PREFIXES, "CA_FAKE_")
    monkeypatch.setattr(adapter, "ADAPTER_ENV_PREFIXES", prefixes)
