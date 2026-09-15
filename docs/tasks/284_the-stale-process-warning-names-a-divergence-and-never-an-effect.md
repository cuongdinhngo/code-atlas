---
id: 284
slug: the-stale-process-warning-names-a-divergence-and-never-an-effect
title: '`server_stale_process` reports that the package on disk moved under the process and names a restart, but never whether any tool contract moved with it — so three consecutive field rounds read it, could not decide, ignored it, and one of them reported a `find_references` payload the shipped code cannot produce; the warning that cannot be acted on is the warning that costs a round of evidence'
phase: 1.5b
milestone: Agent-trust
status: todo
depends_on: [267, 170, 164]
---

## Why this exists (field retros — the anchor repo, rounds 24, 25 and 26, 2026-09-15)

267 made the stale-process warning actionable in the narrow sense: it names an action
(`restart_mcp_server_process`) and what differs (`code_atlas_package_bytes_on_disk`,
`build_info.py:27`). Three rounds later the field verdict is that neither answers the question a
reader actually has — *does this change any answer I am about to act on?* All three rounds recorded
`server_stale_process: true` on every payload, all three deliberately ignored it, and the third wrote:

> *"'I ignored the staleness warning and got away with it' is a bad habit for a tool to be training."*

The cost is not the noise. `server_build` is a **content hash** of the loaded tree frozen at import
(`_content_build_id`, `build_info.py:59`; `_capture_loaded_build_id`, `:70`), so on a diverged process
it resolves to no commit in any repo — while `server_repo_head` (`:130`) names the *checkout's* HEAD,
which moves under a long-lived process. A retro quoting both cannot reconstruct which code answered.

That is not hypothetical. Round 24 reported `find_references` on a PHP class answering
`relationship_not_modelled` with `unlinked_edge_kinds: ["IMPORTS"]`; the shipped code routes exactly
that branch into 252's member union and answers `via_members`
(`find_references.py:498-506`). Either the process predated 252 or the subject had no indexed
`CONTAINS` children — and nothing in the payload lets a reader tell those apart. Three rounds of field
evidence therefore have no resolvable provenance, which is the one thing the retro protocol buys.

The docstring already states the intent the payload does not reach: *"a retro can never quote a commit
that did not answer"* (`build_info.py:1-9`). A content hash that names nothing satisfies the letter and
loses the purpose.

## Scope / Deliverables

- **Say whether the drift is answer-affecting.** A stale payload carries a verdict a reader can act
  on — e.g. `server_stale_impact` distinguishing "no tool contract changed" from "a tool's payload
  shape changed" — derived from stored evidence (the loaded vs on-disk contract/tool surface), never
  from a guess or a timestamp.
- **Make the loaded build locatable, or say plainly that it is not.** When `server_build` is a content
  hash rather than a commit, the payload must mark it as such, so a reader does not spend a round
  trying to `git log` it.
- **`server_repo_head` must read as what it is** — the checkout's HEAD, not the running server's.
  Rename or document it at its definition site; three rounds recorded it as describing the server.

## Constraints

- R5.6: the impact verdict rides stored evidence, never inference from version strings.
- R4.2: identical artifact → identical fields; no timestamps, no mtimes in any published value
  (`_probe_state` stays out of every id, `build_info.py:80-82`).
- 061: a process that matches its disk stays byte-identical — this ticket adds nothing to the
  `stale_process: false` payload.
- Cost: no re-hash per payload; 164 measured that walk at 6.35 ms and 170 replaced it with the
  `sys.modules` stat probe. Whatever this reads must sit behind the same "only when the disk moved" gate.

## Acceptance criteria

- A diverged process whose tool contract is unchanged carries an impact verdict saying so.
- A diverged process whose contract *did* change carries the opposite verdict, and the two are
  distinguishable without reading source.
- A `server_build` that is a content hash is marked as not-a-commit.
- A matching process's payload is byte-identical to today's.
- No published field derives from a timestamp or an mtime.

## References
`code_atlas/build_info.py:1-9,27,59,70,115-131,158-177`,
`code_atlas/tools/find_references.py:498-506`,
[267](267_the-warning-an-autonomous-agent-cannot-act-on.md),
[170](170_server-identity-is-cached-so-a-later-build-swap-is-unreportable.md),
[252](252_a-class-reference-question-costs-n-plus-one-calls.md).
Origin: field retros rounds 24 §6, 25 §6 and 26 §1, 2026-09-15 — the same finding three rounds running.
