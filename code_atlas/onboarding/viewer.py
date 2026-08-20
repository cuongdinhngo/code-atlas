"""Self-contained onboarding HTML viewer (task 089, M11).

One file, no server, no external URLs. The generator embeds the 088 artifact so the page
opens from the filesystem (``file://`` cannot fetch a sibling ``manifest.json``). Inline
CSS/JS only; ``connect-src 'none'`` so a fetch cannot be added later by accident.
"""

from __future__ import annotations

import json

from code_atlas.onboarding.artifact import (
    OnboardingArtifact,
    _rationale_line,
    render_module,
)

_PLACEHOLDER = "__ONBOARDING_PAYLOAD__"

# color-scheme + prefers-color-scheme: light and dark without a runtime toggle (AC2).
_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta http-equiv="Content-Security-Policy" content="default-src 'none';
style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src 'none';
connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>Onboarding</title>
<style>
:root {
  color-scheme: light dark;
  --bg:#f6f5f1; --fg:#1c1917; --muted:#57534e;
  --line:#d6d3d1; --card:#fff; --accent:#1d4ed8;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:#0c0a09; --fg:#f5f5f4; --muted:#a8a29e;
    --line:#292524; --card:#1c1917; --accent:#93c5fd;
  }
}
* { box-sizing: border-box; }
body {
  margin:0; font: 16px/1.45 ui-sans-serif, system-ui, sans-serif;
  background:var(--bg); color:var(--fg);
}
header {
  display:flex; flex-wrap:wrap; gap:.75rem 1rem; align-items:center;
  padding:.9rem 1.25rem; border-bottom:1px solid var(--line);
  background:var(--card);
}
h1 { font-size:1.1rem; margin:0; font-weight:650; }
nav { display:flex; gap:.4rem; }
button {
  font: inherit; border:1px solid var(--line); background:var(--bg);
  color:var(--fg); padding:.3rem .7rem; border-radius:.4rem; cursor:pointer;
}
button[aria-pressed="true"] {
  background:var(--fg); color:var(--bg); border-color:var(--fg);
}
.banner {
  padding:.4rem 1.25rem; background:var(--line); color:var(--muted);
  font-size:.9rem;
}
main {
  display:grid; grid-template-columns: minmax(12rem, 22rem) 1fr;
  min-height: calc(100vh - 4rem);
}
aside { border-right:1px solid var(--line); padding:1rem; overflow:auto; }
section { padding:1.25rem 1.5rem; overflow:auto; }
h2 { font-size:1rem; margin:0 0 .75rem; }
ol, ul { margin:0; padding-left:1.2rem; }
li { margin:.25rem 0; }
button.pick {
  display:block; width:100%; text-align:left; background:none; border:0;
  padding:.35rem .2rem; color:var(--accent); cursor:pointer; font: inherit;
}
pre {
  white-space:pre-wrap; background:var(--card);
  border:1px solid var(--line); padding:1rem; border-radius:.5rem;
}
.muted { color:var(--muted); font-size:.9rem; }
@media (max-width: 720px) {
  main { grid-template-columns: 1fr; }
  aside { border-right:0; border-bottom:1px solid var(--line); }
}
</style>
</head>
<body>
<header>
  <h1>Onboarding</h1>
  <nav>
    <button type="button" id="tab-layers" aria-pressed="true">Layers</button>
    <button type="button" id="tab-tour" aria-pressed="false">Tour</button>
  </nav>
</header>
<noscript class="banner">
  This page builds its content with the inline script below. With scripting off, read
  <code>overview.md</code> and <code>tour.md</code> in this directory instead.
</noscript>
<p id="banner" class="banner" hidden></p>
<main>
  <aside id="rail"></aside>
  <section id="panel"></section>
</main>
<script type="application/json" id="payload">__ONBOARDING_PAYLOAD__</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById("payload").textContent);
  var rail = document.getElementById("rail");
  var panel = document.getElementById("panel");
  var tabLayers = document.getElementById("tab-layers");
  var tabTour = document.getElementById("tab-tour");
  var banner = document.getElementById("banner");
  var pages = {};
  (data.pages || []).forEach(function (page) { pages[page.file] = page; });

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
  function el(name, text) {
    var node = document.createElement(name);
    if (text) node.textContent = text;
    return node;
  }
  function setTab(tour) {
    tabLayers.setAttribute("aria-pressed", tour ? "false" : "true");
    tabTour.setAttribute("aria-pressed", tour ? "true" : "false");
  }
  function showLayers() {
    setTab(false);
    clear(rail);
    clear(panel);
    rail.appendChild(el("h2", "Layers"));
    var list = el("ol");
    (data.layers || []).forEach(function (row) {
      var item = el("li", row.layer + " — " + row.modules + " modules");
      list.appendChild(item);
    });
    rail.appendChild(list);
    panel.appendChild(el("h2", "Summary"));
    var bits = [
      "method: " + (data.method || ""),
      "layers: " + ((data.layers || []).length),
      "stops: " + ((data.stops || []).length),
      "pages: " + ((data.pages || []).length),
      "no page (isolated, no summary): " + ((data.isolated || []).length),
      "truncated: " + (data.truncated ? "true" : "false")
    ];
    bits.forEach(function (line) { panel.appendChild(el("p", line)); });
    panel.appendChild(el("h2", "Crossings"));
    var crossings = data.crossings || [];
    if (!crossings.length) { panel.appendChild(el("p", "(none)")); return; }
    var ul = el("ul");
    crossings.forEach(function (edge) {
      ul.appendChild(el("li", edge.source + " → " + edge.target + " (" + edge.count + ")"));
    });
    panel.appendChild(ul);
  }
  function showPage(file) {
    setTab(true);
    var page = pages[file];
    clear(panel);
    panel.appendChild(el("h2", file));
    if (!page) { panel.appendChild(el("p", "No page for this stop.")); return; }
    var meta = el("p", (page.role || "") + " · " + (page.layer || ""));
    meta.className = "muted";
    panel.appendChild(meta);
    var body = el("pre");
    body.textContent = page.body || "";
    panel.appendChild(body);
  }
  function showTour(file) {
    setTab(true);
    clear(rail);
    rail.appendChild(el("h2", "Reading order"));
    var list = el("ol");
    (data.stops || []).forEach(function (stop) {
      var item = el("li");
      var btn = el("button", stop.file);
      btn.type = "button";
      btn.className = "pick";
      btn.addEventListener("click", function () { showPage(stop.file); });
      item.appendChild(btn);
      if (stop.rationale) item.appendChild(el("div", stop.rationale)).className = "muted";
      list.appendChild(item);
    });
    rail.appendChild(list);
    var first = file || ((data.stops || [])[0] || {}).file;
    if (first) showPage(first);
    else { clear(panel); panel.appendChild(el("p", "(none)")); }
  }

  if (data.truncated) {
    banner.hidden = false;
    banner.textContent = "This tour is truncated: some indexed files have no page.";
  }
  tabLayers.addEventListener("click", showLayers);
  tabTour.addEventListener("click", function () { showTour(); });
  showLayers();
})();
</script>
</body>
</html>
"""


def viewer_payload(artifact: OnboardingArtifact, max_results: int) -> dict[str, object]:
    """The JSON the HTML page boots from — same facts as the markdown, no wall-clock."""
    return {
        "crossings": [
            {"count": count, "source": source, "target": target}
            for source, target, count in artifact.crossings
        ],
        "layers": [
            {
                "description": row.description,
                "entry_points": row.entry_points,
                "fan_in": row.fan_in,
                "fan_out": row.fan_out,
                "layer": row.layer,
                "modules": row.modules,
                "rank": row.rank,
            }
            for row in artifact.layers
        ],
        "isolated": list(artifact.isolated),
        "method": artifact.method,
        "pages": [
            {
                "body": render_module(page, max_results),
                "file": page.file,
                "layer": page.layer,
                "role": page.role,
            }
            for page in artifact.pages
        ],
        "stops": [
            {"file": stop.file, "rationale": _rationale_line(stop.rationale, stop.scc, max_results)}
            for stop in artifact.stops
        ],
        "truncated": artifact.truncated,
    }


def render_viewer(artifact: OnboardingArtifact, max_results: int) -> str:
    """One HTML file. Payload is JSON with ``<`` escaped so it cannot break the script tag.

    The escape is load-bearing, not cosmetic: a repo path can hold ``</script>`` (a directory
    ``a<`` and a file ``script>x``), which would end the JSON block and leave the rest of the
    payload as live markup. ``test_onboarding_viewer`` pins it.
    """
    blob = json.dumps(viewer_payload(artifact, max_results), sort_keys=True, ensure_ascii=True)
    blob = blob.replace("<", "\\u003c")
    return _TEMPLATE.replace(_PLACEHOLDER, blob)
