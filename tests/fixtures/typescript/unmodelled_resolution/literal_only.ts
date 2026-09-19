export async function load(): Promise<unknown> {
  return await import("./sibling");
}
