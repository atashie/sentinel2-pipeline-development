# Phase A re-scope: decision 0008 activated and the planning documents restated, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered, awaiting owner review. No provider script ran. No pixel was read. Nothing is committed.

## Step and authorization

The [replan record](2026-10-13-acolite-first-replan.md) proposed Phase A as the next step, with probe T1 as an option beside it.
The owner answered "Please proceed" on 2026-10-13. This record reads that answer as authorization of Phase A alone.
Probe T1 contacts a provider and did not run. It runs as its own step when the owner invokes it.

Acceptance checks from the replan record: links resolve, tests pass, and every changed assumption cites the decision. All three hold, evidence below.

## What changed

| File | Change |
|---|---|
| [decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) | Status `proposed` to `active`. The replaced provision is narrowed to the route provision of decision 0003. The fallback order of decision 0004 governs the supplementary role. The grid bullet cites finding 18 instead of claiming that 30 m bodies have no interior pixel. |
| [decisions 0003](../decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md), [0004](../decisions/0004-cog-fallback-and-presentation-clarifications.md), and the [index](../decisions/README.md) | Back-links naming the replaced provision. The index row for 0008 reads `active`. |
| [assumptions.md](../assumptions.md) | A3, A4, A13, and A20 revised, each citing decision 0008. New section with rows A46 to A51. They cover the primary product as delivered, the four Level-2A roles, self-run ACOLITE as context, and the delivered NDWI layer. Two more cover the reference series and licensing. |
| [data-contract.md](../data-contract.md) | Draft v2. New fields: `product_family`, `processor` and `processor_version`, `aerosol_mode`, `settings_digest`, `ndwi`, `mask_reason`, and `quality_source_product`. `processing_baseline`, `dn`, `scale`, `conversion_source`, and the time fields gain primary-product meanings. New section on two products for one water body. New questions for T1 to T3. |
| [work-plan.md](../work-plan.md) | Next step restated as Phase B. The former next-session text kept under Phase 2 as status before the re-scope. Route re-scope added to step 2. Stage 5 replaced by phases A to D. Phases 3 and 4 mapped to replan phases E and F with the two-source units of work and the three-way tradeoff. |
| [CLAUDE.md](../../CLAUDE.md) | Current phase, the route convention, and two gotchas: every measurement describes Level-2A files, and the primary product has one 20 m grid. |
| [README.md](../../README.md) | Status paragraph, scope sentences, the page caveat, and two document index rows. |
| [examples/README.md](../../examples/README.md) | The Alaska region lies outside the primary product and stays a Level-2A-only case. |
| [reviews index](README.md) | Row for this record. |

Wording choices in the revised assumptions:

- A4 keeps the 2026-09-09 answer that infrastructure must scale globally. The 2026-10-13 direction narrows the initial scope to the lower 48 states and adds the redraft requirement for expansion.
- A13 holds the route. A46 to A51 hold the other directions, one fact per row, so no row repeats another.
- A20 now says "per source grid" instead of "per resolution", because the primary product has one grid and Level-2A has three.

## Evidence

`/check` on 2026-10-13: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q` passed, 327 tests in 32.79 s.
A style scan over the added lines found no semicolon, no forbidden modal verb, and no sentence over 25 words.
Every relative link in the changed documents resolves, `tests/test_docs.py`.

## Limits

- Every fact about the primary product in these documents is `unverified`. The sources are the AI-generated research under `data/research/`, outside git. Phase B check records and probes T1 to T3 confirm or correct them.
- The decision's activation rests on the owner's "Please proceed". If the owner meant something narrower, the status line of decision 0008 and this record are the two places to revert.
- Documents assigned to Phase B keep their Level-2A wording. The [gap survey plan](../gap-survey-plan.md) still says Earth Search is the route under assumption A13. The inventory's selection block, the presentation page, and practice P10 still describe the Earth Search route. The work plan and CLAUDE.md say so.
- The contract's `mask_reason` vocabulary and the join key are proposals. T1 and T3 decide them.
- The measured gotchas in CLAUDE.md about the two Earth Search collections stay true for the supplementary route and are unchanged.

## Dispositions of prior findings

- Replan record, Phase A items: `fixed` in this step.
- Replan record, Phase B to F items: `accepted and deferred` to their phases.
- Replan record and proposed decision 0008, the statement that 10 m and 30 m bodies have no interior pixel at 20 m: `corrected with evidence`. [Finding 18](../measurements.md#18-pixel-classes-per-size-class-and-lakes-outside-the-chosen-tile) shows 10 of the 30 pilot lakes inside their tile have none at 20 m, and a 30 m body can hold one.
- Replan record, the clipping caveat beside direction 4: carried into assumption A48 and the contract's `aerosol_mode` field as `unverified`.

## Proposed next step

Phase B, first step: research drafts and independent check records for the seven literature inputs and the three raw-data questions of the replan record. No provider script. Then stop for review.
Phase B, second step: the T1 script with fixture tests and a `--dry-run`, then the owner invokes the run. T1 reads headers only and needs no credentials, which the result must prove.
