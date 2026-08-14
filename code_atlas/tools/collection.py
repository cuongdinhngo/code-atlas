"""The shared ``collection`` reconciliation block (task 082, extended by 092).

Two tools publish it — ``get_index_status`` (verbose) and ``build_or_update_index`` (standard) —
so it lives beside them rather than being reached for across a tool module (cf. ``reach_shared``).
"""

from code_atlas.store import INDEXED_SUFFIXES_KEY, GraphStore


def collection_field(
    store: GraphStore, *, ignore_sources: bool = False
) -> dict[str, object] | None:
    """The reconciliation block, or ``None`` for a pre-082 index (task 082).

    Lets an outsider reconcile ``files`` end to end without reading source:
    ``collected - skipped.suffix - skipped.ignore == kept``, and ``kept + stubs == files``.
    ``skipped.untracked`` is beside that partition (task 092) — not in ``collected``.
    ``skipped.ignore_sources`` is verbose-only (task 095); ``ignore`` stays the int so 082 closes.
    """
    census = store.collection_census()
    if census is None:
        return None
    suffixes = store.get_meta(INDEXED_SUFFIXES_KEY)
    skipped: dict[str, object] = {
        "suffix": census["skipped_suffix"],
        "ignore": census["skipped_ignore"],
        "untracked": census.get("skipped_untracked", 0),
    }
    if ignore_sources:
        sources = store.ignore_source_counts()
        if sources:
            skipped["ignore_sources"] = sources
    return {
        "collected": census["collected"],
        "skipped": skipped,
        "kept": census["kept"],
        "indexed_suffixes": suffixes.split(",") if suffixes else [],
    }
