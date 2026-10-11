"use strict";

// Per-symbol body fingerprint (task 384). The scanner streams, so each line's code — comments
// dropped, whitespace outside literals collapsed — is kept as a short digest, never as text, and a
// symbol's fingerprint covers the digests on its lines. Opaque: compared for equality only.

const crypto = require("node:crypto");

const BODY_HASH = "body_hash";
const HASH_CHARS = 16;
// A File spans unrelated objects; a fingerprint of one is no object's body.
const UNHASHED = new Set(["File", "Namespace"]);
// A literal or delimited identifier keeps its text as written; `--` or `/*` inside one is data.
const CLOSERS = /** @type {Record<string, string>} */ ({ "'": "'", '"': '"', "[": "]" });

/** @param {string} text */
const digest = (text) =>
  crypto.createHash("sha256").update(text, "utf8").digest("hex").slice(0, HASH_CHARS);

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

function lineFingerprints() {
  /** @type {number[]} */
  const lines = [];
  /** @type {string[]} */
  const digests = [];
  let block = 0;
  /** @type {string|null} */
  let closer = null;

  /**
   * One physical line, read with the comment and literal state that spans lines.
   * @param {number} lineNo
   * @param {string} text
   */
  const line = (lineNo, text) => {
    let out = closer !== null ? "\n" : "";
    let space = false;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const next = text[i + 1];
      if (closer !== null) {
        out += ch;
        // A doubled closer is the escaped character, not the end (`''`, `]]`, `""`).
        if (ch === closer && next === closer) { out += next; i += 1; }
        else if (ch === closer) closer = null;
        continue;
      }
      if (block > 0) {
        if (ch === "*" && next === "/") { block -= 1; i += 1; }
        else if (ch === "/" && next === "*") { block += 1; i += 1; }
        continue;
      }
      if (ch === "-" && next === "-") break;
      if (ch === "/" && next === "*") { block += 1; i += 1; space = true; continue; }
      if (ch === " " || ch === "\t") { space = true; continue; }
      if (space && out !== "") out += " ";
      space = false;
      out += ch;
      if (ch in CLOSERS) closer = CLOSERS[ch];
    }
    if (out.trim() === "") return;
    lines.push(lineNo);
    digests.push(digest(out));
  };

  /**
   * Add `extra.body_hash` to every object node, over the code lines it spans.
   * @param {Array<Record<string, any>>} nodes
   */
  const stamp = (nodes) => {
    const spans = qnameSpans(nodes);
    for (const node of nodes) {
      if (UNHASHED.has(node.kind) || typeof node.line_start !== "number") continue;
      const [start, end] = /** @type {[number, number]} */ (spans.get(node.qualified_name));
      const span = [];
      for (let at = lowerBound(lines, start); at < lines.length && lines[at] <= end; at += 1) {
        span.push(digests[at]);
      }
      node.extra = { ...(node.extra || {}), [BODY_HASH]: digest(span.join("\0")) };
    }
  };

  return { line, stamp };
}

/**
 * @param {number[]} lines ascending
 * @param {number} target
 */
function lowerBound(lines, target) {
  let low = 0;
  let high = lines.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    if (lines[mid] < target) low = mid + 1;
    else high = mid;
  }
  return low;
}

module.exports = { lineFingerprints, BODY_HASH };
