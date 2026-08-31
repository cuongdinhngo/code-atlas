// Headless harness for the onboarding system map (task 116).
//
//   node tests/viewer_dom_stub.js <index.html> [--search <query>] [--path <path>]
//
// AC4/AC5/AC6 have no static formulation: the page builds its content in the browser, so a scan of
// the HTML sees zero rendered figures. This provides a minimal DOM, runs the page's own inline
// script against it, drives the CA_MAP namespace, and prints ONE JSON report on stdout. Every
// assertion lives in the Python test — this file only reports what happened.
'use strict';

const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const queries = [];
const probes = [];
for (let i = 3; i < process.argv.length; i += 2) {
  (process.argv[i] === '--path' ? probes : queries).push(process.argv[i + 1]);
}

// The page sets content with innerHTML throughout, so an element only has to remember its markup.
function element(id) {
  return {
    id: id,
    innerHTML: '',
    value: '',
    className: '',
    dataset: {},
    style: { cssText: '' },
    clientWidth: 1000,
    clientHeight: 440,
    set onclick(fn) { this._click = fn; },
    get onclick() { return this._click; },
    set oninput(fn) { this._input = fn; },
    get oninput() { return this._input; },
    addEventListener() {},
  };
}
const nodes = {};
global.document = {
  getElementById(id) {
    if (id === 'dataset') return { textContent: payload };
    return nodes[id] || (nodes[id] = element(id));
  },
  documentElement: { dataset: { theme: 'auto' } },
};
global.addEventListener = () => {};

// The payload is the JSON script block; the page script is the last <script> block.
const payload = html.match(
  /<script type="application\/json" id="dataset">([\s\S]*?)<\/script>/
)[1];
const scripts = html.match(/<script>([\s\S]*?)<\/script>/g) || [];
const source = scripts[scripts.length - 1].replace(/^<script>/, '').replace(/<\/script>$/, '');

// eslint-disable-next-line no-eval
eval(source);

const MAP = globalThis.CA_MAP;
const strip = (s) => String(s).replace(/<[^>]*>/g, ' ').replace(/&[a-z]+;|&#\d+;/g, ' ');
// A figure is a digit run standing on its own in the visible text — thousands separators kept.
// The boundaries matter: without them, the digits inside a file name would count as a figure and
// every path on the page would look like a number the renderer had produced.
const figures = (s) =>
  (strip(s).match(/(?<![\w.])\d[\d,]*(?![\w])/g) || []).map((x) => x.replace(/[.,]$/, ''));

const sections = {};
for (const id of MAP.sections) {
  // A section's rendered text is every container the page filled inside it. The page writes into
  // ids, so collect every id that reported content and attribute it to its section by name.
  sections[id] = { text: '', figures: [] };
}
const SECTION_OF = {
  overview: ['lede', 'heads', 'stats', 'stampLine', 'stamp', 'confBy'],
  modules: ['modTable', 'modNote'],
  sitemap: ['tm', 'crumb', 'tmLegend'],
  layers: ['layerTable', 'lyrLegend'],
  deps: ['mxLede', 'mx', 'mxNote'],
  hubs: ['hubLede', 'hubTable'],
  flows: ['flowLede', 'flowTable', 'flowNote'],
  mirrors: ['mirLede', 'mirTable', 'mirNote'],
  reach: ['reachLede', 'reachGrid', 'reachNote'],
  classes: ['clsLede', 'clsTable'],
  prov: ['provCard'],
};
for (const [id, ids] of Object.entries(SECTION_OF)) {
  const markup = ids.map((k) => (nodes[k] ? nodes[k].innerHTML : '')).join('\n');
  sections[id] = { text: strip(markup).replace(/\s+/g, ' ').trim(), figures: figures(markup) };
}

// AC5: the legend and the matrix must each cover every layer in the dataset.
const legendMarkup = nodes.tmLegend ? nodes.tmLegend.innerHTML : '';
const legend = MAP.layers.filter((name) => legendMarkup.indexOf(name) >= 0);
const matrixMarkup = nodes.mx ? nodes.mx.innerHTML : '';
const matrix = {
  rows: (matrixMarkup.match(/<th class="rh">[^<]/g) || []).length,
  cols: (matrixMarkup.match(/<th class="ch">/g) || []).length,
  cells: (matrixMarkup.match(/<td class="c"/g) || []).length,
};

// AC6: search and counterpart, driven directly, negatives included.
const search = {};
for (const q of queries) {
  const found = MAP.search(q);
  // Drive the page's own draw() as well, so the reported hint is the rendered one (126).
  MAP.open(q);
  search[q] = {
    shown: found.shown,
    paths: found.paths,
    cut: found.cut,
    incomplete: found.incomplete,
    short: !!found.short,
    first: found.items.length ? found.items[0].text : null,
    kinds: found.items.slice(0, 6).map((i) => i.kind),
    items: found.items.map((i) => i.text),
    hint: strip(nodes.rhint ? nodes.rhint.innerHTML : '').replace(/\s+/g, ' ').trim(),
  };
}
const counterpart = {};
for (const p of probes.concat(['definitely/not/indexed.xyz'])) {
  counterpart[p] = MAP.counterpart(p);
}

// The flat tree must be closed under parents, or the treemap silently drops a subtree.
const known = new Set(MAP.data.tree.map((r) => r.path));
let closed = true;
for (const row of MAP.data.tree) {
  const segs = row.path.split('/');
  for (let i = 1; i < segs.length; i++) {
    if (!known.has(segs.slice(0, i).join('/'))) closed = false;
  }
}

process.stdout.write(JSON.stringify({
  sections: sections,
  legend: legend,
  layers: MAP.layers,
  matrix: matrix,
  search: search,
  counterpart: counterpart,
  paths: MAP.paths.length,
  tree: { rows: MAP.data.tree.length, closed_under_parents: closed },
  version: MAP.data.version,
  commit: MAP.data.commit,
}, null, 1));
