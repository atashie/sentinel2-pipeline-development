# Sleep rerun record and comparison page review, 2026-09-21

Reviewer: Claude Code (AI coding agent), directed by the repository owner.
Reviewed: Codex's [rerun record](2026-09-21-sleep-rerun.md) and the larger-workloads section of the [comparison page](../s2-options.html), against the evidence they cite.

Every number in both tables, every ratio in the findings, and every audit claim reproduces from the [replacement result](../../benchmarks/results/lazy-reader-workloads.json) and the [execution audit](../../benchmarks/results/lazy-reader-workloads-audit.json).
The guard, the preserved evidence, the frozen-plan equivalence, and the metadata correction hold in the code and the run directory.
Two measurement definitions need a caveat before the tables are read across readers. Three smaller wording points follow. No result changes.

Scope: I recomputed both tables and all fourteen ratios from the result JSON. I compared the audit rows against the saved power events and the two guard sessions.
I read the [readers](../../benchmarks/workload_readers.py), the [runner](../../benchmarks/lazy_reader_workloads.py), the [resource controls](../../src/s2proto/workload_resources.py), the [rerun tool](../../tools/rerun_sleep_workloads.py), the [audit tool](../../tools/audit_workload_execution.py), and the [renderer](../../tools/render_options.py).
No provider script ran. No pixel was read. This review adds this file and its index row, and commits nothing.

## What holds

- Both tables match the result file to the printed precision, all fourteen rows and seven columns. The page's megabyte and gibibyte values are the same numbers with different rounding.
- Every ratio reproduces: 43.9, 32.5, and 61.6 for the Florida control against B-lazy. 5.9 and 10.4 for sharing windows. 5.1 and 4.8 for bytes. 84.8 and 116.6 minutes, and 53 and 49 for whole-image CPU.
- The counts hold: 100 and 1,000 lakes, 121 and 4 products, and 128 and 1,092 memberships. Block records are 810 and 6,349. Pixel entries are 7,749,457 and 32,096,998.
- All seven signatures agree within each cohort. The three originally complete signatures are unchanged, including the replaced Florida control.
- The audit reports 14 launches, 12 new, 2 retained, 0 sleep overlaps, and 0 memory stops. Both guard sessions are present, with 560 and 65 checks and no errors.
- The saved power log has no sleep event inside either guard session. Sleep resumed six minutes after the first session ended and stopped seven minutes before the second began.
- The preserved files keep their bytes. The original result and audit hash to the values in `run.json`, and the public copies are identical to the run directory copies.
- Each frozen plan differs from its original only in `source_digests` and `sha256`. Products, geometry, order, chunk settings, and limits are equal.
- The guard runs `caffeinate -dis` and checks its three assertions before launch and every 30 s. It requires AC power at start and interrupts the supervisor on loss. The saved assertion listings show the three assertions owned by that process.
- The lazy reader builds each item from the frozen dictionary with an empty link list. The fixture test rejects any PySTAC read, and the offline diagnostic built all 625 graphs with metadata blocked.
- The rerun tool refuses an existing destination, active workers, a mismatched audit, and changed limits. It also refuses a changed source snapshot, incomplete preparation, and an unaffected incomplete attempt.
- The first session's refusal is on disk. Florida `phase-history/extract-C-lazy/0001` and `phase-history/validate/0001` record `insufficient available memory to start` at 19:45:47+00:00 and no spawn.
- The record obeys the document rules: no sentence over 25 words, no semicolon, no banned modal verb, no name.
- The gate passes here. The commands and outcomes are listed under Verification.

## Findings

### 1. Medium: "Read + extract" charges file opens to the raster readers' setup, and to the lazy readers' reads

In `Extractor.raster_asset`, `build_seconds` wraps `rasterio.open()`. That call performs the HTTP size request and the header range reads for the file.
Workflow A calls it once per lake, product, and band. Workflows B and C call it once per product and band.
In `Extractor.lazy_asset`, `build_seconds` wraps `native_array()`, which is graph construction with no request. The same file opens happen inside `dask.compute` and land in `read_seconds`.

| Configuration | Dispersed build s | Florida build s |
|---|---:|---:|
| A-raster | 161.2 | 64.9 |
| A-lazy | 176.1, retained | 53.2 |
| B-raster | 198.0 | 5.0 |
| B-lazy | 9.0 | 0.5 |
| B-lazy-control | 3.6 | 0.4 |
| C-raster | 173.5 | 5.0 |
| C-lazy | 7.8 | 0.5 |

The dispersed raster builds are 605 to 640 opens at 0.25 to 0.33 s each. Florida A-raster is 5,460 reopens at 12 ms each, against 20 opens for B and C.
So the page's definition, "Read + extract measures image reads and value extraction", omits network work for raster readers and includes it for lazy readers.
Comparing that column across readers favors raster. Dispersed C-raster excludes 173.5 s of opens that C-lazy carries inside its 6,989.6 s.
No numeric finding in the record uses the column across readers, so no stated conclusion changes. The page invites the comparison without the caveat.

Fix: state on the page and in the record that raster setup contains one HTTP open per file, and per lake in workflow A. Lazy setup is graph construction. For the next experiment, either time the open inside `read_seconds` or add a setup column.

### 2. Medium: the retained A-lazy total still carries the removed catalog resolution

The retained dispersed A-lazy built 640 graphs in 176.1 s, 0.275 s each. The replacement code builds a graph in 10 to 15 ms, from Florida A-lazy and dispersed B-lazy.
The difference, about 165 s, is the live root and collection resolution that the [original record](2026-09-19-larger-workload-execution.md) identified and the replacement removed.
The record says the correction "changes setup overhead" without a size. Its finding "5.8–8.5 minutes, including retained originals" takes its upper bound from that inflated 509.2 s.
Charged alike, dispersed A-raster is 161 s of opens plus 183.9 s of reads, 345 s in total. A-lazy is 332.5 s of reads that include its opens. The two readers are within 4 percent on that cohort.

Fix: quantify the overhead in the record, and quote A-lazy's read-plus-extract time, 332.5 s, when the retained row bounds a range.

### 3. Low: the dispersed cohort shows no sharing effect in either direction, and the record does not say so

Replacement B-raster read 810 windows in 297.6 s. Retained A-raster read the same 810 windows in 183.9 s, with 1,417 against 1,392 range requests and 571.3 against 569.7 MB.
Same work, 62 percent slower per window, two days apart. B-lazy's reads were also slower than A-lazy's, 447.6 against 332.5 s, with 2,143 against 2,134 requests.
With 128 memberships on 121 products, workflow B has almost nothing to share on this cohort. The record's limitation sentence is correct but does not state the direction.

Fix: add one sentence that the dispersed B rows were slower than the retained A rows at equal requests and bytes. The cohort measures no sharing benefit, and the gap is date and network variation.

### 4. Low: the page footnote describes incomplete attempts that the linked file no longer holds

The source note says "Incomplete attempts retain their partial measurements in the evidence file" and "Their RAM peaks cover only the work reached before failure".
The linked replacement result has fourteen complete attempts. The eleven partial attempts live in the [preserved original result](../../benchmarks/results/lazy-reader-workloads-before-sleep-rerun.json).

Fix: point those two sentences at the preserved file, or render them only when the linked result contains an incomplete attempt.

### 5. Low: one number in the execution narrative has no artifact

"Available RAM measured 7.1 GiB before the second guarded session started" cites nothing, and no file in the run directory records it.
The refusal it follows is recorded, and the second session's start time matches `supervisor.json`.

Fix: name the command whose output gave 7.1 GiB, or drop the number and keep the recorded refusal and restart times.

## Notes without action

- Florida's validate phase was refused at the same moment as C-lazy, and the dispersed validate phase ran in both sessions. Validation is a phase, not an attempt, and its archive under `phase-history` is consistent with the record.
- Worker CPU is `os.times()` user plus system inside the worker process. The dask threads are in-process, so lazy CPU is complete. The supervisor's CPU is excluded, as the record says.
- Peak RAM adds the supervisor's RSS to the worker and its descendants, polled with a 0.1 s sleep between samples. The record's description matches.
- The retry and timeout counters are line counts with separate patterns. A line matching both would count twice. The two logs cited have separate lines for each event.
- The 09-21 raster opens cost 0.29 to 0.33 s each against 0.25 s on 09-19. That is the size of the day-to-day variation the record warns about.

## Verification

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 115 files already formatted.
- `uv run pytest -q`: 269 passed in 33.59 s, with 13,000 dependency warnings.
- `uv run python tools/render_options.py --check`: passed.
- `uv run pytest -q tests/test_docs.py tests/test_render_options.py`: 84 passed after adding this record.
- `git diff --check`: passed.

The result and audit JSON were read, not edited. The run directory was read, not changed.

## Proposed next step

Apply findings 1, 4, and 5 as wording changes to the record, the renderer's source note, and the template. Then regenerate the page and rerun the renderer check.
Fold findings 2 and 3 into the record's findings section as two sentences with the numbers above.
Carry finding 1 into the next experiment's design as a timing rule. Setup and read must mean the same thing for every reader. Nothing here starts that experiment.
