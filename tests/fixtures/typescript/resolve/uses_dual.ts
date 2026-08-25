// Integration fixture: a NodeNext `./dual.js` specifier naming the TypeScript source.
import { Widget } from "./dual.js";

export function pick(): Widget {
  return new Widget();
}
