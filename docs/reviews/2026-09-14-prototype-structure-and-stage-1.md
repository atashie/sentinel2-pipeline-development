# Prototype structure, measurement harness, and stage 1 raw access, 2026-09-14

Author: Claude Code (AI coding agent), directed by the repository owner.

## Context

Codex's [pilot manifest review](2026-09-12-pilot-manifest-review.md) sits in the working tree, uncommitted, with its corrections and the partial Prototyping tab. The checks passed with those changes before this work began.
On 2026-09-14 the owner reset the purpose and structure of prototyping. Four workload stages come first. The scientific and quality checks come after them.

## The owner's structure

1. Raw access. Read a tile from each product. Time the band sets per resolution from 10 m upward, then all bands together. Record time, peak memory, and CPU.
2. One lake at a time. For each pilot size class, compare naive clipping, a preprocessed rasterized lake, and preidentified row, column, and resolution indices.
3. Many lakes in one tile. Compare loading lakes one at a time against loading every lake of a tile before moving on.
4. Lakes across two or more tiles. Compare per-lake extraction from every relevant tile against per-tile extraction followed by recombination.

The owner answered four questions the same day:

| Question | Answer |
|---|---|
| Where do timings run | On the owner's laptop only, as smoke tests, until AWS access exists. Recorded as an open item, assumption A25 |
| Which copies in stage 1 | Both GeoTIFF copies. The JPEG 2000 original stays out |
| Which methods in stage 2 | All four: naive clip, precomputed raster mask, precomputed index lists, lazy array stack |
| Delivery | One authorized step per stage. The first step is the harness plus stage 1 |

## How the structure maps to the Discovery candidates

The owner's stage 2 list names the geometry-preparation axis. Our candidates add a read-pattern axis, which stages 3 and 4 exercise.

- Naive clip per scene reprojects the polygon and clips per observation. It yields a binary mask without coverage fractions. It is the baseline.
- The precomputed raster mask is the reference design, assumption A9 and practice P1. Index lists are the same precomputation stored as rows and columns.
- The inventory's read patterns are windowed range reads per lake, one shared whole-tile read, and a lazy array stack. The owner added the lazy array stack to stage 2.
- Stage 4 recombination means concatenating records that keep their tile id and role. The store never mosaics, issue I-30. No value is blended across tiles.
- Per-tile datacubes and per-lake chip archives are storage-side variants for later stages. Provider-side extraction remains context only.

## What changed

- `pyproject.toml`: a `prototype` dependency group, installed by default, with rasterio 1.5.1 on GDAL 3.12.4, numpy 2.5.3, shapely 2.1.2, pyproj 3.8.0, and psutil 7.2.2. `uv sync --locked` covers it in CI.
- [src/s2proto/harness.py](../../src/s2proto/harness.py), new. Wall and CPU time, peak resident memory, machine and library versions, machine-wide network counters, a parser for GDAL's range-request log, and a logging HTTP client.
- [benchmarks/raw_access.py](../../benchmarks/raw_access.py), new. Stage 1. Finds one acquisition on both collections, pairs the items by ESA product URI, and reads every band as a whole tile.
- [tests/test_harness.py](../../tests/test_harness.py) and [tests/test_raw_access.py](../../tests/test_raw_access.py), new. Fourteen tests on synthetic GeoTIFFs and fixtures. No network.
- [work-plan.md](../work-plan.md): Phase 2 rewritten as the five stages with their checkboxes. [assumptions.md](../assumptions.md): A25. [benchmarks/README.md](../../benchmarks/README.md), [CLAUDE.md](../../CLAUDE.md), and the reviews index updated.

## Stage 1 design

- Acquisition: tile 17SKU on 2025-10-15 by default, the pair probe PR-08 compared. Both copies hold the same ESA product for it. `--tile` and `--date` choose another.
- Band groups: the four 10 m bands, the six 20 m bands, the two 60 m bands, the quality layers, and all of them. Quality layers missing from a copy are recorded, not guessed.
- Read modes: `vsicurl`, where GDAL reads the object in ranges, and `whole-object`, one HTTP GET followed by a decode from memory.
- Every copy, group, mode, and repetition runs in a fresh worker process. GDAL's caches start cold each time. Three repetitions by default.
- Per band: open, read, fetch, and decode seconds, requests, bytes requested, and the file's block shape, compression, and overviews. Also a SHA-256 digest of the decoded array with its minimum, maximum, and no-data count.
- Per run: wall seconds, CPU seconds, the worker's peak resident memory while holding every array of the group, and the network counter delta.
- The summary gives medians per copy, group, and mode, and whether both copies decoded to identical bytes per band. That answers pixel equality without a second download.
- The result records both buckets, the region, the unsigned payer status, and the `x-amz-request-charged` header of every whole-object read.

Run commands, for the owner:

```sh
uv run python benchmarks/raw_access.py --dry-run
uv run python benchmarks/raw_access.py --groups 60m --repeat 1
uv run python benchmarks/raw_access.py
```

The smoke run reads two small bands from each copy in each mode. The full run reads every band of the acquisition six times per copy. That is several gigabytes over the laptop's connection.

## Limits before the runs, historical design notes

- Every timing includes the internet path from the laptop to us-west-2. Assumption A25 records the repeat from an instance in the region.
- In `vsicurl` mode, requests and bytes come from GDAL's debug log of requested ranges. The log line format was confirmed on local reads. The range format comes from GDAL's source and has not yet been observed on a live read here.
- Network counters are machine-wide. Other traffic on the laptop lands in them.
- Peak memory is the worker's maximum resident set. In `whole-object` mode the compressed object and the decoded array are held together.
- Nothing has been read from a provider in this step. No number here is a measurement.

## Dispositions of prior findings

Codex's seven findings of 2026-09-12 were fixed, corrected, or deferred by Codex. I reviewed the diffs and reopen none.

- Digest checks in the builder, the area-equivalent width wording, and the source qualifications: fixed by Codex, accepted.
- `--manifest` finds candidate tiles from unbuffered boxes: accepted and deferred. Stage 4 needs polygon and buffer coverage, which its record must establish.
- Report adaptation before a pilot report: accepted and deferred, carried on the work plan.
- `polygon_version` on refetch: accepted and deferred. No refetch is planned.
- Fill policy, Alaska scope, quality layers, model input product, and record layout: open, unchanged.

## Verification

- `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`: passed.
- `uv run pytest -q`: 109 passed after the runs and the review corrections.
- `collate_checks.py --check`, `render_options.py --check`, `gap_report.py --check`: current after re-rendering the page.
- `uv run python benchmarks/raw_access.py --dry-run`: prints 60 planned runs and contacts nothing.

## The runs, later on 2026-09-14

The owner authorized the runs with "run and monitor phase 2". Everything ran on the laptop.

1. Smoke run at 18:21 UTC, 60 m set, one repetition: four runs, none failed. It showed the range-request parser working and the two copies decoding to different bytes.
2. Full run from 18:21 to 18:58 UTC: 60 runs, 12 failed. Every failure was the older copy's `cloud` asset, a JPEG 2000 link into the `sentinel-s2-l2a` bucket that a GeoTIFF reader cannot open. The script now skips such assets with a recorded reason and saves each run's result as it completes.
3. Older-copy rerun of the quality and all-band groups: the session's memory watchdog killed it after 9 of 12 runs while a browser held 2.4 GB. A `--reuse` option was added, and the last three runs completed in the foreground at 19:06 UTC. 12 runs, none failed.
4. Pixel comparison of six files, twelve objects, at 19:10 UTC. Its saved requested ranges total 335,020,511 bytes.
5. The same comparison again at 19:56 UTC, invoked by the owner after the review, with the rule check and grid guards in the script. It replaced the 19:10 file with identical difference counts. The rule check also runs on the classification, where it reports every identical pixel as a violation. That is a script limitation to fix before stage 5.

Findings 13 to 15 in [measurements.md](../measurements.md) hold the numbers. In short: whole-object reads beat range reads for the larger sets on this connection. The older copy needs about three times the range requests for its 10 m bands. Its cloud and snow layers are not GeoTIFFs, and its aerosol and water-vapor grids differ. Its reflectance values sit at or below Collection 1's with a dominant difference of exactly 1,000. That is consistent with the provider's offset-and-clamp conversion, while the catalog still declares the offset.
The Prototyping tab gained a stage 1 chapter with both tables, filled by the renderer from the three result files.

Limits added by the runs: requested bytes come from GDAL's log and whole-object content lengths. The machine-wide network counter is recorded separately and includes other traffic. Its ratio to requested bytes had a median of 1.05, and on one run it recorded about 9 percent of the requested bytes. Three runs exceeded 1.5 times their set's median. The comparison covered three reflectance bands, the classification, and one product.

## Dispositions of Codex's stage 1 review, 2026-09-14

[Codex's review](2026-09-14-codex-stage-1-review.md) raised seven findings. All seven are accepted.

1. Exact clamp rule presented as measured. **Corrected with evidence, then measured.** The wording was first reduced to "consistent with offset application and clamping". The comparator gained a per-pixel check of `older = max(c1 − 1000, 1)` and a count of pixels at or below the offset. The two fixtures from the review are its tests. The owner then invoked the comparison again at 19:56 UTC. It reproduced the first run's difference counts and found zero violations on 99,802,042 valid pixels across the three bands. Finding 15, the page, F-23, I-05, and the gotcha now state the rule as measured for this product, with other bands, items, and baselines open.
2. Reuse could accept another tile, date, or asset set. **Fixed.** Reuse now requires the same copy, group, mode, repetition, asset keys and hrefs, and reader configuration, and reports why it declines. Fixtures reject a changed href, a shorter band set, a changed configuration, and a failed saved run. The saved rerun was checked by Codex and matched its assets.
3. Failed JP2 access presented as a credential requirement. **Corrected with evidence.** The failures were an unconfigured S3 path and an unsupported URL scheme. The page, finding 14, and the skip reason now say the files are outside this GeoTIFF benchmark and that unsigned access is untested. The saved rerun's skip reason keeps the old wording, since result files are never edited.
4. Network-counter agreement overstated. **Corrected with evidence.** The 46 of 48 claim is withdrawn. Requested bytes and the machine-wide counter stay separately labeled, with the median ratio and the one low reading recorded. The docstring now says machine-wide.
5. Comparator lacked product and grid guards. **Fixed.** The comparator refuses different products unless told otherwise, and compares width, height, CRS, and transform before subtracting. A grid mismatch is recorded, not compared. Fixtures cover a shifted grid with the same shape and the product guard.
6. Measurement scope. **Fixed.** The tables now show the per-file read and decode timers, without digest and statistics. The peak memory column says it is the highest of both copies and modes and includes start-up and a digest copy. The digest no longer copies the array. Whole-object requests count HTTP attempts. The request-count explanation is presented as consistent with the timings, not as the cause, with the 60 m and quality exceptions named.
7. Status prose and numbers. **Fixed.** Leads updated on the README, the work plan, and the Prototyping tab. The comparison volume is 335,020,511 requested bytes. Pre-run limits are labeled historical. Outliers use a declared criterion, 1.5 times the set's median, which names three runs. "Same bytes" became "similar volume". Sub-10-second medians keep one decimal. F-23 carries evidence file paths.

## Proposed next step, not started

1. Stage 2 statement: the four methods on the pilot lakes, one tile-date per region, with tolerances declared before comparison. Stage 2 reads Collection 1 for value checks. On the older copy the offset is already applied, so its catalog declaration is not applied again.
2. Commit on the owner's authorization.
