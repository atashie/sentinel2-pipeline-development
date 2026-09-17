# Stage 4 full run, 2026-09-16

Follow-up, 2026-09-17: The owner accepted the Stage 4 response. Current status and documentation dispositions are in the [presentation update](2026-09-17-documentation-and-presentation.md).

Author: Codex. Status: completed and [reviewed by Claude Code](2026-09-16-claude-stage-4-full-run-review.md).
The [response](2026-09-16-codex-stage-4-review-response.md) applies corrections for future selection and qualifies the interpretation.
This executes the [revised plan](2026-09-16-stage-4-plan.md) after the [smoke](2026-09-16-stage-4-smoke.md).
Claude Code reviews the resulting evidence before presentation updates or another workload.

## Preflight correction

The initial catalog selection stopped before imagery reads because Okeechobee's geometry check did not converge.
Its error bound accumulated changes across every alternative catalog item, although the version 2 selector retained only one item per tile.
Adding alternative revisions could therefore fail the bound without changing any selected geometry.

The measured version 2 used the largest candidate footprint change per tile, then summed those tile bounds.
It retains polygon, support, and tile-extent terms, including support changes when clipping either geometry family.
The reporting tolerance and stricter convergence threshold remain unchanged.
The buffer approximation, membership rule, selection ranking, and extraction readers also remain unchanged.
The plan records the bound's scope. The measured script version is 2.
The criterion bounds successive refinements, rather than error against exact geometry. Version 3 handles multiple datastrips, as described in the response.

A regression test repeats one candidate footprint across alternative revisions and requires identical geometry refinement and coverage.
Its nonzero bound also checks a changing geometry, rather than relying on identical successive segmentations.
`uv run pytest -q tests/test_cross_tile_extraction.py`: 18 passed in 9.50 seconds.

The failed selection and guarded diagnostic remain under `data/cross-tile-extraction/selection-2026-09-16T175840+0000/`.
The corrected selection reused that directory's catalog JSON without another provider query.
Its raw selection records remain under `data/cross-tile-extraction/selection-2026-09-16T203355+0000/`.
The historical smoke result retains its original source hashes and script version.

## Execution and evidence

Commands executed:

```sh
uv run python benchmarks/cross_tile_extraction.py --select \
  --plan data/cross-tile-extraction/full-plan.json

uv run python benchmarks/cross_tile_extraction.py \
  --catalog data/cross-tile-extraction/selection-2026-09-16T175840+0000/catalog.json \
  --plan data/cross-tile-extraction/full-plan.json

uv run python benchmarks/cross_tile_extraction.py \
  --run-plan data/cross-tile-extraction/full-plan.json \
  --reuse-masks data/tile-extraction/2026-09-16T122955+0000 \
  --output benchmarks/results/cross-tile-extraction.json
```

The first command failed during selection. The second produced the frozen plan after the correction above.
Source hashes were verified before the third command started.
Raw extraction evidence remains under `data/cross-tile-extraction/2026-09-16T204751+0000/`.

## Results and verification

The [result](../../benchmarks/results/cross-tile-extraction.json) is complete and its corresponding contributions agree.
[Measurement findings 23 to 25](../measurements.md#prototype-stage-4-lakes-across-tiles-2026-09-16) own the workload counts, coverage, no-data counts, timing, requests, and per-tile costs.
Claude Code verified the extraction evidence. Interpretation corrections are recorded in the linked response.
The owner subsequently accepted that response. The follow-up above records the inventory and presentation update.

The extraction logs account for 5,338 requests and 4,530,493,346 requested bytes across the full experiment.
These totals exclude catalog traffic. Requested bytes are not independently metered delivered bytes.
The original metadata query made ten requests and received 10,798,705 bytes, recorded in `catalog-requests.json` beside the saved catalog.
The complete run took 1,158.11 seconds including preparation, excluding catalog selection.

An offline audit separately recomputed the expected worker set, contribution keys, duplicate absence, and contribution equality.
It checked native-grid assertions, polygon identity, cache values, memory flags, workload totals, and medians.
It also recomputed requests and requested bytes from all 198 saved GDAL logs. Every tile total matched its result.
No worker, contribution, or equality problem was found.
Claude Code also verified exact reproduction of the smoke pond in the full run.
All twenty matching contribution keys have identical windows, counts, values, and pixel digests in each smoke reader/path combination.
The response's saved audit repeats this check from JSON, without reading pixels.
The audit is Codex's verification, not Claude Code's independent review.
Its script and output are `independent-audit.py` and `independent-audit.json` inside the raw extraction directory.
`log-detail-audit.json` records the additional raw checks of repeated ranges, observed opens, and timeout or HTTP error messages.

Result SHA-256: `fddea828f0a9516b999c40e879e46c8998e2ed4a8b8dfe16de01d571db4495e8`.

### Resource use

Sixteen preparations reused masks after hash and input checks. Nine computed new masks.
Preparation took 47.78 seconds including reuse checks and worker startup.
Reused records retain their earlier timings, which are not new Stage 4 measurements.

| Phase | Peak resident memory | Measurement |
|---|---:|---|
| Corrected catalog selection | 3.40 GiB | Maximum sampled worker RSS. Host swap-in increased 1.03 GiB during Lanier selection |
| New mask preparation | 791.7 MiB | Maximum worker-reported peak |
| Extraction | 1.80 GiB | Maximum reported peak, also reached by the sampler |

Sources: `plan.selection.*.host_memory`, including `swap_in_delta`, new `preparation.*.result` entries, and `runs[].host_memory` with `peak_rss_bytes`.
The guard stopped no worker in the corrected selection, preparation, or extraction.
Their maximum host page-out deltas were 37.33 MiB, 0.80 MiB, and 1.73 MiB respectively.
None reached the configured 128 MiB flag threshold. Host counters can include unrelated processes.
The smallest available host memory recorded after an extraction worker was 2.71 GiB.
Every extraction worker reported the intended 512 MiB GDAL cache.
The [implementation record](2026-09-16-stage-4-implementation.md#resource-and-geometry-limits) owns sampling, budget, reserve, cache, and lazy-reader settings.

Selection remains the largest observed memory demand. This run fits the guarded laptop workload, without establishing safety for larger polygon sets or parallel workers.

### Repository checks

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed in order.
`uv sync --locked`, `uv run ruff check .`, and `uv run ruff format --check .` passed.
`uv run pytest -q`: 190 passed in 11.82 seconds, with library deprecation warnings.
`git diff --check`: passed.
The frozen source hashes matched at run verification. The subsequent response changes the script, while preserving the result and historical smoke digests.

## Next step at this record’s completion

Review the [response](2026-09-16-codex-stage-4-review-response.md) before the inventory and presentation updates.
Primary roles remain unresolved for ambiguous cases. Passing extraction checks does not establish full contract compliance.
Stage 5 requires separate owner authorization.
