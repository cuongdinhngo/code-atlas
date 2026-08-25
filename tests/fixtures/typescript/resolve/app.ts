// Integration fixture: a direct ESM import; `new User()` must come back RESOLVED to models.ts::User.
import { User } from "./models";

export function make(): User {
  const created = new User();
  created.greet(); // the receiver's type is another file's fact: bare + HEURISTIC, the core links it
  return created;
}
