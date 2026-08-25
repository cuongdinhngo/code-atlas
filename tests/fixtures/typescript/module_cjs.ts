// R6.2 case `module-cjs`: CommonJS `require`. Answers 128 Q2 — a non-ESM import resolves to a real
// file too, so `new Service()` targets `<cjs_service.js>::Service` for the core to link RESOLVED.
const { Service } = require("./cjs_service");

export function boot(): void {
  new Service();
}
