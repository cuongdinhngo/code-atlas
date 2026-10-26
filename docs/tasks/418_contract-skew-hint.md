---
id: 418
slug: contract-skew-hint
title: "A contract refusal names the older half — and a core installed from the adapters' checkout"
phase: 2
milestone: Coverage
status: done
depends_on: [374, 401]
---

## Why this exists

Issue #118, 2026-10-26. The core was installed (non-editable) from a checkout on the unmerged 0.9.0
branch; the checkout then went back to `main`, so the adapters it runs spoke v19 to a v20 core.
Every refresh was refused. `refresh_refused.hint` said to fix `CA_<LANG>_CMD` or its dependencies,
and the SessionStart line said `git pull` — neither was at fault, and `main` was not behind.

## Acceptance

1. A contract refusal's hint names the direction: an older adapter moves to the core's release
   (`git checkout v<release>`), an older core is reinstalled.
2. When an adapter's argv runs a file inside the directory the core was installed from
   (`direct_url.json`, non-editable), the hint says the core came from this checkout at another
   revision.
3. The SessionStart line, for that shared checkout, names the revision or a reinstall, never
   `git pull` / `uv tool upgrade`.
4. Fixture tests for both directions and the shared checkout.

## Resolution

- `adapter_skew.contract_fix` / `installed_from` / `same_checkout`; the refusal payload carries
  `hint`, which the CLI line prints, the refresh hook records and `get_index_status` prefers over
  the generic `REFRESH_HINTS` entry.
- `hooks/state.install_line(same_checkout=)` swaps the checkout and tool steps.
- Not done: "don't say `git pull` when the adapter is at the remote's head" needs a network read the
  offline hook cannot make; the shared-checkout test covers the reported case without one.
- `test_the_top_release_is_tagged` loses 417's strict xfail: `v0.9.0` is pushed, so it XPASSed.
- Proving: `tests/test_contract_skew_hint.py`.
