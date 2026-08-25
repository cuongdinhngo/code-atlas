// R6.2 case `generics`: type parameters `<T>`. Answers 128 Q1 — a qname carries no type params
// (`Box`, not `Box<T>`); the declared type lands in node extra instead.
export class Box<T> {
  value: T;

  get(): T {
    return this.value;
  }
}

export function identity<T>(arg: T): T {
  return arg;
}
