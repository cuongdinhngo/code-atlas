"""232 AC1/AC2 — User, Repo.owner:User, get() -> User. Property + return = 2 REFERENCES today."""


class User:
    pass


class Repo:
    owner: User

    def get(self) -> User:
        return User()
