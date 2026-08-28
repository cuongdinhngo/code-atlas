---
id: 189
slug: a-twin-is-a-container-fact-not-a-path-fact
title: 'A twin is a container fact, not a path fact — `shared_subtree_with_subject` ranks the real twin BELOW same-region noise on the anchor''s layout'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [181, 171, 165]
---

## Why this exists

Filed by **181**, which implemented the basis its Scope 3 delegated, **measured it, and declined to
ship it.** The measurement is the ticket:

```
subject : src/alpha/model/member/ModelMember.php
siblings: src/beta/model/member/ModelMember.php        <- the answer the caller wants
          src/alpha/vendor/lib000/Unrelated0.php  ... x40  <- share only the method NAME

rank_sibling_sites(..., subject_file=subject) -> basis "shared_subtree_with_subject"
  position 1  : src/alpha/vendor/lib000/Unrelated0.php     <- same region, so it wins
  position 41 : src/beta/model/member/ModelMember.php  <- the answer, LAST
```

Pinned as `test_the_subtree_basis_would_rank_the_real_twin_BELOW_the_noise`.

**171's basis is right for the case it was built for and wrong for this one.** A subject's *twins*
live in **sibling regions** (`alpha` / `beta` / shared), while same-name *noise* lives **inside the
subject's own region**. Shared-subtree depth measures exactly the wrong axis: it rewards being near,
and a twin is by definition far.

So 181 shipped `sibling_definitions_ranked: false` plus a cap for path seeds, because an honest
*"cannot rank"* beats a `ranked: true` whose first row is noise — that would re-create 181's own
defect with a better-sounding label.

## The discriminator that would work, and why 181 did not use it

*"Is this sibling a twin of my class, or a same-named method on an unrelated one?"* is a question
about the **container**, not the path. `\Alpha\ModelMember::getName` and `\Beta\ModelMember::getName`
share a container trailing name; `\Vendor\Unrelated0::getName` does not.

The data is already fetched. `impact._split_twinned` holds both the subject row and the sibling rows
before `definition_sites` shapes them — and `definition_sites` (`nav_result.py`) publishes only
`{file, line, kind}`, dropping `qualified_name`. So using the container means one of:

1. **Rank on it without publishing it.** Cheapest, and it ranks on evidence the payload does not
   show — the reader sees `ranked_by: <container>` and cannot check a single row against it. R5.5's
   territory: a stated basis the payload cannot support.
2. **Publish the container per site.** Honest and checkable, but it adds bytes to every sibling row on
   every tool that discloses one (165/168/171/181's four call sites), which is exactly the cost axis
   181 was filed to reduce. Needs measuring against 181's ~1.05 KB.
3. **Publish it only for the unranked/capped case**, where the list is already 10 rows. Cheap, and it
   makes the field asymmetric between the ranked and unranked shapes — a new thing to explain.

## Scope

1. Decide between the three above, with the byte cost measured against 181's capped ~1.05 KB.
2. If a container basis ships, it is a **third** basis value beside `shared_subtree_with_subject`, and
   the choice between them is data-driven per call — not a global switch. Record how the choice is made
   and why it is not a threshold (161 AC1).
3. **Re-examine `shared_subtree_with_subject` itself.** If a twin is a container fact, the subtree
   basis may be wrong for `find_callers`/`find_references` too — round 12's case A worked only because
   it had **two** siblings and no noise to outrank. Measure it on a noisy subject before keeping it.

### Explicitly not in scope

- Dropping sites from a ranked list (171's rule stands).
- Resolving the binding (161's AC1 deviation).
- 181's cap and its `ranked` verdict — both shipped and both stay.

## Constraints

- **R5.5** — the payload says what it ranked by, and a stated basis the payload cannot support is
  worse than none.
- **Cost** — 171's budget: a sort over rows already fetched, no query per sibling. Any published field
  is measured against 181's ~1.05 KB.
- **061** — no-sibling and one-sibling payloads stay byte-identical.
- **R6.7** — one ordering site, shared by all four consumers.
- **R1.1** — `::` is the contract's member separator (CONVENTION §3), not a language fact; no branch.

## Acceptance criteria

1. A noisy subject ranks its real twin **first**, pinned on a fixture that mirrors the region layout
   above — and the test fails under `shared_subtree_with_subject`.
2. Whichever option is chosen, the basis a payload names is one the payload's own rows can be checked
   against, or the design records why not (R5.5).
3. Scope 3's re-examination is recorded: `shared_subtree_with_subject` is kept for the qname path with
   a measurement, or replaced.
4. Byte cost measured against 181's capped figure.
5. 061, R4.2, R1.1, no contract bump (R3).

## References
Filed by [181](181_sibling-definitions-fallback-is-a-dump-not-a-ranking.md) with the measurement
above (`tests/test_sibling_disclosure_is_a_ranking_or_says_not.py`). Round 12 §9.a (cases A and B),
§12.d. `code_atlas/tools/nav_result.py` (`rank_sibling_sites`, `definition_sites`);
`code_atlas/tools/impact.py` (`_split_twinned` holds the rows). Related:
[171](171_sibling-definitions-fires-on-most-calls-and-is-unranked.md) (the basis under review),
[165](165_find-callers-splits-across-twins-and-says-reason-ok.md).
