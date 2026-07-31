"""A protocol fixture: the smallest process that speaks the §4.1 JSONL contract.

Spec-driven, not language-driven (R6.2) — it encodes the wire protocol and nothing about any real
language, parser, or repo. A start-up ``mode`` shapes the handshake; the requested path prefix
shapes each reply, so one process can exercise every failure mode of one boot.
"""

import json
import os
import sys

BOOT_LOG = "CA_FAKE_BOOTLOG"
SUFFIXES = [".aa", ".bb"]

HANDSHAKES = {
    "ok": {"name": "fake", "extensions": SUFFIXES, "capabilities": {}, "contract_version": 1},
    "rich-capabilities": {
        "name": "fake",
        "extensions": SUFFIXES,
        "capabilities": {"semantic_types": True, "not_a_known_flag": True},
        "contract_version": 1,
    },
    "no-capabilities": {"name": "fake", "extensions": SUFFIXES, "contract_version": 1},
    "bad-version": {
        "name": "fake",
        "extensions": SUFFIXES,
        "capabilities": {},
        "contract_version": 99,
    },
    "invalid-handshake": {"name": "fake", "capabilities": {}, "contract_version": 1},
    "not-json-handshake": None,
    "no-handshake": None,
}


def write(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def reply(path):
    """One reply, chosen by the requested path so a single boot can fail in several ways."""
    if path.startswith("soft-error/"):
        return json.dumps({"path": path, "ok": False, "error": "syntax error @12"})
    if path.startswith("not-json/"):
        return "this line is not JSON at all"
    if path.startswith("invalid/"):
        return json.dumps({"path": path, "ok": True, "nodes": [{"kind": "Nope"}], "edges": []})
    if path.startswith("desync/"):
        return json.dumps({"path": "some/other/file.aa", "ok": True, "nodes": [], "edges": []})
    node = {
        "kind": "Class",
        "name": "Thing",
        "qualified_name": f"{path}::Thing",
        "file_path": path,
        "line_start": 1,
    }
    return json.dumps({"path": path, "ok": True, "nodes": [node], "edges": []})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
    boot_log = os.environ.get(BOOT_LOG)
    if boot_log:
        with open(boot_log, "a", encoding="utf-8") as log:
            log.write("boot\n")

    if mode == "chatty-stderr":
        sys.stderr.write("W" * 200_000 + "\n")
        sys.stderr.flush()
    if mode == "not-json-handshake":
        write("hello, I am not a handshake")
    elif mode == "no-handshake":
        # Exits instead of going mute: a process that stays alive and silent would hang the driver,
        # which is the deferred hung-adapter mode (task 009), not something to prove here.
        return
    else:
        write(json.dumps(HANDSHAKES.get(mode, HANDSHAKES["ok"])))

    for line in sys.stdin:
        if not line.strip():
            continue
        path = json.loads(line)["path"]
        if path.startswith("die/"):
            sys.exit(3)
        if path.startswith("undecodable/"):
            sys.stdout.buffer.write(b'{"path": "\xff\xfe", "ok": true}\n')
            sys.stdout.buffer.flush()
            continue
        if path.startswith("blank-first/"):
            write("")
        write(reply(path))

    if mode == "ignore-eof":
        # Deliberately outlive the closed stdin so stop() has to escalate to a signal.
        import time

        time.sleep(600)


if __name__ == "__main__":
    main()
