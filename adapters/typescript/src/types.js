"use strict";

// Local type facts, syntactic and file-at-a-time (task 153, mirroring the PHP TypeTable). Every
// binding comes from the language putting the type in the file — `new X`, a parameter/property
// annotation, an assignment of a `new X` — never a checker and never a framework (R2). It lets a
// member call `obj.method()` resolve to `<Class>::method` instead of a bare, HEURISTIC name.

const ts = require("typescript");

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

// The class an initializer/assignment RHS binds a variable to: an annotation wins, else an inferred
// `new Foo()`; anything else returns null (the caller then forgets the variable).
function boundClass(typeNode, initializer) {
  return typeRefName(typeNode) ?? newExprClass(initializer);
}

// Typed parameters of a callable -> Map(name -> class); a destructured or untyped parameter binds
// nothing. Seeds a fresh local scope at each function/method boundary.
function paramTypeMap(node) {
  const m = new Map();
  for (const p of node.parameters || []) {
    if (ts.isIdentifier(p.name)) {
      const cls = typeRefName(p.type);
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
      const cls = typeRefName(member.type);
      if (cls) m.set(member.name.text, cls);
    }
  }
  return m;
}

module.exports = { typeRefName, newExprClass, boundClass, paramTypeMap, classPropTypeMap };
