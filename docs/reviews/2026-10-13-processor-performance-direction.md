# Owner direction on processor performance recorded, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered, awaiting owner review. No provider script ran. No pixel was read. Nothing is committed.

## Step and authorization

After the [Phase B validation review](2026-10-13-phase-b-claim-validation.md), the owner gave this direction on 2026-10-13:

> "Let's hold off on forming a strong opinion on sen2cor vs acolite in terms of performance modeling water quality until we run our own experiments. In the meantime, we can defer to authority with the assumption that acolite is optimized for this purpose and is our initial primary resource"

This step records the direction where the documents state the basis of decision 0008. It changes no provision and starts no phase.
Acceptance checks: the direction has one home, every changed document links to it, and `/check` passes.

## What changed

| File | Change |
|---|---|
| [replan record](2026-10-13-acolite-first-replan.md#owner-direction-on-processor-performance-2026-10-13) | New section quoting the direction verbatim. The record owns the owner's directions. |
| [assumptions.md](../assumptions.md) | New row A52. ACOLITE is treated as designed for water. The assessment forms no view on relative performance until the company's own experiments. |
| [decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) | New section on the basis. The evidence note now points to the owner's answer. A new review trigger fires when the experiments compare the two corrections. |
| [work-plan.md](../work-plan.md) | The Phase D owner decision now asks where the experiments run and against which reference. |
| [CLAUDE.md](../../CLAUDE.md) | One convention line pointing to A52, so agents form no view on relative performance. |
| `tools/s2-options.template.html` and the [presentation](../s2-options.html) | The correction risk now states the assumption. It replaces "The choice rests on design intent and availability, not on a measured advantage." |
| [options-inventory.json](../options-inventory.json) | Issue I-31's consequence states the same assumption and cites A52. No claim changed. |

## Evidence

`/check` on 2026-10-13: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q` passed, 344 tests in 34.59 s.
The supervisor test that failed under load in the [validation review](2026-10-13-phase-b-claim-validation.md) passed in this run.
The page was regenerated. The collation, sensor band, page, gap report, and review-layer `--check` commands report current.
A style scan of the added lines found no semicolon and no forbidden modal verb. The only sentence over 25 words is the verbatim quote.

## Limits

- No checked claim states ACOLITE's design purpose. A52 rests on the owner's direction. The documented fact is that USGS publishes the output as water-leaving reflectance.
- The validation review found that the delivered bands may not be ACOLITE's own water-leaving reflectance, finding 29. A52 does not settle that question.
- The literature claims W5 to W8 and practice P16 are unchanged. They report the studies and form no view.
- Where the experiments run is open. They may belong to this assessment or to the modeling project. Assumption A15 keeps validation against field data out of this assessment.

## Dispositions of prior findings

- Validation review, the open owner decision on an accuracy comparison: `corrected with evidence`. The owner's direction defers the comparative judgment to the company's own experiments. Their location stays open.
- Replan record, the claim that studies rank Sen2Cor behind ACOLITE: already `corrected with evidence` by the validation review. Unchanged.

## Proposed next step

Phase C, first step: probe T4, validity per band and pixel class on the pilot lakes, with tolerances declared first. It reads pixels and needs owner authorization.
