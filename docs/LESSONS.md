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

### 345-C1 — a PostToolUse hook's plain stdout never reaches the model; `additionalContext` does

- type: 5 (environment) · area: `claude-code hooks / output channel` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 345
- evidence: a Read hook printing a marker as plain text — the model, asked to quote it, said `NONE`;
  the same marker as `hookSpecificOutput.additionalContext` JSON came back verbatim. `code-atlas-nudge`
  emits JSON and was quoted live; `code-atlas-signal` prints plain text (ticket 346).
- destination: first sighting.

### 344-C1 — Claude Code runs a hook's `if` only when it is ONE permission rule

- type: 5 (environment) · area: `claude-code hooks / if filter` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 344
- evidence: `Read(*.py)` ran on `app.py` and skipped `notes.txt`; `Read(*.php)|Read(*.py)`,
  `Read(*.{php,py,ts})` and `Read(*.php) Read(*.py)` all logged `Skipping hook due to if condition`
  on `app.py`. The shipped snippet's `|`-joined filters had never fired; `gen_skill._per_suffix`
  now emits one entry per rule.
- destination: first sighting.

### 344-C2 — a plugin's `userConfig` reaches its MCP server, never its hooks

- type: 5 (environment) · area: `claude-code plugins / userConfig` · verified-at: 2026-09-29, Claude Code 2.1.284
- status: proposed · seen: 344
- evidence: `${user_config.python}` expanded in `mcpServers.env`; a hook saw no
  `CLAUDE_PLUGIN_OPTION_PYTHON`, and an exec-form hook with the option in `args` did not run. Both
  the server and the hooks get `CLAUDE_PROJECT_DIR` and run with the project as cwd — the docs
  research said the server runs from the plugin root.
- destination: first sighting.

### 344-C3 — a directory-marketplace install reads the working tree, so it hides an uncommitted file

- type: 2 (process) · handle: `verify-the-shipped-artifact-not-the-working-tree`
- status: proposed · seen: 344
- evidence: `.gitignore`'s `.mcp.json` dropped the plugin's server file; the live install from the
  checkout connected anyway. Only a clone of the branch shows what a user gets. The challenger found it
  independently. Guard: `tests/test_claude_code_plugin.py::test_every_generated_file_is_committable`.
- destination: first sighting.

*None yet.*

## Retired — the rule carries the class now

`RECALL:` skips these. The rule named is the one that cites the id.

| claim | handle | rule |
|---|---|---|
