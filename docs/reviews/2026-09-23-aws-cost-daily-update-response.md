# AWS daily update review response, 2026-09-23

Author: Codex, directed by the repository owner.
Status: implemented offline refinement, awaiting owner review.

The owner requested integration of the [daily-update review](2026-09-23-claude-aws-cost-daily-update-review.md), including explicit disagreements.
The [analysis](../aws-cost-analysis.md), [estimator](../../tools/estimate_aws_costs.py), and [inputs](../cost-analysis/inputs.json) now separate backfill, forward ingestion, and accumulating retention.
[Decision 0007](../decisions/0007-aws-daily-update-costs.md) records the method and updated assumptions.
Other contributors' files and the original review remain intact. Nothing was staged, committed, pushed, or deployed.

## Finding dispositions

| Finding | Disposition | Result |
|---|---|---|
| 1. Daily costs prorate backfill | fixed | Forward rates, daily geometry reloads, startup, operations, and compaction have explicit terms. Reusable extraction units still derive from calibrated work. |
| 2. Acquisition frequency is understated | corrected with evidence | The saved tile counts support higher frequencies. Point-footprint counts are raw catalog items, not deduplicated valid observations. Both history and forward rates are revised. |
| 3. Storage growth is hidden | fixed | Report daily additions to the monthly charge and 12-, 36-, and 60-month bills and cumulative costs. Include Standard and unaccessed Intelligent-Tiering. |
| 4. Fixed allowance dominates the sample | fixed | Itemize service consumption and price it with independent source checks. Retain an explicit residual contingency and consumption sensitivities. |
| 5. Daily overhead is absent | fixed | Charge prepared-geometry reads, deserialization, batch starts, catalog reconciliation, and ordinary service requests. Overhead assumptions remain unmeasured. |
| 6. Reprocessing is lumpy | fixed | Price annual reserves and a conditional 2022 replacement with retained output. Reserve fractions reference fixed cutoff acquisitions. |
| 7. Compaction charges omit reads and compute | fixed | Charge input GETs, output PUTs, and compaction work. Partition Lambda compaction into bounded invocations. |
| 8. Average-day capacity lacks a latency target | accepted and deferred | Report average work and the busiest measured month. Remove the one-hour daily fleet column. Daily peaks and latency commitments remain unestablished. |

## Qualifications and pushback

The review's 24-tile frequency table reproduces exactly. Its evidence set includes Erie, despite the cost scope excluding the Great Lakes.
The revised evidence uses 23 tiles from 15 eligible survey sites. This does not exclude eligible ponds in Erie's tile from production.
The survey generator counts footprint items without acquisition deduplication. Maximum per-tile site counts cannot establish a cross-tile union or pixel validity.
Purpose-selected sites cannot establish the national orbital-overlap share. The central point-to-tile fraction is explicitly assumed, with half/full sensitivities.

The proposed point-rate scaling for all source bytes is insufficient in dense workloads.
The implementation first adjusts logical intersections per product, then recomputes shared block occupancy and multiplies by tile acquisitions.
Output scales with point frequency. Product overhead follows tile frequency. Separate tile-overlap and routine-revision factors remain intact.

The sample was not wholly unestimated: extraction and storage already had estimates. Its operations allowance was insufficiently informative.
The revision replaces that central allowance with priced components and an explicitly smaller residual, without pretending consumption was measured.
The larger prior allowance remains available only in labeled historical-proration comparator fields.

The review's cumulative storage examples charge month-end inventory for every full month.
Uniform arrivals incur half a month's average storage for each new monthly cohort.
Before pricing tiers change, the review's first-year approximation exceeds that integral by thirteen divided by twelve.
The revised forecast uses midpoint accrual, with explicit Intelligent-Tiering aging after ingestion and monthly compaction.

A future 2022 replacement is conditional, not inevitable. New assets must become usable and the owner must elect to replace retained output.
The event uses acquisition counts for the affected interval rather than calendar days alone.
One replacement copy excludes the historical routine-revision multiplier, avoiding a duplicate revision allowance.
Annual reserve costs assume shared batch infrastructure and do not establish campaign deadlines or dedicated launch costs.

## Evidence and checks

A separate audit agent recomputed the saved survey rates and checked the new arithmetic independently.
A research agent checked service price sources. An independent checking agent confirmed them in [the daily price record](../assessment-checks/aws-cost-daily-sources.json).
The rates include qualified regional proxies. No AWS measurement or new provider query ran.

The audit identified three implementation issues before completion: an infeasible fixed fleet, unsplit Lambda compaction, and duplicate campaign startup charges.
The implementation now enlarges the fleet for average-day feasibility, partitions compaction separately, and derives campaign billing from useful work.
Regression tests cover those corrections, rate distinctions, storage integration, reserve copies, and extraction reconciliation.
At historical rates, daily extraction times history days reproduces EC2 compute plus EBS and Lambda useful duration.
Full Lambda bills differ because daily and backfill invocation partitions differ. That difference is modeled rather than forced away.
The one-year storage increment also reproduces the earlier formula when rates match.

Verification completed:

- `uv sync --locked`: 59 packages resolved, 56 checked.
- `uv run ruff check .`: passed after correcting nine overlong lines.
- `uv run ruff format --check .`: 135 files already formatted.
- `uv run pytest -q`: 309 passed in 34.70 seconds, with 13,000 existing dependency deprecation warnings.
- `uv run python tools/estimate_aws_costs.py --check`: report and JSON match the model and evidence.
- Existing inventory, sensor-band, assessment-page, and gap-report `--check` commands passed.
- `git diff --check`: passed.

The first workflow attempt stopped at lint errors. No test failed and no existing assertion was weakened.

## Limits and proposed next step

National overlap, valid-pixel yield, output encoding, AWS memory fit, request latency, and daily arrival peaks remain unmeasured.
Forecasts assume constant rates and prices. Service usage, shared infrastructure, and access frequencies remain explicit scenarios.
The JSON covers all workloads, recipes, platforms, stress cases, horizons, and reserve fractions.
The report emphasizes central cases and includes combined stress comparisons. These are not confidence bounds.
Owner review is the next step. AWS calibration, new catalog measurements, and production selection remain separately authorized work.
