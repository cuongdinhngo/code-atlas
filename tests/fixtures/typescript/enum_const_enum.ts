// R6.2 case `enum-const-enum`: `enum` and `const enum`. Answers 128 Q3 — both reuse the Enum node
// kind with ClassConst members; `const enum` is marked via node extra, not a new kind.
export enum Color {
  Red,
  Green,
  Blue,
}

export const enum Direction {
  Up,
  Down,
}
