"use strict";

// Per-symbol body fingerprint (task 384): the tokens on a symbol's lines, comments and layout
// dropped, so the core can tell a body edit from a comment edit. Opaque — compared for equality.

const crypto = require("node:crypto");
const ts = require("typescript");

const BODY_HASH = "body_hash";
const HASH_CHARS = 16;
// A File or Namespace spans unrelated symbols; a fingerprint of one is no symbol's body.
const UNHASHED = new Set(["File", "Namespace"]);

/**
 * The source's tokens in order, with the 1-based line each starts on. Trivia (whitespace,
 * comments) never becomes a token, and a JSDoc block is skipped whole.
 * @param {ts.SourceFile} sf
 * @returns {{lines: number[], pieces: string[]}}
 */
function tokensOf(sf) {
  /** @type {number[]} */
  const lines = [];
  /** @type {string[]} */
  const pieces = [];
  /** @param {ts.Node} node */
  const visit = (node) => {
    if (node.kind >= ts.SyntaxKind.FirstJSDocNode && node.kind <= ts.SyntaxKind.LastJSDocNode) return;
    const children = node.getChildren(sf);
    if (children.length === 0) {
      if (node.kind === ts.SyntaxKind.EndOfFileToken) return;
      lines.push(sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1);
      pieces.push(node.getText(sf));
      return;
    }
    children.forEach(visit);
  };
  visit(sf);
  return { lines, pieces };
}

/**
 * One span per qname: a name declared twice in a file (an overload, a redefinition) is stored once,
 * keep-first, so its fingerprint covers every declaration — an edit to a later one is still seen.
 * @param {Array<Record<string, any>>} nodes
 * @returns {Map<string, [number, number]>}
 */
function qnameSpans(nodes) {
  /** @type {Map<string, [number, number]>} */
  const spans = new Map();
  for (const node of nodes) {
    const start = node.line_start;
    if (typeof start !== "number") continue;
    const end = typeof node.line_end === "number" ? node.line_end : start;
    const [low, high] = spans.get(node.qualified_name) ?? [start, end];
    spans.set(node.qualified_name, [Math.min(low, start), Math.max(high, end)]);
  }
  return spans;
}

/**
 * Add `extra.body_hash` to every symbol node, over the tokens on its lines.
 * @param {ts.SourceFile} sf
 * @param {Array<Record<string, any>>} nodes
 */
function stamp(sf, nodes) {
  const { lines, pieces } = tokensOf(sf);
  const spans = qnameSpans(nodes);
  for (const node of nodes) {
    if (UNHASHED.has(node.kind) || typeof node.line_start !== "number") continue;
    const [start, end] = /** @type {[number, number]} */ (spans.get(node.qualified_name));
    let at = lowerBound(lines, start);
    /** @type {string[]} */
    const span = [];
    for (; at < lines.length && lines[at] <= end; at += 1) span.push(pieces[at]);
    const digest = crypto.createHash("sha256").update(span.join("\0"), "utf8").digest("hex");
    node.extra = { ...(node.extra || {}), [BODY_HASH]: digest.slice(0, HASH_CHARS) };
  }
}

/**
 * @param {number[]} lines ascending
 * @param {number} line
 */
function lowerBound(lines, line) {
  let low = 0;
  let high = lines.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (lines[mid] < line) low = mid + 1;
    else high = mid;
  }
  return low;
}

module.exports = { stamp, BODY_HASH };
