"""Protocol / ABC → Interface + IMPLEMENTS — inventory row ``protocol-abc``."""

from abc import ABC, abstractmethod
from typing import Protocol


class Drawable(Protocol):
    def draw(self) -> None: ...


class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...


class Circle(Drawable):
    def draw(self) -> None:
        return None


class Square(Shape):
    def area(self) -> float:
        return 1.0
