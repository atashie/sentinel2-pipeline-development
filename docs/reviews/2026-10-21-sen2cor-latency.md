# Sen2Cor latency survey, 2026-10-21

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: measured, awaiting review. On 2026-10-22 the owner asked for a documentation review, then the commit and push.

## For the owner

- Sen2Cor Level-2A reaches the Collection 1 bucket about 6 hours after sensing, at the median. [Finding 40](../measurements.md#sen2cor-latency-survey-2026-10-21) owns the numbers.
- Most of that delay is ESA's. Earth Search adds well under an hour after Copernicus publishes, at the median.
- On the same clock, window, tiles, and censoring time, ACOLITE's median is about 2 hours longer, and its 90th percentile is several days longer.
- The survey reads metadata and bucket listings only. It cost nothing to the reader, because no bucket is requester pays.
- This computer had no `uv`. With the owner's approval, Claude Code installed it from Astral's installer and ran `uv sync --locked`.

## Step and authorization

The owner asked about the latency of the two products. Finding 27 answered for ACOLITE, and nothing in the repository answered for Sen2Cor.
The owner wrote "Yes, run the Sen2Cor latency query", and after an ad hoc query, "run the proper survey script".

The step builds and runs one metadata survey of Sen2Cor Level-2A arrival. It uses finding 27's tiles, window, and bucket clock, so the two options compare.

Acceptance checks:

1. `--dry-run` prints the plan and creates no client. A fixture test asserts it.
2. Fixture tests cover the bucket layout, the window, the matching, the censoring, and the statistics, with no network.
3. `--from-raw` rebuilds the result byte for byte.
4. The result names every endpoint, the region, the payer, and zero pixels read.
5. `/check` passes, and the inventory and generator checks pass.

Deferred: a pass-by-pass comparison with ACOLITE, live observation over weeks, and the Prototyping tab. The commit waited for the owner, who authorized it on 2026-10-22.

## What changed

| File | Change |
|---|---|
| [benchmarks/l2a_latency.py](../../benchmarks/l2a_latency.py) | New. The survey. It reads the window and tiles from [aqr-coverage.json](../../benchmarks/results/aqr-coverage.json) |
| [tests/test_l2a_latency.py](../../tests/test_l2a_latency.py) | New. Nine fixture tests and one result test, no network |
| [benchmarks/results/l2a-latency.json](../../benchmarks/results/l2a-latency.json) | New. The evidence |
| [docs/measurements.md](../measurements.md) | New section with finding 40 and what the survey does not show |
| [docs/options-inventory.json](../options-inventory.json) | Probe PR-16, bearing on issues I-24 and I-38. On 2026-10-22 both issues cite it, and their consequences state its result |
| [benchmarks/README.md](../../benchmarks/README.md) | One row for the script |
| [CLAUDE.md](../../CLAUDE.md) | The current-phase sentence, the dry-run command, the provider-contact sentence, and the findings index in Gotchas |
| [tools/render_options.py](../../tools/render_options.py) | 2026-10-22. Reads the result, fails unless its window and cutoff are finding 27's, and fills three markers |
| [tools/s2-options.template.html](../../tools/s2-options.template.html) | 2026-10-22. The Discovery tab's archive table states Sen2Cor's median and 90th percentile, and ACOLITE's 90th percentile. The review-comment block is unchanged |
| [docs/s2-options.html](../s2-options.html) | Regenerated. Two cells of the archive table and the generator comment changed |
| [docs/work-plan.md](../work-plan.md), [README.md](../../README.md), [tools/README.md](../../tools/README.md) | 2026-10-22. The survey, its record, and finding 40 in each index |
| [docs/measurements.md](../measurements.md) intro and finding 27 | 2026-10-22. The intro lists the sets after T4. Finding 27 points to finding 40 |
| [Reviews index](README.md) | One row for this record |

## Method

The survey has three sources per tile. Each request is unsigned.

1. Earth Search lists every item of `sentinel-2-c1-l2a` and `sentinel-2-l2a` over the window, catalog fields only.
2. Copernicus OData lists every Level-2A product of the tile over the window, with `OriginDate` and `PublicationDate`.
3. Both buckets are listed per tile and sensing month. Each item folder gives its earliest and latest `LastModified`.

An Earth Search item matches a Copernicus product when `s2:product_uri` equals the product name. Its folder is its item ID.
Every clock counts from the sensing start in the product name. The result's `definitions` hold the exact rules.

The matched cutoff keeps items whose first object predates finding 27's listing time, 2026-10-13T18:22:53+00:00. Both options then face the same censoring.
The within-threshold shares divide by every Copernicus product of the window. A product with no Earth Search item counts as not arrived.

## Evidence and provenance

| Quantity | Value |
|---|---|
| Measured at | 2026-10-21T21:55:19+00:00 |
| Code version | `f77a342-dirty`. The script was new and uncommitted at run time |
| Script hash | `script_sha256` in the result. It matches the script on disk, checked after the run |
| Requests | 96 Earth Search, 24 Copernicus OData, 240 bucket listings. All 360 answered 200 on the first attempt |
| Bytes received | 2,550,854 from the catalogs and 28,970,764 of listings. Object bodies: 0. Pixels: 0 |
| Endpoints | `earth-search.aws.element84.com/v1`, `catalogue.dataspace.copernicus.eu/odata/v1`, `e84-earth-search-sentinel-data` and `sentinel-cogs` in us-west-2 |
| Payer | The bucket owners and the catalog providers. Neither bucket is requester pays |
| Raw listings | `data/l2a-latency/2026-10-21T215519+0000/`, 19 MB, ignored by git, assumption A25 |

Other requests the step made, outside the result:

- Two ad hoc Earth Search queries before the survey existed, from the scratchpad. They sampled 200 items per 10-day window and are superseded.
- Two Copernicus OData requests and two bucket listings, to confirm field names and anonymous listing.
- A smoke run on tile 10SEJ, written to the scratchpad. Its raw listings are in `data/l2a-latency/2026-10-21T215455+0000/`.
- The `uv` installer download and the `uv sync --locked` package downloads.

## Verification

| Command | Outcome |
|---|---|
| `uv run python benchmarks/l2a_latency.py --dry-run` | Printed the plan. Contacted nothing |
| `uv run pytest tests/test_l2a_latency.py` | 9 passed, 1 skipped before the result existed. 10 passed after |
| `uv run python benchmarks/l2a_latency.py --from-raw data/l2a-latency/2026-10-21T215519+0000 --output <scratch>` | `cmp` found the rebuild identical to the result |
| `uv run python tools/collate_checks.py --check` | The inventory matches the check records |
| `/check`, first run | `test_rendered_html_matches_inventory` failed. Probe PR-16 changed the inventory digest the page embeds |
| `uv run python tools/render_options.py` | Regenerated the page. Only the digest comment changed, checked by a diff of a scratch render first |
| `/check`, second run | `uv sync --locked`, `ruff check`, and `ruff format --check` passed. `pytest` passed 421 tests in 39.56 s |
| The `--check` of `collate_checks`, `collate_sensor_bands`, `render_options`, and `gap_report` | All four passed |

## Documentation review, 2026-10-22

The owner wrote "review all relevant documentation to ensure we are up to date with these results. Then let's commit and push".
Claude Code searched the active documents for latency, arrival, publication time, issue I-24, and the findings indexes. The table under What changed lists the edits.

Checked and left unchanged:

- Assumption A11 still holds. No latency target is set.
- The data contract's `published_at` rule names the primary product's clock. Sen2Cor's clock is a contract change, outside this step.
- Decisions 0007 and 0008 name latency in their review triggers only.
- Dated records, including the [session handoff](2026-10-18-session-handoff.md), stay as written.
- The Prototyping tab waits for the owner's hand review.

`inject.py --check` for the review-comment layer did not run. This computer has no `~/github/cc-skills`. The edit lies outside the `rc:start` to `rc:end` block.

| Command | Outcome |
|---|---|
| `uv run python tools/render_options.py` | Rewrote the page. The diff holds two archive-table cells and the generator comment |
| `/check` | `uv sync --locked`, `ruff check`, and `ruff format --check` passed. `pytest` passed 421 tests in 40.84 s |
| The `--check` of `collate_checks`, `collate_sensor_bands`, `render_options`, and `gap_report` | All four passed |

## Limits

- The window looks back four months from one listing. Live arrival over weeks stays open, issue I-24.
- The ACOLITE row is copied from finding 27's result. The survey did not relist the USGS bucket, so no pass is paired across options.
- `LastModified` marks the last write. One older-collection item was rewritten 59.6 days after sensing. Its first object kept the original time.
- Copernicus is the reference set. A product missing from Copernicus is not seen.
- The 24 tiles lie in the lower 48 states. They are the gap survey's tiles, not a random sample.

## Dispositions of prior findings

| Item | Disposition |
|---|---|
| Issue I-24, publication latency documented loosely | Accepted and deferred. Probe PR-16 measures four months of history, and the issue cites it. The issue's status stays `measure` until live observation or the owner's decision |
| Issue I-38, no service commitment for the primary product | Accepted and deferred. Finding 40 gives ACOLITE's arrival a comparison, and the issue cites PR-16. It changes no commitment |
| Claude Code's earlier answer in this session: Sen2Cor medians of 0.2 to 0.5 days on 12 passes | Corrected with evidence. Over 1,502 items, the catalog record median is 0.26 days, finding 40 |
| Claude Code's earlier guess that Earth Search lags Copernicus somewhat | Corrected with evidence. The median lag after Copernicus publication is 0.45 hours, finding 40 |

## Proposed next step

Not started. Each option needs the owner's authorization.

- Fold a fresh USGS bucket listing into probe T8. T8 already lists object timestamps over several weeks. Rerunning this survey on the same days would time both options live, issue I-24.
- Alternatively, relist the USGS bucket once and pair passes across options. That gives ACOLITE's share of passes within a day.
- Add finding 40 to the Prototyping tab after the owner's hand review of that tab.
