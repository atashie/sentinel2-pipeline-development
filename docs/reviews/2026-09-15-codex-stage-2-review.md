# Stage 2 review, 2026-09-15

Reviewer: Codex, with separate primary-source research and checking agents.

The single-lake runs provide a useful initial baseline. Several explanations overstate the evidence, and the saved shoreline distances contain a tile-clipping error.
Correct those findings before using them to compare stage 3 or guide colleagues. The agreed stage order remains appropriate.

Scope: [measurements, findings 16 to 18](../measurements.md#prototype-stage-2-one-lake-at-a-time-2026-09-15), the [stage 2 record](2026-09-14-stage-2-one-lake-at-a-time.md), code, fixtures, saved artifacts, inventory, and presentation.
The reviewed working tree starts from commit `6772683`, with Claude's stage 2 changes uncommitted.
This review changes only this record and the reviews index. It runs no provider survey, pixel download, or subsequent prototype stage.

## Evidence that holds

- The [saved summary](../../benchmarks/results/lake-extraction.json) recomputes exactly from its runs, preparation records, and the current manifest.
- All 360 runs containing pixels reproduce their requested-byte and request totals from their saved GDAL logs.
- All 360 reused extraction records match the original saved records. Preparation polygon digests match the manifest.
- There are 30 lakes with reads, six tiles, six selected items, and five bands. Three mask methods have matching value digests in 150 comparisons.
- Naive extraction matches the wet-value digest in 121 comparisons. Its 29 disagreements coincide with differences recorded during preparation.
- The five sampled ponds in the 10 m class have no interior pixel. Ten sampled lakes have none at 20 m, and fifteen at 60 m.
- Preparation, requested bytes, machine-wide network counters, and extraction timers are recorded separately. Scientific validation and AWS measurements remain explicitly unfinished.

The result digest at review was `ecabada38d65b1951871cff2496d003b06a92e9ccbe1656e995a8892759217aa`.
Local raw artifacts are under `data/lake-extraction/`. They remain outside git.

## Findings

### 1. High: tile clipping creates false shoreline distances in the current masks

Location: [compute_mask](../../src/s2proto/masks.py), the intersection at line 342 and boundary construction at line 385.

The function replaces the lake polygon with its intersection with the tile. It then measures distance to that clipped polygon's boundary.
A tile cut through water becomes an artificial shoreline. This already affects the three partially covered lakes, irrespective of when additional tiles are read.

Offline checks used the saved 60 m masks and the full projected manifest polygons:

| Lake | Tile row, column | Saved edge distance | Distance to the full mapped boundary |
|---|---|---|---|
| Lanier | 1829, 434 | −30 m | −661.854 m |
| Okeechobee | 0, 390 | −30 m | −5,849.955 m |
| Alaska, `nhd-60265485` | 919, 0 | −30 m | −127.525 m |

Okeechobee's value belongs beyond the configured 1,000 m cap, so the stored distance would be NaN under the current convention.
Within 1,000 m of tile edges, 411 Lanier, 4,184 Okeechobee, and 12 Alaska wet pixels disagreed at 60 m.
Those counts use a 0.001 m diagnostic tolerance and equal treatment of NaNs. They are an audit sample, not an all-resolution count.

A synthetic rectangle crossing a tile edge also returns −5 m where the original polygon boundary is 405 m away.
Area conservation does not check this distance calculation. Agreement between extraction methods also cannot reveal an error in their shared mask.

Disposition: open. Keep the original polygon for boundary distances and restrict output pixels to the tile separately.
Add a crossing-tile distance fixture. Mark existing partial-lake distances as affected before reusing those masks.
This corrects the current single-tile calculation without advancing the cross-tile experiment.

### 2. High: 197 of the 198 alleged nonintersecting pixels actually intersect the polygons

Locations: [measurements, finding 17](../measurements.md#17-the-four-methods-returned-identical-values-and-differ-in-cpu-memory-and-what-they-keep), [mask classification](../../src/s2proto/masks.py), the CLAUDE gotcha, and inventory finding F-24.

`naive_only` compares GDAL's selection against water classes requiring coverage greater than `1e-6`.
It does not test whether intersection is empty. Tiny positive overlaps fail this project threshold.

I reconstructed all 198 saved naive-only cells and intersected each pixel square with its projected, tile-clipped polygon:

- 197 have positive intersection area below the configured coverage cutoff.
- One has an empty intersection. Its cause remains uninvestigated.
- None of these 198 has only a zero-area boundary contact.

The area thresholds are 0.0001, 0.0004, and 0.0036 square meters at 10, 20, and 60 m.
The six cells selected only by the area-based rule remain a separate observation.
This audit does not explain those six or the single empty intersection.

Disposition: open. Replace the claim that GDAL marked 198 nonintersecting pixels with the threshold comparison above.
Describe the classes as area-based with a declared tolerance. Preserve the tolerance and measured differences.
The comparison supports different selection rules, not a general failure of GDAL's all-touched rasterization.

### 3. High: the one-block headline misses a measured exception and confuses blocks with HTTP requests

Locations: [measurements, finding 16](../measurements.md#16-one-lake-costs-one-block-per-file-whatever-its-size), presentation stage 2, CLAUDE gotcha, F-24, and I-20.

Of 25 non-anchor lakes with reads, 24 fit within one block per file. The Alaska 300 m lake, `nhd-72879541`, crosses block boundaries.
Its five-file read requests 4,349,464 bytes in 20 requests, with every method. Each file's window intersects two blocks.
For red, rows 9181 through 9239 cross the block boundary at row 9216.
The sample therefore directly contradicts “every lake below the anchors” taking 15 requests.

The Okeechobee red window intersects **20 internal blocks**, not 13.
Its dimensions are 4,806 by 3,872 pixels, starting at tile row and column zero, with 1,024-pixel blocks.
Thirteen is its HTTP request count, including metadata access. GDAL can combine block byte ranges into fewer requests.

All non-anchor five-file reads span 2.49 to 4.35 MB requested. Their class medians remain close, as reported.
Similar medians do not establish that latency alone sets runtime. Position, window extent, compression, caching, and request merging remain relevant.

Disposition: open. Use “Small-lake reads usually fit within one block per file in this sample.”
Name the boundary-crossing exception and report block counts separately from requests.
Keep latency as an inference. Stage 3 can investigate shared reads without assuming a constant cost per lake.

### 4. High: extraction reuse can silently retain results from an earlier polygon or mask

Location: [reuse_mismatch and the extraction reuse call](../../benchmarks/lake_extraction.py), lines 830 and 1054 onward.

Extraction reuse checks the lake ID, method, repetition, tile, item ID, asset keys and hrefs, and GDAL environment.
It does not bind the polygon digest, grid, mask contents, mask parameters, or implementation version.
Preparation checks the polygon digest, so changed geometry can produce new masks while extraction still reuses values from the old masks.

Offline reproduction: changing both geometry and grid origin in a saved raster-mask specification still returns no reuse mismatch.
A saved lazy-stack band marked with a grid error also passes this guard when its key and href remain present.

The current results match their original artifacts. This is a reuse defect, not evidence that these 360 records contain a different polygon.
It becomes immediately relevant when correcting finding 1 or changing any mask parameter.

Disposition: open. Bind extraction reuse to the preparation inputs and artifacts, alongside reader and implementation identity.
Reject failed band records. Add changed-geometry, changed-mask, and failed-band fixtures before the next reuse.
Preparation reuse also needs its parameters and implementation bound, so a corrected distance algorithm cannot reuse an older mask.

### 5. Medium: value hashes do not enforce the declared pixel-set and completeness checks

Location: [summarize](../../benchmarks/lake_extraction.py), lines 423 to 458, and extraction result handling.

The equality summary hashes values alone. It does not hash tile coordinates or classes, or require every expected method and repetition.
Running the summary with only one lake's raster-mask records still reports `mask_methods_identical: true` for all five bands.
Identical value sequences can also come from different coordinates, especially in uniform or no-data areas.

The current saved pass contains all four methods for every reported comparison.
Its 360 nonempty runs have all five bands and no band errors. No current missing-method case was found.
The remaining 24 runs contain five “no pixel” band errors each and no extracted bands.
The script reports zero failures because it counts only top-level errors. Other band errors could receive similarly misleading status.

Disposition: open. Compare a coordinate-and-class digest alongside the value digest, with expected methods and repetitions explicitly accounted for.
Report skipped empty-tile runs separately from successful reads and unexpected band failures.
Retain coverage and native-grid checks as distinct checks. A passing value digest does not establish either.

### 6. Medium: presentation counts and method conclusions exceed what the summaries establish

Locations: [lake_extraction_rows](../../tools/render_options.py), lines 244 to 276, [presentation template](../../tools/s2-options.template.html), and measurement findings 16 to 18.

The renderer adds separately calculated medians for interior, shoreline, and near-land pixels.
The sum of these medians is not the median total per lake:

| Size class | Rendered 10 m total | Median of each lake's actual 10 m total |
|---|---|---|
| 10 m | 360 | 361 |
| 100 m | 896 | 895 |
| 300 m | 2,621 | 2,683 |
| 1,000 m | 14,327 | 14,000 |
| Anchor | 1,061,243 | 1,672,524 |

The measurements table's “Pixels stored at 10 m” column instead contains counts across all five files, including repeated locations in different bands.
Its 910 for a small pond is a count of extracted band values across resolutions, not 910 distinct 10 m pixels.
No production records were stored, and coverage and distance fields are absent from the output-byte estimate.

The introduction and status table also claim agreement between four methods on every band.
The complete extracted arrays agree between the three mask methods. Naive extraction differs in 29 comparisons and omits the near-land class.

The method recommendation is premature. The lazy stack has higher overhead for small lakes, but its observed read medians are lower for two anchors:

| Lake | Raster mask | Index lists | Lazy stack |
|---|---|---|---|
| Lanier | 9.964 s | 7.747 s | 6.268 s |
| Okeechobee | 10.185 s | 9.185 s | 8.053 s |

Okeechobee's lazy reads requested 50.8 MB against 58.8 MB for the raster mask, with more requests.
Across the five anchors, lazy requested more bytes for three, the same for one, and fewer for one.
The record's “four anchors” statement is incorrect. The 14 percent increase describes a ratio of class medians, not every anchor.

These observations do not establish a winner. Fixed ordering, three repetitions, and an uncontrolled laptop connection limit method ranking.
The table's read timers exclude polygon clipping, mask loading, pixel selection, and diagnostics.
Whole-run timers include those operations and some method-specific initialization. Use both scopes when discussing workflow efficiency.

Disposition: open. Calculate per-lake totals before taking medians, label band-value counts accurately, and qualify agreement to the three mask methods.
Remove “the choice is about storage, not extraction” and “without a saving” as established conclusions.
Keep partial results and the paired anchor observations available for the next comparison.

### 7. Medium: the rerun history understates repeated provider reads

Location: [stage 2 run record](2026-09-14-stage-2-one-lake-at-a-time.md), “The runs,” and the result provenance.

The record describes one summary rewrite repeating 90 lazy-stack reads. Local artifacts show two such rewrites:

| Raw directory timestamp, UTC | Fresh nonempty extraction runs | Requested imagery bytes |
|---|---|---|
| 2026-09-15T132137+0000 | 360 | 3,186,184,080 |
| 2026-09-15T134409+0000 | 90 | 822,978,632 |
| 2026-09-15T135019+0000 | 90 | 820,881,480 |
| 2026-09-15T135610+0000 | 0 | 0 |
| 2026-09-15T140106+0000 | 0 | 0 |

The two accidental repeats requested another 1,643,860,112 imagery bytes. This excludes catalog requests and the earlier smoke run.
The final result correctly contains the original 360 nonempty runs. The extra repetitions do not enter its medians.
Their saved start times run from 13:23:11 to 13:41:53 UTC, rather than the stated original pass ending at 13:53.

`--reuse` still re-queries the catalog before looking for cached runs. Summary regeneration through that route is not an offline operation.
This complicates both measurement provenance and the owner's control of provider reads.

Disposition: open. Correct the dated history and derive future summary-only updates directly from saved inputs without executing the acquisition path.
Keep measurement timestamps distinct from summary-generation timestamps. Preserve the original worker provenance.

## Smaller documentation corrections

- Coverage error reaches `2.4e-11`, not `1.3e-11`, in the saved preparation records. Both are comfortably within the declared `1e-6` tolerance.
- Tahoe's 11.3 seconds and 0.87 GB describe preparation across all three resolutions, including saved files. Its 10 m mask computation reports 7.9963 seconds.
- Alaska candidates contain 87 items for each padded tile code and five for each unpadded code. Across both tiles, that is 174 and 10.
- The inventory calls three partial bodies “anchors.” The Alaska body is in the 1,000 m class.
- The work-plan introduction still says lake extraction is open. The stage 2 record's opening and pre-run limits still say no pixels were read.
- The CLAUDE “latest review” link still targets the pilot review. Link current status to this review and identify historical planning text as historical.

## Prior review dispositions

The [stage 1 review](2026-09-14-codex-stage-1-review.md) received substantive corrections in commit `6772683`.
The saved 19:56 comparison now reports the exact clamp test: zero violations across 99,802,042 valid pixels in three reflectance bands.
Product and grid guards, narrower offset claims, access-policy wording, and timing labels were also updated.
Those corrections remain useful. Stage 2 introduces its own reuse and interpretation gaps described above.
This review does not reopen the agreed workload-first sequence or require stage 5 to run early.

## Source checks

Accessed 2026-09-15. The research and checking agents independently confirmed these primary-source distinctions.
Numerical audit findings come from saved project evidence, not these documentation pages.

| Claim checked | Primary documentation | Outcome |
|---|---|---|
| All-touched differs from a fractional-area cutoff | [Rasterio rasterize](https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html#rasterio.features.rasterize), [GDAL all-touched](https://gdal.org/en/stable/programs/gdal_rasterize.html#cmdoption-gdal_rasterize-at) | Confirmed. Project coverage thresholds are separate rules |
| Small windows can touch multiple blocks | [Rasterio windowed reads](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html#reading) | Confirmed. Position as well as size determines intersected blocks |
| HTTP requests do not count raster blocks | [GDAL range merging](https://gdal.org/en/stable/user/configoptions.html#config-GDAL_HTTP_MERGE_CONSECUTIVE_RANGES), [GDAL virtual files](https://gdal.org/en/stable/user/virtual_file_systems.html) | Confirmed. Consecutive ranges can merge, and metadata access is separate |
| Distances use the boundary actually supplied | [Shapely intersection](https://shapely.readthedocs.io/en/stable/reference/shapely.intersection.html), [boundary](https://shapely.readthedocs.io/en/stable/reference/shapely.boundary.html), [nearest distance](https://shapely.readthedocs.io/en/stable/strtree.html#shapely.STRtree.query_nearest) | Confirmed. Measuring the clipped boundary includes artificial tile cuts |

## Verification and proposed next step

Offline audit: summary recomputation, 360 log checks, reused-record comparisons, polygon digests, block/window arithmetic, geometric intersections, and saved shoreline-distance checks.
Additional offline counterexamples exercised changed-geometry reuse, failed-band reuse, and equality with only one method present.

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed in order:

1. `uv sync --locked`: 59 packages resolved, 56 checked.
2. `uv run ruff check .`: passed.
3. `uv run ruff format --check .`: 70 files already formatted.
4. `uv run pytest -q`: 137 passed in 3.64 seconds.

The suite emitted 88 dependency deprecation warnings about affine multiplication in rasterio and odc-geo.
The inventory, presentation, and gap-report `--check` commands passed. The stage 2 `--dry-run` listed 384 planned runs without network access.
`git diff --check` passed. Generated-file freshness confirms reproducibility, not the interpretation of findings.

Proposed next step: Claude responds to these findings, corrects the affected code and explanations, and records any revised evidence separately.
Retain the original measurements. Correcting or annotating existing evidence does not require a new acquisition.
The next authorized workload remains stage 3. No method, storage layout, compute platform, or implementation architecture is selected by this review.
