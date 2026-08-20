# Onboarding mockup prototype

Reference implementation for the design in [`../ONBOARDING_MOCKUP.md`](../ONBOARDING_MOCKUP.md).
**Not shipped code** — it reads `graph.db` directly and would violate R1.4 (only `store.py` owns SQL)
if it lived under `code_atlas/`. It exists so the design note's numbers stay reproducible until tasks
108–117 land the real thing.

```bash
./build.sh /path/to/an/indexed/repo          # → artifacts/onboarding-mockup/index.html
```

Requires the repo to have been indexed already (`.code-atlas/graph.db` present).

## Files

| File | Role |
|---|---|
| `extract.py` | graph.db → one compact aggregate dataset (the shape task 112 formalises) |
| `template.html` | the dashboard; `__DATA__` is replaced with the dataset at build time |
| `build.sh` | runs both steps |
| `dom-stub.js` | minimal DOM so the dashboard script can be exercised headlessly under `node` |

## Headless check

```bash
python3 - <<'P'
import pathlib, re
h = pathlib.Path("../../../artifacts/onboarding-mockup/index.html").read_text()
pathlib.Path("/tmp/ua-check.js").write_text(re.findall(r"<script>(.*?)</script>", h, re.S)[-1])
P
cat dom-stub.js /tmp/ua-check.js > /tmp/ua-run.js
node /tmp/ua-run.js ../../../artifacts/onboarding-mockup/dataset.json
```
