// R6.2 case `arrow-closure`: arrow fns and function expressions. Answers 128 Q1 — a name-bound
// arrow/function is a named Function (TS infers the name); a class-field arrow stays a Property; an
// inline callback is anonymous and gets no node (a deliberate divergence from PHP's synthetic names).
export const greet = (name: string): string => `hi ${name}`;

export const add = function (a: number, b: number): number {
  return a + b;
};

export class Handlers {
  onClick = (): void => {};
}

export function run(): void {
  [1, 2].forEach((n) => n + 1);
}
