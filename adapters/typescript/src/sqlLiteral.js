"use strict";

// A T-SQL write or EXEC at the start of a string literal (task 371; the PHP adapter's 335 shape).
// Statement grammar only — never a driver's method name (R2.2), never a SQL parse: a leading keyword,
// one object name, and the clause T-SQL requires after it, so "Update settings" reads as nothing.
// tests/contract/sql_literal_cases.json keeps this copy, the PHP original and the Python port in step.

const KINDS = {
  insert: "WRITES", update: "WRITES", merge: "WRITES", delete: "DELETES", exec: "CALLS", select: "READS",
};

const HEAD = /^(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?|select)\s+/i;
// A SELECT names its table after FROM (390). An unqualified one must be followed by a clause, or end
// a closed literal, so "Select a file from the list" reads as nothing.
const FROM = /\bfrom\s+/gi;
const AFTER_SOURCE =
  /^\s*(?:(?:where|join|inner|left|right|full|cross|order|group|having|union|with)\b|;)/i;
const NAME_PART = String.raw`(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)`;
const NAME = new RegExp(String.raw`${NAME_PART}(?:\s*\.\s*${NAME_PART})*`, "y");
const PART = new RegExp(NAME_PART, "g");
// `FROM users u WHERE` / `FROM users AS u WHERE`: an alias still needs the clause after it.
const ALIAS = new RegExp(String.raw`\s+(?:as\s+)?${NAME_PART}`, "iy");
const RETURN_CODE = /@[A-Za-z_]\w*\s*=\s*/y;
const END = /^\s*(?:;|$)/;
// T-SQL resolves an unqualified procedure in the caller's default schema, `dbo` unless set (386).
const DEFAULT_SCHEMA = "dbo";
// The EXEC guard also reads `$1`, the positional marker node's SQL drivers write.
const CLAUSES = {
  insert: /^\s*(?:\(|values\b|select\b|default\s+values\b|output\b|with\s*\()/i,
  update: /^\s*(?:set\b|with\s*\()/i,
  merge: /^\s*(?:with\s*\([^)]*\)\s*)?(?:as\s+)?(?:[A-Za-z_]\w*\s+)?using\b/i,
  delete: /^\s*(?:where\b|output\b|with\s*\()/i,
  exec: /^\s+(?:@|\?|:[A-Za-z_]|N?'|-?\d|\$\d)/,
};

// { kind, target, offset } the literal begins, or null. `closed` says the literal is the whole
// string, so its end terminates the object name; a literal cut short by `${…}` or `+` does not.
function readSqlLiteral(text, closed) {
  const head = HEAD.exec(text);
  if (!head) return null;
  let verb = head[2].split(/\s/)[0].toLowerCase();
  if (verb.startsWith("exec")) verb = "exec";
  let start = head[0].length;
  if (verb === "select") return readSelect(text, start, closed, head[1].length);
  if (verb === "exec") {
    RETURN_CODE.lastIndex = start; // `EXEC @rc = dbo.P …`, the return-code capture form
    const rc = RETURN_CODE.exec(text);
    if (rc) start += rc[0].length;
  }
  NAME.lastIndex = start;
  const name = NAME.exec(text);
  if (!name) return null;
  const parts = (name[0].match(PART) || []).map(unquote);
  if (!follows(verb, text.slice(start + name[0].length), parts.length > 1, closed)) return null;
  // A dotted target reaches no method through the bare-name fallback (204); a module
  // whose own qname is `dbo.<name>` still matches exactly, as the qualified form always has.
  if (verb === "exec" && parts.length === 1) parts.unshift(DEFAULT_SCHEMA);
  return { kind: KINDS[verb], target: parts.join("."), offset: head[1].length };
}

// The table a SELECT reads: the first top-level FROM's name, never a temp or derived one.
function readSelect(text, start, closed, offset) {
  FROM.lastIndex = start;
  let source = FROM.exec(text);
  while (source && !topLevel(text, start, source.index)) source = FROM.exec(text);
  if (!source) return null;
  NAME.lastIndex = source.index + source[0].length;
  const name = NAME.exec(text);
  if (!name) return null;
  const parts = (name[0].match(PART) || []).map(unquote);
  if (parts.length === 1 && !sourceEnds(text, NAME.lastIndex, closed)) return null;
  return { kind: KINDS.select, target: parts.join("."), offset };
}

// A clause follows the unqualified source, after an optional alias, or a closed literal ends.
function sourceEnds(text, at, closed) {
  const rest = text.slice(at);
  if (AFTER_SOURCE.test(rest) || (closed && rest.trim() === "")) return true;
  ALIAS.lastIndex = at;
  const alias = ALIAS.exec(text);
  return alias !== null && AFTER_SOURCE.test(text.slice(ALIAS.lastIndex));
}

// Is `end` outside every parenthesis and quoted string opened since `start`?
function topLevel(text, start, end) {
  let depth = 0;
  let quoted = false;
  for (const char of text.slice(start, end)) {
    if (char === "'") quoted = !quoted;
    else if (!quoted && char === "(") depth += 1;
    else if (!quoted && char === ")") depth -= 1;
  }
  return depth === 0 && !quoted;
}

// The clause T-SQL requires after the name; for DELETE / EXEC on a qualified name, its end.
function follows(verb, rest, qualified, closed) {
  if (CLAUSES[verb].test(rest)) return true;
  if (!qualified || (verb !== "delete" && verb !== "exec")) return false;
  return rest === "" ? closed : END.test(rest);
}

function unquote(part) {
  if (part.startsWith("[")) return part.slice(1, -1).replace(/\]\]/g, "]");
  if (part.startsWith('"')) return part.slice(1, -1).replace(/""/g, '"');
  return part;
}

// Words a SELECT uses that never name a column of its source (410): T-SQL keywords, table hints and
// date parts. A delimited `[Status]` is a name however it is spelled, so only bare words are kept.
const NOT_A_COLUMN = new Set(`select from where and or not null is in like between as on join inner
  left right full outer cross apply order by group having union all distinct top percent ties case
  when then else end asc desc exists with nolock readuncommitted holdlock updlock rowlock readpast
  offset fetch next first rows row only into values set insert update delete merge using matched
  output declare begin return returns if while go create alter view procedure proc function table
  trigger for after instead of over partition escape collate pivot unpivot xml path json auto except
  intersect default any some current_timestamp current_user session_user system_user identity day
  month year hour minute second millisecond week weekday quarter dayofyear dd mm yy yyyy hh mi ss ms
  wk dw qq dy`.split(/\s+/));
const STRING = /N?'(?:[^']|'')*'?/gi;
const COLUMN_PART = String.raw`(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_@#][\w@#$]*)`;
const CHAIN = new RegExp(String.raw`${COLUMN_PART}(?:\s*\.\s*(?:${COLUMN_PART}|\*))*`, "g");
const BARE_STAR =
  /(?:\bselect\s+(?:distinct\s+)?(?:top\s*\(?\s*\d+\s*\)?\s*(?:percent\s+)?)?|,\s*)\*/i;
const DOTTED_STAR = new RegExp(String.raw`(${COLUMN_PART}(?:\s*\.\s*${COLUMN_PART})*)\s*\.\s*\*`, "g");
const SECOND_SOURCE = /\bjoin\b|\bapply\b/i;
const PLACEHOLDER = [".", ":", "%", "$", "{"];

// The columns a SELECT literal reads of its first FROM's table, first seen, once each (410):
// `alias.col` / `table.col` always; a bare name only when that table is the string's one source,
// never a keyword, call, alias, parameter, temp or the source's own name. A `*` on it gives none.
function readSqlColumns(text, closed) {
  const found = readSqlLiteral(text, closed);
  if (!found || found.kind !== KINDS.select) return [];
  const target = found.target;
  const masked = text.replace(STRING, (m) => " ".repeat(m.length));
  const head = HEAD.exec(masked);
  if (!head) return [];
  const start = head[0].length;
  FROM.lastIndex = start;
  let source = FROM.exec(masked);
  while (source && !topLevel(masked, start, source.index)) source = FROM.exec(masked);
  if (!source) return [];
  NAME.lastIndex = source.index + source[0].length;
  const name = NAME.exec(masked);
  if (!name) return [];
  const names = new Set([target.toLowerCase(), (target.split(".").pop() ?? target).toLowerCase()]);
  let after = NAME.lastIndex;
  ALIAS.lastIndex = after;
  const alias = ALIAS.exec(masked);
  if (alias) {
    const tokens = alias[0].match(PART) || [];
    const token = tokens[tokens.length - 1] ?? "";
    const word = unquote(token);
    if (/^[["]/.test(token) || !NOT_A_COLUMN.has(word.toLowerCase())) {
      names.add(word.toLowerCase());
      after = ALIAS.lastIndex;
    }
  }
  if (stars(masked, names)) return [];
  const single =
    !SECOND_SOURCE.test(masked) &&
    (masked.match(FROM) || []).length === 1 &&
    !masked.slice(after).trimStart().startsWith(",");
  /** @type {string[]} */
  const out = [];
  const seen = new Set();
  CHAIN.lastIndex = start;
  for (let m = CHAIN.exec(masked); m; m = CHAIN.exec(masked)) {
    const before = masked.slice(0, m.index).trimEnd();
    if (PLACEHOLDER.some((mark) => before.endsWith(mark))) continue;
    const parts = m[0].split(/\s*\.\s*/).map(unquote);
    const column = parts[parts.length - 1] ?? "";
    if (parts.length > 1) {
      if (!names.has(parts.slice(0, -1).join(".").toLowerCase()) || column === "*") continue;
    } else if (!single || !bareColumn(m, masked, column, names)) {
      continue;
    }
    if (!seen.has(column.toLowerCase())) {
      seen.add(column.toLowerCase());
      out.push(column);
    }
  }
  return out;
}

// A bare name that can only be a column: no keyword, call, alias, parameter, temp, source.
function bareColumn(match, masked, column, names) {
  const lower = column.toLowerCase();
  if (/^[@#]/.test(column) || names.has(lower)) return false;
  if (!/^[["]/.test(match[0]) && NOT_A_COLUMN.has(lower)) return false;
  if (masked.slice(match.index + match[0].length).trimStart().startsWith("(")) return false;
  return !/\bas$/i.test(masked.slice(0, match.index).trimEnd());
}

// Does the select list read the source with `*` — bare, or `t.*` naming it?
function stars(masked, names) {
  if (BARE_STAR.test(masked)) return true;
  DOTTED_STAR.lastIndex = 0;
  for (let m = DOTTED_STAR.exec(masked); m; m = DOTTED_STAR.exec(masked)) {
    const key = (m[1] ?? "").split(/\s*\.\s*/).map(unquote).join(".").toLowerCase();
    if (names.has(key)) return true;
  }
  return false;
}

module.exports = { readSqlLiteral, readSqlColumns };
