# Gap survey: plan, script, measurements, findings, and fill-policy options, 2026-09-10

Reviewer: Claude Code (AI coding agent), directed by the repository owner. Step: 3a in [work-plan.md](../work-plan.md), required by [decision 0003](../decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md).
Baseline: commit `943bb1b` plus this step's uncommitted changes. This is an AI record of work. Owner acceptance is separate.

## What this step delivered

- [gap-survey-plan.md](../gap-survey-plan.md): question, bounds, sites, collections, gap definitions, consistency checks, outputs, and rerun steps.
- [benchmarks/gap_survey.py](../../benchmarks/gap_survey.py) and [benchmarks/gap-survey-sites.json](../../benchmarks/gap-survey-sites.json). Standard library only. Catalog metadata only.
- [benchmarks/results/gap-survey.json](../../benchmarks/results/gap-survey.json), one run on 2026-09-10. 900 requests, no imagery.
- [tests/test_gap_survey.py](../../tests/test_gap_survey.py): seven fixture tests of the survey logic. No network.
- [benchmarks/fallback_survey.py](../../benchmarks/fallback_survey.py) and [benchmarks/results/fallback-survey.json](../../benchmarks/results/fallback-survey.json), one run on 2026-09-11 UTC, added on the owner's instruction. 870 requests, headers only on the bucket, no pixel.
- [tools/gap_report.py](../../tools/gap_report.py) and the generated [gap survey report](2026-09-10-gap-survey-report.json), machine-readable, for Codex review. [tests/test_gap_report.py](../../tests/test_gap_report.py) keeps it current. [tests/test_fallback_survey.py](../../tests/test_fallback_survey.py) covers the asset logic.
- [measurements.md](../measurements.md): both runs, two per-tile tables, twelve findings, and what the surveys do not show.
- Probes PR-05 and PR-06 in the inventory. Issues I-05, I-08, I-16, I-25, I-26, I-29, and I-30 updated with the measured evidence. HTML regenerated.
- Pointers added in [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), [benchmarks/README.md](../../benchmarks/README.md), [assumptions.md](../assumptions.md) row A10, [data-contract.md](../data-contract.md), and practice P9.

## How the survey was run

The script ran once, invoked by the agent under the owner's instruction to proceed with the gap survey. A one-site smoke run preceded it and wrote outside the repository.
Two kinds of bounded probe ran beside the script, against the same public endpoints. Catalog checks shaped the script before the run. PR-06 ran after it.
No script or probe read imagery, listed a bucket, or used credentials. Every request the script made is in the result file's request log.

## Checks

- The check workflow and both `--check` tools. Outcomes are in the table at the end of this document.
- Inside the survey: 120 of 120 aggregation-versus-listing checks agree. Copernicus OData and STAC counts agree within 25 products of 27,726.

## Findings that change the picture

Numbers live in [measurements.md](../measurements.md). This list says what each finding means for the plan.

- **GS-01. The 2022 gap is global and is the route's, not ESA's.** Collection 1 is nearly empty from January to November 2022 in all 30 tiles. Six months are empty everywhere and no month is complete anywhere. The tiles span three continents. ESA serves 2022 at baseline 05.10. The older collection covers the year with 03.01 and 04.00 originals.
- **GS-02. Collection 1 is not ESA Collection 1 for December 2022 to December 2023.** It holds 05.09 originals where ESA serves 05.10 reprocessings. Acquisition counts match, products do not. The README's phrase "at least baseline 5.0" describes this.
- **GS-03. One Alaska tile is on no Earth Search collection for 1,162 acquisitions and 52 months.** Collection 1 holds one December 2022 item there. Sustained coverage begins in June 2025. This meets the first review trigger of decision 0003 for that tile, if Alaska is in scope.
- **GS-04. The pre-Collection 1 collection is three months of late 2022 and covers no surveyed United States tile.** It is not a fallback.
- **GS-05. The offset flag cannot be trusted from metadata.** In the older collection it varies per item within one baseline. For most 04.00 items it contradicts the asset's declared offset. Collection 1 items carry no flag.
- **GS-06. The 2022 fallback items carry no cloud or snow probability.** Quality assets follow the provider's ingestion software version, not only the collection.
- **GS-07. The older collection keeps originals beside reprocessings. Collection 1 keeps one product per acquisition key, except same-day splits and one mixed-baseline pair.** A date and platform key does not identify one product. Practice P9 expects a route to delete superseded products. That holds for Collection 1 and not for the older collection.
- **GS-08. Seven of 20 sites lie in two to four tiles.** Every acquisition there arrives as several products. Cross-tile handling, issue I-30, is not an edge case.
- **GS-09. Tile counts overstate coverage at a point.** One tile logged 142 acquisitions in a year while 87 footprints covered the site point. Per-water-body coverage must be measured on footprints, not tiles.

## Fallback survey, added on the owner's instruction

The owner read the correction below and asked for a second survey. It treats the older collection's GeoTIFFs as the fallback. The owner also asked for a machine-readable report for Codex. Numbers are in findings 10 to 12 of [measurements.md](../measurements.md).

- **GS-10. The older collection's GeoTIFFs cover the missing 2022 acquisitions.** Outside the absent Alaska tile, all but 20 missing acquisitions have a complete GeoTIFF set. Aerosol and water vapour are included. Five have JPEG 2000 only and 15 have nothing. The items are 03.01 and 04.00 originals with a mixed offset flag and no cloud or snow probability.
- **GS-11. Sampled objects exist and answer unsigned requests.** 702 HEAD requests on 351 items all returned 200 with sizes, and no request-charged header. Existence and size only.
- **GS-12. The two surveys agree.** Missing and covered counts match in all 405 tile-months.

The [report](2026-09-10-gap-survey-report.json) carries every finding with its numbers, the JSON paths they come from, the issues they bear on, and a review question each. `uv run python tools/gap_report.py --check` confirms the committed report matches the result files.

## Corrections to earlier statements

- Decision 0003 and assumption A13 call the fallback "the older collection's JPEG 2000 assets". The older collection's primary assets are cloud-optimized GeoTIFFs in the public `sentinel-cogs` bucket, with JPEG 2000 alternates. The inventory claim on format already said so. The wording of A13 is for the owner to amend in the next decision.
- Issue I-08 said the README named the 2022 gap as of April 2024. It is now measured, global, and dated to the run.
- The discovery response described the pre-Collection 1 collection as "baseline below 05.00". Measured, it is 35,018 items from three months of 2022.

## Fill policy options for the owner

Each gap gets its own decision. The options are the agent's proposal. The owner decides, and decision 0004 records it.

### Gap A: January to November 2022, every tile

| Option | What it means | Cost and risk |
|---|---|---|
| A1. Fill from the older collection's GeoTIFF assets | 03.01 originals to 2022-01-24, then 04.00 originals. Same route, available now, objects confirmed by HEAD, GS-10 and GS-11 | Different processing from the rest of the history. Offset state unknown until a pixel check, GS-05. No cloud or snow probability, GS-06. Items before 2022-01-25 have no offset, items after do. Five January 2022 acquisitions are JPEG 2000 only |
| A2. Leave 2022 empty and backfill when the route ingests the 05.10 reprocessing | Store records the months as absent. A later backfill lands as a new revision under practice P9 | Timing unknown. The provider's README says so. A model trained without 2022 |
| A3. Fetch ESA's 05.10 products for 2022 from the Copernicus catalog once | A bounded, one-year exception to the route | Contradicts decision 0003 unless the owner records the exception. Needs credentials and egress from a non-AWS store. Context only under A13 |
| A4. Start the 2021 scenario at 2023 and treat 2021 as an isolated year | No fill | Loses a year of the five |

Proposal: A1 as a labelled provisional fill, keyed by baseline, after the pixel check in Gap E passes. A2 as the standing rule, so the 05.10 backfill replaces the provisional rows as a revision. The store's `refinement_status` and baseline fields already distinguish them.

### Gap B: December 2022 to December 2023 at 05.09 instead of 05.10

| Option | What it means | Cost and risk |
|---|---|---|
| B1. Accept the route's 05.09 products | Consistent within the year. Available now | Differs from ESA's current archive. The 05.09 to 05.10 differences are not assessed in this repository |
| B2. Treat as Gap A | Wait for, or fetch, the 05.10 reprocessing | The provider holds items already and may never re-ingest. Fetching is option A3 |

Proposal: B1, with the baseline recorded on every row and a follow-up recheck of the 05.10 release note against claim R5 before prototyping analysis.

### Gap C: tile 05VLG, and any other tile absent from the route

| Option | What it means |
|---|---|
| C1. Confirm whether Alaska water bodies are in scope | If not, record it in the decision and move on |
| C2. If in scope, survey the tiles the customer set touches | Tile ids can be derived in-house from the customer polygons. Tile ids are not customer data. The survey script accepts a tile list |
| C3. For absent tiles, decide between exclusion and a non-route source | A non-route source reopens decision 0003 for those tiles only |

### Gap D: 15 single acquisitions on no Earth Search collection

Record them as absent in the store's missingness fields. No practical fill exists on the route. Rerun the survey before backfill to see whether the provider has filled them.

### Gap E: the offset flag, a blocker for A1

Not a gap. A prototyping measurement. Read one 60 m band window from a GeoTIFF and from its JPEG 2000 alternate, for a flag-true and a flag-false 04.00 item. Compare the digital numbers.
A few megabytes per item. It settles whether the flag or the `raster:bands` offset describes the pixels. Issue I-05 carries it.

## Dispositions of the Codex gap survey review, 2026-09-10

[Codex review](2026-09-10-codex-gap-survey-review.md). Every finding was accepted.

| Finding | Disposition |
|---|---|
| GR01 conclusions contradicted their numbers | fixed. Titles and review prompts in `tools/gap_report.py`, findings 1, 3, and 7 in measurements, GS-01, GS-03, and GS-07 above, and issues I-08 and I-16. Report regenerated. Collection 1's 2022 items stay in scope, and fallback eligibility is per missing acquisition |
| GR02 quality summary overwrote samples | fixed. The report now lists distinct quality-asset layouts with their sample ids and baselines. Software 2026.08.16 shows two layouts. Regression test added |
| GR03 no input compatibility check | fixed. The generator refuses a fallback result whose recorded digest or measured time differs from the gap result. It also refuses one whose tile-months differ from the months the gap survey marked incomplete. Regression tests added |
| GR04 hidden selection preference | corrected with documentation. The helper's docstring now states the asset-count preference and calls it a survey heuristic. Behaviour unchanged, so the result stays reproducible |
| GR05 retries missing from the log | fixed for future runs. Both scripts now log every attempt with its number. The two committed results predate the change, as their measurement rows say |

## Documentation consolidation, 2026-09-10

After the Codex review the owner asked for a pared-down document set before the HTML view is rebuilt. Step 3b in [work-plan.md](../work-plan.md).

- Archived to `docs/archive/`, ignored by git, with an index there: eleven files. They are the initialization review, the discovery review, the owner feedback response, and the four Codex discovery-cycle documents. Also the executed discovery plan, the development workflow, the assessment protocol, and the document index. Their outcomes live in decisions 0001 to 0003, the inventory, CLAUDE.md, work-plan.md, and README.md.
- Folded: the workflow into CLAUDE.md, the assessment criteria and cost formula into work-plan.md, the document index into README.md.
- Pared: the two per-tile tables left measurements.md for the report's `per_tile` list. Steps 0 and 1 of the work plan are two lines each.
- Repaired: every link to an archived file. The link test skips the archive. The check workflow passes.
- Retained as evidence, not prose: the inventory, the check records, the survey results, the probe record, and the supplied reference.

## Proposed next step

1. Rebuild the HTML view from scratch, step 3c in [work-plan.md](../work-plan.md), with owner, Codex, and Claude Code review.
2. The owner records decision 0004: the fill policy per gap, the A13 wording, and whether Alaska is in scope.
3. The owner selects the workflow, platform, and layout to prototype, the open item in step 2 of the work plan.
4. Prototyping begins with two added probes: the offset pixel check of Gap E, and the 05.10 release note recheck of Gap B.

The pilot manifest, once derived, triggers a rerun of the survey on its tiles. That rerun is a step 3 deliverable.

## Limits of this record

Each survey is one run of one script against catalogs that keep changing. The sites are public points, not the customer set. Neither read a pixel.
The proposals above are the agent's reading of the evidence. They are not owner or engineering decisions. Codex has not reviewed this step.

## Check outcomes

Run on 2026-09-10 after the last edit of this step. The same commands run in CI, [.github/workflows/ci.yml](../../.github/workflows/ci.yml).

| Command | Outcome |
|---|---|
| `uv sync --locked` | Pinned environment resolved, 6 packages |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 42 files already formatted |
| `uv run pytest` | 55 passed, 7 of them the new survey fixture tests |
| `uv run python tools/collate_checks.py --check` | Inventory matches the check records |
| `uv run python tools/render_options.py --check` | HTML matches the inventory |
| `uv run python tools/gap_report.py --check` | Report matches the survey results |
