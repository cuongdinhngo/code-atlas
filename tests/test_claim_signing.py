"""Task 100 — an answer that signs its own claim, in one quotable line.

Proving path is **integration**: the line names the revision the INDEX describes, and that only
exists once a real git repo and a real index do. A pure-logic test over a hand-made payload would
prove the formatter and nothing about the claim.

Each degradation assertion is paired with a **positive control** on the same shape — a guard that
cannot be made to fail is not a guard (R6.5, handle ``prove-the-guard-fails``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from fastmcp import Client

from code_atlas import gitutil
from code_atlas.config import Config, load_config
from code_atlas.main import TOOL_NAMES, build_server
from code_atlas.store import (
    INDEXED_SUFFIXES_KEY,
    LAST_COMMIT_KEY,
    LAST_REF_KEY,
    GraphStore,
)
from code_atlas.tokens import estimate_tokens
from code_atlas.tools import (
    claim,
    find_callers,
    find_references,
    get_index_status,
    impact,
    impact_modules,
)
from code_atlas.tools.claim import CLAIM_KEY, CLAIM_SCHEMA, REV_CHARS
from tests.test_incremental import committed, git
from tests.test_mcp_server import committed_repo, served_config
from tests.test_nav_tools import edge, node

REPO = Path(__file__).resolve().parent.parent
# The signing section moved to the design record when the README became a decision page.
SIGNING_DOC = REPO / "docs" / "design" / "impact-and-claims.md"

SOURCE = "src/a.php"
OWNER = "\\App\\UserRepo"
SUBJECT = "\\App\\UserRepo::save"
CALLER = "\\App\\Controller::store"

# The four tools whose answers are attestations (ticket 100 Scope). The denominator they are
# checked against is derived from ``TOOL_NAMES``, never listed here (R6.7).
SIGNERS = frozenset(
    {
        impact.NAME,
        impact_modules.NAME,
        find_callers.NAME,
        find_references.NAME,
        get_index_status.NAME,
    }
)

# The opt-in is one line, not a second payload (061). Measured delta is recorded in the work doc.
CLAIM_TOKEN_CAP = 60

# One key=value token: a quoted value (inner quotes doubled), or a run of non-space chars.
_TOKEN = re.compile(r'[^\s=]+=(?:"(?:[^"]|"")*"|\S*)')

UNSIGNED_HEADING = "#### Answers deliberately left unsigned"
FIELD_PROSE = "No product code, no `src/` consumer."


def indexed_repo(root: Path, *, edges: list[dict] | None = None) -> Path:
    """A one-file git repo plus an index stamped at HEAD, with on-disk bytes matching the row.

    The hash must match the real bytes or ``FreshnessGuard`` calls the file stale and the nav
    tools answer ``index_stale`` instead of the shape under test.
    """
    root.mkdir(parents=True, exist_ok=True)
    committed(root, {SOURCE: "<?php class UserRepo {}\n"})
    digest = hashlib.sha256((root / SOURCE).read_bytes()).hexdigest()
    db_path = root / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with GraphStore(db_path) as store:
        store.upsert_file(SOURCE, digest, "php")
        store.replace_file_rows(
            SOURCE,
            [
                node("Class", "UserRepo", OWNER, SOURCE),
                node("Method", "save", SUBJECT, SOURCE),
                node("Method", "store", CALLER, SOURCE),
            ],
            edges or [],
        )
        store.set_meta(LAST_COMMIT_KEY, git(root, "rev-parse", "HEAD"))
        ref = gitutil.head_ref(root)
        if ref is not None:
            store.set_meta(LAST_REF_KEY, ref)
        store.set_meta(INDEXED_SUFFIXES_KEY, ".php")
    return db_path


def configured(root: Path, db_path: Path) -> Config:
    return load_config(root, {"CA_DB_PATH": str(db_path)})


def fields(payload: Mapping[str, object]) -> dict[str, str]:
    """Split the claim line back into keys — it is machine-readable, or it is prose.

    Deliberately NOT ``shlex``: it applies POSIX escaping and would eat the backslashes in a PHP
    FQN. The line's grammar is space-separated ``key=value`` with double quotes and no escapes.
    """
    line = str(payload[CLAIM_KEY])
    schema, _, rest = line.partition(" ")
    assert schema == CLAIM_SCHEMA, line
    found: dict[str, str] = {}
    for token in _TOKEN.findall(rest):
        key, _, value = token.partition("=")
        found[key] = (
            value[1:-1].replace('""', '"') if value.startswith('"') else value
        )
    return found


def schemas(server: Any) -> dict[str, Any]:
    async def once() -> dict[str, Any]:
        async with Client(server) as client:
            return {tool.name: tool.inputSchema for tool in await client.list_tools()}

    return asyncio.run(once())


def unsigned_section(text: str) -> str:
    _, _, rest = text.partition(UNSIGNED_HEADING)
    section, _, _ = rest.partition("\n## ")
    return section


def test_impact_modelled_zero_is_signed_with_subject_question_answer_and_revision(
    tmp_path: Path,
) -> None:
    """AC1 (proving test) — the claim the field session held, rendered so a reader can re-run it.

    ``answer == seeds`` IS the modelled zero: the blast radius is the seed itself, so nothing
    else depends on it — and ``seeds_dropped=0`` says the walk really covered what was asked.
    """
    db_path = indexed_repo(tmp_path)
    answer = impact.create(configured(tmp_path, db_path))(qnames=[SUBJECT], sign=True)
    found = fields(answer)

    assert found["tool"] == impact.NAME
    assert found["subject"] == SUBJECT
    assert found["question"] == impact.QUESTION
    assert found["answer"] == found["seeds"] == "1"
    assert found["seeds_dropped"] == "0"
    assert found["frontier_skipped_non_resolved"] == "0"
    assert found["rev"] == git(tmp_path, "rev-parse", "HEAD")[:REV_CHARS]
    assert found["ref"] == gitutil.head_ref(tmp_path)
    assert found["index"] == "current"


def test_impact_refuses_to_sign_an_answer_whose_subject_never_resolved(tmp_path: Path) -> None:
    """C5, revised by task 102 — the payload now tells the two apart (``seeds_dropped: 1``), and
    the refusal survives on its own reason: a question nothing answered would be signed
    ``answer=0`` for a subject the index never held."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    real = impact.create(config)(qnames=[SUBJECT], sign=True)
    absent = impact.create(config)(qnames=["\\App\\Nope"], sign=True)

    assert CLAIM_KEY in real  # positive control: signing does happen on this fixture
    assert absent["results"] == [] and absent["seeds_dropped"] == 1
    assert CLAIM_KEY not in absent


def test_a_behind_index_says_so_in_the_line(tmp_path: Path) -> None:
    """AC2 — the line discloses that HEAD has moved past the tree the answer describes."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    current = fields(impact.create(config)(qnames=[SUBJECT], sign=True))
    committed(tmp_path, {"src/b.php": "<?php class B {}\n"}, "second")
    behind = fields(impact.create(config)(qnames=[SUBJECT], sign=True))

    assert current["index"] == "current"  # positive control
    assert behind["index"] == "behind"
    assert behind["rev"] == current["rev"]  # the answer still names the tree it describes


def test_a_heuristic_hit_is_never_claimed_resolved(tmp_path: Path) -> None:
    """AC2 — one weak hit makes the whole answer weak; the line may not claim the stronger tier."""
    call = edge("CALLS", CALLER, "save", SOURCE, target_qname=SUBJECT)
    weak_call = edge("CALLS", CALLER, "save", SOURCE, target_qname=SUBJECT, tier="HEURISTIC")
    strong, weak = tmp_path / "strong", tmp_path / "weak"
    strong_db = indexed_repo(strong, edges=[call])
    weak_db = indexed_repo(weak, edges=[weak_call])

    strong_line = fields(
        find_callers.create(configured(strong, strong_db))(qname=SUBJECT, sign=True)
    )
    weak_line = fields(find_callers.create(configured(weak, weak_db))(qname=SUBJECT, sign=True))

    assert strong_line["tier"] == "RESOLVED"  # positive control
    assert weak_line["tier"] == "HEURISTIC"
    assert weak_line["answer"] == "1"
    assert "RESOLVED" not in str(weak_line)


def test_find_references_carries_the_authoritative_caveat(tmp_path: Path) -> None:
    """AC2 — an all-DYNAMIC answer is a candidate list; the line says so rather than counting."""
    mention = edge(
        "REFERENCES", CALLER, "UserRepo", SOURCE, target_qname=OWNER, tier="DYNAMIC"
    )
    db_path = indexed_repo(tmp_path, edges=[mention])
    found = fields(find_references.create(configured(tmp_path, db_path))(qname=OWNER, sign=True))

    assert found["tier"] == "DYNAMIC"
    assert found["authoritative"] == "false"


def test_the_default_payload_is_byte_identical_and_carries_no_claim(tmp_path: Path) -> None:
    """AC3 — the opt-in is purely additive: same keys, same order, one appended field."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    plain = impact.create(config)(qnames=[SUBJECT])
    signed = impact.create(config)(qnames=[SUBJECT], sign=True)

    assert CLAIM_KEY not in plain
    without = {key: value for key, value in signed.items() if key != CLAIM_KEY}
    assert json.dumps(plain) == json.dumps(without)


def test_the_opt_in_costs_one_line(tmp_path: Path) -> None:
    """AC3 / 061 — the measured delta, pinned so a future field cannot grow it silently."""
    db_path = indexed_repo(tmp_path)
    config = configured(tmp_path, db_path)
    plain = estimate_tokens(json.dumps(impact.create(config)(qnames=[SUBJECT])))
    signed = estimate_tokens(json.dumps(impact.create(config)(qnames=[SUBJECT], sign=True)))

    assert 0 < signed - plain <= CLAIM_TOKEN_CAP


def test_sign_is_published_on_exactly_the_attesting_tools(tmp_path: Path) -> None:
    """AC5 + design assumption A2 — over a live client, so FastMCP's real schema is the judge."""
    committed_repo(tmp_path, "src/a.aa")
    published = schemas(build_server(served_config(tmp_path)))

    assert set(published) == set(TOOL_NAMES)  # denominator derived, never listed (R6.7)
    signing = {
        name for name, schema in published.items() if "sign" in schema["properties"]
    }
    assert signing == SIGNERS
    assert set(TOOL_NAMES) - SIGNERS  # positive control: the exclusion set is not empty


def test_the_docs_show_the_field_claim_beside_the_line_that_would_have_signed_it() -> None:
    """AC4 — the prose that shipped, next to the artifact that was already on screen."""
    text = SIGNING_DOC.read_text(encoding="utf-8")

    assert FIELD_PROSE in text
    assert f"{CLAIM_SCHEMA} tool={impact.NAME}" in text


def test_every_unsigned_tool_is_recorded_with_the_caveat_it_would_have_lost() -> None:
    """AC5 — the exclusion list is a finding the docs carry, not an omission (C5)."""
    section = unsigned_section(SIGNING_DOC.read_text(encoding="utf-8"))

    assert section, f"{SIGNING_DOC.name} is missing the {UNSIGNED_HEADING!r} section"
    for name in sorted(set(TOOL_NAMES) - SIGNERS):
        assert f"`{name}`" in section, name
    for name in sorted(SIGNERS):
        assert f"`{name}`" not in section, name  # positive control


def test_a_parse_failure_rides_the_line_at_every_detail_level(tmp_path: Path) -> None:
    """Review finding 1 — ``parse_failures`` is only a payload key at standard/verbose, so a
    caveat sourced from the payload vanishes at ``minimal`` while the failures are real."""
    committed(tmp_path, {SOURCE: "<?php class UserRepo {}\n"})
    db_path = tmp_path / ".code-atlas" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with GraphStore(db_path) as store:
        store.upsert_file(SOURCE, "h", "php")
        store.replace_file_rows(SOURCE, [node("Class", "UserRepo", OWNER, SOURCE)], [])
        store.upsert_file("bad.php", "h", "php", parsed_ok=False)
        store.replace_file_rows("bad.php", [], [])
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    tool = get_index_status.create(config, (get_index_status.NAME,))

    minimal = fields(tool(detail_level="minimal", sign=True))
    standard = fields(tool(detail_level="standard", sign=True))

    assert standard["parse_failures"] == "1"  # positive control: the caveat is reachable
    assert minimal["parse_failures"] == "1"
    assert minimal["answer"] == standard["answer"]


def test_a_clean_index_carries_no_parse_failure_key(tmp_path: Path) -> None:
    """The counterpart control — a caveat key is present exactly when the caveat is real."""
    db_path = indexed_repo(tmp_path)
    config = load_config(tmp_path, {"CA_DB_PATH": str(db_path)})
    found = fields(get_index_status.create(config, (get_index_status.NAME,))(sign=True))

    assert "parse_failures" not in found


def test_a_quoted_value_round_trips_and_does_not_corrupt_the_rest_of_the_line() -> None:
    """Review finding 2 — an inner quote is doubled, so the value survives and later keys still
    split. Backslashes stay literal: the grammar has no escape character."""
    payload = claim.sign(
        {"results": [], "total_count": 0},
        tool=impact.NAME,
        question=impact.QUESTION,
        subject_parts=['src/od"d.php', "\\App\\UserRepo"],
        staleness={"last_commit": "abc1234def", "last_ref": "main", "staleness": "current"},
    )
    found = fields(payload)

    assert found["subject"] == 'src/od"d.php,\\App\\UserRepo'
    assert found["rev"] == "abc1234"  # a key AFTER the quoted value still parses
    assert found["index"] == "current"
