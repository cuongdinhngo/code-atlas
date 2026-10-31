---
id: 430
slug: limits-and-containment
title: "The indexed repo cannot exhaust code-atlas or reach past it — every read, regex, reply and subprocess is bounded, every path contained, and adapters get a scrubbed environment"
phase: 2
milestone: Trust
status: done
depends_on: [423]
---

## Why this exists

Containment covers most paths but not all: a configured stub root's files are walked unchecked
(342), read-through repair re-parses a file swapped for a link out (375), and the project file's
`host_root` / `container_root` are ungated (341). Resource use is bounded unevenly: no per-file
size cap before a parser, no cap on an adapter's reply line, repo-supplied regexes (architecture
rules) run without a limit, the adapter preflight has no timeout, and caps read from the project
file are not clamped. Adapter subprocesses inherit the whole environment, API keys and tracker
tokens included. git still reads the indexed repo's environment-driven config (`GIT_*` variables
the user's shell may carry).

## Acceptance

One fixture per limit, each seen failing first (R6.5):

1. **Size and reply caps:** a file above `CA_MAX_FILE_BYTES` (default named) is skipped and
   counted, never truncated silently; an adapter reply line above a cap fails that file loudly.
2. **Regex limit:** a repo-supplied pattern is length- and feature-limited (or run with a timeout
   engine); a catastrophic pattern is refused with the rule named.
3. **Timeouts and clamps:** every subprocess (adapter preflight included) has a timeout; every cap
   read from `.code-atlas.toml` is clamped to a ceiling written in the code.
4. **Containment complete:** stub-root files contained (`followlinks=False`, `resolves_inside`);
   read-through repair refuses a file that now resolves outside (closes 375's residual);
   `host_root` / `container_root` gated like `adapter_cmd`; reads that cross the trust line use
   `O_NOFOLLOW`.
5. **Scrubbed environments:** adapters run with an allow-listed environment (no `*_TOKEN`,
   `*_KEY`, `ANTHROPIC_*`, `GH_*`); git runs with `GIT_*` variables other than the ones
   code-atlas sets removed (SEC-IN-13, SEC-IN-14).
6. `generate_onboarding`'s `.code-atlas/onboarding/` cache is written through `containment`, with
   420's modes (`0700`/`0600`), closing 420's residual (SEC-IN-04, SEC-IN-12). A test asserts SQLite
   extension loading is off on every connection the store opens (SEC-IN-05).
7. The BACKLOG follow-ups these close (341, 342/375 symlink residuals, parser-OOM cap, 420's
   cache modes) leave the list in the same commit.

## Call sites

`code_atlas/adapter.py`, `code_atlas/indexer.py`, `code_atlas/config.py`,
`code_atlas/containment.py`, `code_atlas/gitutil.py`, stub-root collection, read-through repair,
architecture-rule loading, `onboarding_llm/cache.py`; standard rows SEC-IN-01, 03..05, 09..14.

<!-- ===== MANGO WORKING DOC (below this line is NOT part of the raw ticket) ===== -->

## Session status

- **KEY:** 430 · **work_doc_mode:** embed · **Current phase:** 5 finalise · **Next action:** the maintainer ratifies W1–W3 and merges after #123.
- `TRACK: backend` · Run mode: `autorun 427 - 430 - 424 - 425 - 428 with skipped reviewer` — `REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.
  The handover delegates decisions, so a want-decision is `ASSUMED`, never silent.
- Branch `feat/430-limits-and-containment`, **stacked on `feat/427-distribution-pinning`** (#123).
  Contract `.mango/run-contract-430.txt`. RECONCILE t0: 4 declared | 2 re-run | 0 holding | 2 BROKEN | 2 UNBOUND | 0 could-not-run.

## Phase 0 — refine

`PREMISE: 10 reference(s) checked | 0 missing | 0 ambiguous (surfaced, not blocking)`
`RECALL: 2 claim(s) surfaced | 0 by symbol | 2 by handle | 0 by area | 0 by finding | 0 retired skipped — advisory (blocks nothing)`
`REFINE: 11 unresolved surfaced | 3 want-decision asked | 8 how-decision resolved+cited | 3 ASSUMED | skip: no`

**Premise.** `code_atlas/adapter.py`, `indexer.py`, `config.py`, `containment.py`, `gitutil.py`,
`architecture_rules.py`, `enrichment.py`, `tools/freshness.py`, `tools/generate_onboarding.py`, `store.py` resolve.
`onboarding_llm/cache.py` already writes through `containment` (`cache.py:50-53`); the cache AC6 means is
`generate_onboarding`'s, written with plain `mkdir`/`write_text` (`tools/generate_onboarding.py:415, 458, 462-466`).
AC7's follow-ups are not in BACKLOG's list (an explorer grep for 341, 342, 375, OOM, cache modes found none):
they live in SECURITY.md's *Known limitations*, which is where this ticket removes them.
Recall (type 2, by handle): 410-C1 `a-word-list-is-not-a-grammar` (the regex limit reads the pattern's parse,
not its text); 413-C1 `validate-a-parameter-before-the-first-return` (every path to a repair checks containment).

**Exposure** was a read-only explorer map (1 dispatch, 87,965 tokens) of fourteen call-site questions; its
findings are the citations below.

| # | Decision | Class | Resolution |
|---|---|---|---|
| H1 | where the size cap acts | how | the core never sends bytes (`adapter.py:~196` sends a path), so the cap acts in `collect` before a file is queued; an oversize file is skipped and counted in the build's census, never truncated |
| H2 | reply-line cap | how | `_read_line` (`adapter.py:318`) reads with a limit; a line that reaches it fails that file (`ok: false`, reason named) |
| H3 | which regexes are repo-supplied | how | `architecture_rules.py:311/476` (rule `name` patterns), `enrichment.py:1145` (`key_pattern`), `enrichment.py:1213` (indirection rules); path globs go through `ignore.translate_path_pattern`, which escapes, and an adapter's `symbol_shapes` comes from the install, not the repo |
| H4 | how a pattern is limited | how | parse it (`re._parser`, the grammar `re` itself uses) and refuse a pattern over 512 characters, a backreference, or a repeat inside a repeat; the refusal names the rule |
| H5 | subprocess timeouts | how | git has one (`gitutil.py:251`); the adapter handshake reads without one outside a build's watchdog (`adapter.py:_read_handshake`) and gets `adapter_timeout`; preflight spawns nothing (`preflight.py:99-111`) |
| H6 | clamps | how | `_as_int` (`config.py:438`) gains a per-key ceiling for values read from the project file; the environment is the operator's and is not clamped |
| H7 | stub roots | how | a root that does not resolve inside the repo is skipped, and so is a file link that leads out (`indexer.py:1023-1047`) |
| H8 | read-through repair | how | `reparse_file` (`indexer.py:842`) refuses a path that no longer resolves inside, and `FreshnessGuard.ensure` answers it as not current |
| W1 | the size cap's default | want | **ASSUMED (awaiting ratification):** `CA_MAX_FILE_BYTES` defaults to 4 MiB (4,194,304); a project file may lower it, never raise it past 64 MiB |
| W2 | the adapter environment allow-list | want | **ASSUMED (awaiting ratification):** `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`, `LC_*`, `TZ`, `TMPDIR`/`TMP`/`TEMP`, the Windows process variables (`SYSTEMROOT`, `COMSPEC`, `PATHEXT`, `WINDIR`, `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`), and the runtimes' own homes (`COMPOSER_HOME`, `NODE_PATH`); nothing else — `CA_*` left out in review (no adapter reads the environment, and a `CA_*` variable could carry a secret) |
| W3 | git's environment | want | **ASSUMED (awaiting ratification):** every `GIT_*` variable is dropped except the ones code-atlas sets; a `GIT_DIR` a host hook exports no longer redirects code-atlas's reads |

## Phase 1 — analysis

`SECTIONS: 3 found (Why this exists · Acceptance · Call sites) | 3 decomposed | ROWS: C=1 R=0 G=1 AC=7`
`CLARIFICATION: 11 raised | 11 self-resolved (cited) | 0 for human decision`
`TRACK: backend — 0/16 touched files under UI paths`
`SCOPE: L`
`TIER: full`
`STRUCTURE: native`

W1–W3 count as self-resolved because the handover handed them back; each stands `ASSUMED` for the maintainer.

| ID | Source | Verbatim | Interpretation | Status |
|---|---|---|---|---|
| G1 | Why | "cannot exhaust code-atlas or reach past it" | every read, regex, reply and subprocess bounded; every path contained | ⚠ |
| AC1 | Acc 1 | "skipped and counted, never truncated silently … fails that file loudly" | H1, H2, W1 | ⚠ |
| AC2 | Acc 2 | "a catastrophic pattern is refused with the rule named" | H3, H4 | ⚠ |
| AC3 | Acc 3 | "every subprocess … has a timeout; every cap … clamped" | H5, H6 | ⚠ |
| AC4 | Acc 4 | "stub-root files contained … repair refuses … `host_root` / `container_root` gated … `O_NOFOLLOW`" | H7, H8; host roots behind `CA_TRUST_PROJECT_FILE`; a contained read opens with `O_NOFOLLOW` and checks the descriptor is the file it resolved | ⚠ |
| AC5 | Acc 5 | "allow-listed environment … `GIT_*` … removed" | W2, W3 | ⚠ |
| AC6 | Acc 6 | "cache is written through `containment` … extension loading is off" | `generate_onboarding`'s cache via `make_private_dir`/`safe_write`; a test asserts `load_extension` is refused on a store connection | ⚠ |
| AC7 | Acc 7 | "follow-ups these close … leave the list" | SECURITY.md's two *Known limitations* bullets (stub roots/repair, cache modes) go; no BACKLOG line exists | ⚠ |
| C1 | Call sites | "standard rows SEC-IN-01, 03..05, 09..14" | each row drops `open: 430` and names its test | ⚠ |

`BASELINE: green — Docker on feat/427-distribution-pinning at 3795bb81 (5224 passed, 8 skipped)`

`RULE SECTIONS: 7 applicable — 7 by change-type | 0 by recalled handle — §1 (change-type) ✅ R1.1: no language branch; limits live in the core, the adapters untouched · §3 (change-type) N/A because no contract vocabulary changes; the reply cap is a transport limit · §4 (change-type) ✅ R4.2: a skipped file is skipped the same way every build · §5 (change-type) ✅ R5.1: an oversize reply fails one file, never the build; R5.3: a refused pattern is a loud config error · §6 (change-type) ✅ R6.5: each limit seen failing first · §7 (change-type) ✅ R7.2, R7.5, R7.6 · §9 (change-type) ✅ R9.1, R9.2, R9.3, R9.6`

## Phase 2 — design

`HANDLES: 2 recalled | 2 traced (command + result) | 0 does not apply (reason) | 0 unanswered`

- 410-C1: the regex limit walks `re._parser.parse(pattern)` for `GROUPREF` and nested `MAX_REPEAT`/`MIN_REPEAT`;
  no text pattern decides it.
- 413-C1: the containment check sits in `reparse_file`, the one function every repair path reaches
  (`search_symbol.py:385`, `file_outline.py:79`, `read_symbol.py:265`, `freshness.py:147`), so no caller returns first.

**Approach.**
1. **Limits module** (`code_atlas/limits.py`, new): `MAX_FILE_BYTES` default and ceiling, `MAX_REPLY_BYTES`,
   per-key ceilings for project-file caps, and `checked_pattern(pattern, origin)`.
2. **Size cap:** `collect` skips a file over the cap and counts it (`oversize` in the build census and its meta);
   **reply cap:** `_read_line` reads with a limit and fails the file when it is hit.
3. **Patterns:** architecture-rule names, `key_pattern` and indirection rules compile through `checked_pattern`;
   a refusal is a `ConfigError` naming the rule.
4. **Timeouts and clamps:** the handshake read is bounded by `adapter_timeout`; `_as_int` clamps project-file values.
5. **Containment:** stub roots and their files contained; `reparse_file` refuses an escaped path; `host_root` /
   `container_root` from the project file need `CA_TRUST_PROJECT_FILE=1`; `containment.read_bytes(root, path)` opens
   with `O_NOFOLLOW` and checks the descriptor's identity, used by the digest, the fingerprint and `read_symbol`'s
   source read.
6. **Environments:** the adapter `Popen` takes an allow-listed `env`; `gitutil._run` drops foreign `GIT_*` variables.
7. **Onboarding cache:** written with `make_private_dir` + `safe_write`; a test asserts extension loading is refused.
8. Docs: SECURITY.md (guarantees widen, two limitations go), SECURITY_STANDARD rows, README env table
   (`CA_MAX_FILE_BYTES`), CHANGELOG *Unreleased*.

**Rejected:** a timeout regex engine (`regex` package) — a new dependency for a pattern a parse can refuse
(R8.2); truncating an oversize file to its first N bytes — a partial parse reads as the whole file.

**Change list:** `code_atlas/limits.py` (new), `code_atlas/adapter.py`, `code_atlas/indexer.py`,
`code_atlas/config.py`, `code_atlas/containment.py`, `code_atlas/gitutil.py`, `code_atlas/architecture_rules.py`,
`code_atlas/enrichment.py`, `code_atlas/tools/freshness.py`, `code_atlas/tools/generate_onboarding.py`,
`code_atlas/tools/read_symbol.py`, `SECURITY.md`, `README.md`, `docs/SECURITY_STANDARD.md`, `CHANGELOG.md`, tests;
bookkeeping (`docs/BACKLOG.md`, `docs/TOKEN_LEDGER.md`, `docs/LESSONS.md`, this file).

**Proving tests:** `tests/test_limits_and_containment.py` (new; one arm per limit) — each arm seen red on the base.

`EXCLUSIONS: 0 recorded | 0 with a checkable expiry | 0 recurring (class seen ≥ 3 → discharged/escalated) | 0 with an overdue predecessor | 0 input-shape-dependent AC(s) | 0 proven on a real corpus`

## Phase 3 — execute

`implementer` landed Approach 1–8 in `06c8a88a`…`01b98d53` (7 commits). **Verification sweep.** File axis: the
change list plus recorded deviations — `code_atlas/source_slice.py` (where `read_symbol`'s source read lives),
`code_atlas/tools/collection.py` (the `oversize` count in the census), `docs/TOOLS.md` (the new knob, derived by
`test_orientation`), and the two module-count guards (107 → 108). Behaviour axis: Approach 1–8 as approved;
`_digest`/`_whitespace_fingerprint` stream through `containment.open_inside` instead of loading the file; an
over-long reply restarts the adapter and fails one file; oversize and escaped paths are refused in `parse_files`
as well as `reparse_file`, so the overlay and `read_symbol` paths are covered.

**Seen failing (R6.5).** `tests/test_limits_and_containment.py` on a worktree of the base `4fb9f998`: 46 failed,
4 passed (the positive "normal pattern still loads" guards; extension loading, red only on a base sabotaged with
`enable_load_extension(True)`). Not exercised: the `O_NOFOLLOW` flag on its own — the descriptor-identity check
that backs it is red on the base.

## Phase 4 — review

`REVIEWER: OFF (--no-reviewer)` · `CHALLENGER: ON`.

- **`challenger` round 1** (ticket-blind, 70,803 tokens): 10 met · 4 partly met · 1 not met · 3 can't tell.
  Taken in `cd290a41` and `b8d4b7c6`:
  - **Important 1** — the regex limit allowed repeated alternation (`(a|aa)+$`, 10.6 s on 41 characters):
    inside a repeat that can run twice, any nested repeat or `BRANCH` is now refused; four planted patterns red
    before, refused after. `(\w|\d)+$` parses to one character class and is linear (17 µs), so it loads.
  - **Important 2** — the LLM cache read followed links: it now reads through `containment.read_text`.
  - **Important 3** — ten more repo-file readers still checked then read (orientation, enrichment ×3,
    architecture rules, records, routes, ignore, capabilities, call-site, the project file): each now reads
    through `containment`, each with a link-out test.
  - Minor, taken: `CA_*` no longer reaches an adapter (W2 narrowed); a file that cannot be stat'ed is skipped.
  - Minor, accepted: the 64 MiB reply cap (bounded; one reply per file); `architecture_diff.py:114` takes a
    path its only caller already refuses outside the root.
- **Round 2: verify-only, main loop.** The four patterns probed refused; the new arms and the standard green.

```
# review-time record (an earlier tree by design; the final-tree run is in Phase 5)
$ .venv/bin/python -m pytest -q tests/test_limits_and_containment.py tests/test_security_standard.py
154 passed in 3.73s
```

Verdict: clean (challenger only — REVIEWER: OFF), W1–W3 standing for ratification.
`Ph3/4 proven by` (all `tests/test_limits_and_containment.py`): AC1 →
`test_an_oversize_file_is_skipped_counted_and_never_sent_to_an_adapter`,
`test_a_reply_line_over_the_cap_fails_that_file_and_the_adapter_is_replaced`; AC2 →
`test_a_catastrophic_repo_pattern_is_refused_naming_the_rule`; AC3 →
`test_the_handshake_is_bounded_by_adapter_timeout_outside_a_build`,
`test_a_project_file_cap_is_clamped_and_the_environment_is_not`; AC4 →
`test_a_stub_root_that_leads_out_and_a_stub_file_that_leads_out_are_skipped`,
`test_read_through_repair_refuses_a_file_swapped_for_a_link_out`,
`test_a_project_file_mapping_root_needs_the_trust_flag_the_environment_does_not`,
`test_a_descriptor_that_is_not_the_file_resolved_is_refused`; AC5 →
`test_an_adapter_gets_an_allow_listed_environment`, `test_git_env_drops_every_git_variable_but_the_ones_code_atlas_sets`;
AC6 → `test_the_onboarding_cache_is_private_and_a_linked_cache_file_is_refused`,
`test_every_connection_the_store_opens_refuses_extension_loading`; AC7 → SECURITY.md's two limitations removed;
C1 → `test_security_standard.py`.

Reviewed at b8d4b7c6.

## Phase 5 — finalise

**Durable lesson.** 430-C1 `redos-is-overlap-not-nesting` (new, type 2). Sightings: 427-C1 +430 (the readers the
ticket did not name were found only by enumerating every reader), 410-C1 +430 and 413-C1 +430 (traced, P1).

`CLAIMS: 4 claim(s) from 4 lesson entr(ies) | T1=0 T2=4 T3=0 T4=0 T5=0 T6=0 | 0 unclassified`
`RECURRENCE: 3 recurring | 0 superseded (0 retired) | 3 promotion candidate(s)`
`FALSIFY: 3 candidate(s) checked | 3 still-true (proceed) | 0 falsified (BLOCKED) | 0 not cheaply checkable (BLOCKED)`
`RECURRING-T2: 3 type-2 claim(s) with seen ≥ 2 | 3 routed to a destination | 0 cannot promote (reason) | 0 left in lessons_path`
`PROMOTION: 3 proposed | 0 human-ratified | destinations: docs/ENGINEERING_RULES.md | mango files written: 0`

**The final gate:** the suite in Docker on the final tree, after one red run that was a real finding: the image's
SQLite (Debian bookworm) left the C-API extension loader **on**, so `load_extension` tried to open the file —
`_connect` now turns it off explicitly (`38f019d6`), and the test that caught it holds SEC-IN-05.

Ran at 38f019d6

```
$ scripts/docker-test.sh
5299 passed, 8 skipped in 663.89s (0:11:03)
$ PATH=.venv/bin:$PATH scripts/gate.sh --fast
  16 passed · 0 failed · 2 skipped
```

The loader fix is a three-line change in `store._connect`, outside the reviewed tree `b8d4b7c6`; its proof is
the review-era test going green in the image, where it was red.

### Outward actions

Under the handover: push `feat/430-limits-and-containment`; open its PR against `feat/427-distribution-pinning`.
Deferred to the maintainer: ratify W1–W3; merge after #123.

## Cost ledger

| Phase | Dispatch | Round | Tokens |
|---|---|---|---|
| 0 refine | read-only `explorer` (call-site map) | 1 | 87,965 |
| 3 execute | `implementer` | 1 | 271,384 |
| 4 review | ticket-blind `challenger` | 1 | 70,803 |
| 4 review | `implementer` (review fixes, resumed) | 2 | 314,236 |

`LEDGER TOTAL: 744,388 · top cost driver: 4 review / implementer` — main loop unmeasured.
