"""Smoke-test the runtime image under the documented hardened run line (426).

    python3 scripts/container_smoke.py <image>

Arms, all against ``<image>`` with exactly ``RUN_FLAGS``: the image's own user is the fixed
non-root one, the server answers an MCP ``initialize``, a repo that commits its index is refused
(420), an index build writes only ``.code-atlas/``, and ``generate_onboarding`` works once
``docs/onboarding`` is mounted too. README's run line is held to ``RUN_FLAGS`` by
``tests/test_container_hardening.py``.
Stdlib only, so CI runs it on the runner's own ``python3``. Exit 0 all pass, 1 any arm failed.
"""

from __future__ import annotations

import json
import os
import queue
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


def run_line(
    image: str, repo: Path, *, extra_mounts: tuple[str, ...] = (), index_mount: bool = True
) -> list[str]:
    """``docker run`` argv: the repo read-only, its ``.code-atlas/`` the one writable mount.

    ``extra_mounts`` are repo-relative directories mounted writable too (``docs/onboarding``).
    """
    ids = f"{os.getuid()}:{os.getgid()}"
    flags = [ids if flag == "<uid>:<gid>" else flag for flag in RUN_FLAGS]
    mounts = [f"{repo}:/workspace:ro"]
    if index_mount:
        mounts.append(f"{repo / '.code-atlas'}:/workspace/.code-atlas")
    mounts += [f"{repo / path}:/workspace/{path}" for path in extra_mounts]
    return [
        "docker", "run", "-i", "--rm", *flags,
        *[arg for mount in mounts for arg in ("-v", mount)],
        image,
    ]  # fmt: skip


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(parent: Path, name: str, *, commit_index: bool) -> Path:
    repo = parent / name
    (repo / ".code-atlas").mkdir(parents=True)
    (repo / "docs" / "onboarding").mkdir(parents=True)
    (repo / "a.php").write_text("<?php\nfunction f(): int { return 1; }\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "a.php")
    if commit_index:
        (repo / ".code-atlas" / "graph.db").write_bytes(b"not a database")
        _git(repo, "add", "-f", ".code-atlas")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    return repo


def _session(
    image: str,
    repo: Path,
    requests: list[dict[str, object]],
    extra_mounts: tuple[str, ...] = (),
    index_mount: bool = True,
) -> tuple[list[dict[str, object]], str]:
    """Send each request in turn, waiting for the answer to those with an ``id``.

    Returns (the answers in order, stderr). A server that exits or goes silent ends the
    conversation early, so a refusal shows as fewer answers than requests.
    """
    proc = subprocess.Popen(
        run_line(image, repo, extra_mounts=extra_mounts, index_mount=index_mount),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdin, stdout, stderr = proc.stdin, proc.stdout, proc.stderr
    assert stdin is not None and stdout is not None and stderr is not None
    lines: queue.Queue[str] = queue.Queue()

    def pump() -> None:
        for line in stdout:
            lines.put(line)
        lines.put("")  # EOF

    threading.Thread(target=pump, daemon=True).start()
    answers: list[dict[str, object]] = []
    try:
        for request in requests:
            stdin.write(json.dumps(request) + "\n")
            stdin.flush()
            if "id" not in request:
                continue
            while True:
                line = lines.get(timeout=TIMEOUT)
                if not line:
                    raise EOFError
                try:
                    reply = json.loads(line)
                except ValueError:
                    continue
                if isinstance(reply, dict) and reply.get("id") == request["id"]:
                    answers.append(reply)
                    break
    except (BrokenPipeError, EOFError, queue.Empty):  # the server's stderr says why
        pass
    try:
        stdin.close()
    except BrokenPipeError:
        pass
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    return answers, stderr.read()


def _call(rid: int, tool: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "method": "tools/call",
        "params": {"name": tool, "arguments": {}},
    }


INITIALIZED: dict[str, object] = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def _listing(repo: Path) -> dict[str, tuple[int, int]]:
    """Every repo file outside ``.git`` and ``.code-atlas`` as path -> (size, mtime_ns)."""
    found = {}
    for path in sorted(repo.rglob("*")):
        rel = path.relative_to(repo)
        if rel.parts[0] in (".git", ".code-atlas") or path.is_dir():
            continue
        stat = path.stat()
        found[rel.as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return found


def _failed_call(answers: list[dict[str, object]], tool: str, err: str) -> str | None:
    """Why the last answer is not a successful ``tools/call`` of ``tool``, else None."""
    if len(answers) < 2:
        return f"{tool}: no answer; stderr={err.strip()[-300:]!r}"
    result = answers[-1].get("result")
    if not isinstance(result, dict) or result.get("isError") or "error" in answers[-1]:
        return f"{tool} failed: {json.dumps(answers[-1])[:300]}"
    return None


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
    answers, err = _session(image, _repo(parent, "clean", commit_index=False), [INITIALIZE])
    if not answers:
        return f"no JSON answer to initialize; stderr={err.strip()[-300:]!r}"
    result = answers[0].get("result")
    info = result.get("serverInfo", {}) if isinstance(result, dict) else {}
    if not isinstance(info, dict) or not info.get("name"):
        return f"initialize answered without serverInfo: {json.dumps(answers[0])[:300]!r}"
    return None


def arm_tracked_index(image: str, parent: Path) -> str | None:
    answers, err = _session(image, _repo(parent, "tracked", commit_index=True), [INITIALIZE])
    if answers:
        return f"the server answered a repo that commits its index: {json.dumps(answers[0])[:200]}"
    if "tracked by git" not in err:
        return f"no refusal naming the tracked index; stderr={err.strip()[-300:]!r}"
    return None


def arm_build(image: str, parent: Path) -> str | None:
    repo = _repo(parent, "build", commit_index=False)
    before = _listing(repo)
    answers, err = _session(
        image, repo, [INITIALIZE, INITIALIZED, _call(2, "build_or_update_index")]
    )
    if problem := _failed_call(answers, "build_or_update_index", err):
        return problem
    if not (repo / ".code-atlas" / "graph.db").is_file():
        return "the build answered but wrote no .code-atlas/graph.db"
    if _listing(repo) != before:
        return "the build wrote outside .code-atlas/ in the read-only repo"
    return None


def arm_onboarding(image: str, parent: Path) -> str | None:
    repo = _repo(parent, "onboarding", commit_index=False)
    calls: list[dict[str, object]] = [
        INITIALIZE,
        INITIALIZED,
        _call(2, "build_or_update_index"),
        _call(3, "generate_onboarding"),
    ]
    answers, err = _session(image, repo, calls, extra_mounts=("docs/onboarding",))
    if len(answers) < 3:
        return f"generate_onboarding: no answer; stderr={err.strip()[-300:]!r}"
    if problem := _failed_call(answers, "generate_onboarding", err):
        return problem
    if not any((repo / "docs" / "onboarding").iterdir()):
        return "generate_onboarding answered but docs/onboarding/ is empty"
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
            ("index build writes only .code-atlas", lambda: arm_build(image, parent)),
            ("generate_onboarding with its mount", lambda: arm_onboarding(image, parent)),
        )
        failed = 0
        for name, arm in arms:
            problem = arm()
            print(f"{'FAIL' if problem else 'ok  '} {name}" + (f": {problem}" if problem else ""))
            failed += problem is not None
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
