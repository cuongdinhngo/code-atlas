"""The ``config_*`` payload fields — which config answered, and whether it still matches disk (175).

164 stamped *which code* answered and 170 made that verdict live. Nothing stamped *which config*
answered — and config decides what the index even contains, so a silently stale read costs a whole
build: the field episode edited `.code-atlas.toml`, built, and got `wrote.files: 0` describing the
old world.

Two tools publish it — ``build_or_update_index`` (the moment a divergence costs a build) and
``get_index_status`` (where ``server_build`` already rides) — so it lives beside them rather than
being reached for across a tool module (cf. ``collection``). Deliberately **not** on nav payloads:
the code axis already costs 91 B unconditionally there, and a second standing tax needs a reason
better than symmetry.
"""

from __future__ import annotations

from code_atlas.config import Config, config_stale
from code_atlas.store import CONFIG_IDENTITY_KEY, GraphStore

CONFIG_BUILD = "config_build"
CONFIG_STALE = "config_stale_process"
INDEX_CONFIG_BUILD = "index_config_build"


def attach_config_provenance(
    payload: dict[str, object], config: Config, store: GraphStore | None = None
) -> None:
    """Name the running config, and say whether the disk still matches it.

    ``config_stale_process`` is stated either way, never omitted: 170 learned omit-when-empty is
    right for a value and wrong for a **verdict** — absence and "checked, still matching" are
    different claims. ``index_config_build`` appears only when the index was built by a *different*
    config than the one running, because equal ids are a fact the reader can already see (061).
    """
    if not config.identity:
        return  # A hand-built Config never resolved from disk; it has nothing to compare.
    payload[CONFIG_BUILD] = config.identity
    payload[CONFIG_STALE] = config_stale(config)
    if store is None:
        return
    built_by = store.get_meta(CONFIG_IDENTITY_KEY)
    if built_by and built_by != config.identity:
        payload[INDEX_CONFIG_BUILD] = built_by
