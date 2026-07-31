# Lessons — code-atlas

Durable lessons discovered while shipping tasks: constraints found, wrong assumptions, process gaps.
One entry per lesson; newest first.

## 024 — A rule enforced only by a lifecycle gate is unenforced for work that skips the lifecycle
`CLAUDE.md` says no PR opens without the task's token spend recorded in **both** the working-doc cost
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
`CLAUDE.md` + `docs/BACKLOG.md`), the ticket-blind challenger and the reviewer both read it as
untraceable scope creep — it maps to no ticket requirement. **Fix:** add it to the task's
Scope/Deliverables + a matrix row (task 001 → R6 + change-list item 8) with a one-line rationale, so
every hunk still traces to a requirement. Splitting it into its own docs ticket is the alternative;
either way, never let a change ride the branch untraceable to a row.
