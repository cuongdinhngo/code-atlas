# Codex session hook — poke the index, and the read-time signal (tasks 036, 099, 200)

Two commands the Claude Code snippet already uses, offered to Codex:

- **`code-atlas-poke`** — after the agent edits a file, reparse that one file into
  `.code-atlas/graph.db`, so the index is often already fresh before the next tool call (036).
- **`code-atlas-signal`** — one line about the index riding along with a file the agent is already
  reading. No tool call, no payload: the field found three decisions that wanted exactly that and
  none that wanted a round-trip (099).

## Install by hand

code-atlas does not write to your agent's settings — not here, not anywhere (036, 099).

1. Install code-atlas into the environment Codex runs in, so **`code-atlas-poke`** and
   **`code-atlas-signal`** are on `PATH` (see the [README](../../README.md)).
2. Merge [`hooks.json`](hooks.json) into **`~/.codex/hooks.json`**. Entries are additive: every
   matching hook from every file runs, in declaration order.
3. Enable the feature in **`~/.codex/config.toml`**:

   ```toml
   [features]
   hooks = true
   ```

   `codex_hooks = true` is the deprecated alias for the same key.
4. Restart Codex.

**No `matcher` is set on purpose.** Codex's tool names are not the ones the Claude Code snippet
filters on, and both commands already decide for themselves: each reads the tool payload from stdin
and exits 0 with no output when there is no path it owns. Add a `matcher` if you would rather they
were not invoked at all.

## Unverified against a running Codex

Written from the published hooks reference (<https://developers.openai.com/codex/hooks>), **not**
observed on a running Codex — no host with Codex installed was available, and code-atlas installs
nothing, so no test here can exercise it. Third-party write-ups disagree about whether the event
names sit inside the `"hooks"` wrapper; the wrapper above is what the reference shows. If your Codex
rejects the file, the reference wins over this snippet.

## Behaviour

Both commands always exit 0 and never block the session: no index means no output, a path they do
not own is a no-op, and an install or config error is one line on stderr.
