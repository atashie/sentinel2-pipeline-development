# Stage 4 review response, 2026-09-16

Author: Codex. Status: corrections accepted by the owner on 2026-09-17.
This responds to [Claude Code's review](2026-09-16-claude-stage-4-full-run-review.md).
The extraction evidence holds. The interpretation and future selection needed correction.
The measured result, smoke result, and frozen plans remain unchanged.
No provider request or public-image read was needed. Tests use synthetic local rasters.

## Dispositions

| Finding | Severity | Disposition | Location and evidence |
|---|---|---|---|
| 1. Split datastrips | Medium | Fixed, with conservative native-grid membership retained | `select_region`, `coverage`, `geometry_context`, preparation, and worker naming in [cross_tile_extraction.py](../../benchmarks/cross_tile_extraction.py). Finding 23 records the six discarded products |
| 2. Coarse footprints | Medium | Fixed. Drop the strict preference and the footprint-overlap table column. Qualify pixel coverage | [Finding 23](../measurements.md#23-tile-geometry-product-identity-and-band-validity-need-separate-accounting), saved geometry audit, and future selection ranking |
| 3. Per-band no-data | Medium | Fixed, with narrower SCL and water claims | Finding 23 separates band validity from footprint geometry. The [contract discussion](../data-contract.md#questions-for-the-next-contract-revision) carries unresolved validity semantics |
| 4. Primary roles | Medium | Accepted and deferred to the owner | Recorded roles remain unresolved. The proposal needs a metric, tie rule, margin, and polygon-version binding |
| 5. Wording and precision | Low | Fixed, except the asserted network cause is qualified | Finding 24, empirical preflight estimate, swap-in reporting, and shorter current state in `CLAUDE.md` |
| 6. Additional evidence | Low | Added, with causal limits | Findings 24 and 25 add cache reuse and window occupancy. The [run record](2026-09-16-stage-4-full-run.md) records smoke reproducibility |
| 7. Mid-step code changes | Low | Accept this correction's review. Do not adopt a blanket approval gate | The existing authorized-step workflow remains. Material scope, scientific, or resource changes need review before execution |

## Future selection and execution

The script advances to version 3. Historical run commands require their recorded source version, rather than bypassing the frozen hash check.
Distinct declared datastrips survive within a tile and datatake.
Only alternatives sharing the complete declared datastrip identity compete on creation time and item id.
Missing datastrip identity prevents deduplication. Different ids are not assumed equivalent across processing versions.

Each retained item has separate metadata, worker identity, GDAL logs, contribution keys, and footprint diagnostics.
Preparation reuses one mask for the same polygon and native tile grid.
The convergence calculation sums potential datastrip changes within each group, then bounds the largest group.
It retains the existing numerical threshold and does not claim accuracy against exact source geometry.

I disagree with using the catalog footprint as a hard membership filter.
Finding 2 demonstrates that those polygons can exclude valid candidate areas.
The implementation retains native tile intersections and records each product's footprint fraction separately.
Some partial products may therefore require reading no-data windows. That cost is preferable to silently excluding possible observations.

The strict per-member footprint preference is removed.
The remaining order is uncovered footprint fraction, cloud cover, sensing time, and stable identity tie-breaks.
Footprint fraction is explicitly a coarse heuristic. No arbitrary distance tolerance replaces it.

Preflight now scales observed windowed workload bytes by membership count, separately for each reader and work organization.
The default reference is the reviewed Stage 4 result. `--transfer-reference` accepts another compatible Stage 4 result.
Reference hashes, rates, settings, and observed ranges are recorded. Missing or incompatible evidence produces an unknown estimate.
Whole-workload totals include shared opens, avoiding the undercount that marginal per-lake records would introduce.
This improves planning relevance without creating a hard transfer guard or extrapolating across unmeasured polygon distributions.

## Interpretations I qualified

**SCL and zero values.** All selected SCL entries are nonzero at 20 m. The reported band zeros occur at 10 m.
The saved aggregates do not locate those zeros within SCL cells or distinguish water from near-land classes.
Therefore, they cannot establish that every zero lies inside sensed water.
Declared band no-data is identifiable from asset metadata independently of SCL.
Nor does stored zero establish physical zero reflectance. The cause of the missing band values remains unknown.

Different zero counts across tile grids motivate matched-location checks.
They do not prove different values for the same ground pixels, because coverage, sampling, and selected pixel sets differ.

**Slow runs.** Repeated request and byte totals, near-constant CPU time, and longer read calls support an I/O-wait explanation.
They do not isolate the network from remote service latency or host scheduling.
The measurements now state this evidence instead of leaving the observation unexplored or asserting a proven network cause.

**Shape and zone boundaries.** The bytes-per-entry and window-occupancy differences are verified and useful for cost planning.
This experiment does not isolate their causes. Both anchors used four tiles, and the denominator retains overlapping entries.
I therefore keep the measured comparison without attributing its magnitude to the zone boundary or reservoir shape alone.

**Workflow.** Routine corrections within an authorized step do not automatically require another approval.
Changes to the workload, scientific assumptions, numerical tolerances, or resource limits warrant review before execution.
The original correction preserved those limits, added a regression test, and retained its failed preflight evidence.
Claude Code has reviewed that correction. This response makes future behavior explicit and leaves its new code ready for review.

## Owner decision still open

The recorded role gap is real: 22 of 25 memberships, covering eight lakes, have no primary or overlap label.
Lanier's ponds have multiple containing tiles. Its anchor has no single containing tile, contrary to the review's broader sentence about every Lanier lake.
Buffered and unbuffered shares choose different primary candidates for the anchor.
The owner still selects the metric and tie rule. The eventual choice needs a recorded margin and an explicit polygon version.
Full contract compliance remains unevaluated until that choice is made.

## Verification

The targeted suite passed: 21 tests in 7.86 seconds.
The new fixture retains two overlapping partial products from one tile through both readers and both work organizations.
It checks distinct values, complete matching contributions, separate logs, and shared mask preparation.
Additional tests cover unknown datastrip identities, conservative membership, empirical transfer scaling, and incompatible reference settings.

The first targeted pass exposed two test failures.
The ranking fixture still expected the removed strict preference. It now distinguishes individual-footprint shortfalls from an actual union gap.
The new unknown-datastrip fixture accidentally shared one copied object. Independent copies corrected its setup.
The alternative-revision geometry test now declares the shared datastrip identity required for valid deduplication.

Saved-artifact checks use `review-response-audit.py` and `review-response-audit.json` in `data/cross-tile-extraction/2026-09-16T204751+0000/`.
They verify geometry shortfalls, SCL summaries, per-band zeros, cache reuse, window occupancy, slow-worker accounting, and smoke agreement without reading pixels.
The measured version 2 script is preserved there as `cross_tile_extraction.v2.py`, with its hash checked against the frozen result.

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed in order.
Dependency synchronization, lint, and formatting passed. `uv run pytest -q`: 195 passed in 11.97 seconds, with library deprecation warnings.
The inventory collator, presentation renderer, and gap-report `--check` commands passed. `git diff --check` passed.
Both result digests are unchanged, and both frozen plan digests remain valid.
Version 3 has synthetic fixture coverage. Its performance on another public catalog selection or imagery run is unmeasured.

## Next step

The owner accepted this response and authorized the [documentation and presentation update](2026-09-17-documentation-and-presentation.md).
That update includes the corrected findings. Review its presentation before agreeing another workload.
Stage 5 and another provider run require separate owner authorization.
