# OpenCode plugin — poke the index after an edit (tasks 036, 200)

After OpenCode edits or writes a file, reparse that one file into `.code-atlas/graph.db` with the
**`code-atlas-poke`** console script — the same entrypoint the Claude Code snippet uses.

## Install by hand

code-atlas does not write to your agent's settings. You do.

1. Install code-atlas into the environment OpenCode runs in, so **`code-atlas-poke`** is on `PATH`
   (see the [README](../../README.md)).
2. Copy [`code-atlas.js`](code-atlas.js) into **`.opencode/plugins/code-atlas.js`** in your project,
   or into `~/.config/opencode/plugins/` for every project.
3. Restart OpenCode.

## Unverified against a running OpenCode

Written from the published plugin documentation (<https://opencode.ai/docs/plugins/>), **not**
observed on a running OpenCode. The docs show the named-export plugin shape and the
`tool.execute.before` signature; `tool.execute.after` is listed as an event but its argument shape is
not spelled out there, so the handler above reads `input.tool` defensively and ignores everything
else. code-atlas installs nothing, so no test here can exercise it.

## Behaviour

`code-atlas-poke` exits 0 in every case — no index, a path outside the project, a suffix no adapter
owns, or a broken install (one stderr line). It never fails your edit.
