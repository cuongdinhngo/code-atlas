// Integration fixture: a direct ESM import; `new User()` must come back RESOLVED to models.ts::User.
import { User } from "./models";

export function make(): User {
  const created = new User();
  created.greet(); // receiver typed by `new User()` -> models.ts::User::greet, RESOLVED (task 153)
  return created;
}
