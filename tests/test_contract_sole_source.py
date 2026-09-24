"""R3.2 guard: the contract vocabulary is declared once, in contract.py, and nowhere else.

Fails when a schema-consuming core module re-declares a kind or field list instead of importing it,
which is how AC2's "sole source of truth" stays true as store/indexer/resolver get written.
"""

import ast
from pathlib import Path

import pytest

from code_atlas import contract

CORE = Path(contract.__file__).parent

VOCABULARY = frozenset(
    contract.NODE_KINDS
    + contract.EDGE_KINDS
    + contract.CONFIDENCE_TIERS
    + contract.NODE_FIELDS
    + contract.EDGE_FIELDS
)


def consumers() -> list[Path]:
    """The core modules that consume the schema (R3.2), including every tool module."""
    modules = [CORE / name for name in ("store.py", "indexer.py", "resolver.py", "adapter.py")]
    return modules + sorted((CORE / "tools").rglob("*.py"))


def collection_literals(tree: ast.AST) -> list[list[str]]:
    """Vocabulary strings found inside each list/tuple/set literal and each dict's keys."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            elements = list(node.elts)
        elif isinstance(node, ast.Dict):
            elements = [key for key in node.keys if key is not None]
        else:
            continue
        found.append(
            [
                element.value
                for element in elements
                if isinstance(element, ast.Constant) and element.value in VOCABULARY
            ]
        )
    return found


def test_the_vocabulary_is_not_empty() -> None:
    # Guards the guard: an empty vocabulary would make every check below pass vacuously.
    # +Table +Column +WRITES (022, v9); +ForeignKey (236, v10); +ALTERS (321, v11); +DELETES (328, v12)
    assert len(VOCABULARY) == 48
    assert len(consumers()) >= 5


@pytest.mark.parametrize("module", consumers(), ids=lambda path: path.name)
def test_consumer_does_not_redeclare_the_contract_vocabulary(module: Path) -> None:
    tree = ast.parse(module.read_text(encoding="utf-8"))

    for literal in collection_literals(tree):
        assert len(literal) < 2, (
            f"{module.relative_to(CORE.parent)} re-declares contract vocabulary {literal} — "
            "import it from code_atlas.contract instead (R3.2)"
        )
