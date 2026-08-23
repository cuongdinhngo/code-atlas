---
id: 131
slug: tour-ranks-configuration-ahead-of-the-front-controller
title: guided_tour's first five stops are lint and bootstrap config, not the front controller
phase: 3
milestone: Quality
status: todo
depends_on: [111, 121]
---

## Why this exists

This is **121**'s negative finding, and the one §5 promised to write down if the phase lost.

On the pinned `symfony/demo`, `guided_tour`'s first five stops are:

```
.php-cs-fixer.dist.php   config/bundles.php   config/preload.php   importmap.php   public/index.php
```

The hand answer to *"what are the first five things to read"* on a canonical layout is the front
controller, the kernel, a controller, an entity, and its repository. The tour gets **1 of 5**, and
spends the first four on lint and bootstrap configuration. A newcomer following it reads a code-style
config file first.

The mechanism is not a bug in the walk: roots are *"entry point (zero inbound)"*, ranked by out-degree,
and a lint config with zero inbound and zero outbound ties with everything else, so path order decides.
The walk is correct; the **claim** — a reading order — is what fails. 111 made the tour narrative
steps; nothing has asked whether the seed set deserves to be a reading order's first page.

Related but distinct: 108-117 fixed a 500-stop tour's *size*. This is its *ordering*.

## Scope

- Rank the seeds by something a reader would recognise: out-degree already exists but does not
  discriminate here; the responsibility layer of the root (110's vocabulary) does — `HTTP / Entry`
  before `Config / Migration`.
- A root with no outbound edge is not a place to start reading. Decide whether it is a seed at all.
- Derive the ordering from what the graph and the layer assignment already carry — no per-repo list of
  filenames to demote (R2.2), no framework knowledge in the core (R1.1).
- Prove it red first against a fixture holding a config file, a lint file and a front controller
  (R6.5), then re-measure `symfony/demo` and record the new first five in
  `docs/benchmarks/121_onboarding-question-class.md`.

## Acceptance criteria

1. **AC1.** On the pinned `symfony/demo`, the front controller appears in the tour's first five stops.
2. **AC2.** The ordering rule is derived from the layer/degree data already computed, with no repo,
   framework or filename literals added to the core.
3. **AC3.** A committed fixture asserts the rule and was observed failing before the change.
4. **AC4.** 121's finding #1 is struck, with the re-measured first five recorded in its place.
