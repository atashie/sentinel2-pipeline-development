# Stage 2, one lake at a time: prepared 2026-09-14, run 2026-09-15

Author: Claude Code (AI coding agent), directed by the repository owner.

Scope: the stage 2 script, the pixel-class module, their fixture tests, the run of 2026-09-15, and the documentation that points at them.
The first sections are the statement written before the run, kept as history. The run, its findings, and the corrections after [Codex's review](2026-09-15-codex-stage-2-review.md) follow. Stage 1 and the earlier reviews are in commit `6772683`.

## The step, as stated before the run

The owner authorized this step on 2026-09-14 after the stage 1 review: "commit and push. Then start stage 2".
Stage 2 in the [work plan](../work-plan.md) is one lake at a time. Every pilot size class, four methods, one acquisition per region.
This step delivers the script, the exact pixel-class computation, fixture tests, and declared tolerances. The runs happen when the owner invokes the script.

Acceptance checks for this step:

1. The three pixel classes of assumption A20 come from exact polygon areas, not sampling. On fixtures the summed coverage equals the polygon area within 1e-9 relative. Every pixel's class matches a brute-force geometry check at 10 m, 20 m, and 60 m.
2. The four methods run on a synthetic tile without network. The three mask methods extract identical stored integers on identical pixel sets.
3. Tolerances are declared in the script before any provider run.
4. `--dry-run` prints the plan and contacts nothing. `/check` passes.

Deferred: the runs themselves, stages 3 to 5, timings from us-west-2 (assumption A25), polygon version handling, and lakes across tiles. A lake that crosses the chosen tile's edge is extracted only inside that tile, and its share inside is recorded.

## What changed

- `pyproject.toml` and `uv.lock`: odc-stac 0.5.3 and pystac 1.15.2 in the `prototype` group. They bring dask 2026.8.0, xarray 2026.7.0, and odc-geo 0.5.3.
- [src/s2proto/masks.py](../../src/s2proto/masks.py), new. A tile grid from an item's projection metadata, polygon projection, and windows. The pixel classes with coverage and edge distance, the naive mask, index lists, and their files.
- [benchmarks/lake_extraction.py](../../benchmarks/lake_extraction.py), new. Scene selection per region, a preparation worker per lake, an extraction worker per method, the summary, the equality checks, and a guarded `--reuse`.
- [tests/test_masks.py](../../tests/test_masks.py) and [tests/test_lake_extraction.py](../../tests/test_lake_extraction.py), new. Twenty-three test cases on synthetic grids, polygons, and GeoTIFFs. The suite holds 133.
- [work-plan.md](../work-plan.md): the first stage 2 box checked. [benchmarks/README.md](../../benchmarks/README.md), [CLAUDE.md](../../CLAUDE.md), the root README, the Prototyping status table, and the reviews index updated.

## How the pixel classes are computed

Practice P1 rasterizes each polygon once per tile and resolution. The prototype does it this way:

- The polygon is projected to the tile's UTM zone and cut to the tile extent. The window is its bounds plus the near-land distance and one pixel.
- The boundary is rasterized with GDAL's all-touched rule and grown by one pixel. Those pixels are the only ones the boundary can pass through.
- Each of them gets its exact intersection area with the polygon. The polygon is clipped to 2 km blocks first, so a detailed shoreline is not intersected with every pixel.
- Every other pixel is entirely inside or entirely outside, decided by its centre.
- Interior is coverage 1, shoreline is coverage between 0 and 1, both within a tolerance of one millionth of a pixel. Near-land is coverage 0 with the centre within 100 m of the boundary, assumption A21, by exact distance to the boundary segments.
- Edge distance is signed, negative inside, as the [draft contract](../data-contract.md) states. It is exact up to 1,000 m. Farther interior pixels carry no distance. That cap is a prototype parameter, recorded in every mask file, not a contract change.
- The mask window is the bounding box of the classified pixels. The index-list form holds the same pixels as rows and columns in row-major order.

During development the masks of the largest anchors computed in seconds to tens of seconds on the laptop. That is a development observation, not evidence. The run records the figure per lake in its result file.

## The four methods, per scene

| Method | Per scene | What it selects |
|---|---|---|
| `naive-clip` | Project the polygon, take its bounding window, read it, rasterize the polygon with the all-touched rule, keep the marked pixels | Pixels GDAL marks as touched. No classes, no coverage, no near-land |
| `raster-mask` | Load the saved class arrays, read the mask window, keep pixels with a class | Interior, shoreline, and near-land, with coverage and edge distance |
| `index-lists` | Load the saved row and column lists, read their bounding window, index into it | The same pixels as `raster-mask` |
| `lazy-stack` | Load the saved class arrays, build an odc-stac lazy array on the mask window in native projection, compute it, keep pixels with a class | The same pixels as `raster-mask`, through a different reader |

Every extraction run is a fresh process with cold GDAL caches. Per band it records the window, the pixels and bytes in it, and the requests and bytes requested from GDAL's log. It also records open and read seconds, pixels extracted per class, no-data among them, and a digest of the values.
Per run it records wall and CPU seconds, peak resident memory, the network counter delta, and output bytes. Output bytes are row, column, class, and value fields per extracted pixel, not a stored file.
Preparation runs once per lake in its own process, all resolutions together, and is timed apart from extraction.

The default band set is one file per resolution plus the classification and near-infrared: `red`, `nir`, `swir16`, `coastal`, `scl`. `--bands all` reads the seventeen Collection 1 assets.

## Scene selection

Per region, the script searches Collection 1 for items intersecting the box around the region's lakes, from 2025-06-01 to 2025-10-31 by default.
The tile that holds the most lakes entirely wins, ties broken by the summed share inside, then by the smaller tile id.
The item whose data footprint covers the most of those lakes wins, ties broken by the lowest cloud cover, then by the latest creation time.
The chosen item is saved in full, and the result records every candidate tile and each lake's share inside the tile and the footprint.
Cloud cover changes compression, so bytes, not the method comparison. Only Collection 1 is read. The older copy's stored values are offset differently, finding F-23.

## Tolerances, declared before any run

- Stored integers extracted by different methods for the same pixel must be identical. Zero tolerance.
- The three mask methods must select identical pixel sets. Zero tolerance.
- The naive method selects what GDAL's all-touched rasterization marks. Its difference from the exact interior and shoreline set is counted in preparation and reported. It is not tolerated away.
- Coverage summed over pixels must equal the polygon area inside the tile within 1e-6 relative.
- The lazy stack's output must sit on the requested native window exactly. Any other grid is recorded and not compared.
- Timing carries no tolerance. Three repetitions by default, medians reported, every run listed.

## What the fixtures showed

- GDAL's all-touched rule marked a neighbouring pixel of the 6 m fixture pond that the polygon does not touch. The exact classes do not. The preparation counts such pixels, and the equality check expects the naive digest to differ exactly when the counts do.
- odc-stac returned the requested native window exactly, with the same integers as a direct windowed read. Its GDAL debug lines were captured through its worker threads.
- A multipolygon lost every boundary segment in an early version, because shapely's ring extraction ignores multipolygons. The fixture with a hole and a second part caught it. The module now refuses a polygon without boundary segments.

## Limits, as stated before the run

- Nothing is measured yet at this point. The run below changes that.
- Request counts for the lazy stack rely on GDAL's debug log reaching the rasterio logger from dask threads. That held on local files. The run will show whether it holds over HTTPS.
- One acquisition per region, chosen by the rule above. Other dates, tiles, and processing versions are not exercised.
- Fixture numbers are synthetic. They test arithmetic and agreement, not cost.
- The edge-distance cap and the near-land distance are prototype parameters, recorded in every mask file.

Run commands, for the owner:

```sh
uv run python benchmarks/lake_extraction.py --dry-run
uv run python benchmarks/lake_extraction.py --regions lanier --lakes nhd-34972105 nhd-41276069 --repeat 1
uv run python benchmarks/lake_extraction.py
```

The smoke run reads two small Lanier ponds once with every method. The full run is 384 extraction runs over 32 lakes, five files each, plus one preparation per lake.
The five anchors dominate. Lake Okeechobee's 10 m window is about half a tile. Expect more than an hour on the laptop.

## The runs, 2026-09-15

The owner authorized the run on 2026-09-15: "Proceed with the run". The sequence was the smoke run, then the full run, then two rewrites of the summary.

1. Smoke run, two Lanier ponds, one repetition, output kept under `data/lake-extraction/smoke.json`. Eight runs, none failed. Every method agreed on every band, and the lazy stack's requests were captured over HTTPS. Each pond cost 15 requests and 3.7 MB for five files, whichever method ran.
2. Full run, started 13:21 UTC, pixels read until 13:41 UTC: 384 runs, none failed. Two lakes lay entirely outside the tile chosen for their region, so their 24 runs read nothing. Findings 16 to 18 in [measurements.md](../measurements.md) hold the numbers. The Prototyping tab gained a stage 2 chapter fed by the renderer, and finding F-24 entered the inventory.
3. The first summary pooled runs across the lakes of a size class and took pixel counts from the first run. I rewrote it to take medians of each lake's own medians and to summarize preparation per size class. It now counts distinct tiles and tile-dates, as the benchmark rules require.
4. The first rewrite with `--reuse`, raw directory 13:44 UTC, repeated 114 runs instead of reusing them. The guard compared asset lists in order, and the lazy stack records its bands grouped by resolution. It re-read 90 lazy stack runs and 24 empty runs. My fix to the guard failed to apply, so the second rewrite at 13:50 UTC repeated the same 114 runs again. Together the two accidental repeats requested another 1,643,860,112 bytes of imagery. The guard now compares sorted lists, with a test. The rewrites at 13:56 and 14:01 UTC reused all 360 measured runs and repeated only the 24 empty ones, without network.
5. The summary then included the two lakes outside their tile in the class medians. They are now counted apart. The result file's runs are the original pass, which started between 13:23:11 and 13:41:53 UTC. Its `measured_at` is the last rewrite, 14:01 UTC, and `pixels_read_between` holds the run times.
6. Empty masks lacked the naive-difference counts, which the first summary rewrite tripped over. Every mask now carries the same count keys. The saved masks of the run predate that change and the summary tolerates them.

What the run showed beyond the findings:

- The scene rule chose tile 16SGD for the two smoke ponds and 17SKU for the whole Lanier region. The region's anchor and three ponds sit in 17SKU. A per-lake tile list would have kept every pond.
- Preparation time is dominated by edge distances on the largest lakes and by exact intersections along a detailed shoreline. Lake Lanier's 84,468 vertices took 19.3 s. Lake Okeechobee's 12.4 million interior pixels took 17.5 s at 1.56 GB.
- The catalog search returned about 75 items per tile for the five-month window, 26.1 MB of JSON for six regions. Bounding-box search over a region returns every tile the box touches, four to six per region.
- GDAL's all-touched rule marked 198 pixels below the coverage threshold on seven lakes, against six the threshold kept and GDAL missed. Codex's review found that 197 of the 198 have a sliver of positive intersection and one has none. The counts are in the result.

## Dispositions of Codex's stage 2 review, 2026-09-15

All seven findings and the smaller corrections were accepted. Nothing was pushed back.

| Finding | Disposition |
|---|---|
| 1. Tile clipping created false shoreline distances for the three lakes partly outside their tile | **Fixed.** The mask keeps the original polygon for every distance and clips only the window to the tile. A tile edge is never a shoreline. A crossing-tile fixture asserts 405 m where the old code gave 5 m. A lake outside the tile now yields its near-land pixels inside it. Masks carry a version number. All 30 lakes' masks were recomputed offline with the corrected code and compared with the saved ones. 27 are identical. Lanier and Okeechobee differ on 77 and 171 near-land pixels at 10 m where the shoreline meets the tile edge. Distances differ on 15,134, 31,678, and 440 pixels at 10 m for Lanier, Okeechobee, and the Alaska lake. The saved masks are marked affected in finding 18. The comparison is saved under `data/lake-extraction/` |
| 2. 197 of the 198 "nonintersecting" pixels intersect the polygons | **Corrected with evidence.** They have a sliver of positive intersection below the coverage threshold of one millionth of a pixel. Finding 17, F-24, the page, and the CLAUDE gotcha now describe two selection rules that differ on 204 pixels. The counts split slivers from empty contacts in every new mask. The one empty intersection stays uninvestigated |
| 3. The one-block headline missed an exception and confused blocks with requests | **Corrected with evidence.** The Alaska 300 m lake sits across a block boundary in every file: 10 blocks, 20 requests, 4.3 MB. Finding 16 now says 24 of 25 small lakes fit within one block per file. It reports blocks apart from requests and keeps latency as an inference. Every band record now carries the blocks its window intersects |
| 4. Extraction reuse could retain results from an earlier polygon or mask | **Fixed.** Extraction results carry their inputs: polygon digest, grid, mask file digests, mask parameters, and implementation version. Reuse requires them to match and rejects any saved run with a band error. Preparation reuse binds parameters and implementation and verifies the copied mask files against their digests. Fixtures cover changed geometry, grid, masks, and failed bands. The 2026-09-15 results predate these fields and cannot be reused |
| 5. Value hashes did not enforce pixel sets or completeness | **Fixed.** Every band record now carries a digest of tile rows, columns, and classes beside the value digest. The equality summary compares both and lists the planned methods and repetitions each comparison is missing. It counts runs with pixels, without a pixel in the tile, with band errors, and failed. The 2026-09-15 records have no pixel digest, so that column reads unknown for them |
| 6. Presentation counts and method conclusions exceeded the summaries | **Corrected with evidence.** The summary takes per-lake totals before medians. The page and finding 16 show the median lake's 10 m pixels, all classes. The "four methods agree" claims are now three mask methods. The storage-not-extraction and no-saving conclusions are removed. Finding 17 reports the anchor timings where the lazy stack read faster, the bytes per anchor, both timer scopes, and the fixed order |
| 7. The rerun history understated repeated provider reads | **Corrected with evidence.** The run section now lists both accidental repeats and their 1.64 GB. `--resummarize RESULT` regenerates a summary from the saved runs without touching the catalog, and records `summary_generated_at` and `pixels_read_between` apart from `measured_at` |
| Coverage error 2.4e-11, Tahoe's timings, Alaska counts, the Alaska body's class, the work-plan and record wording, the CLAUDE latest-review link | **Fixed.** Each is corrected in place |

## Dispositions of prior findings

| Finding | Disposition |
|---|---|
| Codex, 2026-09-14: review the bounded stage 2 statement with the owner, and start no stage 2 run from that review | **Fixed.** This record was the statement. The owner authorized the run after reading it |
| Codex, 2026-09-14: keep the original result files unchanged and document any later script differences | **Fixed.** The stage 1 result files are unchanged. The stage 2 result was rewritten from its own saved runs three times, each rewrite recorded above with its reason |
| Codex, 2026-09-12: the manifest option finds candidate tiles, not the water bodies' tiles | **Accepted and deferred.** Stage 2 resolves tiles per region from the catalog and records each lake's share inside the tile. The survey rerun remains pending |
| Codex, 2026-09-12: refetching always writes polygon version 1 | **Accepted and deferred.** Every mask file records the polygon digest it came from. Version handling waits for refreshed geometry |

## Verification

- Before the run: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q` passed in order, 133 passed. The three `--check` tools passed. `--dry-run` printed 32 lakes, 4 methods, and 384 extraction runs without network access.
- After the run: the same sequence passed with 136 passed, including three new renderer tests and the reuse guard test. `git diff --check` passed.
- After Codex's review: the same sequence passed with 144 passed, including the crossing-tile, outside-lake, naive-split, block-count, input-bound reuse, completeness, and resummarize fixtures. The three `--check` tools, `--dry-run`, and `git diff --check` passed. The result file was resummarized offline once, with `--resummarize`, and its runs are unchanged.
- The result file `benchmarks/results/lake-extraction.json` was written by the script and rewritten by it with `--reuse`. Nothing was edited by hand. Nothing was committed, pushed, or published in this step.

## Proposed next step, not started

1. Commit on the owner's authorization.
2. Stage 3 statement: many lakes in one tile. The same methods reading every pilot lake of a tile, per-lake reads against one shared whole-tile read, and lake-by-lake order against tile-by-tile order. Tile membership per lake from the polygon, so no lake is left outside. Stage 2's per-lake numbers are the baseline it is compared with.
