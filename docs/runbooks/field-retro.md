# Field retro template

The sections a field-round write-up must fill. Not a benchmark harness (055 / 074 own those).
Copy the headings; leave unused later sections blank rather than inventing a parallel outline.

## 0.a Server build

Before the work (and again at the end), record which **code-atlas server** answered — not the indexed
repo's commit, not `contract_version` / `schema_version` (those name the index schema).

One call suffices:

```text
get_index_status(detail_level="standard")
```

Copy `server_version` and `server_build` from the payload. Two builds of the same declared version
must differ in `server_build`. If either field is absent, write **NOT OBSERVED** and treat every
verification verdict as unanchored.

A `server_build` ending in `+dirty` means the server ran from a checkout with uncommitted changes:
record it verbatim and do not quote the bare commit, because the code that answered is not that
commit. A clean run is the only one whose findings can be reproduced from a commit id alone.

When quoting a signed claim (`sign=true`), the line also carries `server=` and `build=` beside the
index revision keys.

## 0.5 Recognition probe

Run [`tool-recognition-probe.md`](tool-recognition-probe.md) **before** the agent sees
`which_tool`, the README tool table, or that runbook's answer key.

Record, or the §0.5 score is void:

- **Resident descriptions:** `K / 24` tool schemas in context at scoring time.
- **Per answer:** the first tool named, and `name-only` | `description-backed`.
- **Two rates:** name-inclusive (`recognised / 24`, labelled) and description-backed
  (`recognised among description-backed / D`, `D` = answers marked description-backed). The second
  is the 081 proxy; `D` equals `K` only if no schema loaded mid-probe.
- If `D = 0`, write `081: NOT OBSERVED`. If `K < 24`, do not treat a name-inclusive 24/24 as
  evidence that descriptions route.
- **Channels (200):** consumer brief present/absent; skill installed/not; `CA_TOOLS` default or
  FIELD18. **Occasion-fit** `/ 6` from the probe runbook. A surface hit with an O6 miss is still a
  result.

Also record the host-repo caveat when it applies: an agent guide that pre-routes tool names
verbatim is routing priming from outside code-atlas and biases the name-inclusive rate up.

## 0.6 The read-time signal (099)

If the host wired `code-atlas-signal`, record for each round — otherwise write `not wired`:

- **Fired:** how many times, and on what (Read outline / untracked-at-create).
- **Per firing, one of:** `seen and acted on` · `seen and ignored` · `tuned out` (the evaluator
  reports it stopped registering) · `not seen`.
- **The verdict question 099 owes:** did the signal reach the moment of decision, or did the
  evaluator learn to treat it as chrome? The field's own bound was ~150 tokens landing and ~500
  becoming chrome — a `tuned out` at the shipped cap **falsifies** the finding, and that is the
  point of recording it.

This is the other half of §0.5. Recognition asks *would you pick the right tool*; this asks *did the
information reach you when you were not choosing a tool at all*.

## 2 Coverage of the tool surface

For every tool **not** called in the work, assign **exactly one** bucket:

| # | Bucket | Means | Opposite fix |
|---|--------|-------|--------------|
| 1 | did not fit | The question never arose | none — not a routing defect |
| 2 | did not know it would answer this | Discovery failure | better / question-first descriptions (069) |
| 3 | knew it, did not trust it | The tool was considered and rejected | payload honesty (065 / 075 / 076) |
| 4 | knew it, it fit, did not think of it | Recall failure — named earlier, unused at the moment of cost | a workflow trigger, **not** a better description |

Bucket 4 is the slot round 5 lacked. Mis-filing it as bucket 2 sends the wrong fix.

## A Verification / other sections

Keep the rest of the retro as the round needs (verification table, cost, claims). This template
only freezes §0.5 and §2 so the next round can score 081 and can tell discovery from recall.
