// 232 AC1/AC2 — same three declarations as the Python/PHP fixtures.
export class User {}

export class Repo {
  owner: User;

  get(): User {
    return this.owner;
  }
}
