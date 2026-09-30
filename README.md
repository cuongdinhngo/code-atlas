# code-atlas

**An evidence layer for AI coding agents.** A local-first MCP server that indexes your codebase into
a symbol graph, then answers *resolved relationship* questions — who calls this, what implements
that, what breaks if I change this file — as rows, not as files to read.

**PHP · TypeScript/JavaScript · Python · T-SQL. 24 tools.** Deterministic, offline, no LLM in the
core. Every edge says how it was resolved, and the adapters differ in how deep they resolve —
[measured per language](#languages).

> ### **~69× fewer tokens** than grep-and-read to reach a resolved answer
> Measured on two pinned public PHP repos (symfony/demo · brick/math): 8/8 answers correct, recall
> **1.0**, precision **1.0**, zero confidently-wrong answers. Relation questions range from **18×** on a small tree to
> **117×** on a wide one; the one scored onboarding lookup is **4.5×**.
> The baseline is a fixed recipe — grep the name, then `Read` every matching file whole — not a
> live model, so the comparison is deterministic.
> [Reproduce it](docs/runbooks/tokens-to-answer.md#sample-tier-pinned-public-repos--the-real-value-claim-task-042)
> · needs PHP and a one-time clone of the pinned repos.

## The 30-second version

Ask *"who calls `member()`?"* in this repo's own TypeScript adapter.

**`grep` — 28 hits, and it cannot tell you which are calls:**

```console
$ grep -rn 'member' adapters/typescript/src/ | wc -l
28

$ grep -rn 'member' adapters/typescript/src/ | head -3
adapters/typescript/src/qname.js:4:// §4.4 Q1). The root container is the repo-relative posix
adapters/typescript/src/qname.js:12:function member(container, name) {
adapters/typescript/src/qname.js:16:module.exports = { SEP, toPosix, member };
```

A comment, the definition itself, and an export line — not one of the three is a call. The agent
has to open and read every one of the 28 to sort them out. **That reading is the cost**, and it is
paid in context.

**code-atlas — the 9 functions that call it, each resolved, with the tier it was resolved at:**

```jsonc
// MCP tool call, not a shell command
find_callers(qname: "src/qname.js::member")

reason: "ok"   total_count: 9   truncated: false   depth: 1

RESOLVED  parseFile::collect               src/parse.js:278
RESOLVED  parseFile::emitBodyEdges         src/parse.js:508
RESOLVED  parseFile::emitDefaultAlias      src/parse.js:428
RESOLVED  parseFile::emitJsDocDeclarations src/parse.js:439
RESOLVED  parseFile::emitReExport          src/parse.js:419
RESOLVED  parseFile::resolve               src/parse.js:301
…
```

No comment, no definition, no export line — and `total_count: 9` is the true size of the answer
(distinct callers; the graph holds all 13 call sites behind them), not the length of the page you
were handed. Building that index took **0.54 s**.

> Real output, reproduced on 2026-09-27 by pointing code-atlas at its own `adapters/typescript/`
> (`code-atlas-build` there, 6 files).

## Why code-atlas

`grep` returns every line containing the string. An LSP answers precisely but one editor buffer at a
time. Neither gives an agent a *countable* answer it can act on, and both make it read files to find
out. code-atlas parses each language with its **best** parser into a **SQLite symbol graph**,
resolves cross-file edges once at index time, and serves callers, implementations, blast radius,
reachability and the path between two symbols as rows.

**Use it if:** you have a large codebase (>10k files) you did not write · an AI agent is doing the
reading, not a human in an IDE · you need the answer to be checkable, not plausible.

**It is not** a faster `grep`, an editor, or a language server — an LSP stays for precise in-buffer
nav, and code-atlas never mutates code.

**Agents do not reach for it on their own when `grep` can serve the question** — on a 23k-file tree,
five control-flow questions drew no index calls with every tool available
([074](docs/benchmarks/074_mechanism-question.md)). It pays off on relationship questions, and an
agent is far likelier to use it once told when to: install the [agent brief](#agent-brief-optional).

## Quick start

**Platform: runs on Linux, macOS, and native Windows.** For heavy indexing on Windows, WSL2 on the
Linux-native filesystem is recommended: a repo under `/mnt/*` crosses the 9p boundary (~100× slower —
measured), and
Defender's real-time scan adds a large cold-read cost — exclude the repo path or use a Dev Drive. The
startup preflight warns about the `/mnt/*` case; the Defender cost it cannot see. The **test and dev loop is POSIX-only** — run it under WSL2 or Docker.

You need **Python ≥ 3.12** with SQLite ≥ 3.25 and FTS5 (a standard CPython build has both), plus the runtime of whichever language you want to index: a **PHP CLI ≥
8.1** with **[Composer](https://getcomposer.org/)** for PHP, **Node.js ≥ 18** for TypeScript/JavaScript
and T-SQL. The Python adapter is stdlib-only and runs on the same interpreter as the core.

```bash
git clone https://github.com/cuongdinhngo/code-atlas.git
cd code-atlas
python3 scripts/setup.py /abs/path/to/your-project
```

That installs the core, builds the PHP adapter, and writes `<your-project>/.mcp.json` with the
correct interpreter, adapter path and working directory filled in — the three things that are easy
to get wrong by hand. Run it with no path to print the snippet instead of writing it.

To run the server without a checkout: `uvx --from git+https://github.com/cuongdinhngo/code-atlas.git
code-atlas`, or `pipx run --spec git+https://github.com/cuongdinhngo/code-atlas.git code-atlas` —
the adapters still need their own runtimes on `PATH`, and a checkout to launch them from.

**In Claude Code, install it as a plugin** — the server, the hooks and the skill in one step, for every
project. The plugin launches the console scripts by name, so put them on `PATH` with a tool install:

```bash
uv tool install git+https://github.com/cuongdinhngo/code-atlas.git   # or: pipx install git+…
claude plugin marketplace add cuongdinhngo/code-atlas
claude plugin install code-atlas@code-atlas
```

Its hooks stay silent in a repo with no `.code-atlas/`. Adapter `CA_<LANG>_CMD` variables stay per
machine, as below. Already wired `.mcp.json` or the hook snippet by hand? Remove those, or each event
fires twice ([`contrib/claude-code/`](contrib/claude-code/)).

For TypeScript/JavaScript, T-SQL or Python, add that adapter — the core resolves any `CA_<LANG>_CMD`
generically from the variable name, so each is one env var, not a code change:

```bash
npm ci --prefix adapters/typescript
export CA_TYPESCRIPT_CMD="node /abs/path/to/code-atlas/adapters/typescript/index.js --server"

npm ci --prefix adapters/sql          # dev-only deps; the scanner itself has none
export CA_SQL_CMD="node /abs/path/to/code-atlas/adapters/sql/index.js --server"

# Python adapter — stdlib only; use the same interpreter that runs the core
export CA_PYTHON_CMD="python3 /abs/path/to/code-atlas/adapters/python/index.py --server"
```

Then **reload your MCP client** (in Claude Code: restart, or re-approve the project's `.mcp.json`)
and call **`get_index_status`** first — it is the cheap (~100-token) entry point that says whether
there is an index, how stale it is, and what to call next. Then `build_or_update_index`, then query.

<details>
<summary>Wiring it by hand, or running the server from a container</summary>

**By hand:** `pip install -e .`, then `composer install --working-dir=adapters/php`, then point an
`.mcp.json` at your repo — `command` = `code-atlas` (or `python3 -m code_atlas.main`), `cwd` = the
repo to index, `env.CA_PHP_CMD` = `php /abs/path/to/code-atlas/adapters/php/index.php --server`. The
adapter lives in this checkout, so `CA_PHP_CMD` must be an **absolute** path. Details in
[`adapters/php/README.md`](adapters/php/README.md).

**In a container** — no host Python or PHP needed; the image bundles the pinned adapters:

```bash
docker build -f docker/Dockerfile.runtime -t code-atlas-server .
```

```jsonc
// .mcp.json — the server indexes the mounted repo and writes .code-atlas/graph.db into it
{"mcpServers": {"code-atlas": {"command": "docker",
  "args": ["run", "-i", "--rm", "-v", "/abs/path/to/your-project:/workspace", "code-atlas-server"]}}}
```

MCP speaks over stdio, so `-i` is required; the server indexes `/workspace`, so mount the repo
there. Add `"--user", "1000:1000"` to keep `.code-atlas/` writes owned by you. See [`docker/`](docker/).
</details>

<details>
<summary>On native Windows</summary>

The runtime is fully supported; setup differs only in path/quoting and the checks the startup preflight
surfaces at build time — long paths, `core.autocrlf`, and an adapter missing from `PATH`.

- **Adapter command — prefer the list form in `.code-atlas.toml`**, so a Windows path's backslashes are
  never eaten by POSIX quoting (the table needs `$env:CA_TRUST_PROJECT_FILE = '1'` — see the config table):

  ```toml
  [adapter_cmd]
  typescript = ["node", "C:\\code-atlas\\adapters\\typescript\\index.js", "--server"]
  python     = ["python", "C:\\code-atlas\\adapters\\python\\index.py", "--server"]
  ```

  Or set the env var in PowerShell: `$env:CA_TYPESCRIPT_CMD = 'node C:\code-atlas\adapters\typescript\index.js --server'`.
- **Enable long paths** so deep `vendor/` / `node_modules/` trees don't hit the 260-char limit (admin,
  then reboot): `Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' LongPathsEnabled 1`.
- **Set `core.autocrlf=false`** for the indexed repo — otherwise a `graph.db` built elsewhere sees every
  file as changed and reparses the world.
- **Speed:** exclude the repo from Defender real-time scan (admin: `Add-MpPreference -ExclusionPath 'C:\path\to\repo'`)
  or put it on a **Dev Drive** — the AV scan dominates cold reads. For very large repos, WSL2 on the
  Linux-native filesystem is fastest.
- **PHP repos** need `php` + `composer` on `PATH`, or the PHP files are skipped (the preflight says so) —
  use WSL2 or the container if you can't install them natively.

`code-atlas-build` warns for each of these it can detect — long paths, `core.autocrlf`, a missing
adapter runtime, a `/mnt/*` repo on WSL. **Defender and Dev Drive it cannot detect**; those two are on
you. A clean host prints nothing.
</details>

Onboarding a **large legacy repo** — where the first build takes minutes and what you exclude
decides whether the database is 1 GB or 2 GB — is covered step by step in
[`docs/runbooks/onboarding-a-repo.md`](docs/runbooks/onboarding-a-repo.md).

### Upgrading

Every release is an entry in [`CHANGELOG.md`](CHANGELOG.md). An entry can flag two extra steps:
**full rebuild required** and **adapter checkout must be updated**. Upgrade by the route you
installed with:

| Installed with | Upgrade |
|---|---|
| `uv tool install git+…` / `pipx install git+…` | `uv tool upgrade code-atlas` / `pipx upgrade code-atlas` |
| a checkout and `scripts/setup.py` | `git pull`, then re-run `python3 scripts/setup.py /abs/path/to/your-project` |
| the Claude Code plugin | `claude plugin marketplace update code-atlas`, then `claude plugin update code-atlas@code-atlas`, then restart. Also upgrade the tool install that puts the scripts on `PATH` |

**The plugin updates only when its `version` moves.** Measured on Claude Code 2.1.284:
- A content change under an unchanged version answers `already at the latest version`.
- `marketplace update` alone leaves the installed version where it was.
- `plugin update` moves it.

Whether a session start auto-updates a third-party marketplace was not measured, so run the two
commands yourself. If the plugin and the tool install disagree, the `SessionStart` hook says so,
names both versions, and names the command for the side that lags.

**After an upgrade**, check two things:
- **The index.** If the changelog flags a full rebuild, run `code-atlas-build --full`. Until then
  `get_index_status` and the state line lead with `rebuild required`.
- **The adapters.** If `CA_<LANG>_CMD` points into a checkout, pull that checkout and reinstall its
  dependencies when the entry says so. An adapter on an older contract fails the handshake.

### Agent brief (optional)

After the first index, offer the **agent brief** into the repo's `AGENTS.md` — six occasions that
name a tool, plus how to spend the calls, how to read an answer's honesty fields, what the index
**cannot** answer, and two traps. Not the full tool roster (generated from `which_tool`; do not
hand-edit):

```bash
python3 scripts/setup.py /abs/path/to/your-project --write-agent-brief
# or: python3 scripts/gen_skill.py --write-agent-brief /abs/path/to/your-project
```

**Load requirement per host:** Cursor reads `AGENTS.md` directly. Claude Code reads only
`CLAUDE.md` / `CLAUDE.local.md` — if `CLAUDE.md` lacks `@AGENTS.md`, the writer **prints** that
one line to add and never edits `CLAUDE.md`.

## Architecture

<img src="docs/assets/architecture.svg" alt="MCP client talks stdio to the language-agnostic core, which drives per-language adapters over a versioned JSONL contract, stores a symbol graph in SQLite, and feeds a deterministic onboarding layer with an opt-in LLM package behind three seams." width="100%">

The core is language-agnostic — **no per-language branches, CI-gated**. Adapters parse files and
emit a common `{nodes, edges}` vocabulary; the core stores them, resolves cross-file edges, and
exposes the MCP tools. Everything runs offline against local SQLite, with incremental updates via
`git diff`.

### Languages

| Language | Parser | Status |
|---|---|---|
| PHP (8.5 grammar, 8.1+ runtime) | nikic/php-parser | **Available** — see [`adapters/php/`](adapters/php/) |
| TypeScript / JavaScript (Node ≥ 18) | TypeScript compiler API | **Available** — see [`adapters/typescript/`](adapters/typescript/) |
| T-SQL (Node ≥ 18) | purpose-built scanner, no production dependencies | **Available** — see [`adapters/sql/`](adapters/sql/) |
| Python (≥ 3.12 grammar) | stdlib `ast` | **Available** — see [`adapters/python/`](adapters/python/) |
| C# / .NET | Roslyn | On the roadmap |

**Resolution depth differs by adapter.** A `CALLS` edge the adapter could not pin to one
definition is stamped `HEURISTIC` rather than guessed, and the share of those is the depth measure
([`scripts/edge_health_report.py`](scripts/edge_health_report.py)); PHP is the depth standard:

| Adapter | `HEURISTIC` share of `CALLS` | Pinned sample | Report |
|---|---|---|---|
| PHP | **1–4 %** | symfony/demo · brick/math · laravel | [137](docs/benchmarks/137_type-table.md) |
| TypeScript/JavaScript | 54.1% | `ky` | [153](docs/benchmarks/153_227_heuristic-share-ts-python.md) |
| Python | 82.2% | `flask` | [227](docs/benchmarks/153_227_heuristic-share-ts-python.md) |
| T-SQL | not measured this way — floors and layer shape instead | SQL samples | [233](docs/benchmarks/233_sql-cross-repo.md) |

Adding a language touches **no core code** — an adapter announces its own name, the file suffixes it
owns and its capabilities on one handshake line, and the core routes files from that alone.

## What you can ask it

| Question | Tool |
|---|---|
| Who calls this? What implements it? Where is it referenced? | `find_callers` · `find_implementations` · `find_references` |
| What breaks if I change these files? | `impact`, and `impact_modules` for the same radius rolled up to business modules |
| What is dead code here? | `find_orphans` · `reachable_from` |
| How does A reach B? | `explain_path` |
| Show me this symbol, without the rest of the file | `read_symbol` · `file_outline` |
| I did not write this repo — where do I start reading? | `architecture_overview` · `guided_tour` · `generate_onboarding` |
| Are any of these ten names already taken? | `search_symbol` with a list of `queries` — one call, not ten |
| Did this change break an architectural rule? | `check_architecture_rules` · `diff_architecture` |
| What happens when a user does X — entry to data? | `trace_capability`, one entry, file or module per call |
| Draw me this type and its ancestry | `class_diagram` |
| Which writers of this table omit a defaulted column? | `check_column_defaults` (T-SQL) |
| Is something *missing* here — an unchecked call site, an untested symbol? | **none of them** — use `grep`, and see [what it cannot answer](docs/TOOLS.md#what-it-cannot-answer--reach-for-grep-instead) |

**All 24 tools, what each returns, and which take a list of subjects: [`docs/TOOLS.md`](docs/TOOLS.md).**

### Three properties worth knowing before you install

**Every answer says what it is not telling you.** `total_count` (the true size, not the page),
`truncated`, `limit_capped_to`, and `reason` on every empty result — `no_such_symbol`,
`name_not_qualified`, `not_indexed`, `relationship_not_modelled`, `capability_not_configured`. **An
empty result is never an unexplained zero**, and where a better route exists the payload names a
real, callable tool in `try_instead`. Where a language loads code by a name the file never spells —
PHP autoload, a non-literal `import()`/`require()`, Python's `importlib`, T-SQL dynamic `EXEC` —
the adapter stamps the file, and `find_orphans` answers `resolution_unmodelled` instead of calling
unmeasured silence dead code. This is what makes an agent's answer auditable instead of merely
confident.

**Every edge carries a confidence tier** — `RESOLVED`, `HEURISTIC` or `DYNAMIC`. A guess is never
linked as a fact, and an answer whose candidates are all dynamic says so with `authoritative: false`.
Inbound answers are **ordered by that tier before the page is cut**, so page 1 leads with what was
resolved rather than with whatever sorts first alphabetically.

**An answer can be signed.** Pass `sign: true` to five tools and the payload gains a one-line
`claim` you can paste into a PR body — a claim a text search cannot make, in a form a reviewer can
re-run. Off by default, +51 tokens when on.

Full detail: [`docs/design/payload.md`](docs/design/payload.md) ·
[`docs/design/impact-and-claims.md`](docs/design/impact-and-claims.md).

## Measured, not asserted

Every number here is reproducible from a runbook in this repo.

| What | Result | Where |
|---|---|---|
| Tokens to reach a resolved answer, vs grep-and-read | **~69× cheaper** on pinned public PHP repos (symfony/demo · brick/math) — 8/8 correct, recall 1.0, precision 1.0; 18×–117× per relation question, 4.5× on an onboarding lookup. Re-measured 2026-09-27: 70.2× | [`tokens-to-answer.md`](docs/runbooks/tokens-to-answer.md#sample-tier-pinned-public-repos--the-real-value-claim-task-042) |
| Answer correctness, blind field round | **8 of 8 checked claims exact, zero false statements** | [PLAN §19](docs/PLAN.md#19-project-context--decision-log) |
| Cost of the *n*-th parallel agent | **~70 MB PSS**; the 925 MB index costs **0 MB** (page-cached, never mmapped) | [`parallel-agents.md`](docs/runbooks/parallel-agents.md) |
| Five agents vs one | **4.3× throughput**, 1.3 % of RAM, zero `SQLITE_BUSY` reaching a caller | same |
| Incremental no-op rebuild, large index | **56.1 s → 2.113 s (26×)** | [PLAN §19](docs/PLAN.md#19-project-context--decision-log) |
| Onboarding lookups vs hand-mapping | **cheaper, 12/12 correct, recall 1.0** | [`121_onboarding-question-class.md`](docs/benchmarks/121_onboarding-question-class.md) |

**Row two is the one the design optimises for.** Every failure in that round was *silence or
ambiguity* — never a wrong answer. A tool an agent cannot trust to be wrong-free is a tool whose
every answer must be re-verified by hand, which costs more than not having it.

## Configuration

Every knob resolves **environment → project file → default**. The project file is
`.code-atlas.toml` at the repo root (optional, meant to be committed); its keys are the environment
names lower-cased without the `CA_` prefix. A malformed value or an unknown key is a loud error,
never a silent fallback.

| Environment | `.code-atlas.toml` | Default | Meaning |
|---|---|---|---|
| `CA_DB_PATH` | `db_path` | `.code-atlas/graph.db` | index location (relative to the repo root). The file value must stay inside the repo; only the env var may point outside |
| `CA_WORKERS` | `workers` | `max(1, min(cpu-2, 8))` | adapter processes during a build |
| `CA_PAGE_LIMIT` | `page_limit` | `50` | query-time row ceiling for search/nav tools (no rebuild). Pre-259 `CA_MAX_RESULTS` does **not** set this |
| `CA_MAX_CANDIDATES` | `max_candidates` | `50` | build-time resolver fan-out (**rebuild** to apply). `CA_MAX_RESULTS` / project-file `max_results` still alias here |
| `CA_IMPACT_DEPTH` / `CA_IMPACT_MAX_NODES` | `impact_depth` / `impact_max_nodes` | `2` / `500` | hops and node budget for one impact query |
| `CA_ENTRY_POINTS` | `entry_points` | unset | file globs that seed reachability. **`reachable_from` and `find_orphans` need this** — unset, they report *no roots configured* rather than guessing, and `get_index_status` nominates candidate globs with a file count for you to choose from |
| `CA_STUB_ROOTS` | `stub_roots` | unset | dependency roots (e.g. `vendor`) to index declarations-only, so third-party signatures resolve |
| `CA_INDIRECTION_RULES` | `indirection_rules` | unset | JSON rule files mapping framework indirection to edges. **`find_view_data` needs this** |
| `CA_ARCHITECTURE_RULES` | `architecture_rules` | unset | JSON rule files of path-set dependency constraints. **`check_architecture_rules` needs this** |
| `CA_TOOLS` | `tools` | all 24 | comma-separated tool allow-list — see the six-tool preset below |
| `CA_<LANG>_CMD` | `[adapter_cmd].<lang>` | — | the **complete argv** that launches one adapter in server mode. The file table is honoured only with `CA_TRUST_PROJECT_FILE=1` |
| `CA_TRUST_PROJECT_FILE` | — (env only) | unset | `1` lets the repo's own `[adapter_cmd]` choose the argv. Unset, a table there is a loud error: a repo you index must not pick the command code-atlas runs |

```toml
# .code-atlas.toml — [adapter_cmd] is honoured only with CA_TRUST_PROJECT_FILE=1
workers = 4
page_limit = 50
max_candidates = 50

[adapter_cmd]
php = "docker compose exec -T php php /app/adapters/php/index.php --server"
typescript = "node /abs/path/to/code-atlas/adapters/typescript/index.js --server"
sql = "node /abs/path/to/code-atlas/adapters/sql/index.js --server"
python = "python3 /abs/path/to/code-atlas/adapters/python/index.py --server"
```

The adapter command is the **whole** command: the core appends nothing to it, not even `--server`,
so it never has to know where a language's adapter lives.

**Trimming the tool surface.** Twenty-four tool descriptions are read before the first question is
asked. `CA_TOOLS=get_index_status,search_symbol,read_symbol,find_callers,find_references,impact` is
the opt-in six-tool preset that covers the relationship questions; the default stays all 24.

**Routing ships with the server.** Its MCP `instructions` reach the model's system prompt and carry
this repo's live index state, the load step a client needs when it delivers MCP tools as deferred
names, where the graph stops, and the eight core rows of the question -> tool map. Claude Code keeps
only the first 2,048 characters, so they render in that order and fit under it; the full map is the
`which_tool` prompt and [`contrib/skill/`](contrib/skill/). Nothing has to be installed in your repo
for an agent to learn that the index exists.

Files are skipped using built-in patterns (`vendor/ var/ uploads/ log/ node_modules/ .git/
*.blade.*`), then `.gitignore`, then an optional `.codeatlasignore` — later rules win. The full
knob table, including the LLM-enrichment switches, is in
[`docs/TOOLS.md`](docs/TOOLS.md#configuration-reference).

**Optional LLM enrichment (off by default).** The onboarding tools are fully deterministic — no LLM,
no network. An opt-in package, [`onboarding_llm/`](onboarding_llm/README.md), plugs into three seams
to reword module summaries, weak layer names and the map's prose. Structure is never the seam's to
change: every count, ranking and grouping is derived before a model is consulted, and the core never
imports it.

## Testing

`scripts/gate.sh` runs the whole gate in one step — bytecode invalidation, entry points, `ruff`,
`mypy`, `pytest`, the tokens-to-answer benchmark, `composer validate`, `php -l`, phpstan at level
max, and the four rulebook grep-gates — in the same order
[`ci.yml`](.github/workflows/ci.yml) runs them. It exits non-zero if a check **failed or was
skipped**, because a gate that quietly shrinks to whatever the host can run has not verified
anything. Add `--fast` to skip the two slow checks, or `--docker` to run the same gate inside the
test image when the host lacks a runtime.

The suite needs a POSIX host with every adapter installed. To run everything off any host
(Windows/macOS included), use the Linux test image:

```sh
scripts/docker-test.sh                       # ruff + mypy + pytest -q (the full suite)
scripts/docker-test.sh pytest -q -k php      # just the PHP-adapter integration tests
```

Contributors: the expected pass/skip count for each route — the one place those numbers are
kept — and what a legitimate skip looks like are in [`AGENTS.md`](AGENTS.md).

## Documentation

| Doc | Answers |
|---|---|
| [`docs/TOOLS.md`](docs/TOOLS.md) | all 24 tools, the operator prompts, the opt-in hooks, and which tools take a list of subjects |
| [`docs/design/`](docs/design/) | why an answer is shaped the way it is — [payload](docs/design/payload.md) · [indexing & search](docs/design/indexing.md) · [impact & claims](docs/design/impact-and-claims.md) |
| [`docs/PLAN.md`](docs/PLAN.md) | the authoritative design, and **§19** — the decision log: what was measured, what was refuted |
| [`docs/CONVENTION.md`](docs/CONVENTION.md) | naming, repo layout, and **§6** — the payload contract every tool answer obeys |
| [`docs/ENGINEERING_RULES.md`](docs/ENGINEERING_RULES.md) | the binding *how we build* rules, several CI-gated |

**Runbooks** — operator protocols, each reproducible:
[onboarding a large legacy repo](docs/runbooks/onboarding-a-repo.md) ·
[tokens-to-answer](docs/runbooks/tokens-to-answer.md) ·
[parallel agents](docs/runbooks/parallel-agents.md) ·
[cross-repo validation](docs/runbooks/cross-repo-validation.md) ·
[field retro](docs/runbooks/field-retro.md) ·
[tool-recognition probe](docs/runbooks/tool-recognition-probe.md).

Contributors start at [`CONTRIBUTING.md`](CONTRIBUTING.md), agents at [`AGENTS.md`](AGENTS.md);
vulnerabilities go through [`SECURITY.md`](SECURITY.md).

## Roadmap

- **Core + PHP — shipped.** Full build → resolver → search/read/outline → scale → incremental → impact.
- **Onboarding — shipped.** `architecture_overview`, `guided_tour` and `generate_onboarding` emit a
  committable **system map** under `docs/onboarding/`: responsibility layers, dependency matrix,
  hubs, a business-module table, mirror-subtree lookup, a bounded tour, and the zero-inbound
  population split.
- **More languages — TS/JS, T-SQL and Python shipped.** The second adapter was the contract's real
  test and it passed **without a version bump** and without a line of core code — still one seam, no
  registry. C#/.NET is next.

**Design principles.** SOLID **at the boundaries** (the axis of change is *languages*, expressed
through one versioned contract) + **YAGNI** (one seam only) + **standard over sample** (adapters
encode the language spec/standards, never a specific repo's conventions). Details in the
[build plan](docs/PLAN.md).

## License

MIT — see [`LICENSE`](LICENSE). © 2026 Cuong Ngo.
