# Sleep-interrupted workload reruns, 2026-09-21

Author: Codex, directed by the repository owner.
The owner explicitly authorized rerunning experiments interrupted by laptop sleep, completing them, and updating results and documentation.
This supersedes the previous single-attempt restriction for the twelve affected configurations.

All twelve replacements completed. Together with two retained originals, all fourteen comparisons are complete and their outputs agree within each cohort.
The final audit records zero sleep overlaps, zero worker memory stops, verified frozen inputs, and complete temporary-image cleanup.
The [2026-09-22 review response](2026-09-22-sleep-rerun-review-response.md) records subsequent timing clarifications and qualifications of the review's interpretations.

## Scope and preserved evidence

The [original execution record](2026-09-19-larger-workload-execution.md) documents fourteen attempts, including twelve with sleep overlap.
Dispersed A-raster and A-lazy completed without recorded sleep. Their original observations remain in the comparison.
Five dispersed configurations and all seven Florida configurations receive replacement attempts.
No unaffected configuration is repeated.

The replacement directory is `data/lazy-reader-workloads/2026-09-21-sleep-rerun`.
The original directory, source snapshot, results, logs, and signatures remain preserved.
The [original result](../../benchmarks/results/lazy-reader-workloads-before-sleep-rerun.json) and [original audit](../../benchmarks/results/lazy-reader-workloads-audit-before-sleep-rerun.json) retain their exact bytes.

The recovery tool verifies the original audit's result hash, all preparation artifacts, source snapshots, and frozen selections.
It refuses an existing destination, active original workers, changed memory limits, or an incomplete unaffected configuration.
Each copied input and retained attempt receives a recorded hash in the new run identity.
Only source-version metadata and its plan digest change in each frozen plan.
Geometry, products, bands, output requirements, configuration order, chunk settings, and memory limits remain unchanged.

## Corrections before execution

The lazy reader constructs standalone items from saved metadata, excluding catalog links from the in-memory copy.
Frozen item files and absolute asset URLs remain unchanged.
This removes implicit live root and collection resolution from graph construction.
The existing synthetic comparison now blocks PySTAC metadata reads while executing all seven readers against known pixels.
It passes with matching values, positions, classes, and complete output counts.

All 625 native graphs from the actual frozen cohorts also built with metadata reads blocked.
That diagnostic computed no pixels and contacted no provider.
Its evidence is `diagnostics/offline-graphs.json` in the replacement directory.

The recovery command acquires macOS display, idle-system, and system-sleep assertions before extraction.
It checks ownership of both system-sleep assertions before launch and every thirty seconds during execution.
Losing the guard interrupts the supervisor, which terminates its worker group and performs normal cleanup.
The guard requires AC power at startup and releases its assertions when extraction exits.
Explicit sleep, lid closure, shutdown, and power loss remain outside this protection.
Saved macOS power events independently qualify each attempt afterward.

Dispositions of prior findings:

| Finding | Disposition |
|---|---|
| Sleep interrupted twelve attempts | Fixed operationally. Twelve replacements completed under verified sleep prevention, with zero sleep overlaps in the final audit |
| Lazy graph construction resolved a live catalog | Fixed and verified with blocked metadata access on synthetic execution and all frozen native graphs |
| Python HTTP calls lacked a bound | Removed from replacement extraction by using standalone frozen metadata. Future live metadata work remains separate |
| Geometry convergence blocked performance work | Existing diagnostic fallback retained without changing tolerances or selected pixels |
| Single-attempt restriction prevented repeats | Superseded by the owner's explicit 2026-09-21 rerun instruction for affected configurations |

The [geometry assessment](2026-09-18-claude-geometry-blocker-assessment.md) prioritizes workflow measurements and records numerical non-convergence without blocking extraction.
Its accepted [implementation](2026-09-18-geometry-diagnostic-resume.md) remains in place.
Lake Yale retains the recorded refinement with the smallest bound. No tolerance, cohort member, or prepared pixel selection changes for these reruns.
Re-deriving the support bound remains accepted and deferred.

## Measurement interpretation

The [replacement result](../../benchmarks/results/lazy-reader-workloads.json) contains worker measurements and complete-output checks.
The separate [execution audit](../../benchmarks/results/lazy-reader-workloads-audit.json) binds its result hash, sleep evidence, source versions, and preserved inputs.

Workflow A reads each lake separately. Workflow B shares image access across lakes. Workflow C reads each complete image before selecting lake pixels.
The improved lazy reader uses native blocks. The lazy control retains larger chunks and separate computes for each lake window.

Elapsed extraction includes reader setup, pixel reads, selection, signature checks, and output bookkeeping, excluding shared preflight preparation.
**Measured instrumentation:** Raster setup includes `rasterio.open()` and any HTTP size or header requests performed there.
Workflow A reopens each product band for each lake. Workflows B and C open each product band once.
An open call does not imply a separate HTTP request because cached metadata can be reused.
Lazy setup constructs graphs. Its file opens occur inside timed computes and count toward read time.
Therefore, the read-plus-extract components are not directly comparable across raster and lazy readers.
Use total extraction for comparisons across readers, retaining the source-version and measurement-date limitations below.
The [reader implementation](../../benchmarks/workload_readers.py) defines these boundaries.

Worker CPU sums user and system CPU seconds. It does not measure billed compute or CPU utilization across the whole laptop.
Peak RAM sums the supervisor and worker processes, sampled every 0.1 seconds. Spikes shorter than the sampling interval can be missed.
Requested bytes come from GDAL HTTP ranges. They are not measured wire traffic, retained output size, or cloud charges.
No currency cost is inferred from these laptop observations.

## Measured results

Both tables come from the [replacement result](../../benchmarks/results/lazy-reader-workloads.json).
GB means decimal gigabytes. GiB means binary gibibytes. Times are seconds, rounded to one decimal place.
All rows passed completeness and agreement checks for positions, classes, raw values, and expected contributions.

### Dispersed cohort

The cohort contains 100 lakes, 121 products, 120 tiles, 120 tile-dates, and 128 lake-product memberships.
Each workflow produced 810 expected block records covering 7,749,457 selected pixel entries.

| Configuration | Read + extract s | Total extraction s | Worker CPU s | Peak RAM GiB | Requests | Requested GB |
|---|---:|---:|---:|---:|---:|---:|
| A-raster, retained | 183.9 | 345.6 | 11.0 | 0.227 | 2,022 | 0.571 |
| A-lazy, retained | 332.5 | 509.2 | 24.8 | 0.291 | 2,134 | 0.535 |
| B-raster | 297.6 | 496.2 | 10.8 | 0.223 | 1,997 | 0.570 |
| B-lazy | 447.6 | 457.2 | 24.4 | 0.293 | 2,143 | 0.535 |
| B-lazy-control | 748.6 | 752.8 | 51.7 | 0.372 | 2,991 | 2.704 |
| C-raster | 4,915.7 | 5,089.7 | 569.9 | 1.026 | 5,792 | 41.466 |
| C-lazy | 6,989.6 | 6,998.0 | 1,197.0 | 0.993 | 58,842 | 42.002 |

### Florida cohort

The cohort contains 1,000 lakes, four products, four tiles, four tile-dates, and 1,092 lake-product memberships.
Each workflow produced 6,349 expected block records covering 32,096,998 selected pixel entries.

| Configuration | Read + extract s | Total extraction s | Worker CPU s | Peak RAM GiB | Requests | Requested GB |
|---|---:|---:|---:|---:|---:|---:|
| A-raster | 532.1 | 599.6 | 63.4 | 0.239 | 2,755 | 1.801 |
| A-lazy | 644.2 | 701.3 | 128.0 | 0.301 | 2,698 | 1.633 |
| B-raster | 95.5 | 101.8 | 9.1 | 0.332 | 464 | 0.352 |
| B-lazy | 66.2 | 67.7 | 10.5 | 0.296 | 513 | 0.337 |
| B-lazy-control | 2,970.7 | 2,974.1 | 343.0 | 0.311 | 13,283 | 20.789 |
| C-raster | 154.5 | 159.8 | 20.9 | 1.027 | 205 | 1.519 |
| C-lazy | 265.2 | 266.2 | 40.9 | 0.864 | 2,173 | 1.540 |

### Findings and interpretation

**Measured:** Florida's control took 43.9 times as long as B-lazy, used 32.5 times its worker CPU, and requested 61.6 times its bytes.
Their RAM peaks were similar. The control's main observed penalties were repeated reads and processing time, rather than a larger peak footprint.
Its log recorded 13,002 repeated exact ranges, compared with zero for B-lazy.

**Measured:** Sharing windows reduced Florida elapsed time by factors of 5.9 for raster and 10.4 for improved lazy, compared with separate-lake reads.
Raster requested 5.1 times fewer bytes. Improved lazy requested 4.8 times fewer bytes.
Florida B-lazy had the lowest elapsed time. B-raster used slightly less worker CPU.

**Measured:** Dispersed whole-image reads requested about 41–42 GB, compared with about 0.53–0.57 GB for native window workflows.
Their elapsed times were 84.8 and 116.6 minutes. Replacement B-raster and B-lazy totals were 8.3 and 7.6 minutes, respectively.
The raster and lazy whole-image workflows used about 53 and 49 times their respective B-workflow CPU time.
These comparisons support treating distinct products and image coverage as workload dimensions alongside lake count.

**Measured:** Retained dispersed A-lazy spent 176.1 seconds in setup and 332.5 seconds in read-plus-extract, within its recorded 509.2-second total.
Its setup includes the catalog resolution removed from the replacement source.
The component time excludes setup and cannot replace the total or establish equivalent performance against A-raster's 345.6-second total.

**Estimated:** Replacement graph-build rates imply 6.2–9.5 seconds for the retained row's 640 graph builds, about 167–170 seconds below its recorded setup.
This scales Florida A-lazy's 53.2 seconds over 5,460 builds and dispersed B-lazy's 9.0 seconds over 605 builds.
It estimates a setup difference across versions and runs. Catalog requests were not timed separately, so their exact contribution remains unmeasured.

**Measured:** Dispersed B-raster's read-plus-extract component was 297.6 seconds versus retained A-raster's 183.9 seconds.
B-lazy's component was 447.6 seconds versus retained A-lazy's 332.5 seconds, although B-lazy's total was lower.
Request counts were nearly unchanged, and sharing reduced requested bytes by less than 0.3 percent for either reader.
B-lazy read 805 native blocks versus A-lazy's 810, showing limited reuse rather than no reuse.
**Inference:** This cohort offers little sharing opportunity. These observations establish no consistent elapsed-time benefit from sharing.
Different dates, source versions, and network conditions prevent assigning the timing gaps to a single cause.

**Measured:** Whole-image peak RAM ranged from 0.864 to 1.027 GiB, compared with 0.223 to 0.372 GiB for window workflows.
Every observed peak remained below the unchanged 4 GiB aggregate stop threshold.
The separate startup refusal reflected available host memory, not an extraction worker exceeding that threshold.
Whole-image lazy peaks were below whole-image raster peaks in both cohorts, despite greater CPU time and request counts.

**Measured:** Dispersed C-lazy recorded one retry message and one timeout message, then completed.
Florida's control recorded two retry messages and seven timeout messages, then completed.
These are transport log counts. Neither required an additional worker attempt.
Consequently, the elapsed ratios include observed network delays and cannot isolate reader implementation effects.

**Inference:** Shared native windows merit the next review for concentrated workloads.
Whole-image reads remain useful comparison cases, but these observations do not select a production workflow or compute platform.
Dispersed A-versus-B elapsed differences are especially limited by retained dates, source versions, and uncontrolled network conditions.

## Commands and execution record

Preparation contacts no provider:

```sh
uv run python tools/rerun_sleep_workloads.py --prepare-from data/lazy-reader-workloads/2026-09-18-approved --destination data/lazy-reader-workloads/2026-09-21-sleep-rerun --audit data/lazy-reader-workloads/2026-09-18-approved/execution-audit.json --reason 'Owner requested rerunning all sleep-interrupted experiments on 2026-09-21, ensuring completion and updating results and documentation.'
```

Extraction uses the existing serial workers, bounded transport retries, memory supervision, signature validation, and image cleanup:

```sh
uv run python tools/rerun_sleep_workloads.py --extract data/lazy-reader-workloads/2026-09-21-sleep-rerun
```

Preparation completed. The prelaunch guard initially refused extraction because macOS reported battery power.
No replacement worker launched during those refusals.
The owner connected power and confirmed the lid would remain open.
The guard verified its sleep assertions before starting dispersed B-raster on 2026-09-21.
The first guarded session completed six replacement workers between 15:06:12+00:00 and 19:45:47+00:00.
It recorded 560 successful guard checks and no guard errors.
Available RAM then fell below the unchanged 5 GiB startup requirement before Florida C-lazy could launch.
That refusal consumed no extraction attempt and did not invalidate completed measurements.
The released guard, assertions, power events, and interim result were archived with hashes under `diagnostics/keep-awake-history/0001`.
The owner freed memory and explicitly requested resumption.
The second guarded session started at 2026-09-21T20:35:25+00:00.
The runner retained every completed attempt and resumed Florida C-lazy.
The second session completed all six remaining workers and both cohort validations, ending at 2026-09-21T21:07:10+00:00.
It recorded 65 successful guard checks and no errors. The extraction command exited successfully.

The final offline audit command was:

```sh
.venv/bin/python tools/audit_workload_execution.py data/lazy-reader-workloads/2026-09-21-sleep-rerun --power-log data/lazy-reader-workloads/2026-09-21-sleep-rerun/diagnostics/power-events.log --output benchmarks/results/lazy-reader-workloads-audit.json
```

The [audit](../../benchmarks/results/lazy-reader-workloads-audit.json) verifies twelve new extraction launches and two retained originals.
Every current attempt falls inside a saved guard session. No measured attempt overlaps recorded sleep.
All three originally complete output signatures remain unchanged, including the replaced Florida control.
Source snapshots, frozen plan equivalence, copied inputs, and retained attempt hashes pass verification.
No benchmark worker remains active. Every per-attempt cleanup passes, and the owned temporary-image workspace is removed.
Diagnostic logs, output signatures, and original evidence remain available locally.

## Verification and limits

Before preparation, repository checks passed: environment synchronization, lint, formatting, and 267 tests in 29.41 seconds.
The historical-evidence preservation follow-up passed lint, formatting, and all three recovery tests.
After reporting changes, repository checks passed again: synchronization, lint, formatting, and 268 tests in 29.61 seconds.
Inventory, sensor dataset, presentation renderer, and gap-report checks passed. `git diff --check` passed.
The final result audit passed with fourteen complete comparisons, no incomplete workers, and no memory stops.
Final repository verification passed:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 115 files already formatted.
- `uv run pytest -q`: 269 passed in 29.03 seconds, with 13,000 dependency deprecation warnings.
- Inventory, sensor dataset, presentation renderer, and gap-report `--check` commands: passed.
- `git diff --check`: passed.

After the final presentation wording change, documentation and renderer tests passed: 84 tests in 0.10 seconds.
The renderer check and three-width browser check passed again.

The local browser check passed at widths of 1,280, 768, and 390 pixels.
Every width displayed fourteen complete comparisons, two retained-original labels, and both worker-CPU columns.
No page overflow, JavaScript error, or remote request occurred. Retained original timings were preserved.
The browser report and section screenshot are saved under `diagnostics/presentation` in the replacement directory.
The screenshot was inspected. Source files remain identical to the extraction snapshot, and nothing was staged, committed, pushed, or published.

Retained original observations and replacement observations use different source versions and measurement dates.
The lazy metadata correction changes setup overhead. This is an operational comparison, without controlled network conditions or timing repetitions.
Scientific validation, primary-tile decisions, production storage, and compute-platform selection remain deferred.

## Proposed next step

Review the completed comparison with the owner and the reviewing agent.
Use elapsed time, CPU, requested bytes, and peak RAM to scope the next experiment across representative product counts and lake concentrations.
For the next experiment, charge file opening and associated network work to the same timing category for every reader.
Report setup separately and retain total extraction, so component boundaries can be audited.
Keep geometry-bound refinement and scientific validation as separately reviewed work.
No further provider run, production choice, commit, push, or publication is part of this step.
