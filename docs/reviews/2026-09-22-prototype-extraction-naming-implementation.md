# Prototyping workflow and reader names, 2026-09-22

Author: Codex, directed by the repository owner.
Status: implemented for owner review.

The owner authorized implementing the [naming proposal](2026-09-22-prototype-extraction-naming-proposal.md), including its five refinements.
This step updates the entire [Prototyping tab](../s2-options.html#prototyping) and its renderer.
It introduces no measurement, benchmark-source change, or production selection.

## Changes

Workflow letters identify processing order and reading extent.
Reader numbers identify direct raster reads, large-chunk lazy reads, and source-block lazy reads.
Pixel selection remains a separate qualifier where it varies.
Codes identify recipes, not performance ranks, implementation versions, or identical experimental settings.

- Section 01 retains the workflow diagram and adds three parallel reader paths for two lakes sharing a source block.
- The reader explanation defines windows, TIFF blocks, array chunks, reuse, and behavior under workflows A, B, and C.
- Section 02 separates three A1 selection variants from the A1/A2 prepared-mask reader comparison.
- Sections 03 and 04 use combined codes while retaining historical process arrangements, measurement bases, exclusions, and timing limits.
- Section 05 compares B1, B2, and B3 explicitly, alongside A1, A3, C1, and C3 in both cohorts.
- Section 06 separates the original pilot from the two larger cohorts.
- Section 07 distinguishes workflow and reader choices, elapsed time, CPU work, requests, requested bytes, and RAM spikes.

The [renderer](../../tools/render_options.py) centralizes reader names and mappings from frozen result keys.
Workflow cells link to reader definitions. Reader names remain visible in the adjacent column.
Table headers, captions, navigation, expanded results, and conclusions use the same vocabulary.
Workflow colors remain attached to A, B, and C.
The reader paths stack vertically on phones. Table regions support horizontal scrolling and keyboard focus.

## Dispositions of the five refinements

| Finding | Disposition | Implemented treatment |
|---|---|---|
| Batch size comes from the thread setting | Fixed | Describe bounded batching generally, with a maximum of two blocks under the measured two-thread setting |
| A2 and B2 differ in chunk origin | Fixed | Explain lake-window versus full-image graphs and shifting chunk boundaries for identical native pixels |
| C3 aligns chunks without bounded batching | Fixed, with the agreed qualification | Describe complete-band computation. C1/C3 changes the reading stack and does not isolate alignment’s performance effect |
| B3’s transfer estimate borrows B1 measurements | Fixed | Label the historical B1 proxy separately from measured B3 bytes. Preserve the corresponding A3/A2 and C3/C2 distinctions |
| B2 settings changed, and C’s overview was stale | Fixed | Put thread and cache settings beside each comparison. Link C to its many-tile measurements in section 05 |

The historical transfer disclosure links the original preflight, including reference digests, formulas, and settings.
It does not relabel proxy estimates as measured performance or transfer bounds.
Earlier B2 observations remain qualified by four threads and a 512 MiB cache.
Section 05’s B2 uses two threads and a 256 MiB cache.

The [prior timing review response](2026-09-22-sleep-rerun-review-response.md) remains in force.
Total extraction remains the cross-reader comparison column.
The component-timing caveat explains where direct and lazy readers charge file opens.
The two retained original rows remain marked, with older catalog setup explicitly attributed to dispersed A3.
Historical C2 evidence remains acknowledged without adding an unmatched C2/C3 performance comparison.

## Verification

The existing renderer assertions now expect the agreed names.
A regression test checks that historical lazy keys identify reader 2 while later lazy keys identify reader 3, except the explicit B2 control.
Distinct fixture timings catch labels attached to the wrong rows, even when input rows arrive in a different order.
Existing tests retain incomplete-result, sleep-interruption, agreement, and historical-baseline checks.

Browser verification used `uv run --offline --with playwright python /private/tmp/review-prototype-layouts.py`.
At widths of 1,280, 768, and 390 pixels:

- All seven sections and eleven tables remain available, including expanded results.
- All fourteen larger-workload rows remain complete, with two retained-original labels and two explicitly scoped B2 controls.
- All 464 compared data cells retain their previous contents, including measured values, statuses, and historical qualifications.
- Reader links resolve, scroll their definitions below the sticky navigation, and keep the Prototyping tab active.
- No page overflow, JavaScript error, or external network request occurred.

Desktop and phone screenshots were inspected for reader flow and result-table readability.
Browser artifacts remain local under `data/reviews/2026-09-22-prototype-extraction-naming/presentation`.
SHA-256 checks confirm all thirteen result JSON files are unchanged.
All twelve source digests still match the frozen rerun manifest.

The repository check workflow passed:

- `uv sync --locked`: 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, with 120 files already formatted.
- `uv run pytest -q`: 275 passed in 29.74 seconds, with 13,000 existing dependency deprecation warnings.

The focused renderer suite passed: 11 tests in 0.02 seconds.
All four artifact checks passed through `uv run python tools/` with `--check`.
These cover `collate_checks.py`, `collate_sensor_bands.py`, `render_options.py`, and `gap_report.py`.
`git diff --check` passed.

The final browser harness initially checked link placement before the existing smooth-scroll animation finished.
Waiting for the destination to settle resolved that harness failure at all three widths.
The page retains its existing navigation spacing and scroll behavior.

## Limits and proposed next step

These changes explain existing experiments. They do not establish isolated causes for timing differences or select a production recipe.
Scientific validation, additional instrumentation, and new provider runs remain separate work.
Review the revised presentation and naming conventions before another implementation step.
Nothing was staged, committed, pushed, or published.
