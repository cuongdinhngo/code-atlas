export class User {}

export class Repo {
  static readonly TIMEOUT = 30;

  private owner: User;

  find(u: User): User {
    return u;
  }

  private static tag(name: string, n: number): string {
    return name;
  }

  run(): string {
    return Repo.tag("name", 3);
  }
}
