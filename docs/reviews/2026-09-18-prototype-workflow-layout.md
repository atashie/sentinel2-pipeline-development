# Prototype workflow comparisons, 2026-09-18

Implementer: Codex, directed by the repository owner.

Scope: reorganize the [Prototype tab](../s2-options.html) around processing choices and their measured outcomes.
The owner authorized implementation after reviewing the proposed structure and the neighboring weather presentation.

## Changes

- Added a processing diagram with reusable pixel preparation, image discovery, three alternative reading workflows, extraction output, and untested storage.
- Used the same workflow names and colors in the diagram and result tables.
- Separated pixel selection, processing order, reading extent, and reader implementation.
- Introduced each comparison with its question, changed factors, fixed inputs, and measured outcomes.
- Made the primary comparison tables visible, with separate columns for time, requests, requested bytes, and memory where available.
- Moved detailed test cases after the results and consolidated remaining decisions at the end.
- Kept detailed measurements, settings, and review history in expandable panels.
- Reduced introductory typography and spacing, with responsive workflow cards and horizontally scrollable tables.

The [template](../../tools/s2-options.template.html) owns the layout and wording.
The [renderer](../../tools/render_options.py) reads the existing frozen results.
The diagram uses HTML and CSS, with no additional library or external request.
Existing fragment links remain available, including the historical identifiers for the three extraction comparisons.

## Evidence and interpretation

The visible pixel-selection table shows the smallest ponds and larger reference lakes.
Each method has its own resource measurements, rather than borrowing the raster method's bytes or memory.
The detailed table retains all six size groups.
The simple clip remains explicitly different because it omits nearby-land context and selects boundary pixels differently.

The shared-image example uses Tahoe's six lakes, all inside its selected tile, with a matching individual-lake baseline.
It includes a large reference lake and smaller lakes. It is labeled an example, not a representative workload or average.
The other eight tiles retain the same columns in an expandable table.
Separate processes and repeated file openings within one process remain distinct alternatives within lake-by-lake processing.

The multiple-tile table preserves the four original combinations and their workload medians and ranges.
Raster savings and increased lazy-reader bytes appear together.
Agreement remains limited to matching source pixels, with separate observations retained.
The page does not equate extraction agreement with scientific validity or agreement between overlapping observations.

Read timers and whole-workload timers retain separate definitions.
Missing baselines, incomplete baseline membership, excluded runs, and unavailable memory summaries remain explicit.
Requested range lengths are not presented as metered network delivery.
Storage writes, retrieval, seasonal performance, AWS performance, and production costs remain untested.

Sources: [individual-lake results](../../benchmarks/results/lake-extraction.json),
[shared-image results](../../benchmarks/results/tile-extraction.json), and
[multiple-tile results](../../benchmarks/results/cross-tile-extraction.json).
No measurement file, inventory fact, sensor specification, or source-selection decision changed.
No provider script ran. Existing contributor changes were preserved.

## Prior findings

- Fixed: the owner's comparison-structure findings and authorized presentation changes.
- Preserved: the [plain-language revision](2026-09-18-presentation-plain-language.md), including archive findings in Discovery and descriptive test names.
- Accepted and deferred within this presentation step: scientific validation, overlap rules, reader tuning, storage, and AWS measurements.
- Open and outside this step: the [sensor accuracy findings](2026-09-18-codex-sensor-band-review.md).

## Verification

Existing renderer assertions were updated for the new row orientation while retaining checks for missing comparisons and excluded runs.
A new fixture test checks that the pixel-selection table uses each method's own measurements and labels absent or failed results.
The shared-image fixture additionally checks partial baselines and filtering the example from the detailed tables.

| Check | Result |
|---|---|
| `uv sync --locked` | Passed, 59 packages resolved and 56 checked |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 95 files already formatted |
| `uv run pytest -q` | 218 passed in 14.27 seconds, with 1,476 existing library deprecation warnings |
| `uv run python tools/collate_checks.py --check` | Inventory matches its records |
| `uv run python tools/collate_sensor_bands.py --check` | Sensor dataset matches its records |
| `uv run python tools/render_options.py --check` | Page matches its template and evidence |
| `uv run python tools/gap_report.py --check` | Gap report matches the saved results |
| `git diff --check` | Passed |
| Before-and-after content comparison | Discovery, later tabs, evidence digests, and page scripts unchanged |
| Parsed text and sentence audit | No visible stage labels. Prototype paragraphs and captions meet the 25-word limit |

The browser command was `uv run --offline --with playwright python /private/tmp/check-s2-browser.py`.
Headless Chromium passed at 1280, 768, and 390 pixels wide.
Checks covered tabs, keyboard navigation, map selectors, section links, and the diagram's link to Discovery.
The three primary result tables are visible without opening disclosures.
Expanded results remain contained, with no page overflow, JavaScript errors, or external requests.
Historical archive fragment links still open the correct Discovery evidence panel.

The temporary browser harness initially checked the cross-tab link before its asynchronous hash-change handler completed.
Waiting for the destination panel resolved that harness failure. No page-script change was needed.
Desktop result tables and the diagram at desktop, tablet, and phone widths were visually inspected.
Temporary screenshots and browser scripts remain outside the repository.

## Proposed next step

Owner and Claude Code review of the revised presentation. No production workflow is selected, and no new experiment is started.
No commit, push, or deployment was made.
