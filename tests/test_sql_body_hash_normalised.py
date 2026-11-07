"""Task 437 — a SQL body fingerprint ignores formatting and still sees a changed body.

Keyword case, a needless ``[bracket]`` or ``"quote"``, ``CREATE OR ALTER`` against ``CREATE`` and a
statement reflowed across lines define the same routine, so they keep one ``body_hash``. A changed
predicate, column list or literal is a different body. Driven through the real adapter.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
SQL_ENTRY = Path(__file__).resolve().parent.parent / "adapters" / "sql" / "index.js"
pytestmark = pytest.mark.skipif(NODE is None, reason=f"needs the Node CLI to run {SQL_ENTRY}")

BASE = (
    "CREATE PROCEDURE dbo.GetOrders @Id int AS\n"
    "BEGIN\n"
    "  SELECT Id, [Order Date], Note FROM dbo.Orders WHERE Id = @Id AND Note = 'Mixed  Case'\n"
    "END\nGO\n"
)

SAME = {
    "keyword_case": BASE.replace("SELECT", "select").replace("WHERE", "where").replace(
        "BEGIN", "begin"
    ),
    "brackets": BASE.replace("dbo.GetOrders", "[dbo].[GetOrders]").replace("Id,", "[Id],"),
    "double_quotes": BASE.replace("Note FROM", '"Note" FROM'),
    "or_alter": BASE.replace("CREATE PROCEDURE", "CREATE OR ALTER PROCEDURE"),
    "reflow": (
        "CREATE PROCEDURE dbo.GetOrders\n  @Id int\nAS\nBEGIN\n"
        "  SELECT Id,\n         [Order Date],\n         Note\n    FROM dbo.Orders\n"
        "   WHERE Id=@Id\n     AND Note = 'Mixed  Case'\nEND\nGO\n"
    ),
    "comments": BASE.replace("BEGIN\n", "BEGIN -- start\n  /* the read */\n"),
    "or_alter_split_after_or": BASE.replace("CREATE PROCEDURE", "CREATE OR\nALTER PROCEDURE"),
    "or_alter_split_after_create": BASE.replace(
        "CREATE PROCEDURE", "CREATE -- the routine\n  OR ALTER PROCEDURE"
    ),
    "alter_header": BASE.replace("CREATE PROCEDURE", "ALTER PROCEDURE"),
    "glued_bracket": BASE.replace("FROM dbo.Orders", "FROM[dbo].[Orders]"),
}

DIFFERENT = {
    "predicate": BASE.replace("Id = @Id", "Id > @Id"),
    "column_list": BASE.replace("Id, [Order Date], Note", "Id, Note"),
    "literal_case": BASE.replace("'Mixed  Case'", "'mixed  case'"),
    "literal_spacing": BASE.replace("'Mixed  Case'", "'Mixed Case'"),
    "quoted_name_with_space": BASE.replace("[Order Date]", "[OrderDate]"),
    "a_column_named_created": BASE.replace("Note FROM", "Note, created FROM"),
    "alias_not_unicode_literal": BASE.replace("= 'Mixed  Case'", "= N 'Mixed  Case'"),
}


def body_hash(tmp_path: Path, name: str, text: str) -> str:
    path = tmp_path / f"{name}.sql"
    path.write_text(text, encoding="utf-8")
    out = subprocess.run(
        [str(NODE), str(SQL_ENTRY), "--file", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    nodes = [n for n in json.loads(out)["nodes"] if n["qualified_name"] == "dbo.GetOrders"]
    assert len(nodes) == 1, nodes
    return str(nodes[0]["extra"]["body_hash"])


@pytest.mark.parametrize("variant", sorted(SAME))
def test_ac3_a_formatting_only_variant_keeps_its_hash(tmp_path: Path, variant: str) -> None:
    """AC3 (proving test): each formatting-only rewrite hashes as the original."""
    assert body_hash(tmp_path, variant, SAME[variant]) == body_hash(tmp_path, "base", BASE)


@pytest.mark.parametrize("variant", sorted(DIFFERENT))
def test_ac3_a_changed_body_moves_its_hash(tmp_path: Path, variant: str) -> None:
    assert body_hash(tmp_path, variant, DIFFERENT[variant]) != body_hash(tmp_path, "base", BASE)


def test_create_or_alter_inside_a_literal_is_kept(tmp_path: Path) -> None:
    """Only code is normalised: the words inside a string are data."""
    said = BASE.replace("'Mixed  Case'", "'create or alter'")
    plain = BASE.replace("'Mixed  Case'", "'create'")
    assert body_hash(tmp_path, "said", said) != body_hash(tmp_path, "plain", plain)
