# Prototyping tab rebuilt for both options, 2026-10-15

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented, with Codex's accuracy review integrated. Awaiting the owner's review by hand.

## For the owner

- The [Prototyping tab](../s2-options.html#prototype-takeaways) now reports both standalone options from Phase C.
- It has six sections: takeaways, what we tested, B1 and B3 on each option, costs per option, pixel checks, and the Level-2A reference series.
- Every new number comes from a committed result file or the generated cost estimates. The renderer refuses to build the page when a result breaks one of the checks listed under renderer refusals.
- The collapsed Level-2A panels are gone. One four-row table replaces them, and the records keep every number.
- Five choices below are this record's own, listed for correction.
- Codex's adversarial accuracy review found nine flaws. This step fixes all nine, [below](#codex-accuracy-review).

## Step and authorization

After the T7 cycle the owner wrote "then I'll compact memory before we start rebuilding the prototyping tab". After the compaction the owner wrote:

> "please start with the prototyping tab rebuild"

The step follows the Prototyping tab plan in the [replan record](2026-10-13-acolite-first-replan.md#prototyping-tab) and the work-plan item for Phase C. It contacts no provider and reads no pixel.
Acceptance: every new number bound to a result or estimate file, tests updated, generator checks and `/check` passing, and this record.
Deferred: probe T8, any Discovery-tab change, any cost-model change, and any new measurement.

After the first version the owner wrote:

> "have codex run an adversarial review, focussing on flaws in technical accuracy. Integrate all of their findings that you agree with, then run one final review of the document for general readability (using /plain-english and converting british spelling to american spelling). then commit and push. Thereafter I will review by hand"

## Choices this record made

1. **A new section 04, pixel checks.** The replan rewrites the takeaways from T4 to T7 but names no section for them. The takeaways need a home on the page. The section follows the owner's results format: brief definitions, then one table.
2. **B1 and B3 only in the cost table.** A1 has no larger-workload run on the primary product, so ACOLITE only has no A1 estimate. One line names A1's Sen2Cor-only estimate and its cap.
3. **B1 and B3 only in the main comparison.** The seven-recipe Level-2A table and its "Read + extract" column left the page. The seven-recipe headline is a row of the reference table.
4. **The pilot summary moved to section 01.** The pilot card and the checked NHD note now sit with the test cohorts. The overlap meters and the pilot case table left with the panels.
5. **No "estimates revised" date.** `inputs.json` still carries `revision_date` 2026-09-23, while the option inputs changed on 2026-10-14. The source note links the [per-option record](2026-10-14-phase-c-cost-options.md) instead. Changing the field would change the input digest and regenerate the estimates, a cost-model step.

## What changed

| Area | Change |
|---|---|
| Section 00 | Rewritten. Shared windows still lead. It gives Florida bytes and requests on both options, and the B1 and B3 cards on ACOLITE files. It adds the cohorts' product counts, three pixel-check lines, and both options' backfill and storage |
| Section 01 | The workflow chart names each option's grids and catalog. The output step marks records primary or overlap, decision 0010. The recipe grid points to sections 02, 03, and 05. The inputs line names each option's five files |
| Section 02 | One table: B1 and B3 on each option, grouped by cohort, with lakes and products, total extraction, CPU, requests, bytes, peak RAM, and run date. Method notes cover settings, selection, layers, and CPU per megabyte |
| Section 03 | One table: B1 and B3 on each option under each workload, with each option's storage in the group heading. Definitions give each option's acquisition rate |
| Section 04 | New. Three definitions and one table of five checks from probes T4, T5, and T7, with a note that neither option is a reference |
| Section 05 | One table replaces the collapsed panels: stages 2 to 4 and the larger workloads, each with its question, headline, and record. Rows keep the ids `stage-2` to `stage-4`, so earlier links resolve |
| Footer | Updated to 2026-10-15 |
| [render_options.py](../../tools/render_options.py) | New: `option_workloads`, `option_workload_rows`, `option_workload_markers`, `percent_range`, `workload_dates`, and `pixel_check_markers`. Rewritten for both options: `cost_table_rows`, `cost_estimates`, and `cost_markers` |
| Renderer, removed | The row builders of the removed tables, their helpers, and five label constants. `cross_tile_markers` keeps the stage 4 headline numbers, now in whole percents |
| Renderer refusals | Incomplete, unequal, or duplicate runs. Level-2A runs without one sleep audit row, or that overlapped laptop sleep. B1 and B3 no longer splitting as stated. Florida no longer faster on fewer bytes. ACOLITE files in Florida no longer taking fewer bytes and more requests. A T4 class masked by the processor. A changed T4 no-data exception. A T5 band that agrees. Changed T7 pooled exceptions. The largest T7 offset leaving B01. An estimate file older than any input it records, or holding the wrong option |
| [test_render_options.py](../../tests/test_render_options.py) | Tests of removed functions removed. 20 fixture tests cover the new functions, the refusals, and the cost table for both options |
| [test_presentation.py](../../tests/test_presentation.py) | The cost test checks both options. A new test checks the probe numbers against the result files. The structure test checks six sections and the reference rows |
| Documents | [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), [tools/README.md](../../tools/README.md), the [work plan](../work-plan.md), the [reviews index](README.md), and the inventory's next steps |

## Where the numbers come from

| Page statement | Source |
|---|---|
| Florida: 40 percent of Level-2A's bytes, 8 to 9 percent more requests | `workloads.florida.comparisons` in [aqr-workloads.json](../../benchmarks/results/aqr-workloads.json) against `cohorts.florida.comparisons` in [lazy-reader-workloads.json](../../benchmarks/results/lazy-reader-workloads.json) |
| Section 02 rows, B1 and B3 CPU, elapsed shares, and RAM | The same runs: `extraction_seconds`, `cpu`, `io`, and `supervision` |
| 93 lakes, 7 dropped, 112 products on 111 tiles, 98 of 112 matching | `workloads.dispersed` in aqr-workloads.json |
| 59 scenes, flag shares 35, 77, and 92, no flag 58, 20, and 7, cloud 7, shadow 74 | `summary.shares` in [aqr-validity.json](../../benchmarks/results/aqr-validity.json). The non-water flag is bit `swir` |
| No-data counts and the two-pixel exception | `summary.no_data_diagnostic` in aqr-validity.json |
| 25 to 81 percent beyond 0.005 | `summary.pooled.both_clear_water.interior` in [aqr-pairs.json](../../benchmarks/results/aqr-pairs.json) |
| Pooled exceptions, 70 and 36 percent, 8 pairs | `summary.pooled` and `diagnostics.relative_offsets` in [aqr-overlap.json](../../benchmarks/results/aqr-overlap.json) |
| Costs, storage, operations | [estimates-acolite-only.json](../cost-analysis/estimates-acolite-only.json) and [estimates.json](../cost-analysis/estimates.json), central case |
| 98.2 and 174.2 acquisitions, 55 percent | `survey_rate_evidence` in each estimate file |
| Reference dates and stage 4 numbers | `measured_at` and `summary` of the stage 2 to 4 results, run dates of the larger workloads |
| Stage 2, stage 3, and larger-workload headlines | Copied from the reviewed page text of 2026-09-23 |

The section 02 times use `extraction_seconds`, the "Total extraction" of the earlier page. [Finding 37](../measurements.md#37-readers-b1-and-b3-read-about-40-percent-of-level-2as-bytes-at-higher-cpu-per-requested-megabyte) used `elapsed_seconds`, so two times differ by 0.1 s.
The T4 cloud share includes the Lake Washington scene of 2025-11-02, whose classification came from the other datastrip. Finding 33 gives 7.4 percent without it. Both round to the page's "about 7".

## Codex accuracy review

Codex ran read-only on the first version, with no network access, and checked claims against the result files. It confirmed every number in the section 02 and section 03 tables.
It reported nine flaws, each marked verified. Claude Code checked each against the sources and agrees with all nine.

| # | Finding | Evidence checked | Disposition |
|---|---|---|---|
| 1 | The page described B1 as reading each lake's rectangle | `raster_asset` in [workload_readers.py](../../benchmarks/workload_readers.py) reads one window per stored block a lake touches. The result's `limitations` say so | Fixed. The B1 card, reader key, section 02 definition, and illustration legend now describe block reads |
| 2 | The page said only B1 and B3 ran on ACOLITE files | `stage2` to `stage4` in [aqr-workloads.json](../../benchmarks/results/aqr-workloads.json) replay stages 2 to 4, finding 36 | Fixed. Section 01 limits the statement to the larger workloads. Section 05 says the ACOLITE tests repeated stages 2 to 4. The A1 notes say "no larger-workload run" |
| 3 | The validity headline claimed every pixel holds a value | `summary.no_data_diagnostic` keeps counts only. Finding 30 says counts cannot place the two B04 values | Fixed. The takeaway and table report the count match and its exception. The renderer refuses any other exception pattern |
| 4 | "Same pixels" hid resampling and the clear-water rule | Rules `P3_resampling` and `P6_strata` in [aqr-pairs.json](../../benchmarks/results/aqr-pairs.json) | Fixed. The page says "same locations" and "pixel observations", states the 20 m comparison grid, and defines clear water |
| 5 | The overlap result omitted the 90 percent agreement rule | Rule `O7_tile_agreement` in [aqr-overlap.json](../../benchmarks/results/aqr-overlap.json) and rule `P7_disagreement` of T5 | Fixed. The table caption defines agreement for both checks |
| 6 | Refusals missed the cross-option byte claim and accepted a missing sleep audit | Tripled ACOLITE bytes still rendered. `audit=None` passed | Fixed. New refusals and fixture tests for both |
| 7 | The renderer checked cost estimates against their inputs and model only | Each estimate also records evidence, cohort-block, survey, and, for ACOLITE only, coverage digests | Fixed. The renderer checks every recorded digest, with tests for stale evidence and coverage |
| 8 | The page gave compression as the cause of higher CPU per megabyte | [Finding 37](../measurements.md#37-readers-b1-and-b3-read-about-40-percent-of-level-2as-bytes-at-higher-cpu-per-requested-megabyte) calls it the likely cause | Fixed. The method note states the observation, then the likely cause |
| 9 | The README named stage 1 in the reference table | The table holds stages 2 to 4 and the larger workloads | Fixed |

Finding 35 and the T5 heading in [measurements.md](../measurements.md) still say "same pixels". They are reviewed findings, and the page links to the heading's anchor. This step left them unchanged.

## Verification

| Command | Outcome |
|---|---|
| `uv run python tools/render_options.py --check` | The page matches its template, evidence inputs, and map assets |
| `uv run python tools/collate_checks.py --check` and `collate_sensor_bands.py --check` | Both match their records |
| `uv run python tools/gap_report.py --check` | Matches the survey results |
| `inject.py ... --check` with `tools/review-layer.json` | Up to date. The comment block was not edited |
| `uv run python tools/estimate_aws_costs.py --check` | Matches, both options |
| `tools/backtest_source_bytes.py --check` and `tools/backtest_aqr_source_bytes.py --check` | Both match saved local evidence |
| `/check`: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest -q` | All passed: 175 files formatted, 406 tests passed in 39.5 s |

A script split the rendered tab into sentences. Only table group headings exceed 25 words. It found no semicolon and no banned word.
Headless Chromium screenshots of the tab at 1,280 pixels wide showed every table within the page width. In the cost table, the option label wraps to two lines.

## Limits

- The owner has not read the new text. Codex read the first version, and this step integrates its findings. AI review is not owner approval.
- The section 02 note warns that elapsed times compare only roughly across options. The Level-2A runs date from 2026-09-21 and the product runs from 2026-10-14.
- The pixel-check rows state headline results. The findings hold the subsets, tolerances, and limits.
- Screenshots covered one desktop width. Narrow screens use the existing responsive styles and horizontal table scrolling.
- Findings of the 2026-09-23 [final accuracy review](2026-09-23-claude-final-page-accuracy-review.md) that concern removed Prototyping text no longer apply. This step did not revisit the rest.

## Dispositions

| Prior item | Disposition |
|---|---|
| Work plan: Prototyping tab rebuilt from the primary product | Fixed |
| Replan, section 00 rewritten from T4 to T7 | Fixed |
| Replan, section 01 grid and cohorts kept with the source changed | Fixed, with both options named |
| Replan, section 02 rebuilt from T6's B1 and B3 | Fixed |
| Replan, section 03 rebuilt from the per-option model | Fixed |
| Replan, section 04 pared to one Level-2A table | Fixed, now section 05 |
| [Cost record](2026-10-14-phase-c-cost-options.md): costs from the primary product on the tab | Fixed |
| [Phase B validation](2026-10-13-phase-b-claim-validation.md): banner labeling the tab as the Level-2A series | Superseded. The intro names both options and the reference series |

## Proposed next step

The owner reviews the rebuilt tab by hand.
Probe T8, retention, remains. It reads metadata only and needs its own authorization. This record does not start it.
