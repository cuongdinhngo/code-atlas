# 140 — what the module rollup costs, against the symbol answer it summarises

**Status:** run 2026-08-24 (Linux, PHP 8.3.6). **Ticket:** [`../tasks/140_impact-answers-in-symbols-not-modules.md`](../tasks/140_impact-answers-in-symbols-not-modules.md).
**AC4 wants a number, not a claim.** Here it is, and so is the case where the saving is smallest.

Measured with `code_atlas.tokens.estimate_tokens` over `json.dumps` of each payload at
`detail_level: standard` — the same ~4-chars-per-token proxy the tokens-to-answer gate uses,
applied identically to both sides, so the *ratio* is meaningful without a model dependency.

| repo | subject | `impact` rows | `impact` tokens | modules | `impact_modules` tokens | saved |
|---|---|---|---|---|---|---|
| 140 fixture | `Invoice::total` | 7 | 299 | 5 | 245 | **18.1 %** |
| `symfony/demo` @ `03fe256` | `…Transformer::reverseTransform` | 6 | 453 | 1 | 186 | **58.9 %** |
| `brick/math` @ `b61d8e6` | `BigNumber::of` | 272 | 12 152 | 1 | 178 | **98.5 %** |

The rollup is **bounded by the module count**, the symbol answer by the radius — so the saving is a
function of how many symbols share a module, and it grows exactly where the complaint was loudest.
`brick/math`'s `BigNumber::of` is the shape the ticket describes: 272 rows, 12 152 tokens, and the
reader aggregating by hand. The 18 % row is the honest floor: a 7-row radius across 5 modules is
almost one module per symbol, so there is nothing to roll up and the rollup costs nearly as much.

**Read the floor as the rule, not the exception.** A rollup is worth calling when the radius is
bigger than the module table; below that, `impact` is the cheaper answer and this tool says so by
being no smaller.

## What the pins could not measure, and why that is the honest result

Both public pins roll up to a **single `unassigned` bucket**: 114's table refuses their layouts.
`symfony/demo` is organised by role (`Controller/`, `Repository/`, `Command/`…) and `brick/math` is
a library with an internal split, and 114 deliberately reports **no** modules rather than inventing
groups from a directory list. So on these two repos the tool is measurably cheaper and is *not*
giving a module answer.

That would read as a bug from the payload alone, so it does not have to be inferred: when the table
is empty the answer carries `NOTE_NO_MODULE_TABLE`, which names which of the two it is and routes
the reader back to `impact`. A tool that is cheap because it summarised nothing must say so — the
same rule 113 wrote for populations and 124 for bounded walks.

The capability-layout case therefore has to be measured on a fixture built to have one
(`tests/fixtures/php/impact_modules/`: four peer capability directories plus one file outside them
all). That is the first row, and it is also the row that exercises `unassigned` and the tier split.

## Bounds this page does not claim

- **Not a token count for a model.** `estimate_tokens` is a proxy; the ratio is the finding.
- **Not a claim about `impact`'s own bound.** Whether 500 nodes is the right walk budget is a
  separate question with its own measurement, explicitly out of this ticket's scope.
- **No repo with a large capability layout was available to pin.** The 98.5 % row shows the saving
  at radius scale; the fixture row shows the module split working. No committed pin shows both at
  once, and this page does not pretend otherwise.
