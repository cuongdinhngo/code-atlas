# Lessons — code-atlas

The **claim corpus** the learning loop reads. One atomic claim per record
(`type` · `handle` · `status` · `seen` · `evidence` · `destination`); recall greps `handle:` and
**recurrence is the number of distinct ticket keys in `seen:`**, unioned across every claim sharing a
handle. Newest first.

**Reset for phase 2 (2026-09-27).** Phase 1's corpus — its live claims, its class index and its
retired index — was archived with phase 1's task files. The rules it produced stay binding in
[`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) and [`AGENT_BRIEF.md`](AGENT_BRIEF.md); a claim id
they cite (`127-C1`, `PROM-C3`) names a phase-1 record and resolves in that archive, not here.
Recurrence restarts at zero: a new sighting of a class a rule already carries cites the rule, and
becomes a claim here only when it shows the rule's wording missed a case.

**No per-ticket narrative.** A record states the claim and its evidence; what the ticket did lives
in its task file and its [`TOKEN_LEDGER.md`](TOKEN_LEDGER.md) row. This is R7.6 applied to this file.

**One claim record per handle.** A second sighting of a handle bumps that record's `seen:`; it never
opens a sibling record, or a recurrence-2 class reads as two recurrence-1 notes.

**Retired claims are an index, not records.** A claim whose class a rule now carries moves to the
Retired table — id, handle, rule — so the rule book's citation still resolves. `RECALL:` skips it.

A record, for shape:

```
### NNN-C1 — the claim, stated as what is true

- type: 2 (code | process) · handle: `a-kebab-case-class-slug`
- status: proposed · seen: NNN
- evidence: what happened, where (path:line, commit, test), and why it generalises past this ticket.
- destination: where it goes on promotion (a rule, a brief entry) — or "first sighting".
```

## Class index — read this before proposing a new rule

Every type-2 handle at recurrence ≥ 2, and where it landed. *None yet in phase 2.*

| handle | rec | tickets | where it landed |
|---|---|---|---|

## Live claims

### 343-C1 — Claude Code keeps only a 2,048-character prefix of an MCP server's `instructions`

- type: 5 (environment) · area: `routing surface / server instructions` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 343
- evidence: a padded probe server (`%08d|` cells) via `claude -p --strict-mcp-config` returned
  `…00002043|00002… [truncated]` — cell 2,043 plus 5 chars. The cut counts characters, not bytes.
  `instructions.CLIENT_CAP` carries the figure; re-measure on a new Claude Code major.
- destination: first sighting.

### 343-C2 — `ruff format` on a file you edit rewrites lines you did not

- type: 2 (code) · handle: `formatter-rewrites-untouched-lines`
- status: proposed · seen: 343
- evidence: formatting four edited files reflowed four untouched spots (two `main.py` calls, the
  `which_tool` string, a test lambda); the challenger caught one I had missed. The gate runs
  `ruff check` only, so the drift is silent. Format, then revert every hunk the change does not own.
- destination: first sighting.

## Retired — the rule carries the class now

`RECALL:` skips these. The rule named is the one that cites the id.

| claim | handle | rule |
|---|---|---|
