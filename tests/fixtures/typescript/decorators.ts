// R6.2 case `decorators`: `@decorator` on a class, property and method. Answers 128 Q3 — decorators
// annotate a declaration, so they land in node extra and emit no edge (mirrors PHP attributes).
import { Component, sealed, readonly, log } from "./decorators-lib";

@Component({ selector: "app" })
@sealed
export class Widget {
  @readonly
  title = "";

  @log()
  render(): void {}
}
