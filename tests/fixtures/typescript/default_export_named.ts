// R6.2 case `default-export-named`: `export default class Foo {}` — the named default export, the
// shape a React component file takes. The class keeps its own name (Widget); an ALIASES from
// `::default` reaches `::Widget` so a default-import resolves (019 review finding, task 157).
export default class Widget {
  render(): string {
    return "w";
  }
}

export function helper(): void {}
