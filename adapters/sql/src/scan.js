"use strict";

// A streaming T-SQL DDL scanner. It never materialises the file: `fs.readSync` fills a fixed buffer
// and lines are handed off as they complete, so peak memory is flat in input size (task 184, C2).

const fs = require("node:fs");
const ddl = require("./ddl.js");

const CHUNK = 64 * 1024;
// A statement larger than this is degraded to a table-level write rather than accumulated, so peak
// memory stays flat in file size (task 184, C2) instead of following the widest statement.
const PENDING_CAP = 256 * 1024;
// A string body is kept only this far, so DDL inside it can be read (321) without peak memory
// following the widest literal; a longer one is scanned and cut down to its last LITERAL_KEEP.
const LITERAL_CAP = 64 * 1024;
const LITERAL_KEEP = 512;

/**
 * @typedef {{kind: string, name: string, qualified_name: string, file_path: string,
 *   line_start: number, line_end: number, modifiers: string[], params: unknown[],
 *   extra: Record<string, unknown>}} Node
 * @typedef {{kind: string, source_qname: string, target_raw: string, file_path: string,
 *   line: number, confidence_tier: string, args?: (string|null)[],
 *   arg_keys?: (string[]|null)[]}} Edge
 * @typedef {{block: number, string: boolean, elided: boolean, line: number, body: string,
 *   bodyLine: number, bodyPrefix: string,
 *   onLiteral: ((body: string, line: number, final: boolean) => string)|null}} ScanState
 */

// T-SQL delimits identifiers with [brackets] or "quotes"; a bracketed ] is escaped by doubling it.
// The qname keeps the parts and drops the delimiters, so `[dbo].[My Proc]` and `dbo.[My Proc]` are
// one name (CONVENTION §3 — a container keeps its native separator, which here is `.`).
/**
 * The last `sep`-separated segment. `split` always yields at least one element, but the checker
 * cannot know that, and a cast would hide a real empty-input case rather than answer it.
 * @param {string} value
 * @param {string} sep
 * @returns {string}
 */
function lastSegment(value, sep) {
  const parts = value.split(sep);
  return parts[parts.length - 1] ?? value;
}

/**
 * True when the last segment of a raw dotted name was written delimited (`dbo.[Key]`).
 *
 * The CREATE_RE path reaches a name as a regex capture rather than through `readIdent`, so this
 * is where that path recovers the one fact the reserved-word rule needs.
 * @param {string} raw
 * @returns {boolean}
 */
function lastSegmentDelimited(raw) {
  const text = raw.trim();
  let delimited = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "[" || ch === '"') {
      const close = ch === "[" ? "]" : '"';
      delimited = true;
      i += 1;
      while (i < text.length) {
        // A doubled delimiter is an escaped one inside the name, not the end of it.
        if (text[i] === close && text[i + 1] !== close) break;
        i += text[i] === close ? 2 : 1;
      }
      continue;
    }
    if (ch === ".") delimited = false;
  }
  return delimited;
}

/**
 * @param {string} raw
 * @returns {string|null}
 */
function splitName(raw) {
  const parts = [];
  let cur = "";
  let i = 0;
  let delim = null;
  while (i < raw.length) {
    const ch = raw[i];
    if (delim === null) {
      if (ch === "[") { delim = "]"; i += 1; continue; }
      if (ch === '"') { delim = '"'; i += 1; continue; }
      if (ch === ".") { parts.push(cur); cur = ""; i += 1; continue; }
      cur += ch;
      i += 1;
      continue;
    }
    if (ch === delim) {
      if (raw[i + 1] === delim) { cur += ch; i += 2; continue; }
      delim = null;
      i += 1;
      continue;
    }
    cur += ch;
    i += 1;
  }
  parts.push(cur);
  const clean = parts.map((p) => p.trim()).filter((p) => p !== "");
  if (clean.length === 0) return null;
  return clean.join(".");
}

// One line of source reduced to the code outside comments, strings and delimited identifiers, with
// the delimiters kept so a name can still be read. `state` carries what spans lines.
/**
 * @param {string} line
 * @param {ScanState} state
 * @returns {string}
 */
function stripToCode(line, state) {
  let out = "";
  let i = 0;
  if (state.string && state.onLiteral) state.body += "\n";
  while (i < line.length) {
    const ch = line[i];
    const next = line[i + 1];
    if (state.block > 0) {
      if (ch === "*" && next === "/") { state.block -= 1; i += 2; continue; }
      if (ch === "/" && next === "*") { state.block += 1; i += 2; continue; }
      i += 1;
      continue;
    }
    if (state.string) {
      // The BODY is dropped: a keyword inside a literal is data, not code. A dropped body leaves an
      // ellipsis so an elided literal cannot be read as a genuinely empty one — which matters for a
      // column DEFAULT, where `''` and "a literal we did not keep" are different facts (022).
      if (ch === "'") {
        if (next === "'") {
          state.elided = true;
          if (state.onLiteral) state.body += ch;
          i += 2;
          continue;
        }
        state.string = false;
        out += (state.elided ? "\u2026" : "") + ch;
        if (state.onLiteral) state.body = state.onLiteral(state.body, state.bodyLine, true);
      } else {
        state.elided = true;
        if (state.onLiteral) {
          state.body += ch;
          if (state.body.length > LITERAL_CAP) {
            state.body = state.onLiteral(state.body, state.bodyLine, false);
          }
        }
      }
      i += 1;
      continue;
    }
    if (ch === "-" && next === "-") break;
    if (ch === "/" && next === "*") { state.block += 1; i += 2; continue; }
    if (ch === "'") {
      state.string = true;
      state.elided = false;
      state.body = "";
      state.bodyLine = state.line;
      state.bodyPrefix = out;
      out += ch;
      i += 1;
      continue;
    }
    out += ch;
    i += 1;
  }
  return out;
}

// `CREATE`/`ALTER`/`CREATE OR ALTER`/`CREATE OR REPLACE` all declare the object. T-SQL spells
// OR ALTER; PostgreSQL/MySQL spell OR REPLACE — both reach the same construct (task 228).
const CREATE_RE =
  /\b(?:create|alter)\s+(?:or\s+(?:alter|replace)\s+)?(proc(?:edure)?|function)\s+((?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/i;


// T-SQL's default schema when a CREATE names none and the creator's was never changed (386).
const DEFAULT_SCHEMA = "dbo";

// A routine header ends at AS or BEGIN; everything before it is the parameter list.
const HEADER_END_RE = /\b(?:as|begin)\b/i;

// T-SQL procedure/function parameters: `@name type [ = default ]`, comma-separated before AS/BEGIN.
const PROC_PARAM_RE =
  /@([A-Za-z_][\w@#$]*)\s+([A-Za-z_][\w]*(?:\s*\([^)]*\))?)/gi;

/**
 * @param {string} line
 * @returns {{name: string, type: string}[]}
 */
function procedureParams(line) {
  const asAt = line.search(HEADER_END_RE);
  const window = asAt >= 0 ? line.slice(0, asAt) : line;
  const out = [];
  PROC_PARAM_RE.lastIndex = 0;
  let m;
  while ((m = PROC_PARAM_RE.exec(window)) !== null) {
    out.push({ name: "@" + m[1], type: m[2].replace(/\s+/g, "") });
  }
  return out;
}

/**
 * @param {string} token
 * @returns {string|null}
 */
function sqlLiteralKind(token) {
  const t = token.trim();
  if (/^N?'(?:[^']|'')*'$/i.test(t)) return "string";
  if (/^0x[0-9A-Fa-f]+$/.test(t)) return "string";
  if (/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(t)) return "number";
  if (/^(?:true|false)$/i.test(t)) return t.toLowerCase() === "true" ? "true" : "false";
  if (/^null$/i.test(t)) return "null";
  return null;
}

/**
 * Named EXEC args after the target: `@p = <literal>`, … — one category per positional slot.
 * @param {string} line
 * @param {number} matchEnd
 * @returns {{args: (string|null)[], arg_keys: (string[]|null)[]}|null}
 */
function execArgs(line, matchEnd) {
  const rest = line.slice(matchEnd);
  const named = [];
  const re = /@([A-Za-z_][\w@#$]*)\s*=\s*([^,;]+)/g;
  let m;
  while ((m = re.exec(rest)) !== null) {
    named.push({ key: "@" + m[1], value: m[2].trim() });
  }
  if (named.length === 0) {
    // Positional: EXEC dbo.Tag 'name', 3 — rare; capture literal categories only.
    const positional = [];
    const pre = rest.replace(/^\s*/, "");
    if (!pre || pre.startsWith("@")) return null; // no args, or only incomplete named form
    // Split on commas not inside quotes. A nested call or a subquery in an argument is
    // beyond a line scanner, and `sqlLiteralKind` returns null for it rather than guessing.
    let cur = "";
    let inStr = false;
    for (let i = 0; i < pre.length; i++) {
      const ch = pre[i];
      if (ch === "'" && !inStr) { inStr = true; cur += ch; continue; }
      if (ch === "'" && inStr) { inStr = false; cur += ch; continue; }
      if (ch === "," && !inStr) {
        positional.push(cur.trim());
        cur = "";
        continue;
      }
      if (ch === ";" && !inStr) break;
      cur += ch;
    }
    if (cur.trim()) positional.push(cur.trim());
    if (positional.length === 0) return { args: [], arg_keys: [] };
    return {
      args: positional.map(sqlLiteralKind),
      arg_keys: positional.map(() => null),
    };
  }
  // Named EXEC args are still positional for `args` categories; `arg_keys` stays null per
  // scalar slot — it means array/object literal keys (063), not T-SQL parameter names.
  return {
    args: named.map((n) => sqlLiteralKind(n.value)),
    arg_keys: named.map(() => null),
  };
}


// EXEC and EXECUTE are the same construct (019-C2). A parenthesised or variable target is dynamic.
const EXEC_RE =
  /\b(exec(?:ute)?)\s+(?:@\w+\s*=\s*)?(\(|@\w+|(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/gi;

const BATCH_RE = /^\s*go\s*(?:\d+\s*)?$/i;

// Tier 2 (022) + FK edges (224). A trigger is a routine like any other — it is `Function` with an
// `object_type`. Tables and columns stay the same kinds; `REFERENCES` is existing contract vocabulary.
const TRIGGER_RE =
  /\b(?:create|alter)\s+(?:or\s+(?:alter|replace)\s+)?trigger\s+((?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/i;
const TABLE_RE = /\b(?:create|alter)\s+table\b/i;
const INSERT_RE = /\binsert\b/i;
const UPDATE_RE = /\bupdate\b/i;
const DELETE_RE = /\bdelete\b/i;
const TRUNCATE_RE = /\btruncate\b/i;
const MERGE_RE = /\bmerge\b/i;
// A statement ends where the next one starts. Only tested at paren depth 0, so a keyword inside a
// table body or a column list never splits the statement that contains it.
const BOUNDARY_RE =
  /^\s*(go|create|alter|insert|update|delete|truncate|merge|if|while|begin|end|return|declare|exec|execute)\b|^\s*;/i;
const DYNAMIC_PROCS = new Set(["sp_executesql", "sp_execute", "dbo.sp_executesql"]);
// DDL that changes an existing object, read inside a string literal (321). The name after it is
// the whole claim: no concatenation is followed, and a constraint clause names no object of its own.
// A literal run where it stands: `EXEC (N'…'` / `EXEC sp_executesql N'…'` (optionally `@stmt =`).
const DIRECT_EXEC_RE =
  /\bexec(?:ute)?\s*\(\s*N?\s*$|\bsp_executesql\s+(?:@\w+\s*=\s*)?N?\s*$/i;
// `SET @v = N'…'` / `DECLARE @v nvarchar(max) = N'…'` / `SET @v += N'…'` — the variable is @v.
const ASSIGN_RE = /\b(?:set|declare)\s+(@[A-Za-z_][\w@#$]*)\b[^=;]*[+]?=/i;
// The variable a dynamic EXEC runs: `EXEC (@v)`, `EXEC @v`, `EXEC sp_executesql [@stmt =] @v`.
const EXECUTED_VAR_RE =
  /^exec(?:ute)?\s*(?:\(\s*|sp_executesql\s+(?:@stmt\s*=\s*)?|dbo\.sp_executesql\s+)?(@[A-Za-z_][\w@#$]*)/i;
const DDL_IN_STRING_RE =
  /\b(?:alter\s+table|(?:create\s+or\s+)?alter\s+(?:proc(?:edure)?|function|trigger))\s+/gi;

/**
 * Scan one `.sql` file into contract nodes and edges.
 * @param {string} qpath repo-relative path, used as the File qname
 * @returns {{path: string, ok: boolean, error?: string, nodes?: object[], edges?: object[]}}
 */
function parseFile(qpath) {
  let fd;
  try {
    fd = fs.openSync(qpath, "r");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { path: qpath, ok: false, error: `cannot read file: ${message}` };
  }

  /** @type {Node[]} */
  const nodes = [];
  /** @type {Edge[]} */
  const edges = [];
  /** @type {ScanState} */
  const state = {
    block: 0, string: false, elided: false, line: 0, body: "", bodyLine: 0, bodyPrefix: "",
    onLiteral: null,
  };
  /** @type {{qname: string, node: Node}|null} */
  let current = null;
  /** @type {Node|null} */
  let paramScan = null;
  let lineNo = 0;
  let lastLine = 0;
  /** @type {{kind: string, buf: string, line: number, depth: number, opened: boolean}|null} */
  let pending = null;
  /** @type {Map<string, Node>} */
  const tables = new Map();
  /** @type {Map<string, Node>} */
  const columns = new Map();
  /** @type {Set<string>} */
  const createdTables = new Set();
  // File-level stamp when EXEC is dynamic or targets DYNAMIC_PROCS (296).
  let sawUnmodelledDynamicSql = false;
  let refusedName = false;
  // Objects named by DDL inside string literals, with what runs the string (321): the EXEC itself
  // (`via` null), or the variable it was assigned to — kept only if an EXEC later runs that variable.
  /** @type {Map<string, {target: string, line: number, via: string|null}>} */
  const stringDdl = new Map();
  /** @type {Set<string>} */
  const executedVars = new Set();
  // The variable the current statement assigns, for a literal on a `+ N'…'` continuation line.
  let assigning = /** @type {string|null} */ (null);

  /**
   * What runs a literal, read from the code before its opening quote: `EXEC (` / `sp_executesql`
   * run it directly (""), `SET|DECLARE @v … =` stores it in `@v`, anything else runs nothing (null).
   * @param {string} prefix
   * @returns {string|null}
   */
  const runnerOf = (prefix) => {
    if (DIRECT_EXEC_RE.test(prefix)) return "";
    const assigned = ASSIGN_RE.exec(prefix);
    if (assigned) return assigned[1].toLowerCase();
    return /^\s*\+/.test(prefix) && assigning !== null ? assigning : null;
  };

  /**
   * Record every DDL target in a literal body. A non-final body keeps its tail, so a verb cut by
   * LITERAL_CAP is read again whole; only matches starting before the cut are taken now.
   * @param {string} body
   * @param {number} line  where the literal opened
   * @param {boolean} final
   * @returns {string}
   */
  state.onLiteral = (body, line, final) => {
    const cut = final ? body.length : body.length - LITERAL_KEEP;
    const runner = runnerOf(state.bodyPrefix);
    if (runner === null) return final ? "" : body.slice(cut);
    DDL_IN_STRING_RE.lastIndex = 0;
    let m;
    while ((m = DDL_IN_STRING_RE.exec(body)) !== null && m.index < cut) {
      const named = ddl.readQualified(body, m.index + m[0].length);
      const qname = named ? splitName(named.name) : null;
      if (!named || !qname || /^[@#]/.test(qname)) continue;
      if (ddl.isReservedObjectName(lastSegment(qname, "."), named.delimited)) continue;
      stringDdl.set(`${qname}\u0000${line}`, { target: qname, line, via: runner || null });
    }
    return final ? "" : body.slice(cut);
  };

  /**
   * A literal `ALTER TABLE` changes the table it names (321) — one edge per statement, from the file.
   * @param {string} qname
   * @param {boolean} delimited
   * @param {number} line
   */
  const alters = (qname, delimited, line) => {
    if (ddl.isReservedObjectName(lastSegment(qname, "."), delimited)) return;
    edges.push({
      kind: "ALTERS", source_qname: qpath, target_raw: qname,
      file_path: qpath, line, confidence_tier: "RESOLVED",
    });
  };

  /** @param {string} text */
  const depthOf = (text) => {
    let d = 0;
    for (const ch of text) {
      if (ch === "(") d += 1;
      else if (ch === ")") d -= 1;
    }
    return d;
  };

  /**
   * @param {string} qname
   * @param {number} line
   * @param {boolean} isCreate  CREATE TABLE wins over ALTER for line_start (task 228).
   * @param {boolean} delimited  The name was written `[Key]` / `"key"`, so no word is reserved.
   * @returns {Node|null}
   */
  const table = (qname, line, isCreate, delimited) => {
    if (ddl.isReservedObjectName(lastSegment(qname, "."), delimited)) {
      refusedName = true;
      return null;
    }
    const seen = tables.get(qname);
    if (seen) {
      // Prefer the defining CREATE site over an earlier ALTER sighting.
      if (isCreate && !createdTables.has(qname)) {
        seen.line_start = line;
        seen.line_end = line;
        createdTables.add(qname);
      }
      return seen;
    }
    /** @type {Node} */
    const node = {
      kind: "Table", name: lastSegment(qname, "."), qualified_name: qname, file_path: qpath,
      line_start: line, line_end: line, modifiers: [], params: [], extra: {},
    };
    tables.set(qname, node);
    if (isCreate) createdTables.add(qname);
    nodes.push(node);
    edges.push({
      kind: "CONTAINS", source_qname: qpath, target_raw: qname,
      file_path: qpath, line, confidence_tier: "RESOLVED",
    });
    return node;
  };

  /**
   * One foreign-key fact as Column→Column RESOLVED edges, or one Column→Table HEURISTIC edge when
   * the referenced column list is omitted (PK implied — same shape WRITES uses for an unnamed write).
   * @param {string} fromTable
   * @param {string[]} fromCols
   * @param {string} toTableRaw
   * @param {string[]|null} toCols
   * @param {number} line
   */
  const references = (fromTable, fromCols, toTableRaw, toCols, line) => {
    const toTable = splitName(toTableRaw);
    if (!toTable || fromCols.length === 0) return;
    if (toCols === null || toCols.length === 0) {
      edges.push({
        kind: "REFERENCES", source_qname: `${fromTable}::${fromCols[0]}`,
        target_raw: toTable, file_path: qpath, line, confidence_tier: "HEURISTIC",
      });
      return;
    }
    const n = Math.min(fromCols.length, toCols.length);
    for (let i = 0; i < n; i += 1) {
      edges.push({
        kind: "REFERENCES", source_qname: `${fromTable}::${fromCols[i]}`,
        target_raw: `${toTable}::${toCols[i]}`,
        file_path: qpath, line, confidence_tier: "RESOLVED",
      });
    }
  };

  /**
   * A standalone foreign-key constraint as its own addressable node (236): the constraint is a
   * schema object, not a second definition of the table it sits on, so it never re-emits a Table
   * row. Child/referenced tables and the child columns ride `extra`, since NODE_FIELDS is frozen.
   * @param {string} parentTable
   * @param {{name: string|null, fromColumns: string[], toTable: string,
   *   toColumns: string[]|null}} fk
   * @param {number} line
   */
  const foreignKey = (parentTable, fk, line) => {
    const referenced = splitName(fk.toTable) ?? fk.toTable;
    // An unnamed FK borrows a deterministic name from its columns AND referenced table, so two on
    // one table (different targets) do not collide on one qname; a named constraint keeps its name.
    const name = fk.name ?? `FK_${fk.fromColumns.join("_")}_${lastSegment(referenced, ".")}`;
    const qname = `${parentTable}::${name}`;
    nodes.push({
      kind: "ForeignKey", name, qualified_name: qname, file_path: qpath,
      line_start: line, line_end: line, modifiers: [], params: [],
      extra: {
        parent_table: parentTable, referenced_table: referenced,
        columns: fk.fromColumns.join(", "),
      },
    });
    // Owned by its table like a column is (the qname joins the table), even when the ALTER lives in
    // another file — the file-independent qname is exactly what lets that CONTAINS link (R3.3).
    edges.push({
      kind: "CONTAINS", source_qname: parentTable, target_raw: qname,
      file_path: qpath, line, confidence_tier: "RESOLVED",
    });
  };

  /**
   * @param {string} tableQname
   * @param {{name: string, dataType: string, dflt: string|null, delimited?: boolean,
   *   references?: {table: string, columns: string[]|null}|null,
   *   nullable?: boolean, identity?: {seed: number, increment: number},
   *   primaryKey?: number}} col
   * @param {number} line
   */
  const column = (tableQname, col, line) => {
    if (ddl.isReservedObjectName(col.name, col.delimited === true)) {
      refusedName = true;
      return;
    }
    const qname = `${tableQname}::${col.name}`;
    const seen = columns.get(qname);
    /** @type {Record<string, unknown>} */
    const extra = {};
    if (col.dataType !== "") {
      // `data_type` is SQL's spelling (CONVENTION §1); `type` is the cross-language key
      // every consumer reads (class_diagram.py, module_facts.py) — same value, one source.
      extra["data_type"] = col.dataType;
      extra["type"] = col.dataType;
    }
    if (col.dflt !== null) extra["default"] = col.dflt;
    if (col.nullable !== undefined) extra["nullable"] = col.nullable;
    if (col.identity !== undefined) extra["identity"] = col.identity;
    if (col.primaryKey !== undefined) extra["primary_key"] = col.primaryKey;
    if (seen) {
      // The other DEFAULT spelling arrives after the column itself; fill it in rather than
      // emitting a second node for the same column (022 AC5). Same merge for PK/nullability.
      Object.assign(seen.extra, extra);
      return;
    }
    /** @type {Node} */
    const node = {
      kind: "Column", name: col.name, qualified_name: qname, file_path: qpath,
      line_start: line, line_end: line, modifiers: [], params: [], extra,
    };
    columns.set(qname, node);
    nodes.push(node);
    // Sparse PK/nullability enrichment from another file must not add a second CONTAINS —
    // the typed CREATE row already owns the table→column edge (247 AC3 fold).
    const enrichmentOnly =
      col.dataType === "" && col.dflt === null && !col.references
      && (col.primaryKey !== undefined || col.nullable !== undefined || col.identity !== undefined);
    if (!enrichmentOnly) {
      edges.push({
        kind: "CONTAINS", source_qname: tableQname, target_raw: qname,
        file_path: qpath, line, confidence_tier: "RESOLVED",
      });
    }
    if (col.references) {
      references(tableQname, [col.name], col.references.table, col.references.columns, line);
    }
  };

  /**
   * Mark PK membership ordinals on the named columns (1-based). Sparse when the column was
   * declared in another file — the indexer folds extras onto the typed row (247 AC3).
   * @param {string} tableQname
   * @param {string[]} pkColumns
   * @param {number} line
   */
  const applyPrimaryKey = (tableQname, pkColumns, line) => {
    pkColumns.forEach((name, i) => {
      column(tableQname, { name, dataType: "", dflt: null, primaryKey: i + 1 }, line);
    });
  };

  /**
   * @param {string} target
   * @param {string[]|null} cols
   * @param {number} line
   */
  const writes = (target, cols, line, tier = "RESOLVED") => {
    const source = current ? current.qname : qpath;
    if (cols === null || cols.length === 0) {
      // The statement writes columns it does not name. The TARGET KIND carries that — a write onto
      // the Table named no columns, one onto a Column named it — so the tier is left to say what it
      // is for, how sure we are of the target. Overloading it here would leave the edge unlinked.
      edges.push({
        kind: "WRITES", source_qname: source, target_raw: target,
        file_path: qpath, line, confidence_tier: tier,
      });
      return;
    }
    for (const col of cols) {
      edges.push({
        kind: "WRITES", source_qname: source, target_raw: `${target}::${col}`,
        file_path: qpath, line, confidence_tier: "RESOLVED",
      });
    }
  };

  /**
   * Row-removal onto a Table — never a Column list (328 / check_column_defaults).
   * @param {string} target
   * @param {number} line
   */
  const deletes = (target, line, tier = "RESOLVED") => {
    const source = current ? current.qname : qpath;
    edges.push({
      kind: "DELETES", source_qname: source, target_raw: target,
      file_path: qpath, line, confidence_tier: tier,
    });
  };

  const flush = () => {
    if (!pending) return;
    const { kind, buf, line } = pending;
    pending = null;
    if (buf.length > PENDING_CAP) {
      let guess = null;
      if (kind === "insert") guess = ddl.readInsert(buf);
      else if (kind === "update") guess = ddl.readUpdate(buf);
      else if (kind === "delete") guess = ddl.readDelete(buf);
      else if (kind === "truncate") guess = ddl.readTruncate(buf);
      else if (kind === "merge") guess = ddl.readMergeDeletes(buf);
      if (guess) guess.table = splitName(guess.table) ?? guess.table;
      // Truncated: the statement was never read to its end, so the target is what we saw of it.
      if (guess && (kind === "delete" || kind === "truncate" || kind === "merge")) {
        deletes(guess.table, line, "DYNAMIC");
      } else if (guess) {
        writes(guess.table, null, line, "DYNAMIC");
      }
      return;
    }
    if (kind === "table") {
      const named = ddl.readNamedDefault(buf);
      const head = /\b(?:create|alter)\s+table\s+/i.exec(buf);
      if (!head) return;
      const isCreate = /^\s*create\b/i.test(head[0]);
      let after = head.index + head[0].length;
      // Skip the optional ANSI/PG/MySQL clause; T-SQL never writes it (task 228).
      const ine = /^\s*if\s+not\s+exists\s+/i.exec(buf.slice(after));
      if (ine) after += ine[0].length;
      const target = ddl.readQualified(buf, after);
      if (!target) return;
      const qname = splitName(target.name);
      if (!qname) return;
      if (!isCreate) alters(qname, target.delimited, line);
      // 236: a standalone `ALTER TABLE t ADD [CONSTRAINT n] FOREIGN KEY (...) REFERENCES ...` is a
      // constraint object, not a (re)definition of t — emit a ForeignKey node, never a Table row.
      // 247: the same for `PRIMARY KEY (...)` — mark Column.extra, never a second Table row.
      // A DEFAULT constraint (`named`) and a plain ADD <column> still need t's node; only FK/PK exit.
      if (!isCreate && !named) {
        const add = /\badd\s+/i.exec(buf.slice(target.next));
        if (add) {
          let tail = buf.slice(target.next + add.index + add[0].length);
          const colKw = /^\s*column\s+/i.exec(tail);
          if (colKw) tail = tail.slice(colKw[0].length);
          const fk = ddl.readForeignKeyDef(tail);
          const pk = fk ? null : ddl.readPrimaryKeyDef(tail);
          if (fk || pk) {
            // Same reserved-name gate as `table()` — do not enrich a bare keyword as a host.
            if (ddl.isReservedObjectName(lastSegment(qname, "."), target.delimited)) {
              refusedName = true;
              return;
            }
            if (fk) { foreignKey(qname, fk, line); return; }
            if (pk) applyPrimaryKey(qname, pk.columns, line);
            return;
          }
        }
      }
      const tbl = table(qname, line, isCreate, target.delimited);
      if (!tbl) return;
      if (named) {
        column(
          qname,
          { name: named.column, dataType: "", dflt: named.dflt, delimited: named.delimited },
          line,
        );
        return;
      }
      const body = ddl.readParens(buf, target.next);
      if (body) {
        // Newlines before `(` (e.g. CREATE …\n() plus those inside the body (254).
        let parenLine = line;
        for (let i = 0; i < body.openAt; i++) {
          if (buf[i] === "\n") parenLine += 1;
        }
        for (const col of ddl.readColumns(body.body)) {
          let colLine = parenLine;
          for (let i = 0; i < col.bodyOffset; i++) {
            if (body.body[i] === "\n") colLine += 1;
          }
          column(qname, col, colLine);
        }
        for (const fk of ddl.readForeignKeys(body.body)) {
          references(qname, fk.fromColumns, fk.toTable, fk.toColumns, line);
        }
        for (const pk of ddl.readPrimaryKeys(body.body)) {
          applyPrimaryKey(qname, pk.columns, line);
        }
        return;
      }
      const added = /\badd\s+/i.exec(buf.slice(target.next));
      if (added) {
        let rest = buf.slice(target.next + added.index + added[0].length);
        // Optional ANSI `COLUMN` keyword after ADD (PG/MySQL/SQLite); T-SQL omits it.
        const colKw = /^\s*column\s+/i.exec(rest);
        if (colKw) rest = rest.slice(colKw[0].length);
        const col = ddl.readColumnDef(rest);
        if (col) column(qname, col, line);
        else {
          const pk = ddl.readPrimaryKeyDef(rest);
          if (pk) applyPrimaryKey(qname, pk.columns, line);
        }
      }
      return;
    }
    if (kind === "delete" || kind === "truncate" || kind === "merge") {
      const stmt = kind === "delete"
        ? ddl.readDelete(buf)
        : kind === "truncate"
          ? ddl.readTruncate(buf)
          : ddl.readMergeDeletes(buf);
      if (!stmt) return;
      const qname = splitName(stmt.table);
      if (qname) deletes(qname, line);
      return;
    }
    const stmt = kind === "insert" ? ddl.readInsert(buf) : ddl.readUpdate(buf);
    if (!stmt) return;
    const qname = splitName(stmt.table);
    if (qname) writes(qname, stmt.columns, line);
  };

  /** @param {number} endLine */
  const closeCurrent = (endLine) => {
    paramScan = null;
    if (current) {
      current.node.line_end = endLine;
      current = null;
    }
  };

  /** @param {string} line */
  const onLine = (line) => {
    lineNo += 1;
    lastLine = lineNo;
    state.line = lineNo;
    const opensAssignment = state.string ? null : ASSIGN_RE.exec(line.split("'")[0] ?? "");
    if (opensAssignment) assigning = opensAssignment[1].toLowerCase();
    else if (!state.string && !/^\s*\+/.test(line)) assigning = null;
    const code = stripToCode(line, state);
    // Blank lines still append to a pending CREATE so Column line math stays honest (254).
    if (code.trim() === "") {
      if (pending) {
        pending.buf += "\n";
        if (pending.buf.length > PENDING_CAP) flush();
      }
      return;
    }

    // A T-SQL parameter list may wrap across lines; the header ends at AS or BEGIN (231).
    if (paramScan) {
      paramScan.params.push(...procedureParams(code));
      if (HEADER_END_RE.test(code)) paramScan = null;
    }

    // A statement in progress absorbs the line unless a new one starts at paren depth 0.
    if (pending && pending.depth <= 0 && BOUNDARY_RE.test(code)) flush();
    if (pending) {
      // Keep newlines so Column line_start can count from the CREATE body's start (254).
      pending.buf += `\n${code}`;
      pending.depth += depthOf(code);
      if (pending.depth > 0) pending.opened = true;
      if (pending.opened && pending.depth <= 0) flush();
      else if (pending.buf.length > PENDING_CAP) flush();
      return;
    }

    if (BATCH_RE.test(code)) {
      flush();
      closeCurrent(lineNo - 1);
      return;
    }

    const created = CREATE_RE.exec(code);
    if (created) {
      closeCurrent(lineNo - 1);
      const qname = splitName(created[2]);
      if (qname && ddl.isReservedObjectName(lastSegment(qname, "."), lastSegmentDelimited(created[2]))) {
        refusedName = true;
        return;
      }
      if (qname) {
        /** @type {Node} */
        const node = {
          kind: "Function",
          name: lastSegment(qname, "."),
          qualified_name: qname,
          file_path: qpath,
          line_start: lineNo,
          line_end: lineNo,
          modifiers: [],
          params: procedureParams(code),
          extra: { object_type: created[1].toLowerCase().startsWith("proc") ? "procedure" : "function" },
        };
        nodes.push(node);
        edges.push({
          kind: "CONTAINS",
          source_qname: qpath,
          target_raw: qname,
          file_path: qpath,
          line: lineNo,
          confidence_tier: "RESOLVED",
        });
        if (node.extra.object_type === "procedure" && !qname.includes(".")) {
          // Created with no schema it lives in the default one, so `dbo.P` names it too (386).
          edges.push({
            kind: "ALIASES",
            source_qname: `${DEFAULT_SCHEMA}.${qname}`,
            target_raw: qname,
            file_path: qpath,
            line: lineNo,
            confidence_tier: "HEURISTIC",
          });
        }
        current = { qname, node };
        paramScan = HEADER_END_RE.test(code) ? null : node;
      }
      return;
    }

    const trigger = TRIGGER_RE.exec(code);
    if (trigger) {
      closeCurrent(lineNo - 1);
      const qname = splitName(trigger[1]);
      if (qname) {
        const on = /\bon\s+/i.exec(code.slice(trigger.index + trigger[0].length));
        const host = on
          ? ddl.readQualified(code, trigger.index + trigger[0].length + on.index + on[0].length)
          : null;
        /** @type {Record<string, string>} */
        const extra = { object_type: "trigger" };
        const hostQname = host ? splitName(host.name) : null;
        if (hostQname) extra["on"] = hostQname;
        /** @type {Node} */
        const node = {
          kind: "Function", name: lastSegment(qname, "."), qualified_name: qname, file_path: qpath,
          line_start: lineNo, line_end: lineNo, modifiers: [], params: [], extra,
        };
        nodes.push(node);
        edges.push({
          kind: "CONTAINS", source_qname: qpath, target_raw: qname,
          file_path: qpath, line: lineNo, confidence_tier: "RESOLVED",
        });
        current = { qname, node };
      }
      return;
    }

    EXEC_RE.lastIndex = 0;
    let call;
    while ((call = EXEC_RE.exec(code)) !== null) {
      const target = call[2];
      const source = current ? current.qname : qpath;
      const dynamic = target === "(" || target.startsWith("@");
      const qname = dynamic ? null : splitName(target);
      const dynamicProc = qname !== null && DYNAMIC_PROCS.has(qname.toLowerCase());
      if (dynamic || dynamicProc) {
        sawUnmodelledDynamicSql = true;
        const ran = EXECUTED_VAR_RE.exec(code.slice(call.index));
        if (ran) executedVars.add(ran[1].toLowerCase());
      }
      // A dynamic target is emitted, never dropped and never RESOLVED (AC7): the call site is a fact
      // even where the callee is not knowable, and the core decides what an unlinkable edge means.
      /** @type {Edge} */
      const edge = {
        kind: "CALLS",
        source_qname: source,
        target_raw: dynamic || qname === null || dynamicProc ? "(dynamic)" : qname,
        file_path: qpath,
        line: lineNo,
        confidence_tier: dynamic || qname === null || dynamicProc ? "DYNAMIC" : "RESOLVED",
      };
      if (!dynamic && qname !== null && !dynamicProc) {
        const captured = execArgs(code, call.index + call[0].length);
        if (captured) {
          edge.args = captured.args;
          edge.arg_keys = captured.arg_keys;
        }
      }
      edges.push(edge);
    }

    const kind = TABLE_RE.test(code)
      ? "table"
      : INSERT_RE.test(code)
        ? "insert"
        : UPDATE_RE.test(code)
          ? "update"
          : DELETE_RE.test(code)
            ? "delete"
            : TRUNCATE_RE.test(code)
              ? "truncate"
              : MERGE_RE.test(code)
                ? "merge"
                : null;
    if (kind === null) return;
    const depth = depthOf(code);
    pending = { kind, buf: code, line: lineNo, depth, opened: depth > 0 };
    if (pending.opened && pending.depth <= 0) flush();
  };

  const buffer = Buffer.allocUnsafe(CHUNK);
  let carry = "";
  try {
    for (;;) {
      const read = fs.readSync(fd, buffer, 0, CHUNK, null);
      if (read === 0) break;
      const text = carry + buffer.toString("utf8", 0, read);
      const parts = text.split("\n");
      carry = parts.pop() ?? "";
      for (const part of parts) onLine(part.endsWith("\r") ? part.slice(0, -1) : part);
    }
    if (carry !== "") onLine(carry.endsWith("\r") ? carry.slice(0, -1) : carry);
  } finally {
    fs.closeSync(fd);
  }
  flush();
  closeCurrent(lastLine);
  // A DDL verb in a string nothing executes is a message, not a migration (321 AC6).
  for (const { target, line, via } of stringDdl.values()) {
    if (via !== null && !executedVars.has(via)) continue;
    edges.push({
      kind: "ALTERS", source_qname: qpath, target_raw: target,
      file_path: qpath, line, confidence_tier: "DYNAMIC",
    });
  }

  // Dialect rides File.extra — META_FIELDS is frozen (R3.1 / 217 precedent); a reader of any File
  // node sees which dialect this adapter read, not a silent `name: "sql"`.
  /** @type {Record<string, unknown>} */
  const fileExtra = { dialect: "tsql" };
  if (refusedName) {
    // A reserved word was refused as an object name: absence is honest, but the file is not a
    // complete successful read of its DDL — distinguish it from a fully-read T-SQL file (AC5).
    fileExtra["parse"] = "refused_reserved_name";
  }
  if (sawUnmodelledDynamicSql) {
    // Stamp, never invent CALLS targets (279/296).
    fileExtra["unmodelled_resolution"] = ["dynamic_sql"];
  }

  nodes.unshift({
    kind: "File",
    name: lastSegment(qpath, "/"),
    qualified_name: qpath,
    file_path: qpath,
    line_start: 1,
    line_end: Math.max(lastLine, 1),
    modifiers: [],
    params: [],
    extra: fileExtra,
  });

  // A file whose only DDL outcomes were refused reserved names is not a successful parse of what
  // it claimed to declare — ok:false so parsed_ok cannot look like a complete read (AC5 / R5.2).
  if (refusedName && tables.size === 0 && columns.size === 0) {
    const functions = nodes.filter((n) => n.kind === "Function");
    if (functions.length === 0) {
      return {
        path: qpath,
        ok: false,
        error: "refused reserved-word object name(s); dialect=tsql",
      };
    }
  }

  return { path: qpath, ok: true, nodes, edges };
}

module.exports = { parseFile, splitName };
