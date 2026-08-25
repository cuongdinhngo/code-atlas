// R6.2 case `interface-type-alias`: `interface` and `type X = …`. Answers 128 Q3 — a `type` alias
// reuses the Interface node kind (a named type with no runtime value); no new vocabulary is needed.
export interface Point {
  x: number;
  y: number;
}

export type Vector = Point;

export type Id = string | number;
