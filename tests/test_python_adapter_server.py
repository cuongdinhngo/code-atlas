"""Task 217 AC3: the Python adapter refuses to launch on a grammar it does not parse.

``ast.parse`` is bound to the running interpreter, so a wrong ``CA_PYTHON_CMD`` host would silently
produce different rows for the same file (R4.2). ``index.py`` therefore checks the floor before it
serves, and this is the check on that check.

In a ``test_*`` module because pytest's default ``python_files`` is ``test_*.py``: the same guard in
``tests/python_adapter_cli.py`` was collected only when that path was named on the command line, so
a full-suite run proved nothing (R6.5 — an absent check is not a pass).
"""

from __future__ import annotations

import importlib.util

import pytest

from tests.python_adapter_cli import ENTRY, needs_python

pytestmark = needs_python


def test_launch_refuses_python_below_3_12(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3 — wrong CA_PYTHON_CMD host fails before handshake (R4.2)."""
    spec = importlib.util.spec_from_file_location("ca_py_index", ENTRY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod.sys, "version_info", (3, 11, 9, "final", 0))
    assert mod.main(["--server"]) == 2
