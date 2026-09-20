"""The standing docs an agent reads every session have a per-file ceiling (task 134).

Every file bounded here is on `AGENTS.md`'s *read before non-trivial work* list — plus `PLAN.md`,
which 133 moved to tier 2 but which a `§`-ref still pulls in — so a session pays for all of it.
The **sum** of tier 1 is capped separately, in `tests/test_agent_chain_budget.py` (133): a
per-file ceiling cannot stop six files each staying just under theirs.

Nothing stopped them growing: eleven field-retro narratives, per-round ordering
essays and a token ledger whose cells had become per-ticket retrospectives took `PLAN.md` +
`BACKLOG.md` to **56,039 tokens**, and `ENGINEERING_RULES.md` carried a copy of every rule's ticket
sightings whose source of record is `LESSONS.md` (P1) — most of it restating something that already
held it.

The ceiling is not a style preference. It is the mechanism R7.6 needs: growth is fine until it
crosses the line, and crossing it makes the next change prune instead of append. Raising a number
here is allowed — but it is a visible edit that has to be argued for in a PR, which is exactly what
was missing.

Tokens are counted with `estimate_tokens`, the one definition site (R6.7); a second
chars-per-token proxy in a test is the drift that rule exists to stop.
"""

from pathlib import Path

import pytest

from code_atlas.tokens import estimate_tokens
from scripts.agent_chain_cost import chain

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# Re-measured 2026-08-23 by `scripts/agent_chain_cost.py` after 133 moved the token ledger out of
# BACKLOG and PLAN off the binding list, plus headroom for what a task legitimately adds. BACKLOG
# drops from 14,000 because the ledger it was sized around is now `TOKEN_LEDGER.md`; CONVENTION
# rises by 200 because §8.1's Tier column is permanent structure, not narrative. `PLAN.md` keeps a
# ceiling though it is tier 2 — a `§`-ref pulls it in anyway (R7.6). `TOKEN_LEDGER.md` gets none:
# it is append-only by R7.2, so a ceiling there would force pruning the evidence.
#
# CONVENTION rises 6,300 -> 6,450 on 2026-08-28 (task 175), argued rather than assumed: §6's
# payload-field table is the product's cross-tool contract, so it grows exactly when the payload
# surface grows, which is what 174/170/175 each did. All three paid for their addition by pruning
# restatement first — consolidated rows, retold incidents, clauses that repeated their own row — and
# the remaining text is information a session would otherwise rediscover from source. 150 tokens
# buys three payload conventions. The next addition prunes again or argues again; it does not
# inherit this raise as headroom.
# CONVENTION rises 6,450 -> 6,600 on 2026-08-29, argued rather than assumed. The README was
# carrying ten ticket design sections while §8.1's own README row said it is "not the design
# record" — the table recorded the boundary and nothing enforced it. Splitting that out created two
# document classes (`TOOLS.md`, `design/*.md`), and a class with no row in §8.1 is precisely the
# unbounded document the table exists to prevent, so the rows are the fix, not an extra.
#
# Paid for inside tier 1, not by raising its total (133's cap is untouched and still binds at
# 25,150): §1's two directory comments that re-listed the directory beneath them, one restated
# clause in §8.1's preamble, and AGENTS.md's *Where things live* — a second copy of this file's §1
# in a file that already said "full layout in CONVENTION.md", which is the R7.6 case exactly. The
# next addition prunes again or argues again; it does not inherit this raise as headroom.
# ENGINEERING_RULES 4,900 -> 5,300 and AGENT_BRIEF 2,000 -> 2,250 on 2026-08-30, argued rather than
# assumed. The 2026-08-30 promotion pass closed six type-2 classes the corpus had earned at
# recurrence 2-3: R5.2 and R6.7 were WIDENED rather than duplicated (AGENT_BRIEF P2), R5.8 and R6.9
# are new, P7 is new, and `two-syntaxes-two-paths` was in R6.2 already. R7.6's "prune as you add"
# has nothing to cut here: what a promoted rule supersedes is the recall weight of a claim
# in LESSONS.md, which is tier 2 — so the payment has to come from elsewhere in tier 1.
#
# Paid for inside tier 1, not by raising its total (133's cap is untouched and still binds at
# 25,200; the chain sits at 24,575): every `done` row in BACKLOG.md is now titled by its own slug
# instead of a prose sentence retelling what that ticket's file already holds — 176 rows, 1,405
# tokens, the R7.6 case exactly, and the slug is derived from the filename so it cannot drift.
# BACKLOG's own ceiling drops 9,500 -> 8,200 in the same change, so the room that bought these rules
# cannot be silently re-consumed by narrative. The next addition prunes again or argues again; it
# does not inherit this raise as headroom.
# 2026-08-31 promotion (R1.9 new, R3.5 new, R6.9 widened): ENGINEERING_RULES.md 5,300 -> 5,700.
# Paid for inside the file first, per R7.6 — four passages that retold what another document
# already holds were cut for 173 tokens: R1.2's adapter-selection mechanism (PLAN §19), R6.5's gate
# paragraph (AGENTS.md *Before a PR*), R7.6's re-listing of the tier-1 set (AGENTS.md's own list,
# and a listed set where a derivation exists is what R6.7 forbids) and R7.1's release history
# (AGENTS.md *Ship discipline*). 133's cap is still 25,200 and untouched; the chain sits at 25,190,
# so the three rules were bought, not borrowed. The next addition prunes again or argues again.
# BACKLOG 8,200 -> 8,300 and 133's cap 25,200 -> 25,300 on 2026-09-01, argued rather than assumed.
# Both ceilings were last re-measured against a table with **no open rows** — every row was `done`
# and therefore slug-titled, which is why 10 tokens of tier-1 slack looked like enough. Tickets
# 200-202 are the first open rows since, and this file's own preamble says an open row is titled by
# its finding, because that title is what you read to choose the next ticket. R7.6 has nothing to
# prune here: the text is the finding, and the prior pass already took the restatement.
#
# The raise was argued as temporary — "the rows shrink to slugs the moment they close, which returns
# the raise" — and closing 201 and 202 measured that claim and refuted it. The three rows cost 138
# tokens; slug-titling all three returns 11. The raise bought three PERMANENT table rows, not three
# verbose titles, so it does not come back when they close and no later pass should plan on it. The
# number to watch is the row count, not the row wording. The next addition prunes or argues again.
# PLAN 24,000 -> 23,000 on 2026-09-01, LOWERED after a compaction pass, so the room it freed cannot
# be silently re-consumed by narrative — the move BACKLOG's 9,500 -> 8,200 made above. What came out
# was retelling, never a decision: §19's field-retro and interview entries kept their verdict,
# their measured numbers and their ticket refs and dropped the walk-through that 075, 077, 121's
# benchmark, ROADMAP.md and the task files already hold; 130/131 kept their outcome instead of the
# struck original beside its correction; 059's operator-local occurrence census left, its decision
# stayed. Two second copies went entirely: §11's knob table (TOOLS.md's Configuration reference is
# the record, and PLAN's copy was two knobs behind) and the return-shape half of §12's tool cells
# (TOOLS.md holds what a tool returns; PLAN keeps args and the design decision). Both were drifting,
# which is the argument (R6.7). Net 23,978 -> 22,855, and no link and no ticket reference was lost.
# 8,300 -> 8,700 on 2026-09-02 (tickets 205-212): eight open rows from one investigation — a single
# onboarding artifact read end to end, plus three ideas taken from an external reference tool and
# one incremental-cost gap the reading exposed. Each defect was filed separately, not bundled,
# which is what costs the 400. R7.6 ran first and came back empty both times it was tried: the
# Conventions section names one mechanism — "a ticketed follow-up leaves the Follow-ups list" — and
# none of the eight tickets one. 205 and 212 are the near misses, both rejected on inspection
# (205's Scope 1 leaves `impact_max_nodes` alone for `reachable_from`; 212 skips on a declaration
# fingerprint, not the byte cap the parser-OOM follow-up describes), because deleting either line
# would record a fix that did not happen. No id sits in two tables; every `done` row is slug-titled.
# 8,700 -> 8,800 on 2026-09-02 (205 landing): one follow-up line, because the onboarding tree's
# remaining bulk — manifest.json + index.html at ~2.5 MB against ~21 KB of Markdown — is a design
# question nothing else records, and the row flip to `done`. R7.6 ran first and came back empty
# again: 205 supersedes no BACKLOG line (its own row stays, with `done`), and the three other facts
# the run earned went to LESSONS.md and the task file rather than here, which is what kept the raise
# to 100. The follow-up itself is two lines pointing at the task doc, not a retelling of it.
# 8,800 -> 2,200 on 2026-09-05 (task 218): measured 1,826 after the 208 `done` rows came out. The
# ceiling drops 6,600 rather than banking it — a budget that is not close enough to bite is the
# slack the test below forbids. The 374 of headroom is ~10 open rows, which is more than the file
# has ever held open at once.
# 2,200 -> 2,100 on 2026-09-05 (217 closing): measured 1,736 once 217's `done` row left, and
# 2,200 is more than 25 % above that, which the test below calls slack. 218's figure had only
# 14 tokens of margin against its own rule; 2,100 keeps ~10 open rows of headroom and 434 of
# margin. Nothing is banked — the ceiling tracks the file.
# 2,100 -> 2,450 on 2026-09-06 (226-230 filed): measured 2,399 with five open rows added to a
# file already at 2,098 against 2,100 — the ceiling had no headroom left to absorb even one. Two
# field builds over private Python repos produced five distinct defects (adapter linkage, receiver
# typing, a SQL dialect the adapter reads nothing of, method locals published as class members, and
# unreachable source roots); each is filed separately rather than bundled, which is 205-212's
# precedent and is what costs the 350. R7.6 ran first and came back empty: no row here is
# superseded — the near miss is 042's PSR-4 follow-up, which is 230's problem in the PHP adapter
# and stays because 230 scopes other adapters out — and each finding lives in its task file, not in
# its row. 51 of margin, ~2 open rows.
# BACKLOG 2,450 -> 2,550 and CONVENTION 6,600 -> 6,700 on 2026-09-06 (tickets 231-233 plus the
# adapter playbook), argued rather than assumed. **133's cap is untouched and still binds at 19,800;
# the chain sits at 19,799** — both raises are paid for inside tier 1, not by widening it.
#
# BACKLOG measured 2,480: three open rows (231, 232, 233). R7.6 ran first and took three items, all
# under this file's own convention that a ticketed follow-up leaves the list — 043's
# duplicate-declaration gap (220 owns it), 018's construct gaps (007 and 025 are both `done`), and
# the adapter/tier ticket mapping, which the playbook's §1 table now holds in one place.
#
# CONVENTION measured 6,650: one row in §8.1 for `ADAPTER_PLAYBOOK.md`. A new document class with no
# row there is exactly the unbounded document the table exists to prevent — the same argument the
# 6,450 -> 6,600 raise was granted for, and the row is the fix, not an extra. Pruned first: §8.2's
# copy of the no-Memory rule, which AGENTS.md carries as an always-loaded rule, and the tier
# legend's prose copy of the token cap. That number had gone stale at 19,400 in **both** tier-1
# files that restated it, which R6.7 forbids; it now lives only in `test_agent_chain_budget.py`.
#
# The next addition prunes again or argues again; neither raise is headroom.
#
# 2026-09-06, same PR, second round (tickets 234-235 + the generated parity table): BACKLOG measured
# 2,498 against the 2,550 already raised above, so **no further raise** — the two new rows were paid
# for by pruning, which is what the line above asked of the next addition. Taken: the Follow-ups
# entry that 205 owns (this file's own convention says a ticketed follow-up leaves the list), a
# preamble paragraph restating the closed-ticket policy that the Conventions section at the foot of
# the file already owns, and the five open rows trimmed to one clause each. The chain sits at 19,837
# against 19,850.
#
# AGENTS.md 2,800 -> 2,850 on 2026-09-06, with 133's cap 19,800 -> 19,850 beside it — a reversal,
# argued. An earlier revision of this PR pruned the `Comments <= 3 lines` non-negotiable from
# AGENTS.md on the reasoning that R7.5 owns it. That reasoning does not hold: the section's own
# header reads "summary — authoritative detail in ENGINEERING_RULES.md", so every bullet in it
# duplicates a rule by design, and the argument applied consistently would delete the whole
# section. The line is restored, now carrying its `(R7.5)` destination like its siblings. Paid for
# in part by dropping AGENTS.md's copy of the R1.2 registry provenance — the third one, after
# `ENGINEERING_RULES.md` R1.2 and PLAN §19, and provenance is §19's job per CONVENTION §8.1. The
# remaining ~17 is the standing cost of an always-loaded rule, and is what these two numbers buy.
# PLAN 23,000 -> 23,150 on 2026-09-08 (232 + 234), argued rather than assumed. §19 gains two
# permanent decision entries — annotations/decorators are edges in every adapter (232) and what
# counts as ClassConst evidence (234) — and a decision entry is the structure this log exists to
# hold, not narrative. R7.6 ran first and paid most of it: 232's entry was written at 252 tokens and
# cut to 165 by moving the 019/217 provenance walk-through to its task file, 234's compacted the 219
# populated-rebuild paragraph it sits beside (-253 for +252), and §8.2's `REFERENCES` bullet was
# WIDENED to name the two new RESOLVED sources for 5 tokens fewer than it cost before. That leaves
# 125, which is what these two verdicts cost. The 2026-09-01 lowering to 23,000 said the room it
# freed must not be re-consumed by narrative; this is not narrative, and the next addition prunes
# again or argues again rather than inheriting the 25 of margin.
BUDGETS = {
    "CLAUDE.md": 50,
    "AGENTS.md": 2_850,
    # 23,150 -> 23,250 on 2026-09-10 (237): two decision entries land in this window — 237
    # superseding 220's `unsupported`, and 238 narrowing 221/AC5 — and a verdict is the structure
    # this log exists to hold. R7.6 ran first and paid most of it: 237 cut the T-SQL entry's retro
    # retelling to a pointer, and both new entries lost the mechanism and the AC list their task
    # files already hold (-81 for +137). The next addition prunes again or argues again.
    # 23,250 -> 23,350 on 2026-09-12 (258), argued rather than assumed. Two things this file
    # owns land together: the `schema_version` bump that ends `max_results` governing graph
    # content, and §12's row for a new nav reason — a reason with no row is a payload shape a
    # reader can only find in source. R7.6 ran first and paid most of it (~180 tokens): the §10
    # per-version enumeration became a task-pointer list, the aside correcting a mis-cited R7.4
    # went (a decision-log note, not a section one), and 251's §19 entry that restated its own
    # §12 row was cut. The next addition prunes again or argues again; this is not headroom.
    # 23,350 -> 23,550 on 2026-09-13 (265), argued rather than assumed. Default page ORDER is a
    # §19 decision and nothing else records it: a reader who does not know page 1 is tier-ranked
    # reads position as spelling. R7.6 ran first and paid ~110 of the 304 the entry arrived with —
    # the 074 re-measure paragraph folded into one clause, §12's cell stopped repeating §19's
    # tier order, and a superseded field-report walk-through went in 261. The next addition
    # prunes again or argues again; this is not headroom.
    # 23,550 -> 23,720 on 2026-09-13 (266), argued rather than assumed. 036/099 locked *offer,
    # never install* for editor settings; writing into the indexed repo's own AGENTS.md is a
    # different blast radius, and a reader who finds only the 036 entry concludes the opposite of
    # what ships. R7.6 ran first and paid ~100 of the 212 the entry arrived with: the mechanism,
    # the flag name and the five occasions live in 266's task file, not here. The next addition
    # prunes again or argues again; this is not headroom.
    # 23,720 -> 23,850 on 2026-09-13 (267), argued rather than assumed. 267 widens 257's
    # serve_behind rule and supersedes one clause of it, and a payload reason with no §19 line is
    # a shape a reader can only find in source. R7.6 ran first and paid ~125 of the 254 the entry
    # arrived with: it folded into 257's existing block instead of opening a second serve_behind
    # decision, so the restated 257 half is gone. The next addition prunes again or argues again.
    # 23,850 -> 24,040 on 2026-09-13 (268), argued rather than assumed. Five things land under
    # one ticket and three of them change a DEFAULT — the tool surface a preset may cut, the walk
    # detail level, and what a linked worktree does with main's DB — which is exactly what §19 is
    # for. R7.6 ran first and came back nearly empty: 071's worktree entry is not superseded (it
    # stays; 268 adds the refusal), and the mechanism, the glob list and the preset's six names
    # live in 268's task file and TOOLS.md. The next addition prunes again or argues again.
    # 24,040 -> 24,100 on 2026-09-15 (276-280), argued rather than assumed. §19 decisions land
    # across this field batch — 278 (Table/Column writers), 279 (unmodelled-resolution stamp), 280
    # (parse_failures floor), plus the 274/276 clauses folded into the serve_behind and unmodelled
    # `*->L` blocks — each a verdict a reader could otherwise only reconstruct from source. R7.6 ran
    # first and paid ~99 tokens: the field-name lists, the "Cost/Evidence" tails and restated detail
    # were cut to the verdict + task link (mechanics live in CONVENTION §6 and each task file). The
    # next addition prunes again or argues again; it does not inherit this raise as headroom.
    # 24,100 -> 24,120 on 2026-09-15 (281), argued rather than assumed. 281 changed a verdict this
    # log already carried — the WRITES caveat keys on which languages emit it, not on language
    # count — so the 278 block states the wrong rule until it is folded in, and a decision log that
    # is wrong is worse than one that is long. R7.6 ran first inside the same block: the superseded
    # "multi-lang caveat when only SQL emits" clause is replaced, not kept, and the mechanism stays
    # in 281's task file. The next addition prunes again or argues again.
    # 24,120 -> 24,150 on 2026-09-16 (285), argued rather than assumed. 285 shipped `supertypes`
    # on the read_symbol row, the sibling that 242 (`params`) and 248 (`columns`) already enumerate
    # there; leaving it off states the row is exhaustive when it is not. R7.6 ran first: the clause
    # is the terse verdict + task link (edge kinds, qname/unresolved and the `inheritance` stamp
    # stay in 285's task file), and no superseded line exists to reclaim. The next addition prunes
    # again or argues again; it does not inherit this raise as headroom.
    "PLAN.md": 24_150,
    # 2,150 -> 1,800 on 2026-09-08, LOWERED: 232-235 all close in this window and each removes
    # its row (R7.6), taking the file 1,737 -> 1,485. 2,150 is more than 25 % above 1,485, which
    # the anti-slack guard below calls slack; 1,800 keeps ~315 of headroom, about five open rows.
    # 1,800 -> 1,950 on 2026-09-11 (251-256), argued rather than assumed. The 2026-09-08 number was
    # sized for "about five open rows" and round 18's field batch files six in one day — open rows
    # are the one thing this table exists to hold, and a ceiling that forces a real open ticket to
    # go unlisted is measuring the wrong thing. R7.6 ran first and paid most of it across the two
    # commits: the `max_results` follow-up's field instance moved into 251, the round-3 grep note
    # left (it is the consumer repo's own doc, which AGENTS.md routes to the consumer as a PR), and
    # three clauses retelling a convention, a named test and two §19 decisions were cut. The next
    # addition prunes again or argues again; it does not inherit this raise as headroom.
    # 1,950 -> 1,850 on 2026-09-12: round 18 closed seven tickets (250, 252-257), so the open
    # table shrank and the old ceiling became slack rather than a bound.
    # 1,850 -> 2,000 on 2026-09-13 (259-269), argued rather than assumed. Eleven tickets file at
    # once off the feedback round, taking Pillar 1 from four open rows to thirteen and reopening
    # Pillar 2 with two. Open rows are the one thing this table exists to hold, and the 2026-09-12
    # number was sized for a table that had just emptied. R7.6 ran first and paid ~170: the two
    # follow-ups now carried by 265 and 268 left the Follow-ups list (the convention already
    # requires it), and the roll-out bullet's claim that the remaining work "is not a ticket here"
    # was superseded by 266 and cut to a pointer. The next addition prunes again or argues again;
    # this is not headroom.
    # 2,000 -> 1,900 on 2026-09-13, LOWERED: 261 and 265-268 all close in this window and each
    # removes its row (R7.6), taking the file to 1,569. 2,000 is more than 25 % above that, which
    # the anti-slack guard below calls slack; 1,900 keeps ~330, about eight open rows.
    # 1,900 -> 1,950 on 2026-09-14 (272-280), argued rather than assumed. Five field retros
    # (rounds 19-23) land nine tickets at once — more than the ~330 was sized for by one row. A row
    # here is what a reader chooses the next ticket from, and the ninth (280) is the one finding
    # with a recorded instance of the trap already costing a session, so dropping it to keep the
    # ceiling would trade the evidence for the number. R7.6 ran first and came back empty: no open
    # row is superseded by any of the nine, no `done` row is left to remove, and the round-3
    # `~650x` note is this repo's only record of that claim. The next addition prunes or argues.
    # 1,950 -> 1,800 on 2026-09-20 (308): 307 and 308 closed and their rows left the table, so the
    # old ceiling stopped biting and `test_the_budgets_are_not_slack` said so. Lowered to the
    # measured size plus headroom, which is what that guard asks for.
    "BACKLOG.md": 1_800,
    "ENGINEERING_RULES.md": 5_700,
    "AGENT_BRIEF.md": 2_250,
    # 6,700 -> 6,800 on 2026-09-09 (236): the `ForeignKey` node kind joins the vocabulary of record
    # (contract v10). The §3 bullet is the tightest statement of its qname and `extra` fields; there
    # is no superseded line to prune, so the ceiling rises one step rather than displacing content.
    # 6,800 -> 6,850 on 2026-09-12 (251), argued rather than assumed. §6's table is the
    # cross-tool payload contract, so it grows exactly when the payload surface grows: 251
    # adds `tier_filter`, `tier_census` and `caveat_limits`, all cross-tool honesty fields an
    # undocumented reader would have to rediscover from source. Paid for first — the 170
    # incident retold in two rows and PLAN's §19 entry that restated §12's own row were cut,
    # ~100 tokens. The next addition prunes again or argues again; this is not headroom.
    # 6,850 -> 6,960 on 2026-09-13 (259 + 262), argued rather than assumed. Same reason as 251's
    # raise above and no other: §6 is the cross-tool payload contract, and 262 puts three new
    # fields on two nav tools — `production_count`, `test_count`, `test_role_source`. A payload
    # field with no row here is a shape a reader can only find in source. 259 lands in the same
    # window and costs the §1 env-var list two knob names where it had one. R7.6 ran first and
    # came back almost empty: no row here is superseded by either ticket, and the narrative each
    # could shed was already taken by the 251 pass. What it did pay: 262's row was rewritten
    # twice, ~55 tokens shorter than first drafted, and 259's alias note was folded back into the
    # env-var bullet it had been wedged inside — it closed the paren mid-list, so the rest of the
    # list read as prose. 16 of margin; the next addition prunes or argues again.
    # 6,960 -> 7,050 on 2026-09-13 (261/265/267/268), argued rather than assumed. §6 is the
    # payload contract, so a shipped field with no row here is a shape a reader can only find in
    # source — and four tickets shipped five: the two root-nomination lists, the stale-process
    # action pair, and the census rule that keeps an empty filtered page honest. R7.6 ran first and
    # paid 56: §6's `try_instead` bullet retold the 186/188 cases that design/payload.md holds in
    # full, so it points there instead. The next addition prunes again or argues again.
    # 7,050 -> 7,150 on 2026-09-20, argued rather than assumed. §6 is the payload contract, and
    # three shipped field groups had no row: the coverage pair 159/160/173 fires on partial
    # answers as well as empty ones, 299 puts `unindexed_same_basename` on a NON-empty page,
    # and 286 extends the mirror fields from search to read. A field a reader can only find in
    # source is the shape this table exists to stop. R7.6 ran first and paid 93 of the 147 the
    # rows arrived with: they were rewritten ~76 tokens shorter than first drafted, and the
    # `server_*` row shed the per-field narrative design/payload.md holds in full, keeping the
    # rule and pointing there. 43 of margin; the next addition prunes again or argues again.
    "CONVENTION.md": 7_150,
}


def _path(name: str) -> Path:
    """A budget key names a file at one of the two roots the chain uses: the repo, or `docs/`."""
    return REPO / name if (REPO / name).is_file() else DOCS / name


def test_every_file_the_chain_binds_has_a_budget() -> None:
    """The bounded set is derived from the chain, never listed twice (R6.7).

    Without this, a new entry on `AGENTS.md`'s *read before non-trivial work* list is charged to
    every session and bounded by nothing — which is how the two biggest files got there.
    """
    bound = {_path(name).resolve() for name in BUDGETS}
    unbounded = [p.relative_to(REPO).as_posix() for p in chain() if p.resolve() not in bound]
    assert not unbounded, (
        f"the chain binds files with no budget: {unbounded}. Add a ceiling, or take the file off "
        "AGENTS.md's read-before-non-trivial-work list."
    )


@pytest.mark.parametrize("name", sorted(BUDGETS))
def test_a_standing_doc_stays_under_its_budget(name: str) -> None:
    text = _path(name).read_text(encoding="utf-8")
    spent = estimate_tokens(text)
    assert spent <= BUDGETS[name], (
        f"docs/{name} is {spent:,} tokens against a budget of {BUDGETS[name]:,}. "
        "Prune what a task file, LESSONS.md or a benchmark already holds (R7.6), or raise the "
        "budget in this test and say why in the PR."
    )


def test_the_budgets_are_not_slack() -> None:
    """Guards the guard: a budget far above the file it bounds would never fail.

    A ceiling only works while it is close enough to bite. If a prune lands and nobody lowers the
    number, this fails and says so — the budget must stay within 25 % of what the doc actually
    spends.
    """
    for name, budget in BUDGETS.items():
        spent = estimate_tokens(_path(name).read_text(encoding="utf-8"))
        assert budget <= max(100, spent * 1.25), (
            f"docs/{name} spends {spent:,} tokens against a budget of {budget:,} — that is slack, "
            "not a ceiling. Lower the budget to the measured size plus headroom."
        )
