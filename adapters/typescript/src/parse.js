"use strict";

// M0 spike parser: TS/JS source -> code-atlas contract JSON, one file at a time, via
// ts.createSourceFile (no Program/type-checker) — see README.md and PLAN §4.4 for what that
// proves (MEMBER_SEPARATOR holds; same-file targets resolve, imports stay bare — R3.3).

const fs = require("node:fs");
const ts = require("typescript");

const SEP = "::";

function toPosix(p) {
  return p.replace(/\\/g, "/");
}

function scriptKindFor(path) {
  if (path.endsWith(".tsx")) return ts.ScriptKind.TSX;
  if (path.endsWith(".jsx")) return ts.ScriptKind.JSX;
  if (path.endsWith(".js") || path.endsWith(".mjs") || path.endsWith(".cjs")) return ts.ScriptKind.JS;
  return ts.ScriptKind.TS;
}

// The construct -> contract node kind map. Keyed on TS syntax, never on an identifier (R2).
function nodeKindOf(node) {
  switch (node.kind) {
    case ts.SyntaxKind.ModuleDeclaration:
      return "Namespace";
    case ts.SyntaxKind.ClassDeclaration:
      return "Class";
    case ts.SyntaxKind.InterfaceDeclaration:
      return "Interface";
    case ts.SyntaxKind.EnumDeclaration:
      return "Enum";
    case ts.SyntaxKind.FunctionDeclaration:
      return "Function";
    case ts.SyntaxKind.MethodDeclaration:
    case ts.SyntaxKind.MethodSignature:
    case ts.SyntaxKind.Constructor:
    case ts.SyntaxKind.GetAccessor:
    case ts.SyntaxKind.SetAccessor:
      return "Method";
    case ts.SyntaxKind.PropertyDeclaration:
    case ts.SyntaxKind.PropertySignature:
      return "Property";
    case ts.SyntaxKind.EnumMember:
      return "ClassConst";
    default:
      return null;
  }
}

function nameOf(node) {
  if (node.kind === ts.SyntaxKind.Constructor) return "__construct";
  if (node.name && ts.isIdentifier(node.name)) return node.name.text;
  if (node.name && ts.isStringLiteral(node.name)) return node.name.text;
  return null;
}

function parseFile(path, _declarationsOnly) {
  const qpath = toPosix(path);
  let text;
  try {
    text = fs.readFileSync(path, "utf8");
  } catch (error) {
    return { path: qpath, ok: false, error: `cannot read file: ${error.message}` };
  }

  const sf = ts.createSourceFile(qpath, text, ts.ScriptTarget.Latest, true, scriptKindFor(qpath));
  const diagnostics = sf.parseDiagnostics || [];
  if (diagnostics.length > 0) {
    const message = ts.flattenDiagnosticMessageText(diagnostics[0].messageText, " ");
    return { path: qpath, ok: false, error: `syntax error: ${message}` };
  }

  const nodes = [];
  const edges = [];
  const lineOf = (pos) => sf.getLineAndCharacterOfPosition(pos).line + 1;

  // The file itself is a node, qnamed by its repo-relative path (contract §3); it is the container
  // every top-level declaration's CONTAINS edge points back at.
  nodes.push({
    kind: "File",
    name: qpath.split("/").pop(),
    qualified_name: qpath,
    file_path: qpath,
    line_start: 1,
    line_end: lineOf(sf.getEnd()),
  });

  // Pre-pass: a simple name -> qname map for same-file resolution. A name declared twice becomes
  // ambiguous and falls back to bare, so the core resolver decides rather than the adapter guessing.
  const declared = new Map();
  const collect = (node, container) => {
    const kind = nodeKindOf(node);
    let childContainer = container;
    if (kind) {
      const name = nameOf(node);
      if (name) {
        const qname = container + SEP + name;
        childContainer = qname;
        if (declared.has(name)) declared.set(name, null);
        else declared.set(name, qname);
      }
    }
    node.forEachChild((child) => collect(child, childContainer));
  };
  collect(sf, qpath);

  const resolve = (name) => {
    const hit = declared.get(name);
    return hit === undefined || hit === null ? name : hit;
  };

  const addNode = (node, kind, qname) => {
    nodes.push({
      kind,
      name: nameOf(node),
      qualified_name: qname,
      file_path: qpath,
      line_start: lineOf(node.getStart(sf)),
      line_end: lineOf(node.getEnd()),
    });
  };
  const addEdge = (kind, sourceQname, targetRaw, pos) => {
    edges.push({
      kind,
      source_qname: sourceQname,
      target_raw: targetRaw,
      file_path: qpath,
      line: lineOf(pos),
    });
  };

  // Main walk: nodes + CONTAINS, plus the edges each construct owns. `enclosingClass` carries the
  // qname a `this.method()` call resolves against without any type information.
  const walk = (node, container, enclosingClass) => {
    const kind = nodeKindOf(node);
    let childContainer = container;
    let childClass = enclosingClass;

    if (kind) {
      const name = nameOf(node);
      if (name) {
        const qname = container + SEP + name;
        addNode(node, kind, qname);
        addEdge("CONTAINS", container, qname, node.getStart(sf));
        childContainer = qname;
        if (kind === "Class" || kind === "Interface") childClass = qname;

        for (const clause of node.heritageClauses || []) {
          const edgeKind = clause.token === ts.SyntaxKind.ExtendsKeyword ? "EXTENDS" : "IMPLEMENTS";
          for (const typeRef of clause.types) {
            if (ts.isIdentifier(typeRef.expression)) {
              addEdge(edgeKind, qname, resolve(typeRef.expression.text), typeRef.getStart(sf));
            }
          }
        }
      }
    }

    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
      addEdge("IMPORTS", qpath, node.moduleSpecifier.text, node.getStart(sf));
    }

    if (ts.isNewExpression(node) && ts.isIdentifier(node.expression)) {
      addEdge("NEW", enclosingClass || container, resolve(node.expression.text), node.getStart(sf));
    }

    if (ts.isCallExpression(node)) {
      const callee = node.expression;
      if (
        ts.isPropertyAccessExpression(callee) &&
        callee.expression.kind === ts.SyntaxKind.ThisKeyword &&
        enclosingClass
      ) {
        addEdge("CALLS", enclosingClass, enclosingClass + SEP + callee.name.text, node.getStart(sf));
      } else if (ts.isIdentifier(callee)) {
        // A bare call is reported even when unresolved: the adapter emits, the core links (R3.3).
        addEdge("CALLS", enclosingClass || container, resolve(callee.text), node.getStart(sf));
      }
    }

    node.forEachChild((child) => walk(child, childContainer, childClass));
  };
  walk(sf, qpath, null);

  return { path: qpath, ok: true, nodes, edges };
}

module.exports = { parseFile };
