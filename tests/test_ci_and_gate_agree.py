"""`scripts/gate.sh` and `.github/workflows/ci.yml` must verify the same things (AGENTS.md).

AGENTS.md says "keep it in step with `ci.yml`: a check in one and not the other means one of them
is lying about what was verified" — and nothing enforced it. `gate.sh`'s header has since been
wrong in both directions about whether Actions run; it now says what AGENTS.md says (323).

The table below is the enforcement. Each row is one check that must be spent in BOTH files, matched
on the command each actually runs rather than on prose, so a check added to CI without a local
counterpart (or the reverse) fails here instead of being discovered on a red PR. One row is spent
only by `gate.sh --docker` — the image build (358) — and a test below pins it to that branch.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.tokens_to_answer import FIXTURE_TIER_RATIO_FLOOR

REPO = Path(__file__).resolve().parent.parent
CI = REPO / ".github" / "workflows" / "ci.yml"
GATE = REPO / "scripts" / "gate.sh"

# check name -> (substring ci.yml must contain, substring gate.sh must contain).
# The commands, not the step titles: a title can be reworded without changing what ran.
SHARED_CHECKS: dict[str, tuple[str, str]] = {
    "bytecode invalidation (146)": ("compileall", "compileall"),
    "entry points from [project.scripts]": ("console_scripts", "console_scripts"),
    "ruff (whole tree)": ("ruff check .", "ruff\" check ."),
    "mypy (no path argument)": ("run: mypy", '"$bin/mypy"'),
    "pytest": ("pytest -q", "pytest\" -q"),
    "tokens-to-answer fixture gate": ("tokens_to_answer.py", "tokens_to_answer.py"),
    "composer validate (R8.3)": ("composer validate", "composer validate"),
    "php -l authored source (R6.5)": ("php -l", "php -l"),
    "phpstan level max (R6.6)": ("phpstan analyse", "phpstan analyse"),
    "tsc TS adapter (R6.6)": (
        "adapters/typescript/tsconfig.json",
        "adapters/typescript/tsconfig.json",
    ),
    "tsc SQL adapter (R6.6)": ("adapters/sql/tsconfig.json", "adapters/sql/tsconfig.json"),
    "ruff Python adapter (R6.6)": ("ruff check adapters/python", "check adapters/python"),
    "mypy Python adapter (R6.6)": (
        "adapters/python/pyproject.toml",
        "adapters/python/pyproject.toml",
    ),
    "npm ci TS adapter deps": (
        "npm ci --prefix adapters/typescript",
        "npm ci --prefix adapters/typescript",
    ),
    "npm ci SQL adapter deps": (
        "npm ci --prefix adapters/sql",
        "npm ci --prefix adapters/sql",
    ),
    "R1.1 no language branch in core": (r"match[^\n]*\blanguage\b", r"match[^\n]*\blanguage\b"),
    "R2.2 framework denylist": (
        "tests/contract/framework_denylist.txt",
        "tests/contract/framework_denylist.txt",
    ),
    "R4.1 no LLM in core": ("anthropic|onboarding_llm", "anthropic|onboarding_llm"),
    "R7.3 no AI-attribution trailer": ("attribution_markers.py", "attribution_markers.py"),
    "R2.4 commit identity (340)": ("identity_markers.py", "identity_markers.py"),
    # The one row a plain run does not spend: only `--docker` builds the image (358).
    "test image builds (358)": (
        "file: docker/Dockerfile",
        'docker build -f "$root/docker/Dockerfile"',
    ),
}


def test_both_files_exist_and_are_substantial() -> None:
    """R6.5 — an empty or missing file would make every check below pass vacuously."""
    assert CI.is_file() and GATE.is_file()
    assert len(CI.read_text(encoding="utf-8").splitlines()) > 100
    assert len(GATE.read_text(encoding="utf-8").splitlines()) > 100
    assert len(SHARED_CHECKS) >= 20, "the table shrank — did a check get dropped instead of fixed?"


@pytest.mark.parametrize("name", sorted(SHARED_CHECKS))
def test_every_shared_check_is_spent_in_both_files(name: str) -> None:
    in_ci, in_gate = SHARED_CHECKS[name]
    assert in_ci in CI.read_text(encoding="utf-8"), (
        f"{name}: ci.yml no longer runs it ({in_ci!r}). Remove the row and the gate.sh check "
        "together, or restore the step — one file must not verify what the other does not."
    )
    assert in_gate in GATE.read_text(encoding="utf-8"), (
        f"{name}: scripts/gate.sh no longer runs it ({in_gate!r}). A local GATE GREEN would then "
        "claim more than it checked."
    )


def test_the_fixture_tier_floor_is_one_number_in_three_places() -> None:
    """The sample floor has been pinned since 223; the per-PR floor was a bare literal twice.

    Made to fail: change either spend site, or the constant, without the other two.
    """
    floor = f"--min-ratio {FIXTURE_TIER_RATIO_FLOOR}"
    assert floor in CI.read_text(encoding="utf-8")
    assert floor in GATE.read_text(encoding="utf-8")


def test_a_lint_failure_does_not_hide_the_test_results() -> None:
    """ruff · mypy · pytest share one job, so pytest must not be skipped when lint goes red.

    Red before the fix: #292's two-line E501 failed `ruff`, GitHub skipped `pytest`, and nine real
    payload-shape failures stayed invisible for four pushes.
    """
    ci = CI.read_text(encoding="utf-8")
    pytest_step = ci.split("- name: Tests (pytest")[1].split("- name:")[0]
    assert "!cancelled()" in pytest_step, (
        "the pytest step must run even after ruff/mypy fail, or a formatting slip hides every "
        "behavioural failure behind it"
    )


def test_the_test_image_job_builds_in_parallel_from_the_gha_cache() -> None:
    """358 AC3 and Scope 1/3: build only, beside the other jobs, reusing unchanged layers.

    Made to fail: add `needs:` to the job, a `run:` step to it, or drop either cache line.
    """
    ci = CI.read_text(encoding="utf-8")
    assert "\n  test-image:\n" in ci, "the test-image job is gone or renamed"
    body = ci.split("\n  test-image:\n")[1].split("\n  guardrails:\n")[0]
    job = "\n".join(line for line in body.splitlines() if not line.lstrip().startswith("#"))
    assert "needs:" not in job and "needs: test-image" not in ci
    assert "run:" not in job, "build only — the suite already runs in the test job"
    assert "file: docker/Dockerfile" in job and "context: ." in job
    assert "push: false" in job and "pull: true" in job
    assert "cache-from: type=gha" in job and "cache-to: type=gha" in job
    # A fork PR's read-only token cannot write the cache; that must not fail the build check.
    assert "ignore-error=true" in job


def test_only_the_docker_gate_builds_the_test_image() -> None:
    """The one `SHARED_CHECKS` row a plain run skips: the build sits in `--docker`'s branch.

    Made to fail: move the `docker build` line above `if [ "$docker" -eq 1 ]`, or past its `exec`.
    """
    gate = GATE.read_text(encoding="utf-8")
    branch = gate.split('if [ "$docker" -eq 1 ]; then\n    if ! command -v docker')[1]
    branch = branch.split("\nfi\n")[0]
    assert 'docker build -f "$root/docker/Dockerfile"' in branch
    assert gate.count('docker build -f "$root/docker/Dockerfile"') == 1
