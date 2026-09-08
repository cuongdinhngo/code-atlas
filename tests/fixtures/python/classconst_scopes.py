"""Scope-symmetric constant rule (234 AC3): same signals at module and class scope."""

from typing import Final

MODULE_UPPER = 1
module_final: Final[int] = 2


class Box:
    CLASS_UPPER = 3
    class_final: Final[int] = 4
    mutable: int = 5
