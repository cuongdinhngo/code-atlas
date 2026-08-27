// Task 153 fixture: the receiver's class comes from `new User()` (the local type table), so the
// member call resolves to User::greet at RESOLVED instead of the bare, HEURISTIC method name.
import { User } from "./models";

export function build(): void {
  const u = new User();
  u.greet();
}
