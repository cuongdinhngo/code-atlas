export class User {}

export class Repo {
  static readonly TIMEOUT = 30;

  private owner: User;

  private static count: number = 0;

  find(u: User): User {
    return u;
  }

  private static tag(name: string, n: number): string {
    return name;
  }

  run(): string {
    Repo.count = Repo.count + 1;
    return Repo.tag("name", 3);
  }
}
