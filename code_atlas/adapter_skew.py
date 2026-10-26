"""Which contract each configured adapter speaks, learned without a build (374).

The checkout ``CA_<LANG>_CMD`` points into is the third half of an install, beside the tool and the
plugin, and nothing checked it before a build: the anchor's first sign of a moved checkout was a
refused build. Two sources, in order:

- **the handshake** — every configured adapter is launched at once under one deadline, the only
  source that speaks before any build;
- **the last refused build** — the contract a refused handshake named, kept beside ``graph.db``
  and cleared by the next build that runs, for an adapter the launch could not answer for.

Offline and writes nothing to the index (R4.1, R4.2); an adapter that cannot answer is ``None``.
"""

from __future__ import annotations

import importlib.metadata
import json
import threading
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from code_atlas import contract
from code_atlas.adapter import AdapterContractError, AdapterError, SubprocessAdapter
from code_atlas.config import Config

REFUSAL_NAME = "contract.refused"
# Well inside the hook's 10 s: adapters launch together, so this bounds the whole probe.
PROBE_TIMEOUT = 3.0
# The fix for a refused handshake, by which half is older (418).
OLDER_ADAPTER_FIX = (
    "adapter {key!r} is v{announced}, core is v{core}: put the adapter checkout on a release that "
    "speaks v{core}{release}, or reinstall the core from that checkout"
)
OLDER_CORE_FIX = (
    "core is v{core}, older than adapter {key!r} (v{announced}): reinstall the core from the "
    "adapter's checkout (`uv tool install --reinstall --from <checkout> code-atlas`)"
)
SAME_CHECKOUT_CLAUSE = (
    "; the core was installed from this checkout ({source}) at another revision, "
    "so reinstall it after switching branches"
)


def _refusal_path(db_path: Path) -> Path:
    return db_path.parent / REFUSAL_NAME


def read_refusals(db_path: Path) -> dict[str, int]:
    """Adapter key → the contract its last refused handshake named; empty when none is kept."""
    try:
        raw = json.loads(_refusal_path(db_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }


def record_refusal(
    db_path: Path, refused: AdapterContractError, *, proven: Iterable[str] = ()
) -> None:
    """Keep the contract a refused handshake named; drop the adapters this announce proved."""
    cleared = set(proven)
    kept = {key: value for key, value in read_refusals(db_path).items() if key not in cleared}
    kept[refused.key] = refused.announced
    try:
        _refusal_path(db_path).write_text(json.dumps(kept, sort_keys=True), encoding="utf-8")
    except OSError:
        pass  # Unwritable: the launch is the only source; the caller still gets the refusal.


def clear_refusals(db_path: Path) -> None:
    """A build that ran met every adapter on this core's contract."""
    try:
        _refusal_path(db_path).unlink(missing_ok=True)
    except OSError:
        pass


def _announce(adapter: SubprocessAdapter, key: str, answers: dict[str, int | None]) -> None:
    try:
        adapter.start()
        answers[key] = contract.CONTRACT_VERSION
    except AdapterContractError as refused:
        answers[key] = refused.announced
    except AdapterError:
        pass  # Cannot run, or announced nothing usable: unknown, never a skew.
    finally:
        adapter.stop()


def adapter_contracts(config: Config, *, timeout: float = PROBE_TIMEOUT) -> dict[str, int | None]:
    """Each configured adapter's contract — announced, else last refused, else ``None``."""
    answers: dict[str, int | None] = {}
    running: list[tuple[SubprocessAdapter, threading.Thread]] = []
    for key in sorted(config.adapter_cmds):
        command = config.adapter_cmd(key)
        if command is None:
            continue
        adapter = SubprocessAdapter(key, command, config.root)
        thread = threading.Thread(target=_announce, args=(adapter, key, answers), daemon=True)
        thread.start()
        running.append((adapter, thread))
    deadline = time.monotonic() + timeout
    for adapter, thread in running:
        thread.join(max(0.0, deadline - time.monotonic()))
        if thread.is_alive():
            adapter.kill()  # A parked handshake read returns once the child dies.
    refused = read_refusals(config.db_path)
    return {key: answers.get(key, refused.get(key)) for key in sorted(config.adapter_cmds)}


def installed_from() -> Path | None:
    """The directory a non-editable install was built from (``direct_url.json``), else ``None``.

    An editable install follows its checkout live, so it can never lag it (418).
    """
    try:
        raw = importlib.metadata.distribution("code-atlas").read_text("direct_url.json")
        record = json.loads(raw or "null")
    except (importlib.metadata.PackageNotFoundError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    url, dir_info = record.get("url"), record.get("dir_info")
    if not isinstance(url, str) or not url.startswith("file:"):
        return None
    if isinstance(dir_info, dict) and dir_info.get("editable"):
        return None
    return Path(url2pathname(urlparse(url).path)).resolve()


def same_checkout(command: Sequence[str] | None, source: Path | None) -> bool:
    """Whether an adapter's argv launches a file inside the directory the core was built from."""
    if not command or source is None:
        return False
    for part in command:
        path = Path(part)
        if path.is_absolute() and path.resolve().is_relative_to(source):
            return True
    return False


def contract_fix(
    refused: AdapterContractError,
    command: Sequence[str] | None,
    *,
    source: Path | None = None,
    release: str | None = None,
) -> str:
    """The fix for a refused handshake: which half is older, and the step that moves it (418)."""
    from code_atlas.build_info import UNKNOWN_VERSION, package_version

    release = package_version() if release is None else release
    tag = f" (`git checkout v{release}`)" if release != UNKNOWN_VERSION else ""
    older_adapter = refused.announced < contract.CONTRACT_VERSION
    template = OLDER_ADAPTER_FIX if older_adapter else OLDER_CORE_FIX
    fix = template.format(
        key=refused.key, announced=refused.announced, core=contract.CONTRACT_VERSION, release=tag
    )
    if same_checkout(command, source):
        fix += SAME_CHECKOUT_CLAUSE.format(source=source)
    return fix
