# Presentation wording and archive findings, 2026-09-18

Implementer: Codex, directed by the repository owner.

Scope: plain language across the [presentation](../s2-options.html), with archive differences consolidated in Discovery.
The owner requested these edits after the [archive introduction revision](2026-09-18-access-problem-first.md).

## Changes

- Replaced visible stage numbers with descriptions of individual-lake, shared-file, and multiple-tile tests.
- Replaced vague headings with direct descriptions of the topic or measured finding across all four tabs.
- Renamed the difficult-cases heading to “Assessing extraction methods across difficult use cases.”
- Explained the archive value difference without project shorthand or unexplained “clamping.”
- Moved the archive comparison out of Prototyping and into Discovery’s existing archive section.
- Kept the detailed pixel comparison, access timings, sources, and limits in a closed evidence panel.
- Updated Prototype navigation and section numbering after removing the repeated section.

The Discovery summary explains that one tested older product changed values and lost low-value information.
It warns against applying an already-applied numerical adjustment again.
The evidence panel retains the three-band scope, exact conversion rule, quality-layer differences, and access limitations.
The findings remain limited to the tested product.

The [template](../../tools/s2-options.template.html) owns the page wording.
The [renderer](../../tools/render_options.py) also changes one missing-comparison label to remove its stage reference.
The existing renderer assertion now expects that display text. No new test was added for this editorial change.
Existing fragment identifiers remain available, including the archive comparison’s old identifier in its new Discovery location.

## Evidence and limits

The archive summary uses [measurement findings 13–15](../measurements.md#prototype-stage-1-raw-access-to-whole-tiles-2026-09-14).
Its tables still render from the saved results. No measurement, sensor dataset, or source claim changed.
No provider script ran. Existing contributor edits were preserved, and no commit or deployment was made.

The owner’s four wording and placement requests are fixed.
The prior [sensor accuracy findings](2026-09-18-codex-sensor-band-review.md) remain open for a separate technical correction.

## Verification

| Check | Result |
|---|---|
| `uv sync --locked` | Passed, 59 packages resolved and 56 checked |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed, 94 files already formatted |
| `uv run pytest -q` | 216 passed in 16.49 seconds, with 1,476 existing library deprecation warnings |
| `uv run python tools/collate_checks.py --check` | Inventory matches its records |
| `uv run python tools/collate_sensor_bands.py --check` | Sensor dataset matches its records |
| `uv run python tools/render_options.py --check` | Generated page matches its inputs |
| `uv run python tools/gap_report.py --check` | Gap report matches the saved measurements |
| `git diff --check` | Passed |
| Parsed page text and changed-sentence audit | No visible stage references or duplicate archive heading. Changed sentences meet the 25-word limit |

The browser command was `uv run --offline --with playwright python /private/tmp/check-s2-browser.py`.
Headless Chromium passed at 1280, 768, and 390 pixels wide.
Checks covered all four tabs, keyboard navigation, map selectors, existing fragment navigation, and page overflow.
There were no JavaScript errors or external requests.
Desktop archive and phone multiple-tile screenshots were also inspected.
The temporary browser script and screenshots are local verification artifacts, outside the repository.

## Proposed next step

Owner and Claude Code review of the updated presentation. Further technical corrections remain separate work.
