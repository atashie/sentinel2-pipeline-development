# Measurements, 2026-09-10

The six measurement sets summarized below cover the surveys and first four prototype stages.
The data gap survey required by [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md) ran once on 2026-09-10 and wrote [gap-survey.json](../benchmarks/results/gap-survey.json).
The fallback survey the owner asked for the same day ran once and wrote [fallback-survey.json](../benchmarks/results/fallback-survey.json). Both are summarized for review in the generated [gap survey report](reviews/2026-09-10-gap-survey-report.json).
The plan, definitions, and rerun steps are in [gap-survey-plan.md](gap-survey-plan.md). Every number in the survey sections is a count of catalog items, acquisitions, requests, or bytes, as labeled. The surveys read no imagery byte.
The third set is [prototype stage 1](#prototype-stage-1-raw-access-to-whole-tiles-2026-09-14), which read whole tiles on 2026-09-14.
The fourth is [prototype stage 2](#prototype-stage-2-one-lake-at-a-time-2026-09-15), which read one lake at a time on 2026-09-15.
The fifth is [prototype stage 3](#prototype-stage-3-many-lakes-in-one-tile-2026-09-16), which read every lake of a tile in one process on 2026-09-16.
The sixth is [prototype stage 4](#prototype-stage-4-lakes-across-tiles-2026-09-16), which preserves separate tile contributions while comparing work organization.
The [larger-workload comparison](reviews/2026-09-21-sleep-rerun.md) records subsequent measurements, replacement attempts, and their limits.

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
So 1,162 acquisitions, and 52 whole months, are on no Earth Search collection. Probe PR-06 shows Collection 1 holding about 10,000 items per month over Alaska as a whole outside 2022. So the absence is specific to this tile or its neighborhood, not to the state.

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

Of the 5,022 missing acquisitions in the incomplete months, 3,840 have an older-collection item with a complete GeoTIFF set. Every one of those 3,840 also has aerosol and water vapor as GeoTIFFs. None is partial.
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
- Tiles whose items never cover a site point in the last year. Neighboring tiles with partial coverage of a lake are not surveyed.
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
- Aerosol and water vapor are 20 m grids on Collection 1. On the older copy aerosol is a 1,830-pixel 60 m grid and water vapor a 10,980-pixel 10 m grid. Both catalogs declare 20 m for them.
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

## Prototype stage 2: one lake at a time, 2026-09-15

[benchmarks/lake_extraction.py](../benchmarks/lake_extraction.py) ran on 2026-09-15 and wrote [lake-extraction.json](../benchmarks/results/lake-extraction.json).
It read the 32 pilot water bodies from Collection 1, one lake at a time, with four methods. Three repetitions each in a fresh process: 384 runs, none failed.
The machine was a 10-core arm64 laptop with 16 GiB of memory, rasterio 1.5.1 on GDAL 3.12.4, and odc-stac 0.5.3. It read over the internet from outside us-west-2, assumption A25.
Five files per lake: red and near-infrared at 10 m, swir16 at 20 m, coastal at 60 m, and the scene classification at 20 m.
The 360 runs that read a pixel started between 13:23:11 and 13:41:53 UTC. Two lakes lay outside the tile chosen for their region, so their 24 runs read nothing.
The file's summary was regenerated offline from its saved runs after [Codex's review](reviews/2026-09-15-codex-stage-2-review.md). The runs themselves are the original pass. The [record](reviews/2026-09-14-stage-2-one-lake-at-a-time.md) lists every rewrite.

One Collection 1 item per region, chosen by the rule in the result's `catalog` section:

| Region | Tile | Item | Cloud cover | No-data share | Lakes entirely inside |
|---|---|---|---|---|---|
| Tahoe | 10SGJ | S2B_T10SGJ_20251020T185627_L2A | 0.001 % | 16.3 % | 6 of 6 |
| Lanier | 17SKU | S2B_T17SKU_20251015T162249_L2A | 0.001 % | 21.6 % | 3 of 5 |
| Okeechobee | 17RNK | S2C_T17RNK_20251031T160522_L2A | 0.04 % | 0 % | 4 of 6 |
| Grand Lake St. Marys | 16TGK | S2C_T16TGK_20250930T163033_L2A | 0.003 % | 0 % | 5 of 5 |
| Washington | 10TET | S2B_T10TET_20250608T191625_L2A | 0.0003 % | 1.0 % | 6 of 6 |
| Iliamna | 05VMG | S2B_T05VMG_20250610T213525_L2A | 6.3 % | 1.1 % | 3 of 4 |

Every item is processing baseline 05.11. Choosing them took 24 catalog requests and 26.1 MB of catalog JSON.

### 16. Small-lake reads usually fit within one block per file in this sample

| Size class | Lakes read | Blocks, five files | Requests | Bytes requested | Read time, raster mask | 10 m pixels, all classes |
|---|---|---|---|---|---|---|
| 10 m | 5 | 5 | 15 | 3.6 MB | 2.1 s | 361 |
| 30 m | 5 | 5 | 15 | 3.6 MB | 2.2 s | 444 |
| 100 m | 5 | 5 | 15 | 3.5 MB | 2.2 s | 895 |
| 300 m | 6 | 5, one lake 10 | 15 | 3.8 MB | 2.1 s | 2,683 |
| 1,000 m | 4 | 5 | 15 | 3.6 MB | 2.2 s | 14,000 |
| Anchor | 5 | 15 to 92 | 36 | 41.5 MB | 6.2 s | 1,672,524 |

Medians of the per-lake medians. Blocks are the internal blocks the five windows intersect, from each window and the file's block shape. Requests are HTTP requests, which GDAL merges when ranges are consecutive.
Read time is the sum of the per-file open, read, build, and compute timers for the five files. The last column is the median lake's interior, shoreline, and near-land pixels together at 10 m.

- 24 of the 25 small lakes with pixels touched one block per file: 5 blocks, 15 requests, 2.5 to 4.4 MB. Three requests per file: one size probe, one header read, one block. Bytes per file are one block. That is 1.5 MB median for a 10 m band with 1,024 pixel blocks and 0.43 MB for swir16 with 512 pixel blocks. Coastal, with 256 pixel blocks, cost 0.11 MB and the classification 0.05 MB.
- The Alaska 300 m lake `nhd-72879541` sits across a block boundary in every file. It took 10 blocks, 20 requests, and 4.3 MB with every method. Its red window spans rows 9,181 to 9,239, across the boundary at row 9,216. Position in the block grid, not size, made the difference.
- Requests are not blocks. Lake Okeechobee's red window intersects 20 blocks and took 13 requests, because GDAL merged consecutive ranges. The anchors touched 15 to 92 blocks over five files, 19 to 48 requests, 11 to 59 MB.
- A 14 pixel pond and a 35,000 pixel lake cost the same bytes and about 2 seconds. Both fit within one block per file. Time per file was 0.2 to 0.6 s to open and 0.1 to 0.5 s to read for the small lakes. Per-request latency on this connection is one explanation consistent with that. Position, window extent, compression, caching, and request merging were not controlled.
- Issue I-20 expected cost to follow blocks touched. The sample agrees for one lake at a time. Machine-wide network counters recorded a median of 1.05 times the requested bytes on the raster mask runs.

### 17. The three mask methods returned identical values, and the methods differ in what they keep and in overhead

- The raster mask, the index lists, and the lazy stack extracted identical stored integers on identical pixel sets. That held on every band of the 30 lakes inside their tile, 150 checks. The run saved value digests. Pixel-set identity for this run rests on the three methods reading the same saved mask files, which the review checked offline. Later runs save a pixel-set digest beside the value digest.
- The naive clip matched the interior and shoreline set on 121 of the 150 checks. On the other 29 it differed exactly where preparation had counted a difference between GDAL's all-touched selection and the coverage threshold. GDAL marked 198 pixels whose coverage lies below one millionth of a pixel. 197 of them have a sliver of positive intersection and one has no intersection at all. The threshold rule kept 6 pixels GDAL did not mark. Two selection rules differ on 204 pixels out of millions. That is not a failure of the all-touched rasterization. The one empty intersection is not investigated.
- The naive clip keeps no near-land pixel and no coverage fraction. For a typical 10 m pond it kept 4 pixels at 10 m against 361 with the near-land ring. For a typical anchor it stored 2.6 million band values over five files against 4.2 million. Its smaller window touched the same blocks, so its bytes and requests were the same.
- The lazy stack used 0.39 s of CPU per small lake against 0.12 s for the raster mask. Its peak memory was 0.17 GB against 0.10 GB. Its read time was 0.05 to 0.1 s longer on small lakes. On two anchors it read faster. Lake Lanier took 6.3 s against 10.0 s for the raster mask and 7.7 s for the index lists. Lake Okeechobee took 8.1 s against 10.2 s and 9.2 s. It requested more bytes than the raster mask on three anchors, the same on one, and fewer on one. On Okeechobee it asked for 50.8 MB against 58.8 MB, in more requests. The class medians, 47.2 MB against 41.5 MB, are a ratio of medians. Its output grid matched the requested native window on every run.
- The raster mask and the index lists were indistinguishable on the small lakes: 2.13 s against 2.15 s for a 10 m pond. Bytes and memory were the same. On the anchors the index lists were faster on two lakes and slower on none, within the run-to-run spread.
- These observations do not rank the methods. The methods ran in a fixed order per lake, three times each, over one uncontrolled connection. The read timers exclude polygon projection, mask loading, pixel selection, and digests. Whole-run wall times include them. For the median 10 m pond they were 2.19 s, 2.14 s, 2.15 s, and 2.43 s. That order is naive clip, raster mask, index lists, lazy stack. For the median anchor they were 7.3 s, 6.4 s, 6.0 s, and 6.7 s.
- Twelve of the 360 runs with pixels took more than 1.5 times their lake and method median, up to 12.6 s against 6.7 s. Nothing on the laptop was controlled.

### 18. Pixel classes per size class, and lakes outside the chosen tile

| Size class | Lakes | 10 m | 20 m | 60 m | Preparation, median and longest |
|---|---|---|---|---|---|
| 10 m | 5 | 0 · 4 · 356 | 0 · 2 · 90 | 0 · 2 · 9 | 0.006 s, 0.006 s |
| 30 m | 5 | 3 · 14 · 427 | 0 · 7 · 105 | 0 · 2 · 10 | 0.006 s, 0.009 s |
| 100 m | 5 | 72 · 60 · 764 | 12 · 30 · 177 | 0 · 9 · 15 | 0.009 s, 0.013 s |
| 300 m | 6 | 739 · 206 · 1,676 | 148 · 99 · 395 | 7 · 31 · 32 | 0.023 s, 0.030 s |
| 1,000 m | 4 | 8,656 · 672 · 4,999 | 2,080 · 334 · 1,164 | 198 · 109 · 92 | 0.083 s, 0.094 s |
| Anchor | 5 | 917,147 · 20,061 · 124,035 | 218,133 · 9,770 · 28,784 | 23,402 · 3,015 · 2,241 | 11.3 s, 19.3 s |

Cells are interior · shoreline · near-land pixels, each the median over the lakes of the class that lie inside their tile. The median lake's total at 10 m is in the table of finding 16. Preparation computes all three resolutions for one lake in its own process and saves the files.

- All five 10 m ponds have no interior pixel at any resolution. At 20 m, 10 of the 30 lakes inside their tile have none. At 60 m, 15 have none. Every one of them has shoreline and near-land pixels.
- Summed coverage matched the polygon area inside the tile within 2.4e-11 relative on every lake, against a declared tolerance of 1e-6. Preparation peaked at 1.56 GB for Lake Okeechobee, whose 10 m mask holds 12.4 million interior pixels. Lake Tahoe's preparation took 11.3 s and 0.87 GB for the three resolutions and their files. Its 10 m mask alone computed in 8.0 s.
- Two lakes lay entirely outside the tile chosen for their region: the Lanier 100 m pond `nhd-34972649` and the Okeechobee 30 m pond `nhd-57dbffd9`. Their 24 runs read nothing. Lake Lanier was 62.6 % inside tile 17SKU, Lake Okeechobee 90.0 % inside 17RNK, and the Alaska 1,000 m lake `nhd-60265485` 70.9 % inside 05VMG. Only the part inside was read.
- The masks this run saved measured edge distances to the polygon cut at the tile edge. A tile edge counted as a shoreline for the three lakes partly outside their tile. Codex's review found it. The code now measures every distance to the real boundary. Recomputing all 30 lakes' masks offline with the corrected code left 27 lakes identical. Lake Lanier's 10 m classes changed on 77 pixels and Lake Okeechobee's on 171, all near-land pixels where the shoreline meets the tile edge. Distances changed on 15,134 Lanier, 31,678 Okeechobee, and 440 Alaska pixels at 10 m, by up to 993 m. The extraction runs read the saved masks, so their pixel counts for those two lakes differ from the corrected masks by those pixels. The run's files are marked affected and are not reused.
- Tiles 10SGJ and 11SKD each hold all six Tahoe lakes entirely. The smaller id won.
- Each Alaska tile appears in the window under two grid codes. 87 items carry `MGRS-05VLG` or `MGRS-05VMG` with the leading zero. Five carry `MGRS-5VLG` or `MGRS-5VMG` without it. Grouping by tile must normalize the code.

### What stage 2 does not show

- Anything about an instance beside the bucket. Every time includes the laptop's internet path.
- Reads shared between lakes. Every lake was read alone, so a block shared by neighboring ponds was fetched once per pond. Stage 3 measures the sharing.
- Lakes across tiles. Stage 2 reads only one selected tile per lake. [Stage 4](#prototype-stage-4-lakes-across-tiles-2026-09-16) tests two regions across tiles.
- A method ranking. Fixed order, three repetitions, and one uncontrolled connection limit what the timings can say.
- Other dates, products, or processing versions. One 05.11 item per region, all with cloud cover at or below 6.3 %.
- Delivered bytes. Requests and bytes are what GDAL asked for. The network counters are machine-wide.
- Why the all-touched rule and the coverage threshold disagree on 204 pixels. The counts are recorded. The one pixel with no intersection is not investigated.
- A storage format. Output bytes are row, column, class, and value fields per extracted pixel, without coverage and distance fields.

Saved items, masks, index lists, worker specifications, GDAL logs, and per-run results are under `data/lake-extraction/`, outside git.

## Prototype stage 3: many lakes in one tile, 2026-09-16

[benchmarks/tile_extraction.py](../benchmarks/tile_extraction.py) ran on 2026-09-16 and wrote [tile-extraction.json](../benchmarks/results/tile-extraction.json).
It read every pilot lake of a tile in one process, with three read patterns and the four methods of stage 2. Three repetitions each in a fresh process: 324 runs over nine tiles, none failed.
The machine was a 10-core arm64 laptop with 16 GiB of memory. It ran rasterio 1.5.1 on GDAL 3.12.4 with a 512 MiB block cache, and odc-stac 0.5.3 on four Dask threads. It read over the internet from outside us-west-2, assumption A25.
A first run on 2026-09-15 held a 512-byte block cache, because the script passed 512 to `rasterio.Env`, which takes bytes. [Codex's review](reviews/2026-09-15-codex-stage-3-review.md) found it. The owner authorized this rerun, and every number below is from it. The [record](reviews/2026-09-15-stage-3-many-lakes-in-one-tile.md) keeps the first run's result outside git and says what the cache changed.
The five files per tile are stage 2's. Those are red and near-infrared at 10 m, swir16 at 20 m, coastal at 60 m, and the scene classification at 20 m.
The runs read pixels from 12:32:10 to 14:00:22 UTC, first start to last completion. They requested 45.2 GB in 19,179 requests, 36.3 GB of it in the 108 whole-tile runs. Every worker stayed under the 4 GiB memory budget, with a peak of 1.94 GiB by its own count. Host page-outs during a run reached 6.4 MB at most. That is below the 128 MiB threshold that marks memory pressure, so every run counts in the medians.
[Codex's pre-run review](reviews/2026-09-15-codex-stage-3-prerun-review.md) was applied before the first run. The record lists the smoke run and the guarded check that preceded it.

Tiles were chosen to place every lake, and a lake belongs to every chosen tile its 100 m buffer touches. The 32 lakes gave 40 lake-tile memberships over nine tiles, the same tiles and acquisitions as the first run:

| Tile | Region | Item | Cloud cover | Members | Stage 2 acquisition |
|---|---|---|---|---|---|
| 05VLG | Iliamna | S2C_T05VLG_20250804T213547_L2A | 0.1 % | 3 | no |
| 05VMG | Iliamna | S2B_T05VMG_20250610T213525_L2A | 6.3 % | 4, the 1,000 m lake 70.9 % inside | yes |
| 10SGJ | Tahoe | S2B_T10SGJ_20251020T185627_L2A | 0.0007 % | 6 | yes |
| 10TET | Washington | S2B_T10TET_20250608T191625_L2A | 0.0003 % | 6 | yes |
| 16SGD | Lanier | S2B_T16SGD_20251015T162249_L2A | 0.0004 % | 4, Lake Lanier 62.5 % inside | no |
| 16TGK | Grand Lake St. Marys | S2C_T16TGK_20250930T163033_L2A | 0.003 % | 5 | yes |
| 17RNK | Okeechobee | S2C_T17RNK_20251031T160522_L2A | 0.04 % | 5, Lake Okeechobee 90.0 % inside | yes |
| 17RNL | Okeechobee | S2C_T17RNL_20251031T160522_L2A | 0.6 % | 4, Lake Okeechobee 22.7 % inside | no |
| 17SKT | Lanier | S2B_T17SKT_20251022T161651_L2A | 0.002 % | 3, Lake Lanier 70.3 % inside | no |

Every item is processing baseline 05.11. Choosing them took 24 catalog requests and 26.1 MB of catalog JSON over 1,473 items.
Lake Lanier lies 70.3 % inside 17SKT, more than the 62.6 % inside stage 2's tile 17SKU, so the rule placed it there. The two ponds stage 2 left outside have pixels now, in 17SKT and 17RNL. Eight lakes are members of two chosen tiles. The 05VLG item is 81.9 % no-data and still covers the support of its three members.

### 19. Reading every lake of a tile in one process cuts requests by more than half

| Tile | Lakes | One process per lake, stage 2 | Every lake in one process, files outermost | Requests | Bytes | Read time |
|---|---|---|---|---|---|---|
| 05VMG | 4 | 65 requests, 14.0 MB, 8.9 s | 30 requests, 11.5 MB, 4.2 s | 46 % | 82 % | 47 % |
| 10SGJ | 6 | 112 requests, 60.5 MB, 17.2 s | 51 requests, 52.4 MB, 8.7 s | 46 % | 87 % | 51 % |
| 10TET | 6 | 100 requests, 30.1 MB, 13.3 s | 34 requests, 18.4 MB, 4.4 s | 34 % | 61 % | 33 % |
| 16TGK | 5 | 79 requests, 26.7 MB, 11.4 s | 19 requests, 13.1 MB, 2.8 s | 24 % | 49 % | 24 % |
| 17RNK | 5 | 108 requests, 70.9 MB, 18.7 s | 48 requests, 58.8 MB, 8.8 s | 44 % | 83 % | 47 % |

The five tiles read from the same acquisition as stage 2, raster mask method, medians of three repetitions. The stage 2 column sums the per-lake medians behind finding 16. The last three columns are the ratio.

- Requests fell to 24 to 46 percent, bytes to 49 to 87 percent, and read time to 24 to 51 percent. A lake read alone in its own process paid a size probe and a header read per file, 10 of its 15 requests. In one process per tile the headers are read once, and a block one lake loaded serves the next. Stage 2 ran with GDAL's default cache, 5 percent of memory, so both runs held their blocks.
- A small lake whose blocks were new cost 4 to 6 requests and 1.5 to 3.8 MB. The Alaska 300 m lake sits across a block boundary in every file, 10 blocks, and cost 6 requests in 05VLG and 5 in 05VMG.
- In the seven tiles with an anchor, 21 of the 26 pond memberships cost no additional request. A neighbor's read, usually the anchor's, had already loaded their blocks into the block cache. The five that paid were Tahoe's 30 m, 100 m, and 1,000 m lakes and Washington's 10 m and 1,000 m lakes. The seven memberships in the two Alaska tiles, which have no anchor, all paid.
- Sharing is modest at this density. The lakes' windows touch 20 to 112 blocks summed over lakes and 16 to 92 distinct blocks, out of 548 in the five files. The nine tiles' lakes need 2.9 to 16.8 percent of their files' blocks.
- Loop order matters within one process. Reading lake by lake reopens every file per lake, and an open file's cached blocks go with it. Against reading file by file it cost 4 to 17 more requests, 1.7 to 9.1 MB more, and 0.7 to 2.8 s more read time. Raster mask medians. Reopening re-read headers, 15 to 30 opens against 5. GDAL's smaller cache of downloaded ranges still served 6 of the 33 smaller lakes for free. Across processes, as in stage 2, every lake pays the headers again.

### 20. One whole-tile read costs 6 to 32 times the bytes of the windowed reads at this lake density

| Tile | Lakes | Windowed reads, files outermost | One whole-tile read | Bytes ratio | Break-even lakes, estimate |
|---|---|---|---|---|---|
| 05VLG | 3 | 6.7 MB, 26 requests, 3.3 s | 57 MB, 19 requests, 7.2 s | 8.4 | 25 |
| 05VMG | 4 | 11.5 MB, 30 requests, 4.2 s | 362 MB, 50 requests, 35 s | 32 | 126 |
| 10SGJ | 6 | 52.4 MB, 51 requests, 8.7 s | 327 MB, 45 requests, 33 s | 6.2 | 37 |
| 10TET | 6 | 18.4 MB, 34 requests, 4.4 s | 393 MB, 54 requests, 37 s | 21 | 128 |
| 16SGD | 4 | 48.3 MB, 36 requests, 7.4 s | 396 MB, 54 requests, 37 s | 8.2 | 33 |
| 16TGK | 5 | 13.1 MB, 19 requests, 2.8 s | 394 MB, 54 requests, 38 s | 30 | 150 |
| 17RNK | 5 | 58.8 MB, 48 requests, 8.8 s | 352 MB, 49 requests, 34 s | 6.0 | 30 |
| 17RNL | 4 | 43.8 MB, 33 requests, 6.4 s | 330 MB, 48 requests, 32 s | 7.5 | 30 |
| 17SKT | 3 | 21.5 MB, 20 requests, 3.4 s | 410 MB, 54 requests, 38 s | 19 | 57 |

Raster mask method, medians of three repetitions. The break-even column divides the whole-tile bytes by the tile's windowed bytes per lake. It is byte arithmetic from these medians, not a measurement.

- Eight tiles have data across the tile. There a whole-tile read of the five files requested 327 to 410 MB in 32 to 38 s, in 45 to 54 requests. The 05VLG item is 82 percent no-data and compressed to 57 MB, read in 7.2 s and 19 requests. The windowed reads of the same lakes requested 6.7 to 58.8 MB in 2.8 to 8.8 s.
- The whole-tile read makes fewer requests than the windowed reads on two tiles, because GDAL merges consecutive block ranges. It moves 6 to 32 times the bytes.
- Seven of the nine tiles hold one anchor and two to five smaller lakes. The two Alaska tiles hold three and four lakes of 30 to 1,000 m and no anchor. At this mix, dividing whole-tile bytes by windowed bytes per lake gives 25 to 150 lakes per tile. A small lake that pays for its own blocks costs 1.5 to 3.8 MB. At that price the eight full tiles would break even at roughly 90 to 270 such lakes. Both are byte arithmetic from these medians. They say nothing about time or cost, and they hold for this lake mix only. Shared blocks can raise that estimate. Lake count alone cannot predict the crossover. Stage 1's whole-tile numbers, finding 13, agree with these whole-tile reads.
- The largest median of extracting every lake from the array in memory was 0.18 s for five files, Lake Okeechobee's tile with the index lists. The largest single-run sum of per-lake extraction timers was 0.1874 s, rounded to 0.19 s. Selection time was small within this experiment.
- Peak resident memory is the highest of each combination's three runs. Whole-tile combinations peaked at 0.78 to 1.77 GB with rasterio and 0.87 to 2.08 GB with the lazy stack. A whole-tile run holds up to 512 MiB of decoded blocks in GDAL's cache. The windowed combinations peaked at 0.11 to 1.80 GB, the highest holding Lake Okeechobee's mask of 12.4 million interior pixels.

### 21. The lazy stack on a shared tile graph reads 1.6 to 7 times the bytes and opens a file once per chunk

- On the shared whole-tile graph, computing each lake's window separately requested 1.6 to 7.1 times the bytes of the rasterio windowed reads, medians. It took 1.4 to 4.6 times as long. Grand Lake St. Marys: 92.9 MB against 13.1 MB. Washington: 130 MB against 18.4 MB. Tahoe: 167 MB against 52.4 MB. Each compute reads whole chunks of 2,048 pixels, four blocks at 10 m, and no decoded chunk is retained between computes. GDAL may keep downloaded ranges apart from that. On Grand Lake's tile all five lakes lie in one red chunk. It was opened and read five times, 27 MB where one read of 5.4 MB would do. This is the tested recipe: 2,048-pixel chunks, four threads, one compute per lake. Other odc-stac settings are not measured.
- A graph per lake is built on the lake's own window, as in stage 2. There the lazy stack requested 0.88 to 1.22 times the bytes of the rasterio reads in the same order.
- Computing the whole tile through the lazy stack requested the same bytes as rasterio within 0.2 MB. It made 219 to 221 requests against 19 to 54. GDAL's log shows it opened each 10 m file 36 times, once per chunk, and each 20 m file 9 times. On the eight full tiles it was faster, 19 to 31 s against 32 to 38 s. On 05VLG it took 7.5 s against 7.2 s. Four threads fetching chunks at once is one explanation, not isolated here. Its peak memory, combination maxima, was within 0.1 GB of rasterio's on six tiles. It was 0.2 GB higher on two and 0.5 GB higher on Lake Okeechobee's.
- Median CPU time per combination was 0.6 to 6.4 s for the lazy stack against 0.2 to 5.7 s for the raster mask.

### 22. Every pattern and method agreed, and per-scene rasterization costs under half a second per large lake

- The three patterns and the three mask methods extracted identical stored integers on identical pixel sets on all 200 lake-bands. That is 40 memberships and five files, twelve combinations each, three repetitions. The naive clip was identical across the three patterns on values and pixel sets.
- The naive clip differs from the interior-plus-shoreline set on 44 of the 200 lake-bands. That is exactly where preparation counted a difference between GDAL's all-touched rule and the coverage threshold, as in finding 17.
- Stage 2 read 26 of the memberships from the same acquisitions. On all 130 of their lake-bands the mask methods matched stage 2's mask methods and the naive clip matched stage 2's naive clip. The other 70 lake-bands were read from acquisitions stage 2 did not use and have no comparison.
- The naive clip projects and rasterizes each polygon per scene, at three resolutions. That setup took 0.16 s for Lake Tahoe and 0.45 s and 0.36 s for Lake Lanier in its two tiles. It took 0.44 s and 0.19 s for Lake Okeechobee, and under 0.1 s for every other lake. Those are medians of each lake's three runs, wall time. Loading the precomputed masks or index lists took 0.001 to 0.17 s per lake, medians, and 0.37 s at most. At one scene per lake the two setups cost the same order. What the precomputed masks buy is the coverage fraction and the near-land class, which the naive clip does not keep. With the 512-byte cache the same rasterization took 14 to 20 s per large lake, one row per pass, see the [record](reviews/2026-09-15-stage-3-many-lakes-in-one-tile.md).
- Nine of the 324 runs took more than 1.5 times their combination's median wall time, up to 107 s against 15 s. Eight had the same requests and bytes as their siblings. The largest outlier had two recorded timeouts and three repeated ranges. Those added 5,158,494 requested bytes. The extraction succeeded. The [rerun review](reviews/2026-09-16-codex-stage-3-rerun-review.md#1-medium-the-largest-outlier-has-recorded-timeouts-and-extra-requested-bytes) records the evidence. Two of the three whole-tile index-list runs on Lake Okeechobee's tile were slow, 101 s and 63 s against 36 s. That combination's median is slow too. Nothing on the laptop or the connection was controlled.

### What stage 3 does not show

- Anything about an instance beside the bucket. Every time includes the laptop's internet path.
- More than six lakes in a tile. The whole-tile break-even is byte arithmetic from these medians.
- Dates over a season. One item per tile, all 05.11, with cloud cover at or below 6.3 percent.
- A lazy stack tuned for this use: smaller chunks, retained chunks, or one compute for every lake. The tested recipe used 2,048-pixel chunks and four threads, with other reader defaults retained.
- A single labeled mask per tile. Each lake was extracted with its own mask from the shared array.
- Lakes across tiles combined. Stage 3 reads selected tile portions separately. [Stage 4](#prototype-stage-4-lakes-across-tiles-2026-09-16) assembles contribution keys without blending or storing pixel arrays.
- Any block cache other than 512 MiB. The record compares this run with the first run's 512-byte cache, two points only.
- Causes of the other eight slow workers. The largest outlier has recorded transport failures, without a complete accounting of its delay.
- Delivered bytes. Requests and bytes are what GDAL asked for.

Saved items, masks, index lists, worker specifications, GDAL logs, and per-run results are under `data/tile-extraction/`, outside git. The first run's result is kept there too.

## Prototype stage 4: lakes across tiles, 2026-09-16

Status: measured and [reviewed](reviews/2026-09-16-claude-stage-4-full-run-review.md). The [response](reviews/2026-09-16-codex-stage-4-review-response.md) records corrections and remaining limits.
Evidence: [cross-tile-extraction.json](../benchmarks/results/cross-tile-extraction.json).
The [run record](reviews/2026-09-16-stage-4-full-run.md) owns commands, the preflight correction, artifact locations, and verification.
Every number in this section is measured or calculated from that result, with JSON paths identified below.

The frozen sample has eleven lakes, eight tiles, two datatakes, and eight tile-datatake pairs.
Its twenty-five lake-tile memberships require 125 band contributions per workload.
Raster mask and lazy stack each run lake-first and tile-first, with three repetitions and rotated orders.
All 114 extraction processes completed. Each workload contains every expected contribution, giving 1,500 records across the experiment.
These counts come from `plan.lakes`, `plan.scenes`, `plan.expected`, and `plan.order`.
Corresponding contributions match across readers, paths, and repetitions on values, native pixel identities, classes, counts, windows, and polygon digests.
No contribution is missing, failed, empty, or entirely no-data. Sources: `summary.equality`, `summary.workloads`, and `runs[].contributions`.

### 23. Tile geometry, product identity, and band validity need separate accounting

Each region uses one datatake, with all four spatial candidate tiles available.
Lanier uses `GS2B_20251015T162149_044968_N05.11`, spanning UTM zones 16 and 17.
Okeechobee uses `GS2C_20251031T160521_006030_N05.11`.
The tile extent unions leave zero uncovered buffered support for every sampled lake.
That establishes grid coverage. It does not establish validity in every band.

| Anchor | Buffered support, km² | Support inside multiple tile extents, km² | Extent overlap, percent |
|---|---:|---:|---:|
| Lanier | 246.68 | 246.68 | 100.00 |
| Okeechobee | 1,409.13 | 402.11 | 28.54 |

Source: `plan.selection.<region>.coverage.<anchor>`.
Overlap is the union of pairwise intersections, counting each multiply covered area once.
The percentages divide `support_overlap_m2` by `support_area_m2`. They are not sums of tile shares.
The diagnostic buffers retain the implementation's polygonal approximation.
Successive boundary refinements converge within the declared arithmetic criterion. This does not measure error against exact geometry or establish catalog footprint accuracy.

No single tile contains either anchor's entire buffered support.
For Lanier, several partial tiles collectively cover every part at least twice.
All tile observations remain separate. Identical row and column indices across UTM grids do not identify the same ground pixel.

**Catalog footprint limits.** The selected footprints contain four to six coordinate pairs, including each ring's closing pair.
Inside the lakes' buffered supports, their edges fall inward from native tile edges by up to approximately 129 m.
The per-tile shortfalls are 129 m for 16SGC, 104 m for 17RML, 99 m for 17RNK, and 71–72 m for 17SKT and 17SKU.
17RMK reaches approximately 1 m. Neither 16SGD nor 17RNL has a sampled shortfall within those supports.
These distances sample native edges every 50 m against projected catalog polygons. They describe this sample, rather than a general accuracy guarantee.
Sources: `plan.scenes[].item.geometry`, native grids, manifest polygons, and the saved geometry audit linked in the [response](reviews/2026-09-16-codex-stage-4-review-response.md).

The footprint union also reports zero uncovered support, but its geometry cannot resolve validity at pixel scale.
The original strict footprint preference failed for all 76 Lanier groups and all 75 Okeechobee groups.
Consequently, ranking used uncovered footprint fraction, cloud cover, and time. Source: `plan.selection.*.groups[].score`.
Future selection drops that strict preference. Footprint unions remain coarse ranking hints, with band validity checked from pixels and asset metadata.
Native tile candidates remain included when catalog footprints omit their support, avoiding exclusions based on these coarse edges.

**Per-band no-data.** Each workload includes 1,034 declared no-data entries among 62,579,464 selected band-pixel entries, spread across eight contributions.
These counts retain separate bands and overlapping tile observations. They are not counts of unique ground pixels.

| Anchor | Tile | NIR no-data entries | Red no-data entries |
|---|---|---:|---:|
| Lanier | 16SGC | 56 | 0 |
| Lanier | 16SGD | 222 | 0 |
| Lanier | 17SKT | 11 | 0 |
| Lanier | 17SKU | 640 | 0 |
| Okeechobee | 17RNK | 16 | 3 |
| Okeechobee | 17RNL | 73 | 13 |

Sources: `runs[].contributions[].nodata_extracted`, `value_min`, and `summary.workloads[].totals.pixels_extracted`.
The zeros occur in 10 m bands. No pond contribution or tested 20 m or 60 m band contains declared no-data.
All selected 20 m SCL entries are nonzero, with minima from 2 to 4 across contributions.
This establishes SCL coverage on its selected native pixels. It does not locate the 10 m zeros or classify them as water.
The saved summaries lack a spatial crosswalk from those zeros to SCL, and extraction includes near-land pixels.
The asset's declared no-data value identifies these missing band values independently of SCL. Stored zero is not evidence of physical zero reflectance.
Their cause remains unknown. Different grids' aggregate zero counts motivate Stage 5 checks but do not establish matched-ground pixel differences.
The [contract discussion](data-contract.md#questions-for-the-next-contract-revision) carries this distinction forward.

**Split datastrips.** A datatake and tile can contain multiple valid products, even without reprocessing.
The original selection mislabeled six items as superseded revisions in two groups.
The following discarded products have different datastrip identities from their retained counterparts:

| Discarded item | Retained item's sensing component | Discarded item's sensing component |
|---|---|---|
| `S2C_T16SGC_20251010T162737_L2A` | `S20251010T163403` | `S20251010T162737` |
| `S2C_T16SGD_20251010T162737_L2A` | `S20251010T163403` | `S20251010T162737` |
| `S2C_T17SKT_20251010T162737_L2A` | `S20251010T163403` | `S20251010T162737` |
| `S2C_T17SKU_20251010T162737_L2A` | `S20251010T163403` | `S20251010T162737` |
| `S2B_T17RMK_20250906T160508_L2A` | `S20250906T160548` | `S20250906T160508` |
| `S2B_T17RNK_20250906T160508_L2A` | `S20250906T160548` | `S20250906T160508` |

Sources: `plan.selection.*.groups[].discarded` and `s2:datastrip_id` in `data/cross-tile-extraction/full-plan.catalog.json`.
The paired footprints overlap. Treating one as a replacement can discard distinct coverage.
The measured winning groups contain one product per tile, so this defect does not alter their extraction or timing evidence.
Future selection retains separate declared datastrips and uses item identity for worker files and contribution keys.
Unknown datastrip identities remain separate, rather than being silently collapsed.

### 24. Work organization changes the readers' costs differently

| Work organization | Reader | Median wall seconds | Wall range, seconds | Median requests | Median requested MB |
|---|---|---:|---:|---:|---:|
| Lake first | Raster mask | 100.13 | 92.67–108.93 | 494 | 325.07 |
| Tile first | Raster mask | 54.00 | 51.85–68.28 | 294 | 258.44 |
| Lake first | Lazy stack | 106.49 | 93.23–108.68 | 524 | 350.90 |
| Tile first | Lazy stack | 102.90 | 91.40–109.34 | 466 | 573.80 |

Sources: `summary.medians` and `summary.workloads`.
Each row summarizes three complete repetitions. None was excluded for errors or memory pressure.
Wall time sums parent-observed worker durations, including startup and worker assembly.
It excludes catalog selection, mask preparation, and final parent summary work. MB means decimal megabytes.

Tile-first raster reading used 40.5 percent fewer requests and 20.5 percent fewer requested bytes than lake-first raster reading.
Its median complete-workload wall time was 46.1 percent lower. These are ratios of complete-workload medians, rather than averages of per-tile ratios.
Observed file opens fell from 125 to 40 in each repetition.
This supports sharing open files and decoded blocks for this sample. Process boundaries and cache behavior change together.
Eight of seventeen pond memberships requested no additional bytes or requests in every tile-first raster repetition.
Source: `summary.per_lake_tile_band_costs`, summed across bands per membership. Shared opens and earlier lakes' reads still contribute to workload totals.
The anchors also benefit. Tile-first marginal reads range from 14.1 to 45.7 MB per Lanier tile and 1.8 to 49.1 MB per Okeechobee tile.
These are medians across repetitions, with five bands summed per tile. Finding 25 records the corresponding independent lake-first costs.

Tile-first lazy reading requested 1.64 times the bytes of lake-first lazy reading and 2.22 times those of tile-first raster reading.
Its timing ranges overlap the lake-first lazy ranges. Three repetitions do not establish a stable lazy-reader timing advantage.
The lazy recipes retain different graph extents and chunk alignment, as described in the [plan](reviews/2026-09-16-stage-4-plan.md).
Saved logs contain repeated identical ranges in eighteen tile-first lazy tile runs and three lake-first lazy tile runs.
No raster tile run contains repeated identical ranges. No imagery log reports a timeout or retry warning.
These counts come from `runs[].tiles[].log_diagnostics`, checked against the saved logs.

Lake-first lazy traffic varied from 350.61 to 357.07 MB and from 524 to 528 requests across repetitions.
The other three combinations repeated their request and byte totals exactly.
Ten workers exceeded 1.5 times the median duration for their own path, reader, and lake or tile.
That diagnostic uses `runs[].elapsed_seconds` and does not exclude those workers.
Their request and byte totals repeat, while CPU times remain close. Additional wall time occurs in read or compute calls.
For example, Okeechobee's slower lake-first raster worker took 43.17 seconds against a 26.22-second median, with identical requests and bytes.
This suggests waiting during I/O, rather than additional extraction work. The logs do not isolate network, remote service, or host scheduling delays.
The laptop, internet connection, and remote caches were not controlled.

### 25. Additional tile shares carry different read costs

These are medians of each anchor's raster-mask, lake-first bytes, summed across its five bands before taking the median across repetitions.

| Anchor | Tile | Polygon share, percent | Buffered share, percent | Requested MB |
|---|---|---:|---:|---:|
| Lanier | 16SGC | 69.02 | 63.07 | 21.10 |
| Lanier | 16SGD | 62.54 | 67.40 | 48.29 |
| Lanier | 17SKT | 70.26 | 64.45 | 20.69 |
| Lanier | 17SKU | 62.57 | 67.79 | 49.68 |
| Okeechobee | 17RMK | 16.14 | 16.71 | 23.42 |
| Okeechobee | 17RML | 0.39 | 0.44 | 1.89 |
| Okeechobee | 17RNK | 90.02 | 89.36 | 58.79 |
| Okeechobee | 17RNL | 22.70 | 22.90 | 43.77 |

Sources: `plan.selection.<region>.coverage.<anchor>.members` and `runs[].contributions`, filtered by anchor, reader, and path.
MB means decimal megabytes. Shares overlap, so adding them does not calculate covered area.
Each row measures reading that tile's observation. It does not measure unique coverage gained by adding tiles in a particular order.
For example, 17RML intersects water in the polygon, despite its small share. It is not a near-land-only case.

Read costs are not proportional to polygon shares.
They reflect the requested windows and compressed ranges for these products.
Tile-first per-lake costs are marginal after shared opens and earlier lakes, so they cannot replace these independent read costs without an ordering caveat.
No tile is dropped because its contribution is small or overlaps another tile.

Lake-first raster reads requested 8.53 bytes per selected band-pixel entry for Lanier and 2.77 for Okeechobee.
Selected pixels fill 17–35 percent of Lanier's windows and 35–68 percent of Okeechobee's windows, across bands and tiles.
Source: `runs[].contributions`, summing requested bytes and selected entries, with window fractions calculated per contribution.
The ratio differs by approximately threefold in these two cases. Shape, compression, window alignment, and tile overlap are not isolated experimentally.
Both anchors use four tiles in this run. These results do not establish that the zone boundary caused the bytes-per-entry difference.
Distinct tiles remain a scale driver, alongside polygon shape and window occupancy.

### What stage 4 does not show

- Scientific agreement between overlapping tile observations, or which observation to prefer.
- Stored-pixel readback, physical concatenation cost, a storage format, or an orchestrator.
- A resolved primary-tile policy. Ambiguous roles remain null, with proposed largest-share choices recorded separately.
- AWS throughput, AWS cost, production density, or performance across a season.
- Reader tuning. This run fixes the GDAL cache, lazy chunks, thread count, and per-lake compute recipe.
- Independently metered network bytes. GDAL records requested ranges, including repeated requests.

The owner accepted the response on 2026-09-17. The [inventory](options-inventory.json) and [presentation](s2-options.html#stage-4) include these corrected findings.
