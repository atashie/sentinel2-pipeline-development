# Larger workload execution, 2026-09-19

Updated 2026-09-20. All fourteen single attempts finished. Three workers completed and eleven failed. The overall comparison remains incomplete.

The owner authorized replacing sleep-affected attempts on 2026-09-21. The [rerun record](2026-09-21-sleep-rerun.md) owns subsequent execution and results.

Author: Codex, directed by the repository owner.
The owner authorized incorporating the [geometry assessment](2026-09-18-claude-geometry-blocker-assessment.md) and continuing the full performance experiment.
The [implementation response](2026-09-18-geometry-diagnostic-resume.md) records corrections, tests, and deferred geometry research.
This record tracks the resumed preflight and extraction in the existing owned directory.

## Preflight review

The source supersession is recorded once in `data/lazy-reader-workloads/2026-09-18-approved/run.json`.
Its previous version and preparation artifacts remain in `source-history/0001/` beneath that directory.
All current source digests and archived artifact hashes passed verification.
Boundary and catalog phases were reused through their existing hash checks.

Both cohorts completed preflight. The offline audit passed at `2026-09-19T16:52:13+00:00`.
The audit script is `check-refrozen-preflight.py`, and its result is `refrozen-preflight-review.json`, both within the run directory.

The dispersed selection and expected-output databases are byte-for-byte identical to their archived versions.
Selected products, memberships, acquisition assignments, band set, order, tolerances, and memory limits also match.
Plan metadata differs only in creation time, source digests, the added limitation, and the empty unconverged-geometry list.

Florida records exactly one unconverged geometry diagnostic: Lake Yale, `nhd-112613946`.
Its acquisition is `GS2B_20250601T155819_043023_N05.11`, matching the assessment's offline prediction.
No extraction launch record existed when this preflight review passed.

Historical transfer scenarios remain proxies, not forecasts or ceilings. They are retained per configuration in each cohort's `preflight.json`.
The owner authorized the complete comparison without a transfer ceiling.

## Execution

Command:

```sh
uv run python benchmarks/lazy_reader_workloads.py --extract data/lazy-reader-workloads/2026-09-18-approved
```

Execution finished after one worker launch for each of the fourteen configurations.
The runner retains CPU time, separate read and extraction timings, sampled RAM peaks, request counters, and compact output signatures.
Each phase removes its owned image workspace after use. Worker failures remain incomplete and are never retried as timing attempts.

The performance comparison does not establish scientific validity, production throughput, or a selected production workflow.

The [original benchmark result](../../benchmarks/results/lazy-reader-workloads-before-sleep-rerun.json) records every configuration, including incomplete attempts.
The preserved [execution audit](../../benchmarks/results/lazy-reader-workloads-audit-before-sleep-rerun.json) verifies source integrity, frozen inputs, all fourteen launches, cleanup, and sleep overlap.
No memory guard stopped a worker. No failed attempt was repeated.

## Completed work and interpretation

Measured values below come from the benchmark result. Peak benchmark RAM includes the worker and supervisor.

| Cohort | Configuration | Extraction timer, seconds | Worker CPU, seconds | Requested MB | Requests | Peak benchmark GiB | Interpretation |
|---|---|---:|---:|---:|---:|---:|---|
| Dispersed | A-raster | 345.6 | 11.00 | 571.3 | 2,022 | 0.227 | Complete, agrees with A-lazy, no recorded sleep overlap |
| Dispersed | A-lazy | 509.2 | 24.75 | 535.3 | 2,134 | 0.291 | Complete, agrees with A-raster, no recorded sleep overlap |
| Florida | B-lazy-control | 2,993.5 | 319.21 | 20,949.1 | 13,358 | 0.332 | Complete output count, agreement unverified, sleep interrupted |

In the completed dispersed pair, raster used less elapsed time, CPU time, and peak RAM. Lazy requested fewer bytes but more requests.
These are single observations on the same frozen workload. They do not establish repeatability or a general reader ranking.
The lazy timer also includes the live catalog behavior described below. Its request count covers GDAL requests, not those Python requests.

Florida's control recorded 13,086 repeated exact ranges. The improved shared-window attempt failed, so this experiment cannot quantify its improvement against that control.
The failed attempts cannot establish complete-workload timings or memory requirements.
The largest observed aggregate RSS was 0.898 GiB during a partial whole-image attempt. Its failure prevents treating that value as a full-workload requirement.

## Laptop sleep and timing limits

The saved macOS power log records sleep overlap in twelve attempts. Only the two completed dispersed lake-by-lake configurations have no recorded overlap.
Florida's completed control overlaps twenty-nine sleep intervals. Its extraction timer is not an uninterrupted wall-clock measurement.
The audit compares saved start timestamps and supervision-file modification times against sleep and wake events.
The recorded elapsed timers differ from observed wall time across sleep.
Sleep is a demonstrated confound. It does not prove the cause of each network failure.

Codex did not establish an idle-sleep assertion before extraction. That was an execution oversight.
The scoped `caffeinate -i -w 38318` command was invoked after detecting the issue, but the runner had already finished.
It therefore protected none of these measurements and left no continuing sleep assertion.
The presentation labels affected rows and does not display interrupted elapsed times as completed comparisons.
It still reports CPU, requested bytes, and requests for completed workers whose peer agreement remains unverified, with that status visible.

## Failures observed during execution

Dispersed B-raster failed after a timed-out HTTP range request returned an incomplete TIFF block.
Dispersed C-raster also failed with an image-read error. Their partial times are not complete-workload comparisons.
Dispersed B-lazy and B-lazy-control failed while resolving the Earth Search root catalog through PySTAC.
The traceback reaches `load_native_item`, `Item.to_dict`, link serialization, and `get_root` before the failing HTTPS response.
Thus, these lazy paths perform live catalog resolution even when the item metadata is already frozen.
GDAL range counters do not account for those separate Python HTTP requests.

The B-lazy stall was sampled before it exited. The main thread was blocked in Python SSL reading while compute threads were idle.
The stack and intervention record remain under `diagnostics/dispersed-B-lazy-stall/` in the run directory.
The first attempted interrupt was denied by the sandbox. The worker exited before the approved retry, so no signal was sent.
Its saved exception reports that the remote end closed the connection without a response.

These failures are operational evidence. They do not establish the readers' completed-workload speed or a geometry defect.
No failed configuration was retried. Source code and frozen selections remain unchanged after the first extraction launch.

Across both cohorts, eight failures report image-read errors and three report STAC root resolution errors.
The offline serialization diagnostic blocked all network access.
Default `Item.to_dict()` attempted a root-catalog read. `to_dict(transform_hrefs=False)` made no request and preserved all asset URLs.
This identifies a concrete serialization correction. The diagnostic alone does not verify the full lazy graph path without network metadata.

## Cleanup, audit, and verification

All fourteen launch records remain present. The saved result and public benchmark result have identical hashes.
All frozen source and input hashes passed. Every extraction cleanup record reports no remaining files.
The owned image workspace is absent, and no benchmark worker remains active.
Original geometry evidence and source history remain preserved. No files were staged, committed, pushed, or published.

Offline audit command:

```sh
uv run python tools/audit_workload_execution.py data/lazy-reader-workloads/2026-09-18-approved --power-log data/lazy-reader-workloads/2026-09-18-approved/diagnostics/power-events.log --output benchmarks/results/lazy-reader-workloads-audit.json
```

The command contacts no provider and writes a separate audit. It does not alter benchmark result JSON.
Final repository checks passed in the required order:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 112 files already formatted.
- `uv run pytest -q`: 264 passed in 28.98 seconds, with 13,000 dependency warnings.

Inventory, sensor dataset, presentation renderer, and gap-report `--check` commands passed. `git diff --check` passed.
The Git index remains empty.
The browser check passed at 1,280, 768, and 390 pixels, with all fourteen rows visible and no page overflow, JavaScript errors, or remote requests.
The desktop comparison was inspected visually. Browser evidence remains under `diagnostics/presentation/` in the run directory.

## Proposed next step

Preserve this run as fourteen used attempts with explicit failures and timing limitations.
Before any new experiment, establish a scoped keep-awake guard and verify graph construction from saved metadata without live catalog resolution.
Add a bounded policy for Python HTTP calls and test it independently of GDAL's retry settings.
Review any new attempts explicitly against the owner's single-attempt instruction. None is started here.
The geometry convergence criterion, scientific validation, primary-tile decision, and production storage remain deferred.
