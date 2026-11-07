"use strict";

// Per-symbol body fingerprint (384, normalised by 437). The scanner streams, so each line's code is
// kept as a composable hash, never as text: a span hashes as one stream, whichever lines hold it.
// Opaque: compared for equality only.

const crypto = require("node:crypto");

const BODY_HASH = "body_hash";
const HASH_CHARS = 16;
// A File spans unrelated objects; a fingerprint of one is no object's body.
const UNHASHED = new Set(["File", "Namespace"]);
// A literal or delimited identifier keeps its text as written; `--` or `/*` inside one is data.
const CLOSERS = /** @type {Record<string, string>} */ ({ "'": "'", '"': '"', "[": "]" });
// Three polynomial hashes; each modulus and base is below 2^26, so every product stays exact.
const MODULI = [67108859, 67108837, 67108819];
const BASES = [4194319, 5767201, 6291469];
const SPACE = 32;
const WORD_CHAR = /[\p{L}\p{N}_@#$]/u;
// A delimited name that needs no delimiters: `[Orders]` and `Orders` are one identifier.
const REGULAR_IDENTIFIER = /^[\p{L}_@#][\p{L}\p{N}_@#$]*$/u;
// `CREATE OR ALTER` and `CREATE` define the same object.
const OR_CLAUSE = new Set(["alter", "replace"]);

/** @param {string} text */
const digest = (text) =>
  crypto.createHash("sha256").update(text, "utf8").digest("hex").slice(0, HASH_CHARS);

/** @param {string|undefined} ch */
const isWord = (ch) => ch !== undefined && WORD_CHAR.test(ch);

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
 * The closing delimiter of a `[name]` / `"name"` opened at `at`, on this line; -1 when it is not.
 * @param {string} text
 * @param {number} at
 */
function closeOf(text, at) {
  const closer = CLOSERS[text[at]];
  for (let i = at + 1; i < text.length; i += 1) {
    if (text[i] !== closer) continue;
    if (text[i + 1] === closer) { i += 1; continue; }
    return i;
  }
  return -1;
}

/**
 * The line's normalised code: lower-cased, regular names unquoted, `OR ALTER` dropped after
 * `CREATE`, and a space only between two word characters. Literal text is kept as written.
 */
class LineText {
  /** @param {boolean} inLiteral */
  constructor(inLiteral) {
    this.out = inLiteral ? "\n" : "";
    this.space = false;
    /** @type {Array<{text: string, cut: number}>} */
    this.words = [];
    /** @type {{start: number, cut: number}|null} */
    this.word = null;
  }

  /** @param {string} ch a code character, already lower-cased */
  code(ch) {
    if (!isWord(ch)) {
      this.endWord(false);
      this.out += ch;
      this.space = false;
      return;
    }
    if (this.word === null) {
      const cut = this.out.length;
      if (this.space && isWord(this.out[this.out.length - 1])) this.out += " ";
      this.word = { start: this.out.length, cut };
    }
    this.space = false;
    this.out += ch;
  }

  /** @param {string} ch a literal's character, kept as written */
  literal(ch) {
    this.endWord(false);
    this.out += ch;
    this.space = false;
  }

  gap() {
    this.endWord(true);
    this.space = true;
  }

  /** @param {boolean} keep whether the word sequence continues past this boundary */
  endWord(keep) {
    if (this.word !== null) {
      this.words.push({ text: this.out.slice(this.word.start), cut: this.word.cut });
      this.word = null;
      const [first, second, third] = this.words.slice(-3);
      if (third && first.text === "create" && second.text === "or" && OR_CLAUSE.has(third.text)) {
        this.out = this.out.slice(0, second.cut);
        this.words = [first];
      }
      if (this.words.length > 3) this.words.shift();
    }
    if (!keep) this.words = [];
  }
}

function lineFingerprints() {
  /** @type {number[]} */
  const lines = [];
  /** @type {Array<{hash: number[], power: number[], length: number, head: boolean, tail: boolean}>} */
  const parts = [];
  let block = 0;
  /** @type {string|null} */
  let closer = null;

  /**
   * One physical line, read with the comment and literal state that spans lines.
   * @param {number} lineNo
   * @param {string} text
   */
  const line = (lineNo, text) => {
    const norm = new LineText(closer !== null);
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const next = text[i + 1];
      if (closer !== null) {
        norm.literal(ch);
        // A doubled closer is the escaped character, not the end (`''`, `]]`, `""`).
        if (ch === closer && next === closer) { norm.literal(next); i += 1; }
        else if (ch === closer) closer = null;
        continue;
      }
      if (block > 0) {
        if (ch === "*" && next === "/") { block -= 1; i += 1; }
        else if (ch === "/" && next === "*") { block += 1; i += 1; }
        continue;
      }
      if (ch === "-" && next === "-") break;
      if (ch === "/" && next === "*") { block += 1; i += 1; norm.gap(); continue; }
      if (ch === " " || ch === "\t") { norm.gap(); continue; }
      if (ch === "[" || ch === '"') {
        const end = closeOf(text, i);
        const name = end > i ? text.slice(i + 1, end) : "";
        if (REGULAR_IDENTIFIER.test(name)) {
          for (const c of name.toLowerCase()) norm.code(c);
          i = end;
          continue;
        }
      }
      if (ch in CLOSERS) { norm.literal(ch); closer = CLOSERS[ch]; continue; }
      norm.code(ch.toLowerCase());
    }
    norm.endWord(false);
    const out = norm.out;
    if (out === "") return;
    const hash = [0, 0, 0];
    const power = [1, 1, 1];
    for (let i = 0; i < out.length; i += 1) {
      const c = out.charCodeAt(i);
      for (let k = 0; k < 3; k += 1) {
        hash[k] = (hash[k] * BASES[k] + c) % MODULI[k];
        power[k] = (power[k] * BASES[k]) % MODULI[k];
      }
    }
    lines.push(lineNo);
    parts.push({
      hash, power, length: out.length, head: isWord(out[0]), tail: isWord(out[out.length - 1]),
    });
  };

  /**
   * The hash of a span's lines as one stream: a line break between two words is one space.
   * @param {number} start
   * @param {number} end
   */
  const spanDigest = (start, end) => {
    const hash = [0, 0, 0];
    let length = 0;
    let tail = false;
    for (let at = lowerBound(lines, start); at < lines.length && lines[at] <= end; at += 1) {
      const part = parts[at];
      for (let k = 0; k < 3; k += 1) {
        if (tail && part.head) hash[k] = (hash[k] * BASES[k] + SPACE) % MODULI[k];
        hash[k] = (hash[k] * part.power[k] + part.hash[k]) % MODULI[k];
      }
      length += part.length + (tail && part.head ? 1 : 0);
      tail = part.tail;
    }
    return digest(`${hash.join(".")}.${length}`);
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
      node.extra = { ...(node.extra || {}), [BODY_HASH]: spanDigest(start, end) };
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
