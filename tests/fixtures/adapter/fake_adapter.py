"""A protocol fixture: the smallest process that speaks the §4.1 JSONL contract.

Spec-driven, not language-driven (R6.2) — it encodes the wire protocol and nothing about any real
language, parser, or repo. A start-up ``mode`` shapes the handshake; the requested path prefix
shapes each reply, so one process can exercise every failure mode of one boot.

Two modes stay alive and say nothing — ``silent-boot`` and ``silent-after-first-boot`` — and the
``hang/`` path prefix answers nothing. They are how a driver's deadline is proven against a process
that is genuinely hung rather than a mock of one.
"""

import json
import os
import sys
import time

BOOT_LOG = "CA_FAKE_BOOTLOG"
PATH_LOG = "CA_FAKE_PATHLOG"
SUFFIXES = [".aa", ".bb"]

# Longer than any deadline a test sets, so "silent" means silent for the whole run.
FOREVER = 600

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
    # Paths under dep/ call into lib/core.aa so incremental can prove single-hop dependents (§8.3).
    edges = []
    if path.startswith("dep/"):
        edges = [
            {
                "kind": "CALLS",
                "source_qname": f"{path}::Thing",
                "target_raw": "lib/core.aa::Thing",
                "file_path": path,
                "line": 2,
                "confidence_tier": "HEURISTIC",
            }
        ]
    return json.dumps({"path": path, "ok": True, "nodes": [node], "edges": edges})


def count_boot(boot_log):
    """Append this boot to the log and return how many boots there have now been."""
    with open(boot_log, "a", encoding="utf-8") as log:
        log.write("boot\n")
    with open(boot_log, encoding="utf-8") as log:
        return len(log.readlines())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
    boot_log = os.environ.get(BOOT_LOG)
    boots = count_boot(boot_log) if boot_log else 0

    if mode == "silent-boot" or (mode == "silent-after-first-boot" and boots > 1):
        # Alive, holding the pipes open, announcing nothing: the hang a deadline has to bound.
        time.sleep(FOREVER)
        return
    if mode == "silent-after-first-boot":
        mode = "ok"

    if mode == "chatty-stderr":
        sys.stderr.write("W" * 200_000 + "\n")
        sys.stderr.flush()
    if mode == "not-json-handshake":
        write("hello, I am not a handshake")
    elif mode == "no-handshake":
        # Exits rather than going mute; staying alive and silent is the `silent-boot` mode above.
        return
    else:
        write(json.dumps(HANDSHAKES.get(mode, HANDSHAKES["ok"])))

    for line in sys.stdin:
        if not line.strip():
            continue
        path = json.loads(line)["path"]
        path_log = os.environ.get(PATH_LOG)
        if path_log:
            with open(path_log, "a", encoding="utf-8") as log:
                log.write(path + "\n")
        if path.startswith("hang/"):
            # Never answers, never exits: the silent *reply* a deadline has to bound.
            time.sleep(FOREVER)
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
        time.sleep(FOREVER)


if __name__ == "__main__":
    main()
