"""async def at module and class level — inventory row ``async-def``."""


async def fetch() -> int:
    return 1


class Service:
    async def run(self) -> int:
        return await fetch()
