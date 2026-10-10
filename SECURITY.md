# Security policy

## Reporting a vulnerability

**Do not open a public issue.** Instead:

1. Open the repository's **Security** tab.
2. Click **Report a vulnerability**. This opens a private advisory that only the maintainer can see.

A useful report includes the affected version or commit, a minimal repo or file that triggers the
issue, and what an attacker gains.

code-atlas has a single maintainer, and reports are handled on a best-effort basis. You will get
an acknowledgement, and a fix or a decision, before anything is disclosed. Please give that time
before publishing.

## Supported versions

Releases are tagged `vX.Y.Z` and listed in [`CHANGELOG.md`](CHANGELOG.md). Only the latest release
is supported: fixes land on `main` and ship in the next release.

## Threat model

code-atlas indexes repositories you may not have written, so **the indexed repo is treated as
untrusted input**. It aims to hold these guarantees:

- **Indexed code is parsed, never executed.** Each adapter uses a parser only: `nikic/php-parser`,
  the TypeScript compiler API, Python's `ast`, and a purpose-built T-SQL scanner.
- **The indexed repo cannot choose what code-atlas runs.** A `.code-atlas.toml` with an
  `[adapter_cmd]` table is a loud error unless you set `CA_TRUST_PROJECT_FILE=1` yourself.
- **The indexed repo cannot aim the index outside itself.** A `db_path` set in `.code-atlas.toml`
  must resolve inside the repo; only the `CA_DB_PATH` environment variable may point elsewhere.
- **Reads and writes stay inside the repo.** A path code-atlas reads from, or writes into, the
  indexed repo is resolved with symlinks followed and refused if it lands outside
  (`code_atlas/containment.py`).
- **The core makes no network calls.** The optional LLM package, `onboarding_llm/`, is off by
  default. When you enable it, it sends derived facts to Anthropic's API: module paths,
  signatures, docblocks and graph facts, not function bodies.

### Known limitations

- **Three symlink paths are not yet contained:** files under a configured stub root (`CA_STUB_ROOTS`),
  a `.code-atlas/` directory that is itself committed as a symlink, and an indexed file swapped for a
  link out of the repo since the build — `read_symbol` refuses it, but another tool's read-through
  repair still re-parses it (375). All three are tracked in [`docs/BACKLOG.md`](docs/BACKLOG.md).
- **The indexed repo's own git config applies.** code-atlas runs read-only `git` commands
  (`rev-parse`, `ls-files`, `diff --name-only`, `config --get`) inside the indexed repo, so that repo's
  `.git/config` applies, exactly as it would if you ran `git` there yourself. Do not index a working
  copy whose `.git` directory you did not create, such as one unpacked from an archive, outside a
  container.
- **The runtime image runs as root** unless you pass `--user`. The README shows how.

A report that breaks one of the guarantees above is in scope. A report that restates a known
limitation is not, unless it shows a worse consequence than the one listed here.
