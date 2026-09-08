"""External import must stay bare (AC3)."""

from typing import Protocol


class Marker(Protocol):
    def run(self) -> None: ...


class UsesExternal(Marker):
    def run(self) -> None:
        return None
