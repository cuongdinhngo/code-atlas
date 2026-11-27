---
id: 457
slug: verify-refs-callable-container-not-gone
title: "A dotted name whose head only matches a method or function is not a member reference"
phase: 2
milestone: "Field gaps — tiny-studio"
status: todo
depends_on: [443]
---

## Why this exists

Same field report as 456 (tiny-studio, 2026-11-27). Docs name dotted words that are **not code**:
telemetry event names, SQL `table.column` pairs, Playwright calls on a local. `_resolve` takes the
part before the last dot, finds *some* indexed symbol with that last word, and asks `_member`.
That symbol is often a **method**, which has no members. Git never saw the member in the method's
file, so the row is `gone` / `missing_on_live_container` and actionable.

| Doc ref (rows) | What it really is | Container it was matched to |
|---|---|---|
| `llm.rejected` (7), `llm.call` (4) | telemetry events | `pipeline.Providers::llm` |
| `run.start` (3), `run.end` (5) | telemetry events | `pipeline.Pipeline::run` (method) |
| `step.end` (5) | telemetry event | `occlusion.OcclusionReport::step` |
| `tts.batch` (3), `tts.synth` (2) | telemetry events | `metrics.Metrics::tts` |
| `render.end` (3) | telemetry event | `HyperframesRenderer::render` (method) |
| `jobs.series_id` (3), `jobs.video_id` (2), `jobs.project_id`, `jobs.log_path` | SQL columns | `SqliteJobQueue::jobs` (method) |
| `accounts.slug` (3), `accounts.id`, `videos.channel_id`, `videos.published_at`, `channels.account_id` | SQL columns | `SqliteJobQueue::accounts` / `::videos` / `::channels` |
| `page.evaluate` | Playwright API on a local | `tests…test_cyber.page` (fixture function) |

Around 50 of the 70 false rows. The match on a lowercase head word is the weak point: `run` or
`jobs` in prose almost never means "the method `Pipeline.run`".

## Scope

1. If the matched container is a function or method (no class or record body), a following segment
   is not a member reference → `unknown` (reason `container_is_callable`), not actionable.
   456 handles a property or method **with** a return annotation first.
2. If the head is a lowercase word that matches a container only by its **last** segment (not its
   qualified name or class name), the row is `weak`. This only changes `strength`; the state stays.
3. Optional, if cheap: when an indexed SQL table has the head's name and a column with the tail's
   name, `ok` (reason `table_column`). Uses what the SQL adapter already emits; no new parser.

## Acceptance

1. Fixtures: `run.end` against a class with method `run` → `unknown`, not actionable;
   `Repo.gone` against a class `Repo` keeps today's verdict; a lowercase head that matches only a
   member name → `weak`.
2. Re-run tiny-studio: none of the rows in the table above is actionable. Report the count.
3. Anchor: the instruction-class actionable count before and after. A drop is fine if each dropped
   row is shown to be a non-code word.
