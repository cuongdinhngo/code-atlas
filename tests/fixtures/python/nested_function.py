"""Nested function inside a function — inventory row ``nested-function``."""


def outer(n: int) -> int:
    def inner(x: int) -> int:
        return x + 1

    return inner(n)
