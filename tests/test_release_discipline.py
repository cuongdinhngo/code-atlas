"""Task 348 — an installed code-atlas can tell it is outdated.

A release is the package version plus the contract and schema it ships, named by the changelog's top
heading. A version bump that forgets the changelog, or a contract bump that forgets the version,
goes red here. The state hook then reports a plugin/package skew from that same version, offline.

431 adds the release pipeline's guards: a signed tag from `SIGNED_FROM` on, an advisory release
that carries its `Security` section, the `Release` workflow's shape, and `release_notes`.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from code_atlas import build_info, contract
from code_atlas.hooks import state
from code_atlas.store import SCHEMA_VERSION

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402
import release_notes  # noqa: E402

from tests.test_ci_hardening import load  # noqa: E402
from tests.test_ci_hardening import problems as workflow_problems  # noqa: E402

HEADING = re.compile(r"^## (\S+) — (\d{4}-\d{2}-\d{2}) · contract (\d+) · schema (\d+)$", re.M)
REBUILD_FLAG = "**Full rebuild required.**"


def _version() -> str:
    return str(tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["version"])


def release_drift(changelog: str, version: str, contract_version: int, schema: str) -> list[str]:
    """Every way the top changelog entry disagrees with the code it claims to describe."""
    entries = HEADING.findall(changelog)
    if not entries:
        return ["CHANGELOG.md has no release heading"]
    top, *older = entries
    drift = []
    if top[0] != version:
        drift.append(f"top entry is {top[0]}, pyproject says {version} — add a release entry")
    if (int(top[2]), top[3]) != (contract_version, schema):
        drift.append(
            f"release {top[0]} names contract {top[2]} · schema {top[3]}, the code is "
            f"contract {contract_version} · schema {schema} — bump the version and add an entry"
        )
    if older and (top[2], top[3]) != (older[0][2], older[0][3]):
        # The top release's own body: an *Unreleased* section may sit above it (381).
        start = HEADING.search(changelog)
        body = changelog[start.end() :].split("\n## ", 1)[0] if start else ""
        if REBUILD_FLAG not in body:
            drift.append(f"release {top[0]} moves contract/schema but does not flag a rebuild")
    return drift


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.mark.xfail(_version() == "0.11.0", strict=True, reason="v0.11.0 not yet tagged (446)")
def test_the_top_release_is_tagged() -> None:
    """381 AC3: a release is a tagged `vX.Y.Z`; commits after it are not a newer release."""
    top = HEADING.findall((REPO / "CHANGELOG.md").read_text(encoding="utf-8"))[0][0]
    assert _git("rev-parse", "--is-shallow-repository") == "false", "fetch tags: fetch-depth 0"
    assert _git("tag", "--list", f"v{top}") == f"v{top}", (
        f"CHANGELOG's top release {top} has no tag — `git tag v{top} <commit>` and push it"
    )


def test_the_top_release_is_the_code_that_ships() -> None:
    """348 AC1: version, contract and schema agree with the changelog's newest release."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_drift(changelog, _version(), contract.CONTRACT_VERSION, SCHEMA_VERSION) == []


@pytest.mark.parametrize(
    ("contract_version", "schema", "version"),
    [
        (contract.CONTRACT_VERSION + 1, SCHEMA_VERSION, None),  # contract bumped, version not
        (contract.CONTRACT_VERSION, str(int(SCHEMA_VERSION) + 1), None),  # schema bumped
        (contract.CONTRACT_VERSION, SCHEMA_VERSION, "9.9.9"),  # version bumped, no entry
    ],
)
def test_a_drifted_release_goes_red(
    contract_version: int, schema: str, version: str | None
) -> None:
    """R6.5: the same check fails on each drift it exists to catch."""
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_drift(changelog, version or _version(), contract_version, schema)


def test_an_era_move_without_the_rebuild_flag_goes_red() -> None:
    older = "## 0.1.0 — 2026-01-01 · contract 12 · schema 6\n\n- x\n"
    newer = "## 0.2.0 — 2026-02-01 · contract 13 · schema 6\n\n- y\n"
    assert release_drift(f"# C\n\n{newer}\n{older}", "0.2.0", 13, "6")
    flagged = newer.replace("- y", f"- {REBUILD_FLAG} x")
    assert release_drift(f"# C\n\n{flagged}\n{older}", "0.2.0", 13, "6") == []


def test_every_generated_hook_table_expects_this_release() -> None:
    """348 AC2 wiring: both hook tables carry the package version and contract (344, 374)."""
    for path in (gen_skill.CLAUDE_CODE_SNIPPET_PATH, gen_skill.PLUGIN_HOOKS_PATH):
        hooks = json.loads(path.read_text(encoding="utf-8"))["hooks"]
        commands = [h["command"] for e in hooks["SessionStart"] for h in e["hooks"]]
        expect = (
            f"code-atlas-state {state.EXPECT_CONTRACT_FLAG} {contract.CONTRACT_VERSION}"
            f" {state.EXPECT_FLAG} {_version()}"
        )
        assert any(c.endswith(expect) for c in commands), (path.name, commands)


@pytest.mark.parametrize(
    ("installed", "expected", "fix"),
    [
        ("0.1.0", "0.2.0", state.tool_step("0.2.0")),  # the tool install lags the plugin
        ("0.3.0", "0.2.0", state.plugin_step("0.3.0")),  # the plugin lags the tool install
    ],
)
def test_a_skew_names_both_releases_and_the_side_to_move(
    monkeypatch: pytest.MonkeyPatch, installed: str, expected: str, fix: str
) -> None:
    monkeypatch.setattr(build_info, "package_version", lambda: installed)
    line = state.skew_line(expected)
    assert line == (
        f"{state.PREFIX}hooks expect code-atlas {expected} but {installed} is installed — run {fix}"
    )


@pytest.mark.parametrize("installed", ["0.2.0", build_info.UNKNOWN_VERSION])
def test_no_skew_line_when_they_match_or_the_version_is_unknown(
    monkeypatch: pytest.MonkeyPatch, installed: str
) -> None:
    monkeypatch.setattr(build_info, "package_version", lambda: installed)
    assert state.skew_line("0.2.0") is None
    assert state.skew_line(None) is None


def _plugin_state_command(version: str) -> str:
    hooks = json.loads(gen_skill.PLUGIN_HOOKS_PATH.read_text(encoding="utf-8"))["hooks"]
    (command,) = [
        h["command"]
        for e in hooks["SessionStart"]
        for h in e["hooks"]
        if gen_skill.ungate(h["command"]).startswith("code-atlas-state ")
    ]
    return command.replace(f"{state.EXPECT_FLAG} {_version()}", f"{state.EXPECT_FLAG} {version}")


def _run_plugin_hook(project: Path, version: str) -> subprocess.CompletedProcess[str]:
    """The plugin's own SessionStart command, the installed console script, a real payload."""
    bin_dir = str(Path(sys.executable).parent)
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    return subprocess.run(
        ["bash", "-c", _plugin_state_command(version)],
        input=json.dumps({"hook_event_name": "SessionStart", "source": "startup"}),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_plugin_hook_names_a_skew_against_the_installed_package(tmp_path: Path) -> None:
    """348 AC2: a plugin one release behind the installed package prints the skew line."""
    installed = build_info.package_version()
    project = tmp_path / "project"
    (project / ".code-atlas").mkdir(parents=True)
    (project / ".code-atlas" / "graph.db").write_bytes(b"not a real index")
    done = _run_plugin_hook(project, "0.0.1")
    assert done.returncode == 0
    assert f"hooks expect code-atlas 0.0.1 but {installed} is installed" in done.stdout
    same = _run_plugin_hook(project, installed)
    assert "hooks expect" not in same.stdout


def test_the_plugin_hook_is_silent_with_no_index(tmp_path: Path) -> None:
    """348 AC2: the 344 gate still holds, skew or not."""
    project = tmp_path / "project"
    project.mkdir()
    done = _run_plugin_hook(project, "0.0.1")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


# ---- 431: the release pipeline ---------------------------------------------------------------

SIGNED_FROM = (0, 10, 0)
SIGNERS = REPO / ".github" / "allowed_signers"
RELEASE_WORKFLOW = REPO / ".github" / "workflows" / "release.yml"
GHSA = re.compile(r"GHSA(?:-[2-9cfghjmpqrvwx]{4}){3}")
FINAL_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
BASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)")


def _git_env(home: Path | None = None) -> dict[str, str]:
    """git with no user or system config, so a signing key never leaks in from the host."""
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com")
    env.update(GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
    if home:
        env["HOME"] = str(home)
    return env


def unverified_tags(repo: Path, signers: Path, env: dict[str, str] | None = None) -> list[str]:
    """Every `v*` tag from SIGNED_FROM on that `git verify-tag` refuses against ``signers``."""
    env = env or _git_env()
    tags = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    ).stdout.split()
    bad = []
    for tag in tags:
        base = BASE_TAG.match(tag)
        if not base or tuple(int(g) for g in base.groups()) < SIGNED_FROM:
            continue
        check = subprocess.run(
            ["git", "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={signers}"]
            + ["verify-tag", tag],
            cwd=repo,
            capture_output=True,
            text=True,
            env=env,
        )
        if check.returncode != 0:
            bad.append(tag)
    return bad


def _signed_range_tags() -> list[str]:
    tags = _git("tag", "--list", "v*").split()
    return [
        t
        for t in tags
        if (m := BASE_TAG.match(t)) and tuple(int(g) for g in m.groups()) >= SIGNED_FROM
    ]


def test_every_release_tag_from_the_signing_release_is_signed_by_an_allowed_key() -> None:
    """431 H5: 0.9.1 and earlier are unsigned history; from SIGNED_FROM a tag must verify."""
    in_range = _signed_range_tags()
    if not in_range:
        return
    assert SIGNERS.is_file(), (
        f"{sorted(in_range)} exist but .github/allowed_signers does not;"
        " see docs/runbooks/releasing.md"
    )
    assert unverified_tags(REPO, SIGNERS) == []


def _keypair(directory: Path, name: str) -> Path:
    assert shutil.which("ssh-keygen"), "ssh-keygen (openssh-client) is needed to plant a signed tag"
    key = directory / name
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", name, "-f", str(key)], check=True
    )
    return key


def _signers_file(path: Path, *keys: Path) -> Path:
    lines = [f"{k.name}@example.com {k.with_suffix('.pub').read_text().strip()}" for k in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _planted_repo(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _git_env(tmp_path)
    for args in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "x"]):
        subprocess.run(["git", *args], cwd=repo, check=True, env=env)
    return repo, env


def _tag(repo: Path, env: dict[str, str], name: str, *, key: Path | None, annotated: bool) -> None:
    args = ["git", "-c", "gpg.format=ssh"]
    if key:
        args += ["-c", f"user.signingkey={key}", "tag", "-s", name, "-m", name]
    else:
        args += ["tag", *(["-a", name, "-m", name] if annotated else [name])]
    subprocess.run(args, cwd=repo, check=True, env=env)


def test_a_tag_not_signed_by_an_allowed_key_goes_red(tmp_path: Path) -> None:
    """R6.5: a signed tag passes; unsigned, lightweight and foreign-key tags each fail."""
    repo, env = _planted_repo(tmp_path)
    ours, theirs = _keypair(tmp_path, "ours"), _keypair(tmp_path, "theirs")
    signers = _signers_file(tmp_path / "signers", ours)
    _tag(repo, env, "v0.10.0", key=ours, annotated=True)
    assert unverified_tags(repo, signers, env) == []
    _tag(repo, env, "v0.10.1", key=None, annotated=True)
    _tag(repo, env, "v0.10.2", key=None, annotated=False)
    _tag(repo, env, "v0.10.3", key=theirs, annotated=True)
    _tag(repo, env, "v0.9.9", key=None, annotated=False)  # before SIGNED_FROM: history, ignored
    assert unverified_tags(repo, signers, env) == ["v0.10.1", "v0.10.2", "v0.10.3"]


# ---- advisory releases (SEC-GV-02, H6) --------------------------------------------------------


def _security_section(body: str) -> str:
    found = re.search(r"^### Security\n(.*?)(?=^### |\Z)", body, re.M | re.S)
    return found.group(1) if found else ""


def advisory_drift(changelog: str, fixes: dict[str, str | None]) -> list[str]:
    """Each advisory's first release must carry a `### Security` section that names it.

    ``fixes`` maps a GHSA to the version of the earliest release containing its fix, or None
    while it is unreleased (nothing to check yet).
    """
    drift = []
    for ghsa, version in sorted(fixes.items()):
        if version is None:
            continue
        body = release_notes.entry(changelog, version)
        if body is None:
            drift.append(f"{ghsa}: release {version} has no CHANGELOG entry")
        elif ghsa not in _security_section(body):
            drift.append(f"{ghsa}: release {version} has no `### Security` section naming it")
    return drift


def advisory_fixes(repo: Path = REPO) -> dict[str, str | None]:
    """Read from git: ledger GHSA -> commit that added it -> earliest final tag containing it."""
    ledger = (repo / "docs" / "TOKEN_LEDGER.md").read_text(encoding="utf-8")
    fixes: dict[str, str | None] = {}
    for ghsa in sorted(set(GHSA.findall(ledger))):
        added = _git("log", "--reverse", "--format=%H", "-S", ghsa, "--", "docs/TOKEN_LEDGER.md")
        first = added.split()[0] if added else None
        tags = _git("tag", "--contains", first, "--list", "v*").split() if first else []
        finals = sorted(
            (tuple(int(g) for g in m.groups()), t[1:]) for t in tags if (m := FINAL_TAG.match(t))
        )
        fixes[ghsa] = finals[0][1] if finals else None
    return fixes


def test_every_release_that_fixed_an_advisory_names_it_under_security() -> None:
    """SEC-GV-02: derived from the ledger and the tags, never from a list kept here (R6.7)."""
    fixes = advisory_fixes()
    assert fixes, "the ledger links no GHSA; the reader is broken"
    assert advisory_drift((REPO / "CHANGELOG.md").read_text(encoding="utf-8"), fixes) == []


CHANGELOG_PLANT = """# C

## 0.2.0 — 2026-02-01 · contract 1 · schema 1

### Security

Fixes GHSA-aaaa-bbbb-cccc.

## 0.1.0 — 2026-01-01 · contract 1 · schema 1

- x
"""


@pytest.mark.parametrize(
    ("fixes", "named"),
    [
        ({"GHSA-aaaa-bbbb-cccc": "0.1.0"}, "no `### Security` section"),  # the release has none
        ({"GHSA-dddd-eeee-ffff": "0.2.0"}, "no `### Security` section naming it"),  # another's
        ({"GHSA-aaaa-bbbb-cccc": "0.3.0"}, "no CHANGELOG entry"),  # tagged, never written up
    ],
)
def test_a_release_without_a_security_section_goes_red(fixes: dict[str, str], named: str) -> None:
    assert any(named in line for line in advisory_drift(CHANGELOG_PLANT, fixes))
    assert advisory_drift(CHANGELOG_PLANT, {"GHSA-aaaa-bbbb-cccc": "0.2.0"}) == []
    assert advisory_drift(CHANGELOG_PLANT, {"GHSA-aaaa-bbbb-cccc": None}) == []


# ---- the Release workflow (431 H1-H3, H7) -----------------------------------------------------


def release_shape(text: str) -> list[str]:
    """Everything wrong with the Release workflow's shape, beyond the repo-wide hardening."""
    doc = load(text)
    jobs = doc.get("jobs") or {}
    found = [f"[hardening] {p}" for p in workflow_problems(text)]
    if doc.get("on") != {"push": {"tags": ["v*"]}}:
        found.append("must trigger on a `v*` tag push and nothing else")
    build, publish = jobs.get("build") or {}, jobs.get("publish") or {}
    steps = [s for s in build.get("steps") or [] if isinstance(s, dict)]
    runs = [str(s.get("run", "")) for s in steps]
    if any(v == "write" for v in (build.get("permissions") or {}).values()):
        found.append("build holds a write scope")
    verify = next((i for i, r in enumerate(runs) if "verify-tag" in r), None)
    building = next((i for i, r in enumerate(runs) if "uv build" in r), None)
    if verify is None or building is None or verify > building:
        found.append("the tag signature must be verified before anything is built")
    if not any("git show origin/main:.github/allowed_signers" in r and "exit 1" in r for r in runs):
        found.append("the signers file must come from main, and its absence must fail the job")
    if any("allowedSignersFile=.github/" in r for r in runs):
        found.append("verify-tag trusts the tag's own tree; read the signers file from main")
    if not any('merge-base --is-ancestor "$GITHUB_SHA" origin/main' in r for r in runs):
        found.append("the tagged commit is never checked to be on main")
    if not any("release_notes.py check" in r for r in runs):
        found.append("tag, pyproject and CHANGELOG are never checked to agree")
    psteps = [s for s in publish.get("steps") or [] if isinstance(s, dict)]
    uses = [str(s.get("uses", "")) for s in psteps]
    if any(u.startswith("actions/checkout@") for u in uses):
        found.append("publish checks out the repo, so it would run repo code with write scopes")
    if publish.get("needs") != "build":
        found.append("publish must need build")
    scopes = publish.get("permissions") or {}
    for need in ("contents", "id-token", "attestations"):
        if scopes.get(need) != "write":
            found.append(f"publish lacks {need}: write")
    for action in ("attest-build-provenance", "attest-sbom", "download-artifact"):
        if not any(f"actions/{action}@" in u for u in uses):
            found.append(f"publish does not use actions/{action}")
    provenance = next((s for s in psteps if "attest-build-provenance" in str(s.get("uses"))), {})
    subjects = str((provenance.get("with") or {}).get("subject-path", ""))
    if not ("release/*.whl" in subjects and "release/*.tar.gz" in subjects):
        found.append("provenance must cover the wheel and the sdist the Release carries")
    if not any("--verify-tag" in str(s.get("run", "")) for s in psteps):
        found.append("the Release is not created with --verify-tag")
    return found


def test_the_release_workflow_has_the_shape_the_standard_names() -> None:
    assert release_shape(RELEASE_WORKFLOW.read_text(encoding="utf-8")) == []


def _release_variants() -> dict[str, str]:
    good = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    def swap(old: str, new: str) -> str:
        assert old in good, old
        return good.replace(old, new, 1)

    keep = "      - name: Keep the release files"
    extra = "      - run: git verify-tag v0\n"
    checkout = "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
    return {
        "a branch trigger": swap('    tags:\n      - "v*"', "    branches:\n      - main"),
        "a write scope in build": swap(
            "    timeout-minutes: 20\n    permissions:\n      contents: read",
            "    timeout-minutes: 20\n    permissions:\n      contents: write",
        ),
        "no tag verification": swap("verify-tag", "describe"),
        "verify after build": swap('verify-tag "$GITHUB_REF_NAME"', "describe").replace(
            keep, extra + keep
        ),
        "a signers guard removed": swap(
            "git show origin/main:.github/allowed_signers", "git show origin/main:.github/other"
        ),
        "signers read from the tag's tree": swap(
            'allowedSignersFile="$RUNNER_TEMP/allowed_signers"',
            "allowedSignersFile=.github/allowed_signers",
        ),
        "a tag off main": swap(
            'merge-base --is-ancestor "$GITHUB_SHA" origin/main', "rev-parse HEAD"
        ),
        "provenance misses the sdist": swap("            release/*.tar.gz\n\n", "\n"),
        "no agreement check": swap("release_notes.py check", "release_notes.py notes"),
        "a checkout in publish": swap(
            "    steps:\n      # The download",
            "    steps:\n" + checkout + "        with:\n          persist-credentials: false\n"
            "      # The download",
        ),
        "no provenance": swap("actions/attest-build-provenance@", "actions/attest-sbom@"),
        "a release no one verified": swap("--verify-tag", "--draft"),
        "a moved action": swap(
            "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2",
            "actions/upload-artifact@v7",
        ),
    }


@pytest.mark.parametrize("case", sorted(_release_variants()))
def test_a_release_workflow_that_breaks_the_shape_goes_red(case: str) -> None:
    """R6.5: each rule in `release_shape` is seen failing on a workflow that breaks only it."""
    assert release_shape(_release_variants()[case]), f"{case} was accepted"


# ---- release_notes (431 H4) -------------------------------------------------------------------

UNRELEASED = "## Unreleased\n\n- y\n\n"


def test_release_notes_reads_the_entry_for_a_version() -> None:
    changelog = CHANGELOG_PLANT.replace("## 0.2.0", UNRELEASED + "## 0.2.0")
    assert release_notes.top_version(changelog) == "0.2.0"
    body = release_notes.entry(changelog, "0.2.0")
    assert body and "GHSA-aaaa-bbbb-cccc" in body and "- x" not in body and "- y" not in body
    assert release_notes.entry(changelog, "0.1.0") == "- x"
    assert release_notes.entry(changelog, "9.9.9") is None


def test_the_real_changelog_has_an_entry_for_the_top_release() -> None:
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    assert release_notes.disagreements(f"v{_version()}", _version(), changelog) == []
    assert release_notes.entry(changelog, _version())


@pytest.mark.parametrize(
    ("tag", "version", "named"),
    [
        ("v0.2.1", "0.2.0", "tag is v0.2.1"),
        ("v0.3.0", "0.3.0", "top entry is 0.2.0"),
        ("v0.2.0", "0.2.0", None),
    ],
)
def test_a_tag_pyproject_and_changelog_that_disagree_go_red(
    tag: str, version: str, named: str | None
) -> None:
    drift = release_notes.disagreements(tag, version, CHANGELOG_PLANT)
    assert (named is None and drift == []) or any(named in d for d in drift or [""])


def test_an_empty_entry_is_not_a_release() -> None:
    top = "## 0.2.0 — 2026-02-01 · contract 1 · schema 1\n\n"
    changelog = top + "## 0.1.0 — 2026-01-01 · contract 1 · schema 1\n\n- x\n"
    assert any("empty" in d for d in release_notes.disagreements("v0.2.0", "0.2.0", changelog))


@pytest.mark.parametrize(
    ("version", "pre"),
    [
        ("0.10.0", False),
        ("1.0.0", False),
        ("0.10.0a1", True),
        ("0.10.0b2", True),
        ("0.10.0rc1", True),
        ("0.10.0.dev3", True),
    ],
)
def test_a_pep440_prerelease_is_named_so(version: str, pre: bool) -> None:
    assert release_notes.is_prerelease(version) is pre


def test_release_notes_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG_PLANT, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n', encoding="utf-8")
    assert release_notes.main(["check", "v0.2.0"], tmp_path) == 0
    assert release_notes.main(["check", "v0.2.1"], tmp_path) == 1
    assert "RELEASE MISMATCH" in capsys.readouterr().out
    assert release_notes.main(["notes", "0.1.0"], tmp_path) == 0
    assert capsys.readouterr().out.strip() == "- x"
    assert release_notes.main(["notes", "9.9.9"], tmp_path) == 1
    assert release_notes.main(["prerelease", "0.3.0rc1"], tmp_path) == 0
    assert release_notes.main(["prerelease", "0.3.0"], tmp_path) == 1
    assert release_notes.main(["bogus"], tmp_path) == 2
