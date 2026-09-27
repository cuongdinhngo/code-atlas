#!/usr/bin/env sh
# Run the whole CI gate locally, in the order .github/workflows/ci.yml runs it.
#
# This is the only gate: the repo's Actions report `fail` in ~3 s with 0 steps (unbillable), so
# `gh pr checks <n>` is not a second opinion (AGENTS.md). It mirrors all three CI jobs — test ·
# adapters · guardrails — and is the single step to perform before a push. Keep it in step with
# ci.yml: a check here that ci.yml lacks, or the reverse, means one of the two is lying about what
# was verified — `tests/test_ci_and_gate_agree.py` is what enforces that.
#
#   scripts/gate.sh            # every check
#   scripts/gate.sh --fast     # skip pytest and the tokens benchmark (the two slow ones)
#   scripts/gate.sh --docker   # the same gate inside docker/Dockerfile, for a host missing a runtime
#
# Exit status is 0 only when every check that ran passed AND nothing was skipped for a missing
# tool — a gate that quietly shrinks to the checks your machine can do is the 0/0 vacuity R6.5
# exists to prevent. Skips are counted, named, and turn the summary red.
set -eu

root=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
cd "$root"

fast=0
docker=0
inner=0
for arg in "$@"; do
    case $arg in
        --fast) fast=1 ;;
        --docker) docker=1 ;;
        --in-container) inner=1 ;;
    esac
done

# The recursion guard is an argv flag the outer run passes, never an env var that leaks (323).
if [ "$docker" -eq 1 ] && [ "$inner" -eq 1 ]; then
    echo "gate.sh: --docker inside the container gate would recurse; refused" >&2
    exit 64
fi
if [ "$docker" -eq 1 ]; then
    if ! command -v docker >/dev/null 2>&1; then
        echo "GATE INCOMPLETE — docker not on PATH; --docker ran no check" >&2
        exit 2
    fi
    # The image holds no check list of its own: it runs this file, so a skip inside is still exit 2.
    docker build -f "$root/docker/Dockerfile" -t code-atlas-test "$root"
    if [ "$fast" -eq 1 ]; then
        exec docker run --rm code-atlas-test sh scripts/gate.sh --in-container --fast
    fi
    exec docker run --rm code-atlas-test sh scripts/gate.sh --in-container
fi
where=""
[ "$inner" -eq 1 ] && where=" (container gate)"

# Prefer the project venv, fall back to PATH.
py=$root/.venv/bin/python
[ -x "$py" ] || py=$(command -v python3 || command -v python)
bin=$(dirname "$py")

passed=0
failed=0
skipped=0
report=""

_record() {  # _record <status> <name> [detail]
    report="${report}${1}|${2}|${3:-}
"
    case $1 in
        PASS) passed=$((passed + 1)) ;;
        FAIL) failed=$((failed + 1)) ;;
        SKIP) skipped=$((skipped + 1)) ;;
    esac
    printf '  %-4s %s%s\n' "$1" "$2" "${3:+  — $3}"
}

# Judge a step by its own exit status, never a pipeline's (LESSONS 084: piping through `tail`
# reports tail's 0 and masks a red gate). Output goes to a log we only print on failure.
_run() {  # _run <name> <command...>
    name=$1
    shift
    if "$@" >"$log" 2>&1; then
        _record PASS "$name"
    else
        _record FAIL "$name"
        sed 's/^/      /' "$log" | tail -30
    fi
}

log=$(mktemp)
trap 'rm -f "$log"' EXIT

echo "== job: test =="

# First, before anything below imports the tree. A .pyc records the source mtime in whole seconds
# plus its size, so an edit inside one second that keeps the length is invisible and every check
# after it reads stale bytecode — a GREEN about code that is not on disk (task 146). `-f` is what
# does the work: without it compileall skips files whose cache it already considers current.
_run "bytecode invalidation (checked-hash, 146)" \
    "$py" -m compileall -q -f --invalidation-mode checked-hash \
    -x 'tests[/\\]fixtures[/\\]python[/\\]' \
    code_atlas onboarding_llm tests

# ci.yml step "Install check": the declared console scripts resolve and import. Derived from
# [project.scripts], never listed (R6.7). Weaker than CI's by construction: CI checks a fresh
# non-editable `pip install .`, while from the repo root importlib.metadata prefers the checked-out
# `code_atlas.egg-info` over site-packages — so this verifies the *declaration*, and it prints which
# metadata it read so that is not mistaken for a check of your installed venv.
if "$py" - <<'PY' >"$log" 2>&1
import importlib.metadata as md
import pathlib
import sys
import tomllib

declared = set(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["scripts"])
eps = {
    e.name: e
    for e in md.entry_points(group="console_scripts")
    if e.dist and e.dist.name == "code-atlas"
}
assert declared, "no [project.scripts] found; this check would pass vacuously"
if declared != set(eps):
    sys.exit(
        f"declared {sorted(declared)} != installed {sorted(eps)}\n"
        "if this is a stale dev venv, reinstall: uv pip install -e '.[dev]'"
    )
for name in sorted(eps):
    eps[name].load()
from code_atlas.main import TOOL_NAMES

assert "search_symbol" in TOOL_NAMES
print("metadata:", md.distribution("code-atlas")._path)
print("entry points ok:", ", ".join(sorted(eps)))
PY
then
    _record PASS "entry points (derived from [project.scripts])" \
        "$(sed -n 's/^metadata: //p' "$log")"
else
    _record FAIL "entry points (derived from [project.scripts])"
    sed 's/^/      /' "$log"
fi

_run "ruff check ." "$bin/ruff" check .
# No path argument — a positional overrides `files` in pyproject.toml and would silently drop
# onboarding_llm/ from the check.
_run "mypy (code_atlas + onboarding_llm)" "$bin/mypy"

if [ "$fast" -eq 1 ]; then
    _record SKIP "pytest" "--fast"
    _record SKIP "tokens-to-answer" "--fast"
else
    # The TS adapter's needs_node tests skip without its deps installed; ci.yml installs them, so
    # mirror that here — otherwise pytest's TS coverage silently shrinks to zero (R6.5).
    if command -v npm >/dev/null 2>&1; then
        _run "npm ci (adapters/typescript)" npm ci --prefix adapters/typescript
        _run "npm ci (adapters/sql)" npm ci --prefix adapters/sql
    else
        _record SKIP "npm ci (adapters/typescript)" "npm not on PATH"
        _record SKIP "npm ci (adapters/sql)" "npm not on PATH"
    fi
    # ci.yml's test job runs `composer install --no-dev` before pytest. Running it here would
    # strip the dev tools phpstan needs below, so assert instead: without vendor/ the PHP adapter
    # tests fail or skip and pytest's PHP coverage shrinks without saying so (R6.5).
    if [ -f adapters/php/vendor/autoload.php ]; then
        _record PASS "php adapter runtime deps present (pytest coverage)"
    else
        _record SKIP "php adapter runtime deps present (pytest coverage)" \
            "run: composer install --working-dir=adapters/php"
    fi
    _run "pytest -q" "$bin/pytest" -q
    if command -v php >/dev/null 2>&1; then
        CA_PHP_CMD="php $root/adapters/php/index.php --server"
        export CA_PHP_CMD
        # 0.63 is FIXTURE_TIER_RATIO_FLOOR in scripts/tokens_to_answer.py; the test named in the
        # header asserts ci.yml and this line both carry it, so the three cannot drift apart.
        _run "tokens-to-answer (ratio >= 0.63, recall 1.0, precision 1.0)" \
            "$py" scripts/tokens_to_answer.py --min-ratio 0.63 --min-recall 1.0 \
            --min-precision 1.0
        unset CA_PHP_CMD
    else
        _record SKIP "tokens-to-answer" "php not on PATH"
    fi
fi

echo "== job: adapters =="

if command -v composer >/dev/null 2>&1; then
    _run "composer validate --strict (R8.3)" \
        composer validate --strict --no-check-publish --working-dir=adapters/php
else
    _record SKIP "composer validate (R8.3)" "composer not on PATH"
fi

if command -v php >/dev/null 2>&1; then
    # R6.5 — authored source only, and the sweep must not be able to empty itself.
    count=$(find adapters -path '*/vendor' -prune -o -name '*.php' -print | wc -l | tr -d ' ')
    if [ "$count" -eq 0 ]; then
        _record FAIL "php -l (authored source)" "no adapter source found — would pass vacuously"
    elif find adapters -path '*/vendor' -prune -o -name '*.php' -print0 \
        | xargs -0 -n1 php -l >"$log" 2>&1; then
        _record PASS "php -l (authored source)" "$count file(s)"
    else
        _record FAIL "php -l (authored source)"
        sed 's/^/      /' "$log" | tail -20
    fi
else
    _record SKIP "php -l (authored source)" "php not on PATH"
fi

if [ -x adapters/php/vendor/bin/phpstan ]; then
    _run "phpstan level max (R6.6)" \
        adapters/php/vendor/bin/phpstan analyse --no-progress \
        --configuration=adapters/php/phpstan.neon
else
    _record SKIP "phpstan level max (R6.6)" "run: composer install --working-dir=adapters/php"
fi

# TS adapter's phpstan-equivalent: tsc --checkJs --strict over the authored source (R6.6). Deps come
# from the `npm ci` in the test job above; a SKIP (never PASS) when they are absent keeps exit 2 honest.
if [ -x adapters/typescript/node_modules/.bin/tsc ]; then
    _run "tsc --checkJs --strict (R6.6, TS adapter)" \
        adapters/typescript/node_modules/.bin/tsc -p adapters/typescript/tsconfig.json
else
    _record SKIP "tsc --checkJs --strict (R6.6, TS adapter)" \
        "run: npm ci --prefix adapters/typescript"
fi

# The SQL adapter runs the same analyser at FULL strict — `noImplicitAny` included, because it is
# typed from its first commit and has no legacy to defer (task 184; contrast task 150).
if [ -x adapters/sql/node_modules/.bin/tsc ]; then
    _run "tsc --checkJs --strict (R6.6, SQL adapter)" \
        adapters/sql/node_modules/.bin/tsc -p adapters/sql/tsconfig.json
else
    _record SKIP "tsc --checkJs --strict (R6.6, SQL adapter)" \
        "run: npm ci --prefix adapters/sql"
fi

# Python adapter (task 020): ruff + mypy --strict over adapters/python only (R6.6). Uses the
# core venv's tools with the adapter-local pyproject.toml — zero adapter runtime deps.
if [ -x "$bin/ruff" ]; then
    _run "ruff check (R6.6, Python adapter)" \
        "$bin/ruff" check adapters/python
else
    _record SKIP "ruff check (R6.6, Python adapter)" "ruff not in .venv"
fi
if [ -x "$bin/mypy" ]; then
    _run "mypy --strict (R6.6, Python adapter)" \
        "$bin/mypy" --config-file adapters/python/pyproject.toml
else
    _record SKIP "mypy --strict (R6.6, Python adapter)" "mypy not in .venv"
fi

echo "== job: guardrails =="

# Each gate carries its own anti-vacuity check, exactly as ci.yml does: a missing directory is a
# failure, never a silent pass.
_gate() {  # _gate <name> <dir> <pattern> [dir2 pattern2 …]
    name=$1
    dir=$2
    pattern=$3
    if [ ! -d "$dir" ]; then
        _record FAIL "$name" "$dir/ is missing — this gate cannot pass vacuously"
        return
    fi
    if grep -rEn "$pattern" "$dir" >"$log" 2>&1; then
        _record FAIL "$name"
        sed 's/^/      /' "$log" | head -10
    else
        _record PASS "$name"
    fi
}

_gate "R1.1 no language branch in core" code_atlas \
    'if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b'

if [ ! -d adapters ] || [ ! -d code_atlas ]; then
    _record FAIL "R2.2 no repo/framework name" "a swept directory is missing"
elif [ ! -s tests/contract/framework_denylist.txt ]; then
    _record FAIL "R2.2 no repo/framework name" "framework denylist is missing or empty"
else
    fw=$(grep -vE '^[[:space:]]*(#|$)' tests/contract/framework_denylist.txt | tr -d '\r' | paste -sd'|' -)
    if grep -rEin --exclude-dir=vendor --exclude-dir=node_modules "\\b(${fw})\\b" adapters/ >"$log" 2>&1 \
        || grep -rEin "\\b(${fw})\\b" code_atlas/ >>"$log" 2>&1; then
        _record FAIL "R2.2 no repo/framework name"
        sed 's/^/      /' "$log" | head -10
    else
        _record PASS "R2.2 no repo/framework name"
    fi
fi

if [ ! -d code_atlas ]; then
    _record FAIL "R4.1 no LLM in core" "code_atlas/ is missing"
elif grep -rEn "^[[:space:]]*(from|import)[[:space:]]+(anthropic|onboarding_llm)\b" \
    code_atlas/ >"$log" 2>&1 \
    || grep -rEin 'claude-[a-z0-9.]|gpt-[0-9]|max_tokens|no preamble' code_atlas/ >>"$log" 2>&1; then
    _record FAIL "R4.1 no LLM in core"
    sed 's/^/      /' "$log" | head -10
else
    _record PASS "R4.1 no LLM in core"
fi

# CI compares the PR's commit range; locally the useful range is what is not yet on the remote.
range=origin/main..HEAD
if ! git rev-parse --verify -q origin/main >/dev/null 2>&1; then
    _record SKIP "R7.3 no AI-attribution trailer" "no origin/main to compare against"
elif [ "$(git rev-list --count "$range")" -eq 0 ]; then
    _record PASS "R7.3 no AI-attribution trailer" "nothing unpushed to check"
elif python3 scripts/attribution_markers.py "$range" >"$log" 2>&1; then
    _record PASS "R7.3 no AI-attribution trailer" "$(git rev-list --count "$range") commit(s)"
else
    _record FAIL "R7.3 no AI-attribution trailer"
    sed 's/^/      /' "$log" | head -10
fi

# Same range as R7.3; the script owns the empty-range refusal CI relies on (340).
if ! git rev-parse --verify -q origin/main >/dev/null 2>&1; then
    _record SKIP "R2.4 commit identity" "no origin/main to compare against"
elif [ "$(git rev-list --count "$range")" -eq 0 ]; then
    _record PASS "R2.4 commit identity" "nothing unpushed to check"
elif python3 scripts/identity_markers.py "$range" >"$log" 2>&1; then
    _record PASS "R2.4 commit identity" "$(git rev-list --count "$range") commit(s)"
else
    _record FAIL "R2.4 commit identity"
    sed 's/^/      /' "$log" | head -10
fi

echo
echo "== summary =="
printf '%s' "$report" | while IFS='|' read -r status name detail; do
    [ -n "$status" ] || continue
    [ "$status" = PASS ] || printf '  %-4s %s%s\n' "$status" "$name" "${detail:+  — $detail}"
done
echo "  $passed passed · $failed failed · $skipped skipped"

if [ "$failed" -gt 0 ]; then
    echo "GATE RED — $failed check(s) failed$where"
    exit 1
fi
if [ "$skipped" -gt 0 ]; then
    # A gate that shrank to what this machine can run has not verified the tree (R6.5).
    echo "GATE INCOMPLETE — $skipped check(s) skipped; this is not a green gate$where"
    exit 2
fi
echo "GATE GREEN — all $passed checks passed$where"
