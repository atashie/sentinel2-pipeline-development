# Stage 3, many lakes in one tile: statement, implementation, runs, corrections, and the rerun, 2026-09-15

Author: Claude Code (AI coding agent), directed by the repository owner.

Scope: the stage 3 script, its fixture tests, the declared tolerances, and the documentation that points at them.
The first sections are the statement written before the run, kept as history. The runs, their outcome, the corrections after [Codex's review of the run](2026-09-15-codex-stage-3-review.md), and the rerun of 2026-09-16 follow.
[Codex's pre-run review](2026-09-15-codex-stage-3-prerun-review.md) of it is applied below. Stage 2, its run, and Codex's stage 2 review are in commit `535357c`.

## The step

The owner authorized this step on 2026-09-15 after compacting memory: "start stage 3".
Stage 3 in the [work plan](../work-plan.md) is many lakes in one tile. The same methods read every pilot lake of a tile. Per-lake reads are compared with one shared whole-tile read, and lake-by-lake order with tile-by-tile order.
The [stage 2 record](2026-09-14-stage-2-one-lake-at-a-time.md) added two requirements. Tile membership comes from the polygon, so no lake is left outside. Stage 2's per-lake numbers are the baseline.

This step delivers the script, the tile and membership rules, three read patterns, fixture tests, and declared tolerances.

Acceptance checks for this step:

1. Every pilot lake is placed in a tile. A lake whose polygon buffered by the near-land distance intersects a tile is a candidate member, and preparation verifies its pixels. On the fixture, a lake 30 m outside a tile is a member with near-land pixels only. A lake 98 m outside is a candidate with no pixel, and a lake that only a second tile holds gets that tile chosen.
2. Three patterns and four methods extract identical stored integers on identical pixel sets on a synthetic tile with four lakes. Twelve combinations, every band, every lake. Extraction from a whole tile in memory equals the windowed reads.
3. The values equal stage 2's worker on the same fixture. Mask methods are compared with stage 2's mask methods and the naive clip with stage 2's naive clip. The summary carries stage 2's per-lake sums for the same acquisition and band set, and names the lakes without a baseline.
4. Tolerances are declared in the script before any provider run. Expected records come from the chosen scenes and the plan, so a missing lake, band, or repetition is reported. The order of patterns and of methods within them rotates between repetitions, and the plan records it.
5. `--dry-run` contacts nothing. `/check` passes.

Deferred: the run itself, stage 4 and stage 5, and timings from us-west-2 (assumption A25).
A lake partly inside a tile is read inside that tile only, with its share recorded. Its other tiles are stage 4 work, as is the primary-tile rule of assumption A22.
A single labelled mask per tile, one array of lake ids, is not prototyped or timed. The whole-tile pattern extracts each lake with its own mask from the shared array.
The catalog grid codes are normalised in this script only. Stage 2's script is unchanged.

## What changed

- [benchmarks/tile_extraction.py](../../benchmarks/tile_extraction.py), new. Tile selection per region merged across regions, candidate membership per lake, and one item per tile. A preparation worker per lake and tile, and an extraction worker per pattern and method, each run under a memory budget. The stage 2 baseline by method family, the summary with expected coverage, the equality checks, a guarded `--reuse`, and `--resummarize`. It imports stage 2's helpers, band sets, methods, and worker pieces.
- [benchmarks/lake_extraction.py](../../benchmarks/lake_extraction.py): the value and pixel-set digests accept an empty array and return the digest of no bytes. Non-empty digests are unchanged. No stage 2 record held an empty selection, so the 2026-09-15 results are unaffected and the implementation version stays.
- [tests/test_tile_extraction.py](../../tests/test_tile_extraction.py), new. Eighteen test cases on two synthetic tiles that overlap by half, with five lakes and 128-pixel lazy chunks. The suite holds 164.
- [work-plan.md](../work-plan.md): the first stage 3 box checked. [benchmarks/README.md](../../benchmarks/README.md), [CLAUDE.md](../../CLAUDE.md), the root README, and the reviews index updated.

## How tiles, items, and members are chosen

Per region, the script searches Collection 1 for items intersecting the box around the region's lakes, from 2025-06-01 to 2025-10-31 by default. Grid codes are normalised to a two-digit zone before grouping, finding 18.

- A tile places a lake when it holds the lake entirely. A lake no tile holds entirely is placed by the tile with its largest share, ties broken by the smaller tile id.
- Tiles are chosen greedily. The tile placing the most unplaced lakes comes first. Ties are broken by the summed share of those lakes inside it, then by the smaller tile id. Selection stops when every lake is placed.
- A lake is a candidate member of a chosen tile when its polygon buffered by 100 m intersects the tile extent. Preparation verifies the candidate: a pixel centre within 100 m of the polygon may still be absent. Members are read whether the tile holds all, part, or none of the polygon.
- Per tile, the item whose data footprint covers each member's support, the buffered polygon cut to the tile, for the most members, wins. Ties are broken by the lowest cloud cover, then by the latest creation time.
- A tile chosen for two regions is merged before its item is chosen, so one item serves the union of members.

The result records every candidate tile with the lakes it places and its members. It records the chosen tiles, each member's share inside the tile and the footprint, and any lake no tile places.
Expected before the run, superseded by the run below. From stage 2's placements, the pilot needs at least eight tiles. The six stage 2 tiles place 30 lakes. The Lanier 100 m pond and the Okeechobee 30 m pond each need another tile. Lake Lanier is placed in 17SKU by its largest share, and the Alaska 1,000 m lake in 05VMG. The catalog decides at run time.

## The three patterns

| Pattern | Loop order in one run | What the lazy stack does |
|---|---|---|
| `lake-by-lake` | Lakes outermost. Every file is opened again for each lake and the lake's window is read. Stage 2's order in one process, so GDAL's caches stay warm between lakes | One lazy array per lake and resolution on the lake's window, as in stage 2 |
| `tile-by-tile` | Files outermost. Each file is opened once and every lake's window is read from it before the next file | One graph per resolution on the whole tile, then each lake's window computed from it separately. Decoded chunks are not retained between computations |
| `whole-tile` | Each file is read entirely once, one shared read. Every lake is extracted from memory | One lazy array per resolution on the whole tile, computed whole, then each lake extracted from memory |

Every run is one fresh process for one tile, one pattern, one method, and one repetition. It reads every member lake and every asset of the default band set: `red`, `nir`, `swir16`, `coastal`, `scl`.
Per file it records the opens the script asked for and the opens GDAL logged. It records open and read seconds, and requests and bytes from GDAL's log. It records the pixels in the windows or the whole tile. The rasterio methods record three block counts. Those are the blocks the lakes' windows touch summed over lakes, the distinct blocks among them, and the blocks in the file. The lazy stack records logical loads and computes instead of opens, and chunk counts relative to its graph's origin. Its block counts are unknown.
Per lake and file it records the window and the lake's own requests and bytes where a read happened. It records the read or compute seconds and the extraction seconds from memory. It records the pixels per class, the value digests, and the pixel-set digests of stage 2.
A member lake can have no pixel for a method, such as the naive clip on a lake outside the tile. It gets a zero-pixel record with a note, not an error.
Per run it records wall and CPU seconds, peak resident memory, the network counter delta, setup per lake, and output bytes.
Patterns and methods both rotate. Repetition r shifts the pattern list and the method list by r minus one positions. A pattern group and the methods within it both change position. Three methods lead a group across three repetitions. The plan in the result lists the order. Rotation reduces an ordering bias and removes no network variation.

Preparation runs once per lake and tile in its own process, all resolutions together, with stage 2's worker. Every mask is version 2, with distances to the real boundary.
The lazy stack runs on four Dask threads, and GDAL's block cache is set to 512 MiB, in bytes, since `rasterio.Env` takes bytes. Stage 2 used GDAL's default cache. Both settings are recorded in the result, and each worker records the cache it held. The run of 2026-09-15 held 512 bytes, see the corrections below.

## Stage 2 as the baseline

The summary reads stage 2's result file. For each tile and method it sums stage 2's per-lake medians of requests, bytes, read seconds, and wall seconds. The sum covers the tile's members that stage 2 read from the same item, and only when the band set is stage 2's. It names the members without a baseline: another item, another tile, or not read in stage 2.
The equality checks compare each lake's interior-plus-shoreline value digest with stage 2's for the same lake, item, and band. Stage 2's digests are kept by method family. The mask methods are compared with stage 2's mask methods and the naive clip with stage 2's naive clip. The two families select different wet pixels on 29 of stage 2's 150 checks. Whether stage 2's own mask digests agree is recorded apart.
Two lakes' near-land sets changed with the mask correction, finding 18. Their interior and shoreline sets did not, so the comparison holds for them.
Stage 2 ran every lake in its own process. The baseline is therefore the cold-cache cost of reading the tile's lakes one process at a time.

## Tolerances, declared before any run

Stage 2's tolerances stand. Values and pixel sets are identical across the three mask methods. The naive difference is counted, not tolerated away. Coverage is within 1e-6 relative, the lazy stack's grid is exact, and timing has no tolerance. Stage 3 adds:

- Every pattern must extract identical stored integers on identical pixel sets for the same lake, band, and method. Zero tolerance. Whole-tile extraction from memory is compared with the windowed reads through the same digests.
- A lake's interior and shoreline values must equal stage 2's mask methods for the same lake, band, and acquisition. Its naive values must equal stage 2's naive clip. Zero tolerance. A lake read from another acquisition has no comparison, which is recorded. Timing sums from stage 2 are compared only for the same band set.
- Buffer intersection makes a lake a candidate member. Preparation verifies its selection. A candidate whose masks hold no pixel at any resolution is recorded as such. That is a valid outcome of the near-land rule, kept apart from failed preparation and missing data.
- Expected lake-band records come from the chosen tiles' members and assets and the plan, before any record is examined. A missing member, band, or repetition makes the comparison incomplete. Runs with errors or memory pressure stay out of timing medians and are counted.
- Patterns and methods both rotate their order between repetitions. The plan records the order of every run.

## What the fixtures showed

- All twelve combinations agreed on every band of five lakes, including a lake 30 m outside the tile that has near-land pixels only. Whole-tile extraction from memory gave the same digests as the windowed reads. The values equal stage 2's worker on the same fixture, family by family.
- The per-lake block sum exceeds the file's block count when lakes share blocks. On the fixture red band the lakes' windows touch more blocks summed than the 225 in the file, and fewer are distinct. The anchor's window holds the ponds. That sharing is what the pilot run measures.
- A lake 98 m outside the tile is a candidate member whose masks hold no pixel at any resolution. The nearest pixel centre is 103 m from it. It is recorded as a member without a pixel, and every method returns an empty record for it.
- The naive clip selects nothing for the lake outside the tile, because it has no near-land class. An empty selection crashed the pixel digest until the digests accepted empty arrays.
- With 128-pixel chunks the fixture tile spans four chunks at 10 m. The anchor touches four chunks in either graph. A window at row 90 and column 118 touches two chunks of the tile graph and one chunk of its own graph. GDAL's log shows the opens the lazy reader made, which the script no longer counts by hand.
- In the lake-by-lake pattern no earlier lake's selections stay alive when the next lake starts. A weak-reference check in the fixture holds that for both reader families.
- A worker whose resident memory exceeds the budget is stopped and recorded as such, and a worker waits when less than the reserve is available. A run that finishes between two samples reports no peak.
- Two tiles that overlap by half place the lakes as the rule says. A lake far from every tile is reported as unplaced. Two regions choosing the same tile are merged before an item is chosen.

## Expected size of the run

Estimated from [lake-extraction.json](../../benchmarks/results/lake-extraction.json): stage 2's per-lake medians for the raster mask, and the five files' sizes its scenes record. The catalog can choose other items.

| Tile in stage 2 | Lakes | Stage 2 sum, five files per lake | Five files, whole |
|---|---|---|---|
| 10SGJ, Tahoe | 6 | 60.5 MB, 112 requests, 17.2 s | 441 MB |
| 17SKU, Lanier | 5 | 60.6 MB, 81 requests, 16.4 s | 407 MB |
| 17RNK, Okeechobee | 6 | 70.9 MB, 108 requests, 18.7 s | 476 MB |
| 16TGK, Grand Lake St. Marys | 5 | 26.7 MB, 79 requests, 11.4 s | 533 MB |
| 10TET, Washington | 6 | 30.1 MB, 100 requests, 13.3 s | 527 MB |
| 05VMG, Iliamna | 4 | 14.0 MB, 65 requests, 8.9 s | 491 MB |

Range reads skip the overviews, about a quarter of each file in stage 1, finding 13. A whole-tile run is then about 350 MB and, at stage 1's rate, about 40 s.
The full plan is 36 runs per tile. For eight tiles that is 288 runs: 96 whole-tile runs near 35 GB and 192 windowed runs near 8 GB. Expect about two hours on the laptop.
`--patterns`, `--methods`, `--tiles`, and `--repeat` reduce it. The smoke run below is one tile, twelve runs, and about 2 GB.

## Limits, as stated before the run

- Fixture numbers are synthetic and test agreement, not cost.
- One process per run. Sharing between lakes is measured within a process. Stage 2 is the reference for one process per lake.
- The whole-tile pattern extracts each lake with its own mask. A production design might label the tile once. That design is not timed here.
- The lazy stack reads chunks of 2,048 pixels, not the file's blocks. Its counts are chunks relative to each graph's origin, and its block counts are unknown. Raster opens are observed in GDAL's log for every method.
- Workers run one at a time under a 4 GiB budget and a start check that 1.5 GiB of host memory is available, both adjustable. Resident memory is sampled four times a second, so a rapid spike can escape. Page-outs during a run mark memory pressure, and such runs stay out of timing medians. The peaks stage 3 needs are unverified until the guarded checks below run.
- One item per tile. Other dates and processing versions are not exercised.
- Requests and bytes are what GDAL asked for. The network counters are machine-wide.

Run commands, for the owner:

```sh
uv run python benchmarks/tile_extraction.py --dry-run
uv run python benchmarks/tile_extraction.py --regions grand-st-marys --repeat 1 --output data/tile-extraction/smoke.json
uv run python benchmarks/tile_extraction.py --regions okeechobee --repeat 1 --output data/tile-extraction/okeechobee-check.json
uv run python benchmarks/tile_extraction.py
```

The smoke run reads one tile once with every pattern and method. Its anchor is the only multipolygon in the pilot.
The Okeechobee check exercises the largest masks and the whole-tile lazy path under the memory guard, because Lake Okeechobee gave stage 2's largest preparation peak. Read its peaks before the full run and adjust `--memory-budget-gb` if needed.
The full run reads every tile three times.

## The runs, 2026-09-15

The owner authorized the run after Codex's review: "Thereafter, we can proceed with the full run". The sequence was the smoke run, the guarded Okeechobee check, then the full run.

1. Smoke run, Grand Lake St. Marys, one repetition, output kept under `data/tile-extraction/smoke.json`. Twelve runs, none failed, 25 lake-bands complete, every digest check true, stage 2 matched on all 25. It exposed two accounting flaws before the larger runs. The observed-open counter included the in-memory datasets the naive clip rasterizes, and the page-out flag fired on every run from kilobytes of page-outs. Opens are now counted per file, and the flag needs 128 MiB of page-outs. The implementation version rose to 3, so the smoke results are never reused.
2. Guarded Okeechobee check, both Okeechobee tiles, one repetition, `data/tile-extraction/okeechobee-check.json`. 24 runs, none failed, 45 lake-bands complete, stage 2 matched on 25. The largest worker peaked at 1.45 GB by its own count, 1.40 GB as the parent sampled it, on the whole-tile lazy stack. Page-outs stayed under 7 MB per run, and no worker waited or was stopped.
3. Full run, started 20:15 UTC, pixels read from 20:18:17 to 22:02:42 UTC, first start to last completion. 324 runs over nine tiles, none failed, none stopped, none under memory pressure. Codex's review found afterwards that every worker held a 512-byte GDAL block cache, see the corrections below. The result is `benchmarks/results/tile-extraction.json`, written once by the script. Findings 19 to 22 in [measurements.md](../measurements.md) hold the numbers. The Prototyping tab gained a stage 3 chapter, and finding F-25 entered the inventory.

What the run showed beyond the findings:

- The tile rule chose nine tiles, two more than stage 2's six plus one. Lanier's tile changed. Lake Lanier lies 70.3 percent inside 17SKT against 62.6 percent inside 17SKU, so 17SKT is the only tile that places it. In the first round 16SGD and 17SKU each placed three ponds entirely inside, a summed share of 3.0, and 16SGD won by the smaller id. 17SKT then placed the two lakes left, Lake Lanier and a pond, with a summed share of 1.70. The candidate table's `summed_share_in_tile` sums every lake's share and is not that score. Each chosen tile now records the score that chose it. Eight lakes are members of two tiles.
- The 05VLG item is 81.9 percent no-data and still covers the support of its three members. Its whole-tile read compressed to 57 MB.
- Preparation of the 40 masks took 94 s in total and 20.7 s at most, for Lake Lanier in 16SGD. It peaked at 1.23 GiB for Lake Okeechobee.
- The run requested 45.6 GB in 19,741 requests, close to the estimate of 35 GB whole-tile plus 8 GB windowed. The catalog search returned 1,473 items in 24 requests and 26.1 MB.
- Every host page-out delta stayed under 7.5 MB per run, below the 128 MiB threshold, so the pressure flag never fired. The threshold and the raw deltas are in every run record.

## Dispositions of Codex's stage 3 pre-run review, 2026-09-15

All seven findings and the smaller corrections were accepted. Nothing was pushed back.

| Finding | Disposition |
|---|---|
| 1. The stage 2 comparator mixed the naive and mask families | **Fixed.** Stage 2's digests are keyed by method family. Mask methods compare with stage 2's mask methods, the naive clip with stage 2's naive clip, and the reference's own consistency is recorded apart. Timing sums require stage 2's band set. The fixture baseline holds all four methods and a lake with a known naive difference |
| 2. A failed preparation or a missing lake or band could look complete | **Fixed.** Expected lake-band records come from the chosen scenes and the plan before any record is examined. Missing members, bands, and repetitions are reported, failed and absent preparations are listed per tile, and unplaced lakes are counted. Runs with errors stay out of timing medians and errors are summed over every repetition. Fixtures cover a missing lake, a missing band, and an error in a later repetition. Codex's run review found a requested band the scene could not resolve outside the expectation, corrected on 2026-09-16 below |
| 3. Lazy opens and chunk counts described other operations than their labels | **Fixed.** Opens are observed in GDAL's log for every method. The lazy stack records logical loads and computes and no block count. Chunks are counted relative to each graph's origin, distinct chunks only on a shared graph. The tile-by-tile lazy pattern is described as separate window computations on a shared graph. The fixture uses 128-pixel chunks |
| 4. Membership and footprint scoring did not establish data | **Fixed.** Buffer intersection is a candidate test and preparation verifies the selection. A candidate with no pixel is recorded as a valid outcome, apart from failures. Items are scored by how much of each member's support inside the tile, near-land included, their footprint covers. A fixture holds a lake 98 m outside the tile and an item whose footprint misses a near-land support |
| 5. Rotation moved patterns but not methods | **Fixed.** Both lists rotate per repetition. The fixture checks the method order within every pattern group. The record no longer claims the ordering concern is removed |
| 6. Lake-by-lake retained every earlier lake's selections | **Fixed.** Each lake's selections are released before the next lake starts, in both reader families. A weak-reference fixture holds it |
| 7. Limited memory headroom without a protective stop | **Fixed** within stage 3, with two corrections on 2026-09-16 below, the cache unit and the pressure exclusion. Workers run one at a time with a fixed Dask thread count and GDAL cache. Every worker runs under a resident-memory budget with a start reserve and is sampled. An early stop is recorded as incomplete work with the partial GDAL log kept. Page-outs are recorded as memory pressure that keeps a run out of timing medians. The guarded Okeechobee check precedes the full run |
| The duplicate-tile merge wrote an item before merging | **Fixed.** Tiles are merged across regions before an item is chosen |
| Naive coordinate digests were not compared across patterns | **Fixed.** The equality rows carry that comparison |
| Resummarizing lost unplaced lakes and tolerated a missing baseline | **Fixed.** The result records the requested lakes and the selection log. A recorded baseline that is missing or changed stops the summary |
| The upper-bound claim for a labelled tile mask | **Corrected.** The claim is removed. That design is not timed |
| The root README claimed every pilot lake was read in stage 2 | **Corrected.** Thirty yielded pixels and two lay outside their tile |

## Dispositions of Codex's stage 3 review, 2026-09-16

[Codex's review of the run](2026-09-15-codex-stage-3-review.md) confirmed the coverage, the digests, and every table, and found six things to correct. All six are accepted. Nothing was pushed back.

| Finding | Disposition |
|---|---|
| 1. The cache setting invalidates the clipping-cost interpretation | **Corrected with evidence, and rerun.** `rasterio.Env(GDAL_CACHEMAX=512)` set a 512-byte block cache. Checked here on 2026-09-16: that call reports 512 from `get_gdal_config`, the environment variable `512` reports 536,870,912, and the corrected value reports 536,870,912. The script sets the cache in bytes, and every worker records the size it held. The naive clip's per-scene cost was withdrawn from finding 22, F-25, the page, and the gotcha. The rerun below replaced every number with the intended cache's |
| 2. Requested assets could disappear from expected coverage | **Fixed.** Expected lake-bands come from the members and the requested bands. A band the scene could not resolve stays expected with no resolution and is counted apart as `lake_bands_without_asset`. Tile rows list the missing and skipped assets. A fixture removes a resolved asset and still requests the band |
| 3. Memory-pressure exclusion was incomplete | **Fixed.** A combination without a clean run keeps its counts and gets no median. Per-lake medians exclude pressured runs and count them. A page cell says how many runs its median used when fewer than planned, and why a cell has none. The threshold stands beside the pressure statements in the measurements and above |
| 4. The Prototyping opening described the state before stage 3 | **Fixed.** The opening, the test-case cards, and the status table say what stages 2 and 3 established, label stage 2's counts, and keep cross-tile combination, seasons, AWS, and validation open |
| 5. Performance prose lost exceptions and turned estimates into recommendations | **Corrected.** Findings 19 to 22, F-25, and the chapter carry the 05VLG exception, the Alaska 300 m lake's requests, the lazy 05VLG time, the 0.2 MB bound, the median and maximum labels, and the anchor counts. The crossover is byte arithmetic for this lake mix. The lazy results are the tested recipe, and decoded chunks are what it does not retain |
| 6. Conventions and historical statements | **Fixed.** Sentences over 25 words are split. F-25 keeps the headline ratios and points at the findings for the rest, and the gotcha keeps no number. The 17SKU expectation is labelled superseded. The index row names the run. The guarded check's peak reads 1.45 GB by the worker's count. The interval is first start to last completion |

The numeric audit's two requests are met. The Lanier selection is explained in full above, and each chosen tile records the score that chose it.

## Corrections after the review, 2026-09-16

- `benchmarks/tile_extraction.py`: the block cache is `512 * 1024**2` bytes and each run records `gdal_cache_bytes`. Expected coverage takes the requested bands. Pressured runs are out of every median. The pixel interval ends at the last completion. Chosen tiles record their score. The implementation version is 4, so nothing from the run of 2026-09-15 is reused under the corrected cache.
- `tools/render_options.py`: a pattern cell says how many runs its median used when fewer than planned, and why a combination has no median.
- `benchmarks/results/tile-extraction.json` was resummarized offline with `--resummarize`. Every run, tile, selection, and median is unchanged, checked field by field against the copy before. The summary gained the asset and pressure fields, the interval ends at 22:02:42 UTC, and `summary_implementation` is 4. The digest in the page's generated comment is the new one. The run's own `gdal_env` still reads `GDAL_CACHEMAX: 512`, the value it held, in bytes.
- Findings 19 to 22, F-25, I-20, the page, `CLAUDE.md`, the work plan, and the READMEs state the cache and the withdrawn claim.
- The result of 2026-09-15 is kept outside git as evidence of the 512-byte configuration, see the rerun below.

## The rerun, 2026-09-16

The owner authorized it: "proceed with the full rerun". The result of 2026-09-15 was copied first to `data/tile-extraction/tile-extraction-2026-09-15-512-byte-cache.json`, digest `4a5b3e398d8060200694c44a4520dc6d28b6531952f7485c4e630ea52ca5701d`, outside git. Then `uv run python benchmarks/tile_extraction.py` ran from 12:29:55 to 14:00:23 UTC, log `data/tile-extraction/full-rerun.log`.

- 324 runs over the same nine tiles and acquisitions, none failed, none stopped, none under memory pressure. Every worker recorded a block cache of 536,870,912 bytes. Pixels were read from 12:32:10 to 14:00:22 UTC. The result is `benchmarks/results/tile-extraction.json`, digest `e951d1662156d978016cb0cd649493c6e645c22e6b99d150b7468e6b99f11aa2`, written once by the script. Findings 19 to 22 in [measurements.md](../measurements.md) now hold its numbers.
- The 200 lake-band digests are identical between the two runs, values and pixel sets. The cache changed what was read and how long it took, not what came out. Stage 2 matched on the same 130 lake-bands.
- Preparation of the 40 masks took 89.8 s in total and 20.0 s at most, for Lake Lanier in 16SGD. It peaked at 1.53 GiB for Lake Okeechobee, against 1.23 GiB in the first run, with identical masks.
- The run requested 45.2 GB in 19,179 requests. The largest worker peaked at 1.94 GiB, the whole-tile lazy stack on Lake Okeechobee's tile. Host page-outs reached 6.4 MB per run at most.

What the cache changed, from the two result files, raster mask medians of three unless stated:

| Tile | Windowed, files outermost, 512 bytes | Windowed, files outermost, 512 MiB | Naive clip setup, 512 bytes | Naive clip setup, 512 MiB |
|---|---|---|---|---|
| 05VLG | 26 requests, 6.7 MB, 3.4 s | 26 requests, 6.7 MB, 3.3 s | 0.01 s | 0.01 s |
| 05VMG | 35 requests, 13.7 MB, 4.5 s | 30 requests, 11.5 MB, 4.2 s | 0.02 s | 0.01 s |
| 10SGJ | 54 requests, 52.9 MB, 10.7 s | 51 requests, 52.4 MB, 8.7 s | 16.8 s | 0.18 s |
| 10TET | 43 requests, 25.7 MB, 6.0 s | 34 requests, 18.4 MB, 4.4 s | 0.78 s | 0.07 s |
| 16SGD | 49 requests, 57.4 MB, 9.2 s | 36 requests, 48.3 MB, 7.4 s | 20.0 s | 0.46 s |
| 16TGK | 27 requests, 23.0 MB, 4.5 s | 19 requests, 13.1 MB, 2.8 s | 1.35 s | 0.06 s |
| 17RNK | 57 requests, 64.6 MB, 10.4 s | 48 requests, 58.8 MB, 8.8 s | 16.1 s | 0.45 s |
| 17RNL | 39 requests, 44.6 MB, 7.5 s | 33 requests, 43.8 MB, 6.4 s | 6.4 s | 0.20 s |
| 17SKT | 30 requests, 28.5 MB, 6.7 s | 20 requests, 21.5 MB, 3.4 s | 14.1 s | 0.36 s |

The naive clip setup is the run's setup median for the lake-by-lake pattern, which the anchor dominates.

- The block cache serves neighbours. With 512 bytes no decoded block survived, and GDAL's cache of downloaded ranges served 7 of the 33 smaller lakes. With 512 MiB the file-by-file pattern served 21 of 33 from the block cache. Requests in that pattern fell on every tile but 05VLG. The stage 2 ratios in finding 19 moved from 34 to 54 percent to 24 to 46 percent.
- The lake-by-lake pattern did not change. Its bytes are identical on all nine tiles, because reopening a file discards its cached blocks. The first run's claim that loop order barely matters was a property of the 512-byte cache. Finding 19 now says the opposite.
- The naive clip's rasterization fell from 14 to 20 s per large lake to under half a second. GDAL's log shows one pass over the polygon instead of one per row. Finding 22's withdrawn claim is replaced by the measured cost.
- The lazy stack's bytes are identical on all nine tiles in the shared-graph pattern. Each compute opens the file again, so the block cache does not help it. Its ratios in finding 21 rose only because the windowed reads fell.
- Whole-tile bytes and requests are identical. Read times moved by minus 14 to plus 1 percent, within the run-to-run variation. Whole-tile peaks rose by 0.15 to 0.4 GB, because the cache now holds up to 512 MiB of decoded blocks.
- The Grand Lake 30 m pond that fetched 6.6 MB from an open file in the first run cost nothing in the rerun. Its blocks were already cached. The mechanism behind the first run's read is not explained. The first run's twelve slow runs were not repeated as such, and the rerun had nine of its own.

## Dispositions of prior findings

| Finding | Disposition |
|---|---|
| Codex, 2026-09-15, stage 2 finding 3: investigate shared reads without assuming a constant cost per lake | **Accepted.** Every run records each lake's own requests and bytes within the tile. It records the summed and distinct blocks per file, with stage 2's per-lake sums beside them |
| Codex, 2026-09-15, stage 2 finding 6: fixed ordering limits method ranking | **Fixed** in stage 3. Patterns and methods both rotate between repetitions, and the plan records the order |
| Finding 18: two lakes lay outside their region's tile | **Fixed** in stage 3. Tiles are chosen to place every lake, and membership comes from the buffered polygon |
| Finding 18: catalog grid codes vary | **Fixed** in stage 3's script. Codes are normalised before grouping by tile. Stage 2's script is unchanged |
| Codex, 2026-09-12: the manifest option finds candidate tiles, not the water bodies' tiles | **Accepted and deferred.** Stage 3 assigns tiles per lake from the polygon for its own runs. The survey rerun remains pending |
| Codex, 2026-09-12: refetching always writes polygon version 1 | **Accepted and deferred.** Every mask file and run record carries the polygon digest. Version handling waits for refreshed geometry |

## Verification

- Before Codex's review, the check sequence passed in order with 159 tests. That is `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.
- After the review was applied: the same sequence passed with 164 passed. The three `--check` tools and `git diff --check` passed.
- `uv run python benchmarks/tile_extraction.py --dry-run` printed 32 lakes in 6 regions, 36 runs per tile, and the rotation of every repetition without network access.
- After the run: the check sequence passed again. `render_options.py` regenerated the page with the stage 3 chapter, and its `--check` passed. Nothing was committed, pushed, or published in this step.
- 2026-09-16, after the corrections: the check sequence passed with 166 tests. The three `--check` tools and `git diff --check` passed. The page was regenerated. Nothing was committed, pushed, or published.
- 2026-09-16, after the rerun: `--dry-run` printed the plan before the run. Afterwards the check sequence passed with 166 tests, the three `--check` tools and `git diff --check` passed, and the page was regenerated from the new result. Nothing was committed, pushed, or published.

## Proposed next step, not started

1. Codex reviews the rerun, the rewritten findings 19 to 22, and the page chapter.
2. Commit on the owner's authorization.
3. Stage 4, lakes across tiles, after that. **Cross-tile mosaicking is a MAJOR CONCERN, issue I-30.**
