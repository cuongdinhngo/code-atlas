"""Non-modifier decorators → REFERENCES — inventory row ``decorator-references``."""


def guard(fn):
    return fn


def audit(flag):
    def wrap(fn):
        return fn

    return wrap


@guard
def handler() -> None:
    return None


@audit("x")
def audited() -> None:
    return None


class Service:
    @guard
    def run(self) -> None:
        return None

    @staticmethod
    def util() -> int:
        return 1
