# Skill-gap candidates — signals for the mango maintainer

Type-3 claims: a mango phase that could have run a check and did not. **Nothing here edits a mango
skill.** This repo records the signal; mango changes only through a normal version release.

**Reset for phase 2 (2026-09-27).** Phase 1's signals were archived with its task files; any still
open is re-filed here the next time it fires, with the new sighting.

Each entry names the phase, what it did, what it could have done instead, and the incident:

```markdown
## SG-<n> — <phase> <what it misses, in one line>

- **phase:** `/mango:<skill>`, step <n>
- **observed:** <date>, task <NNN>
- **status:** open

**What it does.** … **What it misses.** … **The incident.** …
**A doable check the phase could name.** … **Why it matters beyond one repo.** …
```

---

## SG-1 — autorun's TREE-COMPARISON validator reads a branch name as a content grep

- **phase:** `/mango:autorun`, Step 0 (`run_contract.py bind`, `check_floor`)
- **observed:** 2026-09-29, task 345
- **status:** open

**What it does.** `check_floor` refuses a TREE-COMPARISON check matching `\bgrep\b`. **What it
misses.** The branch name sits inside that check. `feat/345-grep-symbol-nudge`, the slug
`branch_strategy` derives from the ticket, contains `grep`, so the bind refused a pure `git diff
--quiet`. **The incident.** The branch was renamed `feat/345-symbol-search-nudge` to bind. **A doable
check the phase could name.** Match `grep` as a command word (after a pipe, or at the start of a
command), not anywhere in the string. **Why it matters beyond one repo.** Any ticket about grep
tooling lands on a refused contract.

## SG-2 — the finalise evidence check refuses a baseline for being run on the baseline tree

- **phase:** `check_lines.py check --phase finalise --tree`, the EVIDENCE axis
- **observed:** 2026-09-29, task 344
- **status:** open

**What it does.** It refuses every `$`-prompted block stamped with a tree other than HEAD.
**What it misses.** Analysis's `BASELINE` is pre-change evidence by definition, so its `Ran at`
can never be HEAD. **The incident.** The 344 baseline block (`Ran at e58d8c13`) was refused, and it
was rewritten without the `$` prompt, as 343's already was, so the check stopped reading it.
**A doable check the phase could name.** Exempt the block under `### BASELINE`, or require its sha to
equal the branch point. **Why it matters beyond one repo.** Every honest baseline trips it, which
invites exactly the formatting workaround the evidence axis exists to prevent.
