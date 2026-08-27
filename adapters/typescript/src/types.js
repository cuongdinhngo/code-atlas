"use strict";

// Local type facts, syntactic and file-at-a-time (task 153, mirroring the PHP TypeTable). Every
// binding comes from the language putting the type in the file — `new X`, a parameter/property
// annotation, an assignment of a `new X` — never a checker and never a framework (R2). It lets a
// member call `obj.method()` resolve to `<Class>::method` instead of a bare, HEURISTIC name.

const ts = require("typescript");

// The type node a declaration carries: a TS annotation `x: Foo`, or — in a `.js` file — a JSDoc
// `@type {Foo}` / `@param {Foo}` the language puts in a comment (task 154). Same slot, one consumer.
function typeNodeOf(node) {
  return node.type || ts.getJSDocType(node) || null;
}

// The simple class name a type annotation names: `Foo` / `Foo<T>` -> "Foo". A qualified, union,
// array or any other type names nothing this file can turn into one class.
function typeRefName(typeNode) {
  if (typeNode && ts.isTypeReferenceNode(typeNode) && ts.isIdentifier(typeNode.typeName)) {
    return typeNode.typeName.text;
  }
  return null;
}

// The class a `new Foo()` / `new Foo<T>()` initializer names, or null for anything else.
function newExprClass(expr) {
  if (expr && ts.isNewExpression(expr) && ts.isIdentifier(expr.expression)) {
    return expr.expression.text;
  }
  return null;
}

// The class a declaration binds a variable to: an annotation (TS or JSDoc) wins, else an inferred
// `new Foo()`; anything else returns null (the caller then forgets the variable).
function boundClass(decl, initializer) {
  return typeRefName(typeNodeOf(decl)) ?? newExprClass(initializer);
}

// Typed parameters of a callable -> Map(name -> class); a destructured or untyped parameter binds
// nothing. Seeds a fresh local scope at each function/method boundary. A JSDoc `@param` counts.
function paramTypeMap(node) {
  const m = new Map();
  for (const p of node.parameters || []) {
    if (ts.isIdentifier(p.name)) {
      const cls = typeRefName(typeNodeOf(p));
      if (cls) m.set(p.name.text, cls);
    }
  }
  return m;
}

// Typed instance properties of a class -> Map(name -> class), so `this.prop.method()` resolves.
function classPropTypeMap(classNode) {
  const m = new Map();
  for (const member of classNode.members || []) {
    if (ts.isPropertyDeclaration(member) && ts.isIdentifier(member.name)) {
      const cls = typeRefName(typeNodeOf(member));
      if (cls) m.set(member.name.text, cls);
    }
  }
  return m;
}

module.exports = {
  typeNodeOf,
  typeRefName,
  newExprClass,
  boundClass,
  paramTypeMap,
  classPropTypeMap,
};
