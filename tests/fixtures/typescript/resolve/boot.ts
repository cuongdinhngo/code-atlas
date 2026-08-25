// Integration fixture: a default-import; `new Service()` must resolve through `service.ts::default`
// to the class that actually declares it.
import Service from "./service";

export function boot(): Service {
  return new Service();
}
