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
        found |= {cmd for cmd in HOOK_COMMANDS if f'"{cmd}"' in text}
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
