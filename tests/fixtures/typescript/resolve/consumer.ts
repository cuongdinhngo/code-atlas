// Integration fixture: imports through the barrel; `new User()` must resolve through the ALIASES
// edge to models.ts::User (RESOLVED at the defining module), not stop at barrel.ts.
import { User } from "./barrel";

export function build(): User {
  return new User();
}
