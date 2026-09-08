"""Bare-name assigns inside methods are locals, not class Property — ticket 229."""


class Marker:
    pass


class Widget:
    kind = "w"
    tagged: Marker

    def render(self):
        tmp = self.kind
        if True:
            nested_if = 1
        for _ in range(1):
            nested_for = 2
        with open(__file__):
            nested_with = 3

        def inner():
            nested_def = 4
            return nested_def

        return tmp

    def typed(self) -> None:
        local: Marker = Marker()
