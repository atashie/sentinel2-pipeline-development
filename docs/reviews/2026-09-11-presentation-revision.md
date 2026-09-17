# Discovery presentation revised, 2026-09-11

Implementer: Claude Code (AI coding agent), directed by the repository owner, who chose Claude Code to implement the revision.
This step applies findings 1 to 8 of the [review of the same date](2026-09-11-presentation-review.md). The owner's ten answers in that review are the specification.
Baseline: commit `943bb1b` plus the uncommitted changes of 2026-09-10 and 2026-09-11. Nothing was committed.

## What changed

| Finding | Change | Where |
|---|---|---|
| 1. Sensor rationale | Section 01 rewritten. What the model reads from the bands, a six-row comparison of the two sensors, the pixel-size figure, a note on 30 m Sentinel-2, and the choice. Landsat is tagged as the other public option, not used for now | [Template](../../tools/s2-options.template.html), section `the-data` |
| 2. Archive tradeoff | Section 02 rewritten. A route figure from catalog to files to store, neutral archive cards, a measured monthly coverage strip, and a two-plan table with the same four rows for both plans. The JPEG 2000 bucket stays absent | Template section `aws`, [renderer](../../tools/render_options.py) |
| 3. Risk bullets | Every inventory issue's `plain` line appears once, as a bullet under one of the six risk categories or in the cost list. The mapping lives in the renderer, which fails if an issue is unplaced. The JPEG 2000 issue is off the page by direction. A test checks the page against the inventory | Renderer `RISK_GROUPS`, `COST_ITEMS`, [test](../../tests/test_presentation.py) |
| 4. Illustrations | Three added: the route, one stored record, and the processing-version timeline. The coverage strip is drawn from the report, so it stays measured | Template sections `aws`, `risks`, `processing` |
| 5. Effort labels | Low, medium, high, or depends, one per step. Reuse is stated in the group headings | Template section `processing` |
| 6. Index maps | The builder keeps negative inputs, excludes only zero denominators, and clips each index to the legend. Maps rebuilt from the cached arrays. Captions explain the noise floor and the gray dark-area class | [Builder](../../tools/build_discovery_maps.py), [provenance](../assets/discovery/provenance.json) |
| 7. Vercel | Static configuration and a hosting note, following the weather repository. The README points to it. A test checks the rewrite target | [vercel.json](../vercel.json), [vercel-hosting.md](../vercel-hosting.md) |
| 8. Housekeeping | The 2026-09-10 HTML rebuild review moved to `docs/archive/`. Step 3c in the work plan collapsed to one line. The format document describes the markers. The sources record's limitation updated. The hash handler tolerates a refused `replaceState` | [work-plan.md](../work-plan.md), [assessment-data-format.md](../assessment-data-format.md) |

All seven decisions the owner listed now have a figure.

- AWS and Earth Search as the route: the route figure.
- Collection 1 first, the older archive as fallback: the archive cards and the two-plan table.
- Raw bands and flags, no derived index: the stored record card.
- Three pixel classes per resolution: the shoreline drawing.
- Never mosaic, every tile kept with a primary marker: the overlap drawing.
- Key by tile, time, and processing version: the version timeline.
- Start at 2021 with a measured survey: the monthly coverage strip.

The report gained a `coverage_by_month` list, computed by [gap_report.py](../../tools/gap_report.py) from the two surveys. The findings did not change. The report's digest in the page footer did.

## Evidence

- Map rebuild: every view now has a valid fraction of 0.978, recorded in the provenance record. Before the fix the two index views had 0.908.
- The five sensor facts added to section 01 carry independent check verdicts in the [sources record](../assessment-checks/discovery-presentation-sources.json), four confirmed and one corrected in wording.
- The band-to-signal statements in section 01 are labeled project rationale on the page. They are not checked claims.

## Checks

| Check | Outcome |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass, 41 files formatted |
| `uv run pytest -q` | 60 passed, including the new inventory-coverage and Vercel tests |
| `collate_checks.py --check`, `render_options.py --check`, `gap_report.py --check` | All three pass |
| Headless Chromium, Playwright build 1234, at 1440 px and 390 px | Every section, figure, and table renders. No horizontal overflow at 390 px |
| Prose audit of the rendered text | No sentence over 25 words outside navigation strings and the record card. No "should", no semicolon, no internal ID, no person's name. No marker left unfilled |

## Limits

- Tab switching, map switching, and deep links were not exercised in a browser during this step. The only script change is a try block around one call. Codex's browser checks of 2026-09-11 covered the rest.
- The Vercel configuration is untested against a live deployment. The first deployment follows the hosting note after the owner authorizes a push.
- Effort labels remain planning judgments. Timings belong to Prototyping.
- Which Sentinel-2 product the model was built on is unknown. Prototyping asks the modeling colleagues.

## Correction after owner review, 2026-09-11

The owner reviewed the page and found the pixel-size figure in section 01 wrong. The nine 10 m cells were drawn as a water square with the land shape painted across them. One cell showed two colors. A sensor reports one value per pixel.

Each cell now has one flat color, mixed from the land fraction that the shoreline encloses in that cell. The 30 m sample is one cell at the mean mix. The shoreline is drawn as a line over both grids for reference, and the caption says so. The fractions come from rasterizing the same boundary path, so the colors match the line.

| Row | Left cell | Middle cell | Right cell |
|---|---|---|---|
| Top | 1.00 land | 0.79 land | 0.03 land |
| Middle | 1.00 land | 0.34 land | 0.00 land |
| Bottom | 0.41 land | 0.00 land | 0.00 land |

The whole square is 0.40 land. The page was re-rendered. Lint, format, 61 tests, and the three generator checks passed again. A headless Chromium screenshot at 1440 px confirmed the figure. The other shoreline diagram, in section 03, already used flat class colors with the lake edge drawn on top, so it was left alone.

## Dispositions

| Review finding | Disposition |
|---|---|
| 1 to 8 | Fixed, as listed above |
| 9, what Codex did well | No change needed |

## Proposed next step

Owner review of the page. After acceptance: authorization to commit, the first Vercel deployment, the fill-policy decision, and prototyping. No commit, push, or deployment was performed.
