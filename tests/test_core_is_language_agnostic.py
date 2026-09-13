"""R1.1/R1.5 guard: the core resolves adapters by suffix alone, so it names no language at all.

The CI grep-gate (`ci.yml`) catches one spelling of one branch. This asserts the stronger claim the
ticket actually makes — that no language name reaches `code_atlas/` in any form, comment and
docstring included, because a name is what a branch is eventually written against.
"""

import re
from pathlib import Path

import pytest

from code_atlas import contract

CORE = Path(contract.__file__).parent

# Every language the plan names, plus the parsers behind them. "Python" is deliberately absent: the
# core is written in it, so the token cannot tell a leak from the host language.
LANGUAGE_NAMES = (
    "php",
    "typescript",
    "javascript",
    "csharp",
    "dotnet",
    "nikic",
    "roslyn",
    "ts-morph",
    "jedi",
)
LANGUAGE_NAME = re.compile(r"\b(" + "|".join(LANGUAGE_NAMES) + r")\b", re.IGNORECASE)

# The CI gate's regex, verbatim (ci.yml) — run here so a red build is not the first time it is seen.
LANGUAGE_BRANCH = re.compile(r"if[^\n]*\blanguage\b[^\n]*==|match[^\n]*\blanguage\b")

# A language's module-file convention is the leak the name grep above cannot see (230): the core is
# written in Python, so the token `python` proves nothing — the package initialiser and a bare `.py`
# literal do. `build_info.py`'s `*.py` reads this package's own source, not an indexed repo's.
MODULE_CONVENTION = re.compile(r"__init__\.py|['\"]\.py['\"]")


def core_modules() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


def test_the_guard_has_something_to_check() -> None:
    # Guards the guard: an empty module list or an empty name list would pass vacuously.
    # +1 each: coverage (160), cli (176), config_provenance (175), check_column_defaults (194),
    # trace_capability (199), onboarding scope (206), community (211), provenance (209),
    # orientation (207), audience (210), sequence_diagram (225), er_diagram (224), preflight (237),
    # fit (260), symbol_role (262)
    assert len(core_modules()) == 87
    assert len(LANGUAGE_NAMES) == 9
    assert LANGUAGE_NAME.search("a PHP file") and LANGUAGE_BRANCH.search('if language == "x":')
    assert MODULE_CONVENTION.search('(f"{rel}.py", f"{rel}/__init__.py")')


@pytest.mark.parametrize("module", core_modules(), ids=lambda path: path.name)
def test_no_core_module_names_a_language(module: Path) -> None:
    found = LANGUAGE_NAME.findall(module.read_text(encoding="utf-8"))

    assert not found, (
        f"{module.relative_to(CORE.parent)} names {sorted(set(found))} — the core resolves "
        "adapters by suffix alone; a language names itself in its handshake (R1.1, R1.5)"
    )


@pytest.mark.parametrize("module", core_modules(), ids=lambda path: path.name)
def test_no_core_module_branches_on_a_language(module: Path) -> None:
    for number, line in enumerate(module.read_text(encoding="utf-8").splitlines(), start=1):
        assert not LANGUAGE_BRANCH.search(line), (
            f"{module.relative_to(CORE.parent)}:{number} trips the CI R1.1 gate — fix the "
            "contract, not the core"
        )


@pytest.mark.parametrize("module", core_modules(), ids=lambda path: path.name)
def test_no_core_module_spells_a_module_file_convention(module: Path) -> None:
    """230 — the hint counter mapped a dotted name to `<rel>.py` / `<rel>/__init__.py`: one
    language's layout rule applied to an indexed repo, invisible to the name grep above because
    the core is written in that language. Derive keys from the indexed paths instead."""
    found = MODULE_CONVENTION.findall(module.read_text(encoding="utf-8"))

    assert not found, (
        f"{module.relative_to(CORE.parent)} spells {sorted(set(found))} — how a module name maps "
        "to a file is the adapter's rule, not the core's (R1.1)"
    )
