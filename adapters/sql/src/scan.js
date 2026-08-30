"use strict";

// A streaming T-SQL DDL scanner. It never materialises the file: `fs.readSync` fills a fixed buffer
// and lines are handed off as they complete, so peak memory is flat in input size (task 184, C2).

const fs = require("node:fs");
const ddl = require("./ddl.js");

const CHUNK = 64 * 1024;
// A statement larger than this is degraded to a table-level write rather than accumulated, so peak
// memory stays flat in file size (task 184, C2) instead of following the widest statement.
const PENDING_CAP = 256 * 1024;

/**
 * @typedef {{kind: string, name: string, qualified_name: string, file_path: string,
 *   line_start: number, line_end: number, modifiers: string[], params: unknown[],
 *   is_test: boolean, extra: Record<string, string>}} Node
 * @typedef {{kind: string, source_qname: string, target_raw: string, file_path: string,
 *   line: number, confidence_tier: string}} Edge
 * @typedef {{block: number, string: boolean, elided: boolean}} ScanState
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
        if (next === "'") { state.elided = true; i += 2; continue; }
        state.string = false;
        out += (state.elided ? "\u2026" : "") + ch;
      } else {
        state.elided = true;
      }
      i += 1;
      continue;
    }
    if (ch === "-" && next === "-") break;
    if (ch === "/" && next === "*") { state.block += 1; i += 2; continue; }
    if (ch === "'") { state.string = true; state.elided = false; out += ch; i += 1; continue; }
    out += ch;
    i += 1;
  }
  return out;
}

// `CREATE`/`ALTER`/`CREATE OR ALTER` all declare the object; T-SQL spells the keyword both ways
// (PROC/PROCEDURE) and both reach the same construct, so both are matched (claim 019-C2).
const CREATE_RE =
  /\b(?:create|alter)\s+(?:or\s+alter\s+)?(proc(?:edure)?|function)\s+((?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/i;

// EXEC and EXECUTE are the same construct (019-C2). A parenthesised or variable target is dynamic.
const EXEC_RE =
  /\b(exec(?:ute)?)\s+(?:@\w+\s*=\s*)?(\(|@\w+|(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/gi;

const BATCH_RE = /^\s*go\s*(?:\d+\s*)?$/i;

// Tier 2 (022). A trigger is a routine like any other — it is `Function` with an `object_type`, so
// the vocabulary spend stays at Table + Column + WRITES.
const TRIGGER_RE =
  /\b(?:create|alter)\s+(?:or\s+alter\s+)?trigger\s+((?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*)(?:\s*\.\s*(?:\[[^\]]*\]|"[^"]*"|[A-Za-z_@#][\w@#$]*))*)/i;
const TABLE_RE = /\b(?:create|alter)\s+table\b/i;
const INSERT_RE = /\binsert\b/i;
const UPDATE_RE = /\bupdate\b/i;
// A statement ends where the next one starts. Only tested at paren depth 0, so a keyword inside a
// table body or a column list never splits the statement that contains it.
const BOUNDARY_RE =
  /^\s*(go|create|alter|insert|update|delete|if|while|begin|end|return|declare|exec|execute)\b|^\s*;/i;
const DYNAMIC_PROCS = new Set(["sp_executesql", "sp_execute", "dbo.sp_executesql"]);

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
  const state = { block: 0, string: false, elided: false };
  /** @type {{qname: string, node: Node}|null} */
  let current = null;
  let lineNo = 0;
  let lastLine = 0;
  /** @type {{kind: string, buf: string, line: number, depth: number, opened: boolean}|null} */
  let pending = null;
  /** @type {Map<string, Node>} */
  const tables = new Map();
  /** @type {Map<string, Node>} */
  const columns = new Map();

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
   * @returns {Node}
   */
  const table = (qname, line) => {
    const seen = tables.get(qname);
    if (seen) return seen;
    /** @type {Node} */
    const node = {
      kind: "Table", name: lastSegment(qname, "."), qualified_name: qname, file_path: qpath,
      line_start: line, line_end: line, modifiers: [], params: [], is_test: false, extra: {},
    };
    tables.set(qname, node);
    nodes.push(node);
    edges.push({
      kind: "CONTAINS", source_qname: qpath, target_raw: qname,
      file_path: qpath, line, confidence_tier: "RESOLVED",
    });
    return node;
  };

  /**
   * @param {string} tableQname
   * @param {{name: string, dataType: string, dflt: string|null}} col
   * @param {number} line
   */
  const column = (tableQname, col, line) => {
    const qname = `${tableQname}::${col.name}`;
    const seen = columns.get(qname);
    /** @type {Record<string, string>} */
    const extra = {};
    if (col.dataType !== "") extra["data_type"] = col.dataType;
    if (col.dflt !== null) extra["default"] = col.dflt;
    if (seen) {
      // The other DEFAULT spelling arrives after the column itself; fill it in rather than
      // emitting a second node for the same column (022 AC5).
      Object.assign(seen.extra, extra);
      return;
    }
    /** @type {Node} */
    const node = {
      kind: "Column", name: col.name, qualified_name: qname, file_path: qpath,
      line_start: line, line_end: line, modifiers: [], params: [], is_test: false, extra,
    };
    columns.set(qname, node);
    nodes.push(node);
    edges.push({
      kind: "CONTAINS", source_qname: tableQname, target_raw: qname,
      file_path: qpath, line, confidence_tier: "RESOLVED",
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

  const flush = () => {
    if (!pending) return;
    const { kind, buf, line } = pending;
    pending = null;
    if (buf.length > PENDING_CAP) {
      const guess = kind === "table" ? null : (ddl.readInsert(buf) ?? ddl.readUpdate(buf));
      if (guess) guess.table = splitName(guess.table) ?? guess.table;
      // Truncated: the statement was never read to its end, so the target is what we saw of it.
      if (guess) writes(guess.table, null, line, "DYNAMIC");
      return;
    }
    if (kind === "table") {
      const named = ddl.readNamedDefault(buf);
      const head = /\b(?:create|alter)\s+table\s+/i.exec(buf);
      const target = head ? ddl.readQualified(buf, head.index + head[0].length) : null;
      if (!target) return;
      const qname = splitName(target.name);
      if (!qname) return;
      table(qname, line);
      if (named) {
        column(qname, { name: named.column, dataType: "", dflt: named.dflt }, line);
        return;
      }
      const body = ddl.readParens(buf, target.next);
      if (body) {
        for (const col of ddl.readColumns(body.body)) column(qname, col, line);
        return;
      }
      const added = /\badd\s+/i.exec(buf.slice(target.next));
      if (added) {
        const col = ddl.readColumnDef(buf.slice(target.next + added.index + added[0].length));
        if (col) column(qname, col, line);
      }
      return;
    }
    const stmt = kind === "insert" ? ddl.readInsert(buf) : ddl.readUpdate(buf);
    if (!stmt) return;
    const qname = splitName(stmt.table);
    if (qname) writes(qname, stmt.columns, line);
  };

  /** @param {number} endLine */
  const closeCurrent = (endLine) => {
    if (current) {
      current.node.line_end = endLine;
      current = null;
    }
  };

  /** @param {string} line */
  const onLine = (line) => {
    lineNo += 1;
    lastLine = lineNo;
    const code = stripToCode(line, state);
    if (code.trim() === "") return;

    // A statement in progress absorbs the line unless a new one starts at paren depth 0.
    if (pending && pending.depth <= 0 && BOUNDARY_RE.test(code)) flush();
    if (pending) {
      pending.buf += ` ${code}`;
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
          params: [],
          is_test: false,
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
        current = { qname, node };
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
          line_start: lineNo, line_end: lineNo, modifiers: [], params: [], is_test: false, extra,
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
      // A dynamic target is emitted, never dropped and never RESOLVED (AC7): the call site is a fact
      // even where the callee is not knowable, and the core decides what an unlinkable edge means.
      edges.push({
        kind: "CALLS",
        source_qname: source,
        target_raw: dynamic || qname === null || dynamicProc ? "(dynamic)" : qname,
        file_path: qpath,
        line: lineNo,
        confidence_tier: dynamic || qname === null || dynamicProc ? "DYNAMIC" : "RESOLVED",
      });
    }

    const kind = TABLE_RE.test(code)
      ? "table"
      : INSERT_RE.test(code)
        ? "insert"
        : UPDATE_RE.test(code)
          ? "update"
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

  nodes.unshift({
    kind: "File",
    name: lastSegment(qpath, "/"),
    qualified_name: qpath,
    file_path: qpath,
    line_start: 1,
    line_end: Math.max(lastLine, 1),
    modifiers: [],
    params: [],
    is_test: false,
    extra: {},
  });

  return { path: qpath, ok: true, nodes, edges };
}

module.exports = { parseFile, splitName };
