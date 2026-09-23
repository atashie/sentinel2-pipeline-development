# Whole-page accuracy fixes, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented and checked. Awaiting owner review.

Claude Code reviewed the whole [assessment page](../s2-options.html) for technical accuracy in the session.
One agent recomputed about 170 numbers typed into the page. All matched their evidence.
A second agent checked external facts against primary pages. The owner authorized the accuracy fixes and the restored NHD note. Flow and readability changes are deferred.

## Dispositions

| Finding | Disposition | Where |
|---|---|---|
| Section 00 said operating costs remain open | Fixed. It points to section 07 | Template |
| The intro said "thousands of lakes" while section 07 prices 5,000,000 | Fixed. "U.S. lakes, ponds, and reservoirs" | Template |
| "30 percent less" held only for reader 1 | Fixed. Reader 3's separate-lake workflow took 11 percent more | Template |
| The version 2 and 3 sentence was reversed | Fixed | Template |
| "One acquisition" conflicted with the repository's definition | Fixed. "One satellite pass" | Template |
| ESA reprocessing dates were out of date | Fixed with evidence C1. Also added to G8 and the archive-gap paragraph | I-08, G8, template |
| The 2017 producer was overstated | Fixed from the issue's own text | I-17 |
| Readers "partially apply" the offset had no evidence | Fixed from the issue's own evidence | I-06 |
| "None promises exactly once" was too broad | Fixed. The line states retries and rewrite-safe outputs | I-21 |
| The tile-overlap qualifier was missing | Fixed with evidence C2 | I-04, G11 |
| The swath-edge mask is coarser only than the 10 m bands | Fixed with evidence C3 | I-11 |
| The Sentinel-2A extension campaign was missing | Fixed with evidence C4 | I-25, Q7 |
| "Sinergise wrote its readme" was an inference | Fixed with evidence C6 | Template |
| The band note named one of three tied bands | Fixed. It now lists B08, B10, and B11 | Renderer |
| Two ponds without rows and the 20-point survey lacked context | Fixed | Template |
| "1092" lacked a thousands separator | Fixed | Renderer |
| NHD note | Restored with corrected wording from C5 | Template |

The [check record](../assessment-checks/presentation-review-sources.json) holds evidence C1 to C6. A separate agent on a different model confirmed five claims and corrected one.
The correction removed "which replaces both" from the NHD wording. No USGS page says the 3D Hydrography Program replaces NHD.

## Changed files

- [Template](../../tools/s2-options.template.html) and the regenerated page.
- [Inventory](../options-inventory.json): issue `plain` lines for I-04, I-06, I-08, I-11, I-17, I-21, and I-25, and the I-21 title. No bound claim changed.
- [Best practices](../s2-best-practices.md): G8, G11, Q7, and sources S15 to S17.
- [Renderer](../../tools/render_options.py): tied bands in the variant note, and thousands separators in the cohort line.
- Tests: a new variant-note test.
  - The archive-names test now asserts "hosted on a Sentinel Hub domain" in place of "Sinergise". The page no longer names Sinergise, because authorship was an inference.
  - The NHD assertion now requires the restored note.
- [Check index](../assessment-checks/README.md).

## Limits

- Bound inventory claim notes still call the L1C and L2A readmes "the Sinergise readme". Changing them needs new check records.
- SentiWiki also describes a swath-edge correction in baseline 05.13. It was not drafted or checked here.
- Whether the Sentinel-2A campaign adds acquisitions over the contiguous United States is not established.

## Verification

- `collate_checks.py --check`, `collate_sensor_bands.py --check`, `gap_report.py --check`, and `render_options.py --check` pass.
- The review-layer check reports up to date.
- `/check`: ruff passed, format passed, 320 tests passed.

## Proposed next step

Owner review, then the flow and readability restructure from the same review. Not started.
