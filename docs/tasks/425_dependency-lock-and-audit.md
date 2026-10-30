---
id: 425
slug: dependency-lock-and-audit
title: "What CI tests is what installs — Python dependencies locked with hashes, the MCP SDK floor above every advisory, and every ecosystem audited in CI and the gate"
phase: 2
milestone: Trust
status: todo
depends_on: [423]
---

## Why this exists

`pyproject.toml` asks for `fastmcp>=3,<4`; there is no lock file, so CI, the images and a user's
install each resolve their own tree. Published FastMCP advisories sit inside that range (fixed in
3.2.0 and 3.4.10). Dev tools (`ruff`, `mypy`, `pytest`) are unpinned, and no step audits the Python,
npm or composer dependencies.

## Acceptance

1. **Floor:** `fastmcp>=3.4.10,<4`; the standard's SEC-MCP-09 row names the advisories it clears.
2. **Lock:** a `uv.lock` (hashes included) committed; CI and both Docker images install from it
   (`uv sync --frozen` or an exported hashed requirements file); dev tools pinned in the same lock.
   The npm adapters already lock (`package-lock.json`) and install with `npm ci`; composer installs
   from `composer.lock` — a test asserts each install line uses the lock.
3. **Audit:** `pip-audit` on the lock, `npm audit --omit=dev` for both adapters and
   `composer audit` run in CI and in `scripts/gate.sh`, failing at the threshold written in the
   standard (any known vulnerability with a fix available).
4. **Seen failing:** the audit step goes red on a seeded vulnerable pin (R6.5), recorded in the
   resolution.
5. The upgrade path a user follows (`uv tool install …@vX.Y.Z`) is unchanged; the CHANGELOG says
   the floor moved.

## Call sites

`pyproject.toml`, new `uv.lock`, `.github/workflows/ci.yml`, `scripts/gate.sh`,
`docker/Dockerfile`, `docker/Dockerfile.runtime`, `tests/test_ci_and_gate_agree.py`;
standard rows SEC-SC-06, 07, SEC-MCP-09.
