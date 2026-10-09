"use strict";

// TS/JS source -> code-atlas contract JSON, one file at a time, via ts.createSourceFile (no
// Program/type-checker). Same-file targets resolve to their qname; imported ones stay bare for the
// core resolver (R3.3). See README.md and PLAN §4.4 for the qname/resolution conventions.

const fs = require("node:fs");
const ts = require("typescript");
const { toPosix, member } = require("./qname");
const {
  resolveSpecifier,
  requireSpecifier,
  importBindings,
  pathBuiltRequire,
  pathModuleNames,
} = require("./imports");
const { readSqlLiteral } = require("./sqlLiteral");
const { boundClass, newExprClass, paramTypeMap, classPropTypeMap, typeNodeOf, typeRefTargets } = require("./types");

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
      // readonly is the language saying "constant" (234); EnumMember stays ClassConst.
      if (hasModifier(node, ts.SyntaxKind.ReadonlyKeyword)) return "ClassConst";
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


function modifierNames(node) {
  const mods = ts.canHaveModifiers(node) ? ts.getModifiers(node) : undefined;
  if (!mods || mods.length === 0) return null;
  const out = [];
  for (const m of mods) {
    switch (m.kind) {
      case ts.SyntaxKind.PublicKeyword:
        out.push("public");
        break;
      case ts.SyntaxKind.PrivateKeyword:
        out.push("private");
        break;
      case ts.SyntaxKind.ProtectedKeyword:
        out.push("protected");
        break;
      case ts.SyntaxKind.StaticKeyword:
        out.push("static");
        break;
      case ts.SyntaxKind.ReadonlyKeyword:
        out.push("readonly");
        break;
      case ts.SyntaxKind.AbstractKeyword:
        out.push("abstract");
        break;
      case ts.SyntaxKind.AsyncKeyword:
        out.push("async");
        break;
      default:
        break;
    }
  }
  return out.length ? out : null;
}

function callableParams(node, sf) {
  const params = node.parameters || [];
  return params.map((p) => {
    let name = "$?";
    if (p.name && ts.isIdentifier(p.name)) name = p.name.text;
    else if (p.name) name = p.name.getText(sf);
    const type = p.type ? p.type.getText(sf) : null;
    return { name, type };
  });
}


// Decorators land in node `extra` AND as REFERENCES edges (task 232 — agrees with Python;
// PHP attributes do the same). The factory call `@log()` is still not a CALLS.
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
  // A TS annotation, else a `.js` file's JSDoc `@type`/`@param`, else a function's `@returns` — the
  // same `extra.type` slot regardless of language flavour (task 154).
  const annotated = node.type || ts.getJSDocType(node) || ts.getJSDocReturnType(node);
  return annotated ? annotated.getText(sf) : null;
}

// A `const f = () => {}` / `= function () {}` binding is a named function (TS infers the name);
// a module/namespace-scoped `const K = <value>` is a Const. Other variables produce no node.
function classifyVariable(stmt, decl, isImport) {
  if (!decl.name || !ts.isIdentifier(decl.name)) return null;
  const init = decl.initializer;
  if (init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init))) {
    return { kind: "Function", name: decl.name.text };
  }
  if (requireSpecifier(init, ts) || (isImport && isImport(init))) return null; // an import, not a Const
  const isConst = (stmt.declarationList.flags & ts.NodeFlags.Const) !== 0;
  const moduleScope = stmt.parent && (ts.isSourceFile(stmt.parent) || ts.isModuleBlock(stmt.parent));
  if (isConst && moduleScope) return { kind: "Const", name: decl.name.text };
  return null;
}

// The contract `args` category of one argument (task 152), or null for any other expression — the
// question is "what shape", never the value. Mirrors the PHP adapter's literalKind.
function literalKind(node) {
  if (
    ts.isStringLiteral(node) ||
    ts.isNoSubstitutionTemplateLiteral(node) ||
    ts.isTemplateExpression(node)
  ) {
    return "string"; // a template literal is a string-typed expression, as PHP treats interpolation
  }
  if (ts.isNumericLiteral(node) || ts.isBigIntLiteral(node)) return "number";
  if (node.kind === ts.SyntaxKind.TrueKeyword) return "true";
  if (node.kind === ts.SyntaxKind.FalseKeyword) return "false";
  if (node.kind === ts.SyntaxKind.NullKeyword) return "null";
  if (ts.isObjectLiteralExpression(node) || ts.isArrayLiteralExpression(node)) return "array";
  return null;
}

// One contract `args` entry per call argument, in source order; null = not a literal. A spread
// argument forwards an unknown count, so no position is trustworthy — the whole list is dropped.
function argLiterals(call) {
  const args = call.arguments;
  if (!args) return []; // `new Foo` with no parens is a zero-argument call
  const out = [];
  for (const arg of args) {
    if (ts.isSpreadElement(arg)) return null;
    out.push(literalKind(arg));
  }
  return out;
}

// The top-level string keys of an object literal, in order: a normal or shorthand property's name;
// a computed key or a spread contributes nothing and does not shift later keys (mirrors PHP 063).
function objectKeys(node) {
  const keys = [];
  for (const prop of node.properties) {
    if (ts.isSpreadAssignment(prop)) continue;
    const name = prop.name;
    if (name && (ts.isIdentifier(name) || ts.isStringLiteral(name))) keys.push(name.text);
  }
  return keys;
}

// Parallel to argLiterals: an object/array literal's keys ([] for a positional array), else null.
function argKeys(call) {
  const args = call.arguments;
  if (!args) return [];
  return args.map((arg) => {
    if (ts.isObjectLiteralExpression(arg)) return objectKeys(arg);
    if (ts.isArrayLiteralExpression(arg)) return [];
    return null;
  });
}

function parseFile(path, declarationsOnly) {
  const qpath = toPosix(path);
  let text;
  try {
    text = fs.readFileSync(path, "utf8");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { path: qpath, ok: false, error: `cannot read file: ${message}` };
  }

  const sf = ts.createSourceFile(qpath, text, ts.ScriptTarget.Latest, true, scriptKindFor(qpath));
  // `parseDiagnostics` is an internal SourceFile field, absent from the public type — read it via a
  // documented cast rather than suppress the whole file (task 150 / R6.6).
  const diagnostics = /** @type {any} */ (sf).parseDiagnostics || [];
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

  // File.extra.unmodelled_resolution — stamp, never invent IMPORTS (279/294).
  const markUnmodelledResolution = (strategy) => {
    const file = nodes[0];
    const extra = file.extra && typeof file.extra === "object" ? { ...file.extra } : {};
    const list = Array.isArray(extra.unmodelled_resolution) ? [...extra.unmodelled_resolution] : [];
    if (!list.includes(strategy)) {
      list.push(strategy);
      list.sort();
    }
    extra.unmodelled_resolution = list;
    file.extra = extra;
  };

  // A `require` built from a directory or a root plus a literal tail (370).
  const pathNames = pathModuleNames(sf, ts);
  const isBuiltRequire = (init) => pathBuiltRequire(init, ts, pathNames, qpath) !== null;

  // Pre-pass: name -> qname for same-file resolution. A name declared twice is ambiguous and falls
  // back to bare, so the core resolver decides rather than the adapter guessing.
  const declared = new Map();
  const remember = (name, qname) => {
    if (declared.has(name)) declared.set(name, null);
    else declared.set(name, qname);
  };
  // Class qname -> its static fields: what `Foo.x` (or `this.x` in a static member) can reach (369).
  const staticFields = new Map();
  const classQnames = new Map();
  const collect = (node, container) => {
    if (ts.isClassDeclaration(node) && nameOf(node)) classQnames.set(node, member(container, nameOf(node)));
    if (
      ts.isPropertyDeclaration(node) &&
      ts.isClassDeclaration(node.parent) &&
      hasModifier(node, ts.SyntaxKind.StaticKeyword) &&
      nameOf(node)
    ) {
      if (!staticFields.has(container)) staticFields.set(container, new Set());
      staticFields.get(container).add(nameOf(node));
    }
    let childContainer = container;
    if (nodeKindOf(node)) {
      const name = nameOf(node);
      if (name) {
        childContainer = member(container, name);
        remember(name, childContainer);
      }
    } else if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        const cls = classifyVariable(node, decl, isBuiltRequire);
        if (cls) remember(cls.name, member(container, cls.name));
      }
    }
    node.forEachChild((child) => collect(child, childContainer));
  };
  collect(sf, qpath);

  const resolveSpec = (specifier) => resolveSpecifier(specifier, qpath);
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

  const addNode = (kind, name, qname, node, extra, opts) => {
    const row = {
      kind,
      name,
      qualified_name: qname,
      file_path: qpath,
      line_start: lineOf(node.getStart(sf)),
      line_end: lineOf(node.getEnd()),
    };
    if (extra && Object.keys(extra).length > 0) row.extra = extra;
    if (opts && opts.modifiers) row.modifiers = opts.modifiers;
    if (opts && opts.params) row.params = opts.params;
    nodes.push(row);
  };
  const addEdge = (kind, sourceQname, targetRaw, pos, tier, call) => {
    const row = { kind, source_qname: sourceQname, target_raw: targetRaw, file_path: qpath };
    row.line = lineOf(pos);
    if (tier) row.confidence_tier = tier;
    // A CALLS/NEW site carries its argument shapes (task 152); a spread drops the whole list.
    if (call) {
      const args = argLiterals(call);
      if (args !== null) {
        row.args = args;
        row.arg_keys = argKeys(call);
      }
    }
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
    // The spec's `constructor` of a named class is what `new` calls (362/367); a class expression has
    // no Class node, so `find_callers` could not name the class it builds.
    if (node.kind === ts.SyntaxKind.Constructor && ts.isClassDeclaration(node.parent)) base.constructor = true;
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

  // Named type references on a declaration → REFERENCES (task 232). Primitives and the
  // declaration's own type parameters emit nothing.
  const emitTypeRefs = (owner, typeNode, pos, skipNames) => {
    const skip = skipNames || new Set();
    for (const name of typeRefTargets(typeNode)) {
      if (skip.has(name)) continue;
      addEdge("REFERENCES", owner, resolve(name), pos);
    }
  };

  const typeParamNames = (node) => {
    const out = new Set();
    for (const p of (node && node.typeParameters) || []) {
      if (p.name && ts.isIdentifier(p.name)) out.add(p.name.text);
    }
    return out;
  };

  const emitDecoratorRefs = (owner, node) => {
    const decos = ts.canHaveDecorators(node) ? ts.getDecorators(node) : undefined;
    if (!decos) return;
    for (const d of decos) {
      const e = d.expression;
      const expr = ts.isCallExpression(e) ? e.expression : e;
      const target = resolveExpr(expr);
      if (target) addEdge("REFERENCES", owner, target, d.getStart(sf));
    }
  };

  const emitAnnotationRefs = (owner, node, skip) => {
    emitDecoratorRefs(owner, node);
    const skipNames = new Set([...(skip || []), ...typeParamNames(node)]);
    emitTypeRefs(owner, typeNodeOf(node) || ts.getJSDocReturnType(node), node.getStart(sf), skipNames);
    for (const p of node.parameters || []) {
      emitTypeRefs(owner, typeNodeOf(p), p.getStart(sf), skipNames);
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

  // A JSDoc `@typedef`/`@callback` names a type — the `.js` analogue of a `type` alias, so it emits an
  // Interface node (task 154). The tag rides the following node's `jsDoc`; anchor it at that container.
  const emitJsDocDeclarations = (node, container) => {
    for (const doc of node.jsDoc || []) {
      for (const tag of doc.tags || []) {
        if (!ts.isJSDocTypedefTag(tag) && !ts.isJSDocCallbackTag(tag)) continue;
        if (!tag.name || !ts.isIdentifier(tag.name)) continue;
        const name = tag.name.text;
        const qname = member(container, name);
        addNode("Interface", name, qname, tag, { type_alias: true });
        addEdge("CONTAINS", container, qname, tag.getStart(sf));
      }
    }
  };

  // The class a call receiver evaluates to, from the local type table: a bare variable, or a
  // `this.prop` whose class the enclosing class declared. null when the receiver is untyped.
  const receiverClass = (expr, locals, selfProps) => {
    if (ts.isIdentifier(expr)) return locals.get(expr.text) || null;
    if (
      ts.isPropertyAccessExpression(expr) &&
      expr.expression.kind === ts.SyntaxKind.ThisKeyword &&
      ts.isIdentifier(expr.name)
    ) {
      return selfProps.get(expr.name.text) || null;
    }
    return null;
  };

  // The qname of the class a `super(...)` call's class extends, or null when the heritage names none.
  const superClassOf = (node) => {
    let cls = node.parent;
    while (cls && !ts.isClassLike(cls)) cls = cls.parent;
    for (const clause of (cls && cls.heritageClauses) || []) {
      if (clause.token === ts.SyntaxKind.ExtendsKeyword && clause.types.length === 1) {
        return resolveExpr(clause.types[0].expression);
      }
    }
    return null;
  };

  // The class qname `this` names: inside a static member of a class declaration it is the class;
  // an arrow inherits `this`, any other function or class rebinds it.
  const thisClass = (node) => {
    for (let n = node.parent; n; n = n.parent) {
      if (ts.isArrowFunction(n)) continue;
      const member =
        ts.isMethodDeclaration(n) || ts.isGetAccessor(n) || ts.isSetAccessor(n) || ts.isPropertyDeclaration(n);
      const isStatic = ts.isClassStaticBlockDeclaration(n) || (member && hasModifier(n, ts.SyntaxKind.StaticKeyword));
      if ((member || ts.isClassStaticBlockDeclaration(n)) && ts.isClassDeclaration(n.parent)) {
        return isStatic ? classQnames.get(n.parent) || null : null;
      }
      if (ts.isFunctionLike(n) || ts.isClassLike(n) || ts.isSourceFile(n)) return null;
    }
    return null;
  };

  // Whether a function-like or block between `node` and the file binds `name` — a parameter or a
  // local `const`/`let`/`var`/`function`/`class`/`catch` — shadowing the file's class of that name.
  const boundLocally = (node, name) => {
    for (let n = node.parent; n && !ts.isSourceFile(n); n = n.parent) {
      if (ts.isFunctionLike(n) && n.parameters.some((p) => bindsName(p.name, name))) return true;
      if (ts.isCatchClause(n) && n.variableDeclaration && bindsName(n.variableDeclaration.name, name)) return true;
      if ((ts.isBlock(n) || ts.isModuleBlock(n)) && declaresName(n, name)) return true;
      if ((ts.isForStatement(n) || ts.isForOfStatement(n) || ts.isForInStatement(n)) && n.initializer &&
          ts.isVariableDeclarationList(n.initializer) &&
          n.initializer.declarations.some((d) => bindsName(d.name, name))) return true;
    }
    return false;
  };
  const bindsName = (binding, name) => {
    if (ts.isIdentifier(binding)) return binding.text === name;
    return binding.elements.some((el) => !ts.isOmittedExpression(el) && bindsName(el.name, name));
  };
  const declaresName = (block, name) =>
    block.statements.some((st) =>
      (ts.isVariableStatement(st) && st.declarationList.declarations.some((d) => bindsName(d.name, name))) ||
      (ts.isFunctionDeclaration(st) && st.name && st.name.text === name) ||
      // the block declaring the class itself (a namespace) does not shadow it
      (ts.isClassDeclaration(st) && st.name && st.name.text === name && classQnames.get(st) !== declared.get(name)));

  // A static field read or written by its class's name, or by `this` in a static member (369, as 336).
  const emitStaticFieldRef = (node, scope) => {
    const parent = node.parent;
    if ((ts.isCallExpression(parent) || ts.isNewExpression(parent)) && parent.expression === node) return;
    const recv = node.expression;
    let owner = null;
    if (ts.isIdentifier(recv) && !boundLocally(node, recv.text)) owner = declared.get(recv.text) || null;
    else if (recv.kind === ts.SyntaxKind.ThisKeyword) owner = thisClass(node);
    const fields = owner ? staticFields.get(owner) : undefined;
    if (fields && fields.has(node.name.text)) {
      addEdge("REFERENCES", scope, member(owner, node.name.text), node.getStart(sf));
    }
  };

  // A HEURISTIC tail the core links by unique path suffix (353) leaves the file stamped.
  const emitBuiltRequire = (node) => {
    const built = pathBuiltRequire(node, ts, pathNames, qpath);
    if (!built) return false;
    addEdge("IMPORTS", qpath, built.target, node.getStart(sf), built.exact ? undefined : "HEURISTIC");
    if (!built.exact) markUnmodelledResolution("dynamic_import");
    return true;
  };

  // A string the program runs as a value: not a bare statement, a type, a module specifier or a
  // member's name, which never reach a database driver.
  const isRuntimeString = (node) => {
    const parent = node.parent;
    if (!parent || ts.isExpressionStatement(parent) || ts.isLiteralTypeNode(parent)) return false;
    if (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent)) return false;
    if (ts.isExternalModuleReference(parent) || ts.isImportTypeNode(parent)) return false;
    return !("name" in parent && parent.name === node);
  };

  // A literal that begins a T-SQL write or EXEC writes, deletes or calls its object (371). The
  // literal before a `+` is cut short, as PHP's `.`; a bare expression statement never runs.
  const continuedLiterals = new Set();
  const emitSqlLiteral = (node, text, closed, scope) => {
    if (!isRuntimeString(node)) return;
    const statement = readSqlLiteral(text, closed);
    if (!statement) return;
    // The keyword's place in the source, not in the cooked text: a cooked `\r\n` or escape is shorter.
    const keyword = text.slice(statement.offset).split(/\s/)[0].toLowerCase();
    const offset = node.getStart(sf) + Math.max(node.getText(sf).toLowerCase().indexOf(keyword), 0);
    edges.push({
      kind: statement.kind,
      source_qname: scope,
      target_raw: statement.target,
      file_path: qpath,
      line: lineOf(offset),
      confidence_tier: "HEURISTIC",
    });
  };

  const emitBodyEdges = (node, scope, enclosingClass, locals, selfProps) => {
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
    } else if (emitBuiltRequire(node)) {
      return; // as a literal require: an import, never a CALLS
    } else if (
      ts.isCallExpression(node) &&
      node.arguments.length >= 1 &&
      !ts.isStringLiteral(node.arguments[0]) &&
      (node.expression.kind === ts.SyntaxKind.ImportKeyword ||
        (ts.isIdentifier(node.expression) && node.expression.text === "require"))
    ) {
      // Non-literal import()/require() — graph cannot name the module (294).
      markUnmodelledResolution("dynamic_import");
    }
    if (declarationsOnly) return;
    if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
      let left = node.left;
      while (ts.isBinaryExpression(left) && left.operatorToken.kind === ts.SyntaxKind.PlusToken) left = left.right;
      continuedLiterals.add(left);
    }
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      emitSqlLiteral(node, node.text, !continuedLiterals.has(node), scope);
    } else if (ts.isTemplateExpression(node)) {
      emitSqlLiteral(node, node.head.text, false, scope);
    }
    // Flow-sensitive, forgetful (137): `x = new Foo()` binds x; `x = <anything else>` re-opens it,
    // so a stale type can never outlive the assignment that invalidated it.
    if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
      ts.isIdentifier(node.left)
    ) {
      const cls = newExprClass(node.right);
      if (cls) locals.set(node.left.text, cls);
      else locals.delete(node.left.text);
    }
    if (ts.isPropertyAccessExpression(node) && ts.isIdentifier(node.name)) {
      emitStaticFieldRef(node, scope);
    }
    if (ts.isNewExpression(node)) {
      const target = resolveExpr(node.expression);
      if (target) addEdge("NEW", scope, target, node.getStart(sf), undefined, node);
    }
    if (ts.isCallExpression(node)) {
      const callee = node.expression;
      if (
        ts.isPropertyAccessExpression(callee) &&
        callee.expression.kind === ts.SyntaxKind.ThisKeyword &&
        enclosingClass
      ) {
        addEdge("CALLS", scope, member(enclosingClass, callee.name.text), node.getStart(sf), undefined, node);
      } else if (callee.kind === ts.SyntaxKind.SuperKeyword) {
        // `super(...)` runs the base class's constructor, a static target (367) — not a dynamic call.
        const base = superClassOf(node);
        if (base) addEdge("CALLS", scope, member(base, "__construct"), node.getStart(sf), undefined, node);
        else addEdge("CALLS", scope, "(dynamic)", node.getStart(sf), "DYNAMIC", node);
      } else if (ts.isIdentifier(callee)) {
        // A bare call is reported even when unresolved: the adapter emits, the core links (R3.3).
        addEdge("CALLS", scope, resolve(callee.text), node.getStart(sf), undefined, node);
      } else {
        const target = resolveExpr(callee);
        if (target) {
          addEdge("CALLS", scope, target, node.getStart(sf), undefined, node);
        } else if (ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.name)) {
          const cls = receiverClass(callee.expression, locals, selfProps);
          if (cls) {
            // The local type table named the receiver's class (task 153): emit the full
            // `<Class>::method` qname so the core links it RESOLVED, not the bare HEURISTIC name.
            addEdge("CALLS", scope, member(resolve(cls), callee.name.text), node.getStart(sf), undefined, node);
          } else {
            // The method name is known and the receiver is not. `HEURISTIC` is not a label here: it
            // is what switches on the core's name-only fallback (`resolver.py` bare-member branch),
            // and it caps the edge so a unique name can never be promoted to RESOLVED (R5.2).
            addEdge("CALLS", scope, callee.name.text, node.getStart(sf), "HEURISTIC", node);
          }
        } else {
          // A computed callee (`obj[name]()`, an IIFE) names nothing linkable. Say so rather than
          // drop the call — the same `(dynamic)`/`DYNAMIC` convention the PHP adapter uses.
          addEdge("CALLS", scope, "(dynamic)", node.getStart(sf), "DYNAMIC", node);
        }
      }
    }
  };

  const walkVariables = (stmt, container, scope, enclosingClass, locals, selfProps, typeParams) => {
    for (const decl of stmt.declarationList.declarations) {
      const init = decl.initializer;
      const spec = requireSpecifier(init, ts);
      if (spec) {
        // A `const x = require(…)` is module structure, not a body edge: its IMPORTS has to survive
        // declarations_only exactly as an ESM `import` does.
        addEdge("IMPORTS", qpath, resolveSpec(spec) || spec, init.getStart(sf));
        continue;
      }
      if (emitBuiltRequire(init)) continue;
      // Type binding (137): an annotation or an inferred `new Foo()` types the variable; anything
      // else re-opens it, so the local table never carries a stale class into a later member call.
      if (ts.isIdentifier(decl.name)) {
        const bound = boundClass(decl, init);
        if (bound) locals.set(decl.name.text, bound);
        else locals.delete(decl.name.text);
      }
      const cls = classifyVariable(stmt, decl, isBuiltRequire);
      if (cls && cls.kind === "Function") {
        const qname = member(container, cls.name);
        // `const f = (u: User) => …` declares its parameters on the initialiser, not on the
        // variable the node is built from, so probing `decl` alone dropped every one of them.
        const opts = init && ts.isFunctionLike(init) ? { params: callableParams(init, sf) } : {};
        addNode("Function", cls.name, qname, decl, extraOf(decl), opts);
        addEdge("CONTAINS", container, qname, decl.getStart(sf));
        if (init && ts.isFunctionLike(init)) emitAnnotationRefs(qname, init, typeParams);
        if (!declarationsOnly && init) walk(init, qname, qname, null, locals, selfProps, typeParams);
      } else if (cls && cls.kind === "Const") {
        const qname = member(container, cls.name);
        addNode("Const", cls.name, qname, decl, extraOf(decl));
        addEdge("CONTAINS", container, qname, decl.getStart(sf));
        if (!declarationsOnly && init) walk(init, container, scope, enclosingClass, locals, selfProps, typeParams);
      } else if (!declarationsOnly && init) {
        walk(init, container, scope, enclosingClass, locals, selfProps, typeParams);
      }
    }
  };

  // Main walk: nodes + CONTAINS, plus the edges each construct owns. `scope` is what a body edge is
  // sourced at, `enclosingClass` the qname a `this.method()` resolves against; body walking is
  // skipped for declarations_only. `typeParams` names type parameters in scope (skip REFERENCES).
  const walk = (node, container, scope, enclosingClass, locals, selfProps, typeParams) => {
    if (ts.isVariableStatement(node)) {
      walkVariables(node, container, scope, enclosingClass, locals, selfProps, typeParams);
      return;
    }

    const kind = nodeKindOf(node);
    let childContainer = container;
    let childScope = scope;
    let childClass = enclosingClass;
    let childLocals = locals;
    let childSelfProps = selfProps;
    let childTypeParams = typeParams;
    let emittedCallable = false;

    // A function/method/ctor opens a fresh local scope seeded with its typed parameters; an arrow or
    // function expression closes over the outer scope, so it inherits and adds its own (137).
    if (CALLABLE.has(node.kind)) childLocals = paramTypeMap(node);
    else if (ts.isArrowFunction(node) || ts.isFunctionExpression(node)) {
      childLocals = new Map([...locals, ...paramTypeMap(node)]);
    }

    if (kind) {
      const name = nameOf(node);
      if (name) {
        const qname = member(container, name);
        const opts = {};
        const mods = modifierNames(node);
        if (mods) opts.modifiers = mods;
        if (CALLABLE.has(node.kind)) opts.params = callableParams(node, sf);
        addNode(kind, name, qname, node, nodeExtra(node, kind), opts);
        addEdge("CONTAINS", container, qname, node.getStart(sf));
        emitAnnotationRefs(qname, node, typeParams);
        childContainer = qname;
        if (SCOPE.has(node.kind)) childScope = qname;
        if (kind === "Class" || kind === "Interface") childClass = qname;
        if (kind === "Class") childSelfProps = classPropTypeMap(node);
        if (kind === "Class" || kind === "Interface" || CALLABLE.has(node.kind)) {
          childTypeParams = new Set([...typeParams, ...typeParamNames(node)]);
        }
        if (CALLABLE.has(node.kind)) emittedCallable = true;
        emitHeritage(node, qname);
        emitDefaultAlias(node, name, qname);
      }
    }

    emitBodyEdges(node, scope, enclosingClass, locals, selfProps);
    emitJsDocDeclarations(node, container);

    // declarations_only stops at a callable's boundary: the node is emitted, its body is not walked.
    if (emittedCallable && declarationsOnly) return;
    // Decorators annotate a declaration (captured in extra); their expressions are not body edges.
    node.forEachChild((child) => {
      if (!ts.isDecorator(child)) {
        walk(child, childContainer, childScope, childClass, childLocals, childSelfProps, childTypeParams);
      }
    });
  };
  walk(sf, qpath, qpath, null, new Map(), new Map(), new Set());

  return { path: qpath, ok: true, nodes, edges };
}

module.exports = { parseFile };
