# Stage 4 smoke test, 2026-09-16

Follow-up, 2026-09-17: The owner accepted the Stage 4 response. Current status and documentation dispositions are in the [presentation update](2026-09-17-documentation-and-presentation.md).

Author: Codex. Status: passed, subsequently reviewed in the [full-run review](2026-09-16-claude-stage-4-full-run-review.md).
The owner authorized this smoke after the [implementation](2026-09-16-stage-4-implementation.md).
At this step, the full Stage 4 experiment had not run.
The owner subsequently authorized the [full workload](2026-09-16-stage-4-full-run.md), which completed.

## Result

The [smoke result](../../benchmarks/results/cross-tile-extraction-smoke.json) records one public pilot pond, four tiles, five bands, two readers, and two work organizations.
It uses one repetition and one datatake. All measured numbers below come from that result and its saved logs.

All ten extraction workers completed.
Each reader/path combination produced its twenty expected contributions, giving eighty records across the run.
Values, native pixel identities, classes, counts, windows, and polygon digests matched for every corresponding contribution.
No contribution was missing, empty, failed, or marked no-data.
Different tiles remained separate throughout extraction and assembly.

| Work organization | Reader | Workers | Wall seconds | Requests | Requested MB | Peak worker MiB |
|---|---|---:|---:|---:|---:|---:|
| Lake first | Raster mask | 1 | 12.27 | 60 | 14.20 | 104.9 |
| Lake first | Lazy stack | 1 | 10.95 | 60 | 14.20 | 176.9 |
| Tile first | Raster mask | 4 | 11.17 | 60 | 14.20 | 94.9 |
| Tile first | Lazy stack | 4 | 34.28 | 88 | 84.58 | 209.1 |

Sources: `summary.workloads`, particularly `end_to_end_seconds`, `totals`, and `peak_worker_rss_bytes`.
MB means decimal megabytes. MiB means binary mebibytes.
Wall time sums the parent-observed worker durations, including process startup. It excludes catalog selection and mask preparation.
These are single observations, without an estimate of variability.

The imagery logs account for 268 requests and 127,199,416 requested bytes in total.
These counts exclude catalog traffic. Requested bytes are not an independently metered network transfer.
No timeout, retry warning, or repeated identical range request appeared in the imagery logs.

## Inputs and coverage

The case is pilot pond `nhd-34972105` in the Lanier region.
Catalog selection chose `GS2B_20251015T162149_044968_N05.11` from the existing date window.
The chosen tiles are 16SGC, 16SGD, 17SKT, and 17SKU, spanning UTM zones 16 and 17.
Every tile and product footprint covers the complete buffered support within the declared tolerance.
The tile and footprint unions leave no uncovered support in this case.

The previously proposed smoke anticipated two tiles from Stage 3's selections.
Enumerating all spatial candidates found four tiles for the chosen datatake. Both readers used all four.
Native pixel counts differ between the UTM grids. Equality compares corresponding contributions across readers and paths, never different tiles against each other.
Primary roles remain unresolved, as specified in the implementation record.

The plan's whole-file transfer proxy was 7.08 GB. It was not a prediction of these windowed reads.
Actual requested imagery bytes are recorded above. This smoke supplies an observed small-polygon case for subsequent planning.

## Memory and preparation

Peak reported extraction-worker memory was 209.1 MiB. The largest sampled resident-memory value was 207.5 MiB.
The memory guard stopped no worker. No extraction worker reached the configured page-out flag threshold.
Host page-out deltas were nonzero, reaching 1.86 MiB in one worker interval. They can include unrelated processes.
The smallest recorded available host memory after an extraction worker was approximately 2.69 GiB.
Every extraction worker reported the configured 512 MiB GDAL cache.
The [implementation record](2026-09-16-stage-4-implementation.md#resource-and-geometry-limits) owns the guard settings and sampling limits.

Two tiles reused Stage 3 masks after input and file-hash checks. Two tiles required new masks.
Reused preparation records retain their original measurements. Their old preparation timings are not new Stage 4 work.
This tiny polygon does not establish that the full anchors will fit comfortably in memory.

## Interpretation and limits

The smoke verifies provider access, separate native grids, logical assembly, complete accounting, and agreement between the readers for this case.
Tile-first lazy reading requested 5.95 times the bytes of each other combination.
Its full native-grid chunk layout differs from the lake-first window-aligned graphs. The detailed file and chunk records remain available for review.
No repeated identical request explains that increase in this run.

This is a smoke result, not a workflow recommendation.
One pond cannot reveal sharing benefits among neighboring lakes. One repetition cannot establish stable timing differences.
Complete overlap does not exercise an anchor whose coverage requires a union of partial tiles.
Large-mask memory, the full workload, and scientific agreement between different tiles remain untested in Stage 4.
The presentation and assessment findings remain unchanged.

## Evidence and verification

Commands executed:

```sh
uv run python benchmarks/cross_tile_extraction.py --select \
  --regions lanier --lakes nhd-34972105 --repeat 1 \
  --plan data/cross-tile-extraction/smoke-plan.json

uv run python benchmarks/cross_tile_extraction.py \
  --run-plan data/cross-tile-extraction/smoke-plan.json \
  --reuse-masks data/tile-extraction/2026-09-16T122955+0000 \
  --output benchmarks/results/cross-tile-extraction-smoke.json
```

The result embeds the frozen plan, source hashes, selected products, machine details, preparation records, and every worker result.
Raw specifications, per-tile results, and GDAL logs remain under `data/cross-tile-extraction/2026-09-16T171341+0000/`.
An offline audit independently checked expected keys, duplicate absence, contribution signatures, native-grid assertions, effective cache sizes, and guard records.
It also recomputed imagery requests and requested bytes directly from every saved GDAL log. Each tile total matched its result.

Result SHA-256: `8140e3ddaa3c31212ca63f51293dbb721c9a4ad387b43e6b12c7320c5499f4dc`.

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed.
Dependency synchronization, lint, and formatting checks passed.
`uv run pytest -q`: 188 passed in 10.04 seconds, with library deprecation warnings.
`git diff --check`: passed.
The frozen input hashes and result digest remained unchanged after verification.

## Next step at this record’s completion

Claude Code reviews the smoke evidence and implementation.
After that review, the owner can authorize selection and execution of the full Stage 4 workload.
No full-workload provider request was made during this smoke.
