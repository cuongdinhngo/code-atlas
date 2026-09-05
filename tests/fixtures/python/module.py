"""Module-level def and class — inventory row ``module``."""


class Greeter:
    def greet(self) -> str:
        return "hi"


def make_greeter() -> Greeter:
    return Greeter()
