#!/usr/bin/env python3
"""Task 371's measure-first: how many TS/JS and Python string literals begin a SQL write or EXEC?

The PHP adapter reads a literal that *begins* a T-SQL statement (278/281/335, `SqlLiteral.php`).
Before porting that recogniser, 371 counts what it would read on the pinned samples (R6.3): every
literal led by `INSERT INTO` · `UPDATE` · `MERGE INTO` · `DELETE FROM` · `EXEC`, how many of those
the recogniser's clause guard accepts, how many it rejects as prose, and how many accepted targets
name a table or procedure the repo's own T-SQL declares — the only ones an edge could link to.

Read-only, no network, deterministic. Python literals are read with `ast`; TS/JS literals with the
TS adapter's pinned `typescript` package. Usage::

    python scripts/sql_literal_report.py <checkout> [<checkout> …]
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TS_MODULES = _REPO / "adapters" / "typescript" / "node_modules"
_SKIP_DIRS = {"node_modules", ".git", "vendor", "dist", "build", "__pycache__", ".venv"}
_TS_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")

# The recogniser's shape, ported from adapters/php/src/SqlLiteral.php (keyword → clause guard).
_HEAD = re.compile(
    r"\A(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?)\s+", re.I
)
_NAME_PART = r'(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)'
_NAME = re.compile(_NAME_PART + r"(?:\s*\.\s*" + _NAME_PART + r")*")
_CLAUSES = {
    "insert": re.compile(
        r"\A\s*(?:\(|values\b|select\b|default\s+values\b|output\b|with\s*\()", re.I
    ),
    "update": re.compile(r"\A\s*(?:set\b|with\s*\()", re.I),
    "merge": re.compile(
        r"\A\s*(?:with\s*\([^)]*\)\s*)?(?:as\s+)?(?:[A-Za-z_]\w*\s+)?using\b", re.I
    ),
    "delete": re.compile(r"\A\s*(?:where\b|output\b|with\s*\()", re.I),
    "exec": re.compile(r"\A\s+(?:@|\?|:[A-Za-z_]|N?'|-?\d)"),
}
_DDL = re.compile(
    r"\bcreate\s+(?:or\s+alter\s+)?(table|proc(?:edure)?)\s+(" + _NAME.pattern + ")", re.I
)


def read(text: str, closed: bool) -> tuple[str, str] | None:
    """`(verb, target)` the literal begins, or None — the PHP recogniser's decision."""
    m = _HEAD.match(text)
    if m is None:
        return None
    verb = m.group(2).split()[0].lower()
    verb = "exec" if verb.startswith("exec") else verb
    start = m.end()
    if verb == "exec":
        rc = re.compile(r"@[A-Za-z_]\w*\s*=\s*").match(text, start)
        start = rc.end() if rc else start
    n = _NAME.match(text, start)
    if n is None:
        return None
    rest = text[n.end() :]
    parts = [p.strip('[]"') for p in re.findall(_NAME_PART, n.group(0))]
    qualified = len(parts) > 1
    if _CLAUSES[verb].match(rest):
        return (verb, ".".join(parts)) if verb != "exec" or qualified else None
    if not qualified or verb not in ("delete", "exec"):
        return None
    ended = closed if rest == "" else re.match(r"\A\s*(?:;|\Z)", rest) is not None
    return (verb, ".".join(parts)) if ended else None


def _files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.suffix in suffixes
        and p.is_file()
        and not _SKIP_DIRS.intersection(p.relative_to(root).parts)
    )


def python_literals(path: Path) -> list[tuple[str, bool]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError):
        return []
    out: list[tuple[str, bool]] = []
    heads: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr) and node.values:
            first = node.values[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.append((first.value, len(node.values) == 1))
                heads.add(id(first))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in heads:
            out.append((node.value, True))
    return out


_TS_DUMP = r"""
const ts = require(process.argv[1]); const fs = require('fs');
for (const file of JSON.parse(fs.readFileSync(0, 'utf8'))) {
  let text; try { text = fs.readFileSync(file, 'utf8'); } catch { continue; }
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, false);
  const visit = (n) => {
    const whole = ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n);
    if (whole) console.log(JSON.stringify([n.text, true]));
    else if (ts.isTemplateExpression(n)) console.log(JSON.stringify([n.head.text, false]));
    n.forEachChild(visit);
  };
  visit(sf);
}
"""


def ts_literals(paths: list[Path]) -> list[tuple[str, bool]]:
    if not paths:
        return []
    done = subprocess.run(
        ["node", "-e", _TS_DUMP, str(_TS_MODULES / "typescript")],
        input=json.dumps([str(p) for p in paths]),
        capture_output=True,
        text=True,
        check=True,
    )
    return [tuple(json.loads(line)) for line in done.stdout.splitlines()]  # type: ignore[misc]


def measure(root: Path) -> dict[str, object]:
    ddl = {
        m.group(2).replace("[", "").replace("]", "").lower()
        for p in _files(root, (".sql",))
        for m in _DDL.finditer(p.read_text(encoding="utf-8", errors="replace"))
    }
    rows: dict[str, object] = {"sample": root.name, "tsql_objects_declared": len(ddl)}
    for language, literals in (
        ("python", [lit for p in _files(root, (".py",)) for lit in python_literals(p)]),
        ("typescript", ts_literals(_files(root, _TS_SUFFIXES))),
    ):
        led = [(t, c) for t, c in literals if _HEAD.match(t)]
        read_ok = [r for r in (read(t, c) for t, c in led) if r is not None]
        linkable = [r for r in read_ok if r[1].lower() in ddl or f"dbo.{r[1].lower()}" in ddl]
        rows[language] = {
            "literals": len(literals),
            "keyword_led": len(led),
            "statements": len(read_ok),
            "prose": len(led) - len(read_ok),
            "linkable": len(linkable),
            "statement_examples": sorted({f"{v} {t}" for v, t in read_ok})[:5],
        }
    return rows


def main(argv: list[str]) -> int:
    for arg in argv:
        print(json.dumps(measure(Path(arg)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
