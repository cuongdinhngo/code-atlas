"use strict";

// A T-SQL write or EXEC at the start of a string literal (task 371; the PHP adapter's 335 shape).
// Statement grammar only — never a driver's method name (R2.2), never a SQL parse: a leading keyword,
// one object name, and the clause T-SQL requires after it, so "Update settings" reads as nothing.
// tests/contract/sql_literal_cases.json keeps this copy, the PHP original and the Python port in step.

const KINDS = { insert: "WRITES", update: "WRITES", merge: "WRITES", delete: "DELETES", exec: "CALLS" };

const HEAD = /^(\s*)(insert\s+into|update|merge\s+into|delete\s+from|exec(?:ute)?)\s+/i;
const NAME_PART = String.raw`(?:\[(?:[^\]]|\]\])+\]|"(?:[^"]|"")+"|[A-Za-z_][\w@#$]*)`;
const NAME = new RegExp(String.raw`${NAME_PART}(?:\s*\.\s*${NAME_PART})*`, "y");
const PART = new RegExp(NAME_PART, "g");
const RETURN_CODE = /@[A-Za-z_]\w*\s*=\s*/y;
const END = /^\s*(?:;|$)/;
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
  return { kind: KINDS[verb], target: parts.join("."), offset: head[1].length };
}

// The clause T-SQL requires after the name; for DELETE / EXEC on a qualified name, its end.
function follows(verb, rest, qualified, closed) {
  if (CLAUSES[verb].test(rest)) {
    // A bare EXEC name would bind to a same-language function by name (204): qualified only.
    return verb !== "exec" || qualified;
  }
  if (!qualified || (verb !== "delete" && verb !== "exec")) return false;
  return rest === "" ? closed : END.test(rest);
}

function unquote(part) {
  if (part.startsWith("[")) return part.slice(1, -1).replace(/\]\]/g, "]");
  if (part.startsWith('"')) return part.slice(1, -1).replace(/""/g, '"');
  return part;
}

module.exports = { readSqlLiteral };
