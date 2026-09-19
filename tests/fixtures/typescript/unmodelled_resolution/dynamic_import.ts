export async function load(name: string): Promise<unknown> {
  return await import(name);
}
