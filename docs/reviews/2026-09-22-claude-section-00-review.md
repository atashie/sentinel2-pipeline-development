# Claude Code review of prototyping section 00, 2026-09-22

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: review complete, with three owner-directed wording fixes applied.

The owner asked for a technical accuracy review of Codex's new
[section 00](../s2-options.html#prototype-takeaways), recorded in its
[implementation record](2026-09-22-prototype-high-level-takeaways-implementation.md),
and for a clearer section title.

## Evidence checked

Every displayed number was recomputed from
[`benchmarks/results/lazy-reader-workloads.json`](../../benchmarks/results/lazy-reader-workloads.json),
using the raw-key mapping in the
[naming proposal](2026-09-22-prototype-extraction-naming-proposal.md):
`A-raster` is A1, `A-lazy` is A3, `B-raster` is B1, `B-lazy` is B3, `B-lazy-control` is B2,
`C-raster` is C1, and `C-lazy` is C3.

| Displayed claim | Recomputed value | Result |
|---|---|---|
| Florida shared windows take one-sixth to one-tenth the separate-lake time | 101.9 s over 599.6 s, and 67.7 s over 701.3 s | Confirmed |
| Whole-image reads request over four times the shared-window bytes | 4.3 times for reader 1, 4.6 times for reader 3 | Confirmed |
| Dispersed B1 processor time 10.8 s, B3 24.4 s | 10.77 s and 24.38 s, user plus system | Confirmed |
| B1 uses less processor time and fewer requests in both cohorts | 1,997 against 2,143, and 464 against 513 | Confirmed |
| B3 elapsed time 8 percent and 34 percent lower | 7.9 percent and 33.6 percent | Confirmed |
| B3 requests slightly fewer bytes | 6 percent and 4 percent fewer | Confirmed |
| No consistent memory winner | B1 lower when dispersed, higher in Florida | Confirmed |
| B1 and B3 peak at 0.22 to 0.33 GiB with supervision | 0.223 to 0.332 GiB aggregate resident memory | Confirmed |
| Cohort products and tiles | 100 lakes, 121 products, 120 tiles, and 1,000 lakes, 4 products, 4 tiles | Confirmed |
| Fourteen configurations agree on outputs | `matches_all_complete_outputs` true for all fourteen | Confirmed |
| Both shared-window readers process Florida faster with fewer bytes | 101.9 s against 496.2 s, and 67.7 s against 457.2 s | Confirmed |

Two method checks also passed. The processor figures come from the worker process that performs
the extraction, and the lazy readers compute on threads inside it, so no child process is excluded.
The reader comparison uses total elapsed time, which avoids the component asymmetry that the
[sleep rerun response](2026-09-22-sleep-rerun-review-response.md) describes.

## Findings and dispositions

| Finding | Disposition |
|---|---|
| 1. The dispersed sharing statement omitted the measured direction and its weaker basis | Fixed. The card now states that the separate-lake workflow took 30 percent less total time, and that its two dispersed observations come from an earlier date and source version |
| 2. "Prepared outputs" collided with the separate preparation phase | Fixed. The sentence now says extraction outputs, matching its own heading |
| 3. The title assumed the workflow codes from section 01 | Fixed. The owner selected grouping by tile image and reading only the needed pixels |

The three fixes changed the [template](../../tools/s2-options.template.html) and the regenerated
[page](../s2-options.html). No measured result, renderer, or other section changed.
The dispersed comparison keeps the attribution limits of the
[sleep rerun response](2026-09-22-sleep-rerun-review-response.md): it names the observations and
their differing date, and assigns no cause.

## Verification

- `uv sync --locked`: 59 packages resolved, 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 122 files already formatted.
- `uv run pytest -q`: 277 passed in 29.78 seconds.
- `uv run python tools/render_options.py --check`: the page matches its template and evidence inputs.

## Limits and proposed next step

This review covers section 00 only. It recomputed displayed numbers and did not repeat any measurement.
No production reader is selected, and scientific validation remains open.
Proposed next step: Codex reviews the three wording changes. No commit, push, or publication occurred.
