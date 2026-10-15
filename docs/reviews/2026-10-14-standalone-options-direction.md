# Owner direction: standalone options and a deferred scene join, 2026-10-14

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: recorded, committed as `ddbaebf` on the owner's instruction of 2026-10-14. Awaiting review by Codex and the owner.

## For the owner

- Each ACOLITE product is now a standalone observation. Its quality comes from its own flags layer.
- The store joins no Level-2A item to an ACOLITE record. A join waits until evidence proves the model needs it.
- The assessment compares two options, each used alone: ACOLITE only or Sen2Cor only. [Decision 0009](../decisions/0009-standalone-options-join-deferred.md) records this and amends decision 0008.
- Under ACOLITE only, the store has no cloud-shadow or snow flag, about half the acquisitions, and no source outside the lower 48 states.
- This record kept ACOLITE as the initial primary source and paused Level-2A's land-value role. Both readings are open to correction.

## Step and authorization

After the T4 review answer of 2026-10-14, the owner wrote:

> "Treat acolite scenes as standalone products; they should include flags within the data to indicate that a pixel is masked due to data quality issues. We can defer joining scenes until we prove beyond a shadow of a doubt that we'd need to do so, and for now treat our options as "acolite only" or "sen2cor only""

Earlier that day the owner wrote "masking rule: yes, same rule applies to acolite products". The [T4 record](2026-10-13-phase-c-t4-validity.md) holds that decision.
This step records the direction in the planning documents, the inventory, and the page. It runs no provider script and starts no Phase C step.
Deferred: the scene join and everything that depends on it, listed below.

## How this record reads the direction

| Owner's words | Reading |
|---|---|
| "Treat acolite scenes as standalone products" | Each product is one observation. Two products of one pass on one tile, one per datastrip, are two observations. This answers the second T4 review question |
| "they should include flags within the data" | Quality comes from the product's own `l2_flags` layer. Probe T4 found that the product flags pixels and keeps their values, finding 30 |
| "defer joining scenes" | No Level-2A layer attaches to an ACOLITE record. The two-source join prototype, the cross-baseline mapping, and the join rule question are deferred |
| "acolite only" or "sen2cor only" | Two standalone options. Neither fills or flags the other. Within Sen2Cor only, the older copy still backs Collection 1 under decision 0004 |

Where the words leave room, this record chose these readings:

- ACOLITE stays the initial primary source. Assumption A52 says so, and the direction does not revoke it. The USGS product keeps the name primary product.
- Direction 2 of 2026-10-13 lets Level-2A serve land monitoring in parallel. This record pauses that role with the others, because it places a second product beside ACOLITE records.
- Self-run ACOLITE stays the gap-fill context of assumption A48. It uses the same processor.
- Probe T5 stays in the plan as a comparison of the two options on the same pixels. It attaches nothing to a record.

## What changed

| File | Change |
|---|---|
| [decisions/0009](../decisions/0009-standalone-options-join-deferred.md) | New. Records the direction and amends decision 0008 |
| [decisions/0008](../decisions/0008-acolite-aquatic-reflectance-first.md) and the [index](../decisions/README.md) | Note that 0009 replaced the supplementary provision. The other provisions stay active |
| [assumptions.md](../assumptions.md) | A13, A46, and A47 restated |
| [data-contract.md](../data-contract.md) | One option per store. The join fields are removed. The join facts move under a deferred heading. `product_id` keeps split datastrips apart |
| [work-plan.md](../work-plan.md) | Next-step text, a checked item for the decision, the fill policy, the deferred join items, and costs, units of work, and tradeoffs per option |
| [Replan record](2026-10-13-acolite-first-replan.md) | A section quoting the direction and naming the plan parts it retires |
| [Inventory](../options-inventory.json) | Selection note and next items. Earth Search and its combinations become options compared for selection. C-09 drops the join. Issues I-31, I-32, I-36, I-38, and I-40 restated, I-32 deferred |
| [assessment-data-format.md](../assessment-data-format.md) | The `supplementary` role is now unused |
| `tools/s2-options.template.html` and the [page](../s2-options.html) | Section 02, the approach under the correction risk, the processing steps, and the stored-record example describe two standalone options |
| [CLAUDE.md](../../CLAUDE.md) and [README.md](../../README.md) | Current phase, the source convention, and two gotchas |
| [gap-survey-plan.md](../gap-survey-plan.md) | Earth Search's role |
| [T4 record](2026-10-13-phase-c-t4-validity.md) and [measurements.md](../measurements.md) | Join lines point to decision 0009 |

## Consequences for the options

These are tradeoffs for Phase F. This record forms no view on which option serves the model better, assumption A52.

- **Flags.** Under ACOLITE only, the store has no cloud-shadow or snow flag, finding 26. In probe T4, ACOLITE set no flag on 74 percent of interior observations the classification calls shadow, finding 33.
- That classification is a land product, so the figure shows where two products disagree. It measures no error.
- **Coverage.** From 2018 the product holds 41 to 61 percent of Earth Search's acquisitions per year, cloudy and partial ones missing most often, finding 27. Under ACOLITE only they stay missing and counted.
- **Reach.** The product is documented for the lower 48 states. Under ACOLITE only, the Alaska pilot region and waters elsewhere have no source. Sen2Cor only covers them.
- **Grid.** The product has one 20 m grid. Sen2Cor only keeps native 10 m bands, which give small ponds more pixels, finding 18.
- **Cost.** Each option carries its own costs. No join work enters either.

## Deferred

- The scene join, the two-source join prototype, the quality-layer mapping across baselines, and a test of the datastrip join key.
- Level-2A's quality, land-value, and fallback roles beside ACOLITE records.
- The Prototyping tab rebuild, a later Phase C step.

## Evidence

No provider contact. Every change is documentation, inventory text, and page text.

`/check` on 2026-10-14: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q` passed, 362 tests in 36.84 s.
The first full run failed one test, `test_supervisor_stops_a_real_worker_and_descendant`. It passed alone and in the second full run, the known memory-pressure flake.
The collation, sensor-band, renderer, gap-report, and review-layer `--check` commands report their outputs current.
A style scan of the added Markdown and inventory text found no semicolon and no forbidden modal verb outside the owner's verbatim quotes.

## Limits

- The readings above are an AI agent's. The owner's words are the authority.
- The inventory keeps `supplementary` in its role vocabulary, unused.
- Dated records of 2026-10-13 keep their text, except the replan record's new section and the T4 record, which still awaits review.

## Dispositions

| Item | Disposition |
|---|---|
| T4 review: which Level-2A item the join takes when two match | Fixed. The join is deferred, decision 0009. |
| T4 review: whether every ACOLITE product of a pass is its own observation | Fixed. Yes, decision 0009. |
| T4 review: the masking rule | Fixed on 2026-10-14. Issue I-35 is `decided`. |
| Issue I-32, status `open` | Deferred under decision 0009. |
| Work plan: the fill policy awaited the join prototype | Fixed. The policy now covers Sen2Cor only. The primary product's gaps stay missing and counted. |

## Proposed next step

Phase C continues one authorized step at a time. Two candidates:

- T6, the access replay of stages 2 to 4 and readers B1 and B3 on the primary product. It measures requests, bytes, time, and memory for the ACOLITE-only option and feeds its cost.
- T5, paired values against Collection 1. It shows where the two options' values differ on the same pixels, input to the company's experiments.

This record recommends T6 first, since it measures an option directly. Both read pixels and need explicit owner authorization. This step starts neither.
