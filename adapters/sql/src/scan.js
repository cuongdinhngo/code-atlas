"use strict";

// A streaming T-SQL DDL scanner. It never materialises the file: `fs.readSync` fills a fixed buffer
// and lines are handed off as they complete, so peak memory is flat in input size (task 184, C2).

const fs = require("node:fs");

const CHUNK = 64 * 1024;

/**
 * @typedef {{kind: string, name: string, qualified_name: string, file_path: string,
 *   line_start: number, line_end: number, modifiers: string[], params: unknown[],
 *   is_test: boolean, extra: Record<string, string>}} Node
 * @typedef {{kind: string, source_qname: string, target_raw: string, file_path: string,
 *   line: number, confidence_tier: string}} Edge
 * @typedef {{block: number, string: boolean}} ScanState
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
      // The BODY is dropped: a keyword inside a literal is data, not code. Only the closing quote is
      // kept, so `N'EXEC dbo.X'` reads as an empty literal rather than a call site.
      if (ch === "'") {
        if (next === "'") { i += 2; continue; }
        state.string = false;
        out += ch;
      }
      i += 1;
      continue;
    }
    if (ch === "-" && next === "-") break;
    if (ch === "/" && next === "*") { state.block += 1; i += 2; continue; }
    if (ch === "'") { state.string = true; out += ch; i += 1; continue; }
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
  const state = { block: 0, string: false };
  /** @type {{qname: string, node: Node}|null} */
  let current = null;
  let lineNo = 0;
  let lastLine = 0;

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

    if (BATCH_RE.test(code)) {
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
