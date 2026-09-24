#!/usr/bin/env node
"use strict";

// Announces the adapter once, then answers one request per line until stdin closes (§4.1) — the same
// handshake-then-serve shape as adapters/php/index.php and adapters/typescript/index.js.

const readline = require("node:readline");
const { parseFile } = require("./src/scan");

const META = {
  name: "sql",
  extensions: [".sql"],
  // No `semantic_types`: tier 1a reads DDL headers and EXEC sites only, and infers no receiver type.
  capabilities: {
    params: true,
    args: true,
    // T-SQL spells no visibility, static or readonly keyword on any object this adapter emits,
    // so there is no modifier to capture — claiming capture would be a claim about the language.
    modifiers: false,
    declared_types: true,
  },
  contract_version: 11,
};

// One `\n`-framed JSON line straight to stdout so a lock-step reader never blocks (§4.1).
/** @param {object} result */
function emit(result) {
  process.stdout.write(JSON.stringify(result) + "\n");
}

function serve() {
  emit(META);
  const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  rl.on("line", (line) => {
    const trimmed = line.trim();
    if (trimmed === "") {
      return;
    }
    let request;
    try {
      request = JSON.parse(trimmed);
    } catch {
      // Never answer an uncorrelatable line: a made-up path would misattribute every reply.
      process.stderr.write("code-atlas sql adapter: skipped an unusable request line\n");
      return;
    }
    const path = request && typeof request.path === "string" ? request.path : null;
    if (path === null) {
      process.stderr.write("code-atlas sql adapter: skipped an unusable request line\n");
      return;
    }
    emit(parseFile(path));
  });
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 1 && args[0] === "--server") {
    serve();
    return;
  }
  if (args.length === 2 && args[0] === "--file") {
    emit(parseFile(args[1]));
    return;
  }
  process.stderr.write("usage: node index.js --file <path> | --server\n");
  process.exit(2);
}

main();
