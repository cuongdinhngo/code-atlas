"""Two bases — inventory row ``class-multiple-inheritance``."""


class Readable:
    def read(self) -> str:
        return ""


class Writable:
    def write(self, data: str) -> None:
        pass


class ReadWriter(Readable, Writable):
    def flush(self) -> None:
        pass
