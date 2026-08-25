"use strict";

// Qname construction for the TS/JS adapter: module-path-anchored, `::`-joined (contract §3, PLAN
// §4.4 Q1). The root container is the repo-relative posix file path; every member appends `::name`.

const SEP = "::";

function toPosix(p) {
  return p.replace(/\\/g, "/");
}

function member(container, name) {
  return container + SEP + name;
}

module.exports = { SEP, toPosix, member };
