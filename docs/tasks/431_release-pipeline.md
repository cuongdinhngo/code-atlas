---
id: 431
slug: release-pipeline
title: "A release is built by a workflow, not a laptop — signed tag, GitHub Release with the wheel, an SBOM and a provenance attestation a user can verify"
phase: 2
milestone: Trust
status: todo
depends_on: [424, 425]
---

## Why this exists

0.9.1 was tagged and released by hand: the tag is unsigned, the release carries no artifact, and a
user installing `@v0.9.1` cannot check that what they got is what CI built. code-atlas is not on
PyPI (a look-alike name is taken), so the GitHub Release is the distribution point and must carry
the proof itself.

## Acceptance

1. **Signed tags and commits:** release tags are signed (SSH signing); the `v*` ruleset requires
   it; `test_release_discipline` verifies the top release's tag signature where the key is known.
2. **`release.yml`** on a `v*` tag push: builds sdist and wheel from the tag, generates a CycloneDX
   SBOM, attests build provenance (`actions/attest-build-provenance`, SLSA Build L2+), and creates
   the GitHub Release with the CHANGELOG entry and those files. Pinned, least-privilege, write
   scopes in that job only.
3. **Verification documented:** README and SECURITY.md show `gh attestation verify` on the wheel,
   and the install line that uses the verified file.
4. **Dry run:** a pre-release tag in a fork produces attested artifacts; recorded in the
   resolution.
5. **Advisory releases:** `test_release_discipline` fails when a release that fixed an advisory
   (its TOKEN_LEDGER row links a GHSA) has no `Security` section in its CHANGELOG entry (SEC-GV-02).
6. The release steps are written once, as `docs/runbooks/releasing.md` (bump, CHANGELOG, signed
   tag, the workflow does the rest); none exists today, and 0.9.1 was released by hand.

## Call sites

New `.github/workflows/release.yml`, `docs/runbooks/releasing.md`;
`tests/test_release_discipline.py`, `README.md`, `SECURITY.md`; standard rows SEC-SC-11..13
(13 recorded N/A: no PyPI), SEC-GV-02.
