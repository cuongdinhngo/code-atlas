"""430 — the indexed repo cannot exhaust code-atlas or reach past it.

One arm per limit, each on a tiny temp repo and each seen failing on the pre-430 code (R6.5).
Names that only exist after 430 are imported inside the arm that needs them, so one arm going
red never takes the module down with it.
"""

from __future__ import annotations

import json
import os
import shlex
import sqlite3
import stat
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from code_atlas import gitutil
from code_atlas.adapter import AdapterError, SubprocessAdapter
from code_atlas.architecture_rules import load_architecture_rules
from code_atlas.config import ConfigError, load_config
from code_atlas.enrichment import load_indirection_rules
from code_atlas.indexer import (
    _adapter,
    _digest,
    collect_stubs,
    file_is_current,
    full_build,
    reparse_file,
)
from code_atlas.onboarding.artifact import CACHE_DIR, CACHE_NAME
from code_atlas.store import GraphStore
from code_atlas.tools import generate_onboarding
from code_atlas.tools.build_or_update_index import create as build_tool
from code_atlas.tools.collection import collection_field
from code_atlas.tools.freshness import FreshnessGuard
from tests.test_guided_tour import _cycle_repo

REPO = Path(__file__).resolve().parent.parent
FAKE = REPO / "tests" / "fixtures" / "adapter" / "fake_adapter.py"
SOURCE = "class Thing {}\n"
OUTSIDE = "class Secret {}\n"
posix_only = pytest.mark.skipif(os.name == "nt", reason="symlinks and modes are POSIX here")


def _cmd(mode: str = "ok") -> str:
    return shlex.join([sys.executable, str(FAKE), mode])


def _env(**extra: str) -> dict[str, str]:
    return {"CA_WORKERS": "1", "CA_FAKE_CMD": _cmd(), **extra}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """A committed git repo holding ``files``."""
    root = tmp_path / "repo"
    for name, body in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(body, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _watch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A log of every path an adapter is asked for; the adapter inherits it through `CA_*`."""
    log = tmp_path / "paths.log"
    monkeypatch.setenv("CA_FAKE_PATHLOG", str(log))
    return log


def _paths_seen(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").split() if log.exists() else []


# ------------------------------------------------------------ AC1: size cap


def test_an_oversize_file_is_skipped_counted_and_never_sent_to_an_adapter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red before 430: `src/big.aa` was handed to the adapter and indexed whole."""
    root = _repo(tmp_path, {"src/small.aa": SOURCE, "src/big.aa": SOURCE + "# pad\n" * 100})
    log = _watch(tmp_path, monkeypatch)
    config = load_config(root, _env(CA_MAX_FILE_BYTES="200"))
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        indexed = set(store.file_paths())
        block = collection_field(store)
    assert indexed == {"src/small.aa"}
    assert _paths_seen(log) == ["src/small.aa"]
    assert block is not None
    skipped = block["skipped"]
    assert isinstance(skipped, dict) and skipped["oversize"] == 1
    # The census still closes: collected - skipped = kept.
    assert block["collected"] == 2 and block["kept"] == 1


def test_the_build_summary_names_the_oversize_count(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"src/small.aa": SOURCE, "src/big.aa": SOURCE + "# pad\n" * 100})
    config = load_config(root, _env(CA_MAX_FILE_BYTES="200"))
    payload = build_tool(config)(full=True)
    assert payload["collection"]["skipped"]["oversize"] == 1  # type: ignore[index]


def test_the_cap_defaults_to_four_mib_and_a_project_file_is_held_to_sixty_four() -> None:
    from code_atlas.limits import DEFAULT_MAX_FILE_BYTES, MAX_FILE_BYTES_CEILING

    assert DEFAULT_MAX_FILE_BYTES == 4 * 1024 * 1024
    assert MAX_FILE_BYTES_CEILING == 64 * 1024 * 1024


def test_the_default_and_the_clamp_of_the_file_cap(tmp_path: Path) -> None:
    assert load_config(tmp_path, {}).max_file_bytes == 4_194_304
    (tmp_path / ".code-atlas.toml").write_text("max_file_bytes = 999999999999\n", encoding="utf-8")
    assert load_config(tmp_path, {}).max_file_bytes == 64 * 1024 * 1024
    # The operator's environment is not the repo's word, so it is not clamped.
    assert load_config(tmp_path, {"CA_MAX_FILE_BYTES": "999999999999"}).max_file_bytes == (
        999_999_999_999
    )


def test_read_through_repair_will_not_parse_an_oversize_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that grew past the cap since the build is not re-parsed to answer a read."""
    root = _repo(tmp_path, {"src/a.aa": SOURCE})
    log = _watch(tmp_path, monkeypatch)
    config = load_config(root, _env(CA_MAX_FILE_BYTES="200"))
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        (root / "src" / "a.aa").write_text(SOURCE + "# pad\n" * 100, encoding="utf-8")
        before = _paths_seen(log)
        assert before == ["src/a.aa"]
        assert reparse_file(config, store, "src/a.aa") is False
        assert FreshnessGuard(config, store).ensure("src/a.aa") == "stale"
    assert _paths_seen(log) == before


# ------------------------------------------------------------ AC1: reply cap


def test_a_reply_line_over_the_cap_fails_that_file_and_the_adapter_is_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red before 430: the 50 KB line was read whole and its nodes indexed."""
    monkeypatch.setattr("code_atlas.adapter.MAX_REPLY_BYTES", 2000, raising=False)
    boots = tmp_path / "boots.log"
    monkeypatch.setenv("CA_FAKE_BOOTLOG", str(boots))
    with SubprocessAdapter("fake", (sys.executable, str(FAKE), "ok"), tmp_path) as adapter:
        huge = adapter.parse("huge/h.aa")
        after = adapter.parse("src/b.aa")
    assert not huge.ok and "over 2000 bytes" in str(huge.error)
    assert after.ok, "the stream was left mid-line, so the next file read the tail of the last"
    assert len(boots.read_text(encoding="utf-8").split()) == 2


def test_an_oversize_reply_costs_one_file_not_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("code_atlas.adapter.MAX_REPLY_BYTES", 2000, raising=False)
    root = _repo(tmp_path, {"huge/h.aa": SOURCE, "src/a.aa": SOURCE, "src/b.aa": SOURCE})
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        report = full_build(config, store)
    assert (report.parsed, report.failed) == (2, 1)


# ------------------------------------------------------------ AC2: regex limit

REFUSED = ["(a+)+$", "(.*)*", r"(\w)\1", "a" * 513]
ACCEPTED = [r"^get[A-Z]\w+$", r"(?:ab)*c", r"action=(\w+)"]


def _rules(tmp_path: Path, variable: str, body: dict[str, Any]):
    (tmp_path / "rules.json").write_text(json.dumps(body), encoding="utf-8")
    return load_config(tmp_path, {variable: "rules.json"})


def _architecture(pattern: str) -> dict[str, Any]:
    rule = {
        "id": "gate-rule",
        "sources": ["a/**"],
        "kind": "Method",
        "name": pattern,
        "required": ["\\X::y"],
        "kinds": ["CALLS"],
        "depth": 2,
    }
    return {"rules": [rule]}


def _keyed(pattern: str) -> dict[str, Any]:
    rule = {"setter": "post", "key_arg": 1, "key_pattern": pattern, "target_template": "X::{key}"}
    return {"keyed_calls": [rule]}


def _template(pattern: str) -> dict[str, Any]:
    rule = {"files": ["*.php"], "pattern": pattern, "target_template": "{path}"}
    return {"template_refs": [rule]}


# site -> (variable, rule body, loader, what the refusal must name, patterns that must load)
SITES = {
    "architecture-rule-name": (
        "CA_ARCHITECTURE_RULES",
        _architecture,
        load_architecture_rules,
        "gate-rule",
        ACCEPTED,
    ),
    "key_pattern": (
        "CA_INDIRECTION_RULES",
        _keyed,
        load_indirection_rules,
        "key_pattern",
        [r"action=(\w+)"],
    ),
    "template-rule-pattern": (
        "CA_INDIRECTION_RULES",
        _template,
        load_indirection_rules,
        "template_refs",
        [r"x(?P<m>\w+)"],
    ),
}


@pytest.mark.parametrize("pattern", REFUSED, ids=["nested", "star-star", "backref", "too-long"])
@pytest.mark.parametrize("site", sorted(SITES))
def test_a_catastrophic_repo_pattern_is_refused_naming_the_rule(
    tmp_path: Path, site: str, pattern: str
) -> None:
    """Red before 430: each of these compiled, and `(a+)+$` then ran for the age of the repo."""
    variable, make, load, names, _ = SITES[site]
    with pytest.raises(ConfigError, match=names):
        load(_rules(tmp_path, variable, make(pattern)))


@pytest.mark.parametrize("site", sorted(SITES))
def test_a_normal_repo_pattern_still_loads(tmp_path: Path, site: str) -> None:
    variable, make, load, _, accepted = SITES[site]
    for pattern in accepted:
        assert load(_rules(tmp_path, variable, make(pattern))) is not None


def test_the_limit_reads_the_parse_not_the_text() -> None:
    from code_atlas.limits import checked_pattern

    assert checked_pattern(r"(?:\w+\s*)?=", "r").search("a =")
    for pattern in REFUSED:
        with pytest.raises(ConfigError, match="rule-7"):
            checked_pattern(pattern, "rule-7")
    for pattern in ACCEPTED:
        assert checked_pattern(pattern, "rule-7")


# ------------------------------------------------------------ AC3: timeouts, clamps


def test_the_handshake_is_bounded_by_adapter_timeout_outside_a_build(tmp_path: Path) -> None:
    """Red before 430: an adapter that booted and said nothing parked `start()` for ever."""
    config = load_config(tmp_path, {"CA_FAKE_CMD": _cmd("silent-boot"), "CA_ADAPTER_TIMEOUT": "1"})
    adapter = _adapter(config, "fake")
    outcome: list[BaseException | None] = []

    def start() -> None:
        try:
            adapter.start()
            outcome.append(None)
        except BaseException as error:
            outcome.append(error)

    thread = threading.Thread(target=start, daemon=True)
    thread.start()
    thread.join(10)
    hung = thread.is_alive()
    adapter.kill()  # never leave the silent child behind, whatever the verdict
    thread.join(5)
    assert not hung, "start() was still parked after ten seconds with adapter_timeout=1"
    assert isinstance(outcome[0], AdapterError) and "within 1s" in str(outcome[0])


CEILINGS = {
    "workers": 64,
    "adapter_timeout": 3600,
    "max_candidates": 1000,
    "page_limit": 1000,
    "max_subjects": 1000,
    "impact_depth": 64,
    "impact_max_nodes": 100_000,
    "orphans_max_nodes": 100_000,
    "path_index_max": 1_000_000,
    "max_file_bytes": 64 * 1024 * 1024,
}


@pytest.mark.parametrize("key", sorted(CEILINGS))
def test_a_project_file_cap_is_clamped_and_the_environment_is_not(tmp_path: Path, key: str) -> None:
    """Red before 430: `workers = 100000` spawned a hundred thousand adapters."""
    ceiling = CEILINGS[key]
    (tmp_path / ".code-atlas.toml").write_text(f"{key} = {ceiling * 10}\n", encoding="utf-8")
    assert getattr(load_config(tmp_path, {}), key) == ceiling
    from_env = load_config(tmp_path, {f"CA_{key.upper()}": str(ceiling * 10)})
    assert getattr(from_env, key) == ceiling * 10


def test_the_legacy_max_results_alias_and_the_crossover_are_clamped_too(tmp_path: Path) -> None:
    (tmp_path / ".code-atlas.toml").write_text(
        "max_results = 99999\nfull_build_crossover = 999999999\n", encoding="utf-8"
    )
    config = load_config(tmp_path, {})
    assert config.max_candidates == 1000
    assert config.full_build_crossover == 1_000_000


def test_every_clamped_key_is_a_knob_with_a_ceiling_in_the_code() -> None:
    from code_atlas.config import KNOB_KEYS
    from code_atlas.limits import CONFIG_CEILINGS

    assert set(CEILINGS) <= set(CONFIG_CEILINGS) <= set(KNOB_KEYS)
    assert {key: CONFIG_CEILINGS[key] for key in CEILINGS} == CEILINGS


# ------------------------------------------------------------ AC4: containment


@posix_only
def test_a_stub_root_that_leads_out_and_a_stub_file_that_leads_out_are_skipped(
    tmp_path: Path,
) -> None:
    """Red before 430: both the linked root and the linked file were walked."""
    root = _repo(tmp_path, {"src/a.aa": SOURCE})
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.aa").write_text(OUTSIDE, encoding="utf-8")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    (root / "vendor").mkdir()
    (root / "vendor" / "lib.aa").write_text(SOURCE, encoding="utf-8")
    (root / "vendor" / "leak.aa").symlink_to(outside / "secret.aa")
    assert collect_stubs(root, ["linked"], [".aa"]) == ()
    assert collect_stubs(root, ["vendor"], [".aa"]) == ("vendor/lib.aa",)


@posix_only
def test_read_through_repair_refuses_a_file_swapped_for_a_link_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Closes 375's residual. Red before 430: the adapter was handed the link."""
    root = _repo(tmp_path, {"src/a.aa": SOURCE})
    log = _watch(tmp_path, monkeypatch)
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        before = _paths_seen(log)
        assert before == ["src/a.aa"]
        outside = tmp_path / "secret.aa"
        outside.write_text(OUTSIDE, encoding="utf-8")
        (root / "src" / "a.aa").unlink()
        (root / "src" / "a.aa").symlink_to(outside)
        assert reparse_file(config, store, "src/a.aa") is False
        assert FreshnessGuard(config, store).ensure("src/a.aa") == "stale"
    assert _paths_seen(log) == before, "the linked path reached an adapter"


@pytest.mark.parametrize(("key", "other"), [("host_root", "container"), ("container_root", "host")])
def test_a_project_file_mapping_root_needs_the_trust_flag_the_environment_does_not(
    tmp_path: Path, key: str, other: str
) -> None:
    """Red before 430: the repo's own file set the path the adapters were handed."""
    (tmp_path / ".code-atlas.toml").write_text(f'{key} = "/from-file"\n', encoding="utf-8")
    companion = {f"CA_{other.upper()}_ROOT": "/from-env"}
    with pytest.raises(ConfigError, match=f"{key}.*CA_TRUST_PROJECT_FILE"):
        load_config(tmp_path, companion)
    trusted = load_config(tmp_path, {**companion, "CA_TRUST_PROJECT_FILE": "1"})
    assert getattr(trusted, key) == Path("/from-file")
    mine = load_config(tmp_path, {**companion, f"CA_{key.upper()}": "/from-operator"})
    assert getattr(mine, key) == Path("/from-operator")


@posix_only
def test_a_read_that_crosses_the_trust_line_opens_without_following_a_link(tmp_path: Path) -> None:
    from code_atlas.containment import UnsafeRead, read_bytes

    root = tmp_path / "root"
    root.mkdir()
    (root / "real.aa").write_bytes(b"inside")
    secret = tmp_path / "secret.aa"
    secret.write_bytes(b"outside")
    (root / "out.aa").symlink_to(secret)
    (root / "in.aa").symlink_to(root / "real.aa")
    assert read_bytes(root, root / "real.aa") == b"inside"
    assert read_bytes(root, root / "in.aa") == b"inside"
    with pytest.raises(UnsafeRead):
        read_bytes(root, root / "out.aa")
    assert issubclass(UnsafeRead, OSError)


@posix_only
def test_a_descriptor_that_is_not_the_file_resolved_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The swap between the check and the open: the open file must be the one that was named."""
    from code_atlas import containment

    root = tmp_path / "root"
    root.mkdir()
    (root / "a.aa").write_bytes(b"inside")
    real_fstat = os.fstat

    def other_file(descriptor: int) -> os.stat_result:
        found = real_fstat(descriptor)
        return os.stat_result((*tuple(found)[:1], found.st_ino + 1, *tuple(found)[2:]))

    monkeypatch.setattr(containment.os, "fstat", other_file)
    with pytest.raises(containment.UnsafeRead, match="changed while"):
        containment.read_bytes(root, root / "a.aa")


@posix_only
def test_the_digest_and_the_source_read_refuse_a_swapped_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red before 430: a link to the indexed bytes read as `current`, and its text could leave."""
    from code_atlas import source_slice

    root = _repo(tmp_path, {"src/a.aa": SOURCE})
    config = load_config(root, _env())
    with GraphStore(config.db_path) as store:
        full_build(config, store)
        outside = tmp_path / "same-bytes.aa"
        outside.write_text(SOURCE, encoding="utf-8")
        (root / "src" / "a.aa").unlink()
        (root / "src" / "a.aa").symlink_to(outside)
        assert not file_is_current(store, root, "src/a.aa")
    assert _digest(root / "src" / "a.aa", root) == ""
    # The check-then-read race: even when the earlier check is fooled, the read itself refuses.
    monkeypatch.setattr(source_slice, "readable", lambda _root, _path: True)
    assert source_slice.declaration_slice(root / "src" / "a.aa", 1, 1, root=root) == ""


# ------------------------------------------------------------ AC5: environments


def test_an_adapter_gets_an_allow_listed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red before 430: every secret in the host's environment reached the adapter process."""
    secrets = ("ANTHROPIC_API_KEY", "GH_TOKEN", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "X_KEY")
    for name in secrets:
        monkeypatch.setenv(name, "hunter2")
    seen = tmp_path / "env.json"
    monkeypatch.setenv("CA_FAKE_ENVLOG", str(seen))
    monkeypatch.setenv("LC_ALL", "C")
    with SubprocessAdapter("fake", (sys.executable, str(FAKE), "ok"), tmp_path):
        pass
    names = set(json.loads(seen.read_text(encoding="utf-8")))
    assert not names & set(secrets)
    assert {"PATH", "CA_FAKE_ENVLOG", "LC_ALL"} <= names


def test_the_allow_list_is_exactly_the_named_variables() -> None:
    from code_atlas.adapter import adapter_env

    host = {
        "PATH": "/bin",
        "HOME": "/h",
        "USER": "u",
        "LOGNAME": "u",
        "LANG": "C",
        "LC_CTYPE": "C",
        "TZ": "UTC",
        "TMPDIR": "/t",
        "TMP": "/t",
        "TEMP": "/t",
        "CA_PHP_CMD": "php",
        "SYSTEMROOT": "C:\\W",
        "COMSPEC": "cmd",
        "PATHEXT": ".EXE",
        "WINDIR": "C:\\W",
        "APPDATA": "a",
        "LOCALAPPDATA": "l",
        "USERPROFILE": "p",
        "COMPOSER_HOME": "/c",
        "NODE_PATH": "/n",
    }
    refused = {"GH_TOKEN": "x", "ANTHROPIC_BASE_URL": "x", "SSH_AUTH_SOCK": "x", "NPM_TOKEN": "x"}
    assert adapter_env({**host, **refused}) == host


def test_git_runs_without_the_git_variables_a_shell_carries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red before 430: a `GIT_DIR` in the shell pointed code-atlas's reads at another repo."""
    root = _repo(tmp_path / "mine", {"src/a.aa": SOURCE})
    decoy = _repo(tmp_path / "decoy", {"elsewhere/b.aa": SOURCE})
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    assert gitutil.ls_files(root) == ("src/a.aa",)


def test_git_env_drops_every_git_variable_but_the_ones_code_atlas_sets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from code_atlas.gitutil import HARDENED_ENV, git_env

    monkeypatch.setenv("GIT_SSH_COMMAND", "evil")
    monkeypatch.setenv("git_config_global", "evil")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
    env = git_env()
    assert {key for key in env if key.upper().startswith("GIT_")} == set(HARDENED_ENV)
    assert env["PATH"] == os.environ.get("PATH", "")
    assert "GIT_CONFIG_NOSYSTEM" not in git_env(system_config=True)


def test_the_release_check_fetch_runs_in_the_same_scrubbed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import release_check

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("GIT_SSH_COMMAND", "evil")
    monkeypatch.chdir(tmp_path)
    seen: dict[str, Any] = {}

    def spawn(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="abc\trefs/tags/v1.2.3\n", stderr="")

    monkeypatch.setattr(subprocess, "run", spawn)
    release_check.fetch("https://example.invalid/r.git", now=1_000_000.0)
    assert "GIT_SSH_COMMAND" not in seen["env"]
    assert gitutil.HARDENED_ENV.items() <= seen["env"].items()


# ------------------------------------------------------------ AC6: cache, SQLite


@posix_only
def test_the_onboarding_cache_is_private_and_a_linked_cache_file_is_refused(tmp_path: Path) -> None:
    """Closes 420's residual. Red before 430: the cache was created 0755/0644."""
    root = tmp_path / "root"
    config = _cycle_repo(root)
    generate_onboarding.create(config)()
    cache = root / CACHE_DIR
    assert stat.S_IMODE(cache.stat().st_mode) == 0o700
    assert stat.S_IMODE((cache / CACHE_NAME).stat().st_mode) == 0o600
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me\n", encoding="utf-8")
    (cache / CACHE_NAME).unlink()
    (cache / CACHE_NAME).symlink_to(victim)
    with pytest.raises(ValueError, match="symlink or resolves outside"):
        generate_onboarding.create(config)()
    assert victim.read_text(encoding="utf-8") == "keep me\n"


def test_every_connection_the_store_opens_refuses_extension_loading(tmp_path: Path) -> None:
    """SEC-IN-05: a loaded extension is native code, so none may load on any connection."""
    from code_atlas.store import _connect

    with GraphStore(tmp_path / "graph.db") as store:
        for conn in (store._conn, _connect(tmp_path / "other.db")):
            # AttributeError: a SQLite build without extension loading, which is "off" too.
            with pytest.raises((sqlite3.OperationalError, AttributeError)) as refused:
                conn.load_extension("no-such-extension")
            # "not authorized" is the switch being off; a missing file would mean it was on.
            assert isinstance(refused.value, AttributeError) or "authorized" in str(refused.value)
