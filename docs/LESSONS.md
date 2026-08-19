# Lessons — code-atlas

## 105 — Elect "the main subtree" by graph mass, not file count; make the real-repo check committed
104's dominant-subtree heuristic elected the top-level directory holding the most **files**. On the
`laravel/laravel` skeleton `config/` (10 flat settings files) out-counted `app/` (3 connected source
files), so the whole application collapsed into one layer — the very F1 shape 104 existed to fix. The
fix: elect by **graph mass** (Σ fan_in+fan_out), so a populous-but-disconnected directory can't
out-vote a small connected core — no directory stop-list (R2.2), no language branch (R1.1), still
deterministic. Separately, this is the 5th time an authored fixture that mirrors the code's own
assumption hid a path-shape defect; 105's durable countermeasure is a **committed, re-runnable
real-repo reporter** (`scripts/layer_report.py`) so the real check is not an ad-hoc session action.

### 105-C1 — Elect a "dominant" group by connectivity mass, not by member count
- type: 1 technical-fact
- handle: elect-by-graph-mass-not-file-count
- status: proposed (awaiting human confirm)
- seen: 105
- evidence: `code_atlas/onboarding/layers.py::_dominant_subtree` sums `fan_in + fan_out`;
  `tests/test_onboarding_layers.py::test_dominant_subtree_survives_a_config_dir_with_more_files` is
  red on the count rule, green on mass; three real repos in 105's working doc (AC2)
- area: onboarding layer assignment / graph heuristics
- destination: `gotchas_path` (a design fact about this heuristic, not a build rule)

### 105-C2 — When AC needs a real-repo judgement, ship a committed reporter, not an ad-hoc run
- type: 2 generalisable-heuristic
- handle: fixture-shape-begs-the-question
- status: proposed (awaiting human confirm)
- seen: 084, 103, 104, 086, 105
- evidence: authored fixtures hid the same class of path-shape defect across 084/103/104/086; 105 adds
  `scripts/layer_report.py` (clones+indexes the pinned repos, prints `assign_layers`) as the committed
  real-repo check
- area: test design / heuristics judged on real inputs
- note: `seen:` crosses ≥2 ticket keys → this is a **cross-ticket promotion candidate**
  (`/mango:promote`, run by the maintainer between tickets), not a within-ticket write
- destination: `rulebook_path` (a heuristic over path/graph shape must be proven on a real indexed
  repo, via a committed re-runnable check — a fixture that shares the code's assumption cannot)


## 091 — Constrain a seam's return type so a bad implementer can't break a core invariant
091 lets an LLM rename architectural layers. The obvious seam shape — `refine(assignment) -> new
assignment` — would let a hallucinating impl drop modules, invent layers, or scramble ranks, and the
core would have to defensively re-validate everything downstream. Instead the `LayerRefiner` seam
returns a **rename map** `{old_layer: new_layer}`; the core applies it. The narrow return type makes
the dangerous outcomes *unrepresentable* — coverage, module→layer membership, and dependency order are
preserved by construction, no matter what the LLM says. The applier only renames and renormalises
ranks; an empty/inapplicable map returns the input object unchanged (the off path is byte-identical to
the heuristic — AC3, proven with `to_json()` equality).

### 091-C1 — Make a seam return the delta, not a rebuilt whole, when a bad impl could corrupt invariants
- type: 2 generalisable-heuristic
- handle: seam-returns-constrained-delta-not-rebuilt-whole
- status: proposed (awaiting human confirm)
- seen: 091
- evidence: `code_atlas/onboarding/layers.py::refine_layers` applies a `{old: new}` map from
  `LayerRefiner.refine_names`; `tests/test_onboarding_llm_layers.py::test_llm_renames_weak_layers`
  asserts coverage is intact and `::test_off_by_default_is_byte_identical_to_084` pins AC3
- area: seam design / untrusted (LLM) implementers behind a Protocol
- destination: `rulebook_path` (R1.2/R7.4-adjacent — a seam whose impl may be an LLM should make
  invariant-violating outputs unrepresentable rather than re-validating them)


## 090 — "The core must never import X" is honoured most strongly by an entry point outside the core
R4.1 says the core must never import an LLM. A config-gated deferred `import onboarding_llm` inside
`main.py` would satisfy CI (the import never fires) but still *names* the LLM package in core source.
090 instead widened the core seam to `build_server(config, summarizer=None)` — the core names only the
085 `Summarizer` *type* — and put the injection in a **separate `code-atlas-llm` entry point outside
`code_atlas/`**, so the core→LLM edge is literally absent. A filesystem confinement test greps
`code_atlas/**` for any `import anthropic`/`onboarding_llm` and finds none. Mirrors how adapters live
outside the core with their own launch.

### 090-C1 — A "never import X" rule wants an out-of-core entry point, not a deferred in-core import
- type: 2 generalisable-heuristic
- handle: plugin-entry-point-keeps-the-core-import-clean
- status: proposed (awaiting human confirm)
- seen: 090
- evidence: `build_server(config, summarizer=None)` threads the seam; `onboarding_llm/server.py:run`
  injects the LLM impl; `tests/test_onboarding_llm.py::test_no_core_module_imports_an_llm` proves
  `code_atlas/**` names neither `anthropic` nor `onboarding_llm`
- area: seam placement / optional plugins
- destination: `rulebook_path` (R4.1-adjacent — where the injection of an out-of-core impl lives)


## 089 — An HTML file that must open from `file://` cannot fetch a sibling JSON
`generate_onboarding` already wrote `manifest.json`. A viewer that `fetch`ed it would pass in a
dev server and fail the moment a human double-clicked the file — the AC is "opens offline from
the filesystem". The HTML therefore **embeds** the artifact at generate time. `connect-src 'none'`
makes a later fetch a CSP violation rather than a silent `file://` miss.

### 089-C1 — Offline HTML cannot treat a sibling JSON as a runtime input
- type: 2 generalisable-heuristic
- handle: embed-what-file-cannot-fetch
- status: proposed (awaiting human confirm)
- seen: 089
- evidence: browsers block `fetch('./manifest.json')` on `file://`; 089 bakes `viewer_payload` into
  a `<script type="application/json">` tag and forbids connect
- area: generated static HTML
- destination: `rulebook_path` (R4.2/R1.2 adjacent — a generated artifact must actually be usable
  in the environment the ticket named)


## 088 — A listed `CALLS` tuple is a tool-surface pin even when `TOOL_NAMES` already grew
`test_mcp_server.CALLS` is the argument list that drives the per-tool `detail_level` contract tests.
087 registered `guided_tour` in `TOOL_NAMES` but left it off `CALLS`. 088 had to add `generate_onboarding`
there and folded `guided_tour` in as proof collateral. Same class as 085-C1 / 087-C1 (a listed integer
or listed subset that is the live surface).

### 088-C1 — A listed subset of `TOOL_NAMES` is a blast-radius hit when adding a tool
- type: 2 generalisable-heuristic
- handle: count-pin-in-blast-radius
- status: proposed (awaiting human confirm)
- seen: 088
- evidence: `tests/test_mcp_server.py` `CALLS` omitted `TOUR` after 087; execute added `TOUR` and `ONBOARD`
- area: analysis/design blast-radius tracing
- destination: `agent_brief_path` (process; same class as 085-C1 / 087-C1 — `/mango:promote` is the cross-ticket pass)


## 089 (review round) — The one line standing between a repo's filenames and a script breakout had no test
`render_viewer` escapes `<` in the embedded JSON, and it is right to: a directory named `a<` holding a
file `script>x.aa` makes the *path string* carry `</script>`, which ends the payload block and leaves
the rest of the artifact as live markup in a committed HTML file. The page's CSP does not save it —
`script-src 'unsafe-inline'` permits inline handlers, and `img-src 'none'` guarantees an
`<img onerror>` fires. Deleting the line kept the whole suite green, so nothing but reviewer memory
stopped a future edit from removing it. Also: with scripting off the "offline viewer" rendered a blank
page and never mentioned the markdown beside it.

### 089-C1 — An escape that neutralises untrusted input needs a test built from the input that defeats its absence
- type: 2 generalisable-heuristic
- handle: prove-the-guard-fails
- status: proposed (awaiting human confirm)
- seen: 089
- evidence: removing `blob.replace("<", "\\u003c")` left `tests/` green (13 passed); the mutant then
  produced `</script>` count 5, an unterminated JSON block, and a literal `<img src=x onerror=...>` in
  the generated page. The pin is a fixture whose *path* is `a</script><img ...>.aa`, not a synthetic
  string handed to the renderer
- area: generated artifacts / untrusted repo text
- destination: `rulebook_path` (R6.5 already demands a recorded red run for a guard; this is the
  narrower case — the guard is one expression inside a renderer, so only a mutant exposes it)

### 089-C2 — A page that builds every element in script must say what to read when script is off
- type: 2 generalisable-heuristic
- handle: degrade-to-the-artifact-beside-you
- status: proposed (awaiting human confirm)
- seen: 089
- evidence: the AC says "opens offline from the filesystem"; with scripting disabled the viewer showed
  nothing, while `overview.md` and `tour.md` sat in the same directory. Fix: a `<noscript>` block naming
  them — and the project's no-language pin rejected the first wording, which said "JavaScript"
- area: onboarding artifacts
- destination: `rulebook_path` (alongside R5's degradation rules)

## 088 (review round) — A generator that owns a directory must delete only what it recorded writing
`_write` cleared its output with `shutil.rmtree(docs/onboarding/modules)`. That is correct for the
pages it wrote and destructive for everything else: a hand-authored page in the same tree vanished, and
a pre-existing `docs/onboarding/overview.md` was overwritten, from any agent call. The fix makes
ownership explicit and *recorded* — the previous `manifest.json` is the delete list, and a tree holding
these filenames without that manifest is refused. Second finding, same shape as 087's: the committed
`overview.md` counted every module while only the budgeted stops had pages, and said nothing about it.

### 088-C1 — A tool that writes into a repo may only remove paths its own last manifest recorded
- type: 2 generalisable-heuristic
- handle: own-only-what-you-wrote
- status: proposed (awaiting human confirm)
- seen: 088, 089
- evidence: `shutil.rmtree(out / "modules")` deleted `modules/HAND_WRITTEN.md`; a foreign
  `docs/onboarding/overview.md` was replaced by generated bytes. Fix: `recorded_pages()` +
  `_remove_recorded_pages` + `_refuse_foreign_tree`; hostile recorded paths (`..`, absolute, outside
  `modules/*.md`) are dropped rather than unlinked. Same rule 050 applied to the index database
- area: tools that write to disk
- destination: `rulebook_path` (R5's degradation section says nothing yet about *destructive* writes;
  `/mango:promote` is the cross-ticket pass)

### 088-C2 — A committed artifact carrying full-graph counts must say when its pages cover only the budget
- type: 2 generalisable-heuristic
- handle: do-not-attest-past-the-payloads-resolution
- status: proposed (awaiting human confirm)
- seen: 088, 089
- evidence: `overview.md` printed `- modules: 4` with one page on disk and no truncation line, while
  `tour.md` and `manifest.json` both carried `truncated`. The overview is the file a human opens first.
  Fix: `- module pages: N` + `- truncated:` in the summary block
- area: onboarding artifacts / tool payloads
- destination: `rulebook_path` (with 087-C2 and 100-C4 on the same handle)

## 087 (review round) — A bounded walk from entry points is not the codebase, and `truncated: false` claimed it was
Four defects, all found on the PR, all reproduced before the fix. The two that matter are one class:
a payload that cannot distinguish *complete* from *cut short*. A component no zero-inbound file
reaches (it must hold a cycle) was silently absent with `truncated: false` and a `total_count` of only
the reachable part — a 3-file index answered with 1 stop; and the surviving member of a budget-cut
cycle was labelled `entry point (zero inbound)` when the store had proved no such thing. The other two
are robustness: recursive Tarjan died with `RecursionError` once `CA_IMPACT_MAX_NODES` admitted a chain
deeper than the interpreter limit (~1200), and a capped `results` page had no `offset`, so the tail of
a reading order was unreachable — the convention 086 had established one ticket earlier.

### 087-C2 — A walk seeded from a computed root set must report what the seeding could not reach
- type: 2 generalisable-heuristic
- handle: do-not-attest-past-the-payloads-resolution
- status: proposed (awaiting human confirm)
- seen: 087, 088
- evidence: `tour_subgraph` seeded from zero-inbound files only; an entry + an unreachable `X ⇄ Y`
  returned 1 stop, `truncated: false`, `total_count: 1`. Fix: re-seed the lowest unseen file until the
  budget binds, and derive `truncated` from *an indexed file is not in the tour* instead of the
  seed/prune bookkeeping. Same class as 100-C4 and 102 (a modelled zero must not read as an absence)
- area: onboarding / store bounded walks / tool payloads
- destination: `rulebook_path` (R4.3's bounded-walk rule says nothing yet about reporting the bound's
  effect on *coverage*; `/mango:promote` is the cross-ticket pass)

### 087-C3 — A recursive graph walk inherits the interpreter's depth limit as a silent input bound
- type: 2 generalisable-heuristic
- handle: bound-the-recursion-or-make-it-iterative
- status: proposed (awaiting human confirm)
- seen: 087
- evidence: recursive Tarjan in `onboarding/tour.py` raised `RecursionError` at 1200 nodes; the tool's
  own budget knob `CA_IMPACT_MAX_NODES` is user-settable with no ceiling, so raising it turned a
  bounded answer into a crash. Rewritten with an explicit work-stack; probe at 1500 nodes
- area: core graph algorithms
- destination: `rulebook_path` (near R4.3 — the sibling of "never load the whole graph" is "never
  recurse per node")

## 087 — A listed `len(descriptions) == N` is a surface count-pin even when it never names `TOOL_NAMES`
Design grepped `TOOL_NAMES ==` and `all 15 tools` and still missed `tests/test_tool_descriptions.py:50`
(`assert len(descriptions) == 15`). Execute folded it as proof collateral of registering the 16th
tool and derived the pin (`set(descriptions) == set(TOOL_NAMES)`). Same class as 085-C1 (count-pin)
and R6.7 (derive the set).

### 087-C1 — A listed integer that is the live tool-surface size is a blast-radius hit when adding a tool
- type: 2 generalisable-heuristic
- handle: count-pin-in-blast-radius
- status: proposed (awaiting human confirm)
- seen: 087, 088
- evidence: `tests/test_tool_descriptions.py:50` was `len(descriptions) == 15`; design's
  `TOOL_NAMES ==` grep did not hit it; execute changed the pin to `set(descriptions) == set(TOOL_NAMES)`
- area: analysis/design blast-radius tracing
- destination: `agent_brief_path` (process; same class as 085-C1 — `/mango:promote` is the cross-ticket pass)

## 085 — A new file under a guarded directory is a blast-radius hit for that guard's COUNT pin, and an AC phrased as a failure mode needs the guard that can actually exhibit it
The Gate-2 blast-radius trace confirmed the two grep-gates *glob* the new module (`CORE.rglob("*.py")`)
but missed that they also **count-pin** the module total (`len(core_modules()) == 44`); execute caught
the 44→45 bump as a 2-file deviation. Separately, AC2 was phrased as a failure mode ("would fail if
presentation read the graph directly"), but the presentation function structurally *cannot* reach the
graph — so the fake-summarizer test actually guards a different boundary (enrichment routes through the
seam), and R6.5 still wanted the guard *observed* failing (a recorded sabotage run), not argued.

### 085-C1 — A count-pinned guard is a blast-radius hit for any file added to its globbed set
- type: 2 generalisable-heuristic
- handle: count-pin-in-blast-radius
- status: proposed (awaiting human confirm)
- seen: 085, 087, 088, 089
- evidence: Gate-2 trace saw `test_core_is_language_agnostic`/`test_sql_confinement` glob
  `CORE.rglob("*.py")` (auto-covering `summary.py`) but not their `assert len(core_modules()) == 44`;
  the bump to 45 landed as a recorded 2-file deviation in execute, not in the approved change-list.
- area: analysis/design blast-radius tracing
- destination: `agent_brief_path` (if it recurs — process subject; seen once, stays in lessons)

### 085-C2 — An AC phrased as a failure mode needs the guard that can actually exhibit that failure
- type: 2 generalisable-heuristic
- handle: ac-failure-mode-needs-the-right-guard
- status: proposed (awaiting human confirm)
- seen: 085
- evidence: AC2 "would fail if presentation read the graph directly" — but `summaries_as_dict(summaries)`
  has no parameter reaching the graph, so that failure mode is guarded *structurally* by a different
  test; the fake-summarizer test guards that enrichment routes through the seam. Reviewer (PR #124)
  flagged the framing mismatch + the absent R6.5 red run; fixed by splitting the claim into two named
  guards and recording a sabotage red run.
- area: tests / AC decomposition / R6.5 (prove-the-guard-fails)
- destination: `rulebook_path` (if it recurs — code subject; seen once, stays in lessons)

## 084 — Piping the Docker gate through `tail` reports the pipe's exit, masking a ruff/mypy failure
The gate `docker-test.sh` runs `ruff check . && mypy code_atlas && pytest -q`, which fails correctly on
a ruff error. But run as `bash scripts/docker-test.sh 2>&1 | tail -N`, the shell reports the exit status
of `tail` (0), not of the gate — so a run with `ruff … Found 10 errors` still surfaced as
`[exited with code 0]`. The green was only visible because the run was judged by its **output content**,
not the pipeline exit code. In an unattended run this is a false-green hazard: a red gate can read as
passed. Judge a piped gate by its content (`Success: no issues …`, `N passed`, ruff silent-on-success),
or drop the pipe so the real exit code propagates.

### 084-C1 — Judge a piped command's result by its output, not the pipeline's exit status
- type: 4 gotcha
- status: proposed (awaiting human confirm)
- seen: 084
- evidence: `bash scripts/docker-test.sh 2>&1 | tail -20` printed ruff's `Found 10 errors` then
  `[exited with code 0]` (tail's exit). The ruff failure was caught by reading the content, not the
  status. `&&`-chained gate → ruff failing stops the chain, but the pipe hides that.
- area: workflow / running the Docker gate on a non-Linux host
- destination: `gotchas_path` (recurrence 1 — recorded, not yet promotable)

## 102 — The fix for "a resolvable subject reported as absent" reintroduced it, one argument over
`seeds_dropped` was documented as the field that separates a modelled zero from a failed query, but
it was **assigned in exactly one place** — the store's budget prune. A subject the tool could not
resolve was never counted in any shape, so the ticket's named root cause (the empty-seed early
return) was the *second* half of the hole; `impact(paths=[a, b])` with `b` unknown also reported `0`
without that return ever firing. **Then the fix repeated the bug in miniature:** the new `qnames`
loop guarded `classify_missing_subject`'s `resolved_unique` status and the new `paths` loop did not,
so a path-slot subject that re-pointed to a real qname (075/076) was counted **lost** and labelled
`name_not_qualified` with `candidate_count: 1`. Gate 2 had recorded that exact hazard as
**assumption 3 — verified**; it was verified for the path that existed, and asserted for the path
the same change added. **Found by the reviewer, not by me**, and confirmed by measurement before it
was accepted: `qnames=["App\Nope"] → results=2 seeds_dropped=0` beside
`paths=["App\Nope"] → results=0 seeds_dropped=1 reason=name_not_qualified`.

### 102-C1 — An assumption is verified for the paths that existed when it was checked
- type: 2 generalisable-heuristic
- handle: re-verify-the-assumption-on-a-new-path
- status: proposed (awaiting human confirm)
- seen: 102
- evidence: Gate 2 assumption 3 (*"a `resolved_unique` resolution can never reach
  `_explain_lost_subject`"*) was true of the `qnames` loop it was read against, and false of the
  `paths` loop the same change introduced. A spike confirmed the mislabelling
  (`classify('Nope') -> resolved_unique … shape={'reason': 'name_not_qualified'}`) and the design
  cited that spike as the reason the branch keys on `status` — for one caller
- area: process / design assumptions
- destination: `agent_brief_path` (process subject) — recurrence 1, not yet promotable

### 102-C2 — Two call sites consuming one classifier need one shared rule, not two copies
- type: 2 generalisable-heuristic
- handle: one-rule-for-every-subject-slot
- status: proposed (awaiting human confirm)
- seen: 102
- evidence: `impact._seeds` grew a second subject slot; the guard was written twice and one copy was
  wrong. Fixed by a single `take()` both slots call, so they cannot drift apart again. The same
  shape exists in `read_symbol.py:189` and `find_callers.py:168`, which each branch on
  `resolution.status == "resolved_unique"` independently
- area: tools / subject resolution
- destination: `rulebook_path` (code subject) — recurrence 1, not yet promotable

### 102-C3 — `seeds_dropped` has two producers, and an unknown path has no reason of its own
- type: 5 project-ground-truth
- status: proposed (awaiting human confirm)
- seen: 102
- evidence: the field now sums `store.impact_radius`'s budget prune (`store.py:1051`) with the
  tool's lost-subject count (`impact.py`), and the two can never overlap because a dropped subject
  never enters `ordered_seeds`. A truly unknown **path** reports `no_such_symbol` — true at the
  class level, not path-specific; `file_outline` has the same gap (`found: false`, no reason), so a
  path-shaped reason is a surface-wide follow-up, not an impact-only one
- area: impact / store / tool payloads

## 100 — A caveat is only as reachable as the payload shape you read it from
The signed line was built to make a caveat undroppable by giving each one its own key. It then
dropped one anyway: `get_index_status` sourced `parse_failures` **from the payload**, and that key
only exists at `standard`/`verbose`. At `minimal` the same index, with the same real parse failure,
produced a signed, quotable claim with the caveat missing — the exact harm the mechanism exists to
prevent, inside the mechanism itself. The data was in scope the whole time (`counts["failed"]` is
computed unconditionally); only the **source** was wrong. **Found by the reviewer, not by me**, and
untested: no test exercised that signer's line content at all, so its AC was green on inspection.
**Second finding, same round:** an embedded `"` was quote-wrapped but never escaped, corrupting the
line's own grammar. The proposed fix — fold `"` to `'` — was rejected: folding silently rewrites the
subject of a claim whose whole purpose is to be re-checked. Doubling the quote is lossless and adds
no escape character, so separator backslashes still survive.

### 100-C1 — A value read from a payload inherits that payload's most minimal shape
- type: 2 generalisable-heuristic
- handle: source-the-caveat-from-the-computation
- status: confirmed — **not retired** on promotion (2026-08-16), so recall keeps surfacing the handle
  and R5.5 stays reachable by the recalled-handle route, not only by change type
- seen: 100, 101, 102
- evidence: `CLAIM_CARRY = ("parse_failures",)` read the key off the payload, which only carries it
  at `standard`/`verbose`; the `minimal` line shipped without the caveat while `counts["failed"]`
  was 1. Fixed by sourcing from the computation, not the presentation. 102: `seeds_dropped` was
  assigned in exactly one place — the store's budget prune — while documented as the field naming
  every dropped seed, so the same principle diagnosed a pre-existing defect
- area: tool payloads / claim signing
- destination: `rulebook_path` — **promoted 2026-08-16** to `docs/ENGINEERING_RULES.md` **R5.5**,
  tagged `PROVISIONAL (awaiting ratification)`, widened at promotion to cover both breaks (narrow by
  detail level, narrow by case). Re-runs of `/mango:promote` must skip this class

### 100-C2 — When an artifact exists to be re-checked, a lossy repair is worse than the corruption
- type: 2 generalisable-heuristic
- handle: lossless-repair-for-a-checkable-artifact
- status: proposed (awaiting human confirm)
- seen: 100
- evidence: review proposed folding an inner `"` to `'`; that would have silently renamed the path a
  reader is meant to verify. Quote-doubling round-trips exactly and keeps the no-escape-character
  grammar the backslash-separated qualified names depend on
- area: tool payloads / claim signing

### 100-C3 — A grep-gate sweep is per-commit, not per-ticket
- type: 2 generalisable-heuristic
- handle: re-run-the-sweep-after-the-last-edit
- status: confirmed — **not retired** on promotion (2026-08-16), same reason as `100-C1`
- seen: 100, 101, 102
- evidence: the Phase-3 R1.1 sweep was clean; a later commit's **docstring** reintroduced a language
  name in a core module and the gate failed the build. The sweep was honest when run and stale by
  the time it was quoted — and review round 1 could not see it either, since the text post-dated it
- area: process / verification sweep
- destination: `agent_brief_path` (process subject) — **promoted 2026-08-16** to
  `docs/AGENT_BRIEF.md` **P4**, tagged `PROVISIONAL (awaiting ratification)`. Two real failures (100,
  101) against one binding (102); in 101 it had been recalled and judged *"does not apply"* and was
  the one that fired. Re-runs of `/mango:promote` must skip this class

### 100-C4 — Do not sign what the payload cannot distinguish
- type: 2 generalisable-heuristic
- handle: do-not-attest-past-the-payloads-resolution
- status: proposed (awaiting human confirm)
- seen: 100, 101, 102, 087, 088, 088
- evidence: `impact_radius` returns `seeds_dropped = 0` for an empty seed set, so an absent subject
  and a genuine modelled zero are indistinguishable in the payload. Rather than fix the count
  in-flight (outside the change list) or sign over it, the answer gets **no line**
- area: impact / claim signing
- destination: `rulebook_path` — **promotion rejected 2026-08-16**: recurrence 3, but **all three
  sightings are the class binding a design (100, 101, 102) and none is the defect recurring** — the
  same shape as `094-C1`'s rejection of 2026-08-15 (*"load-bearing twice but has failed only once"*).
  Note also that 102 **removed this claim's cited evidence** by making the payload distinguish the two
  cases, so the guard it argued for now stands on a different reason. Re-propose on a real failure —
  a signed line that asserts something its own payload cannot tell apart

### 100-C5 — impact seeds are returned inside `results`, so a bare count is ambiguous
- type: 5 project-ground-truth
- status: proposed (awaiting human confirm)
- seen: 100
- evidence: `store.impact_radius` includes the seeds themselves, so `answer=N` conflates *N
  dependents* with *N seeds and zero dependents*. The line carries `seeds=` beside `answer=`;
  `answer == seeds` is the modelled zero
- area: impact / store

## promote-2026-08-15 — Recurrence that only grows when someone writes a lesson under-counts the rules worth having
`/mango:promote`'s first real run proposed **nothing**, then the same corpus corrected proposed two
candidates. The corpus was wrong, not the pass: `seen:` grew only when a **new lesson** was written,
never when an existing handle was recalled and answered at design. `prove-the-guard-fails` read as
recurrence 1 while it had bound 093, 096 and 099; `derived-not-listed-invariant` had two uncredited
sightings and R6.7 cited two of its three claims. **The bias has a direction:** a class that keeps
being *honoured* rather than re-broken never accrues sightings — which is the class most worth
promoting. **Second finding from the same run:** the ratified candidate was a near-duplicate of an
existing rule (R6.5 already carried its special case), and promotion's idempotency grep — handle slug
plus claim IDs — structurally cannot catch that. **Fix:** `docs/AGENT_BRIEF.md` P1 and P2; the mango
half is a type-3 signal in `docs/SKILL_GAP_CANDIDATES.md`, since no lesson edits a mango skill.

### PROM-C1 — A counter that only increments on the rare path measures the rare path
- type: 2 generalisable-heuristic
- handle: increment-on-the-common-path
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15
- evidence: `seen:` grew on lesson-write (rare) not on handle-answer (common), so recurrence
  under-counted every honoured class; corrected in PR #112
- area: process / learning loop
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P1**

### PROM-C2 — An idempotency check keyed on identity cannot detect duplication of substance
- type: 2 generalisable-heuristic
- handle: identity-check-misses-substance
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15
- evidence: promote greps handle slug + claim IDs; R6.5 already carried the candidate's substance
  under a different handle, so the grep was a clean miss that looked like a verified negative
- area: process / learning loop
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P2**;
  the harness half is `docs/SKILL_GAP_CANDIDATES.md` **SG-1** (type 3, out of promotion scope)

### PROM-C3 — A ticket is written at a point in time; the code moves under it
- type: 2 generalisable-heuristic
- handle: record-the-deviation-as-a-deviation
- status: proposed (awaiting human confirm)
- seen: promote-2026-08-15, 101
- evidence: 099's evidence table asked for a `no_such_symbol` warning that 092 had already replaced
  with `not_indexed`; shipped the current form with a test asserting the superseded string is absent
- area: process / lifecycle
- destination: `agent_brief_path` — **written 2026-08-15** as `docs/AGENT_BRIEF.md` **P3**

## 099 — A channel that only answers when asked cannot carry information the asker never requests
Four rounds treated low adoption as routing (069, 081) then as cost (080, 096). The interview said
**position**: all three decisions made without the graph wanted one line at a `Read` or a `Write`,
and **none wanted a tool call**. Cost cannot explain it — both top uncalled queries needed no
rebuild. **Fix:** `code-atlas-signal`, a hook-shaped entry point (the third of 036/053's kind),
offered and never wired. **The reasoning that settled it:** `next_tool_suggestions` reaches the agent
*after it asks*, and the core cannot observe a `Read` — so the rider channel is **structurally**
incapable, not merely expensive. **Bound:** no description reaches an agent that never opens the tool
list; that is the ceiling on 069/081-style work, and 097 is the same finding measured from the
recognition side. **Falsifier, recorded in retro §0.6:** if the next round reports the signal *tuned
out* at the shipped cap, the finding was session-specific.

### 099-C1 — Where a signal is delivered can be a capability question, not a cost question
- type: 2 generalisable-heuristic
- handle: channel-cannot-carry-unasked-information
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: `next_tool_suggestions` rides answers to questions; the finding is that the question is
  never asked, so no token budget on that channel would have helped
- area: agent-fit / product position
- destination: `rulebook_path` (if it recurs)

### 099-C2 — A silence rule keyed to structure needs no state; one keyed to history does
- type: 2 generalisable-heuristic
- handle: structural-silence-over-stateful-latch
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: every occasion the field named as costly (probe output, CI shells, authoring writes) is
  excludable by tool name or by "the path already exists"; a fire-once-per-session latch would need
  persistence and would still be wrong on the second session
- area: hooks
- destination: `rulebook_path` (if it recurs)

### 099-C3 — When a create-vs-edit test reads the filesystem, the hook event is part of the contract
- type: 2 generalisable-heuristic
- handle: hook-event-is-part-of-the-contract
- status: proposed (awaiting human confirm)
- seen: 099
- evidence: the untracked signal is silent by construction at `PostToolUse` because the file exists
  by then; `tests/test_write_time_signal.py::test_the_write_signal_is_a_pre_tool_use_signal` pins it
  so the silence cannot be misread as a bug
- area: hooks
- destination: `rulebook_path` (if it recurs)

## 096 — A cost fix whose correctness argument is "the delta is what changed" needs the case where it isn't
`resolve_edges` re-scanned the **whole** unresolved residue on every incremental — measured flat
across delta size at two scales (20k residue: 0.074 s at 2 files vs 0.078 s at 14; 60k: 0.408 vs
0.405), so the cost was O(residue) and the 0→1-file cliff was the entire tax. **Fix:** an optional
delta scope streams only edges the delta could have changed the answer for — those emitted by the
parsed files, plus those whose `target_raw` is a key the delta now declares. **The trap:** file A
holds an unresolved edge to `\X` and the delta adds `\X` in file B; A is *not* a dependent, because
`file_paths_targeting` matches `target_qname`, which is still NULL — so a file-scoped resolve leaves
it unlinked forever while a full resolve links it. The key set, not the file set, is what makes the
scope equivalent. **Bound:** equivalence holds only while the alias map is fixed (`_lookup_raw` is
key-pure given that map), so the map is snapshotted before the parse and a change falls back to a
full pass — and *pinning* that map is not enough, because `_lookup_raw` also **reaches** a key
through it: the key set has to carry each key's aliases too (096-C4, found in review). **No schema
change** — the ticket assumed one was required; `idx_edges_raw` already
indexed the lookup.

### 096-C1 — A scoped scan is equivalent only for the keys the scope can name
- type: 2 generalisable-heuristic
- handle: scope-by-key-not-by-file
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `tests/test_delta_resolve.py::test_delta_resolve_links_residue_a_new_file_satisfies`;
  stubbing the key set to `set()` fails 5 of 8 tests
- area: resolver / store
- destination: `rulebook_path` (if it recurs)

### 096-C2 — A purity argument that depends on a lookup table must pin that table, not assume it
- type: 2 generalisable-heuristic
- handle: pin-the-table-a-purity-claim-rests-on
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `indexer.py` snapshots `alias_targets()` **before the parse** and falls back to a full
  resolve when it moved; a snapshot taken after the parse would already contain the new rows and
  silently miss the change
- area: resolver / indexer
- destination: `rulebook_path` (if it recurs)

### 096-C3 — A writer that runs after the delta is computed must be added to the delta
- type: 2 generalisable-heuristic
- handle: late-writer-outside-the-delta
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `apply_indirection_rules` rewrites every rule row bare under `INDIRECTION_FILE` *after*
  the parse, so a scope built from `to_parse` never covered it and the fresh `ALIASES` row stayed
  unresolved; `tests/test_delta_resolve.py::test_enrichment_rows_resolve_under_a_delta_scope`
- area: indexer / enrichment
- destination: `rulebook_path` (if it recurs)

### 096-C4 — A scope keyed on raw text must invert every rewrite the lookup applies to that text
- type: 2 generalisable-heuristic
- handle: invert-the-rewrite-the-lookup-applies
- status: proposed (awaiting human confirm)
- seen: 096
- evidence: `_lookup_raw` maps a raw through the alias map (whole name *and* container), so an edge
  naming `\Ns\Aka` resolves to the delta's `\Ns\Real` — comparing `target_raw` against the key set
  alone skipped it in a file no delta lists, while a full resolve linked it. `delta_scope` now adds
  each key's alias pre-images; `tests/test_delta_resolve.py::test_delta_scope_covers_an_edge_naming_an_alias`
  and `::test_delta_scope_covers_an_aliased_container` — reverting the expansion fails both, and
  only those two
- area: resolver
- destination: `rulebook_path` (if it recurs)

## 094 — A mention the resolver skips is indistinguishable from a relationship it refused
`Foo::class` in an array was a textual, unambiguous class name, and `find_references` still
answered `relationship_not_modelled` because (1) the PHP adapter never emitted `REFERENCES` and
(2) `skip_dynamic` dropped every `DYNAMIC` row — including ones whose `target_raw` is an FQN.
**Fix:** emit `REFERENCES`/`DYNAMIC` for `Name::class`; opt the kind into `FQN_EDGE_KINDS`; keep
`skip_dynamic` from hiding `REFERENCES`; leave the linked tier `DYNAMIC`. An all-`DYNAMIC` page
sets `authoritative: false` so it reads as a candidate list. Variable-method dispatch stays
unmodelled. No new `edge_kind` (R3). Anchor edge-count delta is an operator paste, not a merge gate.

### 094-C1 — skip_dynamic must not drop a DYNAMIC row whose target is an FQN
- type: 2 generalisable-heuristic
- handle: skip-dynamic-means-unlinkable
- status: proposed (awaiting human confirm)
- seen: 094, 096
- evidence: `store.py` `iter_unresolved_edges`; `tests/test_class_const_mention.py::test_skip_dynamic_still_yields_reference_mentions`
- area: resolver / store
- destination: `rulebook_path` — **promotion rejected 2026-08-15**: the second sighting (096) was the rule *binding a design*, not the defect recurring, so the class is load-bearing twice but has failed only once. Re-propose on a real second failure

### 094-C2 — A ::class mention is a REFERENCES edge, not a CALLS or a new kind
- type: 5 project-ground-truth
- status: proposed (awaiting human confirm)
- area: adapter / contract
- sub-shape: descriptive
- evidence: ticket 094; `Visitor.php` `enterClassConstFetch`; PLAN §8.2
- destination: stays in lessons_path (PLAN §8.2 already records it)

## 097 — A recognition score off names cannot measure descriptions, and recognition is not recall
Round 5 scored 14/14 on the blind probe while 7 of 14 descriptions were never loaded, then named
`file_outline` at Q4 and did not call it when a 1,196-line port needed the symbol map. **Fix:** the
probe records resident `K/14`, marks each answer name-only or description-backed, and reports two
rates. The 081 proxy is the description-backed rate (or `NOT OBSERVED` when `K = 0`). Q4 is
occasion-worded so a name list can miss it. Retro §2 gained a fourth bucket — *knew it, it fit, did
not think of it* — whose opposite fix is a workflow trigger, not a better description. The
`file_outline` occasion lives in the tool description and the onboarding runbook, not in
`next_tool_suggestions` (061 / R4). **Bound:** descriptions can name the occasion; they cannot make
the agent notice. 074’s n = 1 for *legacy→unified port* is unchanged.

### 097-C1 — A set the probe claims to cover is derived from the surface, never listed
- type: 2 generalisable-heuristic
- handle: derived-not-listed-invariant
- status: proposed (awaiting human confirm)
- seen: 093, 095, 096, 097, 099, 100, 101, 102, 087, 088
- evidence: `tests/test_recognition_probe_protocol.py` parses intended tools from the probe table
  and compares them to `main.TOOL_NAMES`; `test_the_probe_surface_guard_can_actually_fail` injects
  a name the table does not have
- area: tests / R1.1
- destination: `rulebook_path` — already **promoted** as `docs/ENGINEERING_RULES.md` **R6.7**
  (093-C2 / 095-C1). This sighting is recurrence, not a new class. `/mango:promote` is the
  cross-ticket pass.

### 097-C2 — Descriptions can name an occasion; they cannot make the agent notice it
- type: 5 project-ground-truth
- status: proposed (awaiting human confirm)
- area: routing surface / recognition vs recall
- sub-shape: descriptive
- evidence: field retro round 5 §11.3; `file_outline` named at Q4, description loaded, unused on
  the 1,196-line port; trigger placed in description + onboarding, not `next_tool_suggestions`
- destination: stays in lessons_path (descriptive; PLAN §19 already records the bound)

## 095 — An ignore total that does not name its source is an unauditable denominator
082 made `skipped.ignore` an outsider-checkable int, and the identities close. The 9,541 files in
that bucket all have an indexed suffix — they are PHP the index chose not to hold — and nothing
named the rule. Retro suggested `{gitignore, config, vendor}`. That list is a **hint, not the
schema** (082): `load_ignore` composes built-ins + `.gitignore` + `.codeatlasignore`; `vendor/` is a
pattern inside the builtin source, and there is no `CA_*` ignore knob. **Fix:** stamp each `_Rule`
with its source as the matcher concatenates; attribute by the same last-excluding-rule walk
`is_ignored` already uses (the ticket’s “first match wins” was an example of a stable rule, not the
matcher); keep `ignore` as the int; publish `skipped.ignore_sources` at verbose only, omitted when
empty. Persist the dict on a **sibling** meta key — `collection_census()` int-casts every value
(092). On the git path most `.gitignore` hits never enter `collected`, so the breakdown names what
**this matcher** dropped. Per-pattern counts would re-publish the ignore file (061). The absolute
9,541 is an operator paste, not a merge gate (080/074).

### 095-C1 — Source keys are derived from the composition, never listed
- type: 2 generalisable-heuristic
- handle: derived-not-listed-invariant
- status: proposed (awaiting human confirm)
- seen: 093, 095, 096, 097, 099, 100, 101, 102
- evidence: `ignore.py` `COMPOSED_IGNORE_FILES` / `composed_source_names()`;
  `tests/test_ignore_bucket_names_its_rule.py::test_composed_source_names_are_derived_and_exclude_retro_keys`
- area: tests / R1.1
- destination: `rulebook_path` — **promoted 2026-08-14** to `docs/ENGINEERING_RULES.md` **R6.7** (with
  `093-C2`), tagged `PROVISIONAL (awaiting ratification)`. Re-runs of `/mango:promote` skip this class.

### 095-C2 — A JSON meta reader that int-casts cannot hold a dict; use a sibling key
- type: 2 generalisable-heuristic
- handle: sibling-meta-non-int
- status: proposed (awaiting human confirm)
- seen: 092, 095
- evidence: `store.py` `collection_census()` int-casts; `IGNORE_SOURCES_KEY` beside
  `UNTRACKED_INDEXABLE_KEY`
- area: store / census
- destination: `rulebook_path` — **promoted 2026-08-14** to `docs/ENGINEERING_RULES.md` **R1.7**, tagged
  `PROVISIONAL (awaiting ratification)`. Re-runs of `/mango:promote` skip this class.

### 095-C3 — On the git collect path, ignore_sources names matcher leftovers, not git’s drops
- type: 5 project-ground-truth
- status: proposed (awaiting human confirm)
- area: collection census / ignore
- sub-shape: descriptive
- evidence: PLAN §11; `git ls-files` already applies `.gitignore`; proving test uses
  `.codeatlasignore` + builtin, and `git add -f` for a gitignore source
- destination: stays in lessons_path (descriptive; PLAN §11 already records it)

## 093 — A field whose values are usually callable trains the reader to call all of them
Three of five `try_instead` values were real tools; two were instructions shaped like identifiers
(`find_references_on_method_qname`, `path_basename_search`). The field's *routing* was right both
times — an evaluator that followed one got a better answer — but it first had to try the string as a
tool, find nothing, and infer the meaning. **One prose value makes the whole field ambiguous**, not
just itself: a reader cannot tell a route from an instruction without spending a call. **Fix:** one
register per field — `try_instead` is a registered tool name, the qualifier is prose in the sibling
`try_instead_hint` (092's shape, generalised); a self-route (`find_references` → `find_references`)
is honest when only the *subject* was wrong. **Carry the split into the source as a naming rule**
(`TRY_INSTEAD_*` vs `TRY_INSTEAD_HINT_*`) so a test can derive both sets from the module namespace
and `main.TOOL_NAMES` — a hand-kept list of allowed values is the thing that drifts (R1.1). Prove the
gate by running it against the pre-fix shape: 4 of 6 failed there, 6 pass after. A guard that passes
on both shapes is not a guard.
**Review addendum — "callable" is not "useful", and a guard needs its own guard.** Three things the
first cut got wrong. (1) The dead-route guard scanned every module *including the one that defines
the constants*, so each name was always found by its own definition line and the test **could never
fail** — a false-green in a test written to be a gate. Skip assignment lines, and add a test that
**injects a dead constant and asserts the guard reports it**. (2) A route must **make progress**: the
class-level miss self-routed `find_references` → `find_references`, which loops for exactly the
mechanical reader the field targets. Route to the enumerator (`search_symbol` returns the class's
method qnames) instead. (3) A route must **be able to answer**. The unlinked-include miss routed to
`search_symbol`, but that evidence lives in `edges.target_raw` while `nodes_fts` covers
name/qname/file_path/params — following it returned `reason: ok` with the symbols declared *in* the
file and no includer. **Where no tool can answer, emit the hint alone and no route**: naming a tool
that cannot answer is worse than naming none, because the reader spends a call and gets a confident
wrong answer. Making a bad route *callable* is what turned an unfollowable string into a followable
trap.

### 093-C1 — A machine-readable field holds one register; prose gets its own field
- type: 2 generalisable-heuristic
- handle: try-instead-tool-name
- status: confirmed
- seen: 092, 093, 100, 101, 102
- evidence: `nav_result.py:58-76` (naming rule); `tests/test_try_instead_is_a_callable_tool_name.py`
  (4 failed / 2 passed pre-fix, 6 passed after); field retro round 5 §4, §9 runner-up
- area: tool payloads / R1.1 / R4
- destination: `rulebook_path` — **promoted 2026-08-14** to `docs/ENGINEERING_RULES.md` **R5.4**,
  tagged `PROVISIONAL (awaiting ratification)`. Re-runs of `/mango:promote` must skip this class.

### 093-C2 — An enumeration guard derives its sets; it never lists them
- type: 2 generalisable-heuristic
- handle: derived-not-listed-invariant
- status: confirmed
- seen: 093, 095, 096, 097, 099, 100, 101, 102
- evidence: `tests/test_try_instead_is_a_callable_tool_name.py` reads `vars(nav_result)` +
  `main.TOOL_NAMES`; `test_the_dead_route_guard_can_actually_fail` injects a dead constant;
  095: `composed_source_names()` from `COMPOSED_IGNORE_FILES`
- area: tests / R1.1
- destination: `rulebook_path` — **promoted 2026-08-14** to `docs/ENGINEERING_RULES.md` **R6.7** (with
  `095-C1`), tagged `PROVISIONAL (awaiting ratification)`. Re-runs of `/mango:promote` skip this class.

### 093-C3 — A guard is not a guard until it has been made to fail
- type: 2 generalisable-heuristic
- handle: prove-the-guard-fails
- status: confirmed
- seen: 093, 096, 099, 100, 101, 087, 088
- evidence: the dead-route guard scanned its own definition site and could never fail, yet shipped in
  PR #103 advertised as "the audit cannot go stale"; caught by review, not by the suite
- area: tests / R1.1
- destination: `rulebook_path` — **promoted 2026-08-15** into `docs/ENGINEERING_RULES.md` **R6.5**, which already carried the special case (a sweep guarded against emptying itself); this widened it to every guard rather than adding a near-duplicate rule

### 093-C4 — A route the reader cannot use is worse callable than not
- type: 2 generalisable-heuristic
- handle: route-must-answer
- status: confirmed
- seen: 093, 101, 102
- evidence: `include_graph` → `search_symbol` returned `reason: ok`, `total_count: 2`, includer
  absent (`store.py:701-714` vs `store.py:90-92`); now hint-only, no route. 102: an all-dropped
  `impact` answer routes through `shape_exact_miss`, so its route is a registered tool that can
  answer (`search_symbol` / `build_or_update_index`) and never `impact` itself
- area: tool payloads / 065 / 075 / 076
- destination: `rulebook_path` — **folded into R5.4 on 2026-08-16** rather than promoted as a new
  rule; **not retired** (retire declined 2026-08-16, as for `100-C1` / `100-C3`). Per `AGENT_BRIEF.md` **P2** the substance was already in R5.4 clause (c), but the rule's
  *falsifier* tested only clauses (a) and (b) — so the class was stated and unenforceable. R5.4's
  falsifier now covers (c) and cites this handle. Re-runs of `/mango:promote` must skip this class

## 092 — A partition cannot count what never entered the walked set
`collect()` partitions `git ls-files`. Untracked files are not skipped-by-rule; they are never in
`found`, so 082's identity stayed green while four new classes answered `no_such_symbol`. **Fix:**
sit `skipped.untracked` *beside* the partition (a second git spawn, not a second filesystem walk —
folding them into `collected` would break `collected == git ls-files`). Stamp the int on the census
JSON and the path list on a **sibling** meta key — `collection_census()` int-casts every value.
Classify the miss by matching stored stems, reuse `not_indexed` (`indexed: true` vs unbuilt's
`indexed: false`), and put git-add prose in `try_instead_hint` so `try_instead` stays a real tool
(093). Do not index the file.
**Review addendum.** An early return that replaces a fall-through inherits its whole payload
contract: 092's exact-miss shortcut silently dropped `subject_refreshed_only` (073) and
`args_unrecorded` (049) because both were attached below it. And match an untracked file on the
**stem** — a path-shaped qname's trailing ident is its extension, so `Missing.aa` matched `aa.aa`.

## 080 — A "delta" count that is non-zero on an empty delta means the work isn't gated on the delta
080's no-op reported `edges:6071` for 0 files parsed and cost ~56s because `incremental_update` ran
the late writers (enrichment + full-graph `resolve_edges`) unconditionally — even when nothing
changed, where they only re-derive rows already in the store. The unreadable *number* and the *cost*
had one cause: work not gated on the delta. **Fix:** gate it — skip the late writers when
`to_parse` and `removed` are both empty (idempotent on an unchanged graph, so state-equivalent); the
count then means the delta and the floor drops. Guard on the **empty delta**, never on the count
itself (circular) and never by skipping when there *is* a delta (that's the 068 anti-pattern the
ticket names). Two corollaries: (1) when a cost ticket's real number is on an environment you don't
have (the anchor repo), ship the fix + fixture proof and record the absolute seconds as an
operator-confirmed follow-up, not a merge gate (cf. 074) — don't let it stall like 052→053 did;
(2) a mechanical blast-radius grep of the changed *symbol* misses callers that pass it differently —
here a profiler test drove `incremental_update` with `phase_times=` and asserted every phase is
present; grep the phase/inventory constant too, and prefer a fix that keeps the invariant (record the
skipped phases as 0.0) over weakening the other ticket's assertion.

## 081 — A capability on a channel the consumer never sees is unshipped, however well it works
081's four MCP prompts worked perfectly and were never once invoked in four field rounds — because
the agent's client surfaces only tools to the model; prompts are human-invoked entries the model
cannot see. The defect was a **category error** (counting a human-facing channel as agent-facing), not
a bug. **Fix:** for any capability, verify the *consumer's actual surface* reaches it before counting
it as delivered — reachability is a property of the delivery channel, not of the feature's
correctness. The smallest honest fix is often to relabel and re-home, not to rebuild: here, keep the
prompts as operator recipes, route agents via the surface they do see (tool descriptions, 069), and
add no 15th tool (a scanned surface has a budget). Generalises: when a ticket hands you a design choice
"with the field evidence in hand", let the evidence of what the consumer *reached* — not what was
*built* — pick the design.

## 082 — A ticket's illustrative cause-list is a hint, not the schema; count what the code actually does
082 asked to publish `files` skip counts "by cause (ignore rule, suffix, size, unreadable)". Only two
of the four are real collect-time skips (`suffix`, `ignore`); "unreadable" is the existing parse-time
`failed` bucket (`parsed_ok=0`, already on verbose via 058) and code-atlas applies no size limit at
all. Implementing all four literally would have invented a size-filter (new inclusion policy that
changes what gets indexed) and double-counted unreadable. **Fix:** at analysis, re-derive every
enumerated acceptance value against the code before treating it as the schema — an AC's parenthetical
list is a Gate-1 falsifiability check, not a spec. Publish the causes that exist, map the rest to where
they already live, and never add a filter just to satisfy a list. Generalises: a reconciliation that
"closes by construction" (a partition of one walk) is the honest shape — R4's "one walk, not two ways
to count" — so design the census as a partition and let the arithmetic close, rather than reconciling
two independently-derived numbers.

## 079 — A "refusal path" the ticket wants to carry a field may not return a payload at all
079 asked for `index_root` on "every refusal path (no adapter, empty suffixes, schema mismatch)".
Two of those (`no_adapter`, `empty_suffixes`) did not *return* a payload — they `raise AdapterError`
(064's deliberate fail-loud). An exception carries no payload field, so satisfying the AC required
converting the raise to a returned `mode: refused` payload at the tool boundary (the `schema_guard`
pattern) — a real contract change to the *other* ticket's tests. **Fix:** at analysis, for any
"attach field X to every <shape>" requirement, verify each named shape actually *returns* that shape
vs. *raises*; surface the raise→payload conversion (and the test it breaks) as an explicit Gate-1
decision and a proof-collateral change-list item, not an execute surprise. Generalises: "every
refusal" is not a given set of payloads until you confirm each refusal is a payload.

## 078 — A warning field next to a body is ignorable; refuse the body
`ambiguous_definitions` named every site and still shipped one region's `source`/`file`/`line_*`.
Agents read the body and skip the list — the exact failure 070's caveat predicted. **Marking the
chosen site (option 2) still relies on a second field; a disambiguator arg (option 3) is a large
surface.** Prefer **refuse the body** when N>1: empty `source`, omit site keys, keep the list,
`reason=subject_ambiguous` + `found=false` + `try_instead` (never `reason=ok` with an empty answer —
075/076). Refuse **before** freshness and probe multiplicity with `max_results+1`. Unique payloads
stay byte-identical (061). Re-ask via existing `search_symbol` / `file_outline`, not a new parameter.

## 077 — Name the revision with dual refs; do not invent a third staleness word
`staleness: "current"` after an out-of-band branch switch + rebuild is *true* and still useless —
agents reason in branch names, not SHAs. The temptation is a new word (`switched` / `diverged`).
Resist it: 047 owns which files move the signal, and a third word forces every consumer to relearn
the vocabulary. **Ship `last_ref` (meta, stamped at build) + `head_ref` (live) beside the SHA
pair**, keep `current`/`behind`/`unknown`, and put the pair on the shared status↔busy vocabulary
(072) — not on nav (061; directory mismatch stays `index_root`). Detached HEAD is the value
`HEAD`, not an omission.

PR review follow-ups that belong with the feature: (1) clear `last_commit`/`last_ref` on rebuild
when git cannot name them — skip-write inherits a prior branch onto an unversioned snapshot;
(2) omit `last_ref` when the key is absent but `last_commit` is present (pre-077), so `null` is
not overloaded as "non-git"; (3) one `rev-parse HEAD --abbrev-ref HEAD` for an atomic SHA+ref
pair and one fewer spawn on the cheap status path; (4) unbuilt/mismatched stay git-free.

## 075 — "Bump `contract_version`" can name the wrong contract — verify before you force a reindex
Tickets 075/076 constrained the change with "R3 — a new `reason` value is contract vocabulary: bump
`contract_version`." Taken literally that bumps the **adapter** JSONL contract (`contract.CONTRACT_VERSION`),
whose bump makes every existing index schema-incompatible → **a full reindex for all users**. But nav
`reason` codes are **tool-output** vocabulary: defined in `nav_result.NAV_REASONS`, tested in
`test_nav_reason_codes.py`, and — the decisive evidence — `CONTRACT_VERSION` was still `5` after 054, 065
and 069 each added a reason. Two vocabularies both called "the contract"; only one gates reindexing.
**Fix:** before honoring a "bump the contract" constraint, locate where the vocabulary is *defined* and
which *conformance suite* tests it; if that is not `contract.py` / `tests/contract/`, it is not the
adapter contract and must not bump `CONTRACT_VERSION`. Surface the correction in the design + PR
(detect-and-surface, per the uncodified-standard rule), never silently comply or silently ignore.

## 074 — A measurement ticket that needs an external environment splits into prep → run → analyze
074's core is an n≥3 headless benchmark on the anchor repo — data this session cannot produce, and
must never fabricate ("every claim is a counted artifact"; "do not change any tool to make the number
come out"). The wrong move is to run a local toy-repo substitute (it cannot reproduce a confident
*partial* answer terminating correct reasoning) or to invent verdicts. The right move: **split the
ticket** — commit a **pre-registration** (outcomes → consequences, protocol, rubric, capture template)
that is **git-timestamped before any run**, hand the runs to the maintainer's environment, then score
and decide in a later cycle. Pre-registering in git is what makes the result unarguable after the
fact. A benchmark ticket has **no proving test**; its proving artifact is the pre-registration plus the
recorded per-run verdicts. Shipping the prep half alone is a legitimate stopping point — but the PR and
status must say so plainly (measurement ACs still open), never imply the threat was resolved.

## 069 — Adding a member to a pinned vocabulary breaks its pin tests AND every consumer's allow-set
Adding `REASON_CAPABILITY_NOT_CONFIGURED` to `NAV_REASONS` broke **four** tests, and the design's
test-blast-radius grep found only one (the prompt-registration test — which in fact needed no edit).
The real collateral: two tests that **pin** the vocabulary (`NAV_REASONS == (...)`,
`NAV_REASONS[-1] == …`) and two freshness tests that **consume** it via a per-tool reason **allow-set**
(`assert reason in {no_matches, ok}`). **Fix pattern:** when adding a member to a shared enum/vocabulary
tuple, grep for the collection name (`NAV_REASONS`) **and** for set/`in` **memberships** of its
constants across tests — not just the constant's definition. A new member is invalidated both where the
set is pinned and where any consumer enumerates the values it will accept. (Generalizes 070's pinned-count
lesson from counts to vocabulary + consumer allow-sets.)

Second, smaller lesson from the same run: an "inert vs empty" signal belongs **on the existing
empty-answer branch** (override `no_matches`), not as an **early return before the shared
freshness/clamp path** — the early return silently dropped `find_view_data` out of the six-consumer
freshness invariant and the clamp-uniformity guard. Reclassify the reason; keep the tool on every
shared code path.

## 070 — A wall-clock-tolerance test can fail under load; isolate before calling it a regression
`test_profile_incremental::test_phase_times_cover_named_phases_and_sum_near_wall` asserts
`phase_sum_vs_wall.within_tolerance` — a timing assertion, so it is **load-sensitive**. During 070's
delta validation it failed twice, once in the full suite and once in a scoped run — but only when my
two `@needs_php` fixture builds (real PHP subprocesses) and back-to-back Docker image builds were
loading the host. It **passed in isolation with my changes** and **passed on clean `main`**, and 070
touches nothing in the incremental-build path. **Fix pattern:** when a timing/tolerance test fails
during delta validation, before treating it as a regression, (a) re-run it *in isolation* with your
change, and (b) run it on the *stashed clean base* — if it passes both, it is a pre-existing
load-driven flake and a baseline exclusion, not your delta. Do not chase it as a bug in the change,
and do not weaken your delta to "fix" it. (A calmer full run then went green: 1063 passed.)

**Recurred on CI `main` after #108 — and the cause is structural, not merely "load".** py3.12 red,
py3.13 green on the same commit. The slack is `max(0.15 × wall, floor)`, and on the sub-second
scenarios (`noop`, `one_edit`) the **floor** is what binds — it was `0.05` s. What it has to cover
is the work no phase times: adapter subprocess teardown, the store open, the profiler's two count
snapshots. That cost is not proportional-slow, it is **spiky**: throttled to 0.4 CPU, 40 noops gave
p50 **8 ms**, p90 **65 ms**, max **115 ms** — **8 of 40 over the old floor**, 0 over `0.20`. At ~20 %
per scenario and three scenarios a run, a red run is a coin flip, which is exactly the one-runner-red
signature. **Method note:** the first hypothesis (the profiler's own snapshots dominate the gap) was
*refuted by measuring* — moving the wall boundary off them barely moved it — and that refutation is
what located the rest of the glue inside `incremental_update`. Do not ship a timing fix whose
mechanism you have not reproduced. **Fix:** floor raised to `0.20` s and named
(`WALL_FLOOR_SECONDS`), sized ~1.7× the worst tail actually produced; the report now carries
`unattributed_seconds`, so the glue is a visible number that can be watched instead of a pass/fail
bit; the test also asserts the load-independent half (the gap is never negative). **General shape:**
a `max(relative, absolute)` tolerance is only as portable as its absolute term — size that term
against the *tail* on a contended host, never the steady state on a fast dev box.

## 072 — A change that adds/removes a core module must grep pinned counts, not just moved symbols
The design's test-blast-radius grep matched the **symbols** being moved (the staleness constants,
which stayed importable via re-export) and concluded "no existing assertion is invalidated". But two
guardrail tests pin the **core-module count** (`assert len(core_modules()) == 36` in
`test_sql_confinement.py` and `test_core_is_language_agnostic.py`), and a *new* module `staleness.py`
broke both — surfacing only at the full-suite run, as an execute deviation. **Fix pattern:** when a
change adds or removes a file under a swept tree, the blast-radius step must also grep for **pinned
file/module counts and parametrize sources** (`len(... ) == N`, `rglob`, `parametrize(... modules())`),
not only the renamed/moved symbols — a count guard is invalidated by the file *existing*, with no
symbol match to find it by.

## 066 — Report an argument the server honoured only partially, and enumerate limit-takers from code

`cap = min(limit, max_results)` silently discarded the excess: `truncated`/`total_count` said *more
exist* but never *the tool honoured fewer than you asked* — different questions. A previous reader was
burned and hand-patched a caveat into the anchor repo's `CLAUDE.md`, i.e. the server was exporting a
caveat into every consumer's docs. **Fix pattern:** surface the honoured-vs-requested gap at the point
of use — one conditional field (`limit_capped_to`, the effective value) via a shared helper, present
only when a clamp occurred (061) — and state the knob's *full* meaning in the server's own answer
(`max_results` + `governs`: rows **and** resolver candidate fan-out — a hidden double duty makes a
caller mis-read `total_count`). **Uniformity guard:** a "holds for five tools, not the sixth" caveat is
worse than none, so guard it with a **source-scan test** that fails if any `tools/*.py` declaring a user
`limit` skips the helper — a new tool can't silently opt out. **Inventory from code, not prose:** the
ticket said "…and friends" but the code showed exactly five user-`limit` tools (`file_outline` uses
`max_results` directly, no user param) — the denominator came from `limit: int | None`, not the ticket.

## 067 — A storage sort reused for presentation makes correct results mislead

`_EDGE_ORDER` leads with `source_qname`, which *is* the file path for file-scope call sites, so a
truncated page 1 clusters into whichever top-level subtree sorts first — a fully correct, honest
payload (`truncated`, `total_count`) that still points a one-page reader away from the answer.
Correctness and usefulness diverge when the visible sample is unrepresentative, and no honesty field
repairs the sample. **Fix pattern:** prefer a cheap structural *representativeness signal* over a
reorder — an additive `result_subtrees` (top-level path segment → count over the full set) tells the
reader what the page hides while leaving row order, `offset` paging (057), determinism (R4), and every
golden payload untouched. The "measure before designing" kill gate earned its place: quantifying the
skew first showed it was **structural and guaranteed**, not rare — which justified building the fix
but chose the additive signal over an expensive total-order change.

## 068 — Synthetic anchors are edges, not source files

A rules bookmark that is a real `files` row with `parsed_ok=True` makes two honest counters disagree
by one. Keep the edge `file_path` for provenance; do not upsert a `files` row or File node. Purge
legacy bookmark rows on every apply so upgrades self-heal.

## 071 — Answers must name the tree they describe

`db_path` on status is a database location; agents need the **source root**. Emit `index_root` =
`config.root` on every answer (not status-only — agents skip status). Never guess the client's cwd.
Recommend `CA_DB_PATH` per worktree for isolation; the field only makes the un-isolated case legible.
Recalibrate the tokens-to-answer floor when every payload grows (`0.8 × observed`).

## 064 — Empty adapter map is misconfiguration, not an empty repo

`_announce` looping zero times looks like "nothing to do". Fail before meta when
`adapter_cmds` is empty. A successful build over zero matching files still stamps
non-empty `indexed_suffixes` so callers can tell the two apart. The empty-suffix-union
half needed no code: the handshake validator already rejects `extensions: []`. A guard
added for it was unreachable, and its test matched a regex the *handshake* error also
satisfied — a proving test must name the mechanism it proves, or it proves nothing.

## 063 follow-up — Cap the match set, not the CALLS table

`view_data` enrichment must look up CALLS by setter (`idx_edges_raw`), not scan a
`source_qname` prefix of *all* CALLS. A 10k cap on the whole table silently missed
~99% of anchor `setData` sites. Bound = O(matching sites); report truncation only if
a match-set cap returns.

## 063 — Count-first ACs need an Outcome above the mango separator

A “count before code” AC cannot be proven from a single squash commit. Put the table + kill/proceed
in the ticket **Outcome** (above the working-doc separator) and pin it with a small test that reads
that section — otherwise a ticket-blind challenger marks AC1 `can't tell` and Gate 4 fails.

## 062 — `key_arg` is an argument index, not a string-literal ordinal

`view_data` rules name which **argument** holds the key. Store `args` only record categories, so
enrichment must map `key_arg` through those categories to the Nth quoted literal on the call line
(e.g. `put($bag, 'extra', 1)` with `key_arg: 2`). Treating `key_arg` as a raw literal ordinal fails
as soon as a non-string arg precedes the key.

## 061 — Payload fields that earn nothing should leave nav/search

Keep `db_path` on `get_index_status` only. Make `next_tool_suggestions` state-reactive (empty when
current). Suppress redundant File∩Class search hits. Emit `subject_refreshed_only` only when the
subject was actually reparsed — a constant `true` is dead weight.

## 053 — Git refresh hooks must stay opt-in and out of band

When field evidence says an incremental can cost ~a minute, contrib git hooks must spawn
`code-atlas-refresh` in the background and always `exit 0`. Never auto-write `.git/hooks`.
Use a non-blocking lock beside the DB so overlapping hooks skip cleanly (R4.3) instead of
racing the MCP writer.

## 052 — Measure-only tickets still need an Outcome defect decision

When AC demands “is this a defect?” but the host has no repo-sized sample, record **suspected /
unconfirmed** with the field evidence and the profiler command — do not invent a phase split, and do
not close as honest price without one. Ship the profiler; leave 053 gated. Fixture-scale
confirm/refute + a stated pull_shaped wall still belong in Outcome even when the scale sample is unset.

A local-tier profiler that rebuilds `Config` from process env must **fail loud** when
`adapter_cmds` is empty — otherwise reconcile can wipe the index. After touch+restore scenarios,
re-run an untimed incremental so hashes match the restored tree.

## 060 — Record scale re-measures in ticket Outcome with a commit SHA

When an AC requires re-measuring full-build vs status on a clean server, land an `## Outcome`
section (with the tip SHA, and an honest “scale sample unset” if the anchor was not remounted) in
the same card as the code — reviewer and ticket-blind challenger both treat a missing Outcome as
not-met even when fixture tests already prove agreement.

## 058 — A status-only `detail_level` value must update CONVENTION §6

When one tool gains a third `detail_level` (here `verbose` on `get_index_status`), PLAN and the
MCP schema tests are not enough: CONVENTION §6 still said every tool is `{minimal, standard}` and
review correctly blocked on R7.2. Update CONVENTION in the same card as the Literal change.

## 057 — Scope "enumerate every result set" to store-ordered pages

When a ticket AC says every oversized answer must be fully enumerable, pin which
tools/depths use a total store ``ORDER BY … LIMIT/OFFSET`` versus a BFS with a
count floor. Otherwise review correctly rejects depth>1 callers as incomplete
against the letter of the AC. Record the scope in Outcome + PLAN in the same card.

## 056 — Spell `NodeKind` as `Literal[…]` and derive `NODE_KINDS` with `get_args`

`Literal[*NODE_KINDS]` fails mypy (`valid-type`) even when the tuple looks like string literals.
Spelling the `Literal` out (`NodeKind = Literal["File", …]`) and setting
`NODE_KINDS = get_args(NodeKind)` keeps one vocabulary, types MCP `kind: NodeKind | None` cleanly,
and publishes `anyOf: [{enum…, type:string}, {type:null}]` — coherent with a null default.
Do **not** bolt `enum` on via `json_schema_extra` as a sibling of `anyOf`: sibling keywords are
ANDed, so `null` satisfies `anyOf` but fails `enum` and the schema rejects its own default.

## 043 — A per-file dedupe keys on the full UNIQUE key, and a core guard never names `sqlite3`
Two constraints surfaced while making a duplicate-declaration file soft-fail instead of aborting the
build:
- **Dedupe by `(qualified_name, file_path)`, not `qualified_name` alone.** `replace_file_rows` is
  legitimately called with same-qname nodes for **different** files in one call (multi-candidate
  resolver siblings — `tests/test_resolver.py`). A qname-only key silently collapsed them; the design's
  own C1 already said the key is the full UNIQUE key. Match the constraint you are de-duping against.
- **A writer guard must catch a store-owned type, never `sqlite3` directly.** Adding `except
  sqlite3.Error` to `indexer.py` tripped `test_sql_confinement.py` (R1.4/R4.3 — only `store.py` may
  reference SQLite). Export a `WRITE_ERRORS = (sqlite3.Error,)` tuple from the store and catch that, so
  SQLite stays confined. Generalises: when the core must react to a boundary module's failure, the
  boundary owns the exception vocabulary.
Both were caught only by the **existing** regression suite, not the new tests — the delta-green
baseline diff (byte-comparing failure sets) is what exposed them; a bare pass/fail count would not have.
- **Baseline-set diffing has a blind spot: a test that fails-at-launch locally hides a regression in
  the code it would run post-launch.** A widened `replace_file_rows` return (`None`→`int`) broke the
  `RecordingStore` test double (it dropped the `super()` return), but `test_every_write_...` fails on
  the Windows dev host at fake-adapter subprocess launch, so it sat in **both** baseline and after
  failure-sets → the name-diff scored it "not new." CI (Linux) launched the adapter and hit the real
  `TypeError`. **Fix:** when a change alters a signature/return that a subprocess-only test path
  consumes, exercise that consumer **without** the subprocess (drive the store subclass / `_write`
  directly) rather than trusting the failure-set diff. Also: a store subclass override must propagate
  the base return value, and `tests/` is not mypy-checked so an incompatible override annotation there
  won't be caught by the `type` job.

### 043-C1 — Full-UNIQUE-key dedupe + store-owned WRITE_ERRORS
- type: 5 project-ground-truth
- status: confirmed
- evidence: `test_resolver.py` multi-file siblings; `test_sql_confinement.py`; Gate-4 clean
- area: store / indexer / R1.4 / R5.1
- destination: stays in lessons_path

## 042 — A ticket's "References" can be stale; verify claimed wiring before scoping
Task 042's References said the `source: sample` path was "already wired via `cross_repo_validate`". It
was **not** — `tokens_to_answer.py` skipped every non-fixture row and only listed sample IDs as
skipped. Taking the claim at face value would have under-scoped the task to a JSON edit; it actually
needed a new clone→build→evaluate code path plus a scheduled workflow (SCOPE S→L at Gate 0). **Fix:**
at analysis, grep for the symbol/path a ticket claims exists and confirm it before sizing; a stale
"References" line is a requirement to rebuild, not a freebie. Generalises: treat a ticket's factual
claims about the current codebase as hypotheses to verify, not givens.

### 042 — Env prerequisites are satisfiable locally, don't defer on their absence
The sample tier needs PHP+clone, absent on the Windows dev box (`php: not found`, no
`adapters/php/vendor`). Rather than defer the value claim to an operator run, a **portable PHP 8.3.33 +
Composer** env was stood up in scratchpad and the adapter ran end to end (fixtures 10/10, then samples
5/5, ratio 98.2). **Fix:** when a task is gated on a missing runtime, try provisioning a throwaway one
before falling back to a deferral — the fuller deliverable often beats the split. The earlier
`WinError 2` in tests was the *fake* test adapter's subprocess quoting, not the real adapter.

## 041 — Prefer language-free ignore globs over splitting a guarded token
Builtin Blade exclusion is `*.blade.*` (compound template suffix, any trailing extension) — not a
concatenated `*.blade.php` that defeats the R1.1 language-name guard. File-level builtins also apply
inside `collect_stubs` so `CA_STUB_ROOTS=vendor` cannot re-route ignored templates.

### 041-C1 — R1.1-honest Blade ignore + stub-walk coverage
- type: 5 project-ground-truth
- status: confirmed
- evidence: PR #47 review — split-token dodge rejected; `*.blade.*` + `_STUB_FILE_IGNORE`
- area: ignore / indexer / R1.1
- sub-shape: normative
- destination: stays in lessons_path

## 040 — Shipping enrichment requires PLAN §1 / R1.4 honesty in the same card
When an “optional enrichment layer” moves from non-goal into `code_atlas/`, update PLAN §1,
CONVENTION layout, and R1.4’s SRP inventory in the same PR — otherwise review blocks on R7.2
even when the runtime is correct.

### 040-C1 — Doc inventory lags new core module
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer findings 1–3 on `5926e2d`; fixed in `794b55d`
- area: docs / R7.2 / R1.4
- sub-shape: normative
- destination: stays in lessons_path

## 039 — Stub roots must bypass ignore *and* hash-gate on incremental
`vendor/` is a built-in directory exclusion, so `.codeatlasignore` negation cannot re-include it —
stub indexing needs a separate filesystem walk (`collect_stubs`). Those paths are also outside
`git ls-files`, so incremental must hash-gate the whole stub set (not only `changed ∩ stubs`), or
disk edits never refresh and enabling stubs mid-life never indexes new files (R4.2).

### 039-C1 — Incremental stub refresh is hash-gated, not git-named
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer finding on `changed_set & stub_set`; fixed in `ddcfe77` + `test_incremental_hash_gates_stub_edits`
- area: indexer / R4.2
- sub-shape: normative
- destination: stays in lessons_path
- seen: 039

## 038 — Edge-shaped hop dicts trip R3.2 unless keys are assigned one-by-one
Building a hop `{source_qname, target_qname, kind, confidence_tier, line}` as one dict literal
fails `test_contract_sole_source` (≤1 EDGE_FIELDS string per collection). Assign each key in its
own statement (or concatenate single-field key tuples), matching the impact/reachability pattern.

### 038-C1 — Path hop shaping must not multi-key EDGE_FIELDS in one literal
- type: 5 project-ground-truth
- status: confirmed
- evidence: sole-source fail on store.py / explain_path.py; fixed via per-statement hop keys
- area: store / tools / R3.2
- sub-shape: normative
- destination: stays in lessons_path
- seen: 038

## 037 — A guard that checks a formula against itself cannot catch a unit error in its input
037's A/B summed `call_delta` over **4** measured questions, then `verdict()` multiplied that
aggregate by a call count — so the published break-even was in *4-call batches*, wrong by ~4× (8.9 vs
35.7). The existing guard test fed `verdict()` hand-picked deltas and asserted its algebra, which was
self-consistent and stayed green. **Normalize where the number is produced** (`measure()` publishes
`call_delta_per_call`), and write the guard against the **unit**, not the arithmetic.

The tell was in the prose, not the code: the same sentence read "~7 tokens per call" and "break-even
8.9", and 241/7 ≈ 34. When a derived figure and its own stated rate disagree, the figure is wrong —
divide it out by hand before publishing it.

### 037-C1 — Aggregate-vs-per-unit must be normalized at the producer, not the consumer
- type: 5 project-ground-truth
- status: confirmed
- evidence: reviewer round 1 finding 1; `call_delta 27` over 4 questions; corrected 8.9 → 35.7 calls;
  regression guard `test_break_even_is_in_calls_not_in_measured_batches` fails `10.0 vs 40.0` when the
  defect is reinstated (re-mutated by the round-2 reviewer)
- area: benchmark / tokens-to-answer / A-B measurement
- sub-shape: normative
- destination: stays in lessons_path
- seen: 037

### 037-C2 — A decision's argument must be withdrawn when its number moves, not re-fitted
- type: 5 project-ground-truth
- status: confirmed
- evidence: Decision §1 ("crossover ~9, an agent passes it inside one task") no longer held at ~36
  calls and was struck rather than re-argued; the verdict was re-grounded on "no net win at all"
  (−234…+434 tokens) plus C3 and R1.2, and the round-2 reviewer judged the result honest
- area: mango / review / recorded decisions
- sub-shape: normative
- destination: stays in lessons_path
- seen: 037

## 033 — Split vocab-vs-emit when a later ticket owns emission
When Scope lists an enum member (e.g. `index_stale`) that a dependent ticket (035) will emit, refine
must record **W1 vocab present** and **W2 no emit-proof this card**. Otherwise a ticket-blind
challenger scores emission as **not met** against the raw ticket and looks like a Gate-4 miss.

### 033-C1 — Enum members deferred to a paired ticket need W1/W2 at refine
- type: 5 project-ground-truth
- status: confirmed
- evidence: challenger 7cf518c3 row 1b; ASSUMED Option 1; task 035 pairs with 033
- area: mango / refine / reason-codes
- sub-shape: normative
- destination: stays in lessons_path
- seen: 033

Durable lessons discovered while shipping tasks: constraints found, wrong assumptions, process gaps.
One entry per lesson; newest first.

## 030 — Alias remap must rewrite `Class::method`, not only class FQNs
`alias_targets` maps alias class → real class. CALLS/NEW often carry `\Alias::method`. Remapping
only exact class keys leaves method edges dangling; rewrite the class portion before `::` so
`find_callers`/`find_references` under Real see Alias users.

### 030-C1 — Alias remap rewrites the class portion of member qnames
- type: 5 project-ground-truth
- status: confirmed
- evidence: resolver `_lookup_raw` rpartition; proving test Aka::ping → Real::ping
- area: resolver / aliases
- sub-shape: normative
- destination: stays in lessons_path
- seen: 030

## 029 — Innermost class owns `parent::`, not an outer ancestor
`enclosingParentQname` must stop at the first `Class_` in the scope stack. Walking past a
null-`extends` class (e.g. anonymous nested inside `Outer extends Base`) falsely attributes
`Outer`'s parent to the inner class — a RESOLVED-eligible lie (R5.2). Return null when the
innermost class has no extends and leave `\parent::…` as today.

### 029-C1 — parent:: resolution must not walk past an innermost Class_ with null extends
- type: 5 project-ground-truth
- status: confirmed
- evidence: review finding on feat/029; NestedOuter fixture; Visitor.php enclosingParentQname
- area: php-adapter / receiver-resolution
- sub-shape: normative
- destination: stays in lessons_path
- seen: 029

## 028 — Prefer `parsed_ok` over a parallel meta parse-failure counter
When a ticket asks for `parse_failures` "if the build does not already persist this", check existing
aggregates first. `files.parsed_ok` already feeds `GraphStore.counts()["failed"]`; a second `meta`
counter can drift from the file rows (R4). Alias the status field (`parse_failures`) to that count
on `standard` and keep the existing `failed` key for minimal byte-identity.

### 028-C1 — Parse-failure status reads `files.parsed_ok` via `counts()["failed"]`, not a parallel meta counter
- type: 5 project-ground-truth
- status: confirmed
- evidence: ticket 028 R3 conditional; `code_atlas/store.py` counts(); indexer marks `parsed_ok=0`
- area: index-status / parse-health
- sub-shape: normative
- destination: stays in lessons_path
- seen: 028

## 016 — Dependents must be reparsed, not reconstructed
Hash-skipping dependents made `file_paths_targeting` dead work: a dependent is unchanged by
construction, so its hash always matches and it never reached the adapter. Reconstructing its edges
via `unlink_targets` (and collapsing HEURISTIC siblings) then lost adapter confidence tiers and
legitimately duplicated keys — diverging from a full rebuild (R4.2). **Always reparse dependents**;
hash-skip only unchanged *changed* paths. `replace_file_rows` restores adapter output verbatim.

Also: fold paths leaving `collect` (rename sources, newly ignored) into affected qnames *before*
reconcile — `git diff --name-only` names only the rename destination — and union the working tree
vs `HEAD` into the incremental path set so uncommitted edits are not a silent no-op.

## 014 — `code-atlas --help` is not an install smoke test
FastMCP's entry point always calls `.run()` (stdio). Passing `--help` still starts the MCP transport
and will hang CI waiting on stdin. Prove a non-editable install with `importlib.metadata` (version +
console_scripts entry) and an import of `TOOL_NAMES`, never by invoking the server binary.

## 014 — `LIKE ESCAPE '\\'` breaks PHP qnames
Namespace filters that use SQL `LIKE` with backslash as the escape character mis-parse every `\` in
a PHP FQN (`\App\Models\…`). Use a rare escape character that does not appear in qnames (e.g. `!`)
and escape only `!`, `%`, and `_`.

## 012 — Planted tmp_path negative controls must not use relative_to(ROOT)
AC2 plants live under pytest `tmp_path`, which is outside the repo. Calling
`path.relative_to(ROOT)` on those plants raises `ValueError` and breaks the proof that the
grep-gate fails on a planted hit. Assert on `Path` identity (or root the plant under the repo).

## 025 — NEW must peek anonymous qnames without registering them
`enterNew` and `enterAnonymousClass` both need the same H1 qname. If both call a registering
`anonymousQname()`, the Class_ node gets a spurious collision suffix even when it is the only
anonymous class on that line. Peek (`register: false`) on the NEW edge; register only when declaring
the Class_ node. Same-line *true* collisions append `:col` from `getStartFilePos()` (ticket C1) —
not an ordinal, which would rename later same-line declarations when one is inserted earlier.

## 008 — Proving-test names must not overclaim the path shape they assert
Review caught that `…_results_stay_repo_relative` asserted host-**absolute** `ParseResult.path` after
wire rebase (Approach §3 keeps the **caller** path). The relative half was the real repo-relative
proof; the name lied about the absolute half. Rename (or split asserts) so the test title matches
what each half actually checks — R6.1 proofs and CONVENTION “repo-relative” claims stay honest.

## 011 — Never promote HEURISTIC to RESOLVED just because a name is unique
PR review caught that `_resolve_symbol` set the tier from hit count alone. An adapter-emitted
`HEURISTIC` edge whose `target_raw` matched one qname became `RESOLVED`. A unique name does not make
a guess certain — M6 impact will trust these tiers. Fix: take the weaker of (incoming, computed).

**Also deferred to M4 (task 015):** per-edge SQLite commits + materializing all unresolved edges, and
top-N name-match fan-out on common method names (`get`/`save`) exploding edge counts.

## 011 — A clean `Reviewed at` does not survive tip commits landed after it
Task 011's review was clean at `cf445e4` (resolver change-list only). Teammate commits for
`AGENTS.md` / `.mailmap` then landed on the same branch. Finalise's stale-review guard correctly
refused: the marker is a **file-set** claim, not a "we reviewed this ticket once" claim. Keeping the
tip without a new `Reviewed at` covering HEAD is a **human override**, not a cleared gate.

**Fix:** either (a) re-review the full tip and rewrite the marker, or (b) land teammate docs/chore
work on a separate branch/PR so the feature marker stays valid.

## 010 — The same thread rule that enforced a design in 009 dictated the design in 010
Task 009 found that `sqlite3` binds a connection to its creating thread, and treated it as a free
guarantee: R4.3's single writer could not be broken by accident. Task 010 met the same fact from the
other side. FastMCP registers a synchronous tool with `run_in_thread=True` by default, so **every**
tool call runs on a worker thread — a `GraphStore` opened when the server was built raises
`ProgrammingError: SQLite objects created in a thread can only be used in that same thread` on its
first use, in every call, forever. The obvious shape (build the server, hold the store, serve) does
not work at all.

So each tool opens its own store inside the call, and `get_index_status` opens none when there is no
database file. The lesson is not "sqlite is thread-affine" — 009 already recorded that. It is that a
constraint discovered as a *guarantee* in one task can be the thing that *rules out* the natural
design in the next, and only a spike against the real library says which. This one was tagged
`novel-untested` at design and spiked before Gate 2; it came back **false**, and the ten-line spike
that killed it cost less than the rewrite would have.

**Fix:** when a task hands work to a third-party runtime, spike *where that runtime runs your code*
before designing what your code holds on to.

## 009 — The runtime may already enforce the rule you were about to prove by convention
R4.3's "single SQLite writer" read like a discipline the indexer had to keep. It is not: `sqlite3`
binds a connection to the thread that created it, so a worker thread that tried to write through the
build's store raises `ProgrammingError` — loudly, before a single row is touched. The design was
better for finding out: the fan-out needs no lock, no write queue, and no review vigilance, because
the failure mode it was guarding against cannot compile past the first call.

The general lesson is about **when** to check. This was a `novel-untested` assumption tagged at
design and spiked *before* Gate 2, not discovered at execute. Two of the five spikes changed the
design, and this one changed it by coming back **false** — which is the whole point of tagging an
assumption instead of asserting it.

## 009 — A negative control can indict the code instead of the test
Five mutation controls ran against `full_build`; two came back green, and they meant opposite things.
Deleting the `sorted()` from collection broke nothing because the fixture tree happened to be
discovered in order — a **test** too weak to see its own subject, fixed by shaping a tree the walk
provably reaches out of order. Deleting the per-build `rebuild_search_index()` also broke nothing,
but no test could ever have caught it: the schema's triggers already keep `nodes_fts` current, so the
call was a full re-index that changed nothing. That one indicted the **code**, and it was removed.

So a green negative control is a question, not a verdict: *can* a test see this, or is the line
unreachable by construction? The first answer costs a better fixture; the second costs a deletion —
and on a 112k-file repo, that particular deletion is a whole FTS rebuild per build.

## 007 — A stream protocol inherits the host's `php.ini`, so "it works here" proves nothing
Two ini settings silently corrupt a JSONL protocol, and neither shows up on a developer machine.
`display_errors` defaults to **stdout** on many builds, so a PHP notice lands *between two protocol
lines* and the driver reads it as a reply; `output_buffering` holds `echo` output until the process
exits, deadlocking a lock-step reader. Both are host state, so the same file yields different results
on two machines — exactly what R4.2 forbids. **Fix:** force `display_errors` to `stderr` before
anything is written, and write replies with `fwrite(STDOUT, …)`. Note the trap: the design approved
`fflush(STDOUT)` as "immune to any host ini" and that was **false** — `echo` has already entered PHP's
*output buffer*, which neither `fflush()` nor `flush()` releases. Only bypassing `echo` works. Prove a
buffering fix by reading **while the child still runs**; at exit every buffer flushes, so a
post-mortem read passes no matter what.

## 007 — A language's natural empty value may not be the contract's
`json_encode(['capabilities' => []])` yields `{"capabilities":[]}` — a JSON **array**. The contract
requires an object, so the core rejected the handshake with a loud startup error naming
`meta.capabilities`, pointing the reader at the core rather than at the one adapter line responsible.
PHP has one array type for both shapes; `new stdClass()` is needed to get `{}`. **Fix:** spike the
handshake against the real validator before writing the loop — the design phase caught this, and had
it slipped to execute it would have read as a driver bug. Generalises to every adapter: an empty map,
an empty list, and a null are three different wire values, and a language that conflates any two of
them will encode the wrong one by default.

## 024 — A rule enforced only by a lifecycle gate is unenforced for work that skips the lifecycle
`AGENTS.md` says no PR opens without the task's token spend recorded in **both** the working-doc cost
ledger and the BACKLOG table. Tasks 001–006 all complied — because mango's `finalise` phase has a
ledger-completeness gate that refuses to proceed without it. Task 024 was done directly, outside the
five-phase lifecycle, so nothing checked, and PR #14 opened with no token row and a status left at
`in-progress`. The rule was never *disagreed* with; it simply had no enforcement outside one tool's
happy path. **Fix:** `tests/test_backlog_bookkeeping.py` asserts both bookkeeping rules from the repo
itself — every task's status matches in the backlog table and its frontmatter, and every `done` task
carries a token row naming a measured spend and a PR link. Negative-controlled three ways: deleting the
row, desyncing a status, and writing a spend cell with no number each turn it red. Generalises: when a
process rule lives in a document and its only enforcement is a step inside one workflow, it is
**optional by construction** — the moment work arrives by another path, the rule is silently off. Put
the check where the artifact lives, not where the process happens to run.

## 006 — An `instanceof` narrow that falls through to null erases the difference between "absent" and "unhandled"
The PHP visitor read a parameter's type as `$param->type instanceof Node\Name ? fqn(...) : null`. That
looked right and passed both fixtures, because both typed parameters happened to use *class* types. But
`string`, `int`, `bool` and every other scalar hint arrive as `Node\Identifier`, so they fell through to
`null` — and in the emitted JSON, `"type": null` is exactly what an **untyped** parameter looks like. The
adapter was not deferring the case; it was reporting the wrong answer, and nothing could tell. A
ticket-blind challenger found it by writing its own probe file with a scalar hint. **Fix:** when mapping
a foreign AST or schema into your own vocabulary, an `instanceof` chain whose fallback is `null` needs
either exhaustive arms or a loud fallback — never a silent one that collides with a legitimate value.
Generalises: a partial mapping is only safe when "I did not handle this" is **distinguishable in the
output** from "this was not there". Ask of every `?:` default whether some real input already produces
that same value; if so, the branch cannot be audited from the data.

## 006 — The first vendored dependency turns a repo-wide grep-gate into a false positive
`ci.yml`'s R2.2 gate greps `adapters/` for framework names. It was green for five tasks because
`adapters/` was empty. The first `composer install` put 280 files there, and **Composer's own
`vendor/composer/ClassLoader.php` documents itself with a `Symfony\Component` example** — so a
guardrail about *our* source failed on a dependency nobody here wrote. The same run also had
`tests/test_sql_confinement.py` sweeping all 280 dependency files looking for the string `code_atlas`.
**Fix:** scope every guardrail grep to *authored* source (`--exclude-dir=vendor --exclude-dir=node_modules`)
and then guard the scoping — a filter that quietly swallows the authored files too restores exactly the
0/0 vacuity the guard existed to remove (LESSONS 002), so assert the sweep is non-empty. Do it in the
change that introduces the first dependency, since that is the change that creates the collision.
Generalises: a text-grep guardrail's blast radius is a **directory**, not a codebase, and directories
grow third-party content the moment a package manager runs.

## 005 — A subprocess seam fails by silence and by chatter, not by errors
Two failure modes of a long-lived adapter process are invisible in the happy path and neither raises.
**Chatter:** with `stderr=PIPE` left undrained, a child that writes more than a pipe buffer (~64 KB)
blocks writing while the driver blocks reading stdout — a spike reproduced it with 200 KB and got no
reply in 3 s. `stderr=STDOUT` is worse: it corrupts the protocol stream. Only `DEVNULL` or a real file
is safe, and a PHP adapter emitting warnings makes this the *normal* case, not an exotic one.
**Silence:** a child that stays alive and simply never answers hangs a blocking `readline()` forever —
and it does so at `start()` (waiting for the handshake), not only at `parse()`. The analysis had
recorded the hang as a `parse()`-only exclusion; execute found the wider truth when a fixture mode that
went mute wedged the whole suite. **Fix:** never leave a subprocess pipe undrained; treat *silence* as
a first-class failure mode with its own deadline, and when deferring it say which calls it can strike,
not just the obvious one. Generalises: for any IPC seam, enumerate what happens when the peer says
**too much** and when it says **nothing** — those are the two that hang rather than throw, and a test
suite that only feeds well-formed errors will never meet either.

## 005 — A ticket-blind agent can read the working doc without opening it
The challenger is kept honest by *withholding* the working doc: it is handed the raw ticket text plus
the diff and told not to read `docs/tasks/`. It obeyed — and still saw the design. A `git grep` for
`--server` across the repo returned matching lines *from* the working doc, including a "RATIFIED (Q2)"
rationale, so the author's reasoning landed in front of it before it had formed its own view on that
requirement. It disclosed this itself; six of its seven other verdicts were unaffected. **Fix:** the
blind-agent brief must exclude the tickets directory from **every search**, not just from direct reads
(`git grep ... -- ':!docs/tasks/'`, `grep --exclude-dir`), and the agent should be told to report a
leak rather than quietly continue. Generalises: an information barrier enforced as "don't open that
file" leaks through every tool that reads files *without opening* them — grep, search indexes, IDE
symbol lookup. Scope the barrier to the **content**, not to the act of opening; and since the guarantee
is procedural, report it as procedural rather than as proof.

## 004 — A schema object that exists is not a schema object that runs
`tests/test_store.py` asserted every DDL object was registered in `sqlite_master`, and that assertion was
read as if it also proved each object *works*. It does not. The ticket-blind challenger replaced the body
of the `nodes_au` FTS trigger with a reference to a nonexistent column and **the whole suite still passed**
— because `GraphStore.replace_file_rows` only ever DELETEs then INSERTs, so nothing in the codebase fires
an UPDATE on `nodes`. A broken trigger would have shipped green. **Fix:** for any schema object no code
path currently exercises (trigger, `DEFAULT`, `CHECK`, `ON DELETE`), write a test that *fires* it directly
in SQL, and keep the object rather than deleting it as dead code when it closes an invariant — a mirror
with a hole desyncs silently the first time a later task takes that path. Generalises: **existence tests
and behaviour tests are different tests**, and mutation is the cheap way to tell which one you actually
wrote — break the thing on a copy and see whether anything goes red. The same run also caught a related
self-report: the task's own matrix claimed `busy_timeout` was asserted when nothing asserted it.

## 036 — Distribution hooks that promise exit 0 must wrap config load too
A Claude Code PostToolUse script documented as "always exits 0" still raised when
`load_config` saw an unpaired `CA_HOST_ROOT`. Soft-fail only around `reparse_file` is not
enough — wrap imports + config + reparse. Relative path containment must `resolve()` under
the project root (``../`` escapes are not no-ops).

## 035 — Missing on-disk paths are stale; planted fixtures must write matching bytes
`FreshnessGuard.ensure` returns `"stale"` when `(root/path).is_file()` is false so production
never asserts `reason=ok` for a deleted indexed file. Planted-store nav tests therefore write real
bytes (and the matching content hash) in `seed_file(..., root=)` — a shared short-circuit that
trusted the index for missing paths caused the trust bug 033 closed. Adapter/DB failures during
`reparse_file` also degrade to `"stale"` instead of crashing the read tool.

## 073 — Zero-hit freshness cannot invent a subject path
Read-through (035) only repaired paths already on the answer. A brand-new symbol in a drifted file
matched nothing, so `ensure_qname` / `search_symbol` returned a confident empty without reparsing.
**Fix:** miss-repair spends `READ_THROUGH_CAP=1` on the sole dirty indexed tracked file; multiple dirty
files emit `index_stale` + `try_instead=file_outline` instead of guessing. Requires git
`dirty_paths`. Generalises: result-driven repair is incomplete without a documented miss path.

## 065 — Inbound includes cannot be counted by target_qname
`include_graph(direction="imported_by")` used to emit `unresolved_includes: 0` because the outbound
counter is skipped for that direction — a confident zero that is structurally always zero. Unlinked
inbound edges have empty `target_qname`, so they are invisible to `edges_by_target`. **Fix:** omit the
field for `imported_by`, and only claim `relationship_not_modelled` when a cheaper basename
`instr(target_raw, …)` proxy finds evidence. Generalises: a counter that is unanswerable in one
query direction must not print zero; absent beats a structural lie.

## 004 — `git checkout -- <file>` restores the committed state, so it deletes uncommitted work
While negative-controlling the R3.2 guard, a violating literal was appended to `code_atlas/store.py` and
then reverted with `git checkout -- code_atlas/store.py`. The implementation was **not yet committed**, so
the checkout restored the one-line stub from `main` and the whole module was gone; it had to be rewritten.
The first negative control had worked only because the file it mutated (`config.py`) was unmodified in the
working tree. **Fix:** commit the work **before** running any guard experiment that mutates tracked files,
and restore from a `cp` copy (verify with `sha256sum`) rather than from git. Generalises: `git checkout --`
is not an undo for *your* edit — it is a reset to the index/HEAD, and its blast radius is every uncommitted
change in that file.

## 003 — The R1.1 grep-gate fires on ordinary English, not just on code
The CI guardrail for "no language branches in the core" is
`grep -rEn 'if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b' code_atlas/`
(`.github/workflows/ci.yml:49`). Its second alternative has **no code anchor**: any line under
`code_atlas/` where the token `match` appears *before* the word `language` fails the build — including
a plain comment or docstring like `# match the language name to its env var`. The reverse order
(`language … match`) is safe. **Fix:** when touching the core, phrase prose so `language` precedes
`match` (or avoid one word), and run the gate's exact regex locally before opening the PR — a green
`pytest`/`ruff`/`mypy` says nothing about it. Generalises: a guardrail expressed as a text grep over
source will also match the *prose* in that source, so treat comments and docstrings as inputs to
every grep-gate, not just the code.

## 002 — A guard written before its consumers exist must be negative-controlled
Task 002's AC2(b) ("no field lists duplicated in store/indexer") was **vacuously true**: all five
schema-consuming modules were one-line stubs, so any grep or guard passed while proving nothing about
the tasks that would actually write them. A guard that cannot fail is not evidence. **Fix:** inject a
real violation (`COLUMNS = ["kind", "name", …]` appended to `store.py`), confirm the guard fails, then
remove it and confirm the file is byte-identical again — and assert the guard's own inputs are non-empty
(`len(VOCABULARY) == 38`, `len(consumers()) >= 5`) so it can't silently degrade to a no-op later.
Generalises: when an acceptance criterion is satisfied only because the thing it constrains doesn't
exist yet, say so out loud and either negative-control the guard or record the vacuity.

## 001 — Fold a mid-task governance request into the ticket's scope, don't ride it on the branch
When a user asks for a repo-wide rule change mid-task (here: the "Token usage on PR" rule in
`AGENTS.md` + `docs/BACKLOG.md`), the ticket-blind challenger and the reviewer both read it as
untraceable scope creep — it maps to no ticket requirement. **Fix:** add it to the task's
Scope/Deliverables + a matrix row (task 001 → R6 + change-list item 8) with a one-line rationale, so
every hunk still traces to a requirement. Splitting it into its own docs ticket is the alternative;
either way, never let a change ride the branch untraceable to a row.
