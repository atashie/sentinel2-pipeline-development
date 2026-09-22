# Extraction approaches and workflow names, 2026-09-18

Implementer: Codex, directed by the repository owner.

Scope: clarify how the four extraction approaches relate to workflows A, B, and C in the [Prototype tab](../s2-options.html).
The owner found section 02 ambiguous after the [workflow layout revision](2026-09-18-prototype-workflow-layout.md).

## Changes

- Explained that workflows organize image reads, while extraction approaches select and read the required pixels within that arrangement.
- Identified section 02 as four extraction approaches tested within workflow A, with each lake processed separately.
- Defined boundary clipping, pixel masks, stored pixel positions, and chunked array reads before their results.
- Explained that chunked arrays use the same prepared mask through a different reader.
- Connected the pixel-mask and chunked-array approaches to the raster and lazy array reader labels in later tables.
- Updated navigation, section headings, and the comparison overview to name what each section compares.
- Added reading guidance for the workflow tables, separating workflow effects from reader effects.

The definitions retain the names already used in the result rows.
The [individual-lake implementation record](2026-09-14-stage-2-one-lake-at-a-time.md#the-four-methods-per-scene) supplies their behavior.
The simple clip remains distinct because it omits nearby land and prepared pixel classes.
The stored-position explanation explicitly retains the surrounding window read.

Only the [template](../../tools/s2-options.template.html), generated page, this review, and the review index changed in this step.
Measurements, renderer logic, and tests remain unchanged. No new test was needed for these explanatory edits.
No provider script ran, and existing contributor changes were preserved.

## Dispositions

- Fixed: the owner's ambiguity finding about section 02 and its relationship to A, B, and C.
- Preserved: the preceding layout, visible result tables, and measurement limitations.
- Accepted and deferred: scientific validation, overlap rules, production workflow selection, storage, and AWS measurements.
- Open and outside this step: the [sensor accuracy findings](2026-09-18-codex-sensor-band-review.md).

## Verification

| Check | Result |
|---|---|
| `uv sync --locked` | Passed, 59 packages resolved and 56 checked |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 96 files already formatted |
| `uv run pytest -q` | 219 passed in 13.27 seconds, with 1,476 existing library deprecation warnings |
| `uv run python tools/collate_checks.py --check` | Inventory matches its records |
| `uv run python tools/collate_sensor_bands.py --check` | Sensor dataset matches its records |
| `uv run python tools/render_options.py --check` | Page matches its template and evidence |
| `uv run python tools/gap_report.py --check` | Gap report matches the saved results |
| `git diff --check` | Passed |
| Parsed sentence audit | Prototype paragraphs and captions meet the 25-word limit |
| Before-and-after comparison | Evidence digests and page scripts unchanged |

Headless Chromium passed at 1280, 768, and 390 pixels wide.
Checks covered tabs, keyboard navigation, map selectors, section links, visible result tables, expandable results, and page overflow.
There were no JavaScript errors or external requests.
The command was `uv run --offline --with playwright python /private/tmp/check-s2-browser.py`.
The definitions and their surrounding explanations were also visually inspected at tablet and phone widths.
Browser scripts and screenshots remain temporary artifacts outside the repository.

## Proposed next step

Owner and Claude Code review of the revised explanations. No commit, push, deployment, or new experiment was made.
