"""``obj.m()`` / ``self.m()`` / ``super().m()`` — inventory row ``call-method``."""


class Base:
    def hook(self) -> int:
        return 1


class Child(Base):
    def hook(self) -> int:
        return super().hook()

    def run(self) -> int:
        return self.hook()


def call_on(obj: Child) -> int:
    return obj.hook()
