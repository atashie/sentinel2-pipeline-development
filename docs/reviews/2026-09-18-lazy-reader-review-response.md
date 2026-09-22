# Lazy-reader workload review response, 2026-09-18

Author: Codex, directed by the repository owner.
This responds to [Claude Code's review](2026-09-18-claude-lazy-reader-workload-review.md).
The owner requested implementation of agreed suggestions and an explanation of disagreements.
This step changes code, tests, documentation, and the local presentation. It contacts no provider and performs no imagery comparison.

## Dispositions

| Finding | Disposition | Result |
|---|---|---|
| 1. Preflight separation and missing estimates | Fixed, with an authorization qualification | Preflight stops before pixel extraction. Every configuration has a historical transfer scenario with explicit compatibility limits |
| 2. Resume without repeated attempts | Fixed | Persistent geometry selections, verified phase reuse, launch records, and separate extraction resumes |
| 3. Lower the memory floor | Accepted and deferred as an optional resource change | Retain the approved startup requirement, available-memory floor, and aggregate RSS limit |
| 4. Florida acquisition coverage | Fixed | Greedy assignment covers the most remaining complete lakes, preserving one acquisition per lake |
| 5. Remove dispersed whole-image passes | Retain the owner's existing direction | Both readers and all fourteen configurations remain in the experiment |
| 6. Raster cache sharing | Accepted, with a numerical qualification | Keep file-then-lake raster order and repeated-range diagnostics. Cache eviction remains a measurement question |
| 7. Large identifier queries and pacing | Fixed | Count first, subdivide large queries, deduplicate identifiers on disk, record shortages, and pace requests |
| 8. Declare expectations | Fixed, with conditional expectations | The revised plan states prospective comparisons without adopting historical ratios as future bounds |
| 9. Status, commits, chunk checks, project pointers | Fixed | Symmetric disagreement labels, equal checkpoint schedules, separate reader timing, early chunk checks, and current entry points |

## Execution and resume behavior

The [runner](../../benchmarks/lazy_reader_workloads.py) now has two explicit provider modes.
Print its plan offline:

```sh
uv run python benchmarks/lazy_reader_workloads.py
```

Prepare both cohorts, freeze metadata and geometry, print estimates, and stop:

```sh
uv run python benchmarks/lazy_reader_workloads.py --execute data/lazy-reader-workloads/2026-09-18-approved
```

Run the frozen comparisons:

```sh
uv run python benchmarks/lazy_reader_workloads.py --extract data/lazy-reader-workloads/2026-09-18-approved
```

Repeat the appropriate command to resume the same owned directory.
Preflight reads boundary metadata, catalogs, and raster headers. It never calls an image-pixel reader.
Successful preparation phases require matching artifact hashes before reuse.
The run identity binds source code and prevents silent continuation with a different implementation.

Geometry selections now remain in each cohort directory. They contain positions and classes, not downloaded image values.
Temporary imagery directories remain separate and are deleted after use, including after errors and interruptions.
Preparation writes replacement databases in its temporary directory before promoting completed artifacts.
An interrupted preparation can therefore restart without treating an incomplete database as frozen evidence.

Extraction records launch intent before starting a worker and records the spawned process identity afterward.
A startup refusal consumes no attempt. It pauses scheduling rather than spending every remaining configuration.
A launched extraction is never repeated, regardless of success, interruption, or memory termination.
Resume skips those attempts and continues remaining configurations in their frozen order.
Offline validation can run again without reading imagery.

An exclusive run lock prevents concurrent supervisors.
A surviving worker blocks cleanup and resume. An unresolved launch also blocks automatic recovery rather than risking duplicate extraction.
That rare ambiguous launch needs inspection of the retained records. It is not silently treated as an unused attempt.

## Input selection and estimates

The [selector](../../tools/build_workload_manifests.py) queries counts before identifiers.
Requests exceeding 10,000 matching identifiers are subdivided, with a maximum depth of ten.
Identifiers are deduplicated and ranked in SQLite. Geometry requests still contain at most twenty source identifiers.
Requests are paced with a 0.2-second interval after the preceding request completes.
Unavailable subregions and geometry batches are recorded as shortages. They do not become empty successful responses.
The requested cohort counts remain mandatory. Insufficient valid candidates still stop preparation.

When one acquisition cannot cover a local group, the selector assigns the acquisition covering the most remaining complete lakes.
Coverage, cloud cover, sensing time, and acquisition identity break ties.
The assignment repeats until every lake has one acquisition. Individually uncovered lakes remain failures.
Distinct datastrips and native-grid observations remain separate. No mosaicking or partial-lake substitution is introduced.

Preflight now includes seven configuration estimates per cohort, product counts, memberships, block coverage, and lake-area distributions.
Windowed estimates scale measured workload bytes by lake-product memberships, following the accepted Stage 4 method.
Whole-image estimates use each reader's clean full-tile pilot measurements, excluding the partial Iliamna case.
Every estimate records the reference file and digest, formula, scale, and historical range.

The new cache, concurrency, process organization, and block scheduling differ from those historical runs.
Consequently, these are explicitly incompatible historical proxies, not matching-setting predictions or hard ceilings.
Improved B-lazy uses historical B-raster as a shared-reading proxy because optimized B-lazy has no measurements yet.
No runtime bound is inferred from the transfer scenarios.

## Reader and presentation corrections

The [readers](../../benchmarks/workload_readers.py) now verify the exact chunk partition before any lazy computation.
Expected chunk lengths include shorter native edge chunks. A shifted or differently sized partition fails before transfer.

Output databases use `synchronous=NORMAL` and the same checkpoint interval of 256 inserted records for every configuration.
This removes the differing per-lake and per-product commit schedules. A final checkpoint flushes the remainder.
Checkpoint time is recorded separately. A terminated attempt can lose its last uncommitted records and remains incomplete.
These databases retain compact audit signatures, not production pixel storage.

The presentation shows read-plus-extract time beside total extraction time.
The former excludes graph creation, selection loading, signature validation, and database checkpoint work.
Total extraction includes those activities. Startup and final validation remain separately recorded.

When complete outputs disagree, all involved configurations receive the label `differs`.
The first complete reader remains a comparison reference, not an assumed source of truth.
No disagreement identifies which reader is incorrect. Partial outputs remain incomplete regardless of equal or unequal signatures.

## Disagreements and qualifications

**Another mandatory approval gate is unnecessary.** The owner already authorized the plan's complete comparison without a transfer ceiling.
I implemented separate invocations because they improve reviewability and recovery.
The command split does not revoke that authorization. Material changes to workload scope or resource limits still require an owner decision.

**The available-memory reserve and RSS limit protect different conditions.** Bounding benchmark RSS does not reserve memory against other applications.
Therefore, the aggregate cap alone does not justify lowering the available-memory floor.
The approved limits remain unchanged. Lowering the floor is an optional owner decision, not a required defect correction.

**The dispersed whole-image runs remain useful and authorized.** Florida does not measure the whole-image reader comparison on the dispersed cohort's products and geometry.
The expected transfer disadvantage is plausible, but lake count alone does not establish its magnitude.
Removing those configurations would change the experiment rather than fix its implementation.
The preflight now exposes their contribution to the estimated transfer before extraction.

**Historical ratios and runtime estimates are not future bounds.** Inputs, lake areas, image coverage, reader settings, and network conditions differ.
The revised [plan](2026-09-18-lazy-reader-workload-plan.md#expectations-declared-before-execution) states conditional, directional expectations.
The proposed one-in-four swath-edge probability was not verified and is unnecessary to fix acquisition selection.
The implementation handles an empty common-acquisition intersection directly.

**The cache arithmetic does not establish eviction.** The review's 242 MiB band estimate is below the 256 MiB cache budget.
The saved [tile measurements](../../benchmarks/results/tile-extraction.json) record 1,024-square blocks, `uint16` values, and 121 blocks for a full 10 m band.
Repeated ranges remain a useful diagnostic. Their existence and cause must be measured rather than inferred from that arithmetic alone.

**The SQLite concern is broader than workflow A.** Before correction, B-raster, C-raster, the lazy control, and C-lazy also committed per lake and band.
Improved B-lazy committed per product and band. The new shared checkpoint rule addresses that actual asymmetry.

## Verification and limits

The repository check workflow passed in its required order:

- `uv sync --locked`: passed, 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 105 files already formatted.
- `uv run pytest -q`: 251 passed in 16.47 seconds, with 12,916 dependency deprecation warnings.

The inventory, sensor dataset, presentation renderer, and gap-report `--check` commands passed.
`git diff --check` passed. The offline runner and its command help printed without provider access.
`uv run --offline --with playwright python /private/tmp/check-s2-browser.py` passed at 1,280, 768, and 390 pixels.
Browser checks found no page overflow, JavaScript errors, or remote requests. The revised desktop table was also inspected visually.

New fixtures cover acquisition splitting, bounded identifier queries, shortage reporting, resume after startup refusal, and prevention of repeated launched attempts.
They also cover preparation integrity, seven transfer estimates, chunk-grid rejection, equal checkpoint counts, and symmetric disagreement labels.
Existing output-equality, native-class, memory-stop, cleanup, and datastrip tests remain in place.

No provider request, production imagery read, or benchmark timing attempt was performed for this review response.
Provider availability, actual cohort composition, performance benefits, and full-workload resource behavior remain unverified.
The approved memory limits and all fourteen configurations remain unchanged.
No files were staged, committed, pushed, or published. Earlier contributor changes and measured evidence remain intact.

Next step: review these corrections, then continue the already authorized preflight and comparisons when the approved resource conditions are available.
