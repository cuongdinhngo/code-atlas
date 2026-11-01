"""The runtime image: a fixed non-root user, digest-pinned bases, the documented run line (426).

Each arm reads the file it guards and fails on what it cannot classify (R6.5, R6.7): every
`FROM` and `COPY --from` of both Dockerfiles, every `.dockerignore` line, every fenced
`docker run` in the README. The planted cases at the end prove each parser refuses what a
file can lie with.
`scripts/container_smoke.py` is the runtime half: it runs the built image under `RUN_FLAGS`.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

from scripts.container_smoke import IMAGE_USER, RUN_FLAGS

REPO = Path(__file__).resolve().parent.parent
DOCKER = REPO / "docker"
RUNTIME = DOCKER / "Dockerfile.runtime"
PRUNED = {"node_modules", "vendor", ".venv", "venv", ".git", ".mango", ".pytest_cache"}


def find_dockerfiles(root: Path) -> list[Path]:
    """Every `Dockerfile*` under `root`, so a third image is read without a list to update."""
    found = []
    for here, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNED and not d.startswith("pytest-of-")]
        found += [Path(here) / n for n in names if n.startswith("Dockerfile")]
    return sorted(found)


DOCKERFILES = find_dockerfiles(REPO)
DIGEST = re.compile(r"^[^@\s:]+(?::[^@\s]+)?@sha256:[0-9a-f]{64}$")
TAGGED = re.compile(r"^[^@\s]+:[^@\s]+@sha256:[0-9a-f]{64}$")


def _instructions(text: str) -> list[str]:
    """Dockerfile instructions with continuations joined and comments and blanks dropped."""
    joined = re.sub(r"\\[ \t]*\n", " ", text)
    return [
        line.strip()
        for line in joined.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def pin_problems(text: str) -> list[str]:
    """Every `FROM` and `COPY --from` that is not a digest-pinned image or an earlier stage."""
    problems: list[str] = []
    stages: set[str] = set()
    for line in _instructions(text):
        word = line.split(None, 1)[0].upper()
        if word == "FROM":
            match = re.match(r"FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?\s*$", line, re.I)
            if not match:
                problems.append(f"unparsable FROM: {line}")
                continue
            image, name = match.groups()
            if image != "scratch" and image not in stages and not TAGGED.match(image):
                problems.append(f"FROM not pinned as <tag>@sha256:<digest>: {image}")
            if name:
                stages.add(name)
        elif word in ("COPY", "ADD"):
            for flag in re.findall(r"--from(?:=|\s+)(\S*)", line):
                if not flag:
                    problems.append(f"unparsable --from: {line}")
                elif flag not in stages and not DIGEST.match(flag):
                    problems.append(f"{word} --from not pinned by digest: {flag}")
    return problems


def test_the_dockerfile_walk_finds_both_known_images() -> None:
    assert {DOCKER / "Dockerfile", RUNTIME} <= set(DOCKERFILES)


def test_the_dockerfile_walk_finds_a_third_and_skips_vendored_trees(tmp_path: Path) -> None:
    for name in (
        "Dockerfile",
        "svc/Dockerfile.dev",
        "node_modules/x/Dockerfile",
        ".venv/Dockerfile",
    ):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("FROM python:3.12\n", encoding="utf-8")
    found = [p.relative_to(tmp_path).as_posix() for p in find_dockerfiles(tmp_path)]
    assert found == ["Dockerfile", "svc/Dockerfile.dev"]
    assert any(pin_problems(p.read_text("utf-8")) for p in find_dockerfiles(tmp_path))


def test_every_from_and_copy_from_is_pinned_by_digest() -> None:
    seen = 0
    for dockerfile in DOCKERFILES:
        text = dockerfile.read_text(encoding="utf-8")
        assert pin_problems(text) == [], dockerfile.name
        seen += len(re.findall(r"^\s*FROM\s", text, re.M | re.I))
    assert seen >= 3, "fewer FROM lines than the two Dockerfiles carry: the walk read nothing"


def test_every_dockerfile_that_runs_composer_gets_it_from_its_pinned_image() -> None:
    users = [d for d in DOCKERFILES if "composer install" in d.read_text("utf-8")]
    assert {DOCKER / "Dockerfile", RUNTIME} <= set(users)
    for dockerfile in users:
        assert re.search(r"COPY --from=composer:\S+@sha256:", dockerfile.read_text("utf-8"))


def test_no_piped_installer_anywhere_under_docker() -> None:
    files = [p for p in DOCKER.rglob("*") if p.is_file()]
    assert {DOCKER / "Dockerfile", RUNTIME} <= set(files)
    for path in files:
        for line in _instructions(path.read_text(encoding="utf-8")):
            assert not PIPED.search(line), f"{path.name}: a piped installer: {line}"


PIPED = re.compile(r"\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh|php|python3?)\b")


def _final_stage(text: str) -> list[str]:
    lines = _instructions(text)
    last = max(i for i, line in enumerate(lines) if line.split(None, 1)[0].upper() == "FROM")
    return lines[last:]


def test_the_runtime_image_ends_as_one_fixed_numeric_user() -> None:
    final = _final_stage(RUNTIME.read_text(encoding="utf-8"))
    users = [line.split(None, 1)[1] for line in final if line.split(None, 1)[0].upper() == "USER"]
    assert users, "the final stage never sets USER, so it runs as root"
    assert re.fullmatch(r"[1-9]\d*:[1-9]\d*", users[-1]), (
        f"not a fixed numeric uid:gid: {users[-1]}"
    )
    assert users[-1] == IMAGE_USER, "the smoke test and the Dockerfile name different users"
    uid, gid = users[-1].split(":")
    text = " ".join(final)
    assert f"--gid {gid}" in text and f"--uid {uid}" in text, "the user is never created"
    assert "ENV HOME=/tmp" in text, "git and Python need a writable HOME under --read-only"
    assert "git" in " ".join(line for line in final if "apt-get install" in line)
    assert final[-1].startswith("ENTRYPOINT"), "USER must precede, never follow, the entrypoint"


# --- the README holds the run line to RUN_FLAGS ---------------------------------------------------


def _fences(text: str) -> list[str]:
    return re.findall(r"```[a-z]*\n(.*?)```", text, re.S)


def run_line_problems(text: str) -> list[str]:
    """What each fenced `docker run` in `text` lacks: `RUN_FLAGS`, the `:ro` repo, the index."""
    runs = [b for b in _fences(text) if "docker run" in b or '"run"' in b]
    problems = (
        [] if len(runs) >= 2 else [f"{len(runs)} run line(s); want the shell one and .mcp.json"]
    )
    for block in runs:
        flat = re.sub(r'[\s",\\]+', " ", block)
        for flag in RUN_FLAGS:
            if flag.startswith("--") and flag not in flat:
                problems.append(f"missing {flag}")
        if "--tmpfs /tmp" not in flat:
            problems.append("missing `--tmpfs /tmp`")
        if ":/workspace:ro" not in flat:
            problems.append("repo not mounted read-only at /workspace")
        if ":/workspace/.code-atlas" not in flat:
            problems.append("no writable .code-atlas mount")
    return problems


def test_the_readme_run_line_carries_every_documented_flag() -> None:
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    section = readme.split("**In a container**")[1].split("</details>")[0]
    assert run_line_problems(section) == []
    assert "mkdir -p .code-atlas" in section


def test_the_dockerfile_header_points_at_the_run_line_instead_of_copying_it() -> None:
    header = RUNTIME.read_text(encoding="utf-8").splitlines()[:3]
    assert any(
        "README.md, *In a container*" in line and "container_smoke.py" in line for line in header
    )
    assert not any("--cap-drop" in line for line in header), "a third copy of the run line"


# --- context hygiene: .dockerignore and .gitignore ------------------------------------------------

PLANTED = (
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519.pub",
    "server.key",
    "cert.pem",
    "x.p12",
    "x.pfx",
    ".mcp.json",
    ".git/config",
    "adapters/php/.env",
    "deploy/server.key",
    "deploy/cert.pem",
    "sub/id_rsa",
    "sub/.mcp.json",
)
KEPT = ("README.md", ".git/HEAD", ".git/refs/remotes/origin/main", "docker/Dockerfile")


class Unclassifiable(ValueError):
    pass


def _glob(part: str) -> str:
    """One Go `filepath.Match` path component as a regex, never crossing a `/`."""
    out, i = "", 0
    while i < len(part):
        c = part[i]
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[":
            end = part.find("]", i + 2)
            if end < 0:
                raise Unclassifiable(part)
            body = part[i + 1 : end].replace("\\", "")
            if "-" in body:
                raise Unclassifiable(f"a character range is not modelled: {part}")
            out += "[" + ("^" if body.startswith("^") else "") + re.escape(body.lstrip("^")) + "]"
            i = end
        elif c == "\\":
            raise Unclassifiable(part)
        else:
            out += re.escape(c)
        i += 1
    return out


def dockerignore_matcher(text: str) -> re.Pattern[str]:
    """Docker's rules, minimally: a pattern excludes the path or a parent; `!` is refused."""
    alternatives = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            raise Unclassifiable(f"an exception line is not modelled: {line}")
        parts = [p for p in line.strip("/").split("/") if p not in ("", ".")]
        if not parts:
            raise Unclassifiable(line)
        regex = ""
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            if part == "**":
                regex += "(?:.*)" if last else "(?:[^/]+/)*"
            else:
                regex += _glob(part) + ("" if last else "/")
        alternatives.append(f"(?:{regex})")
    if not alternatives:
        raise Unclassifiable("no patterns")
    return re.compile(r"(?:" + "|".join(alternatives) + r")(?:/.*)?")


def excluded(text: str, path: str) -> bool:
    return dockerignore_matcher(text).fullmatch(path) is not None


def test_dockerignore_excludes_every_planted_secret_and_keeps_the_refs() -> None:
    text = (REPO / ".dockerignore").read_text(encoding="utf-8")
    assert [p for p in PLANTED if not excluded(text, p)] == []
    # The container gate's R7.3 check reads refs, so they must reach the image (323).
    assert [p for p in KEPT if excluded(text, p)] == []


def gitignore_misses(gitignore: str, paths: tuple[str, ...], tmp: Path) -> list[str]:
    subprocess.run(["git", "init", "-q", str(tmp)], check=True, capture_output=True)
    (tmp / ".gitignore").write_text(gitignore, encoding="utf-8")
    missed = []
    for path in paths:
        done = subprocess.run(
            ["git", "-C", str(tmp), "check-ignore", "--no-index", "-q", "--", path],
            capture_output=True,
        )
        if done.returncode == 1:
            missed.append(path)
        elif done.returncode != 0:
            raise AssertionError(f"git check-ignore failed on {path}: {done.stderr!r}")
    return missed


def test_gitignore_covers_every_planted_secret_but_the_git_config(tmp_path: Path) -> None:
    text = (REPO / ".gitignore").read_text(encoding="utf-8")
    secrets = tuple(p for p in PLANTED if not p.startswith(".git/"))
    assert gitignore_misses(text, secrets, tmp_path) == []


def test_gitignore_hides_no_tracked_file() -> None:
    done = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-ci", "--exclude-standard"],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == [], "a tracked file matches .gitignore"


# --- the CI job -----------------------------------------------------------------------------------


def _runtime_job() -> str:
    ci = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "\n  runtime-image:\n" in ci, "the runtime-image job is gone or renamed"
    body = ci.split("\n  runtime-image:\n")[1]
    return re.split(r"\n  [a-z][a-z-]*:\n", body)[0]


def test_the_ci_job_builds_smokes_and_scans_without_pushing() -> None:
    job = "\n".join(
        line for line in _runtime_job().splitlines() if not line.lstrip().startswith("#")
    )
    assert "file: docker/Dockerfile.runtime" in job and "load: true" in job
    assert "push: false" in job and "push: true" not in job
    assert not re.search(r"docker (push|login)|registry|ghcr|packages: write", job)
    assert "python3 scripts/container_smoke.py" in job
    scan = job.split("anchore/scan-action@")[1].split("\n      - ")[0]
    assert re.match(r"[0-9a-f]{40}\s", scan), "the scan action is not pinned by full SHA"
    for setting in ("fail-build: true", "severity-cutoff: critical", "only-fixed: true"):
        assert setting in scan, setting
    assert "contents: read" in job
    assert not re.search(r":\s*write\b|write-all", job), "the job grants more than read"
    assert job.index("container_smoke.py") < job.index("anchore/scan-action")


# --- the guards themselves, each seen refusing what it exists to refuse (R6.5) --------------------

PY = "python:3.12-slim-bookworm@sha256:" + "a" * 64


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("FROM python:3.12-slim-bookworm\n", "not pinned"),
        (f"FROM {PY} AS a\nFROM python:3.12\nUSER 1:1\n", "not pinned"),
        (f"FROM {PY} AS a\nFROM {PY}\nCOPY --from=composer:2 /x /y\n", "--from not pinned"),
        (f"FROM {PY}\nCOPY --from= /x /y\n", "unparsable --from"),
        (f"FROM {PY} AS a\nFROM {PY}\nCOPY --from=a /x /y\nCOPY --from=0 /x /y\n", "--from not"),
        ("FROM\n", "unparsable FROM"),
    ],
)
def test_the_pin_walk_refuses_what_it_should(text: str, needle: str) -> None:
    assert any(needle in p for p in pin_problems(text)), pin_problems(text)


def test_the_pin_walk_accepts_a_pinned_multistage_file() -> None:
    composer = f"composer:2@sha256:{'b' * 64}"
    text = f"FROM {PY} AS a\nFROM {PY}\nCOPY --from=a /x /y\nCOPY --from={composer} /c /c\n"
    assert pin_problems(text) == []


@pytest.mark.parametrize(
    "line",
    [
        "RUN curl -sS https://x.example/installer | php",
        "RUN wget -qO- https://x.example/i.sh | sh",
        "RUN curl -fsSL https://x.example | sudo bash",
    ],
)
def test_the_piped_installer_pattern_catches_each_shape(line: str) -> None:
    assert PIPED.search(line)
    assert not PIPED.search("RUN curl -o /tmp/x https://x.example && sha256sum -c /tmp/x.sum")


def test_the_dockerignore_matcher_refuses_a_line_it_cannot_place() -> None:
    for bad in ("!keep.txt\n", "a\\*b\n", "[abc\n", "*.[a-z]\n", "# only a comment\n"):
        with pytest.raises(Unclassifiable):
            dockerignore_matcher(bad)


def test_the_dockerignore_matcher_follows_dockers_depth_rules() -> None:
    assert excluded("*.pem\n", "cert.pem") and not excluded("*.pem\n", "deploy/cert.pem")
    assert excluded("**/*.pem\n", "deploy/cert.pem") and excluded("**/*.pem\n", "cert.pem")
    assert excluded(".git/config\n", ".git/config") and not excluded(".git/config\n", ".git/HEAD")
    assert excluded("build\n", "build/lib/x.py") and not excluded("build\n", "src/build")
    assert excluded("id_rsa*\n", "id_rsa.pub")


def test_the_hygiene_checks_fail_on_a_planted_gap(tmp_path: Path) -> None:
    assert gitignore_misses(".venv/\n", (".env", "server.key"), tmp_path) == [".env", "server.key"]
    assert not excluded("# nothing\n.venv\n", ".env")


def test_the_run_line_check_fails_on_a_dropped_flag() -> None:
    flags = " ".join(f for f in RUN_FLAGS if f != "--network=none")
    mounts = "-v r:/workspace:ro -v r/.code-atlas:/workspace/.code-atlas i"
    block = f"```bash\ndocker run -i --rm {flags} --tmpfs /tmp {mounts}\n```\n"
    assert any("--network=none" in p for p in run_line_problems(block + block))
    assert run_line_problems("no code here") != []
