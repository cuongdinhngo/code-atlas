"""Task 227 fixtures: annotated / ``Foo()``-bound receivers promote member calls; forgetfulness too."""


class Service:
    def run(self) -> int:
        return 1


def build_annotated(svc: Service) -> int:
    return svc.run()


def build_constructed() -> int:
    svc = Service()
    return svc.run()


def build_forgotten() -> int:
    svc: Service = Service()
    svc = unknown()  # type: ignore[name-defined]
    return svc.run()


def build_attr(svc: Service) -> None:
    class Holder:
        def __init__(self) -> None:
            self._svc: Service = svc

        def go(self) -> int:
            return self._svc.run()

    Holder().go()
