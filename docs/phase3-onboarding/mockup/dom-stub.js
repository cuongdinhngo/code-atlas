// Minimal DOM stub: runs the dashboard script headlessly so real data can be exercised.
const fs = require('fs');
const DATA = fs.readFileSync(process.argv[2], 'utf8');
let created = 0;
function mk(tag) {
  const e = {
    tagName: tag, className: '', _html: '', textContent: '', title: '',
    style: { cssText: '', setProperty() {} }, dataset: { theme: 'dark' },
    children: [], clientWidth: 1000, clientHeight: 440, value: '',
    classList: { _s: new Set(), toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
                 add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
                 contains(c) { return this._s.has(c); } },
    append(...k) { k.forEach(c => this.children.push(c)); return this.children[this.children.length - 1]; },
    appendChild(c) { this.children.push(c); },
    focus() {}, select() {},
    getAttribute() { return '#overview'; },
    querySelectorAll() { return []; },
    set innerHTML(v) { this._html = v; }, get innerHTML() { return this._html; },
    get lastChild() { return this.children[this.children.length - 1]; },
  };
  return e;
}
const byId = {};
global.document = {
  getElementById(id) { if (id === 'data') return { textContent: DATA }; return byId[id] || (byId[id] = mk('div')); },
  createElement(t) { created++; return mk(t); },
  createTextNode(t) { return { text: t }; },
  querySelectorAll() { return []; },
  documentElement: { dataset: { theme: 'dark' } },
};
global.addEventListener = () => {};
global.IntersectionObserver = function () { return { observe() {} }; };
