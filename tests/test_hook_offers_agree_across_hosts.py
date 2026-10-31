"""A hook command offered to one host is offered to every host that can run it (task 240).

099 shipped `code-atlas-signal` and wired it in `contrib/codex/hooks.json` only. Nothing failed:
`test_contrib_snippets.py` checks that commands a snippet **calls** are declared in `pyproject.toml`
(the reverse direction), and `test_poke_snippet_covers_every_adapter.py` checks suffix coverage
**inside** one hook. Neither compares one host's offer against another's — so the signal stayed
absent from the Claude Code snippet, which is the host every field round runs on, for 16 rounds.

This is task 200's lesson on a second axis: 200 guarded the *suffix* set after it drifted, in the
same file whose *command* set then drifted.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

CONTRIB = REPO / "contrib"
# Hook commands are the console scripts whose job is to fire at a host event. `code-atlas` (the
# server) and `code-atlas-build` (a CLI) are not hooks and are deliberately outside this guard.
HOOK_COMMANDS = frozenset({"code-atlas-poke", "code-atlas-signal"})
# A host offer is a directory shipping a hook config file the host merges into its own settings.
HOST_OFFERS = ("claude-code", "codex")


def _offered_commands(directory: Path) -> set[str]:
    """Hook commands named by the machine-readable offer a host actually installs."""
    found: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        text = path.read_text(encoding="utf-8")
        json.loads(text)  # an offer a host cannot parse is not an offer
        # A bare command, or one behind the index gate (`…; exec <cmd>`, 344 / 381).
        found |= {cmd for cmd in HOOK_COMMANDS if f'"{cmd}"' in text or f"exec {cmd}" in text}
    return found


def test_the_hook_commands_are_console_scripts() -> None:
    # R6.5: a typo in HOOK_COMMANDS would make every comparison below vacuously equal.
    declared = set(tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
                   ["project"]["scripts"])
    assert HOOK_COMMANDS <= declared, f"not console scripts: {sorted(HOOK_COMMANDS - declared)}"


@pytest.mark.parametrize("host", HOST_OFFERS)
def test_each_host_offer_is_not_vacuous(host: str) -> None:
    # R6.5: a host shipping no parseable config would pass the agreement check by offering nothing.
    assert _offered_commands(CONTRIB / host), f"contrib/{host}/ offers no hook command at all"


def test_every_host_offers_the_same_hook_commands() -> None:
    """The guard 240 exists for: an offer that reaches one host and not the other."""
    offers = {host: _offered_commands(CONTRIB / host) for host in HOST_OFFERS}
    union = set().union(*offers.values())
    missing = {host: sorted(union - cmds) for host, cmds in offers.items() if union - cmds}
    assert not missing, f"hook commands offered to some hosts and not others: {missing}"


# 427: every host wakes on the index database, never the directory a repo can ship.
CODEX_HOOKS = CONTRIB / "codex" / "hooks.json"
OPENCODE_PLUGIN = CONTRIB / "opencode" / "code-atlas.js"


def _gate_segments() -> tuple[str, ...]:
    """The database path `PLUGIN_GATE` tests, split — derived, never re-typed (R6.7)."""
    import gen_skill

    path = re.search(r'\$\{CLAUDE_PROJECT_DIR:-\.\}/(\S+)"', gen_skill.PLUGIN_GATE)
    assert path, gen_skill.PLUGIN_GATE
    return tuple(path.group(1).split("/"))


def _gates_before_spawn(js: str) -> bool:
    """Whether the plugin returns early on a missing database before it spawns the script."""
    gate = re.search(r"if \(!existsSync\(([^;]*)\)\) return;", js)
    spawn = js.find("code-atlas-poke`")
    if not gate or not 0 <= gate.start() < spawn:
        return False
    return all(f'"{segment}"' in gate.group(1) for segment in _gate_segments())


def test_every_codex_command_starts_with_the_plugin_gate() -> None:
    import gen_skill

    hooks = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))["hooks"]
    commands = [h["command"] for e in hooks["PostToolUse"] for h in e["hooks"]]
    assert commands and all(c.startswith(gen_skill.PLUGIN_GATE) for c in commands), commands
    assert {c.rpartition("exec ")[2] for c in commands} == HOOK_COMMANDS


def test_the_opencode_plugin_tests_the_same_database_before_it_spawns() -> None:
    assert _gate_segments() == (".code-atlas", "graph.db")
    assert _gates_before_spawn(OPENCODE_PLUGIN.read_text(encoding="utf-8"))
    # R6.5: the pre-427 plugin spawned unconditionally, and the check sees it.
    ungated = "export const X = async ({ $ }) => ({ a: async () => { await $`code-atlas-poke`; }});"
    directory_only = ungated.replace("await", 'if (!existsSync(".code-atlas")) return; await')
    assert not _gates_before_spawn(ungated)
    assert not _gates_before_spawn(directory_only)
