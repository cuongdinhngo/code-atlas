// R6.2 case `re-export-barrel`: `export … from`. Answers 128 Q2's load-bearing half — a re-export
// aliases to the *defining* module (widgets.ts::Button, ::Modal), so a downstream import resolves
// through the barrel to where the symbol is actually declared. `export *` cannot enumerate names
// file-at-a-time, so it emits only the module dependency.
export { Button } from "./widgets";
export { Modal as Dialog } from "./widgets";
export * from "./more_widgets";
