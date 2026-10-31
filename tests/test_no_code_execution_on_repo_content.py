"""424 — SEC-IN-07: nothing under `code_atlas/` or `adapters/` executes or loads repo content.

A parser reads text; it never runs it. The guard refuses, by syntax tree for Python and by
comment-stripped line for the JS and PHP adapters: `eval` / `exec`, the `pickle` / `marshal` /
`shelve` modules, `yaml.load` without a safe loader, a dynamic import (`importlib.import_module`,
`__import__`), `new Function`, a `require` / `import()` / `include` of a non-literal and a PHP
`assert` of a string. `importlib.metadata` reads installed packages and is fine.

A site that is legitimate is allow-listed below by exact path and construct, with the reason, and a
stale entry fails (an unused exception is a standing hole). Planted sources prove each arm refuses.
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKIPPED = ("/vendor/", "/node_modules/", "tests/fixtures/")
UNSAFE_MODULES = frozenset({"pickle", "cPickle", "marshal", "shelve", "dill"})
SAFE_LOADERS = frozenset({"SafeLoader", "CSafeLoader"})

# (path, construct) -> why this one site cannot run repo text.
ALLOWED = {
    ("code_atlas/limits.py", "import_module"): (
        "imports the literal stdlib module `re._parser` to read a pattern's syntax tree"
    ),
    ("adapters/php/index.php", "require"): (
        "requires Composer's autoloader at a path built from `__DIR__`, never from repo content"
    ),
}


def tracked(*roots: str, suffixes: tuple[str, ...]) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *roots],
        cwd=REPO,
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    ).stdout
    return sorted(
        f
        for f in out.split("\0")
        if f.endswith(suffixes) and not any(part in f"/{f}" for part in SKIPPED)
    )


def _dotted(node: ast.expr) -> str:
    return ast.unparse(node)


def python_constructs(source: str) -> list[tuple[str, int]]:
    """(construct, line) of every refused thing in ``source``."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(ast.parse(source)):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            found += [
                ("unsafe-module", line)
                for a in node.names
                if a.name.split(".")[0] in UNSAFE_MODULES
            ]
        elif (
            isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in UNSAFE_MODULES
        ):
            found.append(("unsafe-module", line))
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            if name in ("eval", "exec"):
                found.append((name, line))
            elif name in ("__import__", "importlib.import_module", "import_module"):
                found.append(("import_module", line))
            elif name in ("yaml.unsafe_load", "yaml.full_load"):
                found.append(("yaml.load", line))
            elif name == "yaml.load":
                loader = [k.value for k in node.keywords if k.arg == "Loader"]
                loader += node.args[1:2]
                if not loader or _dotted(loader[0]).split(".")[-1] not in SAFE_LOADERS:
                    found.append(("yaml.load", line))
    return found


JS_PATTERNS = {
    "eval": re.compile(r"\beval\s*\("),
    "new-function": re.compile(r"\bnew\s+Function\s*\("),
    "require": re.compile(r"\brequire\s*\(\s*(?![\"'])"),
    "import": re.compile(r"\bimport\s*\(\s*(?![\"'])"),
}
PHP_PATTERNS = {
    "eval": re.compile(r"\beval\s*\("),
    "assert": re.compile(r"\bassert\s*\(\s*[\"']"),
    "require": re.compile(r"(?:^|[;{}\s])(?:include|require)(?:_once)?\b\s*\(?\s*(?![\"'(])\S"),
}


def _code_lines(text: str) -> list[tuple[int, str]]:
    """Lines that are code: a comment-only line is dropped, a trailing `//` comment is cut."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("//", "*", "/*", "#")):
            continue
        out.append((n, re.sub(r"\s//.*$", "", line)))
    return out


def text_constructs(text: str, patterns: dict[str, re.Pattern[str]]) -> list[tuple[str, int]]:
    return [
        (name, n)
        for n, line in _code_lines(text)
        for name, pattern in patterns.items()
        if pattern.search(line)
    ]


def _unallowed(
    path: str, constructs: list[tuple[str, int]], used: set[tuple[str, str]]
) -> list[str]:
    found = []
    for construct, line in constructs:
        if (path, construct) in ALLOWED:
            used.add((path, construct))
        else:
            found.append(f"{path}:{line}: {construct}")
    return found


def test_no_python_site_executes_or_imports_repo_content() -> None:
    files = tracked("code_atlas", "adapters", suffixes=(".py",))
    assert len(files) > 50, "the reader found almost no Python; this would pass vacuously"
    used: set[tuple[str, str]] = set()
    found = []
    for path in files:
        source = (REPO / path).read_text(encoding="utf-8")
        found += _unallowed(path, python_constructs(source), used)
    assert found == []
    assert ("code_atlas/limits.py", "import_module") in used, "the allow-list entry is stale"


def test_no_js_or_php_adapter_site_evaluates_repo_content() -> None:
    js = tracked("adapters", suffixes=(".js", ".ts", ".mjs", ".cjs"))
    php = tracked("adapters", suffixes=(".php",))
    assert len(js) >= 8 and len(php) >= 8, "the reader found almost no adapter source"
    used: set[tuple[str, str]] = set()
    found = []
    for path, patterns in [(p, JS_PATTERNS) for p in js] + [(p, PHP_PATTERNS) for p in php]:
        text = (REPO / path).read_text(encoding="utf-8", errors="replace")
        found += _unallowed(path, text_constructs(text, patterns), used)
    assert found == []
    assert ("adapters/php/index.php", "require") in used, "the allow-list entry is stale"


PLANTED_PYTHON = {
    "eval": "x = eval(text)",
    "exec": "exec(source)",
    "pickle import": "import pickle",
    "marshal from-import": "from marshal import loads",
    "shelve import": "import shelve",
    "yaml.load with no loader": "import yaml\nyaml.load(text)",
    "yaml.load with the full loader": "import yaml\nyaml.load(text, Loader=yaml.FullLoader)",
    "yaml.unsafe_load": "import yaml\nyaml.unsafe_load(text)",
    "importlib.import_module": "import importlib\nimportlib.import_module(name)",
    "__import__": "__import__(name)",
}
PLANTED_JS = {
    "eval": "const v = eval(src);",
    "new Function": "const f = new Function('a', body);",
    "require of a variable": "const m = require(name);",
    "require of a built path": "const m = require(dir + '/x');",
    "import() of a variable": "const m = await import(name);",
}
PLANTED_PHP = {
    "eval": "<?php eval($code);",
    "assert of a string": "<?php assert('$x > 1');",
    "include of a variable": "<?php include $path;",
    "require_once of a call": "<?php require_once dirname($f) . '/x.php';",
}


def test_a_planted_site_is_refused() -> None:
    for case, source in PLANTED_PYTHON.items():
        assert python_constructs(source), f"python: {case} was accepted"
    for case, source in PLANTED_JS.items():
        assert text_constructs(source, JS_PATTERNS), f"js: {case} was accepted"
    for case, source in PLANTED_PHP.items():
        assert text_constructs(source, PHP_PATTERNS), f"php: {case} was accepted"


def test_what_the_adapters_legitimately_use_is_accepted() -> None:
    fine_python = (
        "import importlib.metadata\nimportlib.metadata.version('x')\nimport yaml\n"
        "yaml.load(t, Loader=yaml.SafeLoader)\nyaml.safe_load(t)\n"
    )
    assert python_constructs(fine_python) == []
    assert (
        text_constructs('const fs = require("node:fs");\nrequire.main === module', JS_PATTERNS)
        == []
    )
    assert text_constructs("// never eval( a file\n * eval(\n", JS_PATTERNS) == []
    assert text_constructs("<?php assert($n instanceof X);\nrequire 'a.php';", PHP_PATTERNS) == []
