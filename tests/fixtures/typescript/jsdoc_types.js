// R6.2 case `jsdoc-types`: a .js file carries its types in JSDoc, not TS syntax (task 154). A
// `@typedef` is an Interface; `@param`/`@returns` feed extra.type and 153's receiver resolution.
/** @typedef {Object} Point */

class Service {
  handle() {}
}

/**
 * @param {Service} svc
 * @returns {Service}
 */
function run(svc) {
  svc.handle();
  return svc;
}
