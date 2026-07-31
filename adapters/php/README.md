# PHP adapter

Parses PHP into the code-atlas contract vocabulary. Self-contained: its runtime and dependencies live
here and never reach the Python core (R8.1).

## Runtime

- **PHP CLI ≥ 8.1** (the `tokenizer` extension only — no application extensions needed).
- **[nikic/php-parser](https://github.com/nikic/PHP-Parser) ^5**, pinned by the committed
  `composer.lock` so every machine resolves the same parser build.

The parser is pure PHP and targets `ParserFactory::createForNewestSupportedVersion()` — **PHP 8.5
grammar** — regardless of which PHP runs it. An 8.3 CLI parses 8.4 and 8.5 syntax correctly; the
runtime version affects speed, not what can be parsed.

## Install

```bash
composer install --working-dir=adapters/php
```

## Usage

`--file` parses one file and prints one JSON line — the contract result for that path. It is the
debugging and spiking mode; the streaming `--server` mode that the core actually drives arrives with
task 007, and `CA_PHP_CMD` will point at it then.

```bash
php adapters/php/index.php --file src/Models/User.php
```

The path is echoed verbatim into the result, so pass it **repo-relative** — that is what the store
records, under every runtime-invocation mode.

- **stdout carries the protocol and nothing else.** Diagnostics go to stderr.
- A file that cannot be read or parsed yields `{"path": …, "ok": false, "error": …}` and exit 0 — one
  bad file never breaks a build (R5.1).
- A missing `vendor/` is a configuration error: a message on stderr and exit 2, never a parse result
  (R5.3).

## What it emits

Nodes `File · Namespace · Class · Interface · Trait · Enum · Method · Property · ClassConst ·
Function`, and **bare** edges `CONTAINS · EXTENDS · IMPLEMENTS · IMPORTS · CALLS · NEW · INCLUDES` —
`target_raw` only, because a single file cannot know all targets. Cross-file linking is the core
resolver's job (R3.3).

Qualified names follow the convention in [`docs/CONVENTION.md`](../../docs/CONVENTION.md) §3 and are
anchored at the global namespace: `\Ns\Class`, `\Ns\Class::method`, `\Ns\Class::$prop`,
`\Ns\Class::CONST`, `\ns\func`. Global and underscore (PSR-0) names are first-class — `\Foo_Bar_Baz`
is a name like any other, not a special case. `NameResolver` supplies the FQN without a leading
separator; this adapter adds it.

An instance method call cannot reveal its receiver's type from one file, so it is emitted
`HEURISTIC` and never dressed up as `RESOLVED` (R5.2).

## Scope

Task 006 is a spike. Full language coverage — traits, enums, anonymous classes, closures, arrow
functions, first-class callables, attributes, group-use, promoted parameters, enum cases,
`ErrorHandler\Collecting` — lands in task 007 together with `--server`.
