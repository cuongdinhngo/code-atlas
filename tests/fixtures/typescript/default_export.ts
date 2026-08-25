// R6.2 case `default-export`: an anonymous `export default`. Answers 128 Q1 — an unnamed default is
// qnamed `::default` so a default-import can resolve to it; a module-scoped `const` is a Const node.
const version = "1.0";

export default function (): string {
  return version;
}

export function helper(): void {}
