# Claude Code review of the AWS cost analysis for daily updates, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: review complete. The proposed plan has not started.

The owner asked whether Codex's [cost analysis](../aws-cost-analysis.md) covers the cost of daily updates.
The owner also asked for a plan to estimate that cost for every scenario.
This review read the report, the [estimator](../../tools/estimate_aws_costs.py), its [inputs](../cost-analysis/inputs.json), and its [estimates](../cost-analysis/estimates.json).
It also read decisions [0005](../decisions/0005-aws-cost-scenarios.md) and [0006](../decisions/0006-aws-cost-review-refinements.md) and both Codex records.
It contacted no provider. It changed no file except this record and the review index.

## What the analysis already covers

The report has a daily extraction table and a monthly recurring budget.
Daily output bytes include the overlap and revision multipliers. Daily PUTs and monthly compaction PUTs are charged.
Recurring compute assumes instances stop after each run. The Intelligent-Tiering scenario keeps recent updates in frequent access.
The serving table prices thirty days of new output.
The daily line exists. It pro-rates the backfill, and several daily costs sit outside it.

## Findings

| # | Finding | Effect on daily cost |
|---|---|---|
| 1 | Daily figures are the backfill divided by its days | No daily term of its own |
| 2 | The forward acquisition rate is higher than the model's rate | Volume terms 1.2 to 2.5 times the model at survey sites |
| 3 | Storage growth from updates is computed and not reported | Largest recurring cost of updates, absent from every table |
| 4 | The fixed allowance is nearly all of the sample's recurring cost | Sample daily cost is unestimated |
| 5 | Daily-specific overheads are absent | Small in dollars, unmeasured |
| 6 | Reprocessing arrives in lumps outside the revision multiplier | Periodic partial backfills are unpriced |
| 7 | Compaction is charged for writes only | Minor |
| 8 | Capacity columns use the average day | Matters only with a latency target |

### 1. Daily figures are the backfill divided by its days

The estimator divides backfill totals by the 2,091 days from 2021-01-01 to the cutoff.
Daily output bytes (line 218), EC2 hours (line 408), and Lambda slots (lines 442 to 444) follow this rule.
Daily cost therefore inherits the backfill's batching and its historical average rate.

### 2. The forward acquisition rate is higher than the model's rate

The base case uses 73 acquisitions per tile-year. The low and high cases use 60 and 110. No input covers adjacent-orbit overlap.
**Measured** in the [gap survey](../../benchmarks/results/gap-survey.json), reference acquisitions per tile over the 24 contiguous-US tiles:

| Period | Mean per tile | Range |
|---|---|---|
| 2021 | 145.1 | 143 to 146 |
| 2022 | 144.8 | 142 to 146 |
| 2023 | 143.9 | 140 to 146 |
| 2024 | 147.8 | 134 to 157 |
| 2025 | 172.3 | 161 to 176 |
| 2025-09 to 2026-08 | 174.2 | 169 to 180 |

The per-lake rate comes from Collection 1 footprints that cover each site point, 2025-09-10 to 2026-09-10.
Five of 16 contiguous-US sites had 85 to 89. Eleven had 171 to 182.
Against the model's 73, those rates are 1.2 and 2.3 to 2.5 times higher.
Issue I-25 in the [inventory](../options-inventory.json) records this: "Scenes per tile per year are not constant. Benchmarks size on the densest period."
The cost model does not cite I-25. Daily updates run at the current rate, and a 2021 to 2026 average understates it.

The survey sites were chosen by purpose, several because they straddle tiles. They do not measure the national share of orbit overlap.
A footprint can also include no-data pixels at a point, [measurement finding 23](../measurements.md).
This finding also changes the backfill's history volume. It applies to the backfill model as well as the daily one.

### 3. Storage growth from updates is computed and not reported

`s3_monthly_added_each_year_usd` is in the estimates file. For all bodies with land, each year of updates adds $92.14 to the monthly bill.
No report table shows it. The recurring budget uses storage at the cutoff, the lowest storage bill of any later month.
With the model's base numbers for all bodies with land:

| Months after cutoff | Extra S3 from update output, cumulative | B1 EC2 daily extraction, cumulative |
|---|---|---|
| 12 | $599 | $115 |
| 36 | $5,114 | $346 |
| 60 | $14,051 | $576 |

Extra S3 is the sum over month m of $92.14 × m / 12. Extraction is $9.60 per month.
Within the model, the storage that updates create costs 5 to 24 times their extraction.

### 4. The fixed allowance is nearly all of the sample's recurring cost

The 10,000-body sample with land has a B1 EC2 recurring budget of $102.54 per month. The unsourced allowance, assumption A35, is $100 of it.
The scheduler, queue, item ledger, logs, alarms, and container registry are not itemized. The sample's daily cost is therefore unestimated.

### 5. Daily-specific overheads are absent

A backfill worker can load a tile's prepared geometry once and process hundreds of dates. A daily run loads it for each tile-date.
Prepared geometry for all bodies with land is 46.2 GiB over 1,050 tiles.
At the model's 210 tile-dates per day, a daily run reads about 9.2 GiB of geometry. The day's new output is 11.0 GiB.
Per-run work is also absent: EC2 worker start, the catalog query with a lookback for late items, and ledger reconciliation.
Lambda already carries a five-second start per invocation. EC2 carries none.

### 6. Reprocessing arrives in lumps outside the revision multiplier

The 1.05 revision multiplier spreads routine duplicate products evenly over time.
Provider reprocessing re-extracts history in lumps. The [measurement notes](../measurements.md) cite a completed Sentinel-2C tandem reprocessing campaign.
Collection 1 is nearly empty from January to November 2022. That is 334 of 2,091 days, 16 percent of the history.
A switch from the fallback to Collection 1 for that period re-extracts it. Practice P9 keeps local revisions, which adds storage.

### 7. Compaction is charged for writes only

Monthly compaction reads the month's daily objects and rewrites them. The model charges the PUTs. It omits the GETs and the compute.

### 8. Capacity columns use the average day

Cost depends on total work when charges are proportional to runtime. Capacity for a latency target depends on the busiest day.
From 2025-09 to 2026-08, monthly acquisitions summed over the 24 survey tiles ranged from 280 to 374. The daily distribution is unmeasured.
Assumption A11 sets no latency target.

## Proposed plan for daily update costs

Scope: four workloads, recipes A1, B1, and B3, EC2 and Lambda, and the low, base, and high cases.
The work is offline arithmetic. Step 1's optional query needs separate authorization.

1. **Forward rate.** Add a tile acquisition rate and a point observation rate. Derive both from the saved gap survey.
   Report the latest 12 months beside 2021 to 2024. The tile rate drives per-product overheads.
   The point rate drives bytes, compute, output, and storage.
   With authorization, a metadata-only catalog count over all contiguous-US tiles measures the national overlap share and the daily distribution.
2. **Daily unit cost.** Express extraction per tile-date from the existing per-epoch terms. Multiply by forward tile-dates per day.
   Add per-run and per-tile-date overheads as unsourced inputs with low, base, and high values.
   Size geometry reads from `static_geometry_bytes`.
3. **Writes and compaction.** Keep daily PUTs. Add compaction GETs and compute.
4. **Storage accrual.** Report the monthly charge that each day of updates adds.
   Report the monthly bill and the cumulative cost at 12, 36, and 60 months after the cutoff.
   Cover Standard storage and the Intelligent-Tiering scenario.
5. **Reprocessing reserve.** Price re-extraction per tile-date from the backfill terms.
   Show an annual reserve at 0, 5, and 20 percent of history.
   Price the 2022 switch to Collection 1 as a named one-time event, with retained revision storage.
6. **Daily operations.** Itemize the scheduler, queue, item ledger, logs, alarms, registry, and catalog query compute.
   A research agent and a separate checking agent confirm each price. A residual allowance covers anything unpriced.
7. **Capacity.** Report the busiest month and, if measured, the busiest day. Size workers only against a latency target the owner sets.

New report tables show, per scenario, the daily unit cost and the monthly recurring cost at each horizon.
Another table shows cumulative backfill plus update cost.
A sensitivity compares the model's 73, the recent tile rate, and the point-rate range.

Acceptance checks:

- With zero overheads, zero reserve, and the historical rate, daily cost times 2,091 reproduces the backfill extraction cost.
- The 12-month storage accrual equals the existing `s3_monthly_added_each_year_usd`.
- Every new input has a row in the [assumption registry](../assumptions.md#aws-cost-analysis) with its status.
- The estimator's `--check` reproduces the report and JSON. The repository check workflow passes.

Deferred: AWS measurement of overheads, geometry memory, and request latency.
Also deferred: changes to the water-body set and their per-body backfill, and any scheduler choice under assumption A12.

## Decisions for the owner

1. Cadence. A once-daily batch is the proposed base case. Per-tile-date triggers and a weekly batch are optional sensitivities.
2. Horizons. The plan proposes 12, 36, and 60 months after the cutoff.
3. Forward-rate evidence. Choose the saved survey only, or also authorize the metadata-only catalog count.
4. Backfill scope. Finding 2 changes the backfill volume. Choose whether that revision joins this step or follows it.
5. Implementer. Codex owns the estimator and its uncommitted revision. Claude Code can review the result.

## Verification

Every number in this record was recomputed offline with Python from the estimates, inputs, and gap survey files named above.
The survey figures sum the monthly `reference.acquisitions` counts per tile and the per-site footprint counts.
The 24 tiles exclude the Alaska tile and the five tiles outside the United States.

The repository check workflow passed:

- `uv sync --locked`: 59 packages resolved, 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 133 files already formatted.
- `uv run pytest -q`: 301 passed in 29.45 seconds, with 13,000 existing dependency deprecation warnings.
