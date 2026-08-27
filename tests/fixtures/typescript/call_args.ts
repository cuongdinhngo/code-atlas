// Task 152 fixture: every args category + the TS-specific arg_keys shapes (spread, template,
// shorthand, computed key). Not an R6.2 construct case — args is edge metadata, pinned by
// tests/test_ts_call_args.py. The parse is syntactic, so the free names need no declarations.
export function run(): void {
  literals("s", 42, true, false, null, x);
  keyed({ a: 1, b: 2, ...rest, [k]: 3, short });
  positional([1, 2, 3]);
  templated(`hi ${x}`);
  spread(...[1, 2]);
  new Thing({ id: 1 }, "z");
}
