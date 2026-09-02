"""Tier 1 — what an agent reads before it knows what binds it — has a total, not just per-file, cap.

`tests/test_doc_size_budget.py` bounds each standing doc. That cannot hold the number the caller
actually pays: six files each comfortably under their own ceiling summed to **66,500 tokens** when
133 was written, against a Pillar-1 promise of *"a token cost low enough that an agent can afford to
ask"*. So the sum is the thing to bound, and the split that buys it has to be load-bearing rather
than decorative — hence the second test below.

Both numbers are derived from `AGENTS.md`'s own two lists via `scripts/agent_chain_cost.py`, never
listed here (R6.7), and counted with `estimate_tokens`, the one definition site.
"""

from pathlib import Path

from code_atlas.tokens import estimate_tokens
from scripts.agent_chain_cost import chain, consult_only

REPO = Path(__file__).resolve().parent.parent

# 133's measurable goal. 49,572 before this ticket (134 had already pruned 66,500 to it); 22,229
# after.
# 25,000 -> 25,150 on 2026-08-28 (task 175): the whole 150 is CONVENTION's argued raise — see
# tests/test_doc_size_budget.py. No other tier-1 file grew, and 175 pruned before asking.
# 25,150 -> 25,200 on 2026-08-30 (tickets 192/194/195): three BACKLOG rows landed at once, which is
# more than one ticket's headroom. Pruned first, per R7.6 and 175's precedent: a follow-up pointing
# at a list that no longer exists was removed, and 043's two duplicate-declaration follow-ups were
# consolidated into one. Those recovered 84 of the 110; the residue is the three rows themselves.
# 25,200 -> 25,300 on 2026-09-01 (tickets 200/201/202): three open BACKLOG rows again, and this
# time the prior pass had already taken the restatement — the argument is in
# tests/test_doc_size_budget.py. An open row costs more than a done one by design, and it repays
# the raise when it closes and is re-titled by its slug.
# 25,300 -> 25,700 on 2026-09-02 (tickets 205-212): eight open BACKLOG rows, and the whole 400 is
# those rows — no other tier-1 file changed. The R7.6 argument is in tests/test_doc_size_budget.py.
# Measured at 25,658, re-confirmed unchanged on 48ee6b0 after PR #250 (204) merged — that ticket's
# own row had landed inside the 54 tokens free at a502e8f, so the merge moved no tier-1 file and the
# 400 here is this session's eight rows and nothing else.
# 25,700 -> 25,800 on 2026-09-02, second edit the same day: task 203's open row lands on top of the
# eight above and measures 25,711. Two sessions raised this ceiling within the hour and this is the
# later one, re-measured against the merged tree rather than either branch's own figure. R7.6 was
# applied first and found nothing: no id is listed in two tables, and the 2026-08-30 pass already
# slug-titled every `done` row, so there is no prose title left to reclaim. The 100 buys one row.
TIER1_BUDGET = 25_800


def _tokens(paths: list[Path]) -> int:
    return sum(estimate_tokens(path.read_text(encoding="utf-8")) for path in paths)


def test_tier_one_stays_under_its_total_budget() -> None:
    spent = _tokens(chain())
    assert spent <= TIER1_BUDGET, (
        f"tier 1 is {spent:,} tokens against a budget of {TIER1_BUDGET:,}. Every session pays it. "
        "Move what is reference to AGENTS.md's *consult when you need it* list, prune (R7.6), or "
        "raise the budget here and argue for it in the PR."
    )


def test_the_two_tiers_are_a_partition() -> None:
    """A file on both lists would be counted as demoted while still being read every session."""
    binding, consult = chain(), consult_only()
    assert consult, "AGENTS.md names no consult-only document — the tier split is not stated"
    overlap = {p.resolve() for p in binding} & {p.resolve() for p in consult}
    assert not overlap, f"listed as both binding and consult-only: {sorted(overlap)}"


def test_returning_a_consult_only_doc_to_the_binding_list_breaches() -> None:
    """The split has teeth: the budget cannot be met with the demoted files back in tier 1.

    Without this the first test passes on a tier 1 that was never actually reduced — someone could
    move a 200-token file off the list and call the boundary drawn. Recorded red run (R6.5): with
    `docs/PLAN.md` put back on AGENTS.md's binding list, the test above reads tier 1 at **45,249**
    tokens and fails. Not every consult-only file is individually large enough to breach — the
    smallest is 2,291 tokens — so the claim asserted here is about the largest.
    """
    spent = _tokens(chain())
    largest = max(consult_only(), key=lambda p: estimate_tokens(p.read_text(encoding="utf-8")))
    breach = spent + estimate_tokens(largest.read_text(encoding="utf-8"))
    assert breach > TIER1_BUDGET, (
        f"returning {largest.relative_to(REPO).as_posix()} to the binding list costs {breach:,} "
        f"tokens, still under {TIER1_BUDGET:,} — this ticket's boundary is not what bought the "
        "budget, and the consult-only list is decoration."
    )
