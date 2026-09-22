# Geometry diagnostics and workload continuation, 2026-09-18

Follow-up: both cohorts passed preflight. The [execution record](2026-09-19-larger-workload-execution.md) owns the subsequent run status.

Author: Codex, directed by the repository owner.
The owner accepted the [assessment](2026-09-18-claude-geometry-blocker-assessment.md) and requested implementation followed by the authorized experiment.
The purpose is to compare compute, elapsed processing time, transfer, and memory across workflows.
Selection geometry convergence is a recorded diagnostic. Scientific geometry validation remains separate work.

## Dispositions and implementation

| Finding | Disposition | Change |
|---|---|---|
| Lake Yale stops preparation | Corrected with evidence | Use the smallest-bound refinement after nine unsuccessful refinements and record non-convergence |
| Source versions prevent continuation | Fixed | Explicit source supersession preserves prior records and invalidates source-dependent preparation |
| Buffered-support criterion needs a new derivation | Accepted and deferred | Keep the existing criterion, tolerance, and buffer settings |
| Replacing the failing lake | Rejected as recommended | Retain both existing cohorts |
| Additional refinements or weaker tolerances | Rejected as recommended | Retain the existing bounds and iteration count |

The [geometry function](../../benchmarks/cross_tile_extraction.py) retains the successful return path and its original audit fields.
An unsuccessful convergence audit includes the chosen iteration, spacing, smallest bound, and every successive-refinement bound.
The chosen polygon still passes the existing round-trip displacement check. Invalid polygons and failed round trips still raise errors.
Native pixel classes use the original polygon through the existing mask implementation.

The [runner](../../benchmarks/lazy_reader_workloads.py) records unconverged lakes in the selected plan, freeze result, console output, and preflight.
Its limitations explain that this approximation affects selection diagnostics.
Output identities and values remain comparable across readers using the same frozen selections.

`--accept-source-change REASON` applies only with `--execute` and an existing owned run.
It rejects extraction launch records, unresolved attempts, inconsistent recorded source versions, changed artifacts, and active workers.
It verifies the saved metadata and geometry artifacts before updating anything.
The transition appends old and new digests, changed files, reason, timestamp, archive paths, and archived hashes to `run.json`.
Freeze and preparation phase records move into their phase archives.
Their plans, geometry databases, selection diagnostics, and header logs move into the source archive.
An interrupted transition leaves a marker that blocks automatic continuation with mixed versions.

Boundary and catalog records retain their original artifact hashes and reuse checks.
Those phases do not call the changed geometry function. Provider metadata selection and both original cohort manifests remain intact.
The source files before this change were also saved locally under the existing run directory.

## Verification

The public Lake Yale fixture contains its original boundary and the saved catalog geometry, without asset URLs or pixel data.
Its regression test requires the recorded non-convergence, 125 m spacing, smallest bound, valid round trip, and complete native support.
`17RMN` fully contains the lake. `17RMM` remains an overlapping observation, consistent with the existing native-membership rule.
An initial test incorrectly expected only one membership. That assertion was corrected to distinguish full containment from overlap.
Full containment is checked geometrically, without exact equality on floating-point area ratios.
An initial converged-fixture test also had a dictionary-unpacking error, corrected without changing benchmark behavior.

Additional tests cover unchanged converged audits, freeze reporting, source-version rejection, archived extraction launches, preserved inputs, and interrupted transitions.
Existing tests retain zero-tolerance output agreement across all seven reader configurations.
The repository check workflow passed in its required order before provider execution.
`uv sync --locked`, `uv run ruff check .`, and `uv run ruff format --check .` passed.
`uv run pytest -q`: 262 passed in 29.25 seconds, with 13,000 dependency warnings.
Inventory, sensor dataset, presentation renderer, and gap-report `--check` commands passed. `git diff --check` passed.
Execution evidence and final presentation verification will be added after the authorized continuation.

The presentation adds worker CPU seconds beside elapsed extraction time and peak benchmark memory.
CPU measures user plus system time. RAM peaks sample the supervisor and worker processes every 0.1 seconds, so shorter spikes can be missed.

## Authorized continuation

The owner's instruction covers the source supersession, rebuilt preflight, and subsequent extraction.
Review the actual preflight locally, then continue within the unchanged scope and memory limits.
No additional owner approval is required for these already authorized actions.

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved --accept-source-change "geometry convergence recorded, not fatal, per the 2026-09-18 assessment"
uv run python benchmarks/lazy_reader_workloads.py --extract data/lazy-reader-workloads/2026-09-18-approved
```

The saved dispersed selections will be compared with their archived version before extraction.
Preparation must retain both complete cohorts and disclose every unconverged lake.
Each launched extraction still consumes its single attempt. Startup refusals remain resumable without consuming an attempt.
Downloaded imagery is removed after use. Compact signatures, metadata, prepared geometry, and resource records remain available for audit.

Scientific validation, the primary-tile decision, the support-bound derivation, and production storage remain deferred.
No commit, push, or publication is authorized.
