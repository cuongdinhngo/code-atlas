"""Smoke test: the code_atlas package imports."""

import code_atlas


def test_import_code_atlas() -> None:
    assert code_atlas.__name__ == "code_atlas"
