# Stage 3 pre-run review, 2026-09-15

Reviewer: Codex, with separate research and checking agents for Dask and odc-stac behavior.

The three-pattern design fits the intended stage. Correct the baseline comparator, completeness checks, lazy-reader accounting, and memory safeguards before the provider run.
The other findings below improve the experiment without adding another workflow or advancing stages 4 and 5.

Scope: the [stage 3 statement](2026-09-15-stage-3-many-lakes-in-one-tile.md), [script](../../benchmarks/tile_extraction.py), [fixtures](../../tests/test_tile_extraction.py), shared helpers, and updated documentation.
The reviewed tree starts from commit `535357c`, with Claude's stage 3 changes uncommitted.
No stage 3 provider read or new imagery download ran during this review.

## What is ready

- Separating pixel selection from read order makes the comparison understandable. The whole-tile pattern shares its decoded array across lakes.
- Tile selection normalizes grid codes and records placements, members, partial coverage, and lakes that cannot be placed.
- The prior shoreline-distance correction is present. Masks use the full mapped polygon boundary and carry a version.
- Reuse binds polygon and mask digests, grids, parameters, and implementation versions. Summary regeneration has a separate offline path.
- Value and coordinate digests are distinct. A naive selection containing no pixels receives a valid empty record.
- The existing 159 tests pass. Synthetic extraction agrees across patterns, with the expected distinction between naive and mask selections.
- No stage 3 results have been added to the presentation or measurements. The documentation correctly identifies this as preparation.

## Findings

### 1. High: the stage 2 comparator mixes incompatible selection methods

Location: [load_baseline](../../benchmarks/tile_extraction.py), lines 324 to 330, and `_equality`, lines 515 to 551.

`load_baseline` combines every method's wet-value digest under one lake, item, and band key.
Naive clipping and the mask methods deliberately select different wet pixels in some cases.
The comparison then requires the stage 3 mask digest set to equal that mixed set.

Using the committed [stage 2 result](../../benchmarks/results/lake-extraction.json), 121 baseline keys have one digest and 29 have two.
An unchanged stage 2 raster-mask result fails the proposed comparison for all 29 two-digest keys.
For example, Lake Tahoe's red band fails against its own saved values because the baseline also contains the naive digest.

The baseline fixture includes only raster-mask and index-lists. It never loads the naive records responsible for this defect.
The current `matches_stage_2` field also never compares the stage 3 naive method with its own stage 2 counterpart.

Disposition: open. Keep baseline digests separated by method, or compare mask methods against an explicit mask reference.
Test a complete baseline containing all four methods and a known naive-selection difference.
Record disagreements within the chosen baseline reference separately from disagreements with stage 3.

The timing baseline also needs a compatible band selection. `baseline_for` currently attaches five-file totals to runs requesting a different band set.
Mark those totals incomparable unless the bands match. Continue naming lakes and items without a usable baseline.

### 2. High: failed preparation or an entirely missing lake can produce a complete-looking result

Locations: [worker preparation handling](../../benchmarks/tile_extraction.py), lines 1464 to 1487, and `_equality`, lines 480 to 555.

When one member's preparation fails, the parent silently excludes that member from every extraction specification.
It continues if any other member prepared successfully.
Equality checks are constructed only from lake-band records that arrived, so the omitted member receives no missing-record check.

Offline reproduction used the existing four-lake fixture:

- The complete fixture produces 20 lake-band comparisons.
- Marking one preparation failed and excluding that lake produces 15 comparisons.
- All 12 runs remain `ok`, every remaining comparison is complete, and `equality_incomplete` is zero.

The same gap applies when a band is absent from every run. A returned-record list cannot define expected coverage.
Unplaced lakes are recorded in the selection log but likewise do not make the run summary incomplete.

There is another reporting defect in `_combo_rows` and `_lake_rows`.
Runs with band errors remain in timing medians, while displayed band-error counts come only from the first repetition.
An error in repetition two can therefore disappear from the comparison row and contribute an artificially short time.

Disposition: open. Derive expected members and bands from the selected scenes and requested plan before examining returned records.
Preserve failed preparation and missing assets as explicit incomplete work.
Exclude invalid runs from performance medians and aggregate errors across every repetition.
Add fixtures for a whole missing lake, a whole missing band, and an error after the first repetition.

### 3. High: lazy-reader opens and chunk counts describe different operations than their labels imply

Locations: [run_lazy](../../benchmarks/tile_extraction.py), lines 984 to 1058, and `_close_band`, lines 793 to 800.

The lazy path increments `opens` once per lake or sets it to one per file.
These are manual logical counters. They do not observe how often odc-stac opens the underlying raster.

I repeated the existing synthetic fixture with 128-pixel chunks, so its 240-pixel tile spans multiple chunks.
Instrumenting `rasterio.open` for the red file produced:

| Pattern | Reported opens | Observed raster opens |
|---|---|---|
| Lake-by-lake | 4 | 7 |
| Tile-by-tile | 1 | 7 |
| Whole-tile | 1 | 4 |

All runs completed without reported errors. This was entirely local, with no HTTP requests.
The installed odc-loader opens a raster during each executed chunk read. One graph or one compute does not imply one raster open.

The tile-by-tile lazy path also calls `.compute()` separately for each lake.
Reusing the graph does not retain previously decoded chunks between those calls under the default configuration.
GDAL may still reuse downloaded bytes. Repeated computation does not establish repeated network transfer.

Lake-by-lake chunk counts have a separate origin error.
Each lake's graph starts at its requested window, while the counter divides tile coordinates by the chunk size.
A local 21-by-20-pixel window at row 90, column 118 is one 128-pixel lake-local chunk, but the script reports two.
Two is appropriate for that window on the full-tile graph. The graphs use different origins.
Unions of tile-coordinate chunk cells also do not establish shared tasks between separate lake graphs.

Disposition: open. Count actual raster opens, or rename the logical operation counter and leave actual opens unknown.
Count chunks relative to each graph's geobox and distinguish spatial overlap from reused computation.
Describe the current lazy pattern as separate window computations on a shared graph.
Add a multiple-chunk fixture before interpreting lazy-reader cost. The existing single-chunk fixture cannot establish these properties.

The rasterio paths do record internal block counts. The lazy path reports those fields as null and substitutes chunks.
State that distinction in the record instead of promising three internal-block counts for every method.

### 4. Medium: geometric membership and footprint scoring do not establish that the requested pixels have data

Locations: [lake_membership](../../benchmarks/tile_extraction.py), lines 118 to 133, and `choose_item`, lines 214 to 224.

A buffered polygon intersecting a tile is a candidate test. It does not guarantee that any pixel center satisfies the near-land rule.
In a synthetic example, a lake 98 m outside the tile has an intersecting 100 m buffer.
The nearest pixel center lies beyond 100 m. The current masks correctly select zero pixels at all three resolutions.
The statement incorrectly treats this valid geometric possibility as a membership defect.

Footprint scoring ignores near-land support. Every near-land-only member has `in_tile == 0`.
The coverage comparison consequently counts it as covered even when the item's footprint is nowhere near its selected pixels.
A fixture with one such lake chooses a lower-cloud item covering none of its near-land pixels over an item covering them.

Disposition: open. Treat buffer intersection as candidate membership and verify nonempty selection during preparation.
Score footprint coverage against the extraction support being tested, including near-land pixels, or explicitly label near-land coverage unverified.
Keep legitimate empty selections distinct from failed preparation and missing data.
Agreement between methods on no-data values is not evidence that a lake's requested data were available.

### 5. Medium: the rotation changes pattern order but leaves method order fixed

Location: [rotated and plan_runs](../../benchmarks/tile_extraction.py), lines 245 to 270.

With the default twelve combinations and three repetitions, the rotation shifts by four positions.
That moves entire pattern groups. Within every group, methods always run naive, raster mask, index lists, then lazy.
The statement marks the prior fixed-order concern resolved for both patterns and methods, but only patterns are reordered.

Disposition: open. Counterbalance method order within patterns as well, with the resulting order saved in the plan.
The fixture needs to check relative method positions, not only each combination's absolute index.
Rotation reduces an ordering bias. It does not remove uncontrolled network variation or establish statistical equivalence.

### 6. Medium: lake-by-lake retains every earlier lake's selections unnecessarily

Locations: [run_rasterio](../../benchmarks/tile_extraction.py), lines 820 to 825, and `run_lazy`, lines 1007 to 1012.

Both lake-by-lake branches append each lake's selections to a list that they never subsequently use.
Those selections retain coordinate arrays, classes, and masks after extraction has finished for that lake.
An offline weak-reference check found 0, 3, 6, and 9 earlier selection objects alive before successive fixture lakes.

This unnecessarily makes memory depend on accumulated selections across lakes, confounding the intended loop-order comparison.
The tile-by-tile and whole-tile branches intentionally keep selections available for later files.

Disposition: open. Release completed lake selections in the lake-by-lake branches.
Keep the per-lake output records, which contain counts and digests rather than the pixel arrays.

### 7. High: laptop memory headroom is limited and the workers have no protective stop

Added after the owner's memory question on 2026-09-15.
Locations: [worker execution](../../benchmarks/tile_extraction.py), `extract_worker` and `run_in_subprocess`, and [digest allocations](../../benchmarks/lake_extraction.py), `digest_values` and `digest_pixels`.

The [stage 3 estimate](2026-09-15-stage-3-many-lakes-in-one-tile.md#expected-size-of-the-run) lists about 35 GB across 96 whole-tile runs.
That is cumulative transfer, not a measured peak RAM requirement. No 30 GB worker-memory measurement was found.
The parent starts one worker at a time. Whole-tile workers process one band at a time.
A decoded 10 m `uint16` band occupies about 230 MiB: `10980 * 10980 * 2` bytes.
This array size excludes masks, coordinates, caches, temporary arrays, and other processes.

A read-only `psutil.virtual_memory()` check during the follow-up reported 16 GiB total and approximately 3.07 GiB available.
This is a host snapshot, not a reservation or a stable limit. Available memory needs checking again before each worker starts.
The [stage 2 result](../../benchmarks/results/lake-extraction.json) records maximum process peaks of 1.45 GiB for preparation and 0.785 GiB for extraction.
Those earlier measurements do not bound stage 3, whose code and allocation patterns differ.

Stage 3 retains selections for multiple lakes and allocates coordinate arrays and 64-bit hashing temporaries.
Lazy computation adds concurrent work and intermediate arrays. The script sets no explicit lazy-worker concurrency or reader-cache budget.
Finding 6 adds unnecessary retention on the lake-by-lake path.
The harness records peak resident memory after a worker returns. It does not monitor or stop a growing worker.

Memory pressure is therefore a real concern, even without a 30 GB allocation.
Stage 3's peak remains unverified. Heavy swapping could distort timings before an allocation fails or a process is terminated.

Disposition: open. Add the following safeguards within stage 3:

1. Fix the unnecessary selection retention in finding 6.
2. Keep sequential workers and explicitly limit lazy-reader concurrency and cache sizes. Record those settings with the result.
3. Set a worker memory budget with a reserve for the parent, operating system, and other applications.
4. Check memory before launch. Monitor preparation and extraction, stopping when the worker budget or system reserve is breached.
5. Preserve partial logs and report a memory stop as incomplete work. Do not silently retry the same allocation.
6. Record memory pressure and swapping where available. Treat affected timings as unsuitable for clean performance comparisons.

These safeguards reduce risk but cannot guarantee that a rapid allocation spike will always be caught.
Use the proposed Grand Lake smoke run to check functionality after the corrections.
Then run a guarded Okeechobee preparation and extraction check, including the whole-tile lazy path, before the full pass.
Okeechobee produced stage 2's largest preparation peak. Grand Lake alone does not establish memory requirements for the largest cases.
Choose concurrency and batch limits from those observations. Neither provider check ran during this review update.

## Other corrections and limits

- The shared-tile merge branch writes the second region's item file before detecting the duplicate tile, at lines 1366 to 1382.
  The retained scene and asset list can still refer to the first item, while the lazy reader loads the overwritten second item.
  This is outside the six separated pilot regions. Reject duplicate-region tile selection or merge members before selecting and saving one item.
- Equality does not compare naive coordinate digests across patterns when naive values match.
  Add that check for naive-only plans, and keep the declared pixel-set tolerance separate from value equality.
- `resummarize` reconstructs selected lakes from preparation keys, losing unplaced lakes, and tolerates a missing baseline file.
  Preserve the original requested lake IDs and refuse a missing recorded baseline, as with a changed baseline digest.
- A single labeled lake-ID raster has not been implemented or timed. Calling current extraction time an upper bound for that design is unsupported.
- The root README still claims every pilot lake was read in stage 2. Thirty yielded pixels and two were outside the chosen tiles.

## Source checks

Accessed 2026-09-15. Separate research and checking agents confirmed these distinctions against primary documentation and installed source.
Installed versions were odc-stac 0.5.3, odc-loader 0.6.4, odc-geo 0.5.3, and Dask 2026.8.0.

| Question | Primary evidence | Outcome |
|---|---|---|
| Does a reused graph retain results from separate computes? | [Dask repeated computes](https://docs.dask.org/en/stable/best-practices.html#avoid-calling-compute-repeatedly), [persist](https://docs.dask.org/en/stable/generated/dask.array.Array.persist.html) | No retained decoded-chunk reuse is configured here |
| Does one lazy load mean one raster open? | [ODC rasterio reader source](https://odc-stac.readthedocs.io/en/latest/_modules/odc/loader/_rio.html) | Physical opens occur during source reads |
| Where do chunks start? | [ODC load source](https://odc-stac.readthedocs.io/en/latest/_modules/odc/stac/_stac_load.html), [GeoboxTiles](https://odc-geo.readthedocs.io/en/latest/_api/odc.geo.geobox.GeoboxTiles.html) | At the supplied output geobox |
| Does reopening prove another network transfer? | [GDAL virtual file cache](https://gdal.org/en/stable/user/virtual_file_systems.html#vsicurl-http-https-ftp-files-random-access) | No. Downloaded bytes can remain cached across opens |

## Verification and next step

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed in order on Claude's implementation:

1. `uv sync --locked`: 59 packages resolved, 56 checked.
2. `uv run ruff check .`: passed.
3. `uv run ruff format --check .`: 73 files already formatted.
4. `uv run pytest -q`: 159 passed in 4.87 seconds.

The suite emitted 372 dependency deprecation warnings about affine multiplication.
Inventory, presentation, and gap-report freshness checks passed. Stage 3 `--dry-run` printed 36 runs per tile and the rotation without network access.
`git diff --check` passed.
After adding this review, `python -m pytest tests/test_docs.py -q` passed all 46 documentation checks in 0.10 seconds.
That command used the repository's `.venv/bin/python`.

After the memory addendum, the full check workflow passed again on 2026-09-15: 160 tests in 4.31 seconds.
Dependency checks, lint, and formatting passed, with 74 files already formatted. The same 372 dependency warnings remained.
The addendum changes only this review. No benchmark code, result, or run configuration changed.

Additional local diagnostics reproduced baseline contamination, an omitted lake, later-repetition error reporting, empty membership, and incorrect near-land footprint scoring.
Multiple-chunk diagnostics measured actual opens and compared chunk origins. A weak-reference diagnostic checked selection retention.
These diagnostics used temporary synthetic files and saved stage 2 evidence. They did not alter benchmark results or tests.

This review adds only this record and its index entry. Implementation and documentation fixes remain separate for Claude's response.
After those corrections and focused fixtures, the owner can invoke the already proposed smoke run.
Check accounting and completeness there, then validate memory on the larger case described in finding 7 before the full pass.
This remains stage 3 preparation and validation. No additional experimental stage is proposed here.
