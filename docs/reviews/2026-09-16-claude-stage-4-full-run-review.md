# Stage 4 full run review, 2026-09-16

Reviewer: Claude Code (AI coding agent), directed by the repository owner.
Reviewed: Codex's [implementation](2026-09-16-stage-4-implementation.md), [smoke](2026-09-16-stage-4-smoke.md), and [full run](2026-09-16-stage-4-full-run.md) of 2026-09-16, with [findings 23 to 25](../measurements.md#prototype-stage-4-lakes-across-tiles-2026-09-16).
The owner ran the smoke and the full workload before this review. The three records are reviewed together here.

The extraction evidence holds. Every count, digest, request total, and byte total in the records was recomputed and agrees.
The interpretation needs four corrections before the findings enter the inventory or the presentation.
The selection code mislabels split datastrips. The catalog footprints are too coarse for the coverage claims. The no-data heading misattributes. And 22 of 25 memberships carry no role.
None of the four changes the selected datatakes, the extraction, or the timing comparison. None needs another provider run.

Scope: the [full result](../../benchmarks/results/cross-tile-extraction.json), the [smoke result](../../benchmarks/results/cross-tile-extraction-smoke.json), the raw directories under `data/cross-tile-extraction/`, the saved catalog, [cross_tile_extraction.py](../../benchmarks/cross_tile_extraction.py), the change to [tile_extraction.py](../../benchmarks/tile_extraction.py), and the [tests](../../tests/test_cross_tile_extraction.py).
No provider script ran. No pixel was read. Geometry checks below use the saved catalog items and the manifest polygons only.
This review adds this file and its index row, and commits nothing.

## What was verified independently

- The result digest is `fddea828f0a9516b999c40e879e46c8998e2ed4a8b8dfe16de01d571db4495e8` and the smoke digest `8140e3ddaa3c31212ca63f51293dbb721c9a4ad387b43e6b12c7320c5499f4dc`, as recorded.
  The plan digest, the catalog digest, and the frozen source digests match the working tree.
- Requests and bytes were recounted from all 198 GDAL logs with a separate parser. Every tile total matches. No log holds a timeout, retry, or HTTP error line.
- 114 workers ran, 1,500 contributions are `measured`, and all twelve workloads equal the reference on every signature field. Every worker reports a 536,870,912-byte cache. No worker stopped or was flagged for page-outs.
- Findings 24 and 25 were recomputed from `summary.workloads`, `summary.medians`, and `summary.per_lake_tile_band_costs`. Every number in their tables agrees.
- The smoke pond `nhd-34972105` has identical windows, counts, and all four digests in the smoke and the full run. That holds in all four tiles and five bands. That is a cross-run reproducibility check on real pixels, and Codex's records do not mention it.
- The geometry-bound correction changed Lanier's converged spacing from 7.8 m to 62.5 m and its shares by about 1e-9. The selected group and the group order are unchanged. The bound is valid. A change in any union or difference is bounded by the changes of its inputs. The largest footprint change per tile bounds any single group. The `1 + 2T` support coefficient over-counts, which is safe. It is a successive-halving criterion at one eighth of the tolerance, not an error bound against exact geometry.
- The ten slow workers repeat their requests, bytes, and CPU seconds. Okeechobee lake-first raster repetition 2 took 43.17 s against 26.22 s, with 126 requests, 127.9 MB, and 3.3 CPU seconds each time. The extra seconds sit in band read times across several tiles. That is network delay, not extra work, and the record can say so instead of "uninvestigated".
- `/check` passes: `uv sync --locked`, `ruff check`, `ruff format --check`, 190 tests, the three `--check` tools, and `git diff --check`.

## Findings

### 1. Medium: split datastrips are discarded as "superseded revision"

`select_region` keeps one item per tile and group, choosing the latest `created`, and labels the rest "superseded revision".
The catalog holds six such discards, all in two groups. `plan.selection.lanier.groups` and `plan.selection.okeechobee.groups` list them.
None is a revision. Each pair holds two products of one tile from consecutive datastrips of one datatake.

In Lanier's `GS2C_20251010T162221_005730_N05.11`, tile 16SGD has `S2C_T16SGD_20251010T163403_L2A` from datastrip `S20251010T163403` and `S2C_T16SGD_20251010T162737_L2A` from `S20251010T162737`.
The kept product covers 1,609 km² of the tile and 35 of Lake Lanier's 97 km² in it. The discarded product covers 11,868 km² and 97 km² of the lake.
The two overlap by 1,439 km², so the datastrips overlap rather than abut. 17SKU shows the same pattern, 39 km² kept against 97 km² discarded.
Okeechobee's `GS2B_20250906T160509_044410_N05.11` splits 17RMK and 17RNK the same way. The saved catalog under `data/cross-tile-extraction/full-plan.catalog.json` holds the datastrip ids.
Earth Search serves each item at `https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/<item id>`, the primary source for the six.

The selection outcome is unaffected. Both groups lose on cloud cover regardless, 0.21 against 0.016 percent for Lanier and 95 against 0.59 for Okeechobee.
The chosen groups hold one datastrip per tile. The frozen plan and the result stay as evidence.

The method and the assessment are affected.
A datatake can hold two valid products of one tile, so `tile` and `datatake` do not identify one observation. The item id, or the datastrip id, does.
Stage 4's contribution key already carries the item id, which is why the assembly rule survives. The selection model does not, since `scenes` holds one item per tile.

Change: group revisions by tile and `s2:datastrip_id`. Treat different datastrips as separate scenes of one group, with membership and coverage from each footprint. Add a fixture with two overlapping partial products of one tile in one datatake. Record the six item ids and the datastrip pattern in finding 23 and add a gotcha line pointing there. Do not re-freeze the run's plan. Apply the rule to the next selection.

### 2. Medium: catalog footprints are coarse, and the footprint coverage claims inherit that

The chosen items' footprints have four to six vertices. They are chords in longitude and latitude between tile corners, not the tile edges.
In each tile's native CRS the footprint edge lies inside the true tile edge. The shortfall reaches 129 m for 16SGC, 104 m for 17RML, and 99 m for 17RNK. It is 71 to 72 m for 17SKT and 17SKU, and 1 m for 17RMK. 16SGD and 17RNL show no shortfall.
The `support_in_footprint` values in `plan.selection.*.coverage.*.members` record the consequence: 0.9936, 0.9971, and 0.9953 for three Lanier tiles and 0.9405 for 17RML.
Every one of those shortfalls is a strip along a tile edge, geometry computed from the saved items.

The pixels contradict the footprints. The scene classification declares 0 as no-data, and no contribution holds a single SCL value of 0. Its minimum is 2 or more in every tile.
So every selected pixel of every lake, in every tile, lies in the sensed area, including the strips the catalog polygons exclude.
Three consequences follow.

- Ranking criterion 1, "footprints cover every present member's support", never discriminated. All 76 Lanier groups and all 75 Okeechobee groups score `True` on `not all_footprints`. The effective ranking was the uncovered fraction, then cloud, then date.
- Finding 23's "support inside multiple catalog footprints" column, 400.79 km², carries false precision. Its difference from the extent overlap, 402.11 km², is chord error, not observation.
- The plan's footprint tolerance of 1e-6 relative area applies to the arithmetic. The polygons themselves are good to about 130 m in this sample.

Change: state the vertex counts and the edge shortfalls in finding 23. Drop the footprint overlap column, or round it to whole square kilometers with the caveat. Make the SCL statement the coverage evidence. For the assessment, record that catalog footprints cannot decide coverage at lake scale. A pixel-level check, the SCL or a band's no-data value, must. Replace ranking criterion 1 with a distance tolerance of a few hundred meters or drop it.

### 3. Medium: the no-data entries are per-band zeros inside sensed water, not coverage

Finding 23's heading and placement tie the 1,034 no-data entries to footprint coverage. The result says otherwise.
The entries are the declared no-data value 0 in the 10 m `nir` band. Lake Lanier holds 56, 222, 11, and 640 in its four tiles. Lake Okeechobee holds 16 in 17RNK and 73 in 17RNL.
The 10 m `red` band adds 3 in 17RNK and 13 in 17RNL. The 20 m and 60 m bands and the ponds hold none. Source: `runs[].contributions[].nodata_extracted` with `value_min`.
The SCL band has a class at every one of those pixels, as finding 2 shows. These are zeros inside sensed water, per band, and their cause is not established here.

Two things follow for the assessment. No-data is a per-band, per-pixel state, and a reflectance value of 0 inside the sensed area is only recognisable through the SCL.
And the two zone projections of one datatake hold different counts of zeros over largely the same water, 56 against 11 and 222 against 640. That is a first sign that overlapping observations of one datatake differ at the pixel level, for stage 5.

Change: retitle finding 23 or move the no-data sentences under their own heading, name the bands and tiles, and state the SCL evidence. Carry the per-band no-data point into the contract discussion.

### 4. Medium, owner decision: 22 of 25 memberships carry no role

Three memberships carry `primary`, the three Okeechobee ponds with one containing tile. Eight of eleven lakes are `unresolved`. Source: `plan.scenes[].roles`.
Every Lanier lake lies entirely inside one zone-16 tile and one zone-17 tile, so "single containing tile" cannot resolve any lake near a zone boundary.
A22's first clause names the tile containing the buffered polygon entirely. It gives two answers for each Lanier pond unless its tie rule applies to that clause too.

The proposed largest-buffered-share rule picks 17SKU for Lake Lanier by 0.39 points, 67.79 against 67.40 percent for 16SGD.
The unbuffered polygon share ranks the other pair first, 17SKT at 70.26 against 16SGC at 69.02.
So the buffered and unbuffered readings of "largest share" disagree for the sample's hardest case, and the margin is small either way.

Change: none in code. The owner decides the rule. Whichever reading is chosen, freeze it per polygon version and record the margin, so a small polygon edit cannot silently move a lake's primary tile. Until then the contract's role field is not evaluated, as Codex states.

### 5. Low: wording and precision

- Finding 24 says "Its median worker duration was 46.1 percent lower". The number is the median complete-workload wall time, 54.00 against 100.13 s. Say so.
- The ten slow workers have a cause in the logs, see above. Replace "remains uninvestigated" with the evidence.
- The transfer proxy printed 126.7 GB for 4.53 GB of actual requests, 28 times too high. It gated nothing. Replace it with stage 3 and stage 4 windowed bytes per membership for the next preflight.
- The corrected Lanier selection swapped in 1.03 GiB while it ran. The record reports page-outs only. Add the swap-in figure beside the 3.40 GiB peak.
- The current-phase paragraph of `CLAUDE.md` now carries fourteen lines, some stale, such as the implementation record being "ready for Claude Code review". Trim it to the current state.
- The run record's "Result SHA-256" and the measurement section are consistent. The smoke record's numbers were recomputed and agree, including 268 requests, 127,199,416 bytes, and the 5.95 ratio.

### 6. Low: evidence that strengthens the findings, unstated

- In tile-first raster reading, eight of the seventeen pond memberships requested zero bytes and zero requests. Lake Lanier's four tiles cost 14.1 to 45.7 MB marginally against 20.7 to 49.7 MB read alone. Lake Okeechobee's cost 1.8 to 49.1 against 1.9 to 58.8. Source: `summary.per_lake_tile_band_costs`. That is the mechanism behind finding 24.
- Bytes per selected band-pixel entry are 8.5 for Lake Lanier and 2.8 for Lake Okeechobee, lake-first raster. Lanier's windows are 17 to 35 percent selected pixels, Okeechobee's 35 to 68. The zone boundary then doubles Lanier's tiles. A dendritic reservoir at a zone boundary costs about three times the bytes per stored entry of a compact lake. That bears on assumption A17 and issue I-20.
- The smoke and the full run agree on every contribution of the smoke pond, see above.

### 7. Low: the mid-step code change

The geometry-bound change, script version 1 to 2, ran inside the authorized full-run step without review. It touched the diagnostic bound only, added a regression test, and reused the saved catalog, so no extra provider traffic occurred.
The bound is reviewed above and holds. Acceptable this time. In future, a code change during an authorized run step is a stop point for review.

## Dispositions of Codex's corrections to the plan review

- `in_tile` in stage 3 is the unbuffered polygon share: accepted. The primary metric needs its own calculation, which the implementation provides.
- 17RML is not near-land-only: accepted. Its contribution holds 52,295 interior 10 m pixels of Lake Okeechobee.

The [rerun review's](2026-09-16-codex-stage-3-rerun-review.md) four documentation corrections remain open and are separate from stage 4.

## Answers to the review targets

| Target | Answer |
|---|---|
| Convergence bound | Valid and conservative, as a successive-halving criterion. Changed nothing material for Lanier. |
| Acquisition grouping | Grouping by datatake is right. The revision rule mislabels split datastrips, finding 1. |
| Overlapping coverage | The extent overlaps are verified. The footprint overlaps carry chord error, finding 2. |
| No-data accounting | Counts verified. Their attribution to coverage is wrong, finding 3. |
| Timing comparison | Verified. One wording fix, and the slow workers are network delay, finding 5. |

## Verification

- `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 190 passed. The documentation tests include this file.
- `uv run python tools/collate_checks.py --check`, `render_options.py --check`, `gap_report.py --check`: passed.
- `git diff --check`: passed.
- Log recount, digest checks, geometry checks, and the smoke comparison ran from the scratchpad against saved files only.

## Next step

Codex applies findings 1, 2, 3, 5, and 6 in the code, tests, measurements, and records, without re-freezing the plan or rerunning extraction.
The owner resolves finding 4. Then the inventory finding F-26, the presentation, and the commit follow on the owner's authorization. Stage 5 needs separate authorization.
