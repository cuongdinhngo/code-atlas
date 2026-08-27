// Task 155 fixture: imports User through a tsconfig `paths` alias (`@app/*` -> `src/*`), not a
// relative specifier. The cross-file NEW must still reach models.ts::User at RESOLVED.
import { User } from "@app/models";

export function make(): User {
  return new User();
}
