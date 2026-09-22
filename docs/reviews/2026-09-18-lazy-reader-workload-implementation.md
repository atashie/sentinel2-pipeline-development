# Lazy-reader workload implementation, 2026-09-18

Author: Codex, directed by the repository owner.
Historical record: the [review response](2026-09-18-lazy-reader-review-response.md) supersedes this record's commands, resume restrictions, selection retention, and acquisition fallback.
Status: implementation passed local verification. Provider execution has not started because available RAM is below the approved startup requirement.
The owner authorized the [plan](2026-09-18-lazy-reader-workload-plan.md), including its two single-pass workload comparisons.

## Changes

The new [runner](../../benchmarks/lazy_reader_workloads.py) preserves every existing benchmark recipe and result.
It supervises boundary selection, catalog selection, geometry preparation, extraction, and final comparison.
Each extraction configuration uses one fresh process for the complete cohort.

The [readers](../../benchmarks/workload_readers.py) implement the plan's seven configurations.
The improved lazy reader uses one source block per chunk and computes at most two required chunks together.
Shared processing applies every lake selection before releasing those chunks. Each required block appears in one batch per product and band.
Raster readers use required native-block windows. Workflow A reopens each file between lakes. Workflow B retains each file across its lakes.
Workflow C reads a complete band before extracting lake values, then releases that band.
The current lazy control retains 2,048-pixel chunks and separate per-lake computations. Its concurrency and cache budgets match the improved reader.

Geometry preparation partitions selections by native source block, with a two-pixel halo.
Classification still uses the real polygon boundary and existing geometric tolerances.
Compressed selections live in the owned temporary workspace. No complete lake mask or cohort-wide pixel output accumulates in memory.
Selection reuse requires matching grid, resolution, block shape, and lake identity.

Expected contributions and compact output signatures use disk-backed SQLite tables.
Each source block records ordered pixel identities, classes, raw-value signatures, and no-data counts.
Primary keys reject duplicate records. Completeness checks include empty lake contributions and both directions of the expected-output comparison.
Value comparisons use zero tolerance, independent of workflow execution order.

The presentation adds a comparison section for both larger workloads.
It includes the whole-image lazy reader and the current shared-window lazy control.
Incomplete attempts never display their partial elapsed time as a completed comparison.

## Frozen selection rules

The [selector](../../tools/build_workload_manifests.py) preserves the pilot's public NHD feature-code rules.
It queries identifiers before fetching at most 20 geometries per response. Responses exceeding 16 MiB are rejected.
Every response and request attempt is saved. Permanent source identifiers deduplicate lake candidates.
Boundaries use the existing normalization and validity checks. They do not establish current shorelines or water presence.

Area bands are below 0.1 square kilometer, 0.1 through less than 1, and at least 1.
The upper band has no area ceiling.
The dispersed selector divides the continental bounding extent into 32 geographic strata.
It considers 48 deterministically hashed source identifiers per stratum and area band.
Selection cycles through occupied strata and area bands, preferring spatial separation within each stratum.
The Florida selector starts around Lake County and uses three predefined expanding search envelopes if needed.
It balances available area bands and selects nearby candidates around the recorded central point.
Unavailable bands and shortages remain explicit. Neither selector duplicates lakes to reach the requested count.

The imagery window is 2025-06-01 through 2025-06-30, using Collection 1 and the plan's five bands.
Local groups that could share native tiles use one acquisition.
Ranking retains the accepted coverage, cloud, time, and identity rules from the previous selector.
Distinct datastrips remain separate. Ambiguous primary roles remain unresolved.
Geometry processing visits one lake at a time instead of retaining every lake's transformed catalog context.

Source headers establish actual native grids, data types, and internal block shapes before pixel extraction.
Those metadata reads are separate from extraction measurements. They do not provide imagery to extraction workers.
Both cohorts, code hashes, expected contributions, block coverage, transfer estimates, and run orders freeze before the first pixel read.

## Memory and cleanup

[Resource controls](../../src/s2proto/workload_resources.py) implement the approved allocation budgets and process monitoring.
Startup requires 5 GiB available: the planned worker footprint plus the system reserve.
The monitor includes the supervisor, worker, and descendants. It terminates the worker process group when a limit is crossed.
Array admission accounts for decoded data, copies, concurrent chunks, cache use, and existing worker RSS.
Whole-image reading remains whole-image reading. A rejected allocation produces an incomplete result.
These controls reduce risk. They are not an operating-system-enforced memory guarantee.

Every phase owns a separate temporary directory. Cleanup runs after successful, failed, interrupted, and memory-stopped workers.
The final cleanup removes prepared selections and audits the owned workspace.
Recovery recognizes abandoned directories through ownership markers and the supervisor's process identity.
Cleanup rejects root symlinks and leaves symlink targets outside the workspace untouched.
Manifests, catalog snapshots, logs, expected identities, signatures, and measurements remain available for audit.
No existing imagery or benchmark evidence is deleted.

## Commands

Print the configuration without network access:

```sh
uv run python benchmarks/lazy_reader_workloads.py
```

Run the authorized comparisons in a new directory:

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved
```

The runner refuses an existing run directory and a second attempt of a configuration.
It runs no pilot, progressive subsets, or automatic timing repetitions.
Transport retries remain bounded and logged within the attempt.
The generated result is `benchmarks/results/lazy-reader-workloads.json`.
Worker records and frozen metadata remain under the specified run directory.

Regenerate the local presentation after execution:

```sh
uv run python tools/render_options.py
```

## Verification and execution status

The repository check workflow passed in its required order:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 103 files already formatted.
- `uv run pytest -q`: 238 passed in 15.16 seconds, with 12,432 dependency deprecation warnings.
- `uv run python tools/render_options.py --check`: passed.
- `git diff --check`: passed.
- `uv run --offline --with playwright python /private/tmp/check-s2-browser.py`: passed at 1,280, 768, and 390 pixels.

The 16 new runner tests verify all seven readers, class preservation, complete contributions, raw values, allocation rejection, process termination, and cleanup containment.
They also verify retained datastrips and prevent a lone completed configuration from establishing reader agreement.
A presentation test checks that incomplete attempts cannot appear as complete timing results.
Browser checks found no page overflow, JavaScript errors, or remote requests. All fourteen comparison rows remained visible through their scrollable tables.
The new section's desktop rendering was also inspected visually.

No provider request or downloaded image belongs to this implementation step yet.
The final readiness check reported 3.36 GiB available, below the approved 5 GiB startup requirement.
The owner was asked to free memory or defer provider execution. The planned limits remain unchanged.
No benchmark attempt, timing repetition, or imagery download has been consumed.
Existing contributor changes and all previous benchmark results remain intact.

The initial 12 fixture tests passed.
A later run failed because actual host availability fell below the configured reserve.
The fixtures now inject stable available-memory readings for their small synthetic inputs.
Separate tests still exercise allocation rejection and termination of a real worker and descendant.
The benchmark's live memory readings and limits were not weakened.

## Dispositions and remaining work

Repeated lazy chunk computation: fixed in implementation and verified with synthetic shared-block inputs.
Unequal process counts: fixed in the new runner. Historical timings remain unchanged.
Whole-lake geometry allocations: replaced with bounded native-block preparation and regression checks against existing classes.
Whole-image lazy omission: fixed in the new presentation matrix.
Performance benefits and provider workload completeness: unverified until the authorized full comparisons finish.
Scientific pixel agreement, primary roles, and production storage: accepted and deferred, as the approved plan requires.

The implementation is ready for review. Authorized provider execution remains blocked by available memory.
After sufficient memory is available, execute the recorded command and assess all fourteen configurations without a pilot or timing repetitions.
