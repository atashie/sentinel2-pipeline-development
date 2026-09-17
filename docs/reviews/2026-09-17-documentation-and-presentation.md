# Documentation and presentation update, 2026-09-17

Author: Codex. Status: ready for owner and Claude Code review after the checks recorded below.

The owner accepted the [Stage 4 response](2026-09-16-codex-stage-4-review-response.md) and authorized this documentation and presentation update.
The [page](../s2-options.html) now includes corrected Stage 4 findings and clearly labels Prototyping as partial.
No provider script ran. No new imagery was downloaded or read.
The benchmark results remain frozen. No production workflow or additional workload is selected.

## Changes

- Updated current status, the work plan, inventory summaries, renderer documentation, and dated review follow-ups.
- Added inventory finding F-26. Updated the cost and cross-tile consequences without changing bound source claims.
- Reworked the presentation around practical findings and their limits. Detailed benchmark tables remain available in expandable sections.
- Retained four tabs, the corrected archive-history table, its explicitly inferred explanation, and the six local satellite views.
- Corrected native resolutions, HLS grid wording, fallback lossiness, partial tile coverage, and quality-grid assumptions.
- Added Stage 4 workload comparisons, extent-overlap bars, validity limits, and unresolved primary roles.
- Generated Stage 4 headline ratios and table cells from the frozen result. Added its digest to the HTML provenance comment.
- Distinguished whole-workload timing from earlier per-file timers. Binary memory quantities use GiB or MiB.
- Improved chapter labels, keyboard access to scrollable tables, and links into another tab or collapsed section.

Detailed benchmark numbers remain in [measurements.md](../measurements.md) and its linked result files.
The inventory summarizes implications. The presentation explains their relevance to colleagues.
Dated implementation records preserve their historical scope, with follow-up links identifying the current state.

## Dispositions of remaining Stage 3 findings

| Finding | Severity | Disposition | Location and evidence |
|---|---|---|---|
| Largest outlier has recorded transport failures | Medium | Fixed | Finding 22 now names the timeouts and additional requested bytes documented by the [rerun review](2026-09-16-codex-stage-3-rerun-review.md) |
| Conditional byte arithmetic became a lake-count rule | Medium | Fixed | Stage 3 presentation and inventory retain an explicitly conditional estimate. They make no general timing or monetary recommendation |
| Status overstated spatial coverage | Medium | Fixed | Status distinguishes Stage 3’s selected tile portions from Stage 4’s union coverage. Neither establishes usable measurements everywhere |
| Numeric descriptions and cache units | Low | Fixed | Finding 20 uses the verified extraction maximum. The run record qualifies memory changes by method and aggregation. The page uses 512 MiB |

These corrections use existing evidence. No rerun was needed.

## Stage 4 acceptance and limits

The accepted response qualifies footprint precision, split-product identity, band no-data, SCL interpretation, slow-run causes, and shape comparisons.
The page carries these distinctions without implying that scientific agreement has been tested.
The measured implementation remains version 2. Version 3 changes future selection and has fixture coverage only.
Accepting the response does not resolve the primary-tile rule. Ambiguous roles remain open.

## Source checks

Separate research and checking agents independently opened primary sensor documentation on 2026-09-17.
Researcher: `/root/sensor_check`. Checker: `/root/sensor_independent`. Both used separate contexts and compared their conclusions.
Their confirmed wording and qualifications are appended to the [presentation source record](../assessment-checks/discovery-presentation-sources.json).

- Copernicus establishes native band groups, Level-2A’s omission of B10, and nominal two-satellite revisit.
- USGS establishes Landsat band sampling and the combined Landsat 8/9 repeat interval.
- NASA establishes HLS’s shared grid and processing adjustments.

The page avoids claims about the current satellite fleet or guaranteed publication latency.
Archive coverage remains the dated survey evidence. No new archive survey was performed.

## Verification

The repository [check workflow](../../.claude/skills/check/SKILL.md) passed in order.
Dependency synchronization, lint, and formatting passed. `uv run pytest -q`: 200 passed in 26.61 seconds, with existing library deprecation warnings.
The first lint pass found three long renderer lines. Formatting was applied, then lint and formatting checks passed.
Four added fixture cases cover workload medians, excluded repetitions, absent clean results, and refusal of incomplete or unequal headline evidence.
The memory-label fixture now expects binary units. No extraction expectations were changed.

The inventory collator, presentation renderer, and gap-report `--check` commands passed. `git diff --check` passed.
Stage 3, Stage 4, and smoke result digests match the previously reviewed values. No benchmark result changed.
HTML tags balance, local links and Markdown anchors resolve, and the page contains no internal issue or decision identifiers.
A prose audit found no overlong presentation sentences, semicolons, or advisory wording prohibited by the document rules.

Cached Chromium checked widths of 1280, 768, and 390 pixels.
All four tabs, arrow-key navigation, both six-view selectors, and links into other tabs or collapsed sections passed.
The browser recorded no JavaScript errors, external requests, or page overflow.
Visual inspection covered the archive explanation, Stage 4 comparison, overlap graphic, and mobile sensor section.
The first browser pass exposed a closed archive-history target. Navigation now opens the target itself as well as collapsed ancestors.
The diagnostic also waits for smooth scrolling to reach its target before checking position.
Screenshots and browser results remain under `/private/tmp/s2-presentation-check/`, outside the repository.

## Proposed next step

Review the updated presentation with Claude Code.
Then agree the bounded Stage 5 scientific checks, including offset handling, per-band validity, and matched-location comparisons across overlapping tiles.
Stage 5, another provider run, and publication require separate owner authorization.
