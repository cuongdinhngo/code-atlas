"""The adapter seam: the Protocol's shape, the subprocess driver, and extension->adapter lookup.

Every driver test drives a **real** subprocess (the protocol fixture under `fixtures/adapter/`) and
never a mock: a deadlock, an out-of-step reply and a signal escalation exist only at that layer, and
a mocked pipe would stay green through all three.
"""

import json
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from code_atlas import contract
from code_atlas.adapter import (
    AdapterError,
    LanguageAdapter,
    ParseResult,
    SubprocessAdapter,
    adapter_for,
    extension_index,
)

FIXTURE = Path(__file__).parent / "fixtures" / "adapter" / "fake_adapter.py"
BOOT_LOG_ENV = "CA_FAKE_BOOTLOG"  # the fixture's own contract; see fake_adapter.BOOT_LOG
PROTOCOL_MEMBERS = ("name", "extensions", "capabilities", "start", "parse", "stop")
AMORTIZED_FILES = 200


def driver(root: Path, mode: str = "ok", **kwargs) -> SubprocessAdapter:
    """A driver pointed at the protocol fixture, launched the way configuration would launch it."""
    return SubprocessAdapter("fake", (sys.executable, str(FIXTURE), mode), root, **kwargs)


def within(seconds: float, call):
    """Run `call` on a thread so a hang fails the test instead of hanging the suite."""
    box: list[object] = []
    thread = threading.Thread(target=lambda: box.append(call()), daemon=True)
    thread.start()
    thread.join(seconds)
    assert box, f"no answer within {seconds}s — the driver is deadlocked"
    return box[0]


@dataclass
class StubAdapter:
    """A Protocol-shaped adapter with no process behind it, for the lookup tests."""

    name: str
    extensions: tuple[str, ...]
    capabilities: dict[str, bool] = field(default_factory=dict)

    def start(self) -> None: ...

    def parse(self, path: str) -> ParseResult:
        return ParseResult(path=path, ok=True)

    def stop(self) -> None: ...


# --------------------------------------------------------------------------- the Protocol (R1)


def test_the_protocol_declares_exactly_the_six_members() -> None:
    # Guards the guard: an empty member list would make the assertions below pass vacuously.
    assert len(PROTOCOL_MEMBERS) == 6
    for member in PROTOCOL_MEMBERS:
        assert hasattr(SubprocessAdapter, member), f"the driver is missing {member!r}"


def test_the_protocol_rejects_an_adapter_missing_a_member() -> None:
    members = {member: None for member in PROTOCOL_MEMBERS if member != "stop"}
    assert isinstance(StubAdapter("stub", (".aa",)), LanguageAdapter)
    assert not isinstance(type("NoStop", (), members)(), LanguageAdapter)


def test_what_the_adapter_announced_is_unavailable_before_it_starts(tmp_path: Path) -> None:
    unstarted = driver(tmp_path)
    for member in ("name", "extensions", "capabilities"):
        with pytest.raises(AdapterError, match="has not started"):
            getattr(unstarted, member)


# --------------------------------------------------------------------------- the handshake (Q1/Q6)


def test_the_handshake_supplies_the_name_and_the_suffixes(tmp_path: Path) -> None:
    with driver(tmp_path) as adapter:
        assert adapter.name == "fake"
        assert adapter.extensions == (".aa", ".bb")


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("ok", {}),
        ("no-capabilities", {}),
        ("rich-capabilities", {"semantic_types": True, "not_a_known_flag": True}),
    ],
    ids=["declared-empty", "absent-entirely", "known-and-unknown-flags"],
)
def test_capabilities_pass_through_without_being_required(
    tmp_path: Path, mode: str, expected: dict[str, bool]
) -> None:
    # R1.6: an absent flag is legal and an unknown flag is legal; both adapters drive identically.
    with driver(tmp_path, mode) as adapter:
        assert adapter.capabilities == expected
        assert adapter.parse("src/Thing.aa").ok


@pytest.mark.parametrize(
    ("mode", "expected_message"),
    [
        ("bad-version", "speaks contract v99"),
        ("stale-version", "speaks contract v1"),
        ("invalid-handshake", "invalid handshake"),
        ("not-json-handshake", "did not announce itself"),
        ("no-handshake", "did not announce itself"),
    ],
    ids=["wrong-version", "stale-v1", "missing-field", "not-json", "died-before-announcing"],
)
def test_a_bad_handshake_fails_loud(tmp_path: Path, mode: str, expected_message: str) -> None:
    with pytest.raises(AdapterError, match=expected_message):
        driver(tmp_path, mode).start()


def test_a_command_that_cannot_run_fails_loud(tmp_path: Path) -> None:
    unlaunchable = SubprocessAdapter("fake", ("definitely-not-an-executable",), tmp_path)
    with pytest.raises(AdapterError, match="cannot run"):
        unlaunchable.start()


def test_a_diagnostics_path_that_cannot_be_opened_fails_loud(tmp_path: Path) -> None:
    # A bad stderr_path is a config error like any other, so it must raise the one documented
    # type rather than a bare OSError a caller written against the contract would not catch.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    unopenable = driver(tmp_path, stderr_path=blocker / "sub" / "adapter.stderr")

    with pytest.raises(AdapterError, match="cannot run"):
        unopenable.start()


# --------------------------------------------------------------------------- the proving test


def test_one_boot_survives_every_failure_mode_and_stops_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1 + AC2 on one process: each in-stream failure is classified and the stream continues."""
    boot_log = tmp_path / "boots.log"
    monkeypatch.setenv(BOOT_LOG_ENV, str(boot_log))
    adapter = driver(tmp_path)
    adapter.start()
    # Observing the child IS the acceptance criterion, and a public accessor for the tests alone
    # would be a dead abstraction (R7.4), so the private handle is read here deliberately.
    process = adapter._process
    assert process is not None

    soft_failures = [
        ("soft-error/broken.aa", "syntax error @12"),
        ("not-json/broken.aa", "not JSON"),
        ("undecodable/broken.aa", "undecodable"),
        ("invalid/broken.aa", "rejected by the contract"),
    ]
    for path, expected in soft_failures:
        failed = adapter.parse(path)
        assert failed.ok is False and failed.path == path
        assert expected in (failed.error or "")
        assert not failed.nodes and not failed.edges
        # The whole claim: the very next file on the very same process still comes back.
        assert adapter.parse("src/After.aa").ok is True

    blank_led = adapter.parse("blank-first/fine.aa")
    assert blank_led.ok is True and blank_led.nodes

    for index in range(AMORTIZED_FILES):
        assert adapter.parse(f"src/File{index}.aa").ok is True
    assert boot_log.read_text(encoding="utf-8").count("boot") == 1
    assert adapter._process is process and process.poll() is None

    with pytest.raises(AdapterError, match="out of step"):
        adapter.parse("desync/one.aa")

    adapter.stop()
    assert process.returncode == 0


# --------------------------------------------------------------------------- the remaining modes


def test_a_child_that_dies_mid_stream_fails_loud(tmp_path: Path) -> None:
    adapter = driver(tmp_path)
    adapter.start()
    assert adapter.parse("src/Before.aa").ok is True
    with pytest.raises(AdapterError, match="exited"):
        adapter.parse("die/now.aa")
    adapter.stop()


def test_a_chatty_adapter_does_not_deadlock(tmp_path: Path) -> None:
    # 200 KB of diagnostics is more than a pipe buffer holds; an undrained pipe would hang here.
    with driver(tmp_path, "chatty-stderr") as adapter:
        assert within(10, lambda: adapter.parse("src/Thing.aa")).ok is True


def test_diagnostics_can_be_kept_without_blocking_the_stream(tmp_path: Path) -> None:
    log = tmp_path / ".code-atlas" / "adapter-fake.stderr"
    with driver(tmp_path, "chatty-stderr", stderr_path=log) as adapter:
        assert within(10, lambda: adapter.parse("src/Thing.aa")).ok is True
    assert log.stat().st_size > 100_000


# --------------------------------------------------------------------------- lifecycle (AC2b)


def test_stop_escalates_for_a_child_that_ignores_the_closed_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("code_atlas.adapter.STOP_TIMEOUT", 0.3)
    adapter = driver(tmp_path, "ignore-eof")
    adapter.start()
    process = adapter._process
    assert process is not None
    adapter.stop()
    # A child that outlives EOF is signalled rather than left running.
    assert process.returncode is not None and process.returncode != 0


def test_stop_is_idempotent_and_safe_after_the_child_already_died(tmp_path: Path) -> None:
    adapter = driver(tmp_path)
    adapter.start()
    process = adapter._process
    assert process is not None
    with pytest.raises(AdapterError):
        adapter.parse("die/now.aa")
    adapter.stop()
    adapter.stop()
    assert process.returncode == 3


def test_start_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    boot_log = tmp_path / "boots.log"
    monkeypatch.setenv(BOOT_LOG_ENV, str(boot_log))
    with driver(tmp_path) as adapter:
        adapter.start()
        assert boot_log.read_text(encoding="utf-8").count("boot") == 1


def test_parsing_before_start_fails_loud(tmp_path: Path) -> None:
    with pytest.raises(AdapterError, match="has not started"):
        driver(tmp_path).parse("src/Thing.aa")


def test_the_request_carries_the_repo_relative_path(tmp_path: Path) -> None:
    # §4.1 is one JSON object per line; the fixture echoes the path it was asked for.
    with driver(tmp_path) as adapter:
        result = adapter.parse("src/deep/Thing.aa")
    assert result.path == "src/deep/Thing.aa"
    assert result.nodes[0]["file_path"] == "src/deep/Thing.aa"


def test_a_result_is_passed_through_unchanged(tmp_path: Path) -> None:
    # R4.2: the driver enriches nothing, so the rows are exactly what the adapter emitted.
    with driver(tmp_path) as adapter:
        first = adapter.parse("src/Thing.aa")
        second = adapter.parse("src/Thing.aa")
    assert first == second
    assert contract.validate(
        {"path": first.path, "ok": True, "nodes": list(first.nodes), "edges": list(first.edges)}
    ) == []


# --------------------------------------------------------------------------- lookup (R3, AC3)


def test_the_index_maps_every_announced_suffix() -> None:
    one, two = StubAdapter("one", (".aa", ".bb")), StubAdapter("two", (".cc",))
    index = extension_index([one, two])
    assert index == {".aa": one, ".bb": one, ".cc": two}


def test_a_suffix_claimed_twice_fails_loud() -> None:
    with pytest.raises(AdapterError, match="claimed by both"):
        extension_index([StubAdapter("one", (".aa",)), StubAdapter("two", (".aa",))])


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/Thing.aa", "one"),
        ("src/Thing.AA", "one"),
        ("src/Thing.cc", "two"),
        ("src/Thing.zz", None),
        ("src/Makefile", None),
        ("src/page.template.aa", "one"),
    ],
    ids=["known", "upper-case", "second-adapter", "unclaimed", "no-suffix", "several-suffixes"],
)
def test_a_path_reaches_its_adapter_by_suffix_alone(path: str, expected: str | None) -> None:
    index = extension_index([StubAdapter("one", (".aa",)), StubAdapter("two", (".cc",))])
    found = adapter_for(path, index)
    assert (found.name if found else None) == expected


def test_an_empty_index_claims_nothing() -> None:
    assert adapter_for("src/Thing.aa", extension_index([])) is None


# --------------------------------------------------------------------------- the fixture itself


def test_the_fixture_speaks_the_contract(tmp_path: Path) -> None:
    """Guards the guard: if the fixture drifted off the contract, the tests above prove nothing."""
    process = subprocess.run(
        (sys.executable, str(FIXTURE), "ok"),
        input='{"path":"src/Thing.aa"}\n',
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    meta, result = (json.loads(line) for line in process.stdout.splitlines())
    assert contract.validate_meta(meta) == []
    assert contract.validate(result) == []


# --------------------------------------------------------------------------- path mapping (§9)


def test_absolute_host_paths_are_rewritten_on_the_wire_and_caller_paths_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: container wire path; ParseResult keeps the caller's path (§9)."""
    host = tmp_path / "host"
    host.mkdir()
    container = Path("/app")
    relative = "src/Thing.aa"
    absolute = str(host / relative)
    path_log = tmp_path / "wire.log"
    monkeypatch.setenv("CA_FAKE_PATHLOG", str(path_log))

    with driver(tmp_path, host_root=host, container_root=container) as adapter:
        mapped = adapter.parse(absolute)

    assert path_log.read_text(encoding="utf-8").strip() == "/app/src/Thing.aa"
    assert mapped.path == absolute
    assert mapped.ok
    assert mapped.nodes[0]["file_path"] == absolute
    assert mapped.nodes[0]["qualified_name"] == f"{absolute}::Thing"

    path_log.write_text("", encoding="utf-8")
    with driver(tmp_path, host_root=host, container_root=container) as adapter:
        stored = adapter.parse(relative)
    assert path_log.read_text(encoding="utf-8").strip() == relative
    assert stored.path == relative
    assert stored.nodes[0]["file_path"] == relative
    assert stored.nodes[0]["qualified_name"] == f"{relative}::Thing"


def test_a_path_outside_the_host_root_fails_loud_as_an_adapter_error(
    tmp_path: Path,
) -> None:
    host = tmp_path / "host"
    host.mkdir()
    with driver(tmp_path, host_root=host, container_root=Path("/app")) as adapter:
        with pytest.raises(AdapterError, match="not under"):
            adapter.parse(str(tmp_path / "elsewhere" / "x.aa"))


def test_an_unset_adapter_command_names_the_env_variable(tmp_path: Path) -> None:
    from code_atlas.config import load_config
    from code_atlas.indexer import _adapter

    with pytest.raises(AdapterError, match="CA_PHP_CMD"):
        _adapter(load_config(tmp_path, {}), "php")
