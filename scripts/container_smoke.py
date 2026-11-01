"""Smoke-test the runtime image under the documented hardened run line (426).

    python3 scripts/container_smoke.py <image>

Three arms, all against ``<image>`` with exactly ``RUN_FLAGS``: the image's own user is the fixed
non-root one, the server answers an MCP ``initialize``, and a repo that commits its index is
refused (420). README's run line is held to ``RUN_FLAGS`` by ``tests/test_container_hardening.py``.
Stdlib only, so CI runs it on the runner's own ``python3``. Exit 0 all pass, 1 any arm failed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

# The documented flags, once. `--user` takes the caller's ids, so the mounted repo's owner matches.
RUN_FLAGS = (
    "--user",
    "<uid>:<gid>",
    "--read-only",
    "--tmpfs",
    "/tmp",
    "--cap-drop=ALL",
    "--security-opt=no-new-privileges",
    "--network=none",
)
IMAGE_USER = "10001:10001"
TIMEOUT = 120
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "container-smoke", "version": "0"},
    },
}


def run_line(image: str, repo: Path) -> list[str]:
    """``docker run`` argv: the repo read-only, its ``.code-atlas/`` the one writable mount."""
    ids = f"{os.getuid()}:{os.getgid()}"
    flags = [ids if flag == "<uid>:<gid>" else flag for flag in RUN_FLAGS]
    return [
        "docker",
        "run",
        "-i",
        "--rm",
        *flags,
        "-v",
        f"{repo}:/workspace:ro",
        "-v",
        f"{repo / '.code-atlas'}:/workspace/.code-atlas",
        image,
    ]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(parent: Path, name: str, *, commit_index: bool) -> Path:
    repo = parent / name
    (repo / ".code-atlas").mkdir(parents=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "a.txt")
    if commit_index:
        (repo / ".code-atlas" / "graph.db").write_bytes(b"not a database")
        _git(repo, "add", "-f", ".code-atlas")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return repo


def _initialize(image: str, repo: Path) -> tuple[str, str]:
    """Send ``initialize``; return (first stdout line, stderr), the line '' if silent."""
    proc = subprocess.Popen(
        run_line(image, repo),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdin, stdout, stderr = proc.stdin, proc.stdout, proc.stderr
    assert stdin is not None and stdout is not None and stderr is not None
    line: list[str] = []
    reader = threading.Thread(target=lambda: line.append(stdout.readline()), daemon=True)
    reader.start()
    try:
        stdin.write(json.dumps(INITIALIZE) + "\n")
        stdin.flush()
    except BrokenPipeError:  # the server exited before reading: its stderr says why
        pass
    reader.join(TIMEOUT)
    try:
        stdin.close()
    except BrokenPipeError:
        pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    return (line[0] if line else ""), stderr.read()


def arm_user(image: str) -> str | None:
    shown = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Config.User}}", image],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if shown != IMAGE_USER:
        return f"the image's user is {shown!r}, not {IMAGE_USER!r}"
    return None


def arm_initialize(image: str, parent: Path) -> str | None:
    out, err = _initialize(image, _repo(parent, "clean", commit_index=False))
    try:
        reply = json.loads(out)
    except ValueError:
        return f"no JSON answer to initialize; stdout={out!r} stderr={err.strip()[-300:]!r}"
    info = reply.get("result", {}).get("serverInfo", {}) if isinstance(reply, dict) else {}
    if not info.get("name"):
        return f"initialize answered without serverInfo: {out.strip()[:300]!r}"
    return None


def arm_tracked_index(image: str, parent: Path) -> str | None:
    out, err = _initialize(image, _repo(parent, "tracked", commit_index=True))
    if out.strip():
        return f"the server answered a repo that commits its index: {out.strip()[:200]!r}"
    if "tracked by git" not in err:
        return f"no refusal naming the tracked index; stderr={err.strip()[-300:]!r}"
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    image = argv[1]
    with tempfile.TemporaryDirectory(prefix="ca-smoke-") as tmp:
        parent = Path(tmp)
        arms = (
            ("image user", lambda: arm_user(image)),
            ("initialize", lambda: arm_initialize(image, parent)),
            ("tracked index refused", lambda: arm_tracked_index(image, parent)),
        )
        failed = 0
        for name, arm in arms:
            problem = arm()
            print(f"{'FAIL' if problem else 'ok  '} {name}" + (f": {problem}" if problem else ""))
            failed += problem is not None
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
