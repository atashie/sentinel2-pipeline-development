# Prototyping tab reordered answer-first, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented and checked. Awaiting owner review.

The whole-page review found the Prototyping tab accurate but long. It showed about 5,100 words by default, with method detail and caveats before the main result.
The owner chose the answer-first order and one factual cost line in the takeaways. No measurement, estimate, or evidence file changed.

## New order

| Section | Content | Formerly |
|---|---|---|
| 00 High level takeaways | Unchanged, plus one bound cost line and renumbered links | 00 |
| 01 What we tested | Processing outline, a nine-recipe grid, terms, test inputs, collapsed reader details, and the test cohorts | 01 and the cohort part of 06 |
| 02 Main comparison | The larger-workload tables first. Settings, timing boundaries, and reruns move into collapsed method notes | 05 |
| 03 AWS cost estimates | Unchanged except section numbers | 07 |
| 04 Earlier experiments | The pilot summary, then collapsed panels 04.1 to 04.3 and the pilot details | 02, 03, 04, and the pilot part of 06 |

Measured by the rendered page, Prototyping now shows about 2,650 words by default and holds about 4,500 in collapsed panels.

## Other changes

- The grid replaces the reader-code box, the three "reader across workflows" summaries, and the comparison-question table. The reader paragraphs moved into the collapsed reader details.
- The B2 settings note appears once, in the section 02 method notes. Sections 04.2 and 04.3 no longer repeat it.
- The renderer emits the sleep-rerun note as its own marker, placed in the method notes. The table caption points to those notes.
- The takeaway cost line reads the national B1 and B3 backfills and the S3 charge from the estimates.
- Discovery's workload box and closing line now link to the Prototyping results.
- Every former marker, element ID, and evidence link remains. Hash links open collapsed panels, so older links to `#stage-2`, `#stage-3`, `#stage-4`, and `#pilot-why` still work.

## Tests

- The cost page test now expects "03 / AWS cost estimates" and the takeaway cost line.
- A new test checks the chapter order and that 04.1 to 04.3 open from collapsed panels.
- The rerun-note assertions moved to the new `workload_rerun_note` function. Their expected text is unchanged.

## Deferred

- The sensor tables still carry provenance footnotes. They sit in a collapsed panel in Discovery.
- The measurement source notes still repeat the laptop description in each section.

## Verification

- `render_options.py --check` passes, and the rendered page has no unfilled marker.
- The review-layer check reports up to date.
- `/check`: ruff passed, format passed, 323 tests passed.
- Headless Chrome rendered the tab at 1,280 and 390 pixels wide. A link to `#stage-3` opened its panel.

## Proposed next step

Owner review. Not started.
