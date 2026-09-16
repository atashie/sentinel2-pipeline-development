# Stage 3 review, 2026-09-15

Reviewer: Codex, with separate primary-source research and checking for GDAL cache semantics.
Review completed on 2026-09-16. The filename identifies the reviewed run's date.

The saved run is complete, and its request counts, digests, and comparison tables are reproducible.
However, extraction used a 512-byte GDAL cache despite the stated 512 MB setting.
Correct the performance interpretation and presentation before using this run as engineering guidance.

Scope: the [stage 3 record](2026-09-15-stage-3-many-lakes-in-one-tile.md), saved results, raw artifacts, code, tests, inventory, and presentation.
The reviewed tree starts from `535357c`, with stage 3 changes uncommitted.
This review adds only this file and its index entry. No provider script, imagery download, or pixel read ran.
Stages 4 and 5 remain outside this review.

## Evidence that holds

- All 324 extraction records match their saved raw results. Their GDAL logs reproduce every requested-byte total, request count, and observed file-open count.
- All worker specifications contain their tile's expected members. Actual execution order matches both rotations in `plan.order`.
- Buffered polygon intersections reproduce all 40 memberships across the nine selected grids. No requested lake is unplaced.
- Twenty-four lakes appear once, and eight appear twice. Every membership has all five files and all 36 planned combinations.
- The 200 expected lake-bands therefore have 7,200 individual records. No lake, band, method, pattern, or repetition is missing.
- Mask methods agree on value and coordinate digests throughout. Naive results agree across patterns within their own selection family.
- All 44 naive-versus-mask differences coincide with preparation's recorded selection differences.
- The summary recomputes from JSON without opening masks or imagery. Stage 2 timing sums also recompute from the original per-lake medians.

Evidence: [stage 3 result](../../benchmarks/results/tile-extraction.json) and [stage 2 baseline](../../benchmarks/results/lake-extraction.json).
The stage 3 result digest is `3e52f18ec50c59118d0e131f62909f966b7cf87a6ecb1b9062e3b32986b2cbe2`.
The baseline digest matches the result's recorded reference.
Raw evidence remains under `data/tile-extraction/2026-09-15T201558+0000/`, outside git.

## Findings

### 1. High: the cache setting invalidates the stated clipping-cost interpretation

Locations: [tile_extraction.py](../../benchmarks/tile_extraction.py), `GDAL_ENV`, line 72, and `extract_worker`, line 1401.
Also [finding 22](../measurements.md#22-every-pattern-and-method-agreed-and-the-naive-clip-rasterizes-a-large-lake-for-14-to-20-seconds-per-scene), inventory F-25, and presentation chapter 05.

`rasterio.Env(GDAL_CACHEMAX=512)` means 512 bytes. The subprocess environment string `GDAL_CACHEMAX="512"` instead means 512 MiB.
The extraction worker's explicit Rasterio setting overrides the intended larger cache.
A local configuration-only check returned `512` from `get_gdal_config("GDAL_CACHEMAX")`. It opened no dataset.

Rasterio documents byte units and warns that rasterization repeats geometry work when its cache is smaller than the output.
Separate source research and checking confirmed both claims on 2026-09-15.
Sources: [Rasterio configuration](https://rasterio.readthedocs.io/en/latest/topics/switch.html), [version 1.5.1 setter](https://raw.githubusercontent.com/rasterio/rasterio/1.5.1/rasterio/_env.pyx), and [rasterization notes](https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html#rasterio.features.rasterize).
GDAL's string interpretation is documented in its [cache configuration](https://gdal.org/en/stable/user/configoptions.html#config-GDAL_CACHEMAX).

The first Tahoe log records 3,569 one-row rasterization passes at 10 m, followed by 1,785 and 595 passes at coarser resolutions.
Its filename is `001-10SGJ-lake-by-lake-naive-clip-1.gdal.log` within the raw evidence directory.
This corroborates a configuration-driven slowdown. Its quantitative contribution remains unmeasured.

Stage 3's large-lake numbers are per-lake setup wall times, including projection, rasterization, and coordinate construction.
They are not per-lake CPU measurements. The shared `Timer` uses `time.perf_counter()`.

| Same acquisition | Stage 2 median clipping time, five files | Stage 3 median setup, lake-by-lake |
|---|---:|---:|
| Tahoe, 10SGJ | 0.268 s | 16.837 s |
| Okeechobee, 17RNK | 0.460 s | 16.107 s |

These timers cover different work. Stage 2 also rasterizes separately for each file, whereas stage 3 prepares each resolution once.
Nevertheless, the new 14–20 s claim cannot replace the earlier evidence without explaining the cache difference.
The measured setup times exist, but they do not establish an inherent production cost of naive clipping.

The cache also confounds attribution of speed differences to shared reads alone.
Requested bytes and equality results remain observations of this configuration. They are not measurements under the advertised cache.

Disposition: open. Express the intended Rasterio cache in bytes and record its effective value.
Preserve this run and identify its configuration accurately. Withdraw the general clipping-cost claim pending an owner-authorized, guarded comparison.
Correct the cache statement in the record, measurements, inventory, and presentation implications.

### 2. Medium: requested assets can still disappear from expected coverage

Locations: [tile_extraction.py](../../benchmarks/tile_extraction.py), `expected_lake_bands`, line 628, and asset resolution in `main`.

Expected coverage uses only successfully resolved assets in `scene.assets.assets`.
The requested band list and `scene.assets.missing` do not contribute missing comparisons.
The new fixture removes a returned band while retaining its asset definition. It does not exercise failure during asset resolution.

A JSON-only diagnostic removed Tahoe's resolved `scl` asset and its returned records, while preserving the five requested bands.
It recorded `scl` as missing. The summary reduced expected coverage from 200 to 194 and reported zero incomplete comparisons.

The current run has all five assets on every tile, so its 200 comparisons remain valid.
Missing members and repetitions are now detected correctly. The earlier completeness finding is only partially fixed.

Disposition: open. Include requested-but-unresolved assets in completeness reporting before declaring the earlier finding fully fixed.
Keep missing preparation, unplaced lakes, and requested asset failures visibly distinct.

### 3. Medium: memory-pressure exclusion is incomplete

Locations: [tile_extraction.py](../../benchmarks/tile_extraction.py), `_combo_rows`, line 489, and `_lake_rows`, line 564.
Also the record's memory safeguards and disposition of pre-run finding 7.

Combination medians prefer clean runs, but fall back to pressured runs when no clean run exists.
That fallback is flagged. Per-lake medians ignore the parent run's pressure flag entirely.
The renderer consumes medians without checking the pressure flag.

A JSON-only diagnostic marked one saved run as pressured.
Its combination still received a median, labelled pressured. Its six lake rows each reported one clean run and retained their medians.
This contradicts the categorical promise that pressured runs stay outside timing medians.

No extraction or preparation record in the full run crossed the configured threshold. This defect does not change its medians.
The threshold is 128 MiB of host page-outs, not zero page-outs.
It appears in the smoke-run account and raw records, but is absent beside the main measurement's pressure claim.

Disposition: open. Exclude pressured runs consistently, or clearly expose their status in every affected summary and presentation.
State the threshold beside the pressure conclusion. Keep the reserve described as a start check, rather than reserved host memory.

### 4. Medium: the Prototyping opening still describes the state before stage 3

Locations: [template](../../tools/s2-options.template.html), lines 835–837 and status table, lines 876–880.
The same text appears in the [rendered page](../s2-options.html).

The lead says many lakes per tile remain ahead. The next paragraph says no lake has been read from multiple tiles.
Both statements contradict the completed run and chapter 05. Eight lakes were read from two tiles separately.

The status table partly updates processing costs but still gives the unlabeled stage 2 equality counts.
Its coverage row says exact polygon and buffer coverage still need checking, without distinguishing stage 3 from the pending archive survey.
The test-case cards also say pixel counts and shoreline runtime effects remain unmeasured.

Disposition: open. Reconcile the opening, cards, and status table with stage 3.
Keep cross-tile combination, seasonal testing, AWS execution, and scientific validation explicitly unfinished.
Label retained stage 2 counts by stage.

### 5. Medium: performance prose loses exceptions and turns estimates into recommendations

Locations: [findings 19–22](../measurements.md#19-reading-every-lake-of-a-tile-in-one-process-halves-the-requests), inventory F-25, and [chapter 05](../../tools/s2-options.template.html), lines 970–974.

The comparison tables reproduce the result. Several surrounding statements need narrower wording or corrected numbers.

| Claim | Evidence and correction |
|---|---|
| Small lakes cost four or five requests when their blocks are new | The Alaska 300 m lake uses six requests in 05VLG and ten in 05VMG. Preserve the block-boundary exception |
| Whole tiles cost 327–410 MB and 32–43 s | This excludes 05VLG, which costs 56.801 MB and 7.575 s. Measurements name this exception. F-25 and chapter prose omit it |
| Whole-tile lazy reads are faster | 05VLG takes 7.843 s through lazy loading versus 7.575 s through Rasterio. Its lazy request count is 219, versus 19 |
| Whole-tile lazy bytes agree within 0.1 MB | The maximum median difference is 0.165505 MB, on 16TGK. Use a supported bound |
| Extracting from memory takes at most 0.23 s | This is the largest combination median. The largest individual run takes 0.2441 s. The page's quarter-second bound holds |
| Precomputed masks load in 0.01–0.18 s | Per-lake setup medians across precomputed methods span 0.001–0.170 s. Individual setup timers reach 0.2144 s. Specify the statistic |
| CPU and memory ranges describe runs | The reported CPU ranges describe medians. The memory ranges describe maxima within combinations. Label those aggregations |
| Every tile has one anchor and three to five ponds | The Alaska tiles have no anchor. 17SKT has one anchor and two ponds |

Break-even arithmetic is correct and explicitly labelled an estimate in the table, measurement explanation, F-25, I-20, and chapter paragraph.
However, the page then says whole-tile reading only pays off at roughly a hundred water bodies.
The estimate ranges from 25 to 106 and addresses requested bytes only. It measures neither monetary cost nor a runtime crossover.
The roughly 120-pond figure assumes approximately 400 MB divided by 3.3 MB, without additional sharing.
Neither figure establishes an operational threshold for another lake mixture.

Finding 21 correctly identifies repeated computation on the tested shared graph.
However, “nothing is retained” needs to specify decoded Dask chunks. GDAL can retain downloaded byte ranges separately.
The tested recipe explicitly selects 2,048-pixel chunks, four threads, and separate computations per lake.
Its results do not establish the cost of every odc-stac configuration.
Concurrent fetching is a plausible explanation for faster runs. This experiment does not isolate its causal contribution.
The limits correctly name untried smaller chunks, retained chunks, and computing all lake outputs together.

Disposition: open. Preserve the measured exceptions and distinguish medians, maxima, wall time, bytes, and CPU time.
Present the crossover as conditional byte arithmetic. Describe lazy results as this tested recipe, with the cache limitation from finding 1.

### 6. Low: documentation conventions and a few historical statements need reconciliation

Locations: the [stage 3 record](2026-09-15-stage-3-many-lakes-in-one-tile.md), [measurements](../measurements.md), inventory F-25, template, and [reviews index](README.md).

- The chapter's sentence beginning “Every lake of a tile was read” contains 41 words. Several other sentences exceed the 25-word limit.
- F-25 duplicates long numeric paragraphs from measurements. Static presentation prose and CLAUDE gotchas repeat them again, allowing the discrepancies above.
- The record still predicts Lake Lanier's placement in 17SKU before later describing 17SKT. Label that paragraph as a superseded expectation.
- The index still calls the stage 3 implementation “not yet run”. Its entry needs a separate update with Claude's response.
- The guarded Okeechobee check peaked at 1.448804352 GB, approximately 1.45 GB. The record says 1.40 GB.
- `pixels_read_between` contains worker start times. The last worker starts at 22:02:38 UTC and runs another 4.5664 seconds.

Dates in the reviewed stage 3 material use ISO form. Prose avoids semicolons and the prohibited advisory wording.
The visible presentation contains no internal issue, finding, or decision identifiers.
Generated table duplication is useful presentation. Independently maintained copies of numerical prose undermine the one-fact-one-home rule.

Disposition: open. Shorten sentences, link technical detail to its canonical finding, and reconcile current status statements.
Describe the saved time interval as worker start times unless an actual completion interval is recorded.

## Pre-run dispositions

These assessments concern the [seven pre-run findings](2026-09-15-codex-stage-3-prerun-review.md) and five smaller corrections.

| Earlier finding | Review disposition |
|---|---|
| 1. Baseline mixes selection families | Fixed. Separate naive and mask references, reference consistency, and band-set compatibility are implemented |
| 2. Missing work can look complete | Partially fixed. Expected members and repetitions are checked. Unresolved requested assets remain outside expected coverage, finding 2 |
| 3. Lazy opens and chunk accounting | Fixed. Logs count actual file opens, exclude memory datasets, and distinguish shared from local graph origins |
| 4. Membership and footprint support | Fixed. Buffered intersections identify candidates. Preparation verifies selection, and item scoring includes buffered support |
| 5. Method rotation | Fixed. Both lists rotate. Three repetitions do not fully balance four methods, and no such balance is established |
| 6. Selection retention | Fixed. Both lake-by-lake branches release completed selections. The weak-reference fixture checks the next lake's entry |
| 7. Memory safeguards | Partially fixed. Sampling, budget, start reserve, serial workers, and guarded checks exist. Cache units and pressure exclusion need correction |
| Duplicate tiles merged after choosing an item | Fixed. Regions merge before item selection |
| Naive coordinate comparison absent | Fixed. Coordinate digests agree across all patterns |
| Resummary loses requested lakes or tolerates a missing baseline | Fixed. Requested identifiers and selection survive. Missing or changed recorded baselines stop regeneration |
| Unsupported labelled-mask upper bound | Corrected. The assertion is removed and that design remains unmeasured |
| README claims all lakes yielded stage 2 pixels | Corrected in its status paragraph. It distinguishes 30 successful lakes from two outside their tiles |

## Numeric and selection audit

Finding 19 ratios use `by_tile_pattern_method` divided by its independently checked `baseline_stage_2` sums.
The following percentages retain two decimals to expose the rounding.

| Tile | Requests | Requested bytes | Read time |
|---|---:|---:|---:|
| 05VMG | 53.85% | 98.24% | 51.37% |
| 10SGJ | 48.21% | 87.49% | 61.94% |
| 10TET | 43.00% | 85.30% | 45.05% |
| 16TGK | 34.18% | 86.13% | 39.28% |
| 17RNK | 52.78% | 91.06% | 55.61% |

Every percentage in the finding's table rounds correctly.
All nine rendered comparison rows also match their result fields and the renderer's rounding rules.
The three pattern columns and five applicable stage 2 sums are accurate.

Finding 20 estimates use `whole_tile_bytes / windowed_bytes * membership_count`.

| Tile | Byte ratio | Estimated lake count | Published rounded estimate |
|---|---:|---:|---:|
| 05VLG | 8.4263 | 25.2788 | 25 |
| 05VMG | 26.3822 | 105.5287 | 106 |
| 10SGJ | 6.1701 | 37.0205 | 37 |
| 10TET | 15.2909 | 91.7456 | 92 |
| 16SGD | 6.9046 | 27.6182 | 28 |
| 16TGK | 17.1450 | 85.7252 | 86 |
| 17RNK | 5.4512 | 27.2561 | 27 |
| 17RNL | 7.3997 | 29.5988 | 30 |
| 17SKT | 14.4024 | 43.2072 | 43 |

All 130 baseline comparisons use exactly the same item and matching method family.
The compared counts are 20 for 05VMG, 30 each for Tahoe and Washington, and 25 each for Grand Lake and 17RNK.
The 70 uncompared lake-bands are 20 each for 16SGD and 17RNL, plus 15 each for 17SKT and 05VLG.
No other tile contributes uncompared records.

The Lanier rule and saved `catalog.tile_rule` correctly break ties using shares of lakes being placed, then the smaller tile identifier.
The candidate table's `summed_share_in_tile` instead sums every lake's share. It is not the greedy tie-break score.

| First selection | Lakes eligible for placement | Share sum used by the rule | Candidate table's sum |
|---|---:|---:|---:|
| 16SGD | 3 | 3.000000 | 3.625491 |
| 17SKU | 3 | 3.000000 | 3.625737 |
| 17SKT | 3 | 2.702587 | 2.702587 |

16SGD wins its tie with 17SKU by identifier. Afterward, 17SKT places the remaining two lakes with a share sum of 1.702587.
16SGC's recorded two placements cannot beat the first-round leaders.
The anchor belongs on 17SKT under this placement rule because its share is 0.702587, exceeding 17SKU's 0.625737.
The explicit rule is correct. The record's shorter reference to tied ponds does not fully explain both selected tiles.
Clarify that explanation without changing selection.

Other checked figures match the evidence, subject to the statistic and exception corrections above:

- Total requested data are 45.613231602 GB in 19,741 requests. The 108 whole-tile runs account for 36.251046951 GB.
- Catalog accounting totals 1,473 returned items, 24 requests, and 26.072884 MB. Selected item dates, baselines, cloud fractions, and membership shares match.
- Preparation has 40 records, totaling 94.1279 seconds. Its maximum is 20.7331 seconds, and peak memory is 1.227676 GiB.
- Raster-mask windows touch 20–112 blocks summed across lakes, and 16–92 distinct blocks among 548. The distinct fractions are 2.92–16.79%.
- Seven of 33 non-anchor memberships have zero requests. Their lake identifiers and tiles match finding 19's list.
- Loop-order differences reach 14 requests, 3.653632 MB, and 2.342 seconds. The claimed rounded bounds hold for the raster-mask medians.
- Shared-graph lazy byte ratios span 1.5479–5.0626, and read-time ratios span 1.3814–3.3132. Lake-local byte ratios span 0.8765–1.2234.

## Lazy-reader and memory evidence

Every whole-tile lazy log shows 36 opens per 10 m file, nine per 20 m file, and one for coastal.
The open counter correctly excludes `MEM:` datasets used during rasterization.
Grand Lake's shared red graph has one distinct touched chunk but five computations and five file opens.
Its recorded red requests total 26.981079 MB, approximately five reads of 5.4 MB.
This confirms repeated requested ranges for this case, beyond merely repeated graph execution.

All full-run workers record a 4 GiB budget, a 1.5 GiB start reserve, and the 128 MiB pressure threshold.
The parent samples RSS at 0.25-second intervals and checks available host memory before starting each worker.
It records host page-in and page-out deltas, sampled RSS, and worker peak RSS.
The reserve is not enforced throughout execution, and brief allocation spikes can escape sampling.

| Evidence group | Workers | Highest worker RSS | Largest page-out delta |
|---|---:|---:|---:|
| Full extraction | 324 | 1.483063 GiB | 7,438,336 bytes |
| Full preparation | 40 | 1.227676 GiB | 3,522,560 bytes |
| Guarded Okeechobee extraction | 24 | 1.349304 GiB | 6,242,304 bytes |

No full-run worker waited, failed, or stopped for memory. Page-out deltas ranged from zero to the maxima above.
The smoke run has 12 successful workers and 25 complete lake-bands. Its earlier pressure rule flags all 12.
The guarded check has 45 complete lake-bands and 25 baseline comparisons. Neither preliminary run was reused in the full result.

The full run therefore establishes successful execution under its actual configuration.
It does not establish the memory peak after restoring the intended larger cache.

## Acceptable open investigations

The Grand Lake 30 m pond requests 6,586,368 bytes in four requests with the file open.
Lake-by-lake requests 3,112,960 bytes, also in four requests. All three repetitions reproduce each pattern's total.
The anomaly is real. Its cause remains unverified.

Twelve runs exceed 1.5 times their combination's median wall time.
The largest is 93.3484 seconds against a 37.981-second median, on 16SGD with whole-tile index lists.
Their logs and raw records remain available.

Deferring both investigations is acceptable for this exploratory stage, with the anomalies disclosed and precise method rankings withheld.
The known cache defect requires correction before attributing remaining differences to network conditions or reader design.

## Verification and next step

The repository [check workflow](../../.claude/skills/check/SKILL.md) was applied with a pixel-read restriction.

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 74 files already formatted.
- Documentation, inventory, renderer, and saved-report tests: 68 passed in 0.35 seconds.
- JSON, geometry, and log audits ran independently of provider scripts and raster fixtures.

The full `uv run pytest -q` gate remains unrun because its synthetic fixtures read pixels.
The owner's explicit restriction takes precedence. Clarification was requested, without treating silence as authorization.
The selected tests verify repository link targets and generated HTML consistency. They do not validate every external URL or Markdown fragment.

`git diff --check` passed. This review changed only its new record and one index row.
Existing uncommitted implementation and documentation changes remain untouched.

Next step: Claude responds to these findings and prepares the code and documentation corrections for review.
Any corrective pixel experiment needs owner authorization. Preserve the present result as evidence of the configuration that actually ran.
Stage 4 remains the next workload only after the owner authorizes it. No stage 4 work began here.
