# Ingest restart handoff, 2026-09-18

Follow-up: the owner returned and resumed preflight. The [resume record](2026-09-18-ingest-resume-geometry-blocker.md) owns current status and the geometry blocker.
The saved state below describes the checkpoint before that continuation.

Author: Codex, directed by the repository owner.
The owner requested a laptop restart before the authorized ingest begins.
This step saves continuation instructions and a local working-tree backup. It starts no provider work.

## Resume point

The implementation and agreed review corrections are complete. The restart verification found a memory-stop test failure that blocks ingest pending investigation.
Read the [review response](2026-09-18-lazy-reader-review-response.md) for current behavior and the [approved plan](2026-09-18-lazy-reader-workload-plan.md) for scope.
The original implementation record contains superseded commands. Use this handoff and the review response instead.

The owner already authorized the complete comparison and subsequently requested execution.
That authorization covers preflight followed by extraction within the approved scope and resource limits.
The restart does not require another experiment approval. Sandbox permissions may still require approval for individual commands.
Do not start any ingest before the owner returns after restarting.

The experiment compares 100 dispersed continental U.S. lakes with 1,000 concentrated Florida lakes, including varied sizes.
Each cohort has seven configurations: A-raster, A-lazy, B-raster, B-lazy, B-lazy-control, C-raster, and C-lazy.
A processes lakes separately. B shares source-image reads across lakes. C reads whole images before selecting lake pixels.
The approved comparison has no pilot, progressive subsets, or repeated timed attempts.
Downloaded imagery must be deleted after use. Retain compact audit records and prepared geometry selections.

## Saved execution state

The existing run directory is `data/lazy-reader-workloads/2026-09-18-approved`.
Its `preflight.json` records `2026-09-18T18:35:16+00:00`, status `preflight_incomplete`, and stopped phase `dispersed/boundaries`.
The supervisor recorded `not_started`, `spawned: false`, and `insufficient available memory to start`.
No provider request, imagery download, or extraction attempt started. All fourteen extraction attempts remain available.

The local audit verified these conditions:

- `ps -axo pid,ppid,rss,etime,command` showed no workload runner, selector, or extraction process.
- No worker launch records exist in the run directory.
- `cleanup.json` records an empty, removed temporary workspace.
- All eleven source digests in `run.json` match the current files.
- `benchmarks/results/lazy-reader-workloads.json` does not exist yet.
- The Git index contains no staged changes. Existing modifications and untracked files remain uncommitted.

The retained supervisor record describes an exited process. Keep it for the runner's recovery checks.
Do not delete the run directory, invent completed results, or manually change source digests.

## Commands after restart

1. Open the existing repository and read this handoff with [CLAUDE.md](../../CLAUDE.md).
2. Run the repository check workflow in order, stopping at the first failure:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

The memory-stop test below must pass before provider execution. Investigate any repeated failure without weakening its assertion or resource limits.

3. Check available memory from the repository root:

```sh
.venv/bin/python -c 'import psutil; print(round(psutil.virtual_memory().available / 2**30, 2), "GiB available")'
```

Startup requires at least 5 GiB available.
Keep the approved [memory controls](2026-09-18-lazy-reader-workload-plan.md#memory-protection) unchanged.
Their implementation is [workload_resources.py](../../src/s2proto/workload_resources.py).
If memory remains insufficient, leave execution paused. Do not lower the floor automatically.

4. Resume preflight in the existing owned directory:

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved
```

5. Inspect `preflight.json` and the printed cohort counts, coverage, allocations, and transfer estimates.

Continue only after both cohorts finish preparation and the preflight reports `preflight_complete`.
Provider failures, incomplete selections, or integrity failures need investigation before extraction.
Transfer scenarios are historical proxies, not predicted bounds. The approved experiment has no transfer ceiling.

6. Run the authorized frozen comparisons:

```sh
uv run python benchmarks/lazy_reader_workloads.py --extract data/lazy-reader-workloads/2026-09-18-approved
```

Repeat the appropriate command to resume after a resource pause.
Preparation reuses verified successful phases. Extraction skips every configuration whose worker has already launched, including failed attempts.
Keep the same directory and frozen source files. Do not create a second run to repeat an extraction attempt.

7. Verify completeness, output agreement, resource records, and cleanup before interpreting results.
8. Regenerate the presentation after extraction:

```sh
uv run python tools/render_options.py
```

9. Run the repository check workflow and renderer check, then write the execution review.
10. Report complete and incomplete comparisons separately, then stop for owner review.

Do not hand-edit benchmark result JSON. Scientific validation, production storage, and primary-tile decisions remain separate work.

## Persistence and verification

All implementation files are saved in the repository, including currently untracked files.
The local checkpoint is `data/restart-handoff/2026-09-18-before-ingest.zip`.
It contains changed and untracked repository files, Git patches, the run records, and a SHA-256 manifest.
It excludes imagery, environments, caches, and unrelated ignored data.
The checkpoint is additional recovery material. Normal continuation uses the current working tree without restoring anything.
No commit, push, or publication is authorized or performed.

The preceding implementation check passed 251 tests in 16.47 seconds.
The restart handoff's check stopped at its first failure:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 106 files already formatted.
- `uv run pytest -q`: one failed, 251 passed in 37.80 seconds, with 12,916 dependency warnings.

The failing test is `tests/test_lazy_reader_workloads.py::test_supervisor_stops_a_real_worker_and_descendant`.
At line 269, it expected `result["status"] == "memory_stopped"` but received `complete`.
This fixture launches a worker and descendant, each allocating 32 MiB, and compares live aggregate RSS against a threshold.
The cause is unverified. Host memory pressure or changing resident memory may affect the fixture, but neither explanation is established.
No assertion, test, benchmark source, or memory limit was changed to obtain a pass. No retry was performed before restart.
The owner requested restart preparation, so diagnosis resumes after reboot rather than expanding this step into a code change.

Next step: rerun the check workflow after restart, resolve any repeated failure, then resume the existing preflight.
