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


def core_modules() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


def test_the_guard_has_something_to_check() -> None:
    # Guards the guard: an empty module list or an empty name list would pass vacuously.
    assert len(core_modules()) == 32
    assert len(LANGUAGE_NAMES) == 9
    assert LANGUAGE_NAME.search("a PHP file") and LANGUAGE_BRANCH.search('if language == "x":')


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
