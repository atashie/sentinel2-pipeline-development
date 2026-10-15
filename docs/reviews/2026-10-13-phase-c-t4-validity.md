# Phase C, step 1: probe T4, pixel validity on the pilot lakes, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered, committed as `ddbaebf` on the owner's instruction of 2026-10-14. The owner decided the masking question on 2026-10-14 and deferred the join, decision 0009. Awaiting further review.

## For the owner

- Inside the product's scene, every pilot-lake pixel holds a value in every band, shoreline and near-land included. No pixel class is masked by the processor.
- The only no-data pixels are those ACOLITE flags out of scene. Almost all lie in one Lake Washington scene where the join matched two Level-2A items.
- The replan record's rule takes shoreline and near-land values from Level-2A only if the processor masks them. They stay with the primary product. The owner confirmed this on 2026-10-14.
- In both scenes with two Level-2A matches, the join took the other datastrip's item. The owner then deferred the join, decision 0009.
- NDWI matches the normalized difference of the delivered B03 and B8A, times 10,000, on 96 to 100 percent of comparable observations.
- ACOLITE sets no flag on 74 percent of interior pixels the Level-2A scene classification calls shadow, and on 7 percent of those it calls cloud. ACOLITE has no shadow test.
- Sentinel-2C scenes run a second settings variant. This adds to issue I-34 on the processor version.

## Step and authorization

The owner wrote "Hold off on committing for now. Proceed to phase c probe T4" on 2026-10-13. Probe T4 is defined in the [replan record](2026-10-13-acolite-first-replan.md).
This record reads the instruction as invoking T4, which reads pixels. It does not authorize T5 to T9, the join prototype, or the Prototyping tab rebuild.
Acceptance checks from the replan record, per test: declared tolerances, a result file, findings, and a record. All four hold, evidence below.
Deferred: T5 and the later Phase C steps, the Prototyping tab rebuild, and any change to decision 0008 or to the contract beyond answered questions.

## Rules declared before the read

The rules are `TOLERANCES` in [validity.py](../../src/s2proto/validity.py) and `tolerances` in the result. They were fixed before any pixel was read.
One shell command wrote the UTC time, `shasum -a 256` digests of the script and rule modules, and the `--dry-run` output to `data/aqr-validity/declared-before-run.txt`. The time is 2026-10-13T22:47:32+00:00.
The full run started at 22:48:25 UTC. Its recorded digests of the script and the rules module equal the declared ones.

| Rule | What it fixes |
|---|---|
| R1 | Grid. The classification window shares CRS, pixel size, and origin with the product within 1e-6 pixel, or the scene leaves every comparison |
| R2 | Flags decode only as exact multiples of 10,000. Other values are counted, never rounded |
| R3 | No-data where the classification holds data is processor-masked. A class counts as masked above 1 percent of its joined pixels in any band |
| R4 | Negative and above-one values per band and class. No tolerance |
| R5 | Water by NDWI above 0, by a clear non-water flag, and by classification class 6. Descriptive |
| R6 | Classification cloud, classes 8 to 10, and shadow, class 3, without any ACOLITE flag. Descriptive |
| R7 | NDWI recomputed from B03 with B08 or B8A, within the rounding of the stored integers. Diagnostic |

Scene selection, the join rule, and the tiles were fixed in the script at the same time. The tiles are stage 2's choices. A test checks them.

## What changed

| Area | Change |
|---|---|
| [aqr_validity.py](../../benchmarks/aqr_validity.py) | New probe script. Lists 2025 scenes, keeps the first complete scene per tile and month, joins the Level-2A item, and counts validity per lake, class, and band. Stores counts only. `--dry-run` and `--resummarize` contact nothing |
| [validity.py](../../src/s2proto/validity.py) | New pure module: the declared rules, flag decoding, per-class counting, pooling, and the rule R3 verdict |
| `tests/test_aqr_validity.py` | 15 fixture tests, no network. They cover each rule, the selection, the join choice, the grid check, the summary, the diagnostic, and the dry run |
| [aqr-validity.json](../../benchmarks/results/aqr-validity.json) | The result, written by the script |
| [measurements.md](../measurements.md#phase-c-probe-t4-pixel-validity-on-the-pilot-lakes-2026-10-13) | Findings 30 to 33 and what T4 does not show |
| [Inventory](../options-inventory.json) | Probe PR-12. Issue I-35 rewritten from the measurement, status `open` pending review. Issues I-32 and I-34 extended. No claim changed |
| [data-contract.md](../data-contract.md) | The masking question answered. `ndwi`, `mask_reason`, and `acolite_flags` cite the findings. The join note records two-item matches |
| Planning documents | [assumptions.md](../assumptions.md) A46, the [work plan](../work-plan.md), [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), and the [benchmark README](../../benchmarks/README.md) |
| [Presentation](../s2-options.html) | Regenerated. Only the issue I-35 line changed, through the inventory |

After the run, the summary gained a diagnostic outside the declared rules. It compares band no-data counts with out-of-scene flag counts and lists two-item joins.
`--resummarize` recomputed the summary offline at 23:11:13 UTC. The per-record counts are unchanged. The result keeps both the run-time and the summary-time source digests.

## Evidence

Provider contact, all unsigned, all under the owner's instruction:

| Run | Requests | Read |
|---|---|---|
| Smoke run, tile 17SKU, 2025-10, output under `data/aqr-validity/` | 4 bucket listings, 1 settings GET, 2 Earth Search searches, 55 GDAL ranges | One scene, 70 MB requested |
| Full run, `uv run python benchmarks/aqr_validity.py` | 79 bucket GETs, 118 Earth Search searches, 4,442 GDAL ranges | 59 scenes, 3.05 GB from the product, 13.1 MB of classification |

Payer: the bucket owners. Every logged request was unsigned and returned HTTP 200 on its first attempt. A requester-pays bucket refuses unsigned requests.
The product bucket is `usgs-wma-sentinel-2-aqr-acolite-dsf` and the classification bucket `e84-earth-search-sentinel-data`, both in us-west-2.
GDAL also opened one B05 header per tile to build the pixel grid, outside its request log. Those five opens are missing from the range counts.
The machine was the owner's laptop over the internet, assumption A25. The code version is `5806678-dirty`, because the probe was uncommitted when it ran.
Settings files and Earth Search items are saved under `data/aqr-validity/2026-10-13T224825+0000/`, outside git.

`/check` passed on 2026-10-13, 360 tests in 37.80 s.
It ran `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.
Pytest reported 13,000 warnings from a rasterio deprecation in earlier tests. The new test file alone raises none.
The collation, sensor-band, renderer, gap-report, and review-layer `--check` commands all report their outputs current.
A style scan of the added Markdown and inventory text found no semicolon and no forbidden modal verb. Only the owner's verbatim quotes exceed 25 words.

## What T4 found

[Findings 30 to 33](../measurements.md#phase-c-probe-t4-pixel-validity-on-the-pilot-lakes-2026-10-13) own the numbers. In short:

- 59 of 60 tile-months had a complete scene. All joined to a Collection 1 item of baseline 05.11, and every classification grid aligned.
- Rule R3's largest shares are 0.39 percent interior, 0.76 percent shoreline, and 0.88 percent near-land, all below 1 percent.
- Those observations lie in one Lake Washington scene, plus two pixels in one band of another. Two out-of-scene pixels there hold values in ten bands and NDWI.
- The flags layer never holds no-data, and every value read is a multiple of 10,000.
- Non-water flags cover 35 percent of interior, 77 percent of shoreline, and 92 percent of near-land observations. The mixed-pixel flag never occurs, though `l2w_mask_mixed=True`.
- B11 and B12 are negative in 20 and 14 percent of interior observations.
- NDWI agrees with B03 and B8A within rounding on 96 to 100 percent of comparable observations, and with B08 on 0.6 to 1.2 percent.

## Decision 0008 review triggers

[Decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) lists triggers for revisiting it. T4 bears on two:

- The product masks shoreline or near-land pixels: not met on the pilot lakes in 2025.
- The join fails for a material share of scenes: every 2025 scene joined to the same baseline. Two matched two items, and both choices took the other datastrip, finding 30. Whether that is material is the owner's call.

## Limits

- One year, 2025, five tiles, and one scene per tile and month. Earlier inputs are mostly original baselines with poorer joins, finding 28.
- Counts only. Where no-data covers a whole record, the counts prove the same pixels. Elsewhere, as for the two B04 pixels, they cannot.
- Rule R3's verdict holds pooled. Split by tile or size, Lake Washington's tile and every non-anchor size group pass 1 percent through the wrong-item scene alone.
- Finding 33's cloud shares include that scene. Without it, Lake Washington's unflagged share is 8.3 percent, not 6.0.
- The scene classification is a land product with its own errors. Water and cloud agreement shows where two products differ. It does not show which is right.
- Anchor lakes dominate pooled shares. Splits by tile and size class are in the result. Interior is a polygon class, and not every interior pixel is water.
- NHD shorelines are not observations of a given date. Some pilot ponds can hold no water on a scene date.
- Times and bytes are a laptop over the internet. They are not production estimates.
- This record and its findings are an AI agent's work, reviewed by tests only so far.

## Owner review, 2026-10-14

The owner wrote "masking rule: yes, same rule applies to acolite products" and asked for the two-item question to be explained.
Issue I-35 is now `decided`. Shoreline and near-land values and flags stay with the primary product.
Answering the second question found an error in this record. It said one two-item choice covered other pixels. Both choices took the item of the other datastrip.
The evidence came from saved files, with no new provider contact. Finding 30 owns it. No count changes, and rule R3's verdict holds.
In the Tahoe scene, the chosen classification holds no lake pixel, so finding 33 omits that scene. In the Washington scene, R3's count and R6's cloud shares depend on the wrong item.
The selection rule kept one of two Tahoe products of one pass, treating split datastrips as revisions. Finding 23 had already recorded that defect for Level-2A.
Later on 2026-10-14 the owner made each ACOLITE product standalone and deferred the join, [decision 0009](../decisions/0009-standalone-options-join-deferred.md). Both Tahoe products count as observations.

## Dispositions

| Item | Disposition |
|---|---|
| Phase B limit: no pixel test describes the primary product | Fixed. Findings 30 to 33. |
| Phase B carried item: processor masking at scale, and flags per band and class | Fixed. Finding 30 for masking, finding 31 for flags. |
| Issue I-35, status `measure` | Fixed. Measured and rewritten. The owner decided the consequence on 2026-10-14, status `decided`. |
| T4 join rule: the latest created item among several | Corrected with evidence. Wrong in both two-item scenes, finding 30. The join is deferred, decision 0009. |
| T4 selection rule: the latest generation among products of one sensing time | Corrected with evidence. Split datastrips are distinct coverage, finding 23. The counts hold. Decision 0009 keeps every product. |
| Phase B limit: the flag encoding is observed, not documented | Accepted and deferred. Observed on every pixel read. No USGS page documents it. |
| Finding 29: the delivered bands are an unnamed quantity | Accepted and deferred. NDWI matches the bands, finding 32. Which quantity both hold stays undocumented. |
| Processor-performance record: proposed next step T4 | Fixed. This step. |

## Proposed next step

Phase C, next step: probe T5, paired values from Collection 1 on the same tile-dates, with tolerances declared before any read.
T4's 59 scenes and windows can be reused. T5 reads Level-2A pixels, so it needs explicit owner authorization.
Decision 0009 defers the join and the two-source join prototype. The [direction record](2026-10-14-standalone-options-direction.md) proposes the next step.
