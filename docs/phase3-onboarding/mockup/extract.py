"""Extract the sitemap dataset for the onboarding mockup (v2, feedback-driven).

Everything is derived from the code-atlas graph.db alone — no repo doc, no hand-maintained
inventory, no repo-specific filename. What a newcomer can already read (README, docs/) is
deliberately out of scope: this answers only what the codebase itself says.
"""
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
c = sqlite3.connect(f"file:{REPO / '.code-atlas' / 'graph.db'}?mode=ro", uri=True)
def q(sql, *a):
    return c.execute(sql, a).fetchall()


d = {}

# ---------------------------------------------------------------- basics
d["files"] = q("SELECT COUNT(*), SUM(parsed_ok) FROM files")[0]
d["kinds"] = dict(q("SELECT kind, COUNT(*) FROM nodes GROUP BY kind ORDER BY 2 DESC"))
d["edge_kinds"] = dict(q("SELECT kind, COUNT(*) FROM edges GROUP BY kind ORDER BY 2 DESC"))
d["edge_conf"] = dict(q("SELECT confidence_tier, COUNT(*) FROM edges GROUP BY confidence_tier"))
d["commit"] = dict(q("SELECT key, value FROM meta")).get("last_commit", "")

# ---------------------------------------------------------------- layers by responsibility
VOCAB = [
    (("controller", "controllers", "route", "routes", "handler", "handlers",
      "endpoint", "api"), "HTTP / Entry"),
    (("service", "services", "usecase", "business", "manager"), "Services"),
    (("model", "models", "entity", "entities", "repository", "repositories",
      "dao", "dmf", "dbo"), "Domain / Data"),
    (("view", "views", "template", "templates", "page", "pages", "widget",
      "form", "forms"), "Views"),
    (("middleware", "filter", "auth", "session", "acl", "security"), "Middleware / Auth"),
    (("job", "jobs", "cron", "queue", "worker", "batch", "task", "tasks",
      "schedule"), "Background Jobs"),
    (("report", "reports", "export", "import", "interop", "integration",
      "soap", "wsdl", "ws"), "Integration / Reporting"),
    (("lib", "libs", "util", "utils", "helper", "helpers", "common", "shared",
      "system", "include", "includes"), "Shared Library"),
    (("test", "tests", "phpunit", "spec", "mock", "mocks", "stub", "stubs",
      "fixture", "fixtures"), "Tests"),
    (("config", "conf", "settings", "env", "migration", "migrations", "sql",
      "install"), "Config / Migration"),
    (("vendor", "third_party", "3rdparty", "external", "zend", "smarty", "saml"),
     "Vendor / Framework"),
]
ENTRY_NAMES = {"index.php", "main.php", "bootstrap.php", "app.php", "router.php"}


def layer_of(path: str) -> str:
    for seg in reversed([s.lower() for s in path.split("/")[:-1]]):
        for words, name in VOCAB:
            if seg in words:
                return name
    if path.rsplit("/", 1)[-1].lower() in ENTRY_NAMES:
        return "HTTP / Entry"
    return "Uncategorised"


paths = sorted(r[0] for r in q("SELECT path FROM files WHERE parsed_ok=1"))
lay = {p: layer_of(p) for p in paths}

per_file = collections.defaultdict(collections.Counter)
for fp, kind, n in q("SELECT file_path, kind, COUNT(*) FROM nodes GROUP BY file_path, kind"):
    if fp:
        per_file[fp][kind] = n

lr = collections.defaultdict(collections.Counter)
for p in paths:
    lr[lay[p]]["files"] += 1
    for k, n in per_file.get(p, {}).items():
        lr[lay[p]][k] += n
d["layers"] = {L: dict(v) for L, v in sorted(lr.items(), key=lambda kv: -kv[1]["files"])}

# ---------------------------------------------------------------- edges, matrix, degrees
mat = collections.Counter()
fan_in, fan_out = collections.Counter(), collections.Counter()
for sp, tp, n in q("""SELECT s.file_path, t.file_path, COUNT(*) FROM edges e
        JOIN nodes s ON s.qualified_name = e.source_qname
        JOIN nodes t ON t.qualified_name = e.target_qname
        WHERE e.target_qname IS NOT NULL AND s.file_path <> t.file_path
        GROUP BY s.file_path, t.file_path"""):
    if sp in lay and tp in lay:
        mat[(lay[sp], lay[tp])] += n
        fan_out[sp] += 1
        fan_in[tp] += 1
d["matrix"] = [{"from": a, "to": b, "n": n} for (a, b), n in mat.most_common()]
d["hubs"] = [{"path": p, "in": fan_in[p], "out": fan_out[p], "layer": lay[p],
              "symbols": sum(per_file.get(p, {}).values())} for p, _ in fan_in.most_common(25)]
d["classes"] = [{"name": n, "path": fp, "methods": m, "layer": lay.get(fp, "?")}
                for n, fp, m in q("""SELECT c.name, c.file_path, COUNT(m.id) FROM nodes c
        LEFT JOIN nodes m ON m.file_path = c.file_path AND m.kind='Method'
        WHERE c.kind='Class' GROUP BY c.id ORDER BY 3 DESC LIMIT 20""")]

# ---------------------------------------------------------------- zero-inbound, split honestly
VENDOR_RE = re.compile(r"/(tcpdf|mpdf\d*|adodb|phpexcel|phpword|phpqrcode|fpdf|dompdf|smarty|"
                       r"simplesamlphp|saml|log4php|zend|vendor|node_modules)/", re.I)
TEST_RE = re.compile(r"(^|/)(tests?|phpunit|stubs?|fixtures?|mocks?)(/|$)", re.I)
WEB_RE = re.compile(r"(^public/|/controller/|/controllers/)", re.I)
WEBROOT_RE = re.compile(r"(^|/)(webapp|public|www|htdocs)/[^/]+\.php$", re.I)
zero = [p for p in paths if fan_in[p] == 0]


def bucket(p: str) -> str:
    if VENDOR_RE.search("/" + p):
        return "vendor"
    if TEST_RE.search(p):
        return "test"
    if WEB_RE.search(p) or WEBROOT_RE.search(p) or p.rsplit("/", 1)[-1].lower() in ENTRY_NAMES:
        return "web"
    return "unknown"


VIEWISH_RE = re.compile(r"(^|/)(view|views|template|templates|partial|partials|pages)(/|$)", re.I)
buck = collections.Counter(bucket(p) for p in zero)
unresolved = [p for p in zero if bucket(p) == "unknown"]
viewish = [p for p in unresolved if VIEWISH_RE.search(p)]
silent = [p for p in unresolved if not VIEWISH_RE.search(p) and fan_out[p] == 0]
d["entry_split"] = {"zero_inbound": len(zero), "web": buck["web"], "vendor": buck["vendor"],
                    "test": buck["test"], "unknown": buck["unknown"],
                    "viewish": len(viewish), "silent": len(silent)}
d["silent_sample"] = sorted(silent)[:8]

# ---------------------------------------------------------------- business modules, from the code
MOD_RE = re.compile(r"(?:^|/)(?:application|modules|Application)/([A-Za-z][A-Za-z0-9_]{2,})(?:/|$)")
SKIP = {"common", "include", "includes", "system", "lib", "libs", "controller", "model", "view",
        "views", "config", "core", "shared", "util", "utils", "helper", "helpers", "test", "tests",
        # region containers, not business modules
        "alpha", "beta", "ab", "region", "regions",
        # vendored libraries that happen to sit under a modules/ directory
        "phpexcel", "phpword", "saml", "simplesamlphp", "tcpdf", "mpdf", "adodb", "smarty",
        "log4php", "zend", "fpdf", "dompdf", "phpqrcode", "vendor"}
mods = collections.defaultdict(lambda: {"files": 0, "classes": 0, "sides": set(), "dirs": {}})
for p in paths:
    m = MOD_RE.search(p)
    if not m:
        continue
    name = m.group(1)
    if name.lower() in SKIP:
        continue
    e = mods[name.lower()]
    e["files"] += 1
    e["classes"] += per_file.get(p, {}).get("Class", 0)
    base = p[: m.end(1)]
    if p.startswith("legacy/alpha/"):
        e["sides"].add("alpha")
        e["dirs"].setdefault("alpha", base)
    elif p.startswith("legacy/beta/"):
        e["sides"].add("beta")
        e["dirs"].setdefault("beta", base)
    elif p.startswith("src/"):
        e["sides"].add("src")
        e["dirs"].setdefault("src", base)
    e.setdefault("_top", ("", -1))
    if fan_in[p] > e["_top"][1]:
        e["_top"] = (p, fan_in[p])
    e.setdefault("_label", name)
d["modules"] = [
    {"name": v["_label"], "files": v["files"], "classes": v["classes"],
     "sides": sorted(v["sides"]), "dirs": v["dirs"], "hub": v["_top"][0], "hub_in": v["_top"][1]}
    for k, v in sorted(mods.items(), key=lambda kv: -kv[1]["files"]) if v["files"] >= 8
][:24]

# ---------------------------------------------------------------- path index (front-coded)
dirs_idx, dirlist, files_enc = {}, [], []
for p in paths:
    head, _, tail = p.rpartition("/")
    if head not in dirs_idx:
        dirs_idx[head] = len(dirlist)
        dirlist.append(head)
    files_enc.append([dirs_idx[head], tail])
d["dirs"] = dirlist
d["files_idx"] = files_enc

# ---------------------------------------------------------------- tree with dominant layer
tree = {}
for p in paths:
    total = sum(per_file.get(p, {}).values())
    node = tree
    for seg in (p.split("/")[:-1] or ["(root)"])[:4]:
        node = node.setdefault(seg, {"_n": 0, "_f": 0, "_c": 0, "_L": collections.Counter()})
        node["_n"] += total
        node["_f"] += 1
        node["_c"] += per_file.get(p, {}).get("Class", 0)
        node["_L"][lay[p]] += 1
        node = node.setdefault("_ch", {})


def prune(nd, minimum):
    return {k: {"n": v["_n"], "f": v["_f"], "c": v["_c"], "L": v["_L"].most_common(1)[0][0],
                "ch": prune(v.get("_ch", {}), minimum)}
            for k, v in nd.items() if not k.startswith("_") and v["_n"] >= minimum}


d["tree"] = prune(tree, 400)

# ---------------------------------------------------------------- alpha/beta mirror
sides = collections.defaultdict(set)
for p in paths:
    m = re.match(r"legacy/(alpha|beta)/(.*)$", p)
    if m:
        sides[m.group(2)].add(m.group(1))
d["mirror"] = {"both": sum(1 for s in sides.values() if len(s) == 2),
               "alpha_only": sum(1 for s in sides.values() if s == {"alpha"}),
               "beta_only": sum(1 for s in sides.values() if s == {"beta"}),
               "sample": sorted(t for t, s in sides.items() if len(s) == 2)[:6]}

OUT.write_text(json.dumps(d, separators=(",", ":")), encoding="utf-8")
print("wrote", OUT, f"{OUT.stat().st_size/1024:.0f} KB")
print("entry_split:", d["entry_split"])
print("modules:", [(m["name"], m["files"], m["sides"]) for m in d["modules"][:12]])
print("paths:", len(d["files_idx"]), "dirs:", len(d["dirs"]))
print("tree roots:", {k: (v["L"], v["f"]) for k, v in d["tree"].items()})
print("silent sample:", d["silent_sample"][:3])
