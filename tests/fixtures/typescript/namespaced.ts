// R6.2 case `namespace-declare`: TS `namespace` is the only JS/TS construct with a native container
// separator, so it is the fixture that decides 128 Q1 — does MEMBER_SEPARATOR (`::`) bend to TS's
// `.`? The expected edge shapes pin `Geometry::Circle::area`, proving it does not.
export namespace Geometry {
  export interface Shape {
    area(): number;
  }

  export class Circle implements Shape {
    radius: number;

    area(): number {
      return this.radius * this.radius;
    }
  }

  export class Square extends Circle {
    area(): number {
      return this.radius * this.radius;
    }
  }
}
