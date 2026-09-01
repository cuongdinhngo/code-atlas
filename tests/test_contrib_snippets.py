"""What `contrib/` offers is installable by hand, and code-atlas installs none of it (task 200).

036 and 099 both settled the stance and `docs/TOOLS.md` states it: code-atlas emits a file, the host
decides. AC3's four clauses and AC6 are one assertion each — a single aggregate row lets a clause
ship unproven behind a green tick.
"""

import re
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import gen_skill  # noqa: E402

CONTRIB = REPO / "contrib"
# A directory offering an agent something: it has a README beside a snippet or plugin file.
OFFERS = sorted(
    d for d in CONTRIB.iterdir() if d.is_dir() and (d / "README.md").is_file()
)
# An install target a README names: a backticked path with a slash, rooted at `~` or a dotdir.
TARGET = re.compile(r"`(~?[./][\w./~-]*/[\w.-]+)`")
# `.code-atlas/` is code-atlas's OWN index dir, not a host's settings; AC3d is about the latter.
OWN = ".code-atlas/"
# The shape a hook filter uses to claim a language.
GLOB = re.compile(r"\*(\.[A-Za-z0-9_]+)\b")


def _readme(directory: Path) -> str:
    return (directory / "README.md").read_text(encoding="utf-8")


def _targets(directory: Path) -> list[str]:
    return [t for t in TARGET.findall(_readme(directory)) if OWN not in t]


def test_the_sweep_is_not_vacuous() -> None:
    # R6.5: an empty `OFFERS` would pass every parametrised assertion below in silence.
    assert len(OFFERS) >= 4, f"expected the offered directories, found {[d.name for d in OFFERS]}"


@pytest.mark.parametrize("directory", OFFERS, ids=lambda d: d.name)
def test_the_offer_exists_beside_its_readme(directory: Path) -> None:
    """AC3a — each offer ships the file it describes, not only prose about one."""
    beside = [p for p in directory.iterdir() if p.is_file() and p.name != "README.md"]
    assert beside, f"{directory.name}/ offers a README and nothing to install"


@pytest.mark.parametrize("directory", OFFERS, ids=lambda d: d.name)
def test_the_readme_names_the_file_it_belongs_in(directory: Path) -> None:
    """AC3b — a snippet whose destination is unstated is not installable by hand."""
    assert _targets(directory), (
        f"{directory.name}/README.md names no install target path"
    )


@pytest.mark.parametrize("directory", OFFERS, ids=lambda d: d.name)
def test_the_readme_carries_a_hand_install_step(directory: Path) -> None:
    """AC3c — the target alone is not a procedure; there must be numbered steps."""
    steps = [ln for ln in _readme(directory).splitlines() if re.match(r"^\d+\. ", ln)]
    assert len(steps) >= 2, f"{directory.name}/README.md has {len(steps)} numbered install step(s)"


def test_no_code_atlas_command_writes_to_any_install_target() -> None:
    """AC3d — the never-installed stance, checked against the paths the READMEs actually name."""
    targets = {t for d in OFFERS for t in _targets(d)}
    assert targets, "no install targets were extracted — the check would be vacuous"
    sources = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted((REPO / "code_atlas").rglob("*.py"))
    )
    named = sorted(t for t in targets if t in sources)
    assert not named, f"code_atlas/ names a host install target: {named}"


def test_nothing_offered_claims_a_language_this_repo_cannot_index() -> None:
    """AC6 — every suffix a `contrib/` file claims is owned by a shipped adapter."""
    owned = {s for group in gen_skill.declared_extensions().values() for s in group}
    claimed = {
        suffix
        for path in sorted(CONTRIB.rglob("*"))
        if path.is_file()
        for suffix in GLOB.findall(path.read_text(encoding="utf-8", errors="ignore"))
    }
    assert claimed, "no suffix claim was found at all — the check would be vacuous"
    assert claimed <= owned, f"contrib/ claims suffixes no adapter owns: {sorted(claimed - owned)}"


def test_the_console_scripts_the_snippets_call_are_declared() -> None:
    """A snippet calling a command the package does not ship is an offer that cannot work."""
    scripts = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    declared = set(scripts["project"]["scripts"])
    called = {
        name
        for path in sorted(CONTRIB.rglob("*"))
        if path.is_file()
        for name in declared
        if name in path.read_text(encoding="utf-8", errors="ignore")
    }
    assert called, "no console script is called from contrib/ at all"
    assert called <= declared
