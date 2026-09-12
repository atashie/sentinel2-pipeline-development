# Codex gap survey review, 2026-09-10

Reviewer: Codex, an AI coding agent. Scope: the gap survey, COG fallback survey, generated report, tests, and proposed next step.

The evidence supports developing a bounded prototype with the older collection's public COGs as a fallback.
The main counts reproduce from the saved catalog listings. The report needs the corrections below before its conclusions become implementation guidance.
The existing offset check, polygon coverage checks, and cross-tile investigation belong in the prototype.

This review preserves the Earth Search route and 2021-first direction of [decision 0003](../decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md).
It reviews the owner's additional COG fallback survey. It does not select a production architecture or start implementation.

## Evidence independently checked

I read both survey scripts, [gap_report.py](../../tools/gap_report.py), their tests, and the [generated report](2026-09-10-gap-survey-report.json).
I also checked [measurements.md](../measurements.md), the [plan](../gap-survey-plan.md), and the relevant probe and decision records.

Offline diagnostics verified all 180 saved raw-file digests. The fallback survey's input digest matches the first survey's result.
I independently recomputed the reference, primary, missing, covered, and uncovered counts for all 2,070 tile-months. None differed from the first survey.
I also reclassified the fallback assets from their saved catalog entries:

| Missing acquisition keys across the surveyed tiles | Count |
|---|---:|
| Complete COG asset list: twelve reflectance bands plus SCL | 3,840 |
| Partial COG asset list | 0 |
| JP2 only | 5 |
| No older-collection item | 1,177 |
| Total | 5,022 |

Of the 1,177 uncovered keys, 1,162 belong to 05VLG and 15 to the other surveyed tiles.
None of those uncovered keys appears in the saved pre-Collection 1 or Level-1C listings either.
The 405 compared tile-months agree between surveys.
The saved HEAD records contain 702 successful responses for two assets on each of 351 sampled items.

These are tile/date/platform keys and catalog asset lists. They are not counts of validated lake observations.
The report correctly limits HEAD evidence to existence and headers. No catalog query, bucket request, or pixel read ran during this review.

## Corrections before using the report as guidance

### GR01. Several conclusions contradict their own measured numbers

**Priority: high. Locations: GS-01, GS-03, GS-07, their prose summaries, and the generator's fixed text.**

- **GS-01:** January through November 2022 is severely incomplete, rather than absent everywhere.
  Only six months are empty in all 30 surveyed tiles. In March, 27 tiles contain an acquisition.
  Global monthly counts are also nonzero: 676 to 40,798 during those eleven months.
  Preserve existing Collection 1 items and describe fallback eligibility using missing keys, not a blanket empty-year assumption.
- **GS-03:** 05VLG has one Collection 1 acquisition in December 2022, before sustained coverage begins in June 2025.
  Its first recorded month is `2022-12`. Correct the claim that every collection is empty there before June 2025.
- **GS-07:** Collection 1 has 22,501 items for 21,873 acquisition keys, including 628 duplicate groups.
  It therefore does not keep one product per acquisition under the survey's definition.
  One group even mixes baselines: tile 32TLS, `2023-10-23/a`, with 05.09 and 05.11 products.
  Both source product identifiers are present in the saved listing.

The last point matters directly to implementation. A date/platform key is useful for this survey but cannot safely identify one stored product.
Keep product identity and the documented split-granule limitation when translating coverage counts into ingestion work.

Correct the text in the generator and regenerate the report. Updating the generated JSON alone would leave the error in the next run.
The fixed `for_review` text also needs attention: GS-10 asks to confirm only complete COG or uncovered categories, despite the five JP2-only cases.

### GR02. The quality summary overwrites differences between samples

**Priority: medium. Location: [gap_report.py](../../tools/gap_report.py), lines 137–150, GS-06.**

The grouping key contains collection and software version. Each new sample replaces the group's quality assets, hosts, and requester-pays value.
The baselines accumulate, but the asset description comes from the last sample only.

This affects the current data. Software `2026.08.16` has both COG-backed and JP2-only samples.
For example, `S2B_15RYP_20220107_0_L2A` has its SCL in the JP2 bucket, while other samples have SCL COGs.
The report gives all nine baselines one shared description. Reversing the sample order changes that description.

Preserve distinct observed asset layouts with their sample identifiers and baselines. Do not infer one layout from software version alone.
The underlying samples and fallback classification counts remain useful.

### GR03. The freshness check does not validate that the inputs belong together

**Priority: medium. Locations: `build()` in [gap_report.py](../../tools/gap_report.py) and [test_gap_report.py](../../tests/test_gap_report.py).**

The current input pair matches, but the generator never checks the fallback result's recorded source digest against the gap result.
It also compares only tile-months present in the fallback result, without checking that every required tile-month is included.

Two in-memory diagnostics exposed this:

- Replacing the fallback input digest with 64 zeroes still produced a report.
- Removing fallback tile 10SGJ reduced GS-12 to 393 comparisons with no reported disagreements.

Validate the source digest and expected incomplete tile-month set before generating the combined report.
The existing test establishes reproducibility of the rendered report, not compatibility or completeness of its evidence.
Add focused regression cases for these failures and the mixed quality layouts in GR02.

### GR04. The fallback selection helper hides an extra priority

**Priority: medium for reuse in implementation. Location: `best_item()` in [fallback_survey.py](../../benchmarks/fallback_survey.py), lines 134–146.**

The helper says it prefers a complete COG set, then the highest baseline.
Its actual order is completeness, total COG asset count, then baseline.
A complete older product with an extra COG asset can beat a complete newer product.
An offline fixture confirmed that behavior.

Align the implementation with the stated survey rule, or document the extra preference explicitly.
Keep this selection a survey heuristic until the fill policy defines product selection.
It does not resolve which split granule covers a water body, and its selected-item metadata is not a validated ingestion manifest.

### GR05. Retry attempts are missing from the request log

**Priority: low. Locations: `Client.get_json()` and `head()` in the survey scripts.**

Retries increment request counters and then continue before appending a log entry.
The first result records 900 attempts but only 898 log entries: one missing attempt at Earth Search and one at Copernicus STAC.
Response bytes from failed attempts are also excluded from the recorded byte totals.

Record every attempt on future runs and qualify the current log's completeness.
This does not change the acquisition counts. It matters when the same accounting is later used for reliability and cost analysis.

## Implications for the next step

The survey supports the COG fallback option for the observed missing keys, subject to the following existing limits:

- **Conversion:** the 04.00 samples contain both flag states while declaring the same nonzero asset offset.
  The provider documents conversion per asset in its [offset guidance](https://raw.githubusercontent.com/Element84/earth-search/main/README.md).
  Keep the planned COG/JP2 pixel comparison before using derived reflectance. Its conclusions apply to the sampled assets and processing states.
- **Quality:** `complete_cog` covers reflectance bands and SCL. It does not mean all layers in assumption A3 are present.
  The selected fallback items lack cloud/snow probability in 3,833 cases and expose it as JP2 in 12.
  Preserve missing quality layers explicitly. Record the five JP2-only acquisition cases in the fill options.
- **Spatial coverage:** a matching tile/date/platform key does not establish valid pixels inside the chosen water body.
  The planned polygon-based prototype can evaluate that. Preserve distinct tile and product records during the cross-tile investigation.
- **Scope:** update the active fallback wording to reflect the owner's COG direction.
  The route remains Earth Search. The specific treatment of JP2-only cases and uncovered keys remains a fill-policy choice.

The saved evidence is sufficient to correct the report without another live survey.
After those corrections, I recommend proceeding to the bounded prototype and its already identified measurements.
The survey does not yet establish a complete, scientifically validated fill policy.

## Verification and changes

`uv run python tools/gap_report.py --check` passed. The report matches its inputs despite the semantic problems above.
The offline digest, counting, and mutation diagnostics ran with Python against saved files and in-memory copies.
No evidence result was edited.

Only this review and its [index entry](README.md) were added.
The [required check workflow](../../.claude/skills/check/SKILL.md) passed:

| Command | Outcome |
|---|---|
| `uv sync --locked` | Passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run pytest -q` | 61 passed in 0.23 seconds |

The tests include report, inventory, and HTML freshness checks. Their success does not resolve the review findings.
