# Geometry blocker assessment and the path back to extraction, 2026-09-18

Author: Claude Code (AI coding agent), directed by the repository owner.
This reviews the [resume record](2026-09-18-ingest-resume-geometry-blocker.md) and proposes the corrective step for Codex.
The owner's stated priority is the workflow comparison. Exact consistency between geometry refinements is not required now.
This step changes documentation only. It contacted no provider, read no pixel, and changed no benchmark source.
An offline prediction over the pending Florida lakes ran under the repository's own memory supervisor. Its evidence is recorded below.

## What fails and why

`geometry_context` in [cross_tile_extraction.py](../../benchmarks/cross_tile_extraction.py) halves a densification spacing nine times, from 1,000 m to 3.9 m.
It accepts the first refinement whose relative change bound is at most 1.25e-7, one eighth of the declared 1e-6 tolerance.
The bound divides four terms by the polygon area. They are the polygon's own change, the buffered support's change times a multiplier, the tile extent change, and the largest group footprint change.
The multiplier is one plus the tile count plus the footprint count. In Florida it is nine.

Lake Yale, `nhd-112613946`, sets the following budget under that arithmetic. The measurements come from Codex's saved [refinement log](../../data/lazy-reader-workloads/2026-09-18-approved/diagnostics/lake-yale/refinements.json).

| Quantity | Value |
|---|---|
| Polygon area | 16.34 km² |
| Polygon perimeter | 24.0 km |
| Allowed change, all terms together | 2.04 m² |
| Allowed support change after the multiplier of nine | 0.23 m² |
| Observed support change across eight refinements | 0.60 m² to 4.63 m², never decreasing |
| Observed polygon change across the same refinements | 0.63 m² falling to 0.005 m², then 0.0 m² |

The polygon itself converges. The buffered support does not, and it never can under this arithmetic.
GEOS builds the 100 m buffer from the input vertices. Each refinement moves buffer vertices by roughly a tenth of a millimeter along 23 km of boundary.
That sliver is square meters of symmetric difference, and it does not shrink with spacing.
The allowed change grows with lake area. The noise grows with shoreline length. The multiplier of nine amplifies the noise.
The criterion is therefore ill-conditioned for lakes with long shorelines whose edges exceed 250 m, because only those polygons change under densification at all.

Most lakes pass without any refinement. Of the 461 Florida lakes that finished before the failure, 451 converged at 500 m with a bound of exactly zero.
Their longest edge is shorter than 500 m, so densification changed nothing and the difference was empty.
Two finished lakes passed narrowly. The 47.6 km² lake reached 1.226e-7 against the limit of 1.25e-7. A 0.2 km² pending lake reaches 1.247e-7.
For such lakes, convergence under the current criterion is a matter of luck at one of the nine refinements.

## What the criterion protects

The criterion gates only the acquisition selection diagnostics: the buffered share per tile, the uncovered fractions, and the datatake ranking.
`select_region` compares those fractions at the 1e-6 tolerance.
It does not gate pixel selection. Pixel classes come from [masks.py](../../src/s2proto/masks.py) on the native grid with exact areas, under assumption A20.
The frozen selections and expected contributions never see the refined reference polygon.

The inputs do not carry the precision the criterion demands.
The Stage 4 review found the public polygons good to about 130 m. Codex's Stage 4 response calls the catalog footprint fraction a coarse heuristic.
A relative area requirement of 1.25e-7 on those inputs is arithmetic self-consistency, not geometric accuracy. The Stage 4 review already said so.

## Offline prediction over the pending lakes

A patched copy of `geometry_context` recorded every refinement and returned a chosen refinement instead of raising.
`select_region` then ran for each of the 539 pending Florida lakes, using the saved polygons and the 28 saved catalog items.
The run used the repository's supervisor and limits. It contacted no provider and changed no repository file.
Evidence sits beside Codex's diagnostic under `data/lazy-reader-workloads/2026-09-18-approved/diagnostics/florida-pending-convergence/`, ignored by git.
The script's SHA-256 starts `1a944258` and the prediction file's starts `4e980233`. Both are reproducible from the saved inputs.

| Measure | Value |
|---|---|
| Pending lakes tested | 539 |
| Failed the criterion | 1, Lake Yale |
| Converged at 500 m with zero change | 513 |
| Converged after one to seven refinements | 25 |
| Elapsed under the supervisor | 137 s |
| Peak worker resident memory | 928 MiB |

The dispersed cohort converged for all 100 lakes in the actual run. Across both cohorts, exactly one lake in 1,100 fails.

For Lake Yale, three refinement choices were compared: the smallest bound at 125 m, the finest at 3.9 m, and the coarsest at 500 m.
All three select the same datatake, `GS2B_20250601T155819_043023_N05.11`. All three rank the same seven eligible datatakes in the same order.
All three assign the same single containing tile, `17RMN`. The uncovered fractions are identical at 0.0.
The buffered shares differ by at most 1.5e-8. The refinement choice changes no decision for this lake.

## Options considered

1. **Record the failure and proceed.** Recommended. Keep the criterion, the tolerance, and nine refinements. When no refinement passes, use the refinement with the smallest bound and record that it did not converge.
2. **Re-derive the support term.** Deferred. Bound the support change from the polygon's vertex displacement and the shoreline length, instead of differencing two buffer discretizations. My estimate is convergence near 7.8 m for Lake Yale. It changes the numerical criterion, needs its own derivation and review, and the experiment does not need it now.
3. **Drop or replace Lake Yale.** Rejected. It changes the frozen cohort, biases it against long shorelines, repeats boundary selection with provider contact, and leaves the failure for the next cohort.
4. **Loosen the tolerance or add refinements.** Rejected. Codex's tenth refinement made the bound larger and reached 1.49 GiB. A looser tolerance hides the conditioning problem.

## Proposed step for Codex

The step has two code changes, tests, records, and a recorded resume of the same run directory. Owner authorization precedes it.

### Geometry change

1. In `geometry_context`, keep the refinement with the smallest bound while the loop runs.
2. After nine refinements without a pass, return that refinement instead of raising.
3. Extend only that audit with `converged: false`, the chosen iteration, and the bound of every refinement.
4. Keep the round-trip displacement check on the chosen refinement. Keep raising when it exceeds the tolerance.
5. Leave the converged path byte-identical. Its audit gains no key, so a re-frozen converged cohort can be compared to its archive.
6. Change no tolerance, multiplier, refinement count, or buffer setting.

### Runner change: a recorded source supersession

Any change to `cross_tile_extraction.py` changes a digest in `run.json` and in the dispersed frozen plan. The runner then refuses to continue.
The blocker record forbids manual digest replacement. That rule stands. The runner needs an explicit, audited way to record a source change instead.

1. Add an option to `--execute`, for example `--accept-source-change REASON`. Without it, behavior is unchanged.
2. Refuse the option when any extraction launch record exists. Launched attempts bind the old source.
3. Refuse the option when the recorded digests do not match `run.json`. The caller must supersede exactly the recorded version.
4. Append an entry to `run.json` under `source_history`: time, reason, previous digests, current digests, and the changed files. Then replace `source_digests`.
5. Archive the freeze and prepare phases of both cohorts with the existing `archive_phase`. Their artifacts embed the old digests, and freeze runs the changed function.
6. Keep the boundaries and catalog phases. Their artifact hashes verify through the existing reuse check, and neither phase calls `geometry_context`. State that in the record.
7. Continue the normal execute flow.

### Freeze reporting

1. In `freeze`, collect each lake's `geometry_check` from its selection diagnostic.
2. Write the lakes with `converged: false` into `selected-plan.json` and the freeze result, with their spacing and bound.
3. Print those lakes during freeze and count them in `preflight.json`.
4. Add one limitation to the runner's list. Lakes that did not meet the refinement criterion use the refinement with the smallest bound, recorded per lake.

### Tests

1. Copy the Lake Yale polygon into the test fixtures. It is a public boundary of 570 vertices and 37 KB.
2. Assert that `geometry_context` returns for it with `converged: false`, spacing 125 m, and a bound near 4.4e-7.
3. Assert that `coverage` on that context reports no uncovered support and a valid round trip.
4. Assert that a converging fixture's audit is unchanged. The existing single-versus-many audit equality test covers this.
5. Assert that the runner refuses a changed source without the option and refuses it after a launch record. Otherwise it records the history and archives freeze and prepare.
6. Assert that the re-frozen plan's digests equal the new source and that boundaries and catalog were reused.

### Records

1. Write the dated record for the step with dispositions. The blocker becomes `corrected with evidence`.
2. Mark the blocker record's proposed correction of buffered-shoreline convergence as superseded. The criterion is unchanged, and its failure is now recorded rather than fatal.
3. Mark the re-derived support term as `accepted and deferred`.
4. Update the review index, the README status line, the CLAUDE.md phase line, and the work plan's first step.
5. Run `/check` and `git diff --check`. Commit nothing without the owner's authorization.

### Execution after authorization

1. Run the check workflow.
2. Resume the run directory with the source change recorded:

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved --accept-source-change "geometry convergence recorded, not fatal, per the 2026-09-18 assessment"
```

3. Confirm the dispersed re-freeze. Its selected plan must equal the archived one except for source digests. Its selection and expected databases must carry the archived digests.
4. If a database digest differs, compare the table rows before concluding anything. Stop if the rows differ.
5. Confirm that Florida reports exactly one unconverged lake, Lake Yale, with the same datatake the prediction selected.
6. Inspect `preflight.json` as the handoff already requires, then stop for the preflight review.
7. Run `--extract` only after that review. The single-attempt rule, the memory limits, and the fourteen configurations remain unchanged.

Expected costs from the saved phase records: the dispersed freeze took 32 s and its prepare 198 s, of which 171 s were header requests.
The Florida freeze needs roughly two minutes plus the prepare phase, which has not run yet. No pixel is read before `--extract`.

### Acceptance checks for the step

- `/check` passes, including the new fixture tests.
- `run.json` holds one `source_history` entry, and every current digest matches the working tree.
- Both cohorts report `preflight_complete`. All fourteen launch records are still absent.
- The dispersed selection and expected database digests equal their archived values.
- Florida lists one unconverged lake with its bound, and every other lake carries a converged audit.

### Deferred

The re-derived support bound, the primary-tile rule, scientific validation, and production storage remain separate work.
The memory-stop test's earlier failure remains unexplained and is not part of this step.

## Owner decisions

1. Authorize the step above, including the recorded source supersession in the existing run directory.
2. Confirm that recording a non-converged refinement is acceptable for this experiment, in place of correcting the criterion now.

## Verification

This record and the review index changed. No other file changed, and nothing was staged, committed, pushed, or published.
The check workflow passed after the documentation change:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 108 files already formatted.
- `uv run pytest -q`: 254 passed in 14.83 seconds, with 12,916 dependency warnings.

`git diff --check` passed. The additional test is this record's link check.
