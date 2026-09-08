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
    "PLAN.md": 23_150,
    # 2,150 -> 1,800 on 2026-09-08, LOWERED: 232-235 all close in this window and each removes
    # its row (R7.6), taking the file 1,737 -> 1,485. 2,150 is more than 25 % above 1,485, which
    # the anti-slack guard below calls slack; 1,800 keeps ~315 of headroom, about five open rows.
    "BACKLOG.md": 1_800,
    "ENGINEERING_RULES.md": 5_700,
    "AGENT_BRIEF.md": 2_250,
    "CONVENTION.md": 6_700,
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
