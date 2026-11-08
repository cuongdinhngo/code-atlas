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
// A span's opening verb is not its body: `CREATE`, `ALTER` and a split `CREATE OR\nALTER` agree.
const HEADER_VERB = /^(?:create|alter)(?: |(?![\p{L}\p{N}_@#$]))/u;

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
 * `CREATE` (across lines too), a space only between two words. Literal text is kept as written.
 */
class LineText {
  /**
   * @param {boolean} inLiteral
   * @param {{prev: string|null, held: boolean}} carry the word sequence a line break leaves open
   */
  constructor(inLiteral, carry) {
    this.out = inLiteral ? "\n" : "";
    this.space = false;
    this.word = "";
    this.carry = carry;
  }

  /** @param {string} ch a code character, already lower-cased */
  code(ch) {
    if (isWord(ch)) { this.word += ch; return; }
    this.breakWords();
    this.out += ch;
  }

  /** @param {string} ch a literal's character, kept as written */
  literal(ch) {
    // A gap after the last word, read before breakWords clears it (`N'x'` holds `n` unflushed).
    const spaced = this.space && this.word === "";
    this.breakWords();
    // `N 'x'` (a column and its alias) is not `N'x'` (one literal).
    if (spaced && isWord(this.out[this.out.length - 1])) this.out += " ";
    this.space = false;
    this.out += ch;
  }

  gap() {
    this.endWord();
    if (this.out !== "" || this.carry.held) this.space = true;
  }

  endWord() {
    const word = this.word;
    if (word === "") return;
    this.word = "";
    const { carry } = this;
    if (carry.held) {
      carry.held = false;
      if (OR_CLAUSE.has(word)) { carry.prev = word; return; }
      this.put("or");
    }
    if (word === "or" && carry.prev === "create") { carry.held = true; carry.prev = word; return; }
    this.put(word);
    carry.prev = word;
  }

  breakWords() {
    this.endWord();
    if (this.carry.held) { this.carry.held = false; this.put("or"); }
    this.carry.prev = null;
    this.space = false;
  }

  /** @param {string} word */
  put(word) {
    if (this.space && isWord(this.out[this.out.length - 1])) this.out += " ";
    this.space = false;
    this.out += word;
  }
}

/** @typedef {{hash: number[], power: number[], length: number, head: boolean, opens: boolean, tail: boolean}} Poly */

/**
 * Three composable polynomial hashes of `text`, and whether it opens and closes on a word.
 * @param {string} text
 * @returns {Poly}
 */
function polynomial(text) {
  const hash = [0, 0, 0];
  const power = [1, 1, 1];
  for (let i = 0; i < text.length; i += 1) {
    const c = text.charCodeAt(i);
    for (let k = 0; k < 3; k += 1) {
      hash[k] = (hash[k] * BASES[k] + c) % MODULI[k];
      power[k] = (power[k] * BASES[k]) % MODULI[k];
    }
  }
  return {
    hash,
    power,
    length: text.length,
    head: isWord(text[0]),
    // Opens on a literal: after a word it keeps its space, as `LineText.literal` does in a line.
    opens: text[0] in CLOSERS,
    tail: isWord(text[text.length - 1]),
  };
}

function lineFingerprints() {
  /** @type {number[]} */
  const lines = [];
  /** @type {Array<Poly & {lead: Poly|null}>} */
  const parts = [];
  let block = 0;
  /** @type {string|null} */
  let closer = null;
  // A held `or` still waiting for its `alter` at the end of the file is dropped: no body ends so.
  const carry = { prev: /** @type {string|null} */ (null), held: false };

  /**
   * One physical line, read with the comment and literal state that spans lines.
   * @param {number} lineNo
   * @param {string} text
   */
  const line = (lineNo, text) => {
    const norm = new LineText(closer !== null, carry);
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
          // Its own word: `FROM[dbo]` is `FROM dbo`.
          norm.gap();
          for (const c of name.toLowerCase()) norm.code(c);
          norm.gap();
          i = end;
          continue;
        }
      }
      if (ch in CLOSERS) { norm.literal(ch); closer = CLOSERS[ch]; continue; }
      norm.code(ch.toLowerCase());
    }
    if (closer !== null) norm.breakWords();
    else norm.endWord();
    const out = norm.out;
    if (out === "") return;
    lines.push(lineNo);
    const header = HEADER_VERB.exec(out);
    parts.push({ ...polynomial(out), lead: header ? polynomial(out.slice(header[0].length)) : null });
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
    const first = lowerBound(lines, start);
    for (let at = first; at < lines.length && lines[at] <= end; at += 1) {
      const part = at === first ? (parts[at].lead ?? parts[at]) : parts[at];
      const spaced = tail && (part.head || part.opens);
      for (let k = 0; k < 3; k += 1) {
        if (spaced) hash[k] = (hash[k] * BASES[k] + SPACE) % MODULI[k];
        hash[k] = (hash[k] * part.power[k] + part.hash[k]) % MODULI[k];
      }
      length += part.length + (spaced ? 1 : 0);
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
