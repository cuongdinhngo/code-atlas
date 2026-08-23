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
BUDGETS = {
    "CLAUDE.md": 50,
    "AGENTS.md": 2_800,
    "PLAN.md": 24_000,
    "BACKLOG.md": 9_500,
    "ENGINEERING_RULES.md": 4_200,
    "AGENT_BRIEF.md": 1_700,
    "CONVENTION.md": 6_300,
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
