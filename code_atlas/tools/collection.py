"""The shared ``collection`` reconciliation block (task 082, extended by 092).

Two tools publish it — ``get_index_status`` (verbose) and ``build_or_update_index`` (standard) —
so it lives beside them rather than being reached for across a tool module (cf. ``reach_shared``).
"""

from code_atlas.store import COVERED_SUFFIXES_KEY, INDEXED_SUFFIXES_KEY, GraphStore

# Bounded so a repo with 400 extensions cannot inflate the payload (task 174). Top-N by count,
# suffix ascending as the tie-break; `suffix_kinds` says how many exist, so the cut is visible.
SKIPPED_SUFFIX_TOP_N = 10


def collection_field(
    store: GraphStore, *, ignore_sources: bool = False
) -> dict[str, object] | None:
    """The reconciliation block, or ``None`` for a pre-082 index (task 082).

    Lets an outsider reconcile ``files`` end to end without reading source:
    ``collected - skipped.suffix - skipped.ignore == kept``, and ``kept + stubs == files``.
    ``skipped.untracked`` is beside that partition (task 092) — not in ``collected``.
    ``skipped.ignore_sources`` is verbose-only (task 095); ``ignore`` stays the int so 082 closes.

    ``indexed_suffixes`` names what the graph HOLDS files for; ``claimed_suffixes`` names what the
    build was configured to index, and appears only when the two differ (task 173). Wiring an
    adapter used to move the first, under a name that reads as a claim about the index.
    """
    census = store.collection_census()
    if census is None:
        return None
    claimed = store.get_meta(INDEXED_SUFFIXES_KEY)
    covered = store.get_meta(COVERED_SUFFIXES_KEY)
    skipped: dict[str, object] = {
        "suffix": census["skipped_suffix"],
        "ignore": census["skipped_ignore"],
        "untracked": census.get("skipped_untracked", 0),
    }
    _attach_skipped_suffixes(skipped, store)
    if ignore_sources:
        sources = store.ignore_source_counts()
        if sources:
            skipped["ignore_sources"] = sources
    claimed_list = claimed.split(",") if claimed else []
    # A pre-173 index has no covered stamp: fall back to the claimed list rather than report an
    # empty graph, and say nothing about the difference we cannot know (R5.6).
    held = covered.split(",") if covered else (claimed_list if covered is None else [])
    block: dict[str, object] = {
        "collected": census["collected"],
        "skipped": skipped,
        "kept": census["kept"],
        "indexed_suffixes": held,
    }
    if held != claimed_list:
        block["claimed_suffixes"] = claimed_list
    return block


def _attach_skipped_suffixes(skipped: dict[str, object], store: GraphStore) -> None:
    """Say what ``skipped.suffix`` is MADE OF, so its total names a cost (task 174).

    Four rounds disclosed *"an adapter exists and is unwired"* and reported zero contribution. What
    would have been acted on is *"2,831 `.js` files in this repo are invisible"* — a fact about the
    reader's own repo. The core names no language (R1.1); it publishes extensions and the reader
    joins them with ``unconfigured_adapters``. ``suffix_kinds`` is the denominator for the cut.
    """
    counts = store.skipped_suffix_counts()
    if not counts:
        return
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    skipped["suffix_top"] = dict(ranked[:SKIPPED_SUFFIX_TOP_N])
    skipped["suffix_kinds"] = len(counts)
