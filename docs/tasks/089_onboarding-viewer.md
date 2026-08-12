---
id: 089
slug: onboarding-viewer
title: Onboarding — static HTML viewer (M11)
phase: 3
milestone: M11
status: todo
depends_on: [088]
---

## Goal
A small, offline viewer so a human can read the onboarding artifact without a server or toolchain.

## Scope / Deliverables
- A single self-contained, theme-aware HTML file that reads `manifest.json` and renders layers, the
  tour, and per-module pages. No server, no external deps (CSP-safe: inline CSS/JS, no CDNs).
- Emitted as an optional output of `generate_onboarding` (088).

## Acceptance criteria
- Opens offline from the filesystem; fully self-contained.
- Renders the manifest's layers + tour + module pages; legible in light and dark.
- Deterministic output for identical input.

## References
[`../phase3-onboarding/PHASE3_ONBOARDING.md`](../phase3-onboarding/PHASE3_ONBOARDING.md) §4 (M11);
PLAN §14, §15 (M11).
