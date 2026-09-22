# Lazy-reader workload plan and implementation review, 2026-09-18

Reviewer: Claude Code (AI coding agent), directed by the repository owner.
Reviewed: Codex's [plan](2026-09-18-lazy-reader-workload-plan.md) and [implementation record](2026-09-18-lazy-reader-workload-implementation.md) of 2026-09-18, with the code they describe.

The implementation follows the approved plan closely, and the readers are correct on the fixtures. The run is not yet safe to start as one command.
One invocation fetches boundaries and catalogs, freezes both cohorts, and reads an estimated 80 to 140 GB of imagery over several hours. It has no stop for the owner and no way to resume.
Five points need a change before execution. Four smaller ones can follow.

Scope: I read the [runner](../../benchmarks/lazy_reader_workloads.py), the [readers](../../benchmarks/workload_readers.py), the [resource controls](../../src/s2proto/workload_resources.py), the [selector](../../tools/build_workload_manifests.py), the [tests](../../tests/test_lazy_reader_workloads.py), and the renderer and template changes.
I checked them against [masks.py](../../src/s2proto/masks.py), the stage 3 and 4 scripts, and [findings 16 to 21](../measurements.md). I also used the [accepted Stage 4 response](2026-09-16-codex-stage-4-review-response.md) and the saved pilot responses under `data/pilot-manifest/`.
No provider script ran. No pixel was read. This review adds this file, its index row, and two pointer sentences, and commits nothing.

## What holds

- The code does what the plan says. Seven configurations per cohort, one fresh supervised worker each, serial execution, and a fixed order per cohort. The lazy control keeps 2,048-pixel chunks and one compute per lake. The improved lazy reader aligns chunks with the file's blocks, computes at most two blocks together, and applies every lake's selection before releasing them.
- Block-partitioned classes equal the whole-lake classes. `compute_mask` never clips the polygon, its only neighborhood step is a one-pixel growth, and the two-pixel halo covers it. `test_block_halo_preserves_existing_classes` checks a polygon with a hole that leaves the grid, at 10, 20, and 60 m.
- Every lazy graph holds one item on its native grid, through the stage 4 guard `load_native_item`, one graph per band. My stage 4 finding 1 stays satisfied.
- Completeness is checked both ways, block records and lake contributions, with empty lakes counted. Positions, classes, and raw values carry zero tolerance. One complete configuration cannot certify itself.
- The accounting separates requested bytes from delivered bytes and counts repeated exact ranges, retries, and timeouts. Code, plan, selection, and expected-output digests freeze before any pixel read.
- Allocation admission runs before every large array, and the supervisor polls the process group every 0.1 s. Cleanup deletes only a directory it marked, refuses symlinks, and audits what remains. A recovery sweep handles a dead supervisor.
- Distinct datastrips survive, catalog footprints do not filter membership, and ambiguous primary roles stay unresolved, as the accepted Stage 4 response requires.
- The gate passes on my machine: 238 tests, lint, format, the four `--check` tools, and `git diff --check`. The runner prints its plan offline.

## Findings

### 1. High: stop after the preflight, and read imagery in a second, separately invoked step

`execute()` runs boundaries, catalog, freeze, and prepare for both cohorts and writes `preflight.json`. It then continues into the fourteen extractions without a pause, [lazy_reader_workloads.py](../../benchmarks/lazy_reader_workloads.py) lines 482 to 550.
Stage 4 separated `--select`, which freezes metadata and prints a transfer estimate, from `--run-plan`, which reads imagery. [CLAUDE.md](../../CLAUDE.md) documents that separation as the practice.
The accepted response also fixed how a preflight estimates transfer: scale observed windowed bytes by membership count, per reader and per work organization.
The new preflight estimates only the two whole-image passes from finding 20 and leaves the ten windowed configurations unestimated, lines 413 to 439.

The owner set no transfer ceiling, but the owner has not seen the number. Planning arithmetic from findings 16, 19, and 20, not a measurement:

| Part of the run | Basis | Estimate |
|---|---|---|
| Dispersed, C-raster and C-lazy | 100 lakes give 100 to 140 products. Eight full tiles cost 327 to 410 MB and 32 to 38 s each | 65 to 115 GB, 2 to 3 hours |
| Dispersed, A and B, five configurations | 2.5 to 4.4 MB per small lake, the control 1.6 to 7 times more | 2 to 5 GB |
| Florida, C-raster and C-lazy | 4 to 8 products | 3 to 7 GB |
| Florida, A-raster and A-lazy | 1,000 lakes at 15 requests and about 2 s each | 5 to 9 GB, 30,000 requests, about an hour |
| Florida, B, three configurations | Each block once per product, the control more | 2 to 8 GB |

Change: make `--execute` stop after the preflight and print the totals. Add `--extract RUN_DIR` for the fourteen configurations and the validation, on the frozen digests the code already checks.
Estimate every configuration, using the accepted stage 4 method for the windowed ones and finding 20 for the whole-image ones. The owner then authorizes the reads with the real product counts in hand.

### 2. Medium: make the run resumable by phase, without re-attempting a configuration

`execute()` refuses an existing directory, and `run_phase()` refuses an existing spec, lines 447 and 485. The selections database lives in the temporary workspace and is deleted at the end, lines 456 and 545.
A laptop sleep, a dropped connection, a Ctrl-C, or a memory stop in the tenth configuration therefore means a new directory. That means a second round of USGS and Earth Search requests and a second preparation.
When available memory dips under 5 GiB between configurations, `supervise()` returns `not_started` for every remaining one within seconds, [workload_resources.py](../../src/s2proto/workload_resources.py) lines 148 to 154. The directory is then spent.

Change: keep `<cohort>-selections.sqlite` in the run directory. It holds compressed pixel positions, no imagery. On a second invocation, skip phases whose result exists and run the configurations that have no spec.
A configuration that never spawned is not an attempt. One that spawned is never rerun, which keeps the plan's rule of one timed attempt.

### 3. Medium: the memory floor is hard to meet on this laptop, and a miss is final

The laptop has 16 GiB. When I ran the check, psutil reported 3.19 GiB available, near the 3.36 GiB Codex saw. On macOS that number is free plus inactive pages, and it moves with every application.
The start check needs 5 GiB. Admitting one whole 10 m band needs 3.8 GiB available at that moment, `admit()` lines 38 to 47. The dispersed cohort makes about 500 such admissions.
Any 0.1 s poll under 3 GiB stops the worker, lines 112 to 117 and 204 to 208, and the plan forbids a retry. One browser tab opened during hour four ends a configuration for good.

The floor protects the laptop from other applications, not from the benchmark, which the 4 GiB aggregate RSS limit already bounds. The plan calls a limits change a matter for review. This is that review.
Change, for the owner to choose. Keep the 5 GiB start check and the 4 GiB RSS stop, and lower the in-run floor to 1 GiB. Or keep 3 GiB and run on a laptop with nothing else open.
Either way, record the choice in the plan before execution.

### 4. Medium: Florida needs one datatake over all 1,000 lakes, or the run fails after the fetches

`freeze()` intersects the eligible datatakes of every lake in a local group and raises when the intersection is empty, lines 187 to 203. Florida is one group of 1,000 lakes.
A datatake is one orbit pass, about 290 km wide. Adjacent passes are about 250 km apart at 28° N, so a swath edge crosses a 60 km cluster in roughly one case in four.
Lakes on both sides of such an edge have no common datatake, and the run ends after the boundary and catalog fetches with nothing frozen.

Change: when no datatake covers the whole group, take the eligible datatake that covers the most lakes, then repeat on the remainder. Each lake keeps one acquisition, each product holds members from one datatake, and the split is recorded.
Sharing in workflows B and C then holds within each product, which is what the comparison measures.

### 5. Medium, owner decision: the dispersed whole-image passes are most of the bill

By the table above, C-raster and C-lazy on the dispersed cohort move 65 to 115 GB of an 80 to 140 GB run. That serves one lake per product.
Finding 20 already measured whole-tile reads at 6 to 32 times the windowed bytes with three to six lakes per tile. At one lake per product the ratio is larger, and the direction is not in doubt.
What those two passes add is the whole-image lazy reader against the whole-image raster reader, the omission the plan fixes in the presentation. Florida's four to eight products measure the same pair at about one twentieth of the transfer.

The owner authorized fourteen passes and set no ceiling, so this is a choice, not a defect. With finding 1 in place, the owner decides at the gate with the real product count.

### 6. Low: workflow B's raster reader shares through the block cache, in file-then-lake order

`raster_asset()` reads each lake's blocks in turn, [workload_readers.py](../../benchmarks/workload_readers.py) lines 383 to 410. GDAL's 256 MiB cache serves a block the previous lake loaded. The improved lazy reader instead visits each distinct block once, lines 440 to 464.
A 10 m band has 121 blocks of 2 MiB, 242 MiB, against a 256 MiB cache. If the Florida lakes touch most of a band, the cache can evict, and B-raster then re-requests ranges B-lazy never repeats.
The limitations list already says so, and `repeated_exact_ranges` will show it. No change is required. Read that counter before comparing the two readers in B.

### 7. Low: the stratum-wide identifier queries are unbounded, and a failure ends the run

`candidate_ids()` asks for every object id in a 7.25 by 6.2 degree box per area band, [build_workload_manifests.py](../../tools/build_workload_manifests.py) lines 107 to 120. The saved pilot responses show 0.2 to 0.7 matching water bodies per square kilometer.
A stratum box of about 440,000 km² therefore holds 90,000 to 300,000 ids in the small band. The request has a 90 s timeout, three attempts, and raises on `exceededTransferLimit`. The client sends requests without a pause. Stage 4 paced its client at 0.2 s.

Change: ask `returnCountOnly` first and record the count. Subdivide a stratum whose count is large before asking for ids. Record a stratum that fails as a shortage and continue, as the selector already does for empty bands. Pace the requests.

### 8. Low: state the expectations before the run

The plan lists four questions but no expected answers, the point of my stage 4 finding 4. From findings 19, 20, and 21:

- B-lazy requests about the bytes of B-raster, since each block is read once. It makes more requests, because the loader opens the file once per chunk. The control requests 1.6 to 7 times the bytes.
- A in one process, reopening files per lake, sits between stage 2's one process per lake and B, as finding 19's loop-order row measured.
- Dispersed C reads 6 to 32 times the windowed bytes or more, and Florida C is the case where the ratio can fall.

A result that contradicts one of these lines is the informative one. Write them into the plan so the record can say which held.

### 9. Low: smaller items

- `finalize_cohort()` labels a configuration `incorrect` when its values differ from the first complete configuration in list order, lines 386 to 387. A disagreement does not say which side is wrong. Label it `differs`, and note that the page prints statuses verbatim.
- `finish()` commits after every lake and band, `workload_readers.py` line 381. SQLite syncs each commit inside `extraction_seconds`, about 5,000 times in a Florida A configuration and a few times in B. Set `synchronous=NORMAL` on the output database, and show read plus extract seconds beside the total.
- `native_array()` checks the geobox but not the chunk grid, lines 285 to 297. A chunk grid that differs from the block grid fails only at value comparison, after the transfer. Assert `graph.chunks` against the block shape before the first read.
- [CLAUDE.md](../../CLAUDE.md) does not list the runner or the selector. Add the offline plan command to Commands, and add `lazy_reader_workloads.py --execute` and `build_workload_manifests.py` to the paragraph on scripts that contact providers. The work plan and the root README do not mention this step.

## Verification

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. 56 packages checked, no lint finding, 103 files formatted |
| `uv run pytest -q` | 238 passed in 16.85 seconds, existing library deprecation warnings only. Sixteen are the new runner tests |
| The four `--check` tools and `git diff --check` | Inventory, sensor band dataset, page, and gap report match their inputs. No whitespace error |
| `uv run python benchmarks/lazy_reader_workloads.py` | Prints the plan and limits without network access |
| Memory at review time | 16 GiB total, 3.19 GiB available by psutil |

I did not run Codex's browser check, which lives outside the repository. I did not contact a provider, so the stratum counts, the Florida datatake question, and the product counts remain estimates.

## Next step

Codex applies findings 1, 2, 4, and 7, revises the plan and record, and states the expectations of finding 8. The owner decides findings 3 and 5 and records the choice.
Then the owner invokes the freeze, reads the preflight, and authorizes the imagery reads as a separate invocation. Nothing here is committed.
