---
id: 281
slug: the-writes-sql-half-caveat-keys-on-language-count-not-the-emitting-adapter
title: 'The multi-language `WRITES` caveat fires on any index that covers ≥2 languages, not on the presence of a second `WRITES`-emitting adapter — correct only because SQL is the sole writer today, it is a confident over-attach the moment a second writer lands, and the honest key (which languages emit `WRITES`) is already stamped'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [278, 255, 264]
---

## Why this exists

278 (#362) made `find_references` on a `Table`/`Column` return the linked `WRITES` writer set and
attach `writes_sql_adapter_only` (`CAVEAT_WRITES_SQL_HALF`) when the answer is only the SQL half of a
multi-language repo. The gate is `_writes_answer_is_partial` (`code_atlas/tools/find_references.py:88`):

```python
def _writes_answer_is_partial(covered: str | None) -> bool:
    """True when the index covers ≥2 languages — the WRITES answer is the SQL half (278)."""
    if not covered:
        return False
    return len([name for name in covered.split(",") if name]) >= 2
```

It keys on the **count of covered languages**, not on **which languages emit `WRITES`**. Today only
the SQL adapter emits `WRITES`, so "≥2 covered languages" and "a non-SQL half exists that this answer
omits" happen to coincide, and the caveat is correct. The moment a second `WRITES`-emitting adapter
lands, the coincidence breaks: a repo covering SQL + that adapter would carry
`writes_sql_adapter_only` even though the answer already holds both writers — a confident caveat that
names a missing half that is not missing. No code changes for this to become wrong (255/264's recurring
shape: a language-count constant standing in for an edge-kind fact).

The honest signal already exists on the index. `EMITTED_KINDS_BY_LANGUAGE_KEY`
(`code_atlas/store.py:72`, stamped `code_atlas/indexer.py:1258`) records which kinds each language
emits, so "is there a covered language that emits `WRITES` and is not in this answer's set" is
answerable from the stamp, not inferred from a count.

## Scope / Deliverables

- **Key the caveat on emitters, not on language count.** Attach `writes_sql_adapter_only` (or a
  successor name if a second writer makes "sql" wrong) only when a covered language emits `WRITES` and
  is absent from the answer's contributing set — read from `EMITTED_KINDS_BY_LANGUAGE`, the same
  machinery 255/264 already use for the honesty predicate.
- **Name it for the shape, not the language.** If the caveat can now name more than SQL, the field/text
  must stop hard-coding "sql".

## Constraints

- R5.6: evidence, not inference — the caveat rides a stamped emitter fact, never a language count.
- R4.2: derived from stored rows, byte-reproducible.
- 061: a single-language or SQL-only-writer answer is unchanged; no new field where nothing is omitted.
- Do not widen 278's answer set — this ticket changes only *when the caveat fires*, not what is returned.

## Acceptance criteria

- A two-language index where the second language does **not** emit `WRITES` still attaches the caveat
  (unchanged from 278).
- A synthetic index where a second language **does** emit `WRITES`, and the answer already includes it,
  does **not** attach the caveat.
- The gate reads `EMITTED_KINDS_BY_LANGUAGE`, not `covered.split(",")` count.
- No existing 278 test changes verdict except the new emitter-based cases.

## References
`code_atlas/tools/find_references.py:88,568-570`, `code_atlas/tools/nav_result.py:702`
(`CAVEAT_WRITES_SQL_HALF`), `code_atlas/store.py:72` + `code_atlas/indexer.py:1258`
(`EMITTED_KINDS_BY_LANGUAGE`), [278](278_the-writer-set-is-computed-for-one-check-and-addressable-from-nothing.md),
[255](255_the-honesty-predicate-is-keyed-to-two-php-shaped-edge-kinds.md),
[264](264_the-honesty-predicate-is-still-one-language-s-shape-wearing-a-constant-s-name.md).
Origin: review of #362, 2026-09-15 (non-blocking follow-up).
