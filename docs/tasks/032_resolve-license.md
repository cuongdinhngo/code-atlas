---
id: 032
slug: resolve-license
title: Resolve license (LICENSE file + README)
phase: 1.5
milestone: Adoption
status: in-progress
depends_on: []
---

## Goal
Turn the repo from unlicensed into installable. `README.md` currently says the license is **TBD** and
there is no `LICENSE` file at the root. If the audience is other people's AI agents and teams, an
unlicensed MCP server cannot pass a dependency review — this is the cheapest single unblocker for
adoption (§19 agent-first pivot).

## Scope / Deliverables
- A `LICENSE` file at the repo root with the chosen license text.
- `README.md` "License" section updated to name the license and drop "TBD".
- Any packaging metadata that states a license (e.g. `pyproject.toml`) set consistently.

## Constraints
- **License choice is a human decision, not the agent's.** This ticket surfaces options
  (e.g. MIT / Apache-2.0 / BSD-3-Clause) and their trade-offs; a human picks before the file is
  written. Do not select a license autonomously.
- No code change; docs/metadata only.

## Acceptance criteria
- `LICENSE` exists at the root and matches the chosen license verbatim.
- `README.md` names the license and contains no "TBD" for it; packaging metadata agrees.
- The choice is recorded (task working doc / §19 if it is a project-level decision).

## References
`README.md` (License section, "TBD"); `pyproject.toml` (license metadata). Feedback origin:
[`FEEDBACK.md`](../FEEDBACK.md) rounds 2 & 3 ("fix the license line — an unlicensed MCP server
doesn't get installed"). §19 agent-first pivot (cheap unblocker).

## Decision (human, 2026-08-04)
- **License: MIT** — permissive, the MCP/dev-tool ecosystem default, lowest friction for dependency
  review; the repo's own deps (nikic/php-parser BSD-3, PHPStan MIT, FastMCP) are permissive and force
  nothing stronger. Copyleft (GPL/AGPL) was rejected: it would block the commercial/agent audience
  the pivot targets.
- **Copyright holder: Cuong Ngo (personal)** — the GitHub repo is under the personal account.
- Delivered: `LICENSE` (MIT) at root; README License section names MIT + points to `LICENSE`;
  `pyproject.toml` carries `license = { text = "MIT" }` + the OSI MIT classifier.
