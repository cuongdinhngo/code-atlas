"""The ``LanguageAdapter`` seam, the subprocess driver, and extension->adapter lookup (§4.1, §4.3).

The core learns nothing about a language from this module. An adapter is launched from a configured
argv and then announces itself — its name, the file suffixes it owns, any optional capabilities — so
which language a process speaks is data the process supplies, never a literal here (R1.1, R1.5).

One process serves every file it is handed (§4.1). A bad *file* comes back as a failed
:class:`ParseResult` and the stream continues (R5.1); a bad *process* — a command that will not
launch, a child that died, a reply for the wrong path — raises :class:`AdapterError` (R5.3).
"""

import json
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, Protocol, runtime_checkable

from code_atlas import contract
from code_atlas.config import ConfigError, to_adapter_path

# Escalation budget for stop(); module-level so a test can shorten the wait on a deliberate hang.
STOP_TIMEOUT = 5.0
KILL_TIMEOUT = 2.0


class AdapterError(Exception):
    """A broken adapter process or command — a config/programmer error, so it fails loud (R5.3)."""


@dataclass(frozen=True, slots=True)
class ParseResult:
    """One adapter result, mirroring :data:`contract.RESULT_FIELDS`.

    Nodes and edges stay opaque rows: the driver transports them and the store persists them, so
    naming a single node field here would duplicate the contract (R3.2, R1.4).
    """

    path: str
    ok: bool
    nodes: tuple[dict[str, object], ...] = ()
    edges: tuple[dict[str, object], ...] = ()
    error: str | None = None


@runtime_checkable
class LanguageAdapter(Protocol):
    """The one seam between the core and every language (§4.3, R1.2).

    Deliberately tiny: given a file, emit nodes and edges. Richer parsers advertise the extra via
    :attr:`capabilities`, which the core may use and never requires (R1.6).
    """

    @property
    def name(self) -> str:
        """What the adapter calls itself."""

    @property
    def extensions(self) -> tuple[str, ...]:
        """The file suffixes this adapter owns, lower-cased and dot-prefixed."""

    @property
    def capabilities(self) -> contract.Capabilities:
        """Optional powers this adapter offers; an absent flag is legal."""

    def start(self) -> None:
        """Launch the adapter and read its handshake."""

    def parse(self, path: str, *, declarations_only: bool = False) -> ParseResult:
        """Parse one repo-relative path.

        ``declarations_only`` asks the adapter to skip call/NEW edges from bodies (task 039
        stub indexing). Adapters that do not honour the flag may still emit those edges; the
        indexer strips ``CALLER_KINDS`` (CALLS/NEW) for stub roots as a language-agnostic
        backstop. Other body-level kinds (REFERENCES, IMPORTS) are *not* stripped — honouring
        the flag is the adapter's responsibility.
        """

    def stop(self) -> None:
        """Shut the adapter down and release its pipes."""


class SubprocessAdapter:
    """A long-lived adapter process speaking the JSONL contract over stdin/stdout (§4.1).

    Requests and replies are strictly one-for-one: concurrency is N processes (§8.1), never several
    requests in flight on one pipe, which keeps replies attributable and ordering deterministic.
    """

    def __init__(
        self,
        key: str,
        command: Iterable[str],
        root: Path,
        *,
        host_root: Path | None = None,
        container_root: Path | None = None,
        stderr_path: Path | None = None,
    ) -> None:
        # `key` is only the configuration key and error label; the adapter's real name arrives in
        # the handshake, so the core never has to agree with the user about what a language is.
        self._key = key
        self._command = tuple(command)
        self._root = root
        self._host_root = host_root
        self._container_root = container_root
        self._stderr_path = stderr_path
        self._process: subprocess.Popen[str] | None = None
        self._stderr: IO[str] | None = None
        self._meta: dict[str, object] | None = None

    @property
    def name(self) -> str:
        return str(self._announced()["name"])

    @property
    def extensions(self) -> tuple[str, ...]:
        announced = self._announced()["extensions"]
        assert isinstance(announced, list)
        return tuple(str(suffix).lower() for suffix in announced)

    @property
    def capabilities(self) -> contract.Capabilities:
        announced = self._announced().get("capabilities")
        return dict(announced) if isinstance(announced, dict) else {}

    def start(self) -> None:
        """Launch the adapter and read the handshake it opens the stream with. Idempotent."""
        if self._process is not None:
            return
        try:
            # Opening the diagnostics file is part of launching: a bad path is a config error too.
            self._stderr = self._open_stderr()
            self._process = subprocess.Popen(
                self._command,
                cwd=self._root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr or subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as error:
            self._close_stderr()
            raise AdapterError(
                f"adapter {self._key!r}: cannot run {self._command} ({error})"
            ) from error
        self._meta = self._read_handshake()

    def parse(self, path: str, *, declarations_only: bool = False) -> ParseResult:
        """Parse one path. Wire may be remapped; the result always keeps the caller's path (§9)."""
        process = self._running()
        try:
            wire = to_adapter_path(path, self._host_root, self._container_root)
        except ConfigError as error:
            # Bad absolute path under set roots — loud at the process boundary (R5.3).
            raise AdapterError(f"adapter {self._key!r}: {error}") from error
        self._request(process, wire, declarations_only=declarations_only)
        try:
            line = self._read_line(process)
        except UnicodeDecodeError as error:
            return _failure(path, f"adapter emitted undecodable output ({error})")
        try:
            reply = json.loads(line)
        except json.JSONDecodeError as error:
            return _failure(path, f"adapter emitted a line that is not JSON ({error})")
        return self._parse_result(path, reply, wire=wire)

    def kill(self) -> None:
        """Kill the child outright, leaving its pipes alone. Safe from another thread, and twice.

        This is how a caller bounds a silent adapter: a read parked in :meth:`_read_line` returns
        ``''`` once the child dies, so the hang collapses into the usual :class:`AdapterError`.
        Closing the pipes instead would race the parked reader into a `ValueError`.
        """
        process = self._process
        if process is not None:
            process.kill()

    def stop(self) -> None:
        """Close the stream, then escalate wait -> terminate -> kill. Safe to call twice."""
        process, self._process, self._meta = self._process, None, None
        if process is not None:
            _shut_down(process)
        self._close_stderr()

    def __enter__(self) -> "SubprocessAdapter":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def _announced(self) -> dict[str, object]:
        """The handshake, or a loud failure — reading these before start() is a programmer error."""
        if self._meta is None:
            raise AdapterError(f"adapter {self._key!r} has not started, so it announced nothing")
        return self._meta

    def _running(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise AdapterError(f"adapter {self._key!r} has not started")
        return self._process

    def _open_stderr(self) -> IO[str] | None:
        """Diagnostics go to a file or nowhere: an undrained pipe deadlocks once it fills."""
        if self._stderr_path is None:
            return None
        self._stderr_path.parent.mkdir(parents=True, exist_ok=True)
        return self._stderr_path.open("w", encoding="utf-8")

    def _close_stderr(self) -> None:
        if self._stderr is not None:
            self._stderr.close()
            self._stderr = None

    def _read_handshake(self) -> dict[str, object]:
        """Read and check the one meta line an adapter opens with (§4.1)."""
        try:
            meta = json.loads(self._read_line(self._running()))
        except (AdapterError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.stop()
            raise AdapterError(f"adapter {self._key!r} did not announce itself: {error}") from error

        errors = contract.validate_meta(meta)
        if errors:
            self.stop()
            raise AdapterError(f"adapter {self._key!r} announced an invalid handshake: {errors[0]}")
        if meta["contract_version"] != contract.CONTRACT_VERSION:
            announced = meta["contract_version"]
            self.stop()
            raise AdapterError(
                f"adapter {self._key!r} speaks contract v{announced}, "
                f"but this core speaks v{contract.CONTRACT_VERSION}"
            )
        return meta

    def _request(
        self, process: subprocess.Popen[str], path: str, *, declarations_only: bool = False
    ) -> None:
        assert process.stdin is not None
        payload: dict[str, object] = {"path": path}
        if declarations_only:
            payload["declarations_only"] = True
        try:
            process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as error:
            raise AdapterError(
                f"adapter {self._key!r} stopped accepting requests at {path!r} ({error})"
            ) from error

    def _read_line(self, process: subprocess.Popen[str]) -> str:
        """The next non-blank line, or a loud failure when the adapter has gone away."""
        assert process.stdout is not None
        while True:
            line = process.stdout.readline()
            if not line:
                raise AdapterError(
                    f"adapter {self._key!r} exited (code {process.poll()}) with the stream open"
                )
            if line.strip():
                return line

    def _parse_result(self, path: str, reply: object, *, wire: str) -> ParseResult:
        """Classify one reply. An out-of-step reply is loud; anything about the file is soft."""
        errors = contract.validate(reply)
        if errors:
            return _failure(path, f"adapter result rejected by the contract ({errors[0]})")
        assert isinstance(reply, dict)
        if reply["path"] != wire:
            raise AdapterError(
                f"adapter {self._key!r} answered for {reply['path']!r} when {wire!r} was asked — "
                "the stream is out of step"
            )
        if wire != path:
            reply = _rebase_reply(reply, wire, path)
        if not reply["ok"]:
            return _failure(path, str(reply.get("error")))
        nodes = reply.get("nodes") or ()
        edges = reply.get("edges") or ()
        assert isinstance(nodes, list | tuple)
        assert isinstance(edges, list | tuple)
        # Relative build path: no copy. Rebase already copied when wire != path.
        return ParseResult(path=path, ok=True, nodes=tuple(nodes), edges=tuple(edges))


def extension_index(adapters: Iterable[LanguageAdapter]) -> dict[str, LanguageAdapter]:
    """Index started adapters by the suffixes they announced.

    Not a registry (R1.2): a dict built from adapters the caller already made. One suffix claimed
    twice is a configuration error, so it fails loud rather than letting one adapter win silently.
    """
    index: dict[str, LanguageAdapter] = {}
    for adapter in adapters:
        for suffix in adapter.extensions:
            owner = index.get(suffix.lower())
            if owner is not None:
                raise AdapterError(
                    f"{suffix.lower()!r} is claimed by both {owner.name!r} and {adapter.name!r}"
                )
            index[suffix.lower()] = adapter
    return index


def adapter_for(path: str, index: Mapping[str, LanguageAdapter]) -> LanguageAdapter | None:
    """The adapter owning a path's suffix, or None when no adapter claims it."""
    return index.get(PurePosixPath(path).suffix.lower())


def _failure(path: str, error: str) -> ParseResult:
    """One file the adapter could not deliver; the build records it and keeps going (R5.1)."""
    return ParseResult(path=path, ok=False, error=error)


def _rebase_reply(reply: dict[str, object], wire: str, path: str) -> dict[str, object]:
    """Rewrite wire paths the adapter echoed back into the caller's store-facing path (§9)."""
    rebased = dict(reply)
    rebased["path"] = path
    nodes = reply.get("nodes") or []
    edges = reply.get("edges") or []
    assert isinstance(nodes, list) and isinstance(edges, list)
    rebased["nodes"] = [_rebase_row(row, wire, path) for row in nodes]
    rebased["edges"] = [_rebase_row(row, wire, path) for row in edges]
    return rebased


def _rebase_row(row: object, wire: str, path: str) -> dict[str, object]:
    assert isinstance(row, dict)
    out: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, str):
            out[str(key)] = _rebase_string(value, wire, path)
        else:
            out[str(key)] = value
    return out


def _rebase_string(value: str, wire: str, path: str) -> str:
    if value == wire:
        return path
    # Member qnames are `{path}::Name`; a nested `/` prefix is not a file-path shape we emit.
    if value.startswith(f"{wire}::"):
        return path + value[len(wire) :]
    return value


def _shut_down(process: subprocess.Popen[str]) -> None:
    """EOF first, then signals: a child may ignore a closed stdin, and none may be left running."""
    if process.stdin is not None:
        try:
            process.stdin.close()
        except OSError:
            pass
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=KILL_TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if process.stdout is not None:
        process.stdout.close()
