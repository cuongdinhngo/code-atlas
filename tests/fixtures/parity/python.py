from typing import Final


class User:
    pass


class Repo:
    TIMEOUT: Final[int] = 30

    owner: User

    def find(self, u: User) -> User:
        return u

    @staticmethod
    def tag(name: str, n: int) -> str:
        return name

    def run(self) -> str:
        return Repo.tag("name", 3)
