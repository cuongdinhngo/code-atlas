"""A host file's embedded regions, read by the adapter that owns each region's suffix (399).

A file may carry a region written in another language: the host adapter names its byte spans, the
adapter owning the region's suffix reads them, and the rows land under the host file. Which adapter that is comes from the
handshake (suffix + the ``spans`` capability), so no language is named here (R1.1).
"""

from collections.abc import Callable, Mapping

from code_atlas import contract
from code_atlas.adapter import ParseResult
from code_atlas.store import ROW_LANGUAGE

# A region's reader: the guest's announced name and its result, or None when nothing could read it.
Reader = Callable[[Mapping[str, object]], tuple[str, ParseResult] | None]


def merge(host: ParseResult, read: Reader) -> ParseResult:
    """Append each region's rows to ``host``, host rows first; name the regions nothing read.

    Host-first keeps the host's row on a qname clash, since the store de-dupes keep-first (384).
    A guest row carries the guest's language, so the resolver's same-language gate holds (204).
    """
    if not host.ok or not host.embedded:
        return host
    nodes = list(host.nodes)
    edges = list(host.edges)
    unread: list[str] = []
    for region in host.embedded:
        answer = read(region)
        if answer is None or not answer[1].ok:
            unread.append(str(region.get("suffix")))
            continue
        language, guest = answer
        nodes += [_stamped(node, language) for node in guest.nodes if not _is_file(node, host.path)]
        edges += [_stamped(edge, language) for edge in guest.edges]
    if unread:
        nodes = [_marked(node, host.path, unread) for node in nodes]
    return ParseResult(path=host.path, ok=True, nodes=tuple(nodes), edges=tuple(edges))


def _is_file(node: Mapping[str, object], path: str) -> bool:
    """The guest's own File row: the host's already owns the path (File qname = path)."""
    return node.get("kind") == contract.FILE_KIND and node.get("qualified_name") == path


def _stamped(row: Mapping[str, object], language: str) -> dict[str, object]:
    return {**row, ROW_LANGUAGE: language}


def _marked(node: dict[str, object], path: str, unread: list[str]) -> dict[str, object]:
    """The host File, naming each region no adapter read — the index never looked (R5.6)."""
    if not _is_file(node, path):
        return node
    extra = node.get("extra")
    marked = dict(extra) if isinstance(extra, dict) else {}
    marked[contract.EMBEDDED_UNREAD_KEY] = sorted(set(unread))
    return {**node, "extra": marked}
