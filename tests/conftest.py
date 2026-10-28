"""Suite-wide setup: a fixture's ``git add -A`` must not commit the index it built (420).

A tracked ``.code-atlas/`` is refused, as it would be in a user's repo without the ignore line.
Added through ``GIT_CONFIG_COUNT``, so the user's own global config still applies.
"""

import os
import tempfile
from pathlib import Path

_IGNORE = Path(tempfile.mkdtemp(prefix="code-atlas-tests-")) / "exclude"
_IGNORE.write_text(".code-atlas/\n", encoding="utf-8")
_INDEX = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
os.environ["GIT_CONFIG_COUNT"] = str(_INDEX + 1)
os.environ[f"GIT_CONFIG_KEY_{_INDEX}"] = "core.excludesFile"
os.environ[f"GIT_CONFIG_VALUE_{_INDEX}"] = str(_IGNORE)
