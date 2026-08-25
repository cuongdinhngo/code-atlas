// R6.2 case `syntax-error`: a malformed source file. Answers R5.1 — the adapter returns
// {ok:false, error} with no nodes/edges, mirroring the PHP adapter, so one bad file never breaks the stream.
export class Broken {
  method(: void {
}
