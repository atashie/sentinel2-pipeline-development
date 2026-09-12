# Archive explanation and table corrected, 2026-09-11

The owner authorized retaining the proposed archive history, correcting its table, and identifying the explanation as an inference.
Codex updated [measurements.md](../measurements.md#archive-history-measurements-and-inferred-explanation) and the [Discovery template](../../tools/s2-options.template.html).
The [rendered page](../s2-options.html#archive-history) keeps the explanation visible and puts the detailed table in an expandable section.

## Corrections and evidence

- **Fixed:** the table begins at the survey's 2021 boundary. It does not assert measured 2015–2020 holdings.
- **Fixed:** January–November 2022 and the full year have separate counts. Product items remain distinct from acquisition keys.
- **Fixed:** the table records mixed baselines for 2023, replacing “05.09 only”.
- **Corrected with evidence:** post-2024 reprocessing includes the bounded Sentinel-2C tandem campaign. Its announcement does not establish AWS replication.
- **Fixed:** two publication streams and an incomplete historical update are explicitly an inference. The cause and internal ingestion design remain unknown.
- **Fixed:** Plan B adds substantial coverage, without promising complete history or interchangeable values.

The counts were recomputed offline from [gap-survey.json](../../benchmarks/results/gap-survey.json), using its per-tile monthly item, acquisition, and baseline arrays.
No survey result was edited and no new provider measurement ran.
Operational dates and the tandem campaign were independently researched and checked, [source record](../assessment-checks/discovery-presentation-sources.json).
The operational deployment dates are distinct from the CDSE table's sensing-date availability ranges.

This implements the owner's response to the synopsis review and addresses the history explanation in [the archive comparison](2026-09-11-codex-archive-comparison.md).
Other findings in that comparison remain open. This step selects no workflow or new fill policy.

## Verification

- The renderer regenerated the page from its template.
- Offline recomputation confirmed the stated period totals, acquisition counts, and baseline mixtures against the saved survey arrays.
- Headless Chromium verified the expandable table at desktop, tablet, and mobile widths. The table scrolls within its container without page overflow.
- `uv sync --locked`, `uv run ruff check .`, and `uv run ruff format --check .` passed.
- `uv run pytest -q` passed: 65 tests in 0.43 seconds.

## Proposed next step

Review the corrected explanation together. No commit, push, deployment, or prototype was performed.
