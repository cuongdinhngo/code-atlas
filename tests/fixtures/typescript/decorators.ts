// R6.2 case `decorators`: `@decorator` on a class, property and method. Task 232 — decorators
// annotate a declaration in `extra` AND emit REFERENCES (agrees with Python; PHP attributes too).
import { Component, sealed, readonly, log } from "./decorators-lib";

@Component({ selector: "app" })
@sealed
export class Widget {
  @readonly
  title = "";

  @log()
  render(): void {}
}
