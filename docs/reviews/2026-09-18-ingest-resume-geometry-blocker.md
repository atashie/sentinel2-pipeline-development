# Ingest resume and geometry blocker, 2026-09-18

Follow-up: the owner accepted [recorded non-convergence](2026-09-18-geometry-diagnostic-resume.md) and authorized the comparison to continue.
This supersedes the proposed correction of buffered-shoreline convergence below. The criterion remains unchanged and its failure becomes a diagnostic.

Author: Codex, directed by the repository owner.
The owner requested continuation from the [restart handoff](2026-09-18-ingest-restart-handoff.md).
Preflight resumed in the existing directory and stopped during Florida geometry selection. No extraction configuration launched.
The full comparison remains authorized under its existing [plan](2026-09-18-lazy-reader-workload-plan.md).

## Restart verification

The repository check workflow passed before provider work:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 106 files already formatted.
- `uv run pytest -q`: 252 passed in 15.47 seconds, with 12,916 dependency warnings.

The previously failing memory-stop test passed without changing its fixture, assertion, supervisor, or resource limits.
Disposition: corrected with evidence for the restart gate. The cause of its earlier failure remains unverified.
The startup audit found 7.47 GiB available, matching source digests, and no active or unresolved workers.

## Resumed preflight

Command:

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved
```

The runner reused verified completed preparation and continued Florida catalog selection.
Both boundary manifests exist. The dispersed cohort has a complete frozen plan and prepared selections.
Florida catalog selection completed. Its geometry selection failed on Lake Yale, `nhd-112613946`.
The error was `ValueError: geometry did not converge: nhd-112613946`.
The supervisor recorded a worker failure, not a memory stop.

Local evidence remains under `data/lazy-reader-workloads/2026-09-18-approved/`:

| Record | Evidence |
|---|---|
| `preflight.json` | `preflight_incomplete`, stopped at `florida/freeze` |
| `dispersed/frozen-plan.json`, `dispersed/preflight.json` | Completed dispersed preparation |
| `florida/manifest.json`, `florida/catalog.json` | Retained boundary and catalog inputs |
| `florida/freeze.result.json`, `florida/freeze.stdout.log` | Failing lake and traceback |
| `florida/freeze.supervision.json` | Failure status and resource measurements |
| `restart-resume-audit.json` | Source integrity, unused extraction attempts, worker absence, and cleanup |

These local records describe incomplete preparation. No extraction result exists under `benchmarks/results/lazy-reader-workloads.json`.
The presentation therefore retains its existing benchmark evidence.

## Offline diagnosis

The saved polygon and catalog reproduced the failure without provider access or image reads.
The diagnostic copied the geometry function, logged each error-bound component, and allowed additional refinements under the unchanged resource supervisor.
It changed no benchmark source, frozen plan, tolerance, or input polygon.
Additional allocation admission guarded refinements beyond the original iteration limit.

At the original final refinement, the relative change bound was `1.052844446834325e-6` against the required maximum `1.25e-7`.
Buffered-support changes dominated the bound. Tile-extent and catalog-footprint contributions were zero at that refinement.
One additional refinement produced a larger bound, `2.55010591584987e-6`, and still failed the criterion.
The following refinement was refused because its conservative allocation estimate exceeded the planned worker footprint.
This does not establish that every possible geometry algorithm exceeds the memory budget.

Diagnostic evidence is retained in `diagnostics/lake-yale/` beneath the same run directory:

- `diagnostic.py`: exact offline diagnostic source.
- `refinements.json`: spacing, component areas, relative bounds, and resident memory.
- `result.json`: source digests and the final allocation refusal.
- `spec.stdout.log`, `spec.supervision.json`: diagnostic output and supervision evidence.

The measurements identify the buffered-support term as the immediate blocker. They do not establish its underlying numerical cause.
Increasing the iteration count alone did not resolve this case. No geometry threshold was relaxed to accept it.

## Preserved state and next step

All eleven source digests still match the saved run identity. All fourteen extraction attempts remain unused.
The owned temporary image workspace was removed, with no remaining files. No benchmark or diagnostic worker remains active.
Existing modifications remain uncommitted. No files were staged, committed, pushed, or published.

Correct and verify buffered-shoreline convergence using the saved Lake Yale case before resuming extraction.
Retain the declared tolerances, exact cohort counts, resource limits, and single-attempt extraction rule.
Any source correction requires an explicit, audited re-freeze strategy that preserves the current evidence and records the source-version change.
Do not manually replace saved source digests or pass an incomplete preflight to extraction.
The original restart commands alone cannot resolve this deterministic geometry failure.

Review this blocker and the corrective approach before changing the frozen implementation.
Scientific validation, production storage, and the primary-tile decision remain separate work.

## Final documentation verification

The repository check workflow passed again after the documentation changes:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 107 files already formatted.
- `uv run pytest -q`: 253 passed in 14.81 seconds, with 12,916 dependency warnings.

The inventory, sensor dataset, presentation renderer, and gap-report `--check` commands passed.
`git diff --check` passed. The additional test is the new review document's link check.
