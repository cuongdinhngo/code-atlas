---
id: 181
slug: sibling-definitions-fallback-is-a-dump-not-a-ranking
title: '`sibling_definitions` at `ranked_by: "path"` is a 93-row alphabetical dump wearing a ranking''s shape — and 91 % of the session''s disclosure bytes'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [171, 168, 169]
---

## Why this exists (field retro round 12 §12.d)

171 shipped the ordering 165's caveat needed, and round 12 fired it three times. **The good basis is
excellent and the fallback is a dump — and both arrive in the same field, with the same shape.**

*Case A — `find_references(…ModelMember)`, `sibling_definitions_ranked_by: "shared_subtree_with_subject"`:*

```
1. legacy/alpha/web/model/model/member/ModelMember.php:21   Class
2. legacy/beta/web/model/model/member/ModelMember.php:12    Class
```

**2 siblings, both exactly right** — the three-way split this anchor is defined by, named in two rows.

*Case B — `impact(paths:[ModelMember.php])`, `sibling_definitions_ranked_by: "path"`:*

```
1. legacy/alpha/web/application/interimPlan/model/index.php:57   Method
2. legacy/alpha/web/model/entity/EntityMember.php:662          Method
…  legacy/alpha/web/include/adodb/adodb-active-record.inc.php:121    Method
```

**93 entries. 42 (45 %) are real `ModelMember` twins; 51 (55 %) share only a method name** — `adodb`
internals, API controllers, `AddressModel`, `AbstractRateDetail`. `path` is alphabetical, so
`application/` sorts above `model/` and the needed twin sits at position ~6.

**The defect is not the ordering.** 171's AC held: the order is deterministic and drops nothing. The
defect is that **a sort and a ranking are indistinguishable in the payload**, so a caller who does not
branch on `ranked_by` reads case B's first row as if it were case A's. Round 12 recorded it as the
round's design finding — *fired, noticed, changed nothing*.

**It is also the round's cost headline.** Batch C's new fields cost ≈8.9 KB across a 15-call session;
**8.1 KB of that is this one block on this one call** (§6). 91 % of the disclosure bill buys a list
that is 55 % noise for the question asked.

### Why `path` is reached at all

`impact`'s twinned-seed disclosure (169) passes `subject_file=None` — a path request has no single
subject file, so the subtree basis has nothing to measure against and 171 correctly falls back. **The
fallback is doing the only honest thing available; the payload just does not say that it is a
fallback.**

## Scope

1. **The shape says which it is.** When the ordering has no evidence to rank by, the payload must
   say so in a way a caller can branch on without knowing the value vocabulary — design picks and
   records: `sibling_definitions_ranked_by: null` plus an explicit `sibling_ranking: "unranked"`, or
   a value whose name carries it. **A caller must not have to know that `"path"` means *unranked*.**
2. **Cap the unranked list, and name the cap.** An unranked 93-row list is a dump; `find_orphans`
   already has the vocabulary for this shape (`walk_truncated`). Ranked lists stay uncapped — nothing
   is dropped when position is meaningful.
3. **Give `impact`'s path seeds a basis if a cheap one exists.** A path request has no subject file,
   but it does have the **seed's own file** per twinned seed. Whether ranking each seed's siblings
   against that seed's path is reachable at 171's cost budget is a design question this ticket
   delegates — and if it is, `path` stops being reached on the tool where it does most damage.
4. **Cheap noise reduction, if it is honest.** 55 % of case B's rows share only a trailing name with
   no relationship to the subject. Whether the graph already holds something that separates *a twin
   of this class* from *a method with the same name on an unrelated class* — the sibling's own
   container kind or qname prefix — is a design question. **Recording "no, it does not" is a valid
   answer**; guessing is not (161 AC1).

### Explicitly not in scope

- Dropping sites from a **ranked** list. 171's *"noise for one question, not for every question"*
  stands.
- Resolving the binding. The edge model is qname-keyed with no target node id (161's AC1 deviation).
- Changing when the caveat fires. A frequent true caveat is not a false one.
- `find_orphans`' own refusal — [182](182_find-orphans-answers-with-rows-it-has-flagged-unreliable.md).

## Constraints

- **061** — a subject with no sibling stays byte-identical; a ranked answer with ≥ 2 siblings keeps
  today's rows and order unless the basis itself changes.
- **Cost** — 171's budget: a sort over rows already fetched, ~1.35 ms worst case. No query per
  sibling, none per caller. **A cap is a byte saving and must be measured as one.**
- **R5.5** — the payload says what it ranked by, or that it could not rank.
- **R6.7** — one ordering site, shared by `find_callers`, `find_references` and `impact`.
- **R1.1** no language branch · **R3** no bump · **R4.2** deterministic within and across bands.

## Acceptance criteria

1. An unranked disclosure is distinguishable from a ranked one **by shape, not by knowing the value
   vocabulary** — pinned on one payload of each kind, including the `impact` path-seed case.
2. An unranked list is capped, the cap is named in the payload, and the total is still reported —
   pinned; a ranked list is uncapped and byte-identical to today.
3. Scope 3's verdict is recorded: either path seeds gain a per-seed basis (pinned) or the reason they
   cannot is written down.
4. Scope 4's verdict is recorded, with the measurement or the reason it is unmeasurable.
5. No-sibling and one-sibling payloads byte-identical (061).
6. Byte delta on case B measured against the 8.1 KB field figure.
7. Determinism (R4.2), no language branch (R1.1), no bump (R3).

## References

Field retro round 12 §9.a (cases A and B in full), §12.d (the design finding), §6 (8.1 KB of 8.9 KB),
§14.a (proposed carve-out: *"do not read the top rows when `ranked_by` is `path`"*). Round 11 §12.d
is where 171 itself came from. **Provenance note:** 171's AC was proven on authored fixtures only, and
this is the property those fixtures could not test — *for a ranking, "deterministic and lossless" is a
precondition, not an acceptance criterion.*
`code_atlas/tools/nav_result.py:538-544,558`; `code_atlas/tools/impact.py:158-166`. Related:
[171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md),
[168](168_find-references-never-got-165s-twin-disclosure.md),
[169](169_impact-path-seed-walks-every-symbol-and-its-twins.md).
