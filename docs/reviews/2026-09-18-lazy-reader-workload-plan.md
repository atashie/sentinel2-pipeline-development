# Lazy-reader improvements and two ingestion workloads, 2026-09-18

Author: Codex, directed by the repository owner.
Status: proposed plan. This step changes planning documents only.
The owner authorized implementation and execution on 2026-09-18. Follow the [implementation record](2026-09-18-lazy-reader-workload-implementation.md) for subsequent status.
The [review response](2026-09-18-lazy-reader-review-response.md) revises execution and resume behavior while retaining the approved limits and fourteen comparisons.
The owner subsequently accepted [recorded geometry non-convergence](2026-09-18-geometry-diagnostic-resume.md) and authorized continuation of the performance comparison.
On 2026-09-21, the owner explicitly authorized [replacement attempts](2026-09-21-sleep-rerun.md) for experiments interrupted by sleep.
That instruction supersedes this plan's single-attempt restriction for those affected configurations.

## Owner direction and scope

The owner requested efficient lazy reading and two larger workloads after discussing the existing extraction results.

| Workload | Requested selection | Repetitions |
|---|---|---|
| Dispersed U.S. | 100 public lakes spread across the continental United States, with varied sizes | One per comparison |
| Concentrated Florida | 1,000 public lakes concentrated in one Florida area, with varied sizes | One per comparison |

There is no live pilot, progressive workload ladder, or search for a break-even threshold.
Downloaded imagery must be deleted after use. Memory protection must cover preparation and extraction.
The owner set no numeric transfer or runtime ceiling. The plan does not impose the earlier suggested pilot limits.

Measurements remain on the laptop under [assumption A25](../assumptions.md).
Public polygons and the required pixel classes follow assumptions A8, A20, and A21 in the same document.
The existing five-file sample remains the proposed band set: red, near-infrared, shortwave infrared, coastal aerosol, and scene classification.
Each local area uses one suitable acquisition. This is an extraction comparison, with no seasonal backfill or production store benchmark.

## Questions the comparison will answer

1. Does eliminating repeated lazy computations reduce requests, bytes, and time on the same source pixels?
2. How do lake-by-lake, shared-window, and whole-image reading compare in each workload?
3. Do many nearby lakes share enough image blocks to change those results?
4. Can each alternative complete its required output within the declared memory limits?

The two workloads differ in both count and geography. Their size distributions will also be reported.
Differences between them cannot be attributed solely to concentration.
The reader and workflow comparisons within each workload use identical inputs.

## Expectations declared before execution

These are unverified experimental expectations. They are not acceptance thresholds or numeric predictions.
The earlier evidence is [findings 19 through 21](../measurements.md#prototype-stage-3-many-lakes-in-one-tile-2026-09-16).

| Comparison | Expected behavior | What could contradict it |
|---|---|---|
| Improved B-lazy versus its current control | Fewer repeated chunk reads and requested bytes where lakes share blocks | Little shared coverage, cache effects, or unexpected loader behavior |
| Improved B-lazy versus B-raster | Similar requested bytes when both reuse the same required blocks. Lazy reading may make more opens and requests | Different range coalescing, cache behavior, or source layout |
| A versus B | More benefit from B when many lakes reuse blocks. Dispersed lakes may offer little reuse | Measured block sharing is low despite geographic concentration |
| C versus windowed reading | Larger transfer penalty when required blocks cover little of each image | Large lakes, broad buffers, compression, or high required-block coverage |
| Runtime across readers | No fixed ordering predicted. Reduced transfer may help, while graph and scheduling work may offset it | Runtime and transfer move in different directions |

Earlier numeric ratios describe different inputs and settings. The new analysis will state which directional expectations held.

## Select and freeze the inputs

Reuse the project's [public water-body source and filtering rules](../../tools/build_pilot_manifest.py), subject to checking service availability during selection.
Build new manifests without changing the existing 32-body pilot or its evidence.
The existing selector needs extension. It currently chooses one candidate per size class and normally excludes candidates above five square kilometers.
Do not carry that candidate-size limit into the new varied-size cohorts.

For the dispersed cohort, distribute selection across geographic strata covering the continental United States.
Use a fixed seed, deterministic tie-breaking, and small, medium, and large area bands.
Prefer spatially separated lakes, while retaining actual tile memberships and any incidental sharing.

For Florida, identify a compact inland lake cluster in central Florida, starting around Lake County.
Choose exactly 1,000 distinct eligible lakes with varied areas. Freeze the final footprint and selection rule before imagery reads.
Candidate availability and the final number of intersected tiles remain unknown until the boundary and catalog queries complete.
Report unavailable area bands instead of silently inventing or duplicating lakes.

Page candidate responses and load only bounded geometry batches. Deduplicate permanent feature identifiers and validate geometry.
Retain public source IDs, boundaries, source dates, area, vertex counts, and selection reasons.
Mapped water boundaries remain test geometry, without asserting current water presence or shoreline accuracy.

Select Collection 1 imagery within a fixed date window using explicit coverage and cloud-ranking rules.
Prefer one acquisition for each local group of overlapping tiles, with dates allowed to differ across distant regions.
If none covers every lake, assign the acquisition covering the most remaining complete lakes, then repeat for the remainder.
Break ties by coverage, cloud cover, sensing time, and acquisition identity. Record every split.
Each lake still uses one complete acquisition, including its buffer. An individually uncovered lake remains a selection failure.
Keep separate datastrips and complete product identities under the [accepted selection corrections](2026-09-16-codex-stage-4-review-response.md).
Include all required lake portions and buffers. Never substitute catalog outlines for precise native-grid coverage.
Retain overlapping observations separately on their native grids. Do not mosaic or resolve the pending primary-tile rule.

Every alternative uses the same products, bands, masks, and expected contributions within its cohort.
Save catalog snapshots, asset identities, polygon hashes, grid metadata, and source-code digests before running comparisons.
Prepare geometry once and report its cost separately. No alternative receives additional imagery through preparation.

## Comparison matrix

Use workload names above, reserving A, B, and C for processing workflows.

| Workflow | Raster reader | Improved lazy reader | Current lazy recipe as control |
|---|---|---|---|
| A: process each lake separately | Run once | Run once | Not included |
| B: share image windows across lakes | Run once | Run once | Run once |
| C: read the complete image before extracting lakes | Run once | Run once | Not included |

This is seven configurations per workload, fourteen full workload passes in total.
Each configuration has one timed attempt. Comparisons necessarily reread the frozen imagery, but there are no repeated timing trials.
The current lazy control isolates whether the improved shared-window recipe helps on these new inputs.
Earlier timings from different lakes are context, never a substitute for this matched control.

Use one fresh supervised worker per configuration, with the configurations running serially.
Within that worker, A visits lakes sequentially and reopens the relevant files between lakes.
B visits source images and shares their reads across lakes. C visits source images and reads each complete band grid.
All three therefore use one process for the complete cohort. Process startup count is held constant.
The older separate-process-per-lake baseline is not mixed into this new comparison.

Keep the geometry inputs, output requirements, cache budgets, and allowed lazy concurrency fixed across configurations.
The legacy control preserves its larger chunks and separate per-lake computations, within the same resource budget.
It is a matched implementation control, not an exact replay of the earlier machine configuration.
Record the order of configurations, using a fixed permutation and a different order for the second cohort.
Fresh workers reset application caches. Provider and operating-system cache effects remain uncontrolled.

## Improve lazy reading without retaining an entire cohort

The existing [shared lazy reader](../../benchmarks/tile_extraction.py) computes each lake separately on a shared graph.
Its [measured repeated-chunk behavior](../measurements.md#21-the-lazy-stack-on-a-shared-tile-graph-reads-16-to-7-times-the-bytes-and-opens-a-file-once-per-chunk) motivates these changes.

- Align lazy chunks with each source band's internal block grid, using its recorded native origin and block shape.
- Use one source block per chunk initially, with two lazy execution threads and no live parameter sweep.
- Map each required chunk to all lakes that use it before scheduling reads.
- Compute bounded groups of distinct chunks together, then apply every relevant lake selection to each computed chunk.
- Keep a decoded chunk until all its consumers finish, then release it before admitting more work.
- Keep each shared-window chunk in exactly one batch per product and band, so lake batching does not recreate repeated reads.
- In workflow A, use the same aligned reader within each lake while preserving the declared lake-by-lake order.
- In workflow C, read a complete band grid once, then extract lakes sequentially and release the grid.

A complete tile graph or thousand-lake output collection must never be persisted in memory.
The lazy graph, active arrays, geometry selections, and output buffers all need bounded lifetimes.
The shared path must not collect every lake's dense masks before starting its reads.
Load selection data by active chunk, and release lake geometry and mask arrays after their consumers finish.

Use the existing native-item loading safeguards. One graph represents one source product on one native grid.
Preserve stored band values, no-data handling, pixel identities, and classes. No resampling, blending, or value conversion enters this performance experiment.
The optimized design is a hypothesis until local tests and the measured comparison establish its behavior.

Prior finding disposition: repeated lazy reads and unequal process counts are accepted and deferred to this implementation.
Their remedies remain unverified. The earlier results retain their measured values and stated limits.

## Memory protection

The current guard samples worker RSS every 0.25 seconds and checks available memory only before startup.
The new runner needs allocation controls as well as a monitor. Polling alone cannot prevent an instantaneous allocation spike.

Proposed limits for the existing laptop:

| Control | Proposed setting |
|---|---|
| Active comparison workers | One |
| Lazy execution threads | Two |
| Planned active worker footprint | At most 2 GiB, including caches, decoded arrays, selections, graph, and temporary copies |
| GDAL block cache | 256 MiB per active worker |
| Active decoded chunks and pending results | At most 512 MiB, within the worker footprint |
| Benchmark RSS abort threshold | 4 GiB across the supervisor, worker, and any descendants |
| System available-memory floor | 3 GiB during execution |
| Start condition | Available memory covers the next bounded allocation plan plus the system reserve |
| Monitor interval | 0.1 seconds |

Apply the same supervisor to catalog processing, geometry preparation, extraction, validation, and cleanup.
Account for decoded data types, array copies, masks, coordinates, and lazy-task concurrency before admitting each batch.
Reject an operation whose conservative allocation estimate exceeds the planned footprint.
Use bounded geometry batches and incremental output signatures. Do not concatenate all selected pixel arrays for a lake or cohort.

Stop the active worker if aggregate RSS exceeds its threshold or available system memory crosses the floor.
Terminate descendants, preserve the partial status and logs, and clean the run's image workspace.
Do not automatically restart a failed configuration or present partial output as a successful full-workload result.
A configuration blocked by memory remains explicitly incomplete.

Whole-image reading processes one band at a time, including for the lazy reader.
If a complete band cannot fit alongside its scratch space and selections, record that limitation.
Do not silently change C into windowed reading or disk-backed processing.

## Image lifecycle and cleanup

Prefer direct range reads, with no permanent local image cache.
Explicit file downloads, lazy spill, memory maps, and extracted pixel arrays belong only in the new run's dedicated temporary workspace.
Release in-memory image arrays after their last consumer. Delete temporary imagery immediately after validation no longer needs it.
Do not retain imagery to warm later benchmark configurations.

Retain the public manifests, catalog snapshots, execution settings, logs, counters, and compact comparison signatures.
Retain compressed geometry selections outside the image workspace, with their frozen digests. They contain pixel positions and classes, without imagery values.
These allow result auditing without retaining downloaded raster data or full extracted pixel arrays.
Keep prior benchmark evidence and unrelated files untouched.

Both the worker and supervisor enforce cleanup on normal completion, errors, interruption, and memory termination.
Record a cleanup manifest and final remaining-file audit.
A recovery sweep handles unfinished image directories owned by this benchmark after an abrupt process or machine shutdown.
An active worker or unresolved launch blocks recovery rather than risking deletion beneath a running process.
Delete only paths verified beneath this run's workspace. Never follow cleanup symlinks into other directories.

## Measurements and correctness

Report one observed result per configuration, without medians, confidence intervals, or claims of repeatability.
Keep preparation, image reading, pixel extraction, validation, startup, and cleanup timings separate, alongside total elapsed time.
Record CPU time, peak benchmark and worker memory, requests, requested bytes, retries, and repeated ranges.
Only label network-delivered bytes when an appropriate counter records them. Requested ranges remain a separate metric.

Record distinct products, tiles, acquisitions, lake-tile memberships, selected pixels, and distinct required blocks beside lake count.
Report image-block coverage by band and resolution. A thousand small lakes can still occupy little of an image.
Record logical output size separately from any actual file size. Production storage writes and retrieval remain untested.

Declare zero tolerance for source-pixel identities, classes, raw values, and expected-contribution counts before execution.
Use deterministic signatures for each native block's selected records, followed by an ordered contribution signature.
This avoids retaining whole-lake arrays while making comparisons independent of execution order.
Verify duplicate and missing pixels explicitly. Equal partial results do not satisfy completeness.
Retain the existing declared geometric tolerances for prepared classes and coverage.

Every configuration must match the frozen reference selections and expected contributions.
A failed or memory-stopped configuration remains visible, with completed and missing work recorded separately.
Do not compare its partial time with a complete configuration's time as a speed result.

## Transfer expectations and execution sequence

Whole-image comparisons will dominate transfer for the dispersed cohort.
Earlier five-file whole-image reads requested 327–410 MB on eight full tiles, as recorded in [finding 20](../measurements.md#20-one-whole-tile-read-costs-6-to-32-times-the-bytes-of-the-windowed-reads-at-this-lake-density).
With 100 such image products, two whole-image passes would request approximately 65–82 GB, before other configurations or overlapping products.
This is a planning extrapolation, not a new measurement or a download ceiling.
Deleting imagery saves disk space after use. It does not reduce the transfer required by separate comparisons.

1. Implement the new selector, bounded readers, supervisor, cleanup, and result reporting.
2. Test local synthetic cases for shared chunks, different grids, output equality, memory stops, missing contributions, and cleanup containment.
3. Run the repository check workflow and record implementation verification.
4. Fetch boundary and catalog metadata, freeze both cohorts, and calculate transfer and allocation estimates without reading imagery.
5. Print per-configuration transfer scenarios, workload counts, and the execution schedule, then stop the preflight command.
6. Invoke extraction separately on frozen inputs. Run each configuration once under memory controls, without a pilot or subset ladder.
7. Validate outputs, delete temporary imagery, and publish local comparison tables with clear completion and memory statuses.

Metadata preflight and local fixture tests are preparation for the full comparisons, not smaller live imagery trials.
No automatic benchmark repetition follows a slow or failed attempt.
Request-level transport retries remain bounded and counted within the single attempt.
Both commands resume an existing owned directory. Successful preparation phases require matching artifact hashes before reuse.
A startup refusal consumes no extraction attempt. Resume may run that configuration after memory becomes available.
A launched extraction is never repeated, including after failure or interruption. Remaining configurations can still run.
The owner's existing authorization covers the full comparison. The command split provides a review point without adding automatic reapproval.

## Implementation boundaries and handoff

Proposed additions are a separate workload selector and a separate benchmark entry point, reusing the existing native readers and geometry rules.
Keep old result JSON and benchmark recipes reproducible. Introduce explicit configuration names for current and improved lazy reading.
Changes to shared helpers require regression tests for the existing readers.
Do not add a production orchestrator, storage system, new sensor, or scientific correction to this experiment.

The completed assessment will show both workloads, all compared configurations, correctness, resource use, and cleanup status.
Presentation tables must include the whole-image lazy results as well as shared-window lazy results.
No workflow or reader is selected for production by this plan.

## Verification and next step

This planning step read existing scripts, measurements, assumptions, and reviews.
It contacted no provider, downloaded no imagery, changed no benchmark implementation, and deleted no existing data.
Only this plan and the review index changed. Existing contributor changes were preserved.

Verification:

- `uv sync --locked`: passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 97 files already formatted.
- `uv run pytest -q`: 220 passed in 12.28 seconds, with 1,476 dependency deprecation warnings.
- `git diff --check`: passed.

Next step: owner and Claude Code review of this concrete plan, followed by its implementation and single-pass workload comparisons.
