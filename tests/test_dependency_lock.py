"""Task 425 — what CI tests is what installs: a hashed lock, floors above every advisory, and an
install line in every workflow, script and image that goes through a lock.

Each lint is seen matching a planted case (R6.5) and holds over the shipped files as its control.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
LOCK = REPO / "uv.lock"
STANDARD = REPO / "docs" / "SECURITY_STANDARD.md"

# Advisory id -> (package, first fixed version), read from the GitHub Advisory Database 2026-10-31.
FIXED_IN: dict[str, tuple[str, str]] = {
    "GHSA-7xgj-8392-5q4r": ("fastmcp", "3.4.10"),
    "GHSA-vv7q-7jx5-f767": ("fastmcp", "3.2.0"),
    "GHSA-rww4-4w9c-7733": ("fastmcp", "3.2.0"),
    "GHSA-m8x7-r2rg-vh5g": ("fastmcp", "3.2.0"),
    "GHSA-w4fh-qvv9-3v23": ("mcp", "1.30.0"),
    "GHSA-5h93-6whr-6q8j": ("mcp", "1.30.0"),
    "GHSA-rwrf-2pqf-9j8j": ("mcp", "1.30.0"),
    "GHSA-84m7-p3x7-pcfv": ("mcp", "1.30.0"),
    "GHSA-vj7q-gjh5-988w": ("mcp", "1.28.1"),
    "GHSA-jpw9-pfvf-9f58": ("mcp", "1.27.2"),
    "GHSA-hvrp-rf83-w775": ("mcp", "1.27.2"),
}
GHSA = re.compile(r"GHSA(?:-[0-9a-z]{4}){3}")


def _ver(text: str) -> tuple[int, ...]:
    return tuple(int(p) for p in text.split("."))


def _row(rule_id: str) -> str:
    for line in STANDARD.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {rule_id} "):
            return line
    raise AssertionError(f"{rule_id} is not a row of the standard")


def floor_gaps(deps: list[str], advisories: set[str]) -> list[str]:
    """Advisories the declared `>=` floor does not clear, or that have no entry in `FIXED_IN`."""
    floors: dict[str, str] = {}
    for dep in deps:
        m = re.match(r"([A-Za-z0-9_.-]+)\s*>=\s*([\d.]+)", dep)
        if m:
            floors[m.group(1).lower()] = m.group(2)
    gaps = []
    for adv in sorted(advisories):
        if adv not in FIXED_IN:
            gaps.append(f"{adv}: no fixed version recorded in this test")
            continue
        pkg, fixed = FIXED_IN[adv]
        if pkg not in floors or _ver(floors[pkg]) < _ver(fixed):
            gaps.append(f"{adv}: {pkg} floor {floors.get(pkg)} < {fixed}")
    return gaps


def _locked(package: str) -> str:
    data = tomllib.loads(LOCK.read_text(encoding="utf-8"))
    return next(p["version"] for p in data["package"] if p["name"] == package)


# ---------------------------------------------------------------------------------------- AC1
def test_the_floors_clear_every_advisory_sec_mcp_09_names() -> None:
    named = set(GHSA.findall(_row("SEC-MCP-09")))
    assert named == set(FIXED_IN), "the row and the fixed-version table must name the same ids"
    assert floor_gaps(PYPROJECT["project"]["dependencies"], named) == []
    for adv in named:
        pkg, fixed = FIXED_IN[adv]
        assert _ver(_locked(pkg)) >= _ver(fixed), f"{adv}: the lock resolves {pkg} below {fixed}"


def test_a_floor_below_a_fixed_version_is_refused() -> None:
    assert floor_gaps(["fastmcp>=3,<4", "mcp>=1.30.0"], {"GHSA-7xgj-8392-5q4r"})
    assert floor_gaps(["fastmcp>=3.4.10,<4", "mcp>=1.2"], {"GHSA-w4fh-qvv9-3v23"})
    assert floor_gaps(["fastmcp>=3.4.10,<4"], {"GHSA-w4fh-qvv9-3v23"})
    assert floor_gaps(["fastmcp>=3.4.10,<4", "mcp>=1.30.0"], {"GHSA-aaaa-bbbb-cccc"})


# ---------------------------------------------------------------------------------------- AC2
def lock_problems(text: str) -> list[str]:
    """A registry package with a missing hash, or a lock with no package to check."""
    packages = tomllib.loads(text).get("package", [])
    if not packages:
        return ["no package entries — this check would pass vacuously"]
    bad = []
    for pkg in packages:
        if "registry" not in pkg.get("source", {}):
            continue
        files = [*pkg.get("wheels", []), *([pkg["sdist"]] if "sdist" in pkg else [])]
        if not files or any(not f.get("hash", "").startswith("sha256:") for f in files):
            bad.append(f"{pkg['name']} {pkg['version']}")
    return bad


def test_uv_lock_is_committed_and_every_package_has_a_hash() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "uv.lock"], cwd=REPO, capture_output=True
    )
    assert tracked.returncode == 0, "uv.lock must be committed"
    assert lock_problems(LOCK.read_text(encoding="utf-8")) == []


def test_a_planted_unhashed_or_empty_lock_is_refused() -> None:
    registry = '{ registry = "https://pypi.org/simple" }'
    unhashed = f'[[package]]\nname = "x"\nversion = "1"\nsource = {registry}\n'
    assert lock_problems(unhashed) == ["x 1"]
    assert lock_problems("version = 1\n")


def test_the_lock_agrees_with_pyproject() -> None:
    if shutil.which("uv") is None:
        pytest.skip("uv is not installed on this host")
    run = subprocess.run(
        ["uv", "lock", "--check"], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    if run.returncode != 0 and re.search(r"error sending request|dns error|Connect", run.stderr):
        pytest.skip("uv could not reach the package index to re-resolve")
    assert run.returncode == 0, run.stderr


# Where the install lines live. Full-line comments are not run, so they are not read.
SWEEP = (
    *sorted((REPO / ".github" / "workflows").glob("*.yml")),
    REPO / "scripts" / "gate.sh",
    REPO / "docker" / "Dockerfile",
    REPO / "docker" / "Dockerfile.runtime",
)
# Any command that resolves or fetches packages; a bare `uv`/`pip` mention is not one.
INSTALL = re.compile(
    r"(?:\bpython3?\s+-m\s+)?\bpip3?\s+(?:install|download)\b[^&;|\\\n]*"
    r"|\bpipx\s+\w+[^&;|\\\n]*"
    r"|\buvx\b[^&;|\\\n]*"
    r"|\buv\s+(?:pip|tool|add|sync|run\s+--with)\b[^&;|\\\n]*"
    r"|\bnpm\s+(?:install|i|add|update|exec|x|ci)\b[^&;|\\\n]*"
    r"|\b(?:yarn|pnpm)\s+\w+[^&;|\\\n]*"
    r"|\bcomposer\s+(?:install|update|require)\b[^&;|\\\n]*"
)
# The only forms that install: from a lock, or an exact pin of the tool that reads one.
ALLOWED = (
    re.compile(r"uv sync\b(?=.*--(?:frozen|locked)\b)"),
    re.compile(r"npm ci\b"),
    re.compile(r"composer install\b"),
    re.compile(r"pip3? install(?: --[\w-]+)* uv==\d+(?:\.\d+)+\s*$"),
    re.compile(r"npm install (?:--global|-g) @?[\w./-]+@\d+(?:\.\d+)+\s*$"),
)


def install_violations(text: str) -> list[str]:
    """Every install command that is not one of `ALLOWED` — an unclassifiable one fails (424-C1)."""
    bad = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for m in INSTALL.finditer(line):
            cmd = m.group(0).strip()
            if not any(a.match(cmd) for a in ALLOWED):
                bad.append(cmd)
    return bad


PLANTED = [
    "pip install .",
    'pip install -e ".[dev]"',
    "pip install ruff mypy",
    "python -m pip install --upgrade pip",
    "pip install uv",
    "pip install uv>=0.11",
    "uv sync",
    "uv sync --extra dev",
    "uv pip install -e .",
    "uv tool install code-atlas",
    "uvx ruff check .",
    "npm install",
    "npm install --global @anthropic-ai/claude-code",
    "npm install --global @anthropic-ai/claude-code@latest",
    "composer update",
    "composer require phpstan/phpstan",
    "yarn add left-pad",
    "pipx run pip-audit",
    "RUN pip install --no-cache-dir -e . && uv sync --frozen",
]
ALLOWED_LINES = [
    "uv sync --frozen --extra dev",
    "UV_PROJECT_ENVIRONMENT=x uv sync --frozen --no-editable",
    "RUN uv sync --frozen --no-dev --no-editable",
    "npm ci --prefix adapters/sql",
    "composer install --no-dev --no-interaction --working-dir=adapters/php",
    "RUN pip install --no-cache-dir uv==0.11.28",
    "npm install --global @anthropic-ai/claude-code@2.1.316",
    "# pip install anything-in-a-comment",
]


@pytest.mark.parametrize("line", PLANTED)
def test_each_planted_unlocked_install_is_refused(line: str) -> None:
    assert install_violations(line), line


@pytest.mark.parametrize("line", ALLOWED_LINES)
def test_a_locked_install_or_the_pinned_tool_passes(line: str) -> None:
    assert install_violations(line) == [], line


def test_every_install_line_in_the_repo_goes_through_a_lock() -> None:
    sources = {p.relative_to(REPO).as_posix(): p.read_text(encoding="utf-8") for p in SWEEP}
    bad = {name: install_violations(text) for name, text in sources.items()}
    assert {name: found for name, found in bad.items() if found} == {}
    # R6.5: the sweep reads the files that install, and finds installs in each of them.
    for name in (".github/workflows/ci.yml", "docker/Dockerfile", "docker/Dockerfile.runtime"):
        assert any(ALLOWED[0].match(m.group(0)) for m in INSTALL.finditer(sources[name])), name
    assert "--no-dev" in sources["docker/Dockerfile.runtime"]


def test_every_lock_an_install_line_relies_on_is_committed() -> None:
    for lock in (
        "uv.lock",
        "adapters/php/composer.lock",
        "adapters/typescript/package-lock.json",
        "adapters/sql/package-lock.json",
    ):
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", lock], cwd=REPO, capture_output=True
        )
        assert tracked.returncode == 0, f"{lock} must be committed"


# ---------------------------------------------------------------------------------------- AC3
def test_the_audit_threshold_is_written_in_the_standard() -> None:
    for rule in ("SEC-SC-06", "SEC-SC-07"):
        assert "open:" not in _row(rule)
    assert "any known vulnerability" in _row("SEC-SC-07")
