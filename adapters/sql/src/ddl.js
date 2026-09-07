"use strict";

// Pure statement readers for T-SQL data-definition and write statements (task 022, tier 2). They
// take text already stripped to code by scan.js and return facts; nothing here touches the
// filesystem or the contract, so each one is testable on a string.

// A table-level entry that is not a column. `KEY` covers the `PRIMARY KEY`/`FOREIGN KEY` spellings
// once the leading word has been read, and `PERIOD` is the temporal-table entry.
const NOT_A_COLUMN = new Set([
  "constraint", "primary", "unique", "foreign", "check", "index", "key", "period",
]);

// What ends a DEFAULT expression inside a column definition. Everything up to one of these, at
// paren depth 0, is the expression as written.
const AFTER_DEFAULT = new Set([
  "not", "null", "primary", "unique", "check", "references", "identity", "constraint",
  "collate", "for", "with", "rowguidcol", "sparse", "foreign", "index",
]);

/**
 * Split `text` on `sep` at paren depth 0 — a comma inside `decimal(18, 2)` is not a separator.
 * @param {string} text
 * @param {string} sep
 * @returns {string[]}
 */
function splitTopLevel(text, sep) {
  const out = [];
  let depth = 0;
  let cur = "";
  for (const ch of text) {
    if (ch === "(") depth += 1;
    else if (ch === ")") depth -= 1;
    if (ch === sep && depth === 0) { out.push(cur); cur = ""; continue; }
    cur += ch;
  }
  out.push(cur);
  return out.map((p) => p.trim()).filter((p) => p !== "");
}

/**
 * Read one possibly-delimited identifier starting at `i`, skipping leading space.
 * @param {string} text
 * @param {number} i
 * @returns {{name: string, next: number}|null}
 */
function readIdent(text, i) {
  let j = i;
  while (j < text.length && /\s/.test(text[j] ?? "")) j += 1;
  const open = text[j];
  if (open === "[" || open === '"') {
    const close = open === "[" ? "]" : '"';
    let name = "";
    j += 1;
    while (j < text.length) {
      if (text[j] === close) {
        if (text[j + 1] === close) { name += close; j += 2; continue; }
        j += 1;
        return { name, next: j };
      }
      name += text[j];
      j += 1;
    }
    return null;
  }
  const rest = text.slice(j);
  const m = /^[A-Za-z_@#][\w@#$]*/.exec(rest);
  if (!m) return null;
  return { name: m[0], next: j + m[0].length };
}

/**
 * Read a dotted object name (`[dbo].[My Table]`) starting at `i`.
 * @param {string} text
 * @param {number} i
 * @returns {{name: string, next: number}|null}
 */
function readQualified(text, i) {
  const parts = [];
  let j = i;
  for (;;) {
    const part = readIdent(text, j);
    if (!part) break;
    parts.push(part.name);
    j = part.next;
    const after = /^\s*\.\s*/.exec(text.slice(j));
    if (!after) break;
    j += after[0].length;
  }
  if (parts.length === 0) return null;
  return { name: parts.join("."), next: j };
}

/**
 * The balanced-parenthesis slice starting at the first `(` at or after `i`, inclusive.
 * @param {string} text
 * @param {number} i
 * @returns {{body: string, next: number}|null}
 */
function readParens(text, i) {
  let j = i;
  while (j < text.length && /\s/.test(text[j] ?? "")) j += 1;
  if (text[j] !== "(") return null;
  let depth = 0;
  const start = j;
  while (j < text.length) {
    if (text[j] === "(") depth += 1;
    else if (text[j] === ")") {
      depth -= 1;
      if (depth === 0) return { body: text.slice(start + 1, j), next: j + 1 };
    }
    j += 1;
  }
  return null;
}

/**
 * One column definition read out of a table body, or null when the entry is a table constraint.
 * Inline ``REFERENCES T[(cols)]`` is captured on ``references``; table-level FK entries stay null.
 * @param {string} def
 * @returns {{name: string, dataType: string, dflt: string|null,
 *   references: {table: string, columns: string[]|null}|null}|null}
 */
function readColumnDef(def) {
  const first = readIdent(def, 0);
  if (!first) return null;
  if (NOT_A_COLUMN.has(first.name.toLowerCase())) return null;

  const type = readIdent(def, first.next);
  let dataType = "";
  let cursor = first.next;
  if (type) {
    dataType = type.name;
    cursor = type.next;
    const sized = readParens(def, cursor);
    if (sized) {
      dataType += `(${sized.body.trim()})`;
      cursor = sized.next;
    }
  }
  const rest = def.slice(cursor);
  return {
    name: first.name,
    dataType,
    dflt: readDefault(rest),
    references: readInlineReferences(rest),
  };
}

/**
 * ``REFERENCES T`` or ``REFERENCES T (c1, c2)`` inside a column definition's trailing clauses.
 * @param {string} rest
 * @returns {{table: string, columns: string[]|null}|null}
 */
function readInlineReferences(rest) {
  const m = /\breferences\b/i.exec(rest);
  if (!m) return null;
  return readReferencesClause(rest, m.index + m[0].length);
}

/**
 * The target table and optional column list after the ``REFERENCES`` keyword.
 * @param {string} text
 * @param {number} i
 * @returns {{table: string, columns: string[]|null}|null}
 */
function readReferencesClause(text, i) {
  const target = readQualified(text, i);
  if (!target) return null;
  const list = readParens(text, target.next);
  if (!list) return { table: target.name, columns: null };
  const columns = [];
  for (const part of splitTopLevel(list.body, ",")) {
    const ident = readIdent(part, 0);
    if (ident) columns.push(ident.name);
  }
  return { table: target.name, columns: columns.length > 0 ? columns : null };
}

/**
 * Identifier list inside a parenthesised column list, in source order.
 * @param {string} body
 * @returns {string[]}
 */
function readIdentList(body) {
  const out = [];
  for (const part of splitTopLevel(body, ",")) {
    const ident = readIdent(part, 0);
    if (ident) out.push(ident.name);
  }
  return out;
}

/**
 * One table-level ``FOREIGN KEY`` / ``CONSTRAINT … FOREIGN KEY`` entry, or null.
 * @param {string} def
 * @returns {{fromColumns: string[], toTable: string, toColumns: string[]|null}|null}
 */
function readForeignKeyDef(def) {
  let j = 0;
  const first = readIdent(def, 0);
  if (!first) return null;
  if (first.name.toLowerCase() === "constraint") {
    const named = readIdent(def, first.next);
    if (!named) return null;
    j = named.next;
  } else if (first.name.toLowerCase() === "foreign") {
    j = 0;
  } else {
    return null;
  }
  const foreign = readIdent(def, j);
  if (!foreign || foreign.name.toLowerCase() !== "foreign") return null;
  const key = readIdent(def, foreign.next);
  if (!key || key.name.toLowerCase() !== "key") return null;
  const cols = readParens(def, key.next);
  if (!cols) return null;
  const fromColumns = readIdentList(cols.body);
  if (fromColumns.length === 0) return null;
  const refsKw = /\breferences\b/i.exec(def.slice(cols.next));
  if (!refsKw) return null;
  const target = readReferencesClause(def, cols.next + refsKw.index + refsKw[0].length);
  if (!target) return null;
  return { fromColumns, toTable: target.table, toColumns: target.columns };
}

/**
 * Every table-level foreign key declared in a CREATE TABLE body, in source order.
 * @param {string} body
 * @returns {{fromColumns: string[], toTable: string, toColumns: string[]|null}[]}
 */
function readForeignKeys(body) {
  const out = [];
  for (const def of splitTopLevel(body, ",")) {
    const fk = readForeignKeyDef(def);
    if (fk) out.push(fk);
  }
  return out;
}

/**
 * The DEFAULT expression as written in `rest`, or null when there is none.
 * @param {string} rest
 * @returns {string|null}
 */
function readDefault(rest) {
  const m = /\bdefault\b/i.exec(rest);
  if (!m) return null;
  let j = m.index + m[0].length;
  const parens = readParens(rest, j);
  if (parens) return rest.slice(j, parens.next).trim();

  let depth = 0;
  let expr = "";
  while (j < rest.length) {
    const word = /^\s*([A-Za-z_][\w]*)/.exec(rest.slice(j));
    if (word && depth === 0 && AFTER_DEFAULT.has((word[1] ?? "").toLowerCase())) break;
    const ch = rest[j] ?? "";
    if (ch === "(") depth += 1;
    else if (ch === ")") depth -= 1;
    expr += ch;
    j += 1;
  }
  const trimmed = expr.trim();
  return trimmed === "" ? null : trimmed;
}

/**
 * The columns a table body declares, in source order.
 * @param {string} body
 * @returns {{name: string, dataType: string, dflt: string|null}[]}
 */
function readColumns(body) {
  const out = [];
  for (const def of splitTopLevel(body, ",")) {
    const col = readColumnDef(def);
    if (col) out.push(col);
  }
  return out;
}

/**
 * An INSERT's target and the columns it names, or null for the column list when it names none —
 * which is a different fact from naming zero, and the caller degrades it rather than dropping it.
 * @param {string} code
 * @returns {{table: string, columns: string[]|null}|null}
 */
function readInsert(code) {
  // T-SQL makes INTO optional, and `INSERT TOP (n) INTO t` is legal: both spellings reach here.
  const m = /\binsert\s+(?:top\s*\([^)]*\)\s*)?(?:into\s+)?/i.exec(code);
  if (!m) return null;
  const target = readQualified(code, m.index + m[0].length);
  if (!target) return null;
  const list = readParens(code, target.next);
  if (!list) return { table: target.name, columns: null };
  const columns = [];
  for (const part of splitTopLevel(list.body, ",")) {
    const ident = readIdent(part, 0);
    if (ident) columns.push(ident.name);
  }
  return { table: target.name, columns: columns.length > 0 ? columns : null };
}

/**
 * An UPDATE's target and the columns its SET list assigns.
 * @param {string} code
 * @returns {{table: string, columns: string[]}|null}
 */
function readUpdate(code) {
  const m = /\bupdate\s+(?:top\s*\([^)]*\)\s*)?/i.exec(code);
  if (!m) return null;
  const target = readQualified(code, m.index + m[0].length);
  if (!target) return null;
  const set = /\bset\b/i.exec(code.slice(target.next));
  if (!set) return null;
  let tail = code.slice(target.next + set.index + set[0].length);
  // The SET list ends where the statement's next clause begins.
  const stop = /\b(from|where|output|option)\b/i.exec(tail);
  if (stop) tail = tail.slice(0, stop.index);
  const columns = [];
  for (const part of splitTopLevel(tail, ",")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    const ident = readIdent(part.slice(0, eq), 0);
    if (!ident) continue;
    // `SET t.col = …` qualifies the column; the last segment is the column itself.
    const dotted = readQualified(part.slice(0, eq), 0);
    const name = dotted ? (dotted.name.split(".").pop() ?? ident.name) : ident.name;
    columns.push(name);
  }
  return { table: target.name, columns };
}

/**
 * `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr) FOR col` — T-SQL's other way to declare a default,
 * and the one a migration usually takes. Returns the column it names and the expression.
 * @param {string} code
 * @returns {{column: string, dflt: string}|null}
 */
function readNamedDefault(code) {
  const m = /\badd\s+constraint\s+/i.exec(code);
  if (!m) return null;
  const named = readIdent(code, m.index + m[0].length);
  if (!named) return null;
  const kw = /\bdefault\b/i.exec(code.slice(named.next));
  if (!kw) return null;
  let j = named.next + kw.index + kw[0].length;
  const parens = readParens(code, j);
  let expr;
  if (parens) {
    expr = code.slice(j, parens.next).trim();
    j = parens.next;
  } else {
    const word = /^\s*(\S+)/.exec(code.slice(j));
    if (!word) return null;
    expr = (word[1] ?? "").trim();
    j += word[0].length;
  }
  const forKw = /^\s*for\b/i.exec(code.slice(j));
  if (!forKw) return null;
  const column = readIdent(code, j + forKw[0].length);
  if (!column) return null;
  return { column: column.name, dflt: expr };
}

module.exports = {
  readColumns, readColumnDef, readDefault, readInsert, readUpdate, readNamedDefault,
  readForeignKeys, readForeignKeyDef, readInlineReferences,
  readIdent, readQualified, readParens, splitTopLevel,
};
