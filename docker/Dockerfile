# code-atlas test/dev image — Linux, so the FULL suite runs (POSIX `fcntl`) with the PHP adapter
# present. Mirrors CI's "lint · type · test" job: ruff · mypy · pytest, plus the adapter's composer
# deps so the `needs_php` integration tests run instead of skipping.
FROM python:3.12-slim-bookworm

# PHP CLI + the extensions nikic/php-parser and composer need; git/unzip/curl for composer itself.
# Debian bookworm ships PHP 8.2 (composer.json requires >=8.1); CI uses 8.3 — the pinned parser
# build in composer.lock, not the runtime minor, is what keeps parses deterministic (R4.2).
# `nodejs` is a TEST dependency, not a runtime one: the onboarding map builds its content in the
# browser, so task 116's AC4/AC5/AC6 are only provable by running the page under
# tests/viewer_dom_stub.js — grepping the HTML would see zero rendered figures.
RUN apt-get update && apt-get install -y --no-install-recommends \
        php-cli php-mbstring php-xml \
        nodejs \
        git unzip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Composer into a stable path.
RUN curl -sS https://getcomposer.org/installer \
    | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /app

# 1) Adapter deps first, keyed on the lock file so source edits don't re-resolve them (layer cache).
COPY adapters/php/composer.json adapters/php/composer.lock adapters/php/
RUN composer install --no-dev --no-interaction --no-progress --working-dir=adapters/php

# 2) The source, then an editable install so imports and console entry points resolve like CI.
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"

# The adapter launch command; tests pass their own via load_config, but this gives parity with CI's
# benchmark step and lets `code-atlas` run against the adapter inside the container.
ENV CA_PHP_CMD="php /app/adapters/php/index.php --server"

# Default: the three gates CI's test job runs. Override, e.g. `docker run --rm code-atlas-test pytest -q`.
CMD ["sh", "-c", "ruff check . && mypy code_atlas && pytest -q"]
