# Discovery review and Prototyping handoff, 2026-09-11

Reviewer: Codex, with separate research and checking agents for two qualified scientific claims.

The latest Discovery presentation supports the intended audience and assessment goals after the corrections below.
Its four tabs, explanatory figures, expandable detail, and real satellite examples remain.
Later tabs stay placeholders. No workflow prototype, production design, or new provider read was started.

## Findings and dispositions

| Finding | Disposition |
|---|---|
| Archive prose again implied Collection 1 had no 2022 products and that historical ingestion definitively stopped | Fixed. Retained the corrected table. Scoped missing coverage to the measured period and explicitly labeled the proposed ingestion history as an inference |
| The two copies were described as sharing file names and every quality layer | Fixed. Shared catalog labels and sampled red-band metadata are distinguished from file or pixel identity. Quality availability is limited to measured layers |
| Small-pond pixel counts and cloud or terrain effects were too absolute | Fixed. Qualified grid-alignment examples and conditional scientific effects. Separate agents checked ESA documentation and the cited terrain study |
| Retry wording contradicted immutable publications | Fixed. Retries preserve existing records and availability times. Changed geometry or processing creates a revision. Exact identity remains prototype design work |
| The example sensing time came from the item name rather than the observation metadata | Fixed. The renderer now supplies the sensing time from map provenance. Illustrative row values are labeled |
| Map prose disagreed with denominator screening and asserted an untested cause of image texture | Fixed. Described the implemented threshold and clipping. Texture attribution remains unverified. Rebuilt provenance from cached arrays |
| Active assumptions, the fallback candidate, and historical route wording disagreed | Fixed. [Decision 0004](../decisions/0004-cog-fallback-and-presentation-clarifications.md) consolidates existing owner direction and identifies the superseded fallback provision |
| Assumptions still called the sensor rationale unconfirmed and the hosting note implied a deployment | Fixed. Linked the owner's recorded rationale. Hosting is prepared, with no deployment recorded |
| Current-phase notes mixed historical review steps with the next work | Fixed. README, CLAUDE, and the work plan point to the Phase 2 handoff |

The [owner's second review](2026-09-11-owner-review-round-two.md) remains the basis for page structure and terminology.
This review supersedes stale pending-decision wording in earlier reviews. Historical records and survey result files remain intact.

## Evidence and limits

- [Gap survey report](2026-09-10-gap-survey-report.json) and [measurements](../measurements.md) support archive counts and limitations.
- [Presentation source checks](../assessment-checks/discovery-presentation-sources.json) record the independent cloud-dilation and terrain-error checks.
- [Map provenance](../assets/discovery/provenance.json) supplies the example time, recipes, and image digests.
- This review reconciles current documents with existing evidence. It does not refresh every vendor claim or establish current global archive completeness.
- Pixel equivalence between archives, offset interpretation for fallback assets, cross-tile consistency, runtime, and costs remain unmeasured.
- Effort bars remain explicitly unverified judgments. The stored-row illustration remains a candidate layout.

## Verification

- `uv sync --locked`: passed.
- `uv run ruff check .`: passed. `uv run ruff format --check .`: 50 files already formatted.
- `uv run pytest -q`: 70 passed in 0.28 seconds, including document links, inventory consistency, and generated-file checks.
- `git diff --check`: passed. No staged changes existed or were added.
- Local Chromium: four tabs, keyboard navigation, and all six choices in both map selectors passed without browser errors.
- Page width stayed within the viewport at 390, 768, and 1024 pixels. Desktop and map screenshots were inspected.
- Offline map regeneration preserved all six image hashes and image statistics. Provenance records the updated builder hash.

## Next session

Begin Phase 2 using the [work-plan handoff](../work-plan.md#next-session-phase-2-prototyping).
Agree the first bounded comparison together, using public pilot polygons and the modeling team's input-product requirements.
Use experiments to resolve the open choices. No complete processing workflow or infrastructure design is required before that discussion.
Remaining choices include fill policy, missing quality layers, Alaska scope, processing-version comparability, and record layout.
Committing, publishing, and deploying remain separate actions. No deployment is a prerequisite for prototype planning.
