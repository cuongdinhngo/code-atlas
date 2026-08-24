# onboarding_llm — opt-in LLM enrichment (tasks 090/091, M12)

The one and only place an LLM touches code-atlas. It lives **outside** `code_atlas/` (mirroring
`adapters/`) so the deterministic core never imports an LLM and never runs one in the per-PR gate
(R4/R4.1). It provides two opt-in enrichers, each behind its own seam and off by default:

- **090 — summaries** (`LLMSummarizer`, 085 `Summarizer` seam): replaces only the prose one-liner
  (`docline`) per module; signature and role stay deterministic.
- **091 — layer names** (`LLMLayerRefiner`, 091 `LayerRefiner` seam): renames the **weak** layers 084
  falls back to on flat namespaces (`source`/`sink`/`mixed`/`isolated`/`(root)`); real
  directory-named layers are left alone, and modules are never re-grouped, so coverage is unchanged.

## Enable it

1. Install the optional dependency:

   ```bash
   pip install -e ".[llm]"          # adds `anthropic`
   ```

2. Provide Claude credentials the SDK understands (e.g. `ANTHROPIC_API_KEY`, or an `ant auth login`
   profile).

3. Opt in (either or both) and run the LLM entry point instead of `code-atlas`:

   ```bash
   export CA_ONBOARDING_SUMMARIZER=llm      # 090 — per-module summaries
   export CA_ONBOARDING_LAYER_REFINER=llm   # 091 — layer-name refinement
   export CA_ONBOARDING_PROSE=llm           # 117 — the map's prose
   code-atlas-llm                    # == python -m onboarding_llm
   ```

With no switch set, `code-atlas-llm` behaves exactly like `code-atlas` — the deterministic
`StructuralSummarizer`, 084's heuristic layers and the structural prose. The switches are
independent.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `CA_ONBOARDING_SUMMARIZER` | *(unset)* | `llm`/`claude` enables LLM summaries; anything else = deterministic default |
| `CA_ONBOARDING_LLM_MODEL` | `claude-sonnet-5` | Summary model — a mid tier for per-module summaries (PHASE3 §4 M12) |
| `CA_ONBOARDING_LLM_CACHE` | `.code-atlas/onboarding-llm-cache.json` | Summary content-hash cache path |
| `CA_ONBOARDING_LAYER_REFINER` | *(unset)* | `llm`/`claude` enables layer-name refinement; anything else = 084 heuristic |
| `CA_ONBOARDING_LLM_LAYER_MODEL` | `claude-opus-5` | Layer model — a top tier for the refinement pass (PHASE3 §4 M12) |
| `CA_ONBOARDING_LLM_LAYER_CACHE` | `.code-atlas/onboarding-llm-layers.json` | Layer content-hash cache path |
| `CA_ONBOARDING_PROSE` | *(unset)* | `llm`/`claude` enables the 117 prose seam; anything else = structural defaults |
| `CA_ONBOARDING_LLM_PROSE_MODEL` | `claude-opus-5` | Prose model — a top tier, the highest-judgment slot (PHASE3 §4 M12) |
| `CA_ONBOARDING_LLM_PROSE_CACHE` | `.code-atlas/onboarding-llm-prose.json` | Prose content-hash cache path |

### What the prose seam writes, and what it cannot

Three slots and nothing else: a layer's one-line responsibility, a tour step's 2–4 sentence
narrative, and the wording of a headline fact. **Which** headlines exist, every count, ranking and
grouping, and the tour's own order are all derived before the seam is consulted, so enrichment can
reword the map but never change what it says. Inputs are structural only — member paths, degree mix,
node-kind composition — never file contents. A model failure, a refusal, or prose that merely
restates a path all resolve the same way: the slot keeps its deterministic sentence. Spend is capped
per slot (6 headlines, 12 layers, 15 steps — 33 calls for a whole build, whatever the repo's size);
`generate_onboarding` reports `prose_calls` and `prose_declined`, and
`scripts/prose_cost_report.py` records the cost on real repos.

## The caches — deterministic, committable

Each result is keyed on **content** — a summary on the module's (path, signature, docblock, role,
model, prompt version); a layer name on the layer's membership (its sorted file list, model, prompt
version); a piece of prose on its slot's whole request (the facts, the deterministic sentence it
replaces, and for a tour step the prose already settled for the step before it). A rename or reorder
is a cache hit, an edit is a miss. All three files are sorted-key JSON with no timestamps, so they
are byte-stable and diff cleanly. The default locations are gitignored
(regenerable, like 088's onboarding `artifact.json`); point the `_CACHE` env at a **tracked** path to commit the
results so every run — anywhere — replays them without calling Claude.
