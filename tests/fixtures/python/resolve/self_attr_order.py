"""``self.<attr>`` types are what the class declares, not what the last method visited said."""


class Service:
    def run(self) -> int:
        return 1


class Other:
    def run(self) -> int:
        return 2


class InitFirst:
    def __init__(self) -> None:
        self._svc: Service = Service()

    def call_it(self) -> int:
        return self._svc.run()


class InitLast:
    def call_it(self) -> int:
        return self._svc.run()

    def __init__(self) -> None:
        self._svc: Service = Service()


class AnnotationSurvivesAnUntypedWrite:
    def __init__(self) -> None:
        self._svc: Service = Service()

    def reset(self) -> None:
        self._svc = make()  # type: ignore[name-defined]

    def call_it(self) -> int:
        return self._svc.run()


class TwoMethodsDisagree:
    def a(self) -> None:
        self._svc: Service = Service()

    def b(self) -> None:
        self._svc: Other = Other()

    def call_it(self) -> int:
        return self._svc.run()
