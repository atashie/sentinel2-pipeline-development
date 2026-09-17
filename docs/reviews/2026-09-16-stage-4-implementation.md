# Stage 4 implementation, 2026-09-16

Follow-up, 2026-09-17: The owner accepted the Stage 4 response. Current status and documentation dispositions are in the [presentation update](2026-09-17-documentation-and-presentation.md).

Author: Codex. Status at this step: implemented for review, without a provider run.
Subsequent work: the owner authorized the [smoke test](2026-09-16-stage-4-smoke.md), which passed.
The owner then authorized the [full run](2026-09-16-stage-4-full-run.md), which completed with a documented geometry-bound correction.
The [full-run response](2026-09-16-codex-stage-4-review-response.md) documents version 3 changes for future selection and execution.
The owner authorized implementation after the [revised plan](2026-09-16-stage-4-plan.md).
Claude Code reviews this step before the owner authorizes catalog selection and a bounded imagery smoke run.

## What changed

The [new entry point](../../benchmarks/cross_tile_extraction.py) compares lake-first and tile-first work using the existing Stage 3 readers.
Both paths preserve separate native grids, item identities, datatakes, pixel classes, and contribution digests.
The [fixture tests](../../tests/test_cross_tile_extraction.py) use synthetic local rasters. Their timings are not prototype measurements.

| Area | Implementation |
|---|---|
| Selection | Enumerate spatial candidates, group complete datatake identities, rank usable revisions, and retain unavailable tiles and excluded groups |
| Frozen inputs | Save raw metadata, source hashes, polygons, native grids, memberships, acquisition identities, expected keys, and worker order |
| Geometry | Densify before projection, refine boundary differences within each lake's support, and record convergence and round-trip checks |
| Native readers | Reject merged items, shifted windows, changed resolutions, and changed CRSs before creating a lazy graph |
| Worker units | One process visits a lake's tiles sequentially, or one process extracts a tile's lakes |
| Assembly | Sort contribution keys and compare values, native pixel identities, counts, windows, and polygon digests |
| Completeness | Retain expected keys after failures, including empty selections, missing records, and failed reads |
| Memory | Apply the shared guard to selection, preparation, and extraction workers. Record each outer process independently |
| Reuse | Verify saved mask hashes, polygon hashes, grids, resolutions, parameters, and mask algorithm versions |
| Evidence | Save specifications, per-tile logs, per-worker results, preparation records, and the combined result incrementally |

The shared reader gains a native-grid check and an optional subprocess entry point.
Its implementation version advances because worker validation changed. Existing measurement files remain untouched.
No new reader, pixel-fragment store, production contract, inventory finding, or presentation result is added.

## Dispositions of the plan review

The [plan review](2026-09-16-claude-stage-4-plan-review.md) retains the original findings.
The revised plan records the reasoning behind accepted and deferred suggestions.

| Finding | Disposition |
|---|---|
| 1. Lazy mosaics | Fixed. A fixture rejects merged inputs before loading. Separate UTM grids produce separate graphs |
| 2. Fragment store | Fixed. Assembly uses keys and digests. Output size retains the existing logical byte model |
| 3. Primary labels | Accepted and deferred where ambiguous. Record the proposed largest-share winner separately. Assign roles only for one unambiguous containing tile |
| 4. Hypothesis | Fixed. Preserve marginal bytes per lake, tile, and band beside union coverage and overlap diagnostics |
| 5. Two methods | Fixed. Raster mask and lazy stack run through both work organizations |
| 6. Geometry refinement | Fixed with an explicit buffer approximation limit, described below |
| 7. Group ranking | Fixed. Report every score, revision rejection, missing candidate tile, and coverage exclusion |
| 8. Reuse | Fixed. Both paths call Stage 3 extraction. Saved geometry requires compatible inputs and verified files |

## Resource and geometry limits

The guard retains a 4 GiB worker budget and a 1.5 GiB available-memory reserve.
It samples resident memory every 250 ms and flags host page-outs of at least 128 MiB.
The effective GDAL cache remains 512 MiB. Lazy graphs retain 2,048-pixel chunks and four threads.
These values are frozen in the plan. Every extraction worker records the effective cache and guard observations.
A sampler can miss a short memory spike between samples. Host page-outs can include unrelated processes.

An offline Lanier check exposed excessive work from an unnecessarily dense buffer approximation.
The guard stopped that selection worker above its budget. The implementation now uses Stage 3's 16 segments per quadrant.
The result records this approximation explicitly. Its convergence tolerance covers CRS boundary refinement, not ideal circular-buffer accuracy.
Native candidate membership uses distance to the tile extent. This retains marginal candidates despite differences between projected buffer approximations.
Existing pixel-center classification governs extraction. A geometric candidate can still produce an empty contribution.

Coverage and overlap use one metric reference CRS per lake.
The convergence check differences changing tile boundaries before clipping them to complex shorelines.
This avoids repeatedly overlaying nearly identical shoreline geometries.
A coordinate round trip supplies a separate displacement-based area-error bound.

Primary roles remain unresolved when A22 gives no unambiguous answer.
This benchmark cannot establish contract compliance for those roles until the owner resolves the rule.
Cross-tile scientific agreement and a physical storage format remain outside this experiment.

## Run interface

No arguments and `--dry-run` print the local workload without contacting a provider.
`--select` fetches catalog metadata and freezes a plan. It reads no imagery or raster headers.
`--catalog FILE` freezes the same plan from saved metadata, without network access.
`--run-plan FILE` reads imagery using exactly that plan. It performs no catalog query.
A changed source hash, altered plan, incomplete acquisition selection, or existing output prevents that run.
`--resummarize FILE` rebuilds accounting from saved JSON alone.

Selection prints the worker count and a transfer planning proxy before any pixel read.
The proxy counts compressed file sizes per membership, band, path, method, and repetition.
It is neither predicted window traffic nor a strict upper bound. Missing size metadata produces an unknown estimate.
Sharing can reduce traffic. Lazy re-reads and retries can exceed the proxy.
Review this estimate and the chosen memberships before invoking imagery extraction.

Proposed first smoke selection, after review and owner authorization:

```sh
uv run python benchmarks/cross_tile_extraction.py --select \
  --regions lanier --lakes nhd-34972105 --repeat 1 \
  --plan data/cross-tile-extraction/smoke-plan.json
```

This small pilot pond appeared in two tiles during Stage 3. Verify cross-tile membership in the new frozen selection.
The smoke keeps both readers and work organizations.
After reviewing the frozen plan, the corresponding imagery command is:

```sh
uv run python benchmarks/cross_tile_extraction.py \
  --run-plan data/cross-tile-extraction/smoke-plan.json \
  --reuse-masks data/tile-extraction/2026-09-16T122955+0000 \
  --output data/cross-tile-extraction/smoke-result.json
```

The complete experiment requires a separate default selection and plan.
Its worker count depends on the available datatakes and tiles. The planning estimate remains in the revised plan.
Do not infer authorization for the complete workload from a passing smoke run.

## Verification

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed:

- `uv sync --locked`: passed.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 187 passed in 9.31 seconds, with library deprecation warnings.
- `git diff --check`: passed.
- `uv run python benchmarks/cross_tile_extraction.py --dry-run`: eleven lakes, two readers, and two paths, without network access.

The fixtures exercise different datatakes, missing and redundant tiles, partial footprints, full overlaps, and three-way overlap area.
They also exercise empty native selections, two CRSs, shifted grids, failed inputs, duplicate contributions, changed masks, and memory stops.
A local CLI test saves a frozen plan, runs both paths, reuses compatible masks, and regenerates its summary.
Saved Stage 3 metadata also exercised both real pilot regions under the selection guard.
Those saved inputs were rejected as incomplete Stage 4 workloads, retaining the acquisition and uncovered-support reasons.
No provider endpoint was contacted. No satellite pixels were read.

## Next step at this record’s completion

Claude Code reviews this implementation and its limits.
Then the owner can authorize metadata selection and review the concrete smoke plan before imagery extraction.
Stage 4 has no measured provider results. The presentation and measurement findings remain unchanged.
