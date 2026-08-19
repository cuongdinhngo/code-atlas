# onboarding_llm — opt-in LLM summarizer (task 090, M12)

The one and only place an LLM touches code-atlas. It lives **outside** `code_atlas/` (mirroring
`adapters/`) so the deterministic core never imports an LLM and never runs one in the per-PR gate
(R4/R4.1). It plugs into the 085 `Summarizer` seam and replaces only the prose one-liner
(`docline`) per module; layer/role stay deterministic (role refinement is task 091).

## Enable it

1. Install the optional dependency:

   ```bash
   pip install -e ".[llm]"          # adds `anthropic`
   ```

2. Provide Claude credentials the SDK understands (e.g. `ANTHROPIC_API_KEY`, or an `ant auth login`
   profile).

3. Opt in and run the LLM entry point instead of `code-atlas`:

   ```bash
   export CA_ONBOARDING_SUMMARIZER=llm
   code-atlas-llm                    # == python -m onboarding_llm
   ```

Without `CA_ONBOARDING_SUMMARIZER=llm` (or `=claude`), `code-atlas-llm` behaves exactly like
`code-atlas` — the deterministic `StructuralSummarizer`.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `CA_ONBOARDING_SUMMARIZER` | *(unset)* | `llm`/`claude` enables the LLM; anything else = deterministic default |
| `CA_ONBOARDING_LLM_MODEL` | `claude-sonnet-5` | Claude model — a mid tier for per-module summaries (PHASE3 §4 M12) |
| `CA_ONBOARDING_LLM_CACHE` | `.code-atlas/onboarding-llm-cache.json` | Content-hash cache path |

## The cache — deterministic, committable

Each summary is keyed on the module's **content** (path, signature, docblock, structural role, model,
prompt version) — a rename or reorder is a cache hit, an edit is a miss. The file is sorted-key JSON
with no timestamps, so it is byte-stable and diffs cleanly. The default location is gitignored
(regenerable, like 088's onboarding cache); point `CA_ONBOARDING_LLM_CACHE` at a **tracked** path to
commit the summaries so every run — anywhere — replays them without calling Claude.
