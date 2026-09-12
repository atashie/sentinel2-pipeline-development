# Data gap survey plan, 2026-09-10

Authority: [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md), which requires this survey before any substantial analysis of the 2021 scenario. Step 3a in [work-plan.md](work-plan.md).
Results are in [measurements.md](measurements.md). The script is [../benchmarks/gap_survey.py](../benchmarks/gap_survey.py).

## Question

For the tiles a pilot set touches, which months from 2021-01-01 to the present lack Level-2A items in Earth Search's Collection 1 collection?
For each missing acquisition, does the older Earth Search collection hold it, and at which processing baseline?
Which quality assets does each collection deliver, and does that change with baseline or with the provider's ingestion software?

## Bounds

- Catalog metadata only. No imagery byte is read. No bucket is listed. No credentials are used.
- Earth Search is the route (assumption A13). The Copernicus Data Space Ecosystem catalogs serve one purpose: a reference count of what ESA lists today. They are not a route and are not compared for selection.
- Every request is logged in the result file with host, path, status, bytes, and seconds.
- One request stream, with a pause between requests and backoff on throttling.

## Sites and tiles

The pilot manifest is empty. The survey uses named public water bodies as points, listed in [../benchmarks/gap-survey-sites.json](../benchmarks/gap-survey-sites.json) with the reason for each.
Seventeen sites lie in the United States, the service area of assumption A4. Three context sites outside it show whether a gap is regional or global.
One site straddles a UTM zone boundary, so it lies in two tiles.

Tiles are discovered from the catalog, not computed. For each site, the survey lists Collection 1 items whose footprint covers the point in the last year and takes their tile codes.
A tile whose items never cover the point in that year is not surveyed. That limit is recorded in the result file.
Rerun the survey on the pilot manifest's tiles when the manifest is populated.

## Collections and window

| Collection | Role in the survey |
|---|---|
| `sentinel-2-c1-l2a` | Primary. The preferred assets of decision 0003 |
| `sentinel-2-l2a` | Fallback. The older Earth Search collection, the same operator's earlier GeoTIFF conversion of the same ESA products, in the `sentinel-cogs` bucket |
| `sentinel-2-pre-c1-l2a` | Listed for completeness. Its extent is measured, not assumed |
| `sentinel-2-l1c` | Acquisition reference within Earth Search. Level-1C exists for every Level-2A product |
| Copernicus STAC `sentinel-2-l2a` | External reference. What ESA lists today per tile and year |
| Copernicus OData products | Second external reference. A per-year count that checks the STAC listing |

The window runs from 2021-01-01 to the run date, one calendar month at a time. The run date is recorded as `window.end`.

## What is recorded per item

The listing keeps a fixed set of fields per item. They are the id, sensing datetime, platform, tile code, processing baseline, sequence, and the provider's ingestion software version. They also include the `earthsearch:boa_offset_applied` flag, cloud cover, no-data percentage, product URI, generation time, and the catalog's created and updated times.
Assets are excluded from the listing to keep responses small. Raw listings are written under `data/gap-survey/`, outside git, and their SHA-256 digests are in the result file.

## Quality assets to list

For every distinct combination of collection, ingestion software version, and baseline seen in the listings, the survey fetches one full item and records:

- every asset key present,
- for `scl`, `cloud`, `snow`, `aot`, `wvp`, and their `-jp2` alternates: host, media type, resolution, data type, scale, offset, and no-data value,
- the red band's host, scale, and offset, as the offset indicator the provider's README names,
- the item's storage properties, including whether the bucket is requester pays.

## Gap definitions

An acquisition is a distinct pair of sensing date and platform letter within one tile. Item counts are reported beside acquisition counts but never used alone, because one acquisition can appear as several items.
Two products of one tile from one pass, split across datastrips, collapse into one acquisition. The result file states this limit.

Per tile and month, the survey compares acquisition sets:

| Status | Meaning |
|---|---|
| `complete` | Every reference acquisition is in Collection 1 |
| `partial` | Some reference acquisitions are missing from Collection 1 |
| `empty` | The reference has acquisitions and Collection 1 has none |
| `primary_only` | Collection 1 has acquisitions and the reference has none |
| `no_reference` | Neither has any |

For every missing acquisition, the survey records whether the older collection holds it (`covered_by_fallback`) or nothing on the route holds it (`uncovered`). It lists every uncovered acquisition by key.
The same comparison runs for the older collection alone against the reference.

## Consistency checks

- Per tile and collection, the sum of the aggregation endpoint's monthly counts must equal the number of items listed. The result records whether they agree.
- Per tile and year, the Copernicus OData count must equal the Copernicus STAC count. The result records whether they agree.
- Every listed item must carry the tile code queried. Mismatches are counted.

## Outputs

1. [../benchmarks/results/gap-survey.json](../benchmarks/results/gap-survey.json). It carries `measured_at`, code version, endpoints, request counts and bytes by host, per-tile results, asset samples, a cross-tile summary, the request log, and limitations.
2. Raw listings under `data/gap-survey/<measured_at>/`, one file per tile and collection. Not committed.
3. Gap tables and interpretation in [measurements.md](measurements.md).
4. A fill policy per gap, decided by the owner and recorded in a new decision. This survey proposes options and does not decide.

## Fallback survey

The owner asked on 2026-09-10 for a second survey that treats the older collection's GeoTIFFs as the fallback. [../benchmarks/fallback_survey.py](../benchmarks/fallback_survey.py) reads the first survey's result and takes every tile and month marked empty or partial.
For each such span it lists Collection 1 items, the older collection's items with their assets, and the Copernicus reference again. It classifies each older-collection item by its assets:

| Class of a missing acquisition | Meaning |
|---|---|
| `complete_cog` | An older-collection item has all twelve reflectance bands and the scene classification as cloud-optimized GeoTIFFs in the public `sentinel-cogs` bucket |
| `partial_cog` | Some GeoTIFF assets in that bucket, not the full set |
| `jp2_only` | Only JPEG 2000 assets, which point into the Sinergise bucket |
| `uncovered` | No older-collection item |

It also records whether aerosol and water vapour are GeoTIFFs, and whether cloud and snow probability exist at all. For each tile and month it sends a HEAD request, without credentials, for the scene classification and red band objects of the first `complete_cog` item.
A HEAD returns headers only: status, size, entity tag, storage class, and whether the requester was charged. No pixel is read.

## Report

`tools/gap_report.py` computes a machine-readable report from both result files and the probe record. It writes [reviews/2026-09-10-gap-survey-report.json](reviews/2026-09-10-gap-survey-report.json).
Every number in the report comes from the inputs. `--check` fails when the committed report no longer matches them, and `tests/test_gap_report.py` runs that check.

## Rerun

1. Run `uv run python benchmarks/gap_survey.py` from the repository root.
2. Wait for the final line, which names the result file and the request total.
3. Update the tables in [measurements.md](measurements.md) from the new file.
4. Run `uv run python benchmarks/fallback_survey.py`, then `uv run python tools/gap_report.py`.
5. Run `/check`.

Pass `--max-sites 1 --output data/smoke.json --raw-dir data/smoke` for a smoke run that writes no evidence.
Pass `--tiles 10SGJ 11SKD` to survey named tiles without discovery. Pass `--no-reference` to skip the Copernicus catalogs.
