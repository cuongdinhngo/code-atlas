---
id: 230
slug: absolute-imports-resolve-only-by-climbing-from-the-importer
title: '`resolve_absolute` tries the repo root and then only the importer''s own ancestors, so a source root that is a sibling subtree — `src/` seen from `tests/`, a Lambda layer, any monorepo package dir — never resolves: 2,524 of one repo''s 4,838 unlinked `IMPORTS` name a module that is in the index, and 941 of them are four files under one root the walk cannot reach'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [020, 226]
---

## Why this exists

`resolve_absolute` (`adapters/python/src/imports.py:52-67`) tries `""` — the repo root — and then
walks **up** from the importing file's own directory, one `package_dir`/`climb` step at a time. Both
are correct and neither can reach a source root that sits in a *different* subtree.

That is not an edge case; it is two of the most common Python layouts:

- **`src/` layout**, the shape PyPA recommends. `tests/test_x.py` does `import mypkg`; `mypkg` lives
  at `src/mypkg/`. Ancestors of the importer are `tests` and `""`. The root `src` is never tried.
- **A shared package directory** — a Lambda layer, a monorepo `packages/` dir, anything put on
  `sys.path` at deploy time rather than by its position in the tree.

**Measured on a 1,209-file repo** whose shared code lives at `layers/packages/` and is imported as
`packages.*` because the layer is mounted at the interpreter's path root:

| Unlinked `IMPORTS` | | |
|---|---:|---:|
| names a module **that is in this index** | 2,524 | 52.2 % |
| external / stdlib — correctly unlinked | 2,314 | 47.8 % |

**941 of those in-repo misses are four modules under one root**: `packages.utils` (293),
`packages.exceptions` (251), `packages.constants` (228), `packages.decorators` (169) — all resolvable
under `layers`, none reachable by climbing from a caller in `lambdas/`. Downstream,
`architecture_overview` on that build reports the *Shared Library* layer as **8 modules with fan-in
12**, on a repo whose shared library is ~500 modules imported ~2,500 times.

**The naive fix is wrong and this ticket must not ship it.** Searching every directory for a
matching module manufactures false links: in the same repo `import requests` — the third-party HTTP
library — matches `lambdas/api/infer/models/requests.py`, and linking it would be a `RESOLVED` lie
about which code runs (R5.2). The distinguishing fact is *which roots the interpreter is actually
given*, and that is configuration, not something the filesystem can be asked.

**Nothing can express it today.** `KNOB_KEYS` (`code_atlas/config.py`) has `stub_roots` and
`working_roots` but no source root, and more fundamentally **the adapter never receives config at
all** — a parse request is `{path, declarations_only}` (`adapters/python/index.py:40-44`). So even a
new knob needs a decision about how a root reaches the adapter, and that decision is the substance
of this ticket.

## Scope

1. **Decide how a source root reaches an adapter, and record the decision.** The two candidate
   shapes are a new `KNOB_KEYS` entry carried on the parse request, and a language-neutral field on
   the handshake or request that any adapter may read. **A `python`-shaped field in the core is
   R1.1-barred** — whatever lands must be expressible by the PHP, TS and SQL adapters without the
   core naming a language. State the rejected option and why.
2. **Try configured roots in `resolve_absolute`, after the existing two.** Repo root, then the
   importer's ancestors (unchanged), then each configured root in the order given. First hit wins;
   determinism comes from the configured order, not from a directory walk (R4.2).
3. **Infer nothing.** With no configured root the adapter behaves exactly as it does today. An
   auto-detected `src/` is tempting and is the `requests` trap in another costume — if inference is
   proposed at all it needs its own evidence and its own ticket.
4. **Say when it would have helped.** An unlinked `IMPORTS` whose module resolves under **no**
   configured root but matches an indexed module by dotted suffix is the signal an operator needs to
   set the knob. Publishing that count at build or status time turns a silent 52 % into an
   actionable one; the surface is this ticket's to choose.

**Not in scope:** namespace packages (PEP 420) without `__init__.py`; `sys.path` manipulation in
code; editable installs and `.pth` files; any adapter but Python — though Scope 1's seam is
deliberately shaped so the others can use it.

## Acceptance criteria

- **AC1 (R6.5 — prove the guard fails first).** A fixture in the `src/` layout — `src/pkg/mod.py`
  plus `tests/test_mod.py` doing `from pkg.mod import Thing` — asserts today's adapter leaves that
  `IMPORTS` edge unlinked.
- **AC2** With `src` configured as a source root the same fixture links, at `RESOLVED`.
- **AC3** With **no** root configured the fixture is byte-identical to today's output. The default
  path does not move (R4.2).
- **AC4** A module name that collides with a third-party package — the `requests` shape, a file at
  `other/requests.py` under a root that is *not* configured — stays unlinked. Proven by a test, since
  this is the failure the ticket exists to avoid.
- **AC5** No language branch enters `code_atlas/` (R1.1, CI-gated), and `CONTRACT_VERSION` moves only
  if Scope 1 chooses a request-shape change — in which case the conformance suite moves with it (R3).

## Exclusions

- **E1** The 2,524 / 4,838 measurement is from a **local, private checkout**
  (`~/WORKSPACE/PROJECTS/InCloud/valance-system/valance-backend`, `develop` @ `7ba652d4`) and is not
  reproducible from this repo. The committed artifact is AC1's fixture; the re-run method is to test
  each unlinked `IMPORTS` `target_raw` against every `(root, dotted-module)` pair the indexed file
  set can offer.

## Notes

**Bounded interaction with 226.** 226 links a base class or annotation by looking its module up
through the same `imports.py` arithmetic, so on a repo like this one 226 would resolve the *relative*
imports (`from ..base.entity import Entity`, 62 of the 65 subclasses of `Entity` here) and miss the
absolute `packages.*` ones. 226 is worth landing without this; this ticket is what makes it complete
on a repo that mounts a source root.

**Why this is not a documentation fix.** `.codeatlasignore` and the runbook can tell an operator
what to exclude; there is no knob, no field and no payload that tells them a source root exists to be
declared, or that half their import graph is dark because none was.
