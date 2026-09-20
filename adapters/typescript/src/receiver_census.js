"use strict";

// TypeScript HEURISTIC CALLS receiver-shape census (task 301). File-at-a-time, no Program: names
// whether a bare member call's receiver is an identifier bound from a same-file explicit return,
// a direct `factory().m()` call result, an imported/unknown callable, or something else — the
// ceiling a return-type table could move (assigned + direct forms, Scope §3).

const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const _PRIMITIVES = new Set([
  "string",
  "number",
  "boolean",
  "bigint",
  "symbol",
  "undefined",
  "null",
  "void",
  "any",
  "unknown",
  "never",
  "object",
]);

/** @returns {{kind: string, name?: string}} */
function singleClassReturn(typeNode) {
  if (!typeNode) return { kind: "missing" };
  const classes = [];
  let poisoned = false;
  const walk = (n) => {
    if (!n) return;
    if (ts.isParenthesizedTypeNode(n)) {
      walk(n.type);
      return;
    }
    if (typeof ts.isThisTypeNode === "function" && ts.isThisTypeNode(n)) {
      classes.push("__this__");
      return;
    }
    if (ts.isUnionTypeNode(n) || ts.isIntersectionTypeNode(n)) {
      for (const part of n.types) walk(part);
      return;
    }
    if (ts.isLiteralTypeNode(n)) return;
    if (n.kind === ts.SyntaxKind.NullKeyword || n.kind === ts.SyntaxKind.UndefinedKeyword) return;
    if (ts.isTypeReferenceNode(n) && ts.isIdentifier(n.typeName)) {
      if (n.typeArguments && n.typeArguments.length) {
        poisoned = true;
        return;
      }
      const name = n.typeName.text;
      if (_PRIMITIVES.has(name)) return;
      classes.push(name);
      return;
    }
    poisoned = true;
  };
  walk(typeNode);
  if (poisoned) return { kind: "generic_or_complex" };
  if (classes.length === 0) return { kind: "non_class" };
  if (classes.length > 1) return { kind: "union_ambiguous" };
  return { kind: "explicit_class", name: classes[0] };
}

function buildReturnMaps(sf) {
  const fn = new Map();
  const meth = new Map();
  const visit = (node) => {
    if (ts.isFunctionDeclaration(node) && node.name) {
      fn.set(node.name.text, singleClassReturn(node.type || ts.getJSDocReturnType(node)));
    }
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer &&
      (ts.isArrowFunction(node.initializer) || ts.isFunctionExpression(node.initializer))
    ) {
      fn.set(
        node.name.text,
        singleClassReturn(node.initializer.type || ts.getJSDocReturnType(node.initializer))
      );
    }
    if (ts.isClassDeclaration(node) && node.name) {
      const cn = node.name.text;
      for (const m of node.members) {
        if ((ts.isMethodDeclaration(m) || ts.isGetAccessor(m)) && m.name && ts.isIdentifier(m.name)) {
          let ret = singleClassReturn(m.type || ts.getJSDocReturnType(m));
          if (ret.kind === "explicit_class" && ret.name === "__this__") {
            ret = { kind: "explicit_class", name: cn };
          }
          meth.set(`${cn}::${m.name.text}`, ret);
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { fn, meth };
}

/** Resolve the declared return of a callee expression against same-file maps. */
function callReturnOf(expr, fn, meth) {
  if (ts.isIdentifier(expr)) {
    return fn.get(expr.text) || { kind: "imported_or_unindexed_callee" };
  }
  if (ts.isPropertyAccessExpression(expr) && ts.isIdentifier(expr.name)) {
    for (const [k, v] of meth) {
      if (k.endsWith(`::${expr.name.text}`)) return v;
    }
    return { kind: "imported_or_unknown_method" };
  }
  return { kind: "complex_callee" };
}

/** Class name a call expression returns, or null when not a single explicit class. */
function explicitClassOfCall(callExpr, fn, meth) {
  if (!ts.isCallExpression(callExpr)) return null;
  const ret = callReturnOf(callExpr.expression, fn, meth);
  return ret.kind === "explicit_class" ? ret.name : null;
}

function shapeForReturn(ret, method, nameSet, qnameSet) {
  if (ret.kind === "imported_or_unindexed_callee") return "call_imported_or_unindexed_callee";
  if (ret.kind === "imported_or_unknown_method") return "call_imported_or_unknown_method";
  if (ret.kind === "complex_callee") return "call_complex_callee";
  if (ret.kind !== "explicit_class") return `call_return_${ret.kind}`;
  const typeOk = nameSet.has(ret.name);
  const methodOk = [...qnameSet].some(
    (n) => n.endsWith(`::${method}`) && n.includes(ret.name)
  );
  if (typeOk && methodOk) return "explicit_return_indexed";
  if (typeOk) return "explicit_return_type_only";
  return "explicit_return_unindexed";
}

/**
 * Flow-sensitive walk: bind locals from `x = factory()` / `const x = factory()` when factory has
 * an explicit class return; forget on any other assignment (ticket forgetful-flow constraint).
 * Record a shape for every property-access call site.
 */
function analyzeFile(abs, nameSet, qnameSet) {
  const text = fs.readFileSync(abs, "utf8");
  const sf = ts.createSourceFile(abs, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const { fn, meth } = buildReturnMaps(sf);
  /** @type {Map<string, string>} key `${line}:${method}` → shape */
  const siteShapes = new Map();

  const recordCall = (node, locals) => {
    if (
      !ts.isCallExpression(node) ||
      !ts.isPropertyAccessExpression(node.expression) ||
      !ts.isIdentifier(node.expression.name)
    ) {
      return;
    }
    const method = node.expression.name.text;
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    const key = `${line}:${method}`;
    const recv = node.expression.expression;
    let shape;
    if (ts.isIdentifier(recv)) {
      const bound = locals.get(recv.text);
      if (bound) {
        shape = shapeForReturn({ kind: "explicit_class", name: bound }, method, nameSet, qnameSet);
      } else {
        shape = "identifier_receiver";
      }
    } else if (recv.kind === ts.SyntaxKind.ThisKeyword) {
      shape = "this_receiver";
    } else if (ts.isPropertyAccessExpression(recv)) {
      shape = "property_receiver";
    } else if (ts.isNewExpression(recv)) {
      shape = "new_receiver";
    } else if (ts.isCallExpression(recv)) {
      const ret = callReturnOf(recv.expression, fn, meth);
      shape = shapeForReturn(ret, method, nameSet, qnameSet);
    } else {
      shape = "other_receiver";
    }
    // First match at a line wins (matches the reporter's one-edge-per-site expectation).
    if (!siteShapes.has(key)) siteShapes.set(key, shape);
  };

  const bindFromInit = (name, init, locals) => {
    const cls = explicitClassOfCall(init, fn, meth);
    if (cls) locals.set(name, cls);
    else locals.delete(name);
  };

  const walk = (node, locals) => {
    // Fresh scope at function/method boundaries (params do not carry return bindings).
    if (
      ts.isFunctionDeclaration(node) ||
      ts.isMethodDeclaration(node) ||
      ts.isConstructorDeclaration(node) ||
      ts.isArrowFunction(node) ||
      ts.isFunctionExpression(node) ||
      ts.isGetAccessor(node) ||
      ts.isSetAccessor(node)
    ) {
      const childLocals =
        ts.isArrowFunction(node) || ts.isFunctionExpression(node)
          ? new Map(locals)
          : new Map();
      // Walk body only with the child scope; still record calls inside.
      if (node.body) walk(node.body, childLocals);
      // Do not walk children again via forEachChild — body handled.
      return;
    }

    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      bindFromInit(node.name.text, node.initializer, locals);
    }
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      ts.isIdentifier(node.left)
    ) {
      bindFromInit(node.left.text, node.right, locals);
    }

    recordCall(node, locals);
    ts.forEachChild(node, (child) => walk(child, locals));
  };

  walk(sf, new Map());
  return { siteShapes };
}

function classifyEdge(edge, info) {
  if (!info) return "no_source_file";
  const shape = info.siteShapes.get(`${edge.line}:${edge.method}`);
  return shape || "no_ast_at_line";
}

/**
 * @param {string} root repo root containing the indexed files
 * @param {{file: string, line: number, method: string}[]} edges bare HEURISTIC CALLS
 * @param {string[]} qnames indexed node qualified names
 */
function censusReceivers(root, edges, qnames) {
  const qnameSet = new Set(qnames);
  const nameSet = new Set([...qnameSet].map((n) => n.split("::").pop()));
  const fileCache = new Map();
  const counts = {};
  let explicitIndexed = 0;
  for (const edge of edges) {
    const rel = edge.file;
    if (!fileCache.has(rel)) {
      const abs = path.join(root, rel);
      fileCache.set(rel, fs.existsSync(abs) ? analyzeFile(abs, nameSet, qnameSet) : null);
    }
    const shape = classifyEdge(edge, fileCache.get(rel));
    counts[shape] = (counts[shape] || 0) + 1;
    if (shape === "explicit_return_indexed") explicitIndexed += 1;
  }
  return {
    total: edges.length,
    counts,
    // The ticket-301 ceiling: same-file explicit class-like return, type + method indexed
    // (direct `factory().m()` and assigned `const x = factory(); x.m()`).
    explicit_return_indexed_ceiling: explicitIndexed,
  };
}

function main(argv) {
  const args = argv.slice(2);
  if (args[0] !== "--json") {
    process.stderr.write("usage: node receiver_census.js --json <payload.json>\n");
    process.exit(2);
  }
  const payload = JSON.parse(fs.readFileSync(args[1], "utf8"));
  const result = censusReceivers(payload.root, payload.edges, payload.qnames || []);
  process.stdout.write(JSON.stringify(result) + "\n");
}

if (require.main === module) main(process.argv);

module.exports = { censusReceivers, singleClassReturn, classifyEdge };
