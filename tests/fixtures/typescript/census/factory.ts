// Task 301 census fixture: same-file explicit return used as a member-call receiver.
export class Client {
  send(): void {}
}

export function makeClient(): Client {
  return new Client();
}

export function run(): void {
  makeClient().send();
  const c = makeClient();
  c.send();
}
