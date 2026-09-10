# Discovery review, 2026-09-10

Reviewer: Claude Code (AI coding agent), directed by the repository owner. Scope: the discovery step specified in [discovery-plan.md](../discovery-plan.md) and authorized by the owner on 2026-09-09 after accepting the [initialization review](2026-09-09-codex-initialization-review.md).
Research ran on 2026-09-09. Collation, findings, and this review were written on 2026-09-10. Nothing here is committed.
The owner's feedback on this review is recorded in the [response](2026-09-10-owner-feedback-response.md) and [decision 0002](../decisions/0002-aws-source-pixel-classes-tile-provenance.md). The findings stand. The proposed next step is superseded in part.

## Delivered artifacts

- [options-inventory.json](../options-inventory.json), schema 2, rebuilt by [collate_checks.py](../../tools/collate_checks.py) from the research and check records.
- [s2-options.html](../s2-options.html), rendered by [render_options.py](../../tools/render_options.py). The Discovery tab is populated. The other three tabs are `TBD`.
- [s2-best-practices.md](../s2-best-practices.md), rewritten from the [recheck record](../assessment-checks/best-practices-recheck.json) with statuses, corrected wording, citations, four new practices, and a table of items still unverified.
- Research drafts, check records, and the recheck record under [assessment-checks/](../assessment-checks/README.md).
- Stronger inventory tests, the `estimated` status, the `offset_delivery` field, assumption A20, and the wording fixes the initialization review asked for.

| Quantity | Count |
|---|---|
| Candidates, across four dimensions | 22 |
| Bound claims | 319, of which 288 documented and 31 estimated |
| Primary sources with access dates | 120 |
| Check verdicts | 287 confirmed, 1 corrected, 0 not verifiable |
| Draft claims that did not bind | 0 |
| Best-practices verdicts | 9 confirmed, 10 partial, 1 contradicted, 0 not on page |
| Findings and combinations | 20 and 7 |
| Options noticed but not assessed | 26 |

These counts describe documentation coverage. They are not provider performance, cost, or data quality measurements.

## Method and verification

Four research agents, one per dimension, ran on the Opus model. Each drafted claims with a verbatim quote, a locator, and an access date, and re-verified its own quotes before writing.
Four checking agents ran on the Sonnet model. Each fetched every cited page fresh and recorded a verdict per draft claim. Only confirmed and corrected records bind claims.
One recheck agent on the Opus model read the primary pages behind every best-practices claim and recorded verdicts, corrected wording, and fifteen additional findings.
The parent agent reviewed the 31 estimated claims, wrote the findings and combinations, wrote the collation script and renderer, and ran the check workflow.

Limits of that verification:

- AWS pricing pages render prices with JavaScript. Every AWS price was read from a worked example on the page or from the pricing data files the page names. The checker for storage matched prices by rate code in those files.
- The workflow checker forked six sub-checkers, and three of them checked the whole file instead of their share. The checker audited the merged result and re-fetched nine high-stakes sources itself. Its record notes this.
- The domain `sentinel.esa.int` did not resolve from the research environment. ESA pages were read from SentiWiki and Sentinel Online. Four publisher domains returned 403, so three directly relevant papers were not read.
- Two provider pages disagree on whether the Sinergise Level-2A bucket is requester pays. Both are recorded. Neither is resolved.
- Researcher and checker are both AI agents of one family. They are independent of each other by model, not by organization. No human has checked a claim.
- No product was opened. Every metadata field name comes from a specification or an announcement, not from an observed product.

## Dispositions of the initialization review

| Finding | Disposition | Where |
|---|---|---|
| F01, conversion caveat | fixed | `offset_state` in [data-contract.md](../data-contract.md), practice P8, the `offset_delivery` field, finding F-01 |
| F02, pixel-count wording and extraction geometry | fixed | CLAUDE.md gotcha, practice P6, assumption A7 note, new assumption A20, finding F-04 |
| F03, provisional wording and scientific choices | fixed | Best-practices preamble marks practices provisional. Claims R3 and G8 now carry the sources the review cited or their SentiWiki equivalents |
| F04, overstated test coverage | fixed | [test_inventory.py](../../tests/test_inventory.py) opens check records, matches claim IDs and approved values, requires a documented basis for estimates, and fails on stale HTML or inventory. [assessment-data-format.md](../assessment-data-format.md) lists exactly what is enforced |
| F05, estimates versus source facts | fixed for claims, deferred for budgets | The `estimated` status labels every inference in the inventory and HTML. Pilot spending limits versus production budgets remain for the tradeoffs step |
| F06, duplicated guidance | accepted and deferred | CLAUDE.md was edited only where facts changed. Pruning waits for a pass that does not also carry content changes |
| Scope clarification, HydroBASINS versus HydroLAKES | fixed | [examples/README.md](../../examples/README.md) |

## Corrections to the supplied report

The recheck found two errors in the supplied geolocation report. It conflated the Global Reference Image accuracy with product accuracy. It missed the Euro-Africa refinement step of March 2021. Correction on 2026-09-10: an earlier version of this paragraph also attributed an adjacency-distance error to the report. That figure came from the first draft of the best-practices document, not from the report, which does not cover adjacency. The [Codex discovery review](2026-09-10-codex-discovery-review.md), finding D10, caught it. Its 12 m pre-refinement figure and its steep-terrain figure could not be traced. Section 6 of the best-practices document lists what remains unverified.

## Findings that bear on selection

The inventory's findings F-01 to F-20 carry the claim references. In brief:

- Offset handling differs by route and by reading library, so the store must record conversion state per asset (F-01, F-02).
- One lazy-stack library resamples every band to 10 m by default, and no library default selects pixels for a 10 m pond (F-03, F-04).
- Some workflows fuse or stitch tiles and lose the tile provenance that adjacent-tile differences require (F-05).
- Quality layers, Collection 1 availability, 2017 coverage, payer, and region all differ by route. Only two routes document reprocessed products (F-07 to F-10).
- No compute platform documents native deduplication. Every platform documents fan-out without a scheduler (F-12, F-13).
- Atomic commits and as-of reads come from Iceberg or Icechunk, or from application code over Parquet. Snapshot expiry defaults delete history (F-15).
- Small objects carry minimum charges, and a cluster carries a fee whether or not work is queued (F-16, F-17).

## Report validation

A static parse of [s2-options.html](../s2-options.html) on 2026-09-10 found no external script, stylesheet, image, or frame. It found the four part sections, four tables, 22 candidate cards, and 31 estimate badges. The embedded dataset held 319 claims, 120 sources, 20 findings, and 7 combinations. The footer digest matches the inventory file.
No browser rendering check ran. The browser extension was not connected from the environment, and file URLs are refused. Desktop and mobile layout, tab switching, and the no-JavaScript fallback remain unverified in a browser.

## Repository gate

The [check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10.

| Command | Outcome |
|---|---|
| `uv sync --locked` | Passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run pytest -q` | Passed, 36 tests |
| `uv run python tools/collate_checks.py --check` | Passed, run inside the tests |
| `uv run python tools/render_options.py --check` | Passed, run inside the tests |

## Proposed next step, not started

Selection, step 2 in [work-plan.md](../work-plan.md), is the owner's decision after this review. Two questions precede it and are the owner's to answer:

1. The pixel selection rule for small ponds, assumption A20. Finding F-04 shows the library defaults can select nothing for a 10 m pond. Coverage-fraction selection, all-touched selection, and centre selection produce different pixel sets and different storage volumes.
2. Which history scenario a prototype must serve first. Finding F-09 shows that a 2017 global Level-2A history is not on the preferred route's main collection. It is on its Collection 1 collection, with documented gaps, or on the Sinergise buckets.

As a proposal for the owner's consideration, the windowed-read path over Earth Search is shared by combinations C-01 and C-02. It is the only path that is free, unauthenticated, and in a US region. It is also documented to carry both Collection 1 and the cloud and snow probabilities. A bounded prototype of that read path on the public pilot set would measure request counts and bytes per pond-scene. It would also settle the detector footprint question. A separate bounded probe would settle the Sinergise Level-2A payer conflict without reading imagery. Neither is selected by this review.
