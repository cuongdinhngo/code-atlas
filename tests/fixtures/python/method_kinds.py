"""Instance / static / class / property methods — inventory row ``method-kinds``."""


class Widget:
    def instance_m(self) -> int:
        return 1

    @staticmethod
    def static_m() -> int:
        return 2

    @classmethod
    def class_m(cls) -> int:
        return 3

    @property
    def prop_m(self) -> int:
        return 4
