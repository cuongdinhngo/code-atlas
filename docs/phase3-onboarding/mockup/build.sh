#!/usr/bin/env bash
# Rebuild the onboarding mockup from an indexed repo. Prototype only — not shipped code.
#   ./build.sh <repo-root> [out-dir]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="${1:?usage: build.sh <repo-root> [out-dir]}"
out="${2:-$here/../../../artifacts/onboarding-mockup}"
py="${PYTHON:-python3}"
mkdir -p "$out"
"$py" "$here/extract.py" "$repo" "$out/dataset.json"
"$py" - "$here/template.html" "$out/dataset.json" "$out/index.html" <<'PY'
import json, pathlib, sys
tpl, data, dest = (pathlib.Path(a) for a in sys.argv[1:4])
payload = json.dumps(json.loads(data.read_text(encoding="utf-8")), separators=(",", ":"))
dest.write_text(tpl.read_text(encoding="utf-8").replace("__DATA__", payload), encoding="utf-8")
print("wrote", dest, f"{dest.stat().st_size/1024:.0f} KB")
PY
