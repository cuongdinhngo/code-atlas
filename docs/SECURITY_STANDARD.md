# Security standard — code-atlas

The criteria code-atlas holds itself to, one row each. [`SECURITY.md`](../SECURITY.md) states the
trust model they protect; [`ENGINEERING_RULES.md`](ENGINEERING_RULES.md) §9 makes them binding.
Drawn up 2026-10-27 from the MCP specification (2026-07-28: security best practices, local-server
security, tools, transports), OWASP (LLM Top 10 2026, Agentic Top 10 2026, MCP Top 10, MCP Security
Cheat Sheet, Docker Security Cheat Sheet), CoSAI's MCP guide, OpenSSF Scorecard and the OSPS
Baseline, SLSA v1.2, and Claude Code's hooks and plugins references.

**Level:** `MUST` or `SHOULD`. **Verified by** is a `;`-separated list that
`tests/test_security_standard.py` resolves, item by item:

| Item | Means | Resolves when |
|---|---|---|
| `test: tests/<file>.py::<name>` | a test holds it | the file defines that test |
| `ci: <name>` | a workflow job or step holds it | a workflow under `.github/workflows/` has a job or step of that name |
| `doc: <path>#<heading>` | a document states it | the file has that heading |
| `open: NNN` | not held yet; ticket NNN closes it | `docs/tasks/NNN_*.md` exists and is not `done` |
| `n/a: <reason>` | does not apply, and why | a reason is written |
| `deferred: <reason>` | a `SHOULD` put off, and why | the row is a `SHOULD` and a reason is written |

A row is **held** when it names no `open:`. A held `MUST` names at least one `test:` or `ci:` — a
document alone guards nothing. A row held in part lists the guards it has and the ticket that
finishes it. A repo setting is not an item yet: until 424's drift check reads settings back, a row
that depends on one is `open: 424`.

## IN — untrusted repo input

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-IN-01 | Every path from repo content, config or tool arguments is resolved (symlinks followed) and contained by path components, never by string prefix | MUST | MCP Roots §Security; CVE-2025-53109, CVE-2025-53110 | test: tests/test_symlink_containment.py::test_a_link_out_of_the_repo_is_not_collected_and_is_counted; test: tests/test_symlink_containment.py::test_a_built_index_holds_no_row_from_outside; test: tests/test_symlink_containment.py::test_containment_treats_a_loop_and_an_escape_as_outside; test: tests/test_symlink_containment.py::test_an_indexed_file_swapped_for_a_link_out_reads_no_outside_text; open: 430 |
| SEC-IN-02 | Subprocesses take argv lists with `shell=False`; a positional derived from the repo or the index follows `--end-of-options` or `--` and is validated (a revision is a full object id) | MUST | Python `subprocess` §Security; CVE-2025-68144 | test: tests/test_git_revision_arguments.py::test_a_poisoned_last_commit_leaves_the_victim_untouched; test: tests/test_git_revision_arguments.py::test_a_non_object_id_is_refused_and_reported |
| SEC-IN-03 | The repo cannot choose a command, an output location or a host directory: `adapter_cmd`, `db_path`, `host_root` and `container_root` from the project file are gated or contained | MUST | MCP Security Best Practices §Local MCP server compromise; CVE-2025-59536 | test: tests/test_project_file_trust.py::test_an_untrusted_table_is_a_loud_error_naming_the_way_out; test: tests/test_project_file_trust.py::test_a_file_db_path_outside_the_repo_is_refused; test: tests/test_index_artifact_trust.py::test_a_linked_db_path_is_refused; open: 430 |
| SEC-IN-04 | Index artifacts are trusted only if code-atlas wrote them: an index git tracks is refused with the fix, and every write under the index directory refuses a link | MUST | CVE-2025-54136 | test: tests/test_index_artifact_trust.py::test_a_committed_index_is_refused_with_the_fix; test: tests/test_index_artifact_trust.py::test_a_running_server_refuses_an_index_committed_under_it; test: tests/test_index_artifact_trust.py::test_a_linked_index_file_leaves_the_victim_untouched; test: tests/test_index_artifact_trust.py::test_only_the_safe_writer_writes_files |
| SEC-IN-05 | A database opened from disk runs with `trusted_schema=OFF` and SQLite's defensive mode; extension loading stays off | SHOULD | SQLite defensive mode | test: tests/test_index_artifact_trust.py::test_a_view_in_the_index_runs_no_function; test: tests/test_index_artifact_trust.py::test_a_trigger_in_the_index_runs_no_function |
| SEC-IN-06 | SQL values are always bound; full-text input is quoted as one literal; `LIKE` wildcards are escaped | MUST | Python `sqlite3` placeholders | test: tests/test_store.py::test_a_search_operator_is_treated_as_a_literal; test: tests/test_store.py::test_a_punctuated_query_never_raises; test: tests/test_find_callers_cross_language_unmodelled.py::test_like_wildcards_in_the_name_match_only_themselves; test: tests/test_sql_confinement.py::test_exactly_one_core_module_touches_sqlite |
| SEC-IN-07 | No `eval`, `exec`, `pickle`, unsafe YAML or dynamic import on repo content; parsers never execute repo code | MUST | OWASP MCP Security Cheat Sheet §5; OWASP Agentic ASI05 | open: 424 |
| SEC-IN-08 | Repo- or index-derived text written to a log or state file, or shown by a hook or the server instructions, is validated or escaped | MUST | CWE-117 | test: tests/test_index_text_injection.py::test_a_forged_name_or_kind_adds_no_log_line; test: tests/test_index_text_injection.py::test_only_a_progress_line_the_build_writes_reaches_the_hook; test: tests/test_index_text_injection.py::test_hostile_meta_never_reaches_the_summary |
| SEC-IN-09 | Resources are bounded: a per-file size cap, an adapter reply-line cap, a timeout on every subprocess, project-file caps clamped to a ceiling | MUST | MCP Tools §Security; OWASP LLM10 unbounded consumption; CoSAI MCP guide | open: 430 |
| SEC-IN-10 | Repo-supplied regular expressions run under a length and feature limit, or a timeout engine | SHOULD | CWE-1333 | open: 430 |
| SEC-IN-11 | A read that crosses the trust line closes the check-then-use race (`O_NOFOLLOW`, or the opened descriptor's real path) | SHOULD | CWE-367 | open: 430 |
| SEC-IN-12 | Files and directories code-atlas creates are user-only (`0700` directories, `0600` files) | SHOULD | OSPS Baseline | test: tests/test_index_artifact_trust.py::test_the_index_is_private; open: 430 |
| SEC-IN-13 | Adapter subprocesses get a scrubbed environment: no API keys or tracker tokens | SHOULD | MCP Local Server Security §credentials | open: 430 |
| SEC-IN-14 | git runs hardened on an untrusted repo (the repo's `core.fsmonitor`, `core.hooksPath`, `core.sshCommand` and `diff.external` overridden; no prompt), and a network git command never runs in the repo's working directory | MUST | git documentation; CVE-2024-32002 | test: tests/test_git_revision_arguments.py::test_every_call_carries_the_hardening; test: tests/test_git_revision_arguments.py::test_only_gitutil_runs_git; test: tests/test_git_revision_arguments.py::test_an_old_git_fails_loud; open: 427; open: 430 |

## MCP — protocol and tool surface

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-MCP-01 | stdio only, no HTTP transport; one added later checks `Origin`, binds `127.0.0.1` and requires a token | MUST | MCP Security Best Practices; Streamable HTTP §Security | open: 428 |
| SEC-MCP-02 | stdout carries MCP messages only: adapter output is always captured and logs go to stderr | MUST | MCP stdio transport | open: 428 |
| SEC-MCP-03 | Every tool declares honest annotations: queries read-only and closed-world; the build and onboarding tools not read-only, not destructive, idempotent | SHOULD | MCP Tools; `ToolAnnotations` | open: 428 |
| SEC-MCP-04 | Input schemas are closed: no additional properties, bounded strings, enums where the domain is closed | SHOULD | MCP Tools; OWASP MCP Security Cheat Sheet §2 | open: 428 |
| SEC-MCP-05 | The tool surface is pinned: a committed manifest of names, descriptions, schemas and annotations, compared in CI, so a change is a reviewed diff with a CHANGELOG line | SHOULD | OWASP MCP Security Cheat Sheet §2, §11 | open: 428 |
| SEC-MCP-06 | Tool descriptions, prompts and server instructions hold no repo-derived text beyond a bounded, escaped, enumerated state line | MUST | OWASP MCP Top 10 (tool poisoning) | test: tests/test_index_text_injection.py::test_a_planted_refusal_record_never_speaks_as_code_atlas; test: tests/test_index_text_injection.py::test_hostile_meta_never_reaches_the_summary; test: tests/test_index_text_injection.py::test_the_cap_holds_the_longest_summary_the_code_composes |
| SEC-MCP-07 | An error is a tool error result, without a stack trace, a secret or a host path outside the repo | MUST | MCP Tools §Error handling | open: 428 |
| SEC-MCP-08 | Roots and Sampling are not adopted (deprecated 2026-07-28); the repo root comes from configuration | SHOULD | MCP changelog 2026-07-28 | doc: SECURITY.md#Trust model |
| SEC-MCP-09 | The MCP SDK floor is above every published advisory against it | MUST | GitHub Advisory Database (GHSA-7xgj-8392-5q4r; CVE-2026-32871) | open: 425 |

## PI — prompt injection and LLM output

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-PI-01 | Repo-derived text in a tool answer is framed as data (a named field, never instruction-like prose), and the server instructions say it is untrusted | MUST | OWASP LLM01; OWASP MCP Top 10 | open: 429 |
| SEC-PI-02 | ANSI escapes, bidi controls and invisible format characters are escaped in tool answers, hook output, generated markdown and the viewer | MUST | CVE-2021-42574 | test: tests/test_index_text_injection.py::test_hostile_meta_never_reaches_the_summary; open: 429 |
| SEC-PI-03 | LLM prose is untrusted output: escaped before it is rendered, never executed, and the prompt delimits repo text as data | MUST | OWASP LLM05 improper output handling | open: 429 |
| SEC-PI-04 | Persisted derived content carries provenance; a committed cache is checked or ignored, never trusted as-is | SHOULD | OWASP Agentic ASI06 | open: 429 |
| SEC-PI-05 | Safety lives in deterministic code; a model-facing rule is only ever an addition | MUST | OWASP MCP Security Cheat Sheet §12 | ci: R4.1 — no prompt, model name or LLM import in the core (task 117 AC7); doc: docs/ENGINEERING_RULES.md#4. Determinism & purity of the core |
| SEC-PI-06 | Agent configuration inside the indexed repo (`.claude/`, `.mcp.json`, `.cursor/`, editor tasks) is indexed as inert text, never activated | MUST | CVE-2025-54135, CVE-2025-54136 | open: 429 |

## PL — plugin and hooks

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-PL-01 | A hook activates on state the repo cannot ship (an index code-atlas built), not on a directory existing | MUST | Claude Code hooks §Security | open: 427 |
| SEC-PL-02 | Hook commands quote their variables, stay fast and make no network call on the session's path | MUST | Claude Code hooks §Security | test: tests/test_claude_code_plugin.py::test_every_plugin_hook_is_gated_and_names_a_declared_script; test: tests/test_claude_code_plugin.py::test_each_hook_is_silent_in_a_repo_with_no_index; open: 427 |
| SEC-PL-03 | The plugin runs the server release it shipped with; a mismatch refuses to start rather than warns | SHOULD | MCP Local Server Security §provenance; OWASP Agentic ASI04 | open: 427 |
| SEC-PL-04 | Every install and upgrade line names a release tag; nothing tells a user to unpin | MUST | Scorecard Pinned-Dependencies | open: 427 |
| SEC-PL-05 | No advice to auto-update the marketplace while it tracks a branch | SHOULD | OWASP Agentic ASI04 | open: 427 |
| SEC-PL-06 | `claude plugin validate --strict` passes in CI | SHOULD | Claude Code plugins reference | open: 424 |
| SEC-PL-07 | Skill text never tells the agent to auto-approve, widen permissions or follow tool output as instructions | MUST | OWASP Agentic Skills Top 10 | open: 427 |
| SEC-PL-08 | Other hosts' snippets carry the same gates as the Claude Code hooks | SHOULD | Claude Code hooks §Security | test: tests/test_hook_offers_agree_across_hosts.py::test_every_host_offers_the_same_hook_commands; open: 427 |

## SC — supply chain, CI and release

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-SC-01 | Every `uses:` is pinned to a full commit SHA, and the repo requires it | MUST | GitHub secure use of Actions; Scorecard Pinned-Dependencies | open: 424 |
| SEC-SC-02 | Workflow permissions are least privilege; a write scope appears only in a job that runs no pull-request code | MUST | Scorecard Token-Permissions; OSPS-AC-04 | open: 424 |
| SEC-SC-03 | No `pull_request_target` or `workflow_run` with a pull-request checkout; no event expression inside `run:` | MUST | Scorecard Dangerous-Workflow; OSPS-BR-01 | open: 424 |
| SEC-SC-04 | Every checkout sets `persist-credentials: false` | SHOULD | GitHub secure use of Actions | open: 424 |
| SEC-SC-05 | Dependabot covers every ecosystem (pip, npm, composer, Actions, Docker), with security updates on | MUST | Scorecard Dependency-Update-Tool; OSPS-VM-05 | open: 424 |
| SEC-SC-06 | Python dependencies are locked with hashes and installed from the lock in CI and the images; dev tools are pinned | MUST | Scorecard Pinned-Dependencies; OSPS-QA-02 | open: 425 |
| SEC-SC-07 | CI and the gate audit dependencies (`pip-audit`, `npm audit`, `composer audit`) against a documented threshold | MUST | Scorecard Vulnerabilities; OSPS-VM-05 | open: 425 |
| SEC-SC-08 | CodeQL runs on Python and JavaScript | SHOULD | Scorecard SAST; OSPS-VM-06 | open: 424 |
| SEC-SC-09 | Secret scanning and push protection are on; `.gitignore` and `.dockerignore` cover `.env*`, keys and `.mcp.json` | MUST | OSPS-BR-07 | open: 424; open: 426 |
| SEC-SC-10 | `main` and `v*` tags are protected by rulesets that target them: pull request and required checks on `main`, no tag update or deletion | MUST | OSPS-AC-03; Scorecard Branch-Protection | open: 424 |
| SEC-SC-11 | Release tags and commits are signed, and the ruleset requires it | SHOULD | Scorecard Signed-Releases; OSPS-BR-06 | open: 431 |
| SEC-SC-12 | A workflow builds each release with SLSA Build L2+ provenance and an SBOM, as a GitHub Release | SHOULD | SLSA v1.2; OSPS-QA-02 | open: 431 |
| SEC-SC-13 | A release published to PyPI uses Trusted Publishing only, with attestations | MUST | PyPI Trusted Publishing | n/a: code-atlas is not published to PyPI, the GitHub Release is its distribution point (431) |
| SEC-SC-14 | No unreviewable binary is committed | MUST | OSPS-QA-05; Scorecard Binary-Artifacts | open: 424 |
| SEC-SC-15 | OpenSSF Scorecard runs weekly against an agreed target | SHOULD | OpenSSF Scorecard | open: 424 |
| SEC-SC-16 | The identity sweep (R2.4) covers branch and pull-request ref names, not only files and commits | MUST | OSPS-BR-01 | open: 424 |

## CT — container

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-CT-01 | The runtime image runs as a non-root user with a fixed UID and GID | MUST | OWASP Docker Security Cheat Sheet #2 | open: 426 |
| SEC-CT-02 | Base images are pinned by digest; build tools come from pinned images, never a piped installer script | MUST | Docker build best practices | open: 426 |
| SEC-CT-03 | The documented run line is read-only, drops every capability, forbids new privileges, has no network and mounts one writable index | SHOULD | OWASP Docker Security Cheat Sheet #3, #4, #7, #8 | open: 426 |
| SEC-CT-04 | The image is scanned in CI | SHOULD | OWASP Docker Security Cheat Sheet #9 | open: 426 |
| SEC-CT-05 | No secret or `.git` credential is baked into a layer | MUST | OWASP Docker Security Cheat Sheet #12 | open: 426 |

## GV — governance and disclosure

| ID | Criterion | Level | Source | Verified by |
|---|---|---|---|---|
| SEC-GV-01 | `SECURITY.md` names a working private channel (private vulnerability reporting on) | MUST | OSPS-VM-02, OSPS-VM-03 | doc: SECURITY.md#Reporting a vulnerability; open: 424 |
| SEC-GV-02 | A fixed vulnerability gets a GHSA, a CVE request and a `Security` section in its CHANGELOG release | MUST | OSPS-VM-01, OSPS-VM-04 | doc: docs/ENGINEERING_RULES.md#9. Security; open: 431 |
| SEC-GV-03 | The threat model is written down: trust domains, every network call, every git command | MUST | OSPS-SA-01..03; MCP Local Server Security | test: tests/test_security_standard.py::test_security_md_names_every_git_command_code_atlas_runs; doc: SECURITY.md#Trust model; doc: SECURITY.md#Network calls |
| SEC-GV-04 | The maintainer account uses 2FA and the repo has no other admin | MUST | OSPS-AC-01, OSPS-AC-02 | open: 424 |
| SEC-GV-05 | Supported versions are stated | SHOULD | OSPS-DO-04, OSPS-DO-05 | doc: SECURITY.md#Supported versions |
| SEC-GV-06 | Users are told which client-side controls to keep on | SHOULD | MCP Tools §User interaction; OWASP MCP Security Cheat Sheet §4 | doc: SECURITY.md#Client-side controls |
| SEC-GV-07 | No doc tells a user to install from PyPI by name; the README says look-alike packages are not code-atlas | MUST | typosquatting defence | open: 427 |
