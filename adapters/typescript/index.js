#!/usr/bin/env node
"use strict";

// M0 spike entry point. Announces the adapter once, then answers one request per line until stdin
// closes (§4.1) — the same handshake-then-serve shape as adapters/php/index.php.

const readline = require("node:readline");
const { parseFile } = require("./src/parse");

const META = {
  name: "typescript",
  extensions: [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"],
  // A local type table (src/types.js) infers a receiver's class from `new`, annotations and
  // assignments, so a member call resolves to `<Class>::method` — the one capability (task 153).
  capabilities: {
    semantic_types: true,
    params: true,
    args: true,
    modifiers: true,
    declared_types: true,
    inheritance: true,
  },
  contract_version: 11,
};

// One `\n`-framed JSON line straight to stdout so a lock-step reader never blocks (§4.1).
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
      process.stderr.write("code-atlas typescript adapter: skipped an unusable request line\n");
      return;
    }
    const path = request && typeof request.path === "string" ? request.path : null;
    if (path === null) {
      process.stderr.write("code-atlas typescript adapter: skipped an unusable request line\n");
      return;
    }
    emit(parseFile(path, request.declarations_only === true));
  });
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 1 && args[0] === "--server") {
    serve();
    return;
  }
  if (args.length === 2 && args[0] === "--file") {
    emit(parseFile(args[1], false));
    return;
  }
  process.stderr.write("usage: node index.js --file <path> | --server\n");
  process.exit(2);
}

main();
