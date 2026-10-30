---
id: 426
slug: container-hardening
title: "The runtime image runs as a fixed non-root user from digest-pinned bases, and the documented run line drops every privilege it does not need"
phase: 2
milestone: Trust
status: todo
depends_on: [425]
---

## Why this exists

Both images build from `python:3.12-slim-bookworm` by tag, fetch composer with
`curl … | php`, and run as root. Running as root is also why 0.9.1 leaves a residual: git refuses
a host-owned `.git` mounted into a root container, so a tracked index cannot be refused there (420,
SECURITY.md *Known limitations*). The README run line passes no hardening flags.

## Acceptance

1. **Non-root:** `docker/Dockerfile.runtime` ends with `USER` at a fixed UID/GID; the README run
   line passes `--user "$(id -u):$(id -g)"` so the mounted repo's owner matches and git answers.
2. **Pinned bases:** every `FROM` names a digest (tag kept as a comment); composer comes from a
   digest-pinned `composer` image by `COPY --from`, never `curl | php`.
3. **Documented run line:** `--read-only --tmpfs /tmp --cap-drop=ALL
   --security-opt=no-new-privileges --network=none`, one writable index mount. A smoke test runs
   the image with exactly those flags and gets an MCP `initialize` answer.
4. **The 420 residual closes in the image:** with `--user`, a tracked index in the mounted repo is
   refused (fixture), and SECURITY.md's limitation narrows to "git cannot run".
5. **Context hygiene:** `.dockerignore` and `.gitignore` cover `.env*`, key files and `.mcp.json`;
   no `.git` credentials reach a layer (a test greps the build context rules).
6. **Scan:** the image is scanned in CI (Trivy or Grype), failing on a fixable critical; images
   stay build-only (not published).

## Call sites

`docker/Dockerfile`, `docker/Dockerfile.runtime`, `.dockerignore`, `.gitignore`, `README.md`
(container section), `scripts/docker-test.sh`, `.github/workflows/ci.yml` (image job),
`SECURITY.md`; standard rows SEC-CT-01..05, SEC-SC-09 (files).
