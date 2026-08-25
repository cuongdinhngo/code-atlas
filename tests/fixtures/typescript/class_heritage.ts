// R6.2 case `class-heritage`: `class … extends … implements …`. Answers 128 Q3 — the existing
// EXTENDS/IMPLEMENTS vocabulary suffices; same-file supertypes resolve to their full qname.
export interface Drawable {
  draw(): void;
}

export abstract class Shape implements Drawable {
  abstract draw(): void;
}

export class Circle extends Shape implements Drawable {
  draw(): void {}
}
