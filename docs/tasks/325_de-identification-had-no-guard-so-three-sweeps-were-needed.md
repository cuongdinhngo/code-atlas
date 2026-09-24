---
id: 325
slug: de-identification-had-no-guard-so-three-sweeps-were-needed
title: "De-identification had no guard, so it took three sweeps and still missed things"
phase: 1
milestone: Agent-trust
status: done
depends_on: [148]
---

## Why this exists

The anchor repo is a **client codebase**. Preparing this repo to go public, its identifiers were
replaced with shape-preserving stand-ins. That took **three manual passes**, and the reason there
were three is the finding:

- **Pass 1** (123 files) replaced the vocabulary it knew about.
- **Pass 2** found thirteen survivors, including two symbols where only one of two spellings had
  been mapped.
- **Pass 3** found the entire `Hm*` class family in **fifteen** files. Pass 2 had missed it because
  its grep output was read three lines at a time and judged complete on that sample.
- A fourth item — a fixture path — surfaced only when the rewrite rules were run against the tree
  and required to be a no-op. Any file the rules still changed was a file the sweeps had missed.

**A sweep cannot certify itself.** Every pass above was run by someone who believed the previous one
had finished. What was missing was not diligence; it was a guard that fails when the tree is dirty.

R2.2 does not cover this. It bans repo and framework names from **adapter and core source** — a
correctness rule, because a parser that encodes a customer's directory layout has stopped
implementing the language. R2.3 then leaves `tests/` and `scripts/` deliberately unswept. Every leak
found above was in `docs/tasks/`, fixtures or test assertions: outside R2.2 by design, and nothing
else looked there.

## The design problem, and why it shapes the solution

The obvious fix is a denylist, as `tests/contract/framework_denylist.txt` does for R2.2. It cannot
be copied here: **that file lists `laravel` and `react`, which are public names. This list would
hold a client's identifiers, so writing it in the clear publishes exactly what the guard exists to
keep out.** A plaintext denylist of secrets is the leak.

So the vocabulary arm matches **digests**, not words: `tests/contract/anchor_vocabulary_hashes.txt`
holds SHA-256/16 of each banned token, lowercased, and the plaintext mapping stays with the
maintainer, outside the repo. When the guard fires it prints the digest; the maintainer resolves it
locally.

**This is obfuscation, not secrecy, and the file says so in its own header.** The digests are short
and unsalted, so anyone who already suspects a term can confirm it by hashing their guess. What it
buys is that the repo never *hands over* the vocabulary. Salting would defeat CI, which has to
reproduce the digests from the committed file alone. Claiming more than that would be the kind of
false assurance this repo tickets.

## What the guard is

`tests/test_no_client_identifiers.py`, over **every tracked file** — no directory exempt, which is
the whole point.

| Arm | Catches | Blind to |
|---|---|---|
| Vocabulary (88 digests) | a removed name pasted back verbatim | anything not yet on the list |
| Foreign tracker key | a real ticket in someone's tracker | keys under our own stand-in prefix |
| Corporate domain `*.com.au` | an employer | a `.com` that is also a vendor |
| Real account home dir | a person's username in a transcript | `/home/you`, `/home/runner` |
| Windows domain logon | an employer in an author line | a drive-rooted path, which has the same shape |
| Email outside an allowlist | a work address | the allowlisted public ones |

The structural arms matter more than the vocabulary one: they carry no client knowledge, so they
catch the **next** leak, whose vocabulary no list can hold yet. Three of the four findings below
came from them, not from the digests.

**What it cannot catch, stated rather than implied:** a client term that is also ordinary English.
`resident` occurs 1,277 times here meaning *a resident language server*; banning it would fire on
every honest use. Those terms were handled by replacement, and a fresh paste of one would pass.

## Findings the guard produced on first run

1. `TKT-` and `FIELD-` were **two stand-ins for the same tracker**, 27 and 7 uses — drift between
   two de-identification passes. Unified to `FIELD-`.
2. `/home/<account>/` in **17 files** of transcript excerpts, naming the maintainer. Now `/home/you/`,
   matching the placeholder `docs/TOOLS.md` already used.
3. `.mailmap` carried a Windows domain logon — an **employer name** — and its presence was the
   tell that **173 commits carry that name as their author**. Checked against the API rather than
   assumed: GitHub serves the raw author name, so the mailmap was hiding it from local `git log`
   and from nothing else. Author names rewritten across history; `.mailmap` deleted, since a map
   whose left and right sides now agree has no work to do. The literal is not repeated here —
   this file is subject to its own guard, which is the intended answer to *"how do I document a
   removed name?"*: by its shape.
4. Two false-positive classes the first draft flagged, which calibrated the patterns rather than
   being silenced: one-letter scenario labels and line ranges are not tracker keys, so a prefix
   must be two-or-more letters; and a drive-rooted Windows path is not a logon, so the domain must
   not follow a separator.

5. **The guard fired on its own first draft** — the ticket you are reading, and the test source,
   both spelled out the strings they detect. Rewritten by shape. That is not an inconvenience to
   work around: a rule that cannot be documented without breaking itself would be unenforceable,
   and the fix is the same one every finding above took.

## Rule judgments

- **R6.7 (derive, never list) does not bind here.** It governs the set of *valid* members — tool
  names, reason codes — which has a definition site to derive from. A denylist is the set of things
  deliberately **absent**; it has no definition site by construction, and `framework_denylist.txt`
  is the standing precedent. R6.7's second clause — *a text sweep is not a derivation* — also does
  not bind: it forbids deciding a **source** fact from text where a parse was available. This
  decides a *disclosure* fact, and comments, docstrings and prose are precisely what must match.
- **R6.5 (no vacuous pass).** Two guards-of-the-guard: the digest file must hold ≥ 80 valid
  digests, and the sweep must reach > 500 tracked files. A green run over zero files was the
  failure mode that made three passes look finished.
- **R6.7 / R6.9 (one composition site).** No new `gate.sh` or `ci.yml` step: both already spend
  `pytest -q`, which runs this module. A shell arm would be a second place to drift, and a digest
  match is not a grep.
- **R7.6.** Ran first against `ENGINEERING_RULES.md` and came back empty — every rule there is one
  clause per falsifier and the sightings live in `LESSONS.md` by the preamble's own instruction. The
  ceiling rose 5,700 → 5,880 with the argument recorded at the budget line. What the pass did pay:
  R2.4 was cut from 190 tokens to 85, and the preamble's *"every rule below was ratified
  2026-08-30"* was corrected in the same commit, because R2.4 is `Provisional` and leaving that
  sentence would have made the doc lie.

## What this does not fix

The guard binds the **tree**. It cannot bind what GitHub already serves: `refs/pull/*/head` still
pins the pre-rewrite commits of every merged PR, and those refs are not deletable by a force-push
or by garbage collection, because they are reachable. Recreating the remote is the only thing that
clears them. That decision is open and is not this ticket's.

## Token ledger

One session, folded into the public-launch preparation; the row is in
[`TOKEN_LEDGER.md`](../TOKEN_LEDGER.md).
