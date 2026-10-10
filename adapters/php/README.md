# PHP adapter

Parses PHP into the code-atlas contract vocabulary. Self-contained: its runtime and dependencies live
here and never reach the Python core (R8.1).

## Runtime

- **PHP CLI ≥ 8.1** (the `tokenizer` extension only — no application extensions needed for indexing).
- **[nikic/php-parser](https://github.com/nikic/PHP-Parser) ^5**, pinned by the committed
  `composer.lock` so every machine resolves the same parser build.

The parser is pure PHP and targets `ParserFactory::createForNewestSupportedVersion()` — **PHP 8.5
grammar** — regardless of which PHP runs it. An 8.3 CLI parses 8.4 and 8.5 syntax correctly; the
runtime version affects speed, not what can be parsed.

### Host PHP (default)

```bash
CA_PHP_CMD="php /abs/path/adapters/php/index.php --server"
```

Native paths, no mapping. Point the command at the complete argv — the core appends nothing.

### Docker exec

When PHP is only inside a compose service, use a complete `docker compose exec` argv and point the
container service's **working directory** at the mounted repo. The build sends **repo-relative**
paths; with that cwd they open correctly — that is the Docker happy path. No root mapping required.

```bash
CA_PHP_CMD="docker compose exec -T php php /app/adapters/php/index.php --server"
```

Optional `CA_HOST_ROOT` / `CA_CONTAINER_ROOT` (both or neither) rewrite **absolute** host paths onto
the container root for the adapter wire; relative paths still pass through. The indexer never passes
absolutes today — the pair is defensive for callers that do. The core rebases echoed wire paths so
the store keeps the caller's form. CI indexes with host PHP only; live Docker dual-mode is a
documented coverage gap, not a CI job.

## Install

```bash
composer install --working-dir=adapters/php
```

## Static analysis

PHPStan at **`level: max`**, configured in `phpstan.neon` over `index.php` and `src/`. It is this
adapter's counterpart to the core's `mypy` and runs in CI (R6.6). No baseline file and no
`@phpstan-ignore`: a finding is closed by fixing the code, never by suppressing the rule.

```bash
composer install --working-dir=adapters/php   # phpstan is a dev dependency
adapters/php/vendor/bin/phpstan analyse --configuration=adapters/php/phpstan.neon
```

## Usage

`--server` is the mode the core drives: the adapter announces itself once, then answers one request
per line until stdin closes. Point `CA_PHP_CMD` at the complete argv (§9) — the core appends nothing.
See **Runtime** above for host vs Docker forms.

```
← {"name":"php","extensions":[".php",".phtml"],"capabilities":{},"contract_version":14,"symbol_shapes":[…]}
→ {"path":"src/Models/User.php"}
← {"path":"src/Models/User.php","ok":true,"nodes":[…],"edges":[…]}
```

**Extensions.** `.php` is the language default. `.phtml` is announced too — it is a widely used PHP
template suffix and still PHP source. Shared suffixes such as `.module` / `.inc` (also used by
asm/C/SQL and some CMS layouts) are **not** announced: PHP would treat non-`<?php` bytes as inline
HTML and index junk File nodes with no `parse_failures` signal (R2.3). Repos that need those
suffixes can follow up with an opt-in extension pack; until then exclude noise with `.codeatlasignore`.

`--file` parses one file and prints one JSON line. It is the debugging mode, and it shares its parse
with `--server`, so both modes emit byte-identical results for the same file:

```bash
php adapters/php/index.php --file src/Models/User.php
```

The path is echoed verbatim into the result, so pass it **repo-relative** — that is what the store
records, under every runtime-invocation mode.

- **stdout carries the protocol and nothing else.** Two host `php.ini` settings would otherwise
  corrupt it, so the entry point defends against both:
  - `display_errors` defaults to **stdout** on many builds, which would put a PHP warning between two
    protocol lines. The adapter forces it to `stderr` before writing anything.
  - `output_buffering` holds `echo` output until the process exits, deadlocking a lock-step reader.
    Replies are written with `fwrite(STDOUT, …)`, which bypasses that buffer — `fflush()`/`flush()`
    do **not**.
- A file that cannot be read or parsed yields `{"path": …, "ok": false, "error": …}` and exit 0 — one
  bad file never breaks a build or the stream (R5.1). `ErrorHandler\Collecting` recovers from every
  syntax error rather than throwing, so the process stays alive for the next request.
- A missing `vendor/`, or an unrecognised argv, is a configuration error: a message on stderr and
  exit 2, never a parse result (R5.3).
- A request line that is blank or carries no usable `path` is skipped with a note on stderr. It is
  never answered: a made-up path in a reply would misattribute every later result.

## What it emits

Nodes `File · Namespace · Class · Interface · Trait · Enum · Method · Property · ClassConst ·
Const · Function`, and **bare** edges `CONTAINS · EXTENDS · IMPLEMENTS · USES_TRAIT · IMPORTS ·
CALLS · NEW · INCLUDES · REFERENCES · ALIASES`, plus `WRITES`/`DELETES` from a string literal that
begins a T-SQL write, and `CALLS` from one that begins an `EXEC` (335; an unqualified name is
`dbo.<name>`, T-SQL's default schema, 386) —
`target_raw` only, because a single file cannot know all targets. Cross-file linking is the core
resolver's job (R3.3).

Qualified names follow the convention in [`docs/CONVENTION.md`](../../docs/CONVENTION.md) §3 and are
anchored at the global namespace: `\Ns\Class`, `\Ns\Class::method`, `\Ns\Class::$prop`,
`\Ns\Class::CONST`, `\ns\func`. Global and underscore (PSR-0) names are first-class — `\Foo_Bar_Baz`
is a name like any other, not a special case. `NameResolver` supplies the FQN without a leading
separator; this adapter adds it.

An instance method call whose receiver the local type table (137, `semantic_types`) can name is
emitted `Class::method`; otherwise it is the bare name at `HEURISTIC`, never dressed up as
`RESOLVED` (R5.2).

## Scope

Task 007 delivered the protocol: `--server`, `ErrorHandler\Collecting`, and the two `php.ini`
defences above. Task 025 delivered the language coverage — traits, enums and backed enums,
closures and arrow functions, attributes, property hooks, nullsafe calls and the rest of its
42-construct inventory, which lives in the tests (`tests/contract/`, `tests/fixtures/php/`).
