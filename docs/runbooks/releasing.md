# Releasing

A release is built by [`release.yml`](../../.github/workflows/release.yml) from a signed `v*` tag,
never from a laptop (431). You bump, write the CHANGELOG entry, sign the tag and push it; the
workflow verifies, builds, attests and publishes. Nothing here needs a token of yours.

## One-time setup

1. **Pick the signing key.** An SSH key you sign with (`ssh-keygen -t ed25519`), kept off the repo.
2. **Commit `.github/allowed_signers` to `main`** by pull request, one line per key allowed to sign:
   `<email> ssh-ed25519 AAAA…` (the public key). Until this file exists the workflow refuses every
   tag, by design: no release without a signature it can verify.
3. **Turn on the tag ruleset's signature rule** (Settings, Rules, the `v*` tag ruleset, *Require
   signed commits*). The weekly `Settings drift` job reports `rulesets.tags.required_signatures`
   until it is on; GitHub does not document that the rule checks a tag object, so the workflow's own
   `verify-tag` is the guarantee, and the rule is the second lock.
4. Tell git how to sign: `git config gpg.format ssh` and `git config user.signingkey ~/.ssh/<key>`.

## Each release

1. Bump `version` in `pyproject.toml`, `.claude-plugin/marketplace.json`, the plugin's
   `plugin.json` and the hook tables (`python3 scripts/gen_skill.py`); the tests name any that lag.
2. In `CHANGELOG.md` turn *Unreleased* into `## X.Y.Z — YYYY-MM-DD · contract N · schema M`. A fixed
   advisory gets a `### Security` section that names its GHSA (SEC-GV-02), or the test goes red.
3. Run `scripts/gate.sh`, merge to `main` by pull request.
4. Sign and push the tag on the merge commit: `git tag -s vX.Y.Z -m vX.Y.Z <commit>` then
   `git push origin vX.Y.Z`. A lightweight or unsigned tag fails the workflow's first step.
5. Watch the `Release` run. It checks the tag, `pyproject.toml` and the CHANGELOG name one version,
   builds the sdist and wheel, writes the CycloneDX SBOM, attests provenance and the SBOM, and
   creates the GitHub Release with the CHANGELOG entry and those files.

A PEP 440 pre-release (`X.Y.ZrcN`, `aN`, `bN`, `.devN`) is created as a GitHub pre-release, so a
dry run in a fork never reads as the latest release. Try one there before the first real tag.

## Signing keys — another machine, a lost or stolen key

A key, not a machine, may release: the workflow trusts the lines of `main`'s `allowed_signers`, the
tag ruleset the signing keys on the GitHub account. Every change below lands on `main` by pull
request, and every new key is also added on GitHub (Settings, SSH keys, *Signing key*).

- **Another machine.** Give it its own key and add its line; never copy a key between machines.
  A hardware key (`ssh-keygen -t ed25519-sk`) signs from any machine it is plugged into.
- **A lost key.** Add the replacement's line and keep the old one, so the tags it signed still
  verify (`test_release_discipline` checks every tag from 0.10.0 against this file).
- **A stolen key.** Prefix its line with `valid-before="YYYYMMDD"` (the day it left your hands) and
  remove it on GitHub: tags it signed earlier still verify, later ones fail. A thief can backdate a
  tag, so check any tag dated near that day by hand.

## Verify a release

```bash
gh release download vX.Y.Z --repo cuongdinhngo/code-atlas --pattern '*.whl' --pattern 'sbom.cdx.json'
gh attestation verify code_atlas-X.Y.Z-py3-none-any.whl --repo cuongdinhngo/code-atlas
gh attestation verify code_atlas-X.Y.Z-py3-none-any.whl --repo cuongdinhngo/code-atlas \
  --predicate-type https://cyclonedx.org/bom
uv tool install ./code_atlas-X.Y.Z-py3-none-any.whl
```

## History

0.9.1 and earlier were tagged by hand: unsigned, no files on the Release. `test_release_discipline`
verifies signatures from 0.10.0 on (`SIGNED_FROM`).

## If a run fails

| Step | Cause | Fix |
|---|---|---|
| Verify the tag signature | no `.github/allowed_signers` on `main`, a tagged commit `main` does not hold, an unsigned or lightweight tag, or a key not in `main`'s file | land the file or key on `main`, then cut the next version with a signed tag on a `main` commit; a tag is never moved |
| Check the tag, pyproject.toml and the CHANGELOG | the three name different versions | fix and release the next version; a tag is never moved (the ruleset forbids it) |
| Release | the tag has a Release already | none needed; a Release is never replaced |
