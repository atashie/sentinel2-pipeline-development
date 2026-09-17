# Stage 3 rerun review, 2026-09-16

Follow-up, 2026-09-17: The remaining documentation corrections are recorded in the [presentation update](2026-09-17-documentation-and-presentation.md).

Reviewer: Codex.

Scope: the corrected-cache rerun, its saved evidence, implementation changes, findings 19–22, and the Prototyping presentation.
This follows the [first run review](2026-09-15-codex-stage-3-review.md) and Claude's [response and rerun record](2026-09-15-stage-3-many-lakes-in-one-tile.md).
The reviewed rerun is in commit `4d9d08f`. This review adds no implementation changes.

The rerun resolves the cache defect and supports the main Stage 3 findings.
All 324 extraction records reconcile with their raw results and logs.
Coverage accounting, equality, baseline comparisons, and the main comparison tables check out.
No new high-severity finding emerged.
The remaining findings concern interpretation and documentation, rather than invalidating the rerun.

No provider script ran. No imagery was downloaded, and no pixels or mask arrays were read.
Only this review and its index entry were added. Implementation fixes remain separate.

## Findings

### 1. Medium: the largest outlier has recorded timeouts and extra requested bytes

Locations: [measurements](../measurements.md), finding 22 and “What stage 3 does not show”.
Evidence: [result](../../benchmarks/results/tile-extraction.json), run 59, and its saved GDAL log.

Finding 22 says the nine slow runs requested the same bytes as their siblings.
That is false for the largest outlier: 16SGD, lake-by-lake, lazy stack, repetition 2.

| Repetition | Wall time | Requests | Requested bytes |
|---|---:|---:|---:|
| 1 | 15.2810 s | 54 | 69,115,065 |
| 2 | 107.2489 s | 57 | 74,273,559 |
| 3 | 9.2984 s | 54 | 69,115,065 |

The log is `059-16SGD-lake-by-lake-lazy-stack-2.gdal.log` under `data/tile-extraction/2026-09-16T122955+0000/`.
Lines 616–619 report two timed-out B11 range requests with response code zero.
Lines 621–623 repeat three previously requested ranges, adding 5,158,494 requested bytes.
The final extraction succeeded and its digests agree.

This identifies a transport problem in that run. It does not allocate every second of the delay or explain the other outliers.
The other eight flagged runs have the same request and byte totals as their respective siblings.
The nine-run count is correct. The slow Okeechobee index-list median is also correctly disclosed.

Disposition: open. Correct the equal-bytes statement and name the observed timeout and repeated requests.
Keep the remaining causes unresolved. Preserve the successful run and its median calculation.
This correction needs no new download or experiment.

### 2. Medium: the page still turns conditional byte arithmetic into a lake-count rule

Locations: [presentation template](../../tools/s2-options.template.html), chapter 05, second “Why it matters” paragraph.
The [rendered page](../s2-options.html) repeats it.

The 25–150 estimates are calculated correctly and explicitly described as byte arithmetic.
However, the following paragraph says whole-tile reads pay off only with far more water bodies.
It also says tiles with few lakes are cheaper through windows.

Those statements exceed the evidence.
The experiment measures three to six memberships per tile, with particular sizes, shapes, positions, and shared blocks.
Lake count alone does not determine bytes. A different size distribution can change the result without adding lakes.
No monetary crossover was measured, as the preceding paragraph correctly states.

Disposition: open. Restrict the conclusion to the pilot's observed lake mix and block coverage.
For example: “At the pilot's density, windowed reads requested fewer bytes on every tile.”
Keep the estimates conditional, without presenting a general operating threshold.

### 3. Medium: the status table overstates complete spatial coverage

Location: [presentation template](../../tools/s2-options.template.html), “Which images cover these bodies?”, line 877.

The status table says Stage 3 placed every polygon and its 100 m buffer in a tile.
Selection instead places a lake wholly where possible, otherwise by its largest available share.
Candidate membership then uses buffer intersection. Preparation clips the selection to each chosen tile.

For example, Lanier is 62.5491% inside 16SGD and 70.2587% inside 17SKT.
Okeechobee is 90.0244% inside 17RNK and 22.7045% inside 17RNL.
These percentages cannot establish complete coverage simply by addition, because tiles overlap.
The result correctly retains partial memberships, and the presentation correctly leaves combined cross-tile records unfinished elsewhere.

Disposition: open. Say every pilot lake yielded pixels from its selected tile memberships.
State that partial polygons were read within tile boundaries. Leave complete cross-tile coverage assessment to the authorized Stage 4 work.

### 4. Low: a few numeric descriptions still need correction

Locations: [measurements](../measurements.md), finding 20, the [rerun record](2026-09-15-stage-3-many-lakes-in-one-tile.md), and chapter 05.

| Statement | Saved evidence |
|---|---|
| The largest single extraction from memory took 0.21 s | The largest sum of per-lake extraction timers is 0.1874 s, on 17RNK with whole-tile index lists. Rounded: 0.19 s |
| Whole-tile memory peaks rose by 0.15–0.4 GB | For raster-mask combination maxima, increases span 0.112–0.393 GB. Across all whole-tile methods, changes span −0.026 to +0.700 GB |
| Chapter 05 used a 512 MB cache | The recorded setting is 536,870,912 bytes: 512 MiB. Measurements and code already use the precise unit |

The record introduces raster-mask medians as its comparison convention.
Memory peaks are maxima, so their method and aggregation need explicit labels.
The page's quarter-second extraction bound remains supported.

Disposition: open. Correct these descriptions from existing evidence. No rerun is needed.

## Dispositions of the previous review

| Previous finding | Assessment |
|---|---|
| 1. Cache units and clipping-cost interpretation | Fixed. All 324 extraction workers record 536,870,912 effective cache bytes. The obsolete clipping-cost claim was withdrawn |
| 2. Unresolved requested assets disappear from coverage | Fixed. Removing Tahoe's resolved SCL asset preserves 200 expectations and reports six unresolved, missing, incomplete lake-bands |
| 3. Memory-pressure exclusion | Fixed. A pressured-run diagnostic produces no combination or per-lake timing median. Counts retain the pressure flag |
| 4. Stale Prototyping opening and status | Mostly fixed. The opening, stage-labeled equality counts, and unfinished work are accurate. Finding 3 corrects the remaining coverage overstatement |
| 5. Performance exceptions and recommendations | Mostly fixed. The no-data tile, lazy recipe, statistics, and conditional estimates are identified. Finding 2 removes the remaining recommendation |
| 6. Historical statements and documentation | Mostly fixed. The superseded selection expectation, index, guarded-check memory, and completion interval are corrected. Finding 4 covers remaining numeric discrepancies |

The missing-asset and pressure diagnostics used copies of saved JSON, without raster fixtures.
The new fixture assertions cover both defects, although those raster-dependent tests were not executed during this review.
The renderer reports excluded runs or absent clean medians.
Implementation version 4 prevents reuse of the earlier extraction configuration. The rerun reused zero runs.

## Evidence audit

The reviewed [result](../../benchmarks/results/tile-extraction.json) has SHA-256:

`e951d1662156d978016cb0cd649493c6e645c22e6b99d150b7468e6b99f11aa2`

The preserved, resummarized first result is `data/tile-extraction/tile-extraction-2026-09-15-512-byte-cache.json`, with SHA-256:

`4a5b3e398d8060200694c44a4520dc6d28b6531952f7485c4e630ea52ca5701d`

Both match the rerun record. The first review records the earlier digest before offline resummarization.

- All 324 raw extraction results match the combined result. Worker specifications, execution rotation, logged requests, requested bytes, and observed opens agree.
- Every chosen tile's buffered memberships and footprint fractions reproduce from the saved polygons, grids, and item footprints.
- There are 32 lakes, nine tiles, 40 memberships, and 200 expected lake-bands. Every lake-band has all 36 planned records.
- All 7,200 extraction records retain the first run's value and coordinate digests, compared by tile, lake, band, method, pattern, and repetition.
- All 40 raw preparation results match the combined result. Counts, windows, and mask parameters agree with the first run.
- ZIP directory checksums and lengths agree for numerical members of all 240 mask and index archives across runs. Array payloads were not opened.
- Whole-archive hashes differ because archives also contain run-specific timing metadata. The numerical-member checks support the claimed unchanged masks without reading them.
- The complete summary reproduces from saved JSON, including every method's Stage 2 baseline. All 108 combination medians were checked independently.
- All 130 Stage 2 comparisons use the same acquisition and matching method family. The 70 unmatched lake-bands remain on 16SGD, 17SKT, 17RNL, and 05VLG.
- The naive selection differs on 44 lake-bands, exactly where preparation reports a selection difference. All three naive patterns agree with each other.
- Lanier's recorded selection scores reproduce the stated greedy rule. The selected tiles remain 16SGD and 17SKT.

Finding 19's recomputed ratios are:

| Tile | Requests / Stage 2 | Bytes / Stage 2 | Read time / Stage 2 |
|---|---:|---:|---:|
| 05VMG | 46.15% | 82.00% | 47.12% |
| 10SGJ | 45.54% | 86.57% | 50.81% |
| 10TET | 34.00% | 60.97% | 33.41% |
| 16TGK | 24.05% | 49.12% | 24.47% |
| 17RNK | 44.44% | 82.86% | 47.04% |

Every published rounded percentage agrees.
Finding 20's nine byte ratios and crossover estimates also recompute correctly.
The rounded estimates are 25, 126, 37, 128, 33, 150, 30, 30, and 57 lakes, in tile order.
These are conditional estimates, not tested densities.

The generated presentation table matches its result fields.
The Prototyping lead accurately describes partial results, and the page exposes no internal issue or decision identifiers.
Other than the findings above, its Stage 3 headline figures agree with the measurement findings.

## What the corrected cache establishes

The revised naive setup cost is supported.
Per-lake medians remain below half a second across every pattern. The largest individual setup timer is 0.4738 s.
All saved naive rasterization logs report a single swath, replacing the earlier one-row passes on large polygons.
These are setup wall times, including projection and coordinate construction, rather than isolated CPU measurements.

For raster-mask file-by-file reads, 21 of 26 smaller memberships in anchor tiles request no bytes.
All seven smaller memberships in the two Alaska tiles still request data.
The old Grand Lake 30 m anomaly becomes a zero-request read. Its original cause remains unresolved.
Window sharing improves, while lake-by-lake raster-mask byte medians remain unchanged on all nine tiles.

The lazy shared-graph byte medians also remain unchanged.
Logs confirm repeated chunk reads and 36 opens per 10 m file during whole-tile lazy computation.
The reported 1.6–7.1 byte ratio concerns this recipe, with separate lake computations and no retained decoded chunks.
Smaller chunks, retained chunks, and computing lake outputs together remain legitimate untested options.

The corrected workload ran within the recorded memory limits:

| Measure | Verified value |
|---|---:|
| Extraction peak RSS | 1.9371 GiB |
| Preparation peak RSS | 1.5260 GiB |
| Largest extraction page-out delta | 6,356,992 bytes |
| Largest preparation page-out delta | 1,048,576 bytes |
| Worker RSS budget | 4 GiB |
| Available-memory start check | 1.5 GiB |
| Host page-out pressure threshold | 128 MiB |
| Sampling interval | 0.25 s |

No worker waited, stopped, or crossed the pressure threshold. Every extraction run contributes to its median.
The parent observed a lower peak than the worker reported, illustrating the sampler's inability to capture every brief peak.
This supports successful serial execution of this workload on the laptop. It does not establish safe memory use for larger or concurrent workloads.

Deferring the remaining timing anomalies is acceptable for partial prototype results, with their limits disclosed.
The measured outputs and request counts do not require another full run to address this review.

## Verification and next step

The repository [check workflow](../../.claude/skills/check/SKILL.md) was applied under the retained no-pixel restriction.

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 75 files already formatted.
- `uv run pytest -q tests/test_docs.py tests/test_inventory.py tests/test_render_options.py tests/test_gap_report.py`: 69 passed in 0.38 seconds.
- Independent JSON, geometry, log, and archive-directory audits passed, subject to the documented findings.
- `git diff --check`: passed.

The full `uv run pytest -q` gate remains unrun because its synthetic raster fixtures read pixels.
The selected tests check repository link targets and generated output consistency. They do not validate every external URL or Markdown fragment.
The supplied guidance references a missing `docs/development-workflow.md`. The on-disk AGENTS.md instead points to CLAUDE.md's Workflow section, which was followed.

Next step: Claude corrects the four documentation findings and regenerates the presentation for the owner's review.
Keep Stage 3 labeled partial. Stage 4 starts only after the owner's explicit authorization.
No Stage 4 work began here.
