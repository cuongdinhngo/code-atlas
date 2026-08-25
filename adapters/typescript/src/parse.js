"use strict";

// TS/JS source -> code-atlas contract JSON, one file at a time, via ts.createSourceFile (no
// Program/type-checker). Same-file targets resolve to their qname; imported ones stay bare for the
// core resolver (R3.3). See README.md and PLAN §4.4 for the qname/resolution conventions.

const fs = require("node:fs");
const ts = require("typescript");
const { toPosix, member } = require("./qname");
const { resolveRelative, requireSpecifier, importBindings } = require("./imports");

function scriptKindFor(path) {
  if (path.endsWith(".tsx")) return ts.ScriptKind.TSX;
  if (path.endsWith(".jsx")) return ts.ScriptKind.JSX;
  if (path.endsWith(".js") || path.endsWith(".mjs") || path.endsWith(".cjs")) return ts.ScriptKind.JS;
  return ts.ScriptKind.TS;
}

// The construct -> contract node kind map. Keyed on TS syntax, never on an identifier (R2). A `type`
// alias reuses Interface (a named type with no runtime value); const enums reuse Enum.
function nodeKindOf(node) {
  switch (node.kind) {
    case ts.SyntaxKind.ModuleDeclaration:
      return "Namespace";
    case ts.SyntaxKind.ClassDeclaration:
      return "Class";
    case ts.SyntaxKind.InterfaceDeclaration:
    case ts.SyntaxKind.TypeAliasDeclaration:
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

const CALLABLE = new Set([
  ts.SyntaxKind.FunctionDeclaration,
  ts.SyntaxKind.MethodDeclaration,
  ts.SyntaxKind.Constructor,
  ts.SyntaxKind.GetAccessor,
  ts.SyntaxKind.SetAccessor,
]);

// A scope owns the CALLS/NEW edges written inside it, so a call in a method body is sourced at the
// method — the same stack the PHP adapter pushes (Visitor.php `open()`: namespaces, class-likes and
// callables push a scope; properties and consts only declare).
const SCOPE = new Set([
  ts.SyntaxKind.ModuleDeclaration,
  ts.SyntaxKind.ClassDeclaration,
  ts.SyntaxKind.InterfaceDeclaration,
  ...CALLABLE,
]);

function nameOf(node) {
  if (node.kind === ts.SyntaxKind.Constructor) return "__construct";
  if (node.name && ts.isIdentifier(node.name)) return node.name.text;
  if (node.name && ts.isStringLiteral(node.name)) return node.name.text;
  // A default export with no name is qnamed `::default` so a default-import can resolve to it.
  if (hasModifier(node, ts.SyntaxKind.DefaultKeyword)) return "default";
  return null;
}

function hasModifier(node, kind) {
  const mods = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
  return !!mods && mods.some((m) => m.kind === kind);
}

// Decorators are recorded on the node's `extra`, never as edges — mirrors how the PHP adapter keeps
// attributes out of the edge set (they annotate a declaration, they don't call or construct it).
function decoratorsOf(node, sf) {
  const decos = ts.canHaveDecorators(node) ? ts.getDecorators(node) : undefined;
  if (!decos || decos.length === 0) return null;
  return decos.map((d) => {
    const e = d.expression;
    if (ts.isIdentifier(e)) return e.text;
    if (ts.isCallExpression(e) && ts.isIdentifier(e.expression)) return e.expression.text;
    return e.getText(sf);
  });
}

function typeTextOf(node, sf) {
  return node.type ? node.type.getText(sf) : null;
}

// A `const f = () => {}` / `= function () {}` binding is a named function (TS infers the name);
// a module/namespace-scoped `const K = <value>` is a Const. Other variables produce no node.
function classifyVariable(stmt, decl) {
  if (!decl.name || !ts.isIdentifier(decl.name)) return null;
  const init = decl.initializer;
  if (init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init))) {
    return { kind: "Function", name: decl.name.text };
  }
  if (requireSpecifier(init, ts)) return null; // `const x = require(...)` is an import, not a Const
  const isConst = (stmt.declarationList.flags & ts.NodeFlags.Const) !== 0;
  const moduleScope = stmt.parent && (ts.isSourceFile(stmt.parent) || ts.isModuleBlock(stmt.parent));
  if (isConst && moduleScope) return { kind: "Const", name: decl.name.text };
  return null;
}

function parseFile(path, declarationsOnly) {
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

  nodes.push({
    kind: "File",
    name: qpath.split("/").pop(),
    qualified_name: qpath,
    file_path: qpath,
    line_start: 1,
    line_end: lineOf(sf.getEnd()),
  });

  // Pre-pass: name -> qname for same-file resolution. A name declared twice is ambiguous and falls
  // back to bare, so the core resolver decides rather than the adapter guessing.
  const declared = new Map();
  const remember = (name, qname) => {
    if (declared.has(name)) declared.set(name, null);
    else declared.set(name, qname);
  };
  const collect = (node, container) => {
    let childContainer = container;
    if (nodeKindOf(node)) {
      const name = nameOf(node);
      if (name) {
        childContainer = member(container, name);
        remember(name, childContainer);
      }
    } else if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        const cls = classifyVariable(node, decl);
        if (cls) remember(cls.name, member(container, cls.name));
      }
    }
    node.forEachChild((child) => collect(child, childContainer));
  };
  collect(sf, qpath);

  const resolveSpec = (specifier) => resolveRelative(specifier, qpath);
  const importCtx = importBindings(sf, ts, resolveSpec);

  // Name resolution (adapter's half of R3.3): a same-file declaration wins; otherwise an import
  // binding names the target file, so `<file>::<exported>` is what the core links to a RESOLVED node.
  const resolve = (name) => {
    const local = declared.get(name);
    if (local) return local;
    if (declared.has(name)) return name; // declared but ambiguous -> bare, the core decides
    const bound = importCtx.bindings.get(name);
    if (bound) return member(bound.file, bound.name);
    return name;
  };

  // A `new`/heritage/callee expression -> the qname it names: a bare/bound identifier, or a
  // namespace member `ns.Foo` -> `<ns-file>::Foo`. null means "nothing an edge should point at".
  const resolveExpr = (expr) => {
    if (ts.isIdentifier(expr)) return resolve(expr.text);
    if (ts.isPropertyAccessExpression(expr) && ts.isIdentifier(expr.expression)) {
      const nsFile = importCtx.namespaces.get(expr.expression.text);
      if (nsFile) return member(nsFile, expr.name.text);
    }
    return null;
  };

  const addNode = (kind, name, qname, node, extra) => {
    const row = {
      kind,
      name,
      qualified_name: qname,
      file_path: qpath,
      line_start: lineOf(node.getStart(sf)),
      line_end: lineOf(node.getEnd()),
    };
    if (extra && Object.keys(extra).length > 0) row.extra = extra;
    nodes.push(row);
  };
  const addEdge = (kind, sourceQname, targetRaw, pos, tier) => {
    const row = { kind, source_qname: sourceQname, target_raw: targetRaw, file_path: qpath };
    row.line = lineOf(pos);
    if (tier) row.confidence_tier = tier;
    edges.push(row);
  };

  const extraOf = (node, base) => {
    const extra = base ? { ...base } : {};
    const decos = decoratorsOf(node, sf);
    if (decos) extra.decorators = decos;
    const t = typeTextOf(node, sf);
    if (t) extra.type = t;
    return extra;
  };

  const nodeExtra = (node, kind) => {
    const base = {};
    if (node.kind === ts.SyntaxKind.TypeAliasDeclaration) base.type_alias = true;
    if (kind === "Enum" && hasModifier(node, ts.SyntaxKind.ConstKeyword)) base.const = true;
    if (node.kind === ts.SyntaxKind.EnumMember) base.enum_case = true;
    return extraOf(node, base);
  };

  const emitHeritage = (node, qname) => {
    for (const clause of node.heritageClauses || []) {
      const edgeKind = clause.token === ts.SyntaxKind.ExtendsKeyword ? "EXTENDS" : "IMPLEMENTS";
      for (const typeRef of clause.types) {
        const target = resolveExpr(typeRef.expression);
        if (target) addEdge(edgeKind, qname, target, typeRef.getStart(sf));
      }
    }
  };

  // `export { A as B } from "./x"` re-exports x's A as this module's B: an ALIASES edge names the
  // *defining* module, so a downstream import of B resolves through it (149's load-bearing case).
  const emitReExport = (node) => {
    const spec = node.moduleSpecifier.text;
    const file = resolveSpec(spec);
    addEdge("IMPORTS", qpath, file || spec, node.getStart(sf));
    if (file && node.exportClause && ts.isNamedExports(node.exportClause)) {
      for (const el of node.exportClause.elements) {
        const exported = (el.propertyName ?? el.name).text;
        addEdge("ALIASES", member(qpath, el.name.text), member(file, exported), el.getStart(sf));
      }
    }
  };

  // `export default class Foo` keeps its own name, but an importing file only ever knows it as
  // `default`: alias the two so a default-import resolves, the same way a barrel re-export does.
  const emitDefaultAlias = (node, name, qname) => {
    if (name === "default" || !hasModifier(node, ts.SyntaxKind.DefaultKeyword)) return;
    addEdge("ALIASES", member(qpath, "default"), qname, node.getStart(sf));
  };

  const emitBodyEdges = (node, scope, enclosingClass) => {
    // Module structure (IMPORTS, re-export ALIASES) survives declarations_only; CALLS/NEW do not.
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
      const spec = node.moduleSpecifier.text;
      addEdge("IMPORTS", qpath, resolveSpec(spec) || spec, node.getStart(sf));
    } else if (
      ts.isExportDeclaration(node) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier)
    ) {
      emitReExport(node);
    } else if (requireSpecifier(node, ts)) {
      const spec = requireSpecifier(node, ts);
      addEdge("IMPORTS", qpath, resolveSpec(spec) || spec, node.getStart(sf));
      return; // a require is an import, never a CALLS
    }
    if (declarationsOnly) return;
    if (ts.isNewExpression(node)) {
      const target = resolveExpr(node.expression);
      if (target) addEdge("NEW", scope, target, node.getStart(sf));
    }
    if (ts.isCallExpression(node)) {
      const callee = node.expression;
      if (
        ts.isPropertyAccessExpression(callee) &&
        callee.expression.kind === ts.SyntaxKind.ThisKeyword &&
        enclosingClass
      ) {
        addEdge("CALLS", scope, member(enclosingClass, callee.name.text), node.getStart(sf));
      } else if (ts.isIdentifier(callee)) {
        // A bare call is reported even when unresolved: the adapter emits, the core links (R3.3).
        addEdge("CALLS", scope, resolve(callee.text), node.getStart(sf));
      } else {
        const target = resolveExpr(callee);
        if (target) {
          addEdge("CALLS", scope, target, node.getStart(sf));
        } else if (ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.name)) {
          // The method name is known and the receiver is not. `HEURISTIC` is not a label here: it is
          // what switches on the core's name-only fallback (`resolver.py` bare-member branch), and
          // it caps the edge so a unique name can never be promoted to RESOLVED (R5.2).
          addEdge("CALLS", scope, callee.name.text, node.getStart(sf), "HEURISTIC");
        } else {
          // A computed callee (`obj[name]()`, an IIFE) names nothing linkable. Say so rather than
          // drop the call — the same `(dynamic)`/`DYNAMIC` convention the PHP adapter uses.
          addEdge("CALLS", scope, "(dynamic)", node.getStart(sf), "DYNAMIC");
        }
      }
    }
  };

  const walkVariables = (stmt, container, scope, enclosingClass) => {
    for (const decl of stmt.declarationList.declarations) {
      const init = decl.initializer;
      const spec = requireSpecifier(init, ts);
      if (spec) {
        // A `const x = require(…)` is module structure, not a body edge: its IMPORTS has to survive
        // declarations_only exactly as an ESM `import` does.
        addEdge("IMPORTS", qpath, resolveSpec(spec) || spec, init.getStart(sf));
        continue;
      }
      const cls = classifyVariable(stmt, decl);
      if (cls && cls.kind === "Function") {
        const qname = member(container, cls.name);
        addNode("Function", cls.name, qname, decl, extraOf(decl));
        addEdge("CONTAINS", container, qname, decl.getStart(sf));
        if (!declarationsOnly && init) walk(init, qname, qname, null);
      } else if (cls && cls.kind === "Const") {
        const qname = member(container, cls.name);
        addNode("Const", cls.name, qname, decl, extraOf(decl));
        addEdge("CONTAINS", container, qname, decl.getStart(sf));
        if (!declarationsOnly && init) walk(init, container, scope, enclosingClass);
      } else if (!declarationsOnly && init) {
        walk(init, container, scope, enclosingClass);
      }
    }
  };

  // Main walk: nodes + CONTAINS, plus the edges each construct owns. `scope` is what a body edge is
  // sourced at, `enclosingClass` the qname a `this.method()` resolves against; body walking is
  // skipped for declarations_only.
  const walk = (node, container, scope, enclosingClass) => {
    if (ts.isVariableStatement(node)) {
      walkVariables(node, container, scope, enclosingClass);
      return;
    }

    const kind = nodeKindOf(node);
    let childContainer = container;
    let childScope = scope;
    let childClass = enclosingClass;
    let emittedCallable = false;

    if (kind) {
      const name = nameOf(node);
      if (name) {
        const qname = member(container, name);
        addNode(kind, name, qname, node, nodeExtra(node, kind));
        addEdge("CONTAINS", container, qname, node.getStart(sf));
        childContainer = qname;
        if (SCOPE.has(node.kind)) childScope = qname;
        if (kind === "Class" || kind === "Interface") childClass = qname;
        if (CALLABLE.has(node.kind)) emittedCallable = true;
        emitHeritage(node, qname);
        emitDefaultAlias(node, name, qname);
      }
    }

    emitBodyEdges(node, scope, enclosingClass);

    // declarations_only stops at a callable's boundary: the node is emitted, its body is not walked.
    if (emittedCallable && declarationsOnly) return;
    // Decorators annotate a declaration (captured in extra); their expressions are not body edges.
    node.forEachChild((child) => {
      if (!ts.isDecorator(child)) walk(child, childContainer, childScope, childClass);
    });
  };
  walk(sf, qpath, qpath, null);

  return { path: qpath, ok: true, nodes, edges };
}

module.exports = { parseFile };
