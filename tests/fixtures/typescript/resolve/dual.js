// Integration fixture: the stale compiled sibling of dual.ts. A `./dual.js` specifier must resolve
// to the source, not to this — tsc's own NodeNext behaviour.
export class Widget {}
