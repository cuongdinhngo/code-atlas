"""323 — `scripts/gate.sh --docker` re-runs the same gate in the test image, and cannot recurse."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GATE = REPO / "scripts" / "gate.sh"
DOCKERFILE = REPO / "docker" / "Dockerfile"
DOCKERIGNORE = REPO / ".dockerignore"

# Records every call and exits 0 — stands in for docker so the route is checked without a daemon.
_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$DOCKER_CALLS"
"""


def _gate(
    *args: str, path: str | None = None, calls: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if path is not None:
        env["PATH"] = path
    if calls is not None:
        env["DOCKER_CALLS"] = str(calls)
    return subprocess.run(
        ["sh", str(GATE), *args], cwd=REPO, env=env, capture_output=True, text=True, timeout=60
    )


def test_inner_gate_refuses_docker_rather_than_recursing() -> None:
    """AC5 — the argv guard: `--in-container --docker` stops before any check runs."""
    out = _gate("--in-container", "--docker")
    assert out.returncode == 64, out.stdout + out.stderr
    assert "refused" in (out.stdout + out.stderr)
    assert "== job: test ==" not in out.stdout


def test_docker_route_builds_the_test_image_and_runs_the_same_gate(tmp_path: Path) -> None:
    """R1 — build docker/Dockerfile, then run this very script inside it with --in-container."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "docker"
    stub.write_text(_STUB, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    calls = tmp_path / "calls.txt"
    out = _gate("--docker", "--fast", path=f"{bin_dir}:{os.environ['PATH']}", calls=calls)
    assert out.returncode == 0, out.stdout + out.stderr
    build, run = calls.read_text(encoding="utf-8").splitlines()
    assert build.startswith("build -f ") and "docker/Dockerfile -t code-atlas-test" in build
    assert run == "run --rm code-atlas-test sh scripts/gate.sh --in-container --fast"
    assert "== job: test ==" not in out.stdout  # the host ran no check of its own


def test_docker_route_without_docker_is_named_not_a_pass(tmp_path: Path) -> None:
    """R6.5 — no docker on PATH is exit 2 with the reason, never a silent green."""
    empty = tmp_path / "empty"
    empty.mkdir()
    for tool in ("sh", "dirname"):
        target = next(
            Path(p) / tool for p in os.environ["PATH"].split(":") if (Path(p) / tool).exists()
        )
        (empty / tool).symlink_to(target)
    out = _gate("--docker", path=str(empty))
    assert out.returncode == 2, out.stdout + out.stderr
    assert "docker not on PATH" in (out.stdout + out.stderr)


def test_the_image_carries_what_the_gate_needs() -> None:
    """AC3/AC4 preconditions — phpstan (dev deps), the SQL adapter's tsc, and `.git` for R7.3."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "--no-dev" not in dockerfile
    assert "npm ci --prefix adapters/sql" in dockerfile
    ignored = [line.strip() for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()]
    assert ".git" not in ignored


def test_header_agrees_with_agents_md() -> None:
    """Scope 6 — the header no longer tells a reader that Actions are a second opinion."""
    head = "\n".join(GATE.read_text(encoding="utf-8").splitlines()[:12])
    assert "GitHub Actions DO run" not in head
    assert "gh pr checks" in head and "only gate" in head
