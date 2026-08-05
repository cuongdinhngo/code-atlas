"""Task 007: the PHP adapter's ``--server`` mode, driven by the real core (§4.1, §7).

Every assertion here launches the real interpreter and drives it through the real
:class:`SubprocessAdapter` — the first live integration of the driver built in task 005 with the
adapter built in task 006. A fake on either side would only prove the fake is self-consistent.

Most of these skip without PHP or ``vendor/``, so ``0 skipped`` in CI is the load-bearing evidence
that the PHP path actually ran.
"""

import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

import pytest

from code_atlas.adapter import AdapterError, SubprocessAdapter

ROOT = Path(__file__).resolve().parent.parent
ADAPTER = ROOT / "adapters" / "php"
ENTRY = ADAPTER / "index.php"
AUTOLOAD = ADAPTER / "vendor" / "autoload.php"
FIXTURES = ROOT / "tests" / "fixtures" / "php"

GOOD = "tests/fixtures/php/namespaced.php"
OTHER = "tests/fixtures/php/global_underscore.php"
BROKEN = "tests/fixtures/php/syntax_error.php"

PHP = shutil.which("php")
needs_php = pytest.mark.skipif(
    PHP is None or not AUTOLOAD.is_file(),
    reason=f"needs the PHP CLI and `composer install` in {ADAPTER}",
)


def server(*php_flags: str, stderr_path: Path | None = None) -> SubprocessAdapter:
    """The adapter under the core's own driver, exactly as `CA_PHP_CMD` would launch it."""
    return SubprocessAdapter(
        "php",
        [str(PHP), *php_flags, str(ENTRY), "--server"],
        ROOT,
        stderr_path=stderr_path,
    )


def test_the_proof_has_something_to_run() -> None:
    # Runs without PHP: a skipped proof must not also hide a missing entry point or fixture.
    assert ENTRY.is_file()
    for path in (GOOD, OTHER, BROKEN):
        assert (ROOT / path).read_text(encoding="utf-8").startswith("<?php")
    assert "--server" in ENTRY.read_text(encoding="utf-8")


@needs_php
def test_the_core_drives_the_real_php_adapter_end_to_end() -> None:
    """The proving test: pre-change `--server` is rejected with exit 2, so start() raises."""
    with server() as adapter:
        assert adapter.name == "php"
        assert adapter.extensions == (".php", ".phtml", ".module", ".inc")

        result = adapter.parse(GOOD)
        assert result.ok is True
        assert result.path == GOOD
        # A valid but empty result would prove nothing (the bar task 006 set).
        assert result.nodes and result.edges


@needs_php
def test_the_handshake_announces_capabilities_as_an_object_not_an_empty_array() -> None:
    # PHP's natural `[]` encodes as a JSON array, which validate_meta rejects loudly at startup.
    with server() as adapter:
        assert adapter.capabilities == {}


@needs_php
def test_each_reply_is_correlated_to_the_request_that_asked_for_it() -> None:
    # Lock-step: a reply for an unasked path is a desync, which the driver raises on.
    with server() as adapter:
        for path in (GOOD, OTHER, GOOD, BROKEN, OTHER):
            assert adapter.parse(path).path == path


@needs_php
def test_a_bad_file_fails_softly_and_the_next_file_still_parses() -> None:
    """R5.1: ErrorHandler\\Collecting makes a syntax error one bad result, not a dead stream."""
    with server() as adapter:
        broken = adapter.parse(BROKEN)
        assert broken.ok is False
        assert broken.error and "Syntax error" in broken.error
        assert not broken.nodes and not broken.edges

        survived = adapter.parse(GOOD)
        assert survived.ok is True, "one bad file must not end the process"
        assert survived.nodes


@needs_php
def test_an_unreadable_path_fails_softly_and_the_next_file_still_parses() -> None:
    with server() as adapter:
        missing = adapter.parse("tests/fixtures/php/does_not_exist.php")
        assert missing.ok is False
        assert adapter.parse(GOOD).ok is True


@needs_php
def test_a_host_that_prints_warnings_cannot_corrupt_the_protocol(tmp_path: Path) -> None:
    """P7: `display_errors` is host-set; on stdout a PHP notice lands between two protocol lines.

    Reading a directory emits one deterministically. Without the stderr redirect the driver sees
    `Warning:`/`Notice:` text instead of JSON and soft-fails a file for the wrong reason.
    """
    diagnostics = tmp_path / "adapter.stderr"
    with server("-d", "display_errors=1", stderr_path=diagnostics) as adapter:
        # A directory reads as "" while still emitting a notice, so it provokes one reliably.
        result = adapter.parse("tests")

        assert result.path == "tests"
        assert not (result.error and "not JSON" in result.error), (
            "a PHP diagnostic leaked onto stdout and was read as a protocol line"
        )
        # A leaked line also shifts every later reply, which surfaces as a desync AdapterError.
        assert adapter.parse(GOOD).ok is True

    assert "directory" in diagnostics.read_text(encoding="utf-8").lower(), (
        "the diagnostic must still be produced — on stderr, where it belongs"
    )


@needs_php
def test_a_multi_megabyte_reply_survives_one_line(tmp_path: Path) -> None:
    # §4.1: "a 2 MB result line is normal" — one `\n`-framed line, however large.
    big = tmp_path / "big.php"
    body = "\n".join(f"class C{i} {{ public function m{i}(): void {{}} }}" for i in range(4000))
    big.write_text(f"<?php\n{body}\n", encoding="utf-8")

    with server() as adapter:
        result = adapter.parse(str(big))

    assert result.ok is True
    assert len(result.nodes) == 8001, "4000 classes + 4000 methods + the File node"
    assert len(json.dumps(list(result.nodes))) > 1_000_000


@needs_php
def test_undecodable_bytes_fail_that_file_softly_and_are_never_repaired(tmp_path: Path) -> None:
    """§4.1: a result that will not encode as UTF-8 fails soft, never patched into mojibake.

    An include target is copied verbatim from a string literal, so invalid bytes there reach
    `json_encode` — mojibake would parse as valid JSON and store silently corrupt rows.
    """
    undecodable = tmp_path / "undecodable.php"
    undecodable.write_bytes(b'<?php\nrequire "\xff\xfe_broken.php";\n')

    with server() as adapter:
        result = adapter.parse(str(undecodable))
        assert result.ok is False
        assert result.error and "UTF-8" in result.error
        assert not result.nodes and not result.edges
        # The reply was still well-formed protocol, so the stream is intact.
        assert adapter.parse(GOOD).ok is True


@needs_php
def test_a_blank_or_malformed_request_line_does_not_desync_the_stream() -> None:
    """Blank and unusable lines are skipped, so the next real request still gets its reply."""
    process = subprocess.Popen(
        [str(PHP), str(ENTRY), "--server"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    assert process.stdin is not None and process.stdout is not None
    try:
        handshake = json.loads(process.stdout.readline())
        assert handshake["contract_version"] == 2

        process.stdin.write("\n")
        process.stdin.write("   \n")
        process.stdin.write("this is not json at all\n")
        process.stdin.write('{"no_path": true}\n')
        process.stdin.write(json.dumps({"path": GOOD}) + "\n")
        process.stdin.flush()

        reply = json.loads(process.stdout.readline())
        assert reply["path"] == GOOD, "a skipped line must not shift the replies"
        assert reply["ok"] is True
    finally:
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()


@needs_php
def test_a_reply_is_readable_before_the_process_exits_even_when_the_host_buffers_output() -> None:
    """A host-set `output_buffering` holds `echo` until exit, deadlocking a lock-step reader.

    The reply must therefore bypass PHP's output buffer entirely. Reading *while the child is still
    running* is the whole point: at exit every buffer flushes, so a post-mortem read proves nothing.
    """
    process = subprocess.Popen(
        [str(PHP), "-d", "output_buffering=8192", "-d", "implicit_flush=0", str(ENTRY), "--server"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    assert process.stdin is not None and process.stdout is not None
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(process.stdout.readline)
            try:
                handshake = pending.result(timeout=20)
            except FuturesTimeout:
                process.kill()
                pytest.fail("the handshake never arrived — the reply sat in PHP's output buffer")

        assert json.loads(handshake)["contract_version"] == 2
    finally:
        process.stdin.close()
        process.wait(timeout=30)
        process.stdout.close()


@needs_php
def test_the_server_exits_cleanly_when_its_stdin_closes() -> None:
    # stop() escalates wait -> terminate -> kill; a clean EOF exit must settle at the first step.
    adapter = server()
    adapter.start()
    adapter.parse(GOOD)
    adapter.stop()

    # Using a stopped adapter is a programmer error, so it fails loud rather than hanging.
    with pytest.raises(AdapterError):
        adapter.parse(GOOD)


@needs_php
@pytest.mark.parametrize("path", [GOOD, OTHER], ids=["namespaced", "global-underscore"])
def test_both_modes_emit_the_same_result_for_the_same_file(path: str) -> None:
    """One parse implementation behind two entry points — sameness is structural, not a promise."""
    completed = subprocess.run(
        [str(PHP), str(ENTRY), "--file", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    from_file = json.loads(completed.stdout)

    with server() as adapter:
        result = adapter.parse(path)
    from_server = {
        "path": result.path,
        "ok": result.ok,
        "nodes": list(result.nodes),
        "edges": list(result.edges),
    }

    assert json.dumps(from_server, sort_keys=True) == json.dumps(from_file, sort_keys=True)


@needs_php
def test_every_edge_is_bare_in_server_mode() -> None:
    # R3.3: cross-file linking is the resolver's job; the adapter never claims a target_qname.
    with server() as adapter:
        edges = adapter.parse(GOOD).edges

    assert edges
    for edge in edges:
        assert "target_qname" not in edge
        assert edge["target_raw"]
