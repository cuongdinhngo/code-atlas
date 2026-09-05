"""Param / return / AnnAssign named types → REFERENCES — inventory row ``annotation-references``."""

from typing import Optional, Union


class User:
    pass


class Repo:
    owner: User
    tag: str

    def get(self, key: int) -> User:
        return User()

    def find(self, name: str) -> Optional[User]:
        return None

    def merge(self, a: User | None, b: Union[User, Repo]) -> list[User]:
        return [a] if a else []
