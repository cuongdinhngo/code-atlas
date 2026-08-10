#!/usr/bin/env sh
# Build the Linux test image and run the CI gates (ruff · mypy · pytest) — or any command passed.
# This is how you run the FULL suite off a non-Linux host: `fcntl` and the PHP adapter are present
# in the container, so nothing skips the way it does on Windows/macOS-without-php.
#
#   scripts/docker-test.sh                              # ruff + mypy + pytest -q
#   scripts/docker-test.sh pytest -q tests/test_store.py
#   scripts/docker-test.sh pytest -q -k php             # just the PHP-adapter integration tests
set -eu

root=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
docker build -f "$root/docker/Dockerfile" -t code-atlas-test "$root"

if [ "$#" -eq 0 ]; then
    exec docker run --rm code-atlas-test
fi
exec docker run --rm code-atlas-test "$@"
