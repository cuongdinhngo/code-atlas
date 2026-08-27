// R6.2 case `module-esm`: module-scoped symbols (no FQNs) + an ESM import. Answers 128 Q1's
// "module-path-anchored qname" half and Q2's "same-file RESOLVED vs imported bare" split.
import { Logger, log } from "./logger";

export interface Greeter {
  greet(): string;
}

export class User implements Greeter {
  name: string;

  greet(): string {
    return this.describe();
  }

  describe(): string {
    return "user " + this.name;
  }
}

export function makeUser(): User {
  const created = new User();
  new Logger();
  log(created); // bare call to an imported function — emitted bare for the core to link (R3.3)
  created.greet(); // receiver typed by `new User()` -> User::greet, RESOLVED via the type table (153)
  return created;
}
