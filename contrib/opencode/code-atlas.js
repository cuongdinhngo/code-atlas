// OpenCode plugin — poke the code-atlas index after an edit (tasks 036, 200, 427).
// Offered, never installed: copy this into your own .opencode/plugins/ by hand.
import { existsSync } from "node:fs";
import { join } from "node:path";

export const CodeAtlas = async ({ $, directory }) => ({
  "tool.execute.after": async (input) => {
    if (input?.tool !== "edit" && input?.tool !== "write") return;
    // Wake only on the index database; code-atlas-poke refuses one git tracks.
    if (!existsSync(join(directory ?? ".", ".code-atlas", "graph.db"))) return;
    await $`code-atlas-poke`.quiet().nothrow();
  },
});
