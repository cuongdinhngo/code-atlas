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

module.exports = { readSqlLiteral };
