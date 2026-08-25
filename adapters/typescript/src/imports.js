"use strict";

// Import/require resolution: turn a module specifier into the repo-relative file it names, and a
// file's imports into local-name -> {file, exportedName} bindings. Name resolution is the adapter's
// job; the core links the qname (R3.3). tsconfig `paths` is unread, so an alias resolves to nothing.

const fs = require("node:fs");
const path = require("node:path");

// TS module resolution order: prefer the typed source, fall back to JS, then a declarations file.
const EXTS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts"];

function isFile(posixPath) {
  try {
    return fs.statSync(posixPath).isFile();
  } catch {
    return false;
  }
}

// A `./x` specifier -> the repo-relative posix path it resolves to (against cwd = repo root), or
// null when nothing on disk matches (an external package, or a target outside the indexed tree).
function resolveRelative(specifier, fromQpath) {
  if (!specifier.startsWith(".")) return null;
  const base = path.posix.normalize(path.posix.join(path.posix.dirname(fromQpath), specifier));
  return resolveWithExt(base);
}

function resolveWithExt(base) {
  // A `./user.js` specifier (NodeNext) names the `./user.ts` *source*, which wins over a compiled
  // `./user.js` sitting beside it — so when the specifier carries a JS extension the swapped
  // candidates are tried first, as tsc's own resolution does.
  const swapped = base.replace(/\.(js|jsx|mjs|cjs)$/, "");
  const sources = EXTS.map((e) => swapped + e);
  const index = EXTS.map((e) => `${base}/index${e}`);
  const candidates = swapped === base ? [base, ...sources, ...index] : [...sources, base, ...index];
  for (const candidate of candidates) {
    if (isFile(candidate)) return candidate;
  }
  return null;
}

// The `./y` a `const … = require("./y")` names, or null if the initializer is not a require call.
function requireSpecifier(node, ts) {
  if (
    node &&
    ts.isCallExpression(node) &&
    ts.isIdentifier(node.expression) &&
    node.expression.text === "require" &&
    node.arguments.length === 1 &&
    ts.isStringLiteral(node.arguments[0])
  ) {
    return node.arguments[0].text;
  }
  return null;
}

// Walk the top level for ESM imports and CJS requires. `bindings` maps a local name to the file +
// exported name it stands for; `namespaces` maps a whole-module binding (`import * as ns`, or a
// `const ns = require(...)`) to its file, so a later `ns.Foo` resolves to `<file>::Foo`.
function importBindings(sf, ts, resolve) {
  const bindings = new Map();
  const namespaces = new Map();
  const bind = (local, file, name) => {
    if (file) bindings.set(local, { file, name });
  };

  sf.forEachChild((node) => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
      const file = resolve(node.moduleSpecifier.text);
      const clause = node.importClause;
      if (!clause || !file) return;
      if (clause.name) bind(clause.name.text, file, "default");
      const named = clause.namedBindings;
      if (named && ts.isNamespaceImport(named)) {
        namespaces.set(named.name.text, file);
      } else if (named && ts.isNamedImports(named)) {
        for (const el of named.elements) {
          bind(el.name.text, file, (el.propertyName ?? el.name).text);
        }
      }
    } else if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        const spec = requireSpecifier(decl.initializer, ts);
        const file = spec ? resolve(spec) : null;
        if (!file) continue;
        if (ts.isIdentifier(decl.name)) {
          namespaces.set(decl.name.text, file);
        } else if (ts.isObjectBindingPattern(decl.name)) {
          for (const el of decl.name.elements) {
            if (ts.isIdentifier(el.name)) {
              const exported = el.propertyName && ts.isIdentifier(el.propertyName)
                ? el.propertyName.text
                : el.name.text;
              bind(el.name.text, file, exported);
            }
          }
        }
      }
    }
  });

  return { bindings, namespaces };
}

module.exports = { resolveRelative, requireSpecifier, importBindings };
