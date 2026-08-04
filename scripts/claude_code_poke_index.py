#!/usr/bin/env python3
"""Thin wrapper — prefer the ``code-atlas-poke`` console script after install."""

from __future__ import annotations

from code_atlas.hooks.poke import main

if __name__ == "__main__":
    raise SystemExit(main())
