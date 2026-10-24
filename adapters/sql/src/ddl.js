"use strict";

// Pure statement readers for T-SQL data-definition and write statements (task 022, tier 2). They
// take text already stripped to code by scan.js and return facts; nothing here touches the
// filesystem or the contract, so each one is testable on a string.

// A table-level entry that is not a column. `KEY` covers the `PRIMARY KEY`/`FOREIGN KEY` spellings
// once the leading word has been read, and `PERIOD` is the temporal-table entry. `COLUMN` is the
// ANSI `ADD COLUMN` keyword — never a real column name (task 228).
const NOT_A_COLUMN = new Set([
  "constraint", "primary", "unique", "foreign", "check", "index", "key", "period", "column",
]);

// Bare words no dialect uses for a Table/Column — refusing them is honest (R5.2); emitting them
// is not. Bare is the whole rule: `[Key]` / `"key"` IS how SQL names an object after a keyword,
// so a delimited name is never reserved, however it is spelled.
const RESERVED_OBJECT_NAMES = new Set([
  "if", "not", "exists", "column", "constraint", "table", "key",
]);

// What ends a DEFAULT expression inside a column definition. Everything up to one of these, at
// paren depth 0, is the expression as written.
const AFTER_DEFAULT = new Set([
  "not", "null", "primary", "unique", "check", "references", "identity", "constraint",
  "collate", "for", "with", "rowguidcol", "sparse", "foreign", "index",
]);

/**
 * Split `text` on `sep` at paren depth 0 — a comma inside `decimal(18, 2)` is not a separator.
 * Pieces keep their start offset in `text` (after leading trim) for per-column lines (254).
 * @param {string} text
 * @param {string} sep
 * @returns {{text: string, start: number}[]}
 */
function splitTopLevelPieces(text, sep) {
  const raw = [];
  let depth = 0;
  let curStart = 0;
  let cur = "";
  for (let i = 0; i < text.length; i++) {
    const ch = text[i] ?? "";
    if (ch === "(") depth += 1;
    else if (ch === ")") depth -= 1;
    if (ch === sep && depth === 0) {
      raw.push({ text: cur, start: curStart });
      cur = "";
      curStart = i + 1;
      continue;
    }
    cur += ch;
  }
  raw.push({ text: cur, start: curStart });
  const out = [];
  for (const piece of raw) {
    const trimmed = piece.text.trim();
    if (trimmed === "") continue;
    const lead = piece.text.length - piece.text.trimStart().length;
    out.push({ text: trimmed, start: piece.start + lead });
  }
  return out;
}

/**
 * @param {string} text
 * @param {string} sep
 * @returns {string[]}
 */
function splitTopLevel(text, sep) {
  return splitTopLevelPieces(text, sep).map((p) => p.text);
}

/**
 * Read one possibly-delimited identifier starting at `i`, skipping leading space.
 *
 * `delimited` says the source wrapped this name in `[]` or `""`. The name itself is returned
 * unwrapped, so this flag is the only thing left that separates a deliberate `[Key]` from a bare
 * keyword the reader mistook for a name — callers refusing reserved words need it.
 * @param {string} text
 * @param {number} i
 * @returns {{name: string, next: number, delimited: boolean}|null}
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
        return { name, next: j, delimited: true };
      }
      name += text[j];
      j += 1;
    }
    return null;
  }
  const rest = text.slice(j);
  const m = /^[A-Za-z_@#][\w@#$]*/.exec(rest);
  if (!m) return null;
  return { name: m[0], next: j + m[0].length, delimited: false };
}

/**
 * Read a dotted object name (`[dbo].[My Table]`) starting at `i`.
 *
 * `delimited` is the LAST segment's flag, because that is the segment a caller compares against
 * the reserved list — `dbo.[Key]` is a delimited object in an undelimited schema.
 * @param {string} text
 * @param {number} i
 * @returns {{name: string, next: number, delimited: boolean}|null}
 */
function readQualified(text, i) {
  const parts = [];
  let j = i;
  let delimited = false;
  for (;;) {
    const part = readIdent(text, j);
    if (!part) break;
    parts.push(part.name);
    delimited = part.delimited;
    j = part.next;
    const after = /^\s*\.\s*/.exec(text.slice(j));
    if (!after) break;
    j += after[0].length;
  }
  if (parts.length === 0) return null;
  return { name: parts.join("."), next: j, delimited };
}

/**
 * The balanced-parenthesis slice starting at the first `(` at or after `i`.
 * ``openAt`` is the index of that `(` in ``text`` (254 — line map must count newlines before it).
 * @param {string} text
 * @param {number} i
 * @returns {{body: string, next: number, openAt: number}|null}
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
      if (depth === 0) {
        return { body: text.slice(start + 1, j), next: j + 1, openAt: start };
      }
    }
    j += 1;
  }
  return null;
}

/**
 * One column definition read out of a table body, or null when the entry is a table constraint.
 * Inline ``REFERENCES T[(cols)]`` is captured on ``references``; table-level FK entries stay null.
 * Nullability / IDENTITY / inline PRIMARY KEY ride optional fields (omit when the DDL is silent).
 * @param {string} def
 * @returns {{name: string, dataType: string, dflt: string|null, delimited: boolean,
 *   references: {table: string, columns: string[]|null}|null,
 *   nullable?: boolean, identity?: {seed: number, increment: number},
 *   primaryKey?: number}|null}
 */
function readColumnDef(def) {
  const first = readIdent(def, 0);
  if (!first) return null;
  // `[key] int` is a column; bare `KEY (...)` is the table-level entry NOT_A_COLUMN names.
  if (!first.delimited && NOT_A_COLUMN.has(first.name.toLowerCase())) return null;

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
  /** @type {{name: string, dataType: string, dflt: string|null, delimited: boolean,
   *   references: {table: string, columns: string[]|null}|null,
   *   nullable?: boolean, identity?: {seed: number, increment: number}, primaryKey?: number}} */
  const out = {
    name: first.name,
    dataType,
    dflt: readDefault(rest),
    delimited: first.delimited,
    references: readInlineReferences(rest),
  };
  const nullable = readNullability(rest);
  if (nullable !== undefined) out.nullable = nullable;
  const identity = readIdentity(rest);
  if (identity !== undefined) out.identity = identity;
  if (/\bprimary\s+key\b/i.test(rest)) out.primaryKey = 1;
  return out;
}

/**
 * Explicit ``NULL`` / ``NOT NULL`` in a column's trailing clauses, or undefined when neither.
 * Session default nullability is unmeasured (R5.6) — never invent ``true``.
 * ``DEFAULT (NULL)`` is a default expression, not a nullability clause — strip DEFAULT first.
 * @param {string} rest
 * @returns {boolean|undefined}
 */
function readNullability(rest) {
  const withoutDefault = stripDefaultClause(rest);
  if (/\bnot\s+null\b/i.test(withoutDefault)) return false;
  // A bare NULL token as a column attribute (not inside another word).
  if (/(?:^|[^\w])null(?:[^\w]|$)/i.test(withoutDefault)) return true;
  return undefined;
}

/**
 * Remove a ``DEFAULT …`` clause from trailing column text so later attribute scans do not
 * mistake ``DEFAULT (NULL)`` for a nullability clause.
 * @param {string} rest
 * @returns {string}
 */
function stripDefaultClause(rest) {
  const m = /\bdefault\b/i.exec(rest);
  if (!m) return rest;
  const start = m.index;
  let j = m.index + m[0].length;
  const parens = readParens(rest, j);
  if (parens) {
    return rest.slice(0, start) + " " + rest.slice(parens.next);
  }
  // Bare ``DEFAULT NULL`` — NULL is the *value*, not a nullability clause. Consume it first;
  // AFTER_DEFAULT still ends later attributes (``DEFAULT getdate() NULL``).
  const litNull = /^\s*null\b/i.exec(rest.slice(j));
  if (litNull) {
    j += litNull[0].length;
    return rest.slice(0, start) + " " + rest.slice(j);
  }
  // Bare DEFAULT expr ends at the next attribute keyword (same set as AFTER_DEFAULT).
  let depth = 0;
  while (j < rest.length) {
    const word = /^\s*([A-Za-z_][\w]*)/.exec(rest.slice(j));
    if (word && depth === 0 && AFTER_DEFAULT.has((word[1] ?? "").toLowerCase())) break;
    const ch = rest[j] ?? "";
    if (ch === "(") depth += 1;
    else if (ch === ")") depth -= 1;
    j += 1;
  }
  return rest.slice(0, start) + " " + rest.slice(j);
}

/**
 * T-SQL ``IDENTITY`` or ``IDENTITY(seed, increment)``. Bare IDENTITY uses the grammar default (1,1).
 * Refuses Postgres ``GENERATED … AS IDENTITY`` — that is not this dialect (228).
 * @param {string} rest
 * @returns {{seed: number, increment: number}|undefined}
 */
function readIdentity(rest) {
  // Require IDENTITY not preceded by AS (GENERATED … AS IDENTITY) within the preceding token run.
  const m = /(?:^|[^\w])identity\b\s*(?:\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\))?/i.exec(rest);
  if (!m) return undefined;
  const before = rest.slice(0, m.index).trimEnd();
  if (/\bas$/i.test(before)) return undefined;
  if (m[1] !== undefined && m[2] !== undefined) {
    return { seed: Number(m[1]), increment: Number(m[2]) };
  }
  return { seed: 1, increment: 1 };
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
 * ``name`` is the constraint's own name when written (``CONSTRAINT n``), else null.
 * @param {string} def
 * @returns {{name: string|null, fromColumns: string[], toTable: string,
 *   toColumns: string[]|null}|null}
 */
function readForeignKeyDef(def) {
  let j = 0;
  let name = null;
  const first = readIdent(def, 0);
  if (!first) return null;
  if (first.name.toLowerCase() === "constraint") {
    const named = readIdent(def, first.next);
    if (!named) return null;
    name = named.name;
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
  return { name, fromColumns, toTable: target.table, toColumns: target.columns };
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
 * One table-level ``PRIMARY KEY`` / ``CONSTRAINT … PRIMARY KEY`` entry, or null.
 * ``NOT_A_COLUMN`` correctly refuses these as columns; this reader is the second pass.
 * @param {string} def
 * @returns {{name: string|null, columns: string[]}|null}
 */
function readPrimaryKeyDef(def) {
  let j = 0;
  let name = null;
  const first = readIdent(def, 0);
  if (!first) return null;
  const word = first.name.toLowerCase();
  if (word === "constraint") {
    const named = readIdent(def, first.next);
    if (!named) return null;
    name = named.name;
    j = named.next;
  } else if (word === "primary") {
    j = 0;
  } else {
    return null;
  }
  const primary = readIdent(def, j);
  if (!primary || primary.name.toLowerCase() !== "primary") return null;
  const key = readIdent(def, primary.next);
  if (!key || key.name.toLowerCase() !== "key") return null;
  let afterKey = key.next;
  // Optional CLUSTERED / NONCLUSTERED between KEY and the column list (T-SQL table_constraint).
  const clustered = readIdent(def, afterKey);
  if (clustered && /^(?:non)?clustered$/i.test(clustered.name)) {
    afterKey = clustered.next;
  }
  const cols = readParens(def, afterKey);
  if (!cols) return null;
  const columns = readIdentList(cols.body);
  if (columns.length === 0) return null;
  return { name, columns };
}

/**
 * Every table-level primary key declared in a CREATE TABLE body, in source order.
 * @param {string} body
 * @returns {{columns: string[]}[]}
 */
function readPrimaryKeys(body) {
  const out = [];
  for (const def of splitTopLevel(body, ",")) {
    const pk = readPrimaryKeyDef(def);
    if (pk) out.push(pk);
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

  // Bare ``DEFAULT NULL`` — NULL is the default *value*, not an AFTER_DEFAULT terminator.
  const litNull = /^\s*(null)\b/i.exec(rest.slice(j));
  if (litNull) return litNull[1];

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
 * Each row carries ``bodyOffset`` — byte index of the definition's first non-space char in
 * ``body`` — so the scanner can map it to a line without a second pass (254).
 * @param {string} body
 * @returns {(NonNullable<ReturnType<typeof readColumnDef>> & {bodyOffset: number})[]}
 */
function readColumns(body) {
  const out = [];
  for (const piece of splitTopLevelPieces(body, ",")) {
    const col = readColumnDef(piece.text);
    if (col) out.push({ ...col, bodyOffset: piece.start });
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
  // `UPDATE c SET … FROM dbo.T c` names an alias; its table is the FROM source (333).
  return { table: aliasSourceTable(code, target.next + set.index, target) ?? target.name, columns };
}

/**
 * `ALTER TABLE t ADD CONSTRAINT n DEFAULT (expr) FOR col` — T-SQL's other way to declare a default,
 * and the one a migration usually takes. Returns the column it names and the expression.
 * @param {string} code
 * @returns {{column: string, dflt: string, delimited: boolean}|null}
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
  return { column: column.name, dflt: expr, delimited: column.delimited };
}

/**
 * True when `name` (last segment of a qname) is a BARE reserved word, never a real object.
 *
 * `delimited` is required rather than optional: SQL's own escape hatch for naming an object after
 * a keyword is to delimit it, so refusing `[Key]` would drop a legal table (and, when it is a
 * file's only DDL, report the file unreadable). A caller that cannot say either way has not read
 * the name yet.
 * @param {string} name
 * @param {boolean} delimited
 * @returns {boolean}
 */
function isReservedObjectName(name, delimited) {
  if (delimited) return false;
  return RESERVED_OBJECT_NAMES.has(name.toLowerCase());
}


/**
 * DELETE FROM t — table only; never a column list (328).
 * @param {string} code
 * @returns {{table: string}|null}
 */
function readDelete(code) {
  const re = /\bdelete\s+(?:top\s*\([^)]*\)\s*(?:percent\s+)?)?(?:from\s+)?/gi;
  for (let m = re.exec(code); m; m = re.exec(code)) {
    // `FOR` / `AFTER` / `INSTEAD OF` / `ON DELETE` name a trigger or FK event, not a statement.
    if (/(?:\bfor|\bafter|\bof|\bon|,)\s*$/i.test(code.slice(0, m.index))) continue;
    const target = readQualified(code, m.index + m[0].length);
    if (!target || target.name.toLowerCase() === "as") continue;
    if (isReservedObjectName(target.name, target.delimited)) continue;
    const from = /^\s*from\b/i.test(code.slice(target.next)) ? target.next : -1;
    return { table: (from < 0 ? null : aliasSourceTable(code, from, target)) ?? target.name };
  }
  return null;
}

/**
 * The top-level FROM / JOIN source that `target` aliases, scanning `code` from offset `from` — the
 * one alias resolver for `DELETE c FROM dbo.T c` (328) and `UPDATE c SET … FROM dbo.T c` (333).
 * A source inside parentheses scopes its own alias and is skipped; a bare top-level statement
 * keyword ends the statement (T-SQL needs no `;`); a delimited `[Select]` is a name, not one (333).
 * @param {string} code
 * @param {number} from
 * @param {{name: string}} target
 * @returns {string|null}
 */
function aliasSourceTable(code, from, target) {
  const tail = code.slice(from);
  const alias = target.name.toLowerCase();
  const source = /\b(?:(?:from|join)\s+|(?<![["])(select|insert|update|delete|merge|exec|execute)\b(?![\]"]))/gi;
  let depth = 0;
  let seen = 0;
  for (let m = source.exec(tail); m; m = source.exec(tail)) {
    for (; seen < m.index; seen++) {
      if (tail[seen] === "(") depth += 1;
      else if (tail[seen] === ")") depth -= 1;
    }
    if (depth !== 0) continue;
    if (m[1]) break;
    const table = readQualified(tail, m.index + m[0].length);
    if (!table) continue;
    const named = /^\s+(?:as\s+)?/i.exec(tail.slice(table.next));
    const next = named ? readIdent(tail, table.next + named[0].length) : null;
    if (next && next.name.toLowerCase() === alias) return table.name;
  }
  return null;
}

// Pseudo-tables a trigger reads and a CTE's own name are not tables a statement reads (390).
const NOT_A_SOURCE = new Set(["inserted", "deleted"]);
const CTE_NAME = /(?:\bwith|,)\s*([A-Za-z_][\w@#$]*|\[[^\]]+\])\s*(?:\([^)]*\)\s*)?as\s*\(/gi;

/**
 * The tables a statement reads: every `FROM` / `JOIN` source, subqueries included (390).
 * A temp table (`#t`), a table variable (`@t`), a derived table, a table-valued function
 * call and a CTE's own name are not read from the database, so none is a source.
 * Each carries ``at``, the byte offset of its keyword, so a caller can place it on its own line.
 * @param {string} code
 * @returns {{name: string, at: number}[]}
 */
function readSources(code) {
  const ctes = new Set();
  for (let m = CTE_NAME.exec(code); m; m = CTE_NAME.exec(code)) {
    ctes.add((m[1] ?? "").replace(/^\[|\]$/g, "").toLowerCase());
  }
  CTE_NAME.lastIndex = 0;
  /** @type {{name: string, at: number}[]} */
  const out = [];
  const keyword = /\b(?:from|join)\s+/gi;
  /** @type {number[]} */
  const open = []; // offsets of the `(` still open before the keyword
  let seen = 0;
  for (let m = keyword.exec(code); m; m = keyword.exec(code)) {
    for (; seen < m.index; seen++) {
      if (code[seen] === "(") open.push(seen);
      else if (code[seen] === ")") open.pop();
    }
    // `TRIM(' ' FROM x)`, `EXTRACT(YEAR FROM d)`: a FROM inside a call's parens names no table.
    const inner = open.length ? open[open.length - 1] : -1;
    if (inner >= 0 && !/^\s*(?:select|with)\b/i.test(code.slice(inner + 1))) continue;
    let at = m.index + m[0].length;
    // `FROM a x, b y` — the old comma join: each listed source is read.
    for (;;) {
      const table = readQualified(code, at);
      if (!table) break;
      const name = table.name;
      const lower = name.toLowerCase();
      const call = /^\s*\(/.test(code.slice(table.next)); // a table-valued function call
      const skip = /^[#@]/.test(name) || NOT_A_SOURCE.has(lower) || ctes.has(lower) || call;
      if (!skip && !out.some((seen) => seen.name === name)) out.push({ name, at: m.index });
      const more = /^\s*(?:as\s+)?(?:[A-Za-z_][\w@#$]*\s*)?,\s*/i.exec(code.slice(table.next));
      if (call || !more) break;
      at = table.next + more[0].length;
    }
  }
  return out;
}

// Reserved words a statement uses that never name a column of its source (410), plus the table
// hints. A date part, `Path` or `Rows` is a common column name, so those are read by place instead.
// A delimited `[Status]` is a name however it is spelled, so only bare words are kept.
const NOT_A_COLUMN_READ = new Set([
  "select", "from", "where", "and", "or", "not", "null", "is", "in", "like", "between", "as", "on",
  "join", "inner", "left", "right", "full", "outer", "cross", "apply", "order", "by", "group",
  "having", "union", "all", "distinct", "top", "percent", "case", "when", "then", "else", "end",
  "asc", "desc", "exists", "with", "nolock", "readuncommitted", "holdlock", "updlock", "rowlock",
  "readpast", "into", "values", "set", "insert", "update", "delete", "merge", "using", "output",
  "declare", "begin", "return", "returns", "if", "while", "go", "create", "alter", "view",
  "procedure", "proc", "function", "table", "trigger", "for", "of", "over", "escape", "collate",
  "pivot", "unpivot", "except", "intersect", "default", "any", "some", "current_timestamp",
  "current_user", "session_user", "system_user", "identity", "partition",
]);
const PART = String.raw`(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_@#][\w@#$]*)`;
// A name and its dotted tail; `t.*` keeps its star so it is seen, then never bound.
const CHAIN = new RegExp(String.raw`${PART}(?:\s*\.\s*(?:${PART}|\*))*`, "g");
// Clauses whose words are syntax, not names: paging, `FOR XML/JSON`, `WITH TIES`.
const NOT_NAMES =
  /\boffset\s+\S+\s+rows?\b(?:\s+fetch\s+(?:first|next)\s+\S+\s+rows?\s+only\b)?|\bfor\s+(?:xml|json)\b[^;]*|\bwith\s+ties\b/gi;
// The first argument of a date function is a date part, never a column.
const DATE_PART_ARG = /\b(?:dateadd|datediff|datediff_big|datepart|datename|datetrunc|date_bucket)\s*\(\s*$/i;
// A top-N count precedes the select list; any other number or name before a bare word aliases it.
const TOP_N = /\btop\s*\(?\s*\d+\s*\)?\s*(?:percent\s*)?(?:with\s+ties\s*)?$/i;

/** @param {string} part */
function unbracket(part) {
  return part.replace(/^\[|\]$/g, "").replace(/^"|"$/g, "");
}

/**
 * Every FROM / JOIN / APPLY item of a statement, a skipped one included (a #temp, `inserted`, a
 * CTE name, a derived table), with its alias and the span its name and alias cover (410).
 * @param {string} code
 * @returns {{name: string|null, alias: string|null, from: number, to: number}[]}
 */
function sourceItems(code) {
  /** @type {{name: string|null, alias: string|null, from: number, to: number}[]} */
  const items = [];
  const keyword = /\b(?:from|join|apply)\s+/gi;
  const open = [];
  let seen = 0;
  for (let m = keyword.exec(code); m; m = keyword.exec(code)) {
    for (; seen < m.index; seen++) {
      if (code[seen] === "(") open.push(seen);
      else if (code[seen] === ")") open.pop();
    }
    const inner = open.length ? open[open.length - 1] ?? -1 : -1;
    if (inner >= 0 && !/^\s*(?:select|with)\b/i.test(code.slice(inner + 1))) continue;
    let at = m.index + m[0].length;
    for (;;) {
      if (/^\s*\(/.test(code.slice(at))) {
        items.push({ name: null, alias: null, from: at, to: at });  // a derived table or a call
        break;
      }
      const table = readQualified(code, at);
      if (!table) break;
      const named = /^\s+(?:as\s+)?/i.exec(code.slice(table.next));
      const alias = named ? readIdent(code, table.next + named[0].length) : null;
      const word = alias && (alias.delimited || !NOT_A_COLUMN_READ.has(alias.name.toLowerCase()))
        ? alias : null;
      const to = word ? word.next : table.next;
      items.push({ name: table.name, alias: word ? word.name : null, from: at, to });
      const more = /^\s*,\s*/.exec(code.slice(to));
      if (/^\s*\(/.test(code.slice(table.next)) || !more) break;
      at = to + more[0].length;
    }
  }
  return items;
}

/**
 * The names a statement may qualify each real source by — alias, own name, last part — lower-cased
 * (410). A name two sources share (an alias reused in a subquery) binds neither: never a guess.
 * @param {{name: string|null, alias: string|null}[]} items
 * @param {{name: string}[]} sources
 * @returns {Map<string, string>}
 */
function sourceNames(items, sources) {
  /** @type {Map<string, string|null>} */
  const names = new Map();
  const bind = (/** @type {string} */ key, /** @type {string} */ table) => {
    const had = names.get(key);
    names.set(key, had === undefined || had === table ? table : null);
  };
  for (const item of items) {
    const source = sources.find((s) => s.name === item.name);
    if (!source) continue;
    bind(source.name.toLowerCase(), source.name);
    bind((source.name.split(".").pop() ?? source.name).toLowerCase(), source.name);
    if (item.alias) bind(item.alias.toLowerCase(), source.name);
  }
  /** @type {Map<string, string>} */
  const bound = new Map();
  for (const [key, table] of names) if (table !== null) bound.set(key, table);
  return bound;
}

/**
 * The columns a statement reads, each with its table (410): `alias.col` / `table.col` against its
 * sources; and, when `bare` and the statement has exactly one FROM item and no CTE, a bare name
 * that is no keyword, call, date part, alias, parameter or temp. First seen, once each. A source
 * read by `*` (or `t.*`) gives no column at all: which columns it reads is not known.
 * @param {string} raw
 * @param {boolean} bare
 * @returns {{table: string, column: string}[]}
 */
function readColumnReads(raw, bare) {
  const code = raw.replace(NOT_NAMES, (m) => " ".repeat(m.length));
  const items = sourceItems(code);
  const names = sourceNames(items, readSources(code));
  const sources = [...new Set(names.values())];
  if (sources.length === 0) return [];
  // A CTE or a derived table answers its outer query's bare names, never the base table (W5).
  CTE_NAME.lastIndex = 0;
  const cte = CTE_NAME.test(code);
  CTE_NAME.lastIndex = 0;
  const only = bare && items.length === 1 && !cte && sources.length === 1 ? sources[0] : null;
  const select = /\bselect\b/i.exec(code);
  /** @type {{table: string, column: string}[]} */
  const out = [];
  const seen = new Set();
  const add = (/** @type {string} */ table, /** @type {string} */ column) => {
    const key = `${table}::${column}`.toLowerCase();
    if (!seen.has(key)) { seen.add(key); out.push({ table, column }); }
  };
  CHAIN.lastIndex = 0;
  for (let m = CHAIN.exec(code); m; m = CHAIN.exec(code)) {
    const before = code.slice(0, m.index).trimEnd();
    if (before.endsWith(".") || before.endsWith(":") || /[0-9]$/.test(code.slice(0, m.index))) {
      continue;
    }
    const parts = m[0].split(/\s*\.\s*/).map(unbracket);
    const column = parts[parts.length - 1] ?? "";
    if (parts.length > 1) {
      const table = names.get(parts.slice(0, -1).join(".").toLowerCase());
      if (table && column !== "*") add(table, column);
      continue;
    }
    if (only === null || !select || m.index < select.index + select[0].length) continue;
    if (items.some((item) => m.index >= item.from && m.index < item.to)) continue;
    if (bareColumn(m[0], code.slice(m.index + m[0].length), before)) add(only, column);
  }
  const starred = starredSources(code, names);
  return starred === null ? [] : out.filter(({ table }) => !starred.has(table));
}

/**
 * A bare word that can only be a column (410): no keyword, call, date part, parameter or temp, and
 * not an alias — a word after `AS`, after `)` or `END`, or straight after another name or number.
 * @param {string} token
 * @param {string} after
 * @param {string} before
 */
function bareColumn(token, after, before) {
  const delimited = /^[[\"]/.test(token);
  const lower = unbracket(token).toLowerCase();
  if (/^[@#]/.test(token) || (!delimited && NOT_A_COLUMN_READ.has(lower))) return false;
  if (/^\s*\(/.test(after) || DATE_PART_ARG.test(before) || /\bas$/i.test(before)) return false;
  if (TOP_N.test(before)) return true;
  if (/(?:\)|\bend)$/i.test(before)) return false;
  const prior = /(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[\w@#$]+)$/.exec(before);
  if (!prior) return true;
  const word = prior[0];
  return !/^[[\"0-9]/.test(word) && NOT_A_COLUMN_READ.has(word.toLowerCase());
}

/**
 * The sources a statement selects with `*` — `t.*` names one; a bare `*` in a select list all
 * of them, signalled by null (410). `count(*)` is a call, not a select list.
 * @param {string} code
 * @param {Map<string, string>} names
 * @returns {Set<string>|null}
 */
function starredSources(code, names) {
  if (/(?:\bselect\s+(?:distinct\s+)?(?:top\s*\(?\s*\d+\s*\)?\s*(?:percent\s+)?)?|,\s*)\*/i.test(code)) {
    return null;
  }
  const starred = new Set();
  const dotted = new RegExp(String.raw`(${PART}(?:\s*\.\s*${PART})*)\s*\.\s*\*`, "g");
  for (let m = dotted.exec(code); m; m = dotted.exec(code)) {
    const key = (m[1] ?? "").split(/\s*\.\s*/).map(unbracket);
    const table = names.get(key.join(".").toLowerCase());
    if (table) starred.add(table);
  }
  return starred;
}

/**
 * TRUNCATE TABLE t (328).
 * @param {string} code
 * @returns {{table: string}|null}
 */
function readTruncate(code) {
  const m = /\btruncate\s+(?:table\s+)?/i.exec(code);
  if (!m) return null;
  const target = readQualified(code, m.index + m[0].length);
  if (!target) return null;
  return { table: target.name };
}

/**
 * MERGE … WHEN … DELETE — the target table of a merge that can remove rows (328).
 * Insert/update-only MERGE returns null here (WRITES path may still apply separately).
 * @param {string} code
 * @returns {{table: string}|null}
 */
function readMergeDeletes(code) {
  if (!/\bmerge\b/i.test(code)) return null;
  if (!/\bwhen\b[\s\S]*?\bdelete\b/i.test(code)) return null;
  const m = /\bmerge\s+(?:top\s*\([^)]*\)\s*)?(?:into\s+)?/i.exec(code);
  if (!m) return null;
  const target = readQualified(code, m.index + m[0].length);
  if (!target) return null;
  return { table: target.name };
}

module.exports = {
  readColumns, readColumnDef, readDefault, readInsert, readUpdate, readDelete, readTruncate, readMergeDeletes, readNamedDefault,
  readForeignKeys, readForeignKeyDef, readInlineReferences,
  readPrimaryKeys, readPrimaryKeyDef, readNullability, readIdentity,
  readIdent, readQualified, readParens, readSources, readColumnReads, splitTopLevel, splitTopLevelPieces,
  isReservedObjectName, NOT_A_COLUMN,
};
