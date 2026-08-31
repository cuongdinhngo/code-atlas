"""The onboarding system map — one self-contained offline HTML page (task 116, M11).

089 embedded a rendered markdown body for every module and answered the wrong question: it was a
paginated data dump, not a map, and a reader could not see from it where the system's classes and
modules sit. This renders the **112 aggregate dataset** instead, as a sitemap treemap, a layer table
with its node-kind composition, the full layer x layer matrix, hubs, the 114 capability table, the
113 zero-inbound split, the 115 mirror panel, and a search palette with counterpart lookup.

The dataset **is** the payload: ``dataset.as_dict()`` is embedded verbatim, so there is one shape,
declared once, and identical input yields byte-identical output (R4.2/AC3). One file, no server, no
external stylesheet, script, font or image; ``connect-src 'none'`` so a fetch cannot be added later.

Every displayed figure is interpolated from that blob — no literal number lives in the template
(AC4), which is also why an empty matrix cell renders blank and there are no numbered section
badges. Presentation only: no SQL, no LLM, no language branch (R1.1/R1.4/R4). Nothing here names a
repository, directory, framework or language; the prototype this replaces named nine of them (R2.2).
"""

from __future__ import annotations

import json

from code_atlas.onboarding.dataset import OnboardingDataset

_PLACEHOLDER = "__ONBOARDING_DATASET__"

# The page's own query surface, assigned to a global so the committed headless harness can drive it.
# A page that cannot be driven cannot be tested, and AC4/AC5/AC6 have no static formulation: the
# content is built in the browser, so a scan of this file sees zero rendered figures.
NAMESPACE = "CA_MAP"

SECTION_IDS: tuple[str, ...] = (
    "overview",
    "modules",
    "sitemap",
    "layers",
    "deps",
    "hubs",
    "flows",
    "mirrors",
    "reach",
    "classes",
    "prov",
)

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';
style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'none';
connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>System map</title>
<style>
:root {
  color-scheme: light dark;
  --bg:#f6f8fa; --panel:#fff; --panel2:#eef1f5; --line:#d8dee4; --line2:#c2cad2;
  --tx:#1f2328; --tx2:#57606a; --tx3:#8c959f; --ac:#0969da; --warn:#9a6700; --ok:#1a7f37;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#0d1117; --panel:#161b22; --panel2:#1c2230; --line:#2a3441; --line2:#3a4553;
    --tx:#e6edf3; --tx2:#9aa8b6; --tx3:#6e7d8d; --ac:#4dabf7; --warn:#d29922; --ok:#3fb950;
  }
}
:root[data-theme="dark"] {
  --bg:#0d1117; --panel:#161b22; --panel2:#1c2230; --line:#2a3441; --line2:#3a4553;
  --tx:#e6edf3; --tx2:#9aa8b6; --tx3:#6e7d8d; --ac:#4dabf7; --warn:#d29922; --ok:#3fb950;
}
* { box-sizing:border-box; }
html, body { margin:0; padding:0; }
body { background:var(--bg); color:var(--tx); font:14px/1.55 var(--sans); }
a { color:var(--ac); text-decoration:none; cursor:pointer; }
.wrap { display:flex; min-height:100vh; }
nav {
  width:236px; flex:0 0 236px; border-right:1px solid var(--line); background:var(--panel);
  position:sticky; top:0; height:100vh; overflow-y:auto; padding:18px 0;
}
nav .brand { padding:0 20px 14px; border-bottom:1px solid var(--line); margin-bottom:10px; }
nav .brand b { display:block; font-size:15px; }
nav .brand span { font:11px/1.4 var(--mono); color:var(--tx3); word-break:break-all; }
nav a.item {
  display:flex; gap:9px; padding:7px 20px; color:var(--tx2); font-size:13px;
  border-left:2px solid transparent;
}
nav a.item:hover { background:var(--panel2); color:var(--tx); }
nav .grp {
  padding:13px 20px 4px; font:10px/1 var(--mono); text-transform:uppercase;
  letter-spacing:.12em; color:var(--tx3);
}
.navbtn {
  margin:6px 20px 0; padding:6px 10px; background:var(--panel2); border:1px solid var(--line);
  color:var(--tx2); border-radius:6px; font:11.5px var(--sans); cursor:pointer;
  width:calc(100% - 40px); text-align:left; display:flex; justify-content:space-between; gap:6px;
}
.navbtn:hover { color:var(--tx); border-color:var(--line2); }
.navbtn kbd {
  font:10px var(--mono); border:1px solid var(--line2); border-radius:3px; padding:1px 4px;
  color:var(--tx3);
}
main { flex:1; min-width:0; padding:30px 40px 80px; max-width:1260px; }
section { margin-bottom:50px; scroll-margin-top:18px; }
section:target h2 { color:var(--ac); }
h1 { font-size:26px; letter-spacing:-.5px; margin:0 0 6px; }
h2 { font-size:18px; margin:0 0 4px; }
.lede { color:var(--tx2); margin:0 0 18px; max-width:78ch; }
.sub { color:var(--tx3); font-size:12px; margin:8px 0 0; max-width:88ch; }
.grid { display:grid; gap:12px; }
.g4 { grid-template-columns:repeat(auto-fit, minmax(158px, 1fr)); }
.card {
  background:var(--panel); border:1px solid var(--line); border-radius:9px; padding:14px 16px;
}
.stat .v { font:23px/1.1 var(--mono); color:var(--ac); }
.head { display:flex; gap:12px; align-items:baseline; }
.head b {
  flex:0 0 108px; font:10px/1.5 var(--mono); text-transform:uppercase; letter-spacing:.1em;
  color:var(--tx3);
}
.head span { color:var(--tx2); }
.stat .k {
  font-size:11px; color:var(--tx3); text-transform:uppercase; letter-spacing:.08em; margin-top:5px;
}
.stat .n { font-size:11px; color:var(--tx2); margin-top:6px; }
code {
  font:11.5px var(--mono); background:var(--panel2); padding:1px 5px; border-radius:3px;
  color:var(--tx); word-break:break-all;
}
.crumb { font:12px var(--mono); color:var(--tx2); margin-bottom:10px; display:block; }
.crumb b { color:var(--tx); }
#tm {
  position:relative; width:100%; height:440px; background:var(--panel);
  border:1px solid var(--line); border-radius:9px; overflow:hidden;
}
.cell { position:absolute; border:1px solid var(--bg); overflow:hidden; }
.cell.dig { cursor:pointer; }
.cell:hover { filter:brightness(1.22); z-index:3; }
.cell .nm {
  font:600 12px/1.2 var(--sans); color:#fff; text-shadow:0 1px 3px rgba(0,0,0,.7);
  padding:6px 8px 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.cell .mt {
  font:10px/1.3 var(--mono); color:rgba(255,255,255,.88);
  text-shadow:0 1px 3px rgba(0,0,0,.7); padding:0 8px;
}
.empty {
  display:flex; align-items:center; justify-content:center; height:100%; padding:0 8%;
  text-align:center; color:var(--tx2); font-size:13px;
}
.legend {
  display:flex; gap:14px; flex-wrap:wrap; font-size:11.5px; color:var(--tx2); margin:12px 0 0;
}
.legend span { display:flex; gap:6px; }
.dot {
  width:9px; height:9px; border-radius:2px; flex:0 0 9px; margin-top:5px; display:inline-block;
}
.lyr {
  display:grid; grid-template-columns:minmax(150px, 235px) 1fr auto; gap:14px; align-items:center;
  padding:9px 0; border-bottom:1px solid var(--line);
}
.lyr:last-child { border-bottom:0; }
.lyr .nm { font-size:13px; display:flex; gap:8px; }
.stack { display:flex; height:16px; border-radius:3px; overflow:hidden; background:var(--panel2); }
.stack i { display:block; height:100%; }
.lyr .qty { font:11.5px var(--mono); color:var(--tx2); white-space:nowrap; }
.desc { font-size:11.5px; color:var(--tx3); margin-top:2px; }
.mxwrap {
  overflow-x:auto; border:1px solid var(--line); border-radius:9px; background:var(--panel);
}
table.mx { border-collapse:collapse; font:11px var(--mono); min-width:max-content; }
table.mx th, table.mx td { padding:0; text-align:center; }
table.mx th.rh {
  text-align:right; padding:0 10px 0 12px; font-weight:500; color:var(--tx2);
  white-space:nowrap; font-family:var(--sans); font-size:11.5px;
}
table.mx th.ch { height:124px; vertical-align:bottom; padding-bottom:8px; width:36px; }
table.mx th.ch div {
  writing-mode:vertical-rl; transform:rotate(180deg); color:var(--tx2);
  font-family:var(--sans); font-size:11.5px; font-weight:500; white-space:nowrap;
}
table.mx td.c { width:36px; height:30px; border:1px solid var(--bg); color:#fff; font-size:10px; }
table.tb { width:100%; border-collapse:collapse; font-size:12.5px; }
table.tb th {
  text-align:left; padding:7px 10px; border-bottom:1px solid var(--line2); color:var(--tx3);
  font:10px/1 var(--mono); text-transform:uppercase; letter-spacing:.08em; white-space:nowrap;
}
table.tb td { padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
table.tb tr:last-child td { border-bottom:0; }
table.tb td.p { font:11.5px var(--mono); color:var(--tx2); word-break:break-all; }
table.tb td.n { font:12px var(--mono); text-align:right; white-space:nowrap; }
.pill {
  display:inline-block; font:10px var(--mono); padding:2px 7px; border-radius:99px;
  border:1px solid var(--line2); color:var(--tx2); white-space:nowrap;
}
.bar { height:5px; border-radius:3px; background:var(--ac); margin-top:4px; }
.note {
  background:var(--panel2); border:1px solid var(--line); border-left:3px solid var(--warn);
  border-radius:7px; padding:12px 15px; font-size:12.5px; color:var(--tx2); margin-top:14px;
}
.prov h4 { margin:0 0 8px; font-size:13px; }
.prov h4 + ul { margin:0 0 14px; padding-left:19px; color:var(--tx2); }
.prov li { margin-bottom:4px; }
.banner {
  padding:.5rem 1.25rem; background:var(--panel2); color:var(--tx2); font-size:.9rem;
  border-bottom:1px solid var(--line);
}
#ov {
  position:fixed; inset:0; background:rgba(0,0,0,.55); display:none; z-index:50;
  align-items:flex-start; justify-content:center; padding-top:9vh;
}
#ov.on { display:flex; }
#pal {
  width:min(760px, 92vw); background:var(--panel); border:1px solid var(--line2);
  border-radius:11px; box-shadow:0 18px 50px rgba(0,0,0,.5); overflow:hidden;
}
#q {
  width:100%; border:0; outline:0; background:transparent; color:var(--tx);
  font:14px var(--mono); padding:15px 17px; border-bottom:1px solid var(--line);
}
#res { max-height:56vh; overflow-y:auto; }
.r { padding:8px 17px; border-bottom:1px solid var(--line); }
.r:last-child { border-bottom:0; }
.r:hover { background:var(--panel2); }
.r .t { font:11.5px var(--mono); color:var(--tx); word-break:break-all; }
.r .m { font-size:11px; color:var(--tx3); margin-top:3px; display:flex; gap:10px; flex-wrap:wrap; }
.r .m b { color:var(--ok); font-weight:500; }
.r .m i { color:var(--warn); font-style:normal; }
#rhint { padding:11px 17px; font-size:11.5px; color:var(--tx3); }
@media (max-width:880px) {
  .wrap { flex-direction:column; }
  nav {
    width:auto; flex:none; height:auto; position:static; border-right:0;
    border-bottom:1px solid var(--line);
  }
  nav a.item { display:inline-flex; } .navbtn { width:auto; }
  main { padding:20px 16px 60px; } #tm { height:370px; } .lyr { grid-template-columns:1fr; }
}
</style>
</head>
<body>
<noscript class="banner">
  This page builds its content from the dataset embedded below with the inline script. With
  scripting off, read <code>overview.md</code> and <code>tour.md</code> in this directory instead.
</noscript>
<div class="wrap">
<nav>
  <div class="brand"><b>System map</b><span id="stamp"></span></div>
  <button class="navbtn" id="openSearch" type="button">
    <span>Find a path&hellip;</span><kbd>Ctrl K</kbd>
  </button>
  <div class="grp">Orientation</div>
  <a class="item" href="#overview">Overview</a>
  <a class="item" href="#modules">Capability &rarr; directory</a>
  <div class="grp">Map</div>
  <a class="item" href="#sitemap">Sitemap</a>
  <a class="item" href="#layers">Layers &amp; composition</a>
  <a class="item" href="#deps">Dependency matrix</a>
  <div class="grp">Hotspots</div>
  <a class="item" href="#hubs">Hubs</a>
  <a class="item" href="#flows">Capability flows</a>
<a class="item" href="#mirrors">Mirror subtrees</a>
  <a class="item" href="#reach">Nothing calls these</a>
  <a class="item" href="#classes">Largest classes</a>
  <div class="grp">Provenance</div>
  <a class="item" href="#prov">Where each number came from</a>
  <button class="navbtn" id="themeBtn" type="button">
    <span>Switch theme</span><kbd>&#9686;</kbd>
  </button>
</nav>
<main>
<section id="overview">
  <h1>System map</h1>
  <p class="lede" id="lede"></p>
  <div class="grid g4" id="stats"></div>
  <div class="grid" id="heads"></div>
  <p class="sub" id="stampLine"></p>
  <p class="sub" id="confBy"></p>
</section>
<section id="modules">
  <h2>Capability &rarr; directory</h2>
  <p class="lede">The bridge from "fix screen X" to "open which file". Read out of the directory
  tree, never from a list of names.</p>
  <div class="card" style="padding:4px 6px"><table class="tb" id="modTable"></table></div>
  <p class="sub" id="modNote"></p>
</section>
<section id="sitemap">
  <h2>Sitemap &mdash; where the code sits</h2>
  <p class="lede">Cell area is the symbol count. Colour is the responsibility layer holding the most
  files <i>inside</i> that cell. Click to descend.</p>
  <span class="crumb" id="crumb"></span>
  <div id="tm"></div>
  <div class="legend" id="tmLegend"></div>
</section>
<section id="layers">
  <h2>Responsibility layers &amp; composition</h2>
  <p class="lede">The layer is inferred from what a path's directories name, not from the root
  folder. The bar shows which node kinds the layer's files declare, so a procedural layer is
  visible as procedural.</p>
  <div class="card" id="layerTable"></div>
  <div class="legend" id="lyrLegend"></div>
</section>
<section id="deps">
  <h2>Who depends on whom</h2>
  <p class="lede" id="mxLede"></p>
  <div class="mxwrap" id="mx"></div>
  <p class="sub" id="mxNote"></p>
</section>
<section id="hubs">
  <h2>Hubs &mdash; editing here touches everything</h2>
  <p class="lede" id="hubLede"></p>
  <div class="card" style="padding:4px 6px"><table class="tb" id="hubTable"></table></div>
</section>
<section id="flows">
  <h2>Capability flows &mdash; one request, end to end</h2>
  <p class="lede" id="flowLede"></p>
  <div class="card" style="padding:4px 6px"><table class="tb" id="flowTable"></table></div>
  <div class="note" id="flowNote"></div>
</section>
<section id="mirrors">
  <h2>Mirror subtrees</h2>
  <p class="lede" id="mirLede"></p>
  <div class="card" style="padding:4px 6px"><table class="tb" id="mirTable"></table></div>
  <div class="note" id="mirNote"></div>
</section>
<section id="reach">
  <h2>Nothing calls these &mdash; and what that means</h2>
  <p class="lede" id="reachLede"></p>
  <div class="grid g4" id="reachGrid"></div>
  <div class="note" id="reachNote"></div>
</section>
<section id="classes">
  <h2>Largest classes</h2>
  <p class="lede" id="clsLede"></p>
  <div class="card" style="padding:4px 6px"><table class="tb" id="clsTable"></table></div>
</section>
<section id="prov">
  <h2>Where each number came from</h2>
  <div class="card prov" id="provCard"></div>
</section>
</main>
</div>
<div id="ov"><div id="pal">
  <input id="q" autocomplete="off" spellcheck="false"
   placeholder="Paste a path, or type a file, capability or class name">
  <div id="res"></div><div id="rhint"></div>
</div></div>
<script type="application/json" id="dataset">__ONBOARDING_DATASET__</script>
<script>
var D = JSON.parse(document.getElementById("dataset").textContent);
var NS = "__NS__";
var SECTIONS = __SECTIONS__;

/* Thousands separator done by hand: toLocaleString depends on the host's locale data, and this
   page is asserted byte-for-byte and driven headlessly. */
function fmt(n) {
  if (typeof n !== "number" || !isFinite(n)) return String(n);
  var s = String(n), out = "", i;
  for (i = 0; i < s.length; i++) {
    out += s.charAt(i);
    var rest = s.length - 1 - i;
    if (rest > 0 && rest % 3 === 0) out += ",";
  }
  return out;
}
function pct(part, whole) { return whole ? Math.round((100 * part) / whole) : 0; }
function esc(s) {
  return String(s).replace(/[&<>"']/g, function (m) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m];
  });
}
function put(id, html) {
  var node = document.getElementById(id);
  if (node) node.innerHTML = html;
}
function total(rows) {
  var sum = 0, i;
  for (i = 0; i < rows.length; i++) sum += rows[i].count;
  return sum;
}
function pick(rows, key) {
  var i;
  for (i = 0; i < rows.length; i++) if (rows[i].kind === key) return rows[i].count;
  return 0;
}

var LAYERS = D.layers.map(function (row) { return row.layer; });
var PALETTE = ["#4dabf7", "#f59f00", "#37b24d", "#9775fa", "#e8590c", "#20c997",
               "#f06595", "#748ffc", "#fcc419", "#22b8cf", "#ff8787", "#868e96"];
var COLOR = {};
LAYERS.forEach(function (name, i) { COLOR[name] = PALETTE[i % PALETTE.length]; });
function colorOf(name) { return COLOR[name] || "#5c6773"; }

var PATHS = D.path_index.entries.map(function (entry) {
  var dir = D.path_index.dirs[entry[0]];
  return dir ? dir + "/" + entry[1] : entry[1];
});
var PSET = {};
PATHS.forEach(function (p) { PSET[p] = 1; });
var INDEX_PARTIAL = !!D.path_index.truncated;

/* ---------- overview ---------- */
var SYMBOLS = total(D.node_counts), EDGES = total(D.edge_counts);
var CONF = total(D.confidence);
var HEUR = 0;
D.confidence.forEach(function (row) {
  if (row.tier !== "EXACT") HEUR += row.count;
});
var STAMP = D.commit ? D.commit.slice(0, 12) : "";
put("stamp", STAMP ? esc(STAMP) : "no commit recorded");
put("lede",
  "Everything on this page is read out of one aggregate dataset built from the index; nothing is "
  + "hand-written about this repository. Use it to find where code lives, not as proof that it "
  + "does what you expect — the limits are stated in each section and again at the end.");
put("stampLine",
  (STAMP ? "Indexed at commit <code>" + esc(STAMP) + "</code>. " : "No commit was recorded. ")
  + "Dataset shape version " + D.version + ", layers derived by the <code>" + esc(D.method)
  + "</code> method. " + fmt(PATHS.length) + " of " + fmt(D.path_index.total)
  + " paths are embedded for search"
  + (INDEX_PARTIAL ? ", so search over this page is incomplete." : "."));
/* 196 — which language earned the confidence figure, or why that cannot be said. Never omitted:
   this is a document a human reads, so an absent attribution is stated rather than left blank. */
var CBL = D.confidence_by_language || { available: false, note: "", rows: [] };
put("confBy", CBL.available
  ? "Which language earned that: " + CBL.rows.map(function (row) {
      var all = 0, heur = 0;
      row.tiers.forEach(function (k) { all += k.count; if (k.tier !== "EXACT") heur += k.count; });
      return "<b>" + esc(row.language || "unattributed") + "</b> " + fmt(all) + " dependencies ("
        + pct(heur, all) + "% below exact)";
    }).join(" &middot; ")
  : esc(CBL.note));
var STATS = [
  ["Files", fmt(D.files), fmt(D.files - D.parsed) + " did not parse"],
  ["Symbols", fmt(SYMBOLS), D.node_counts.length + " distinct node kinds"],
  ["Dependencies", fmt(EDGES), pct(HEUR, CONF) + "% below the exact confidence tier"],
  ["Layers", fmt(LAYERS.length), "inferred from what paths name"],
  ["Capabilities", fmt(D.modules.modules.length), "read out of the directory tree"],
  ["Mapped directories", fmt(D.tree.length),
   "holding at least " + fmt(D.dir_symbol_threshold) + " symbols"]
];
put("heads", (D.headlines || []).map(function (row) {
  return '<div class="card head"><b>' + esc(row.label) + '</b><span>' + esc(row.text)
    + "</span></div>";
}).join(""));
put("stats", STATS.map(function (row) {
  return '<div class="card stat"><div class="v">' + row[1] + '</div><div class="k">'
    + row[0] + '</div><div class="n">' + row[2] + "</div></div>";
}).join(""));

/* ---------- capability table (114) ---------- */
var MODS = D.modules;
if (MODS.modules.length) {
  put("modTable",
    '<tr><th>Capability</th><th>Lives in</th><th style="text-align:right">Files</th>'
    + '<th style="text-align:right">Classes</th><th>Busiest file</th></tr>'
    + MODS.modules.map(function (m) {
      return '<tr><td><b>' + esc(m.module) + "</b>"
        + (m.single_tree ? ' <span class="pill">only tree</span>' : "")
        + '</td><td class="p">' + m.trees.map(esc).join("<br>")
        + '</td><td class="n">' + fmt(m.files) + '</td><td class="n">' + fmt(m.classes)
        + '</td><td class="p"><a data-p="' + esc(m.hub) + '" onclick="' + NS
        + '.open(this.dataset.p)">' + esc(m.hub || "—") + "</a>"
        + (m.hub_fan_in ? ' <span class="pill">' + fmt(m.hub_fan_in) + " dependents</span>" : "")
        + "</td></tr>";
    }).join(""));
} else {
  put("modTable", "<tr><td>No capability layout was found in this tree, so this table is empty "
    + "rather than invented. Use the search palette to find a file by name.</td></tr>");
}
var COV = MODS.coverage;
put("modNote", esc(COV.note) + " This table accounts for " + fmt(COV.covered)
  + " of " + fmt(COV.total) + " indexed files (" + COV.percent + "%); " + fmt(COV.excluded)
  + " were excluded as vendored or test code."
  + (MODS.truncated ? " The list is capped, so it is not every capability." : "")
  + MODS.refused.map(function (row) {
      return "<br>Refused <code>" + esc(row.container) + "</code>: " + esc(row.reason);
    }).join(""));

/* ---------- sitemap treemap ---------- */
function nest(rows) {
  var root = { ch: {}, symbols: 0, files: 0, layer: "" };
  rows.forEach(function (row) {
    var segs = row.path.split("/"), node = root, i;
    for (i = 0; i < segs.length; i++) {
      if (!node.ch[segs[i]]) node.ch[segs[i]] = { ch: {}, symbols: 0, files: 0, layer: "" };
      node = node.ch[segs[i]];
    }
    node.symbols = row.symbols;
    node.files = row.files;
    node.layer = row.layer;
  });
  return root;
}
var TREE = nest(D.tree);
var trail = [];
function nodeAt(segs) {
  var node = TREE, i;
  for (i = 0; i < segs.length; i++) {
    if (!node || !node.ch[segs[i]]) return null;
    node = node.ch[segs[i]];
  }
  return node;
}
/* Squarified treemap: greedily take the row whose worst aspect ratio stops improving. */
function squarify(items, x, y, w, h, out) {
  if (!items.length || w < 1 || h < 1) return out;
  var sum = items.reduce(function (a, b) { return a + b.value; }, 0);
  if (sum <= 0) return out;
  var horiz = w >= h, side = horiz ? h : w;
  var best = Infinity, cut = 1, acc = 0, i, j;
  for (i = 0; i < items.length; i++) {
    acc += items[i].value;
    var len = (horiz ? w : h) * (acc / sum);
    if (len <= 0) continue;
    var worst = 0;
    for (j = 0; j <= i; j++) {
      var t = (items[j].value / acc) * side;
      if (t > 0) worst = Math.max(worst, Math.max(len / t, t / len));
    }
    if (worst <= best) { best = worst; cut = i + 1; } else break;
  }
  var row = items.slice(0, cut), rest = items.slice(cut);
  var rowSum = row.reduce(function (a, b) { return a + b.value; }, 0);
  var span = (horiz ? w : h) * (rowSum / sum), off = 0;
  row.forEach(function (item) {
    var t = side * (item.value / rowSum);
    out.push({ item: item, x: horiz ? x : x + off, y: horiz ? y + off : y,
               w: horiz ? span : t, h: horiz ? t : span });
    off += t;
  });
  return horiz ? squarify(rest, x + span, y, w - span, h, out)
               : squarify(rest, x, y + span, w, h - span, out);
}
function drawTree() {
  var box = document.getElementById("tm");
  var here = trail.length ? nodeAt(trail) : TREE;
  var kids = (here && here.ch) || {};
  var items = Object.keys(kids).map(function (name) {
    return { name: name, value: kids[name].symbols, files: kids[name].files,
             layer: kids[name].layer, deep: !!Object.keys(kids[name].ch).length };
  }).sort(function (a, b) {
    return b.value - a.value || (a.name < b.name ? -1 : 1);
  });
  if (!items.length) {
    box.innerHTML = '<div class="empty">' + (D.tree.length
      ? "Nothing below this directory holds at least " + fmt(D.dir_symbol_threshold)
        + " symbols, so there is nothing further to draw."
      : "No directory in this repository holds at least " + fmt(D.dir_symbol_threshold)
        + " symbols, so the sitemap is empty. That is the pruning threshold, not a missing map.")
      + "</div>";
  } else {
    var w = box.clientWidth || 900, h = box.clientHeight || 440;
    box.innerHTML = squarify(items, 0, 0, w, h, []).map(function (cell) {
      var it = cell.item, label = "";
      if (cell.w > 52 && cell.h > 26) {
        label = '<div class="nm">' + esc(it.name) + "</div>";
        if (cell.h > 44) {
          label += '<div class="mt">' + fmt(it.value) + " symbols · " + fmt(it.files)
            + " files</div>";
        }
      }
      var full = trail.concat([it.name]).join("/");
      return '<div class="cell' + (it.deep ? " dig" : "") + '" style="left:' + cell.x
        + "px;top:" + cell.y + "px;width:" + cell.w + "px;height:" + cell.h
        + "px;background:" + colorOf(it.layer) + '" title="' + esc(full) + " — "
        + fmt(it.value) + " symbols, " + fmt(it.files) + " files, mostly "
        + esc(it.layer || "unlabelled") + '"'
        + (it.deep ? ' data-p="' + esc(full) + '" onclick="' + NS + '.dive(this.dataset.p)"' : "")
        + ">" + label + "</div>";
    }).join("");
  }
  var crumb = ['<a data-p="" onclick="' + NS + '.dive(this.dataset.p)">(repository root)</a>'];
  trail.forEach(function (seg, i) {
    var upto = trail.slice(0, i + 1).join("/");
    crumb.push(i === trail.length - 1 ? "<b>" + esc(seg) + "</b>"
      : '<a data-p="' + esc(upto) + '" onclick="' + NS + '.dive(this.dataset.p)">'
        + esc(seg) + "</a>");
  });
  put("crumb", crumb.join(" / ")
    + (here && trail.length ? '  <span class="pill">' + fmt(here.symbols) + " symbols · "
       + fmt(here.files) + " files</span>" : ""));
}
put("tmLegend", LAYERS.map(function (name) {
  return '<span><i class="dot" style="background:' + colorOf(name) + '"></i>' + esc(name)
    + "</span>";
}).join(""));

/* ---------- layers & composition ---------- */
var KIND_COLOR = {};
var KIND_NAMES = D.node_counts.map(function (row) { return row.kind; });
KIND_NAMES.forEach(function (kind, i) { KIND_COLOR[kind] = PALETTE[i % PALETTE.length]; });
var WIDEST = D.layers.reduce(function (a, row) { return Math.max(a, row.modules); }, 0);
put("layerTable", D.layers.map(function (row) {
  var sum = total(row.kinds) || 1;
  var bars = row.kinds.map(function (k) {
    return '<i style="background:' + (KIND_COLOR[k.kind] || "#868e96") + ";width:"
      + (100 * k.count) / sum + '%" title="' + esc(k.kind) + ": " + fmt(k.count) + '"></i>';
  }).join("");
  return '<div class="lyr"><div class="nm"><i class="dot" style="background:' + colorOf(row.layer)
    + '"></i><span>' + esc(row.layer) + '<div class="desc">' + esc(row.description)
    + '</div></span></div><div><div class="stack" style="width:'
    + Math.max(6, (100 * row.modules) / (WIDEST || 1)) + '%">' + bars
    + '</div></div><div class="qty">' + fmt(row.modules) + " files · fan-in "
    + fmt(row.fan_in) + " · fan-out " + fmt(row.fan_out) + "</div></div>";
}).join(""));
put("lyrLegend", "Bar segments: " + KIND_NAMES.map(function (kind) {
  return '<span><i class="dot" style="background:' + (KIND_COLOR[kind] || "#868e96") + '"></i>'
    + esc(kind) + "</span>";
}).join("") + "<span>bar length is the file count</span>");

/* ---------- dependency matrix: every layer, both axes, no cut (AC5) ---------- */
var CELL = {}, MXMAX = 0;
D.matrix.forEach(function (edge) {
  CELL[edge.source + "\\u0000" + edge.target] = edge.count;
  if (edge.count > MXMAX) MXMAX = edge.count;
});
put("mxLede", "All " + fmt(LAYERS.length) + " layers appear on both axes, with nothing cut. Rows "
  + "call, columns are called. A brighter cell is a heavier dependency.");
var head = '<table class="mx"><tr><th class="rh"></th>' + LAYERS.map(function (name) {
  return '<th class="ch"><div>' + esc(name) + "</div></th>";
}).join("") + "</tr>";
put("mx", head + LAYERS.map(function (from) {
  return '<tr><th class="rh">' + esc(from) + "</th>" + LAYERS.map(function (to) {
    var n = CELL[from + "\\u0000" + to] || 0;
    var shade = n ? 0.1 + Math.pow(n / MXMAX, 0.42) * 0.85 : 0;
    return '<td class="c" style="background:'
      + (n ? "rgba(77,171,247," + shade + ")" : "transparent") + '" title="' + esc(from)
      + " → " + esc(to) + ": " + fmt(n) + '">' + (n ? fmt(n) : "") + "</td>";
  }).join("") + "</tr>";
}).join("") + "</table>");
put("mxNote", D.matrix.length
  ? "Heaviest: <code>" + esc(D.matrix[0].source) + "</code> → <code>"
    + esc(D.matrix[0].target) + "</code>, " + fmt(D.matrix[0].count) + " edges. The diagonal is "
    + "dependency within one layer. " + fmt(D.matrix.length) + " ordered layer pairs carry an edge."
  : "No dependency crosses between layers in this index.");

/* ---------- hubs ---------- */
var HUBMAX = D.hubs.reduce(function (a, h) { return Math.max(a, h.fan_in); }, 0);
put("hubLede", "Ranked by how many files depend on them. This is the " + fmt(D.hubs.length)
  + " highest, a ranking rather than an inventory — a file absent here is not unimportant.");
put("hubTable", D.hubs.length
  ? '<tr><th>File</th><th>Layer</th><th style="text-align:right">Dependents</th>'
    + '<th style="text-align:right">Depends on</th></tr>'
    + D.hubs.map(function (h) {
        return '<tr><td class="p"><a data-p="' + esc(h.file) + '" onclick="' + NS
          + '.open(this.dataset.p)">' + esc(h.file) + '</a></td><td><span class="pill" style="'
          + "border-color:" + colorOf(h.layer) + ";color:" + colorOf(h.layer) + '">'
          + esc(h.layer || "unlabelled") + '</span></td><td class="n">' + fmt(h.fan_in)
          + '<div class="bar" style="width:' + pct(h.fan_in, HUBMAX) + '%"></div></td>'
          + '<td class="n">' + fmt(h.fan_out) + "</td></tr>";
      }).join("")
  : "<tr><td>No file in this index has an inbound dependency.</td></tr>");

/* ---------- capability flows (197) ---------- */
var FL = D.flows;
if (!FL) {
  put("flowLede", "This index was built before capability flows existed, so none are recorded. "
    + "That is a missing input, not a repository with no requests.");
  put("flowTable", "");
  put("flowNote", "");
} else if (FL.refused) {
  put("flowLede", esc(FL.refused));
  put("flowTable", "");
  put("flowNote", "");
} else {
  put("flowLede", fmt(FL.flows_found) + " flow(s) traced from " + fmt(FL.seeds_traced) + " of "
    + fmt(FL.seeds_found) + " entry symbol(s); " + fmt(FL.flows.length) + " shown, "
    + fmt(FL.flows_cut) + " cut. Each row is one request: every hop is an edge, and a hop that "
    + "could not be proven ends the trace instead of being bridged.");
  put("flowTable", FL.flows.length
    ? '<tr><th>Entry</th><th>Module</th><th>Layers crossed</th><th>Ends</th>'
      + '<th style="text-align:right">Hops</th></tr>'
      + FL.flows.map(function (f) {
          return '<tr><td class="p">' + esc(f.seed) + '</td><td>'
            + esc(f.module || "unattributed") + '</td><td>' + esc(f.layers.join(" \u2192 "))
            + '</td><td>' + esc(f.sink ? f.ended + " \u2192 " + f.sink : f.ended)
            + '</td><td class="n">' + fmt(f.steps.length) + '</td></tr>';
        }).join("")
    : '<tr><td>No flow reached a recorded ending.</td></tr>');
  put("flowNote", esc(FL.coverage_note)
    + (FL.walk_truncated_note ? " " + esc(FL.walk_truncated_note) : "")
    + (FL.unattributed.length
        ? " " + fmt(FL.unattributed.length) + " seed(s) fall outside every module directory."
        : ""));
}

/* ---------- mirror subtrees (115) ---------- */
var MIR = D.mirrors;
put("mirLede", MIR.pairs.length
  ? "Sibling directories holding the same relative paths. Editing one side and forgetting the "
    + "other is the failure this section exists to prevent — paste a path into the search "
    + "palette and it names the parallel file, or says there is none."
  : "No sibling subtrees in this repository share enough of their relative paths to be reported "
    + "as mirrors. That is a measured absence, not an unrun check.");
put("mirTable", MIR.pairs.length
  ? '<tr><th>Left</th><th>Right</th><th style="text-align:right">Shared</th>'
    + '<th style="text-align:right">Overlap</th><th style="text-align:right">Left only</th>'
    + '<th style="text-align:right">Right only</th></tr>'
    + MIR.pairs.map(function (p) {
        return '<tr><td class="p">' + esc(p.left) + '</td><td class="p">' + esc(p.right)
          + '</td><td class="n">' + fmt(p.shared) + '</td><td class="n">'
          + Math.round(p.overlap * 100) + '%</td><td class="n">' + fmt(p.left_only)
          + '</td><td class="n">' + fmt(p.right_only) + "</td></tr>";
      }).join("")
  : "");
put("mirNote", esc(MIR.caveat));

/* ---------- zero-inbound split (113) ---------- */
var SPLIT = D.reachability;
put("reachLede", fmt(SPLIT.total) + " files (" + pct(SPLIT.total, D.files)
  + "% of the index) have no file depending on them by static analysis. Reporting that as one "
  + "number would be wrong — it is " + fmt(SPLIT.buckets.length)
  + " different populations, and only the last is a list of suspects.");
put("reachGrid", SPLIT.buckets.map(function (b) {
  /* 119: one number over two signals hid a false declaration, so the tally rides the card. */
  var tally = Object.keys(b.signals || {}).filter(function (k) { return b.signals[k]; })
    .map(function (k) { return fmt(b.signals[k]) + " " + esc(k); }).join(" \u00b7 ");
  return '<div class="card stat"><div class="v">' + fmt(b.count) + '</div><div class="k">'
    + esc(b.label) + '</div><div class="n">' + esc(b.signal)
    + (tally ? '</div><div class="n">' + tally : "") + "</div></div>";
}).join(""));
put("reachNote", SPLIT.buckets.map(function (b) {
  return "<b>" + esc(b.label) + ".</b> " + esc(b.note)
    + (b.sample.length ? " For example " + b.sample.slice(0, 2).map(function (s) {
        return "<code>" + esc(s) + "</code>";
      }).join(", ") + (b.sample_truncated ? " (sample capped)" : "") : "");
}).join("<br>") + SPLIT.dropped.map(function (row) {
  return "<br><b>" + esc(row.bucket) + " is not reported.</b> " + esc(row.reason);
}).join("") + "<br>" + esc(SPLIT.caveat) + (SPLIT.patterns.length
  ? "<br>" + SPLIT.patterns.map(function (c) {
      return "<code>" + esc(c.pattern) + "</code> (" + esc(c.kind) + ") matches "
        + fmt(c.files_matched) + " indexed files and claims " + fmt(c.zero_inbound_claimed)
        + " of the modules above";
    }).join("<br>")
  : "<br>No entry-point or dependency-root globs are declared, so no count above is a declared one."
));

/* ---------- largest classes ---------- */
put("clsLede", "Ranked by declared members in the same file. This is the " + fmt(D.classes.length)
  + " largest, a ranking rather than an inventory.");
put("clsTable", D.classes.length
  ? '<tr><th>Class</th><th>Layer</th><th style="text-align:right">Members</th><th>File</th></tr>'
    + D.classes.map(function (c) {
        return "<tr><td><b>" + esc(c.name) + '</b></td><td><span class="pill" style="border-color:'
          + colorOf(c.layer) + ";color:" + colorOf(c.layer) + '">' + esc(c.layer || "unlabelled")
          + '</span></td><td class="n">' + fmt(c.members) + '</td><td class="p"><a data-p="'
          + esc(c.file) + '" onclick="' + NS + '.open(this.dataset.p)">' + esc(c.file)
          + "</a></td></tr>";
      }).join("")
  : "<tr><td>This index declares no classes.</td></tr>");

/* ---------- provenance ---------- */
put("provCard",
  "<h4>Derived from the index &mdash; recomputable, and nobody's opinion</h4><ul>"
  + "<li>Every count: files, symbols by kind, dependencies by kind and confidence tier.</li>"
  + "<li>Responsibility layers, from what a path's directories name.</li>"
  + "<li>The sitemap, the layer composition, the matrix, the hubs and the largest classes.</li>"
  + "<li>The capability table, the mirror pairs and the zero-inbound split.</li>"
  + "<li>Every figure in this page's own prose, interpolated at render time.</li></ul>"
  + "<h4>Written by a person or generated</h4><ul><li><b>Nothing on this page.</b> Each sentence "
  + "here is either a fixed label shipped with the tool or a figure read out of the dataset. When "
  + "a narrative layer is added, this list names it, so a reader can always tell a derived number "
  + "from an interpretation of one.</li></ul>"
  + "<h4>What this page cannot tell you</h4><ul>"
  + "<li>" + esc(MIR.caveat) + "</li>"
  + "<li>" + pct(HEUR, CONF) + "% of dependencies sit below the exact confidence tier: they were "
  + "inferred, not resolved. Dynamic dispatch is not statically visible at all.</li>"
  + "<li>" + esc(D.path_index.caveat) + "</li>"
  + "<li>Operational documentation — how to run this, its environment, its data — belongs "
  + "to the repository and is not derivable from an index.</li></ul>"
  + '<p class="sub">Companion documents written beside this page: <code>overview.md</code>, '
  + "<code>tour.md</code> and one page per module under <code>modules/</code>.</p>");

/* ---------- counterpart lookup (115's four outcomes, in the browser) ---------- */
function counterpart(path) {
  var pairs = MIR.pairs, i, j;
  for (i = 0; i < pairs.length; i++) {
    var sides = [[pairs[i].left, pairs[i].right], [pairs[i].right, pairs[i].left]];
    for (j = 0; j < 2; j++) {
      var prefix = sides[j][0] + "/";
      if (path.indexOf(prefix) !== 0) continue;
      var candidate = sides[j][1] + "/" + path.slice(prefix.length);
      if (PSET[candidate]) {
        return { status: "counterpart", path: candidate,
                 pair: [pairs[i].left, pairs[i].right], qualified: false };
      }
      return { status: "no_counterpart", path: "",
               pair: [pairs[i].left, pairs[i].right], qualified: INDEX_PARTIAL };
    }
  }
  return { status: "outside_mirror", path: "", pair: null, qualified: false };
}

/* ---------- search palette ---------- */
var SHOWN_MAX = 40;
var NAMED_TREES = 6;
function subtreeOf(path) {
  var cut = path.indexOf("/");
  return cut > 0 ? path.slice(0, cut) : "";
}
/* Rank first, truncate second (067). Basename beats directory, short beats long, name breaks
   the tie — a total order, so the page cannot depend on the walk that filled the index. */
function rankOf(low, q) {
  var base = low.slice(low.lastIndexOf("/") + 1);
  if (low === q) return 0;
  if (base === q) return 1;
  if (base.indexOf(q) >= 0) return 2;
  return 3;
}
function ranked(hits, q) {
  return hits.map(function (p) { return { path: p, rank: rankOf(p.toLowerCase(), q) }; })
    .sort(function (a, b) {
      return a.rank - b.rank || a.path.length - b.path.length
        || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
    });
}
/* A floor, not a quota: every subtree in the full match set keeps one row on the page, and it is
   paid for by the most over-represented subtree. Never evicts a subtree's last row. */
function represent(order, cap) {
  var page = order.slice(0, cap);
  if (order.length <= cap) return page;
  var best = {}, trees = [], counts = {}, i;
  for (i = 0; i < order.length; i++) {
    var tree = subtreeOf(order[i].path);
    if (!(tree in best)) { best[tree] = order[i]; trees.push(tree); }
  }
  for (i = 0; i < page.length; i++) {
    var on = subtreeOf(page[i].path);
    counts[on] = (counts[on] || 0) + 1;
  }
  for (i = 0; i < trees.length; i++) {
    if (counts[trees[i]]) continue;
    var crowd = null, at = -1, seat;
    for (seat = 0; seat < page.length; seat++) {
      var owner = subtreeOf(page[seat].path);
      if (crowd === null || counts[owner] > counts[crowd]
          || (counts[owner] === counts[crowd] && seat > at)) { crowd = owner; at = seat; }
    }
    if (crowd === null || counts[crowd] < 2) break;
    counts[crowd] -= 1;
    counts[trees[i]] = 1;
    page[at] = best[trees[i]];
  }
  return page.sort(function (a, b) {
    return a.rank - b.rank || a.path.length - b.path.length
      || (a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  });
}
function search(raw) {
  var q = String(raw || "").trim().toLowerCase();
  if (q.length < 2) {
    return { items: [], shown: 0, incomplete: INDEX_PARTIAL, short: true, paths: 0, cut: 0,
             trees: [] };
  }
  var exact = [], part = [], i;
  for (i = 0; i < PATHS.length; i++) {
    var low = PATHS[i].toLowerCase();
    if (low === q) exact.push(PATHS[i]);
    else if (low.indexOf(q) >= 0) part.push(PATHS[i]);
  }
  var items = [];
  MODS.modules.forEach(function (m) {
    if (m.module.toLowerCase().indexOf(q) >= 0) {
      items.push({ kind: "capability", text: m.module,
                   note: fmt(m.files) + " files, " + fmt(m.classes) + " classes, in "
                         + m.trees.join(" and ") });
    }
  });
  D.classes.forEach(function (c) {
    if (c.name.toLowerCase().indexOf(q) >= 0) {
      items.push({ kind: "class", text: c.name,
                   note: fmt(c.members) + " members in " + c.file, target: c.file });
    }
  });
  var hits = exact.concat(part);
  var order = ranked(hits, q), spans = {}, trees = [];
  order.forEach(function (row) {
    var tree = subtreeOf(row.path);
    if (tree && !(tree in spans)) { spans[tree] = 1; trees.push(tree); }
  });
  represent(order, SHOWN_MAX).forEach(function (row) {
    var p = row.path, answer = counterpart(p), note;
    if (answer.status === "counterpart") note = "parallel file: " + answer.path;
    else if (answer.status === "no_counterpart") {
      note = "inside a mirror pair with no parallel file"
        + (answer.qualified ? " in the embedded index, which is capped" : "");
    } else note = "";
    items.push({ kind: "path", text: p, note: note, target: answer.path || p,
                 status: answer.status });
  });
  return { items: items, shown: items.length, incomplete: INDEX_PARTIAL, short: false,
           paths: hits.length, cut: Math.max(0, hits.length - SHOWN_MAX),
           trees: trees.sort() };
}
function draw(raw) {
  var found = search(raw);
  if (found.short) {
    put("res", "");
    put("rhint", "Type at least two characters."
      + (INDEX_PARTIAL ? " The embedded path index is capped, so search is incomplete." : ""));
    return;
  }
  put("res", found.items.map(function (item) {
    var lead = item.kind === "path" ? "" : esc(item.kind) + " ";
    var mark = item.status === "counterpart" ? "<b>" : (item.note ? "<i>" : "<span>");
    var close = item.status === "counterpart" ? "</b>" : (item.note ? "</i>" : "</span>");
    return '<div class="r"><div class="t">' + lead + esc(item.text) + '</div><div class="m">'
      + (item.note ? mark + esc(item.note) + close : "") + "</div></div>";
  }).join(""));
  put("rhint", found.items.length
    ? "Showing " + fmt(found.items.length) + " result"
      + (found.items.length === 1 ? "" : "s")
      + (found.cut ? ", " + fmt(found.cut) + " further path matches not listed" : "")
      + (found.cut && found.trees.length > 1
          ? ". The matches span " + fmt(found.trees.length) + " top-level subtrees: "
            + found.trees.slice(0, NAMED_TREES).join(", ")
            + (found.trees.length > NAMED_TREES
                ? " and " + fmt(found.trees.length - NAMED_TREES) + " more" : "")
          : "")
      + (INDEX_PARTIAL ? ". The embedded index is capped, so there may be more." : ".")
    : "No match among the " + fmt(PATHS.length) + " embedded paths."
      + (INDEX_PARTIAL ? " The index is capped, so this is not proof of absence." : ""));
}

/* ---------- wiring ---------- */
var NS_OBJ = {
  data: D,
  layers: LAYERS,
  paths: PATHS,
  sections: SECTIONS,
  search: search,
  counterpart: counterpart,
  dive: function (path) { trail = path ? path.split("/") : []; drawTree(); },
  open: function (value) {
    var overlay = document.getElementById("ov"), box = document.getElementById("q");
    if (overlay) overlay.className = "on";
    if (box) { box.value = value || ""; }
    draw(value || "");
  },
  close: function () {
    var overlay = document.getElementById("ov");
    if (overlay) overlay.className = "";
  },
  theme: function () {
    var root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    drawTree();
  }
};
globalThis[NS] = NS_OBJ;
drawTree();
if (document.getElementById("openSearch")) {
  document.getElementById("openSearch").onclick = function () { NS_OBJ.open(""); };
}
if (document.getElementById("themeBtn")) {
  document.getElementById("themeBtn").onclick = NS_OBJ.theme;
}
if (document.getElementById("q")) {
  document.getElementById("q").oninput = function () { draw(this.value); };
}
if (document.getElementById("ov")) {
  document.getElementById("ov").onclick = function (event) {
    if (event && event.target && event.target.id === "ov") NS_OBJ.close();
  };
}
</script>
</body>
</html>
"""


def render_viewer(dataset: OnboardingDataset, max_results: int) -> str:
    """One HTML file rendering the 112 dataset as a map. ``max_results`` is already baked in.

    The dataset is embedded as JSON with ``<`` escaped so it cannot break out of the script tag: a
    repo path can hold ``</script>`` (a directory ``a<`` and a file ``script>x``), which would end
    the block and leave the rest as live markup. ``test_onboarding_viewer`` pins it.

    ``max_results`` is accepted for signature parity with the other renderers and is deliberately
    unused: every list in the dataset was already capped where it was built (R4.3), and re-capping
    here would silently disagree with the counts the page prints.
    """
    del max_results
    blob = json.dumps(dataset.as_dict(), sort_keys=True, ensure_ascii=True)
    blob = blob.replace("<", "\\u003c")
    return (
        _TEMPLATE.replace("__NS__", NAMESPACE)
        .replace("__SECTIONS__", json.dumps(list(SECTION_IDS)))
        .replace(_PLACEHOLDER, blob)
    )
