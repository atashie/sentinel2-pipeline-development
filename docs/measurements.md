# Measurements, 2026-09-10

Three measurement sets exist. The data gap survey required by [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md) ran once on 2026-09-10 and wrote [gap-survey.json](../benchmarks/results/gap-survey.json).
The fallback survey the owner asked for the same day ran once and wrote [fallback-survey.json](../benchmarks/results/fallback-survey.json). Both are summarized for review in the generated [gap survey report](reviews/2026-09-10-gap-survey-report.json).
The plan, definitions, and rerun steps are in [gap-survey-plan.md](gap-survey-plan.md). Every number in the survey sections is a count of catalog items, acquisitions, requests, or bytes, as labelled. The surveys read no imagery byte.
The third set is [prototype stage 1](#prototype-stage-1-raw-access-to-whole-tiles-2026-09-14), which read whole tiles on 2026-09-14.

An acquisition is one sensing date and platform within one tile. Item counts stand beside acquisition counts because one acquisition can appear as several items.

## The run

| Quantity | Value |
|---|---|
| Measured at | 2026-09-10T20:16:28+00:00 |
| Sites and tiles | 20 sites in [gap-survey-sites.json](../benchmarks/gap-survey-sites.json). 30 tiles found from Collection 1 footprints covering the site points |
| Window | 2021-01-01 to 2026-09-10, 69 months |
| Requests made | 900: 539 to Earth Search, 181 to the Copernicus STAC, 180 to the Copernicus OData catalog. 898 answered on the logged attempt, 2 were retried |
| Bytes received | 51,381,575 from Earth Search, 10,014,295 from the Copernicus STAC, 382,789 from OData. Catalog JSON only. Imagery bytes: 0 |
| Payer | The provider, for every request. No credentials. No requester-pays bucket was touched. Collection 1 items declare `storage:requester_pays` false |
| Code version | Commit 943bb1b plus uncommitted changes, because the script was new at run time. The committed script differs from the one that ran in one way: it now logs every retried attempt, Codex finding GR05. No count changes |

Consistency checks: all 120 aggregation-versus-listing checks agree, one per tile and collection. The Copernicus OData and STAC counts agree for 15 of 30 tiles.
In the other 15 they differ by one or two products in a year, 25 products of 27,726. No listed item carried a wrong tile code. No item fell outside the window.

## Per-tile results

Reference means the Copernicus STAC listing, what ESA serves today. Missing means reference acquisitions absent from Collection 1. Covered means the older Earth Search collection holds the missing acquisition. Uncovered means no Earth Search collection holds it.
The 30 per-tile rows are the `per_tile` list of the [report](reviews/2026-09-10-gap-survey-report.json). Totals over the 29 tiles outside Alaska: 25,358 reference acquisitions, 21,526 in Collection 1, 3,860 missing, 3,845 covered by the older collection, 15 uncovered.

## Archive history: measurements and inferred explanation

**Inference, not a documented ingestion history:** the newer collection's holdings are consistent with two publication streams.
One carries operational products for acquisitions from late 2022 onward. The other backfills ESA's historical reprocessing.
The survey found reprocessed 2021 products, severely incomplete 2022 coverage, and predominantly unrevised 05.09 products for 2023.
This pattern suggests an incomplete historical update. It does not establish Element 84's internal jobs, intentions, or why updates are missing.

The table separates ESA's processing history from the catalog holdings measured on 2026-09-10.
Its counts cover all 30 surveyed tiles and refer to product items, not distinct acquisitions or usable lake observations.
The survey begins in 2021. ESA's reprocessing extends to 2015, but this survey does not establish either archive's 2015–2020 holdings.

| Acquisition period | Operational processing then | Later ESA reprocessing | Older Earth Search collection | Earth Search Collection 1 |
|---|---|---|---|---|
| 2021 | 02.x to 03.x | 05.00, with 05.11 used for a few historical products | Originals beside 05.00 versions | All sampled 2021 items are 05.00 |
| January–November 2022 | 03.01, then 04.00 from 2022-01-25 | Mainly 05.10, with a few 05.11 products | Mainly 03.01 and 04.00. Also 37 at 05.10, 5 at 05.11, and 6 at 05.09 | 45 items: 37 at 05.10, 5 at 05.11, and 3 at 05.09 |
| December 2022–December 2023 | 04.00 initially. 05.09 from 2022-12-06. 05.10 from 2023-12-13 | Mainly 05.10 for history through 2023-12-13, with a few 05.11 products | Mainly 05.09, plus early December 2022 at 04.00 and some 05.10 and 05.11 | Mainly 05.09. The 2023 subset has 4,036 at 05.09, 221 at 05.10, and 20 at 05.11 |
| 2024–2026, through the survey date | 05.10 and later. Some Sentinel-2C commissioning products used 99.xx | A bounded Sentinel-2C campaign reprocessed late-2024 tandem acquisitions to 05.11 | Recent products present, with multiple baselines | Recent products present, with multiple baselines |

For all of 2022, the newer collection has 348 items representing 340 acquisition keys. December accounts for 303 items and 295 keys.
The 2022 reference has 4,558 items, including 4,550 at 05.10. The newer collection's 348 items include 305 at 05.09.
These counts compare holdings, not identical copies of the reprocessed reference products.
The figure 384 belongs to the fallback survey's incomplete tile-months across its full window, not January–November or all of 2022.

**Measured evidence:** [gap-survey.json](../benchmarks/results/gap-survey.json), `tiles.<tile>.earth_search.<collection>.items`, `acquisitions`, and `baselines`, summed over the stated months.
Findings 1, 2, 4, and 7 below describe the coverage, baseline mixtures, bridge collection, and duplicate products.
**Documented context:** [ESA processing history](https://sentiwiki.copernicus.eu/web/s2-processing), [05.09 deployment](https://sentinels.copernicus.eu/documents/d/sentinel/ompc-cs-dqr-002-03-2023-i60r0-msi-l2a-dqr-april-2023), and [the completed Sentinel-2C tandem campaign](https://dataspace.copernicus.eu/news/2026-9-2-copernicus-sentinel-2c-tandem-data-reprocessing-campaign-completed).
The last announcement establishes CDSE availability, not AWS replication. Context sources were independently checked on 2026-09-11, [check record](assessment-checks/discovery-presentation-sources.json).

The [Earth Search README](https://github.com/Element84/earth-search/blob/main/README.md) attributed missing history to incomplete ESA reprocessing as of April 2024.
ESA has since completed the historical reprocessing. The survey also finds those reprocessed products in the reference catalog.
The remaining gap is downstream of ESA production. These measurements cannot distinguish missing copying, conversion, or catalog indexing.
The small pre-Collection 1 collection and retained 05.09 products are consistent with the inferred history, but do not prove its cause.

Among the proposed plans, Plan B adds substantial 2022 coverage for the surveyed US tiles while keeping Collection 1 primary.
It leaves some gaps and does not establish value comparability. Source-selection and offset-validation questions remain open.
The [Discovery page](s2-options.html#archive-history) presents this explanation with an expandable table.

## Findings

### 1. Collection 1 is nearly empty from January to November 2022 in every tile, and the shape is global

Six months are empty in all 30 tiles: 2022-01, 2022-02, 2022-04, 2022-05, 2022-09, and 2022-11. No 2022 month is complete in any tile. In 2022-03, 27 tiles hold exactly one acquisition at baseline 05.10 and 3 hold none.
From 2022-06 to 2022-10, at most 3 tiles hold a single acquisition in any month. December 2022 is partial in all 30 tiles: Collection 1 items resume at baseline 05.09 after the last 04.00 item on 2022-12-05.
The few Collection 1 items inside 2022 are real and stay in scope. Fallback eligibility is decided per missing acquisition, never per month.

The whole collection shows the same shape. Its monthly item counts from 2022-01 to 2022-11 run from 676 to 2,816, except 40,798 in 2022-03. Other months outside 2022 range from 152,138 to 487,234 items. That range includes the partial September 2026 window, as reported in GS-01.
Probe PR-06 in the [probe record](assessment-checks/probes-2026-09-10.json) shows the same months near zero over Alaska, Hawaii, and a northern plains box.

ESA lists 2022 for these tiles at baseline 05.10, 4,550 of 4,558 reference items, generated in 2024. The gap is therefore in the route's ingestion, not in ESA's production.

Over the 29 tiles outside Alaska, 2022 has 4,196 reference acquisitions. Collection 1 holds 339. Of the 3,857 missing, the older collection covers 3,842 and 15 are on no Earth Search collection.
The 15 uncovered acquisitions are single dates spread over 12 tiles, all in 2022. They are listed per tile under `uncovered_keys` in the result file.

The older collection's 2022 items in those 29 tiles carry five baselines. 03.01 has 284 items, 2022-01-01 to 2022-01-24. 04.00 has 3,717 items, 2022-01-25 to 2022-12-05. 05.09 has 308, 05.10 has 37, and 05.11 has 5.
So a fill from the older collection means pre-Collection 1 originals. Items before 2022-01-25 predate the radiometric offset of claim R1. Items from that date carry it.

### 2. Collection 1 holds baseline 05.09 originals from December 2022 to December 2023, where ESA now serves 05.10

In the 29 tiles outside Alaska, Collection 1 items sensed in 2023 carry baselines 05.09 (4,036 items), 05.10 (221), and 05.11 (20). The reference carries 05.10 (4,258) and 05.11 (20).
December 2022 shows the same: 302 Collection 1 items at 05.09 against 362 reference items at 05.10. Acquisition counts match, so those months read as complete, but the products differ.

Claim R2 in [s2-best-practices.md](s2-best-practices.md) records that ESA removed products before 13 December 2023 that predate the reprocessing. The route's 2023 products are therefore ones ESA no longer distributes.
Measured baseline spans in Collection 1: 05.00 for 2021, 05.09 to 2023-12-12, 05.10 from 2023-12-13 to 2024-07-22, 05.11 to 2026-02-03, and 05.12 from 2026-02-04. A few earlier 05.10 and 05.11 items sit inside 2022.

### 3. One Alaska tile is absent from the older and Level-1C collections, and nearly absent from Collection 1 before June 2025

Tile 05VLG, at Lake Iliamna, has 1,507 reference acquisitions. Collection 1 holds 347: one in 2022-12, then nothing until sustained coverage begins in 2025-06. The older collection and the Level-1C collection hold none in the window.
So 1,162 acquisitions, and 52 whole months, are on no Earth Search collection. Probe PR-06 shows Collection 1 holding about 10,000 items per month over Alaska as a whole outside 2022. So the absence is specific to this tile or its neighbourhood, not to the state.

This meets the first review trigger of decision 0003 for that tile, if Alaska water bodies are in scope. The survey did not establish why the tile is absent.

### 4. The pre-Collection 1 collection is three months of late 2022

The whole collection holds 35,018 items, sensed between 2022-10-01 and 2022-12-05, at baseline 04.00. In the surveyed tiles it holds 70 items, all in the two Geneva tiles. It covers no United States tile in the survey.

### 5. The provider's offset flag varies per item and disagrees with the asset metadata

No Collection 1 item carries `earthsearch:boa_offset_applied`. Every sampled Collection 1 band asset declares a `raster:bands` offset of -0.1, at every baseline.

In the older collection the flag is per item and both values occur inside one baseline. At 04.00 it is true on 3,024 items and false on 693. At 05.10 it is true on 2,644, false on 37, and absent on 10. At 05.11 it is true on 7,071 and false on 570. At 05.12 it is true on 3,169 and false on 5.
Every sampled older-collection band asset from baseline 04.00 declares a `raster:bands` offset of -0.1 whether the flag is true or false. Assets before 04.00 declare 0.

The provider's README says to apply a non-zero `raster:bands` offset. A flag of true says the offset is already in the pixels. For 3,024 of the 3,717 fallback items at 04.00, the two statements cannot both hold.
Catalog metadata cannot settle it. A pixel-level check is the prototyping measurement, issue I-05.

### 6. Quality assets depend on the collection and on the provider's ingestion software

| Collection and software | Quality assets | Where |
|---|---|---|
| Collection 1, every sampled version from v2023.12.01 to v2025.06.17 | `scl`, `cloud`, `snow`, `aot`, `wvp` | Cloud-optimized GeoTIFF in `e84-earth-search-sentinel-data`, us-west-2, requester pays false |
| Older collection, software 0.1.0 and 0.1.1 | `scl`, `aot`, `wvp`, each with a `-jp2` alternate | GeoTIFF in `sentinel-cogs`, JPEG 2000 alternates in `sentinel-s2-l2a` |
| Older collection, software 2025.03.06 and 2026.08.16 | Adds `cloud` and `snow` | The added two are JPEG 2000 in `sentinel-s2-l2a`. One 2026.08.16 variant points every asset at `sentinel-s2-l2a` |

All 3,717 fallback items at 04.00 for 2022 were ingested by software 0.1.0 except 6. They carry a scene classification and no cloud or snow probability.
Level-1C items ingested by software 0.1.0 point their assets into the `sentinel-s2-l2a` bucket rather than the Level-1C bucket. That is a metadata oddity, noted and not pursued.

### 7. Duplicates and revisions

Collection 1 holds 22,501 items for 21,873 acquisition keys. 628 keys have two items, all but one at the same baseline: two products of one tile from one pass, split across datastrips. One key, tile 32TLS on 2023-10-23, holds a 05.09 and a 05.11 item.
A date and platform key therefore does not identify one product. Product ids do. The store must keep both products of a split and both baselines of a pair.
The older collection holds 30,942 items for 25,326 acquisitions. 4,260 acquisition groups mix baselines, mostly an original 02.14, 03.00, or 03.01 item beside its 05.00 reprocessing for 2021. 685 groups are same-baseline splits.
The sample contains originals beside reprocessed products in the older collection. Collection 1 also contains multiple-product keys, mostly same-day splits and one mixed-baseline pair. Neither observation establishes a retention policy. The `_0_`, `_1_` sequence suffix in older-collection ids numbers same-day splits as well as reprocessings. Practice P9 and issue I-16.

Collection 1 also holds 30 acquisitions the reference no longer lists. They fall in 2026-02 (18), 2021-05 (6), 2024-11 (3), 2024-12 (2), and 2026-03 (1). The survey did not establish why.

### 8. Tile multiplicity and revisit

Seven of 20 sites lie in more than one tile by footprint: Lake Lanier in 4, Grand Lake St. Marys in 3, and Lake Tahoe, Lake Travis, Lake Pontchartrain, Lake Geneva, and Lake Taupo in 2 each. Every acquisition at those sites arrives as two to four products. Issue I-30.
Tile counts overstate coverage at a point. Tile 11SQA logged 142 acquisitions in 2024, while 87 Collection 1 footprints covered the Lake Mead site point in the last year.

Reference acquisitions per tile rose with the third satellite. Tile 10SGJ had 145 in 2021, 148 in 2024, and 175 in 2025. Tile 32TLS had 216, 234, and 301. Tile 36MVE had 70, 74, and 102. Issue I-25.

### 9. Reference catalog notes

The reference lists 61 items at baselines 99.05 and 99.06, sensed in December 2024 by the third satellite during its commissioning. They count as reference acquisitions here.

## The fallback survey run

| Quantity | Value |
|---|---|
| Measured at | 2026-09-11T00:11:08+00:00 |
| Input | [gap-survey.json](../benchmarks/results/gap-survey.json), measured 2026-09-10T20:16:28+00:00. Its tiles, and every month marked empty or partial for each tile |
| Scope | 30 tiles, 405 tile-months. All of 2022 for 29 tiles, one further partial month for three of them, and 54 months for the Alaska tile |
| Requests made | 870: 131 to Earth Search, 37 to the Copernicus STAC, 702 HEAD requests to the public `sentinel-cogs` bucket |
| Bytes received | 80,895,110 from Earth Search, 2,000,314 from the Copernicus STAC. HEAD responses carry headers only. Imagery bytes: 0 |
| Payer | The provider. No credentials. No HEAD response carried a request-charged header |
| Code version | Commit 943bb1b plus uncommitted changes, because the script was new at run time. The committed script differs from the one that ran in retry logging, GR05, and in the docstring of its item-selection helper, GR04. No count changes |

## Per-tile fallback results

Missing means reference acquisitions absent from Collection 1 in the tile's incomplete months. Complete GeoTIFF means an older-collection item holds all twelve reflectance bands and the scene classification as cloud-optimized GeoTIFFs in the public bucket.
The per-tile rows are in the `per_tile` list of the [report](reviews/2026-09-10-gap-survey-report.json), under `fallback`.

### 10. The older collection's GeoTIFFs cover the missing 2022 acquisitions

Of the 5,022 missing acquisitions in the incomplete months, 3,840 have an older-collection item with a complete GeoTIFF set. Every one of those 3,840 also has aerosol and water vapour as GeoTIFFs. None is partial.
Five acquisitions have JPEG 2000 assets only, all in January 2022, in tiles 15RYP, 16RBU, 17TKE, 17TKF, and 18TXQ. The provider ingested those items with software 2026.08.16. The remaining 1,177 have no older-collection item: 1,162 in the Alaska tile and 15 elsewhere.

| Month | Missing | Complete GeoTIFF | JPEG 2000 only | Uncovered |
|---|---|---|---|---|
| 2022-01 | 372 | 351 | 5 | 16 |
| 2022-02 | 347 | 326 | 0 | 21 |
| 2022-03 | 346 | 317 | 0 | 29 |
| 2022-04 | 370 | 341 | 0 | 29 |
| 2022-05 | 385 | 360 | 0 | 25 |
| 2022-06 | 370 | 344 | 0 | 26 |
| 2022-07 | 379 | 355 | 0 | 24 |
| 2022-08 | 367 | 341 | 0 | 26 |
| 2022-09 | 370 | 344 | 0 | 26 |
| 2022-10 | 383 | 359 | 0 | 24 |
| 2022-11 | 364 | 341 | 0 | 23 |
| 2022-12 | 59 | 58 | 0 | 1 |

The 3,845 items a fill would use carry baselines 03.01 (276), 04.00 (3,563), 05.00 (1), 05.09 (4), and 05.10 (1). Their offset flag is true on 2,895, false on 945, and absent on 5.
3,831 of them were ingested by software 0.1.0. Cloud and snow probability are absent on 3,833 and present as JPEG 2000 on 12.

### 11. Sampled GeoTIFF objects exist in the public bucket and answer unsigned requests

For each tile and incomplete month with a complete GeoTIFF item, the survey took the first such item. It sent HEAD requests for that item's scene classification and red band objects: 351 items, 702 requests. All 702 returned 200.
Scene classification objects run from 53,632 to 5,690,939 bytes. Red band objects run from 454,695 to 264,001,994 bytes. The small sizes are partial granules at swath edges.
Where the bucket reported a storage class it was intelligent tiering. No response carried a request-charged header. A 200 to HEAD shows existence and size. It shows nothing about pixels or the offset state.

### 12. The two surveys agree

Over the 405 tile-months both surveys covered, their missing and covered counts agree in every case. The [report](reviews/2026-09-10-gap-survey-report.json) recomputes this comparison under finding GS-12.

## What the surveys do not show

- Whether any listed asset opens, holds valid pixels, or has the offset in its values. Nothing read a pixel. A HEAD shows existence and size only.
- Objects the HEAD sample did not touch. One item per tile and month was checked, two objects each. The other bands and items are assumed to match their catalog entries.
- Whether two products of one tile from one pass are both usable. The acquisition key collapses them.
- Tiles whose items never cover a site point in the last year. Neighbouring tiles with partial coverage of a lake are not surveyed.
- Completeness of the Copernicus catalogs. Two of them agree within 25 products of 27,726, which is agreement, not proof.
- Any cause. Why tile 05VLG is absent, why 15 acquisitions have no Level-2A on the route, and why 30 route acquisitions vanished from ESA are open.
- The customer's tiles. Sites are 20 public points. The survey must rerun on the pilot manifest's tiles, and later on the tiles the customer set touches.
- Whether the two GeoTIFF copies of one product hold identical pixels. Probe PR-08 found matching red-band grid, scale, and offset metadata for one shared ESA product. No pixel was compared.
- Completeness after the survey window. Saved listings contain recent products in both collections, as described in the [archive comparison](reviews/2026-09-11-codex-archive-comparison.md). Future ingestion is unverified.

Raw listings are under `data/gap-survey/2026-09-10T201628+0000/` and `data/fallback-survey/2026-09-11T001108+0000/`, outside git. Their digests are in the result files. The fill policy options are in the [gap survey review](reviews/2026-09-10-gap-survey.md).

## Prototype stage 1: raw access to whole tiles, 2026-09-14

Stage 1 of [work-plan.md](work-plan.md) ran on 2026-09-14 on the owner's laptop over the internet, outside us-west-2 (assumption A25).
[raw_access.py](../benchmarks/raw_access.py) read every band of one acquisition, tile 17SKU on 2025-10-15, from both GeoTIFF copies. The same ESA product, `S2B_MSIL2A_20251015T162149_N0511_R040_T17SKU_20251015T202039.SAFE`, sits on both.
Two read modes: `vsicurl`, where GDAL asks for byte ranges, and `whole-object`, one GET per file then a decode from memory. Three repetitions each, every run in a fresh process.
Results: [raw-access.json](../benchmarks/results/raw-access.json) with 60 runs, of which 12 failed on one asset, and [raw-access-older-quality-all.json](../benchmarks/results/raw-access-older-quality-all.json), the 12 older-copy runs repeated with that asset skipped.
[copy_difference.py](../benchmarks/copy_difference.py) then compared six files pixel by pixel, [copy-difference.json](../benchmarks/results/copy-difference.json).
Machine: 10-core arm64 laptop, 17 GB memory, rasterio 1.5.1 on GDAL 3.12.4. Every time below includes the internet path from the laptop to the buckets.

### 13. Whole-tile read cost per band set

Medians of three runs. Bytes are what the reader asked for. Range reads skip the overview pyramids, whole-object reads include them.
Time is the sum of the per-file open, read, fetch, and decode timers. It excludes the digest and statistics each run also computed. The quality and all-band sets hold different files on the two copies.

| Band set | Files | Collection 1, range reads | Collection 1, whole object | Older copy, range reads | Older copy, whole object |
|---|---|---|---|---|---|
| Four 10 m bands | 4 | 508 MB, 54 s, 61 requests | 682 MB, 43 s, 4 requests | 507 MB, 69 s, 195 requests | 681 MB, 45 s, 4 requests |
| Six 20 m bands | 6 | 213 MB, 24 s, 36 requests | 284 MB, 20 s, 6 requests | 212 MB, 25 s, 46 requests | 283 MB, 21 s, 6 requests |
| Two 60 m bands | 2 | 7 MB, 1.7 s, 6 requests | 9 MB, 1.8 s, 2 requests | 7 MB, 1.5 s, 6 requests | 9 MB, 1.8 s, 2 requests |
| Quality layers | 5 or 3 | 32 MB, 4.5 s, 17 requests | 44 MB, 5.3 s, 5 requests | 38 MB, 6.8 s, 29 requests | 80 MB, 5.7 s, 3 requests |
| Everything | 17 or 15 | 759 MB, 76 s, 120 requests | 1,019 MB, 66 s, 17 requests | 765 MB, 91 s, 276 requests | 1,053 MB, 85 s, 15 requests |

Peak resident memory of the worker while holding a whole set, on Collection 1: 1.0 GB for the 10 m bands by range reads. Everything by range reads peaked at 1.2 GB and by whole-object reads at 1.7 GB. The peak includes process start-up and a copy made for the digest.
CPU time was 7 s per 10 m set and 11 to 12 s for everything, against 43 to 91 s of read time. The reads waited on the network for most of the time.
Whole-object reads were faster than range reads for the 10 m, 20 m, and all-band sets on this connection, despite moving a third more bytes. For the 10 m set they made 4 requests instead of 61. The 60 m sets and the Collection 1 quality layers went the other way by a small margin.
Per-request latency is one explanation consistent with these timings. The run order was fixed and the connection uncontrolled, so the cause is not isolated.
Three runs exceeded 1.5 times their set's median wall time. A Collection 1 20 m whole-object run took 36 s against 20 s. An older-copy 20 m whole-object run took 99 s against 21 s. An older-copy 60 m run took 7.5 s against 1.8 s.

### 14. The two copies are laid out differently, and the older copy's quality layers differ

- The older copy's 10 m bands have the same 1024-pixel blocks, four overviews, and deflate compression as Collection 1. Yet they needed 47 to 51 range requests per band against 14 to 17. Range reads of its 10 m set took 25 percent longer.
- The older copy's `swir16` uses 1024-pixel blocks and three overviews. Its five other 20 m bands use 512-pixel blocks and four overviews, like Collection 1.
- The older copy's `cloud` and `snow` assets are JPEG 2000 files in the `sentinel-s2-l2a` bucket, outside this GeoTIFF benchmark. The first pass opened them through an unconfigured S3 path and failed 12 of 60 runs with the errors saved in the result. Whether they open without credentials is untested. The registry documents unsigned access and the older readme says requester pays, issue I-18. The rerun skips them and records why. Most 2022 fallback items lack these assets in the catalog, finding 10.
- Aerosol and water vapour are 20 m grids on Collection 1. On the older copy aerosol is a 1,830-pixel 60 m grid and water vapour a 10,980-pixel 10 m grid. Both catalogs declare 20 m for them.
- No whole-object response carried a requester-pays charge header on either bucket.

### 15. The copies differ by the offset applied and clamped, measured on one product

Six files of the same product were compared pixel by pixel, older copy minus Collection 1, where both have data. The comparison ran twice on 2026-09-14. The owner invoked the second run at 19:56 UTC with the rule check added. It reproduced the first run's difference counts exactly and replaced its file.

| File | Valid in both | Differ | Most common difference | Next most common |
|---|---|---|---|---|
| coastal | 2,627,222 | all | −1,000 on 98.3 percent | −999, −998, −997, tailing to −102 |
| nir09 | 2,627,905 | all but 641 | −1,000 on 99.0 percent | 0 on 641 pixels, then −952 |
| red | 94,546,915 | all | −1,000 on 99.98 percent | −999, −998, tailing to −633 |
| scl | 23,636,736 | none | identical | |
| aot, wvp | | | different grids, not compared | |

The dominant difference is exactly −1,000, the radiometric offset −0.1 at scale 0.0001 in stored units. Every difference lies between −1,000 and 0. That excludes an unclamped subtraction, which would wrap below zero in unsigned integers, and any positive shift.
The rule `older = max(c1 − 1000, 1)` was then checked on every pixel valid in both copies. It held without exception: zero violations on 99,802,042 pixels across the three reflectance bands. That is the conversion the provider described for the older copy, subtract the offset and clamp low values, now measured for this product.
The clamp touches every Collection 1 value at or below 1,000, which is reflectance at or below zero after the offset. On this tile that is 44,936 coastal pixels, 1.71 percent of those valid in both. For nir09 it is 26,317 pixels, 1.00 percent, and for red 20,898, 0.02 percent. Those pixels keep their value only on Collection 1. How many of them lie over water is not measured.
The rule check also ran on the classification, where it has no meaning and reports every pixel as a violation. The values there are identical.
The older item's `earthsearch:boa_offset_applied` flag is true and the Collection 1 item has no such flag. Both items' `raster:bands` declare offset −0.1 for these assets. A reader that applies the declaration on the older copy would subtract the offset twice. No-data masks agree exactly. The scene classification is identical.
This is one 05.11 product. It says nothing about the 04.00 items with mixed flags that the gap survey found, issue I-05.

### What stage 1 does not show

- Anything about an instance beside the buckets. Every time includes the laptop's internet path. Repeat from us-west-2 when access exists.
- Windowed reads of a water body. Only whole tiles were read. Requests per pond, the question of issue I-20, is stage 2 work.
- Other acquisitions, tiles, or processing versions. One 05.11 product was read. The 04.00 items that the gap survey found with mixed offset flags are the subject of issue I-05 and stage 5.
- Whether the clamp rule holds on the other nine reflectance bands, on other items, or at other baselines. Three bands of one 05.11 product were checked.
- Whether the older copy's JPEG 2000 quality files open without credentials. The failures were reader configuration, not an access decision.
- Delivered network bytes. Requested ranges and machine-wide counters are recorded separately. The counters include other traffic and, on one run, recorded far less than requested.
- The two outlier runs' cause. Nothing on the laptop was controlled during the runs.

Worker specifications, GDAL logs, and per-run results are under `data/raw-access/`, outside git.
