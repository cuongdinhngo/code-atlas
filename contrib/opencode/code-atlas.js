// OpenCode plugin — poke the code-atlas index after an edit (tasks 036, 200).
// Offered, never installed: copy this into your own .opencode/plugins/ by hand.
export const CodeAtlas = async ({ $ }) => ({
  "tool.execute.after": async (input) => {
    if (input?.tool !== "edit" && input?.tool !== "write") return;
    // code-atlas-poke reads the edited path from stdin and always exits 0.
    await $`code-atlas-poke`.quiet().nothrow();
  },
});
