// Integration fixture: a *named* default export — the common TS/React shape. The declaration keeps
// its own name, so only the `::default` alias lets an importing file reach it.
export default class Service {
  start(): void {}
}
