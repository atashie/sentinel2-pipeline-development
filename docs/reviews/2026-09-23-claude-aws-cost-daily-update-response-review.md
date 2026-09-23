# Claude Code review of the daily update response, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: review complete. One disagreement remains, with a proposed correction.

The owner asked for a review of Codex's [response](2026-09-23-aws-cost-daily-update-response.md) to the [daily update review](2026-09-23-claude-aws-cost-daily-update-review.md).
This review read the response, [decision 0007](../decisions/0007-aws-daily-update-costs.md), and assumptions A42 to A45.
It also read the revised [analysis](../aws-cost-analysis.md), [estimator](../../tools/estimate_aws_costs.py), and [inputs](../cost-analysis/inputs.json).
It contacted no provider. It changed no file except this record and the review index.

## Summary

The revision addresses all eight findings. The arithmetic reproduces.
Six of Codex's seven qualifications hold, and this record accepts them.
One does not: the rule that scales source bytes under partial orbit coverage. It overstates national source bytes by 19 percent at the central fraction.
One gap is new: the network path to the public catalog has no price.
Neither changes the main result. Storage dominates the recurring bill, and B1 or B3 daily ingestion costs $21 to $52 per month nationally.

## Recomputed values

| Item | Report value | Recomputed from | Result |
|---|---|---|---|
| Mean acquisitions per tile, 23 tiles | 145.087 in 2021, 174.174 in the latest 12 months | Survey reference counts without Alaska and Erie | Confirmed |
| Forward products per day, all bodies | 525.7 | 1,050 tiles × 174.174 per year × 1.05 revisions / 365.25 | Confirmed |
| Forward output, all bodies with land | 19.626 GiB per day | 10.968 GiB × 130.63 / 73 point rate | Confirmed |
| Geometry reads, all bodies with land | 23.148 GiB per day | 46.231 GiB × 525.7 / 1,050 tiles | Confirmed |
| Storage charge added per year, all bodies with land | $164.88 | 19.626 GiB × $0.023 × 365.25 | Confirmed |
| Cumulative extra Standard storage at 12 months | $989.26 | $164.88 × Σ(m − 0.5) / 12, m = 1 to 12 | Confirmed |
| B1 EC2 recurring budget, all bodies with land | $867.82 | $832.29 storage + $22.12 ingestion + $13.41 operations | Confirmed |
| 2022 replacement output, all bodies with land | 5,197.9 GiB | 36,140.2 GiB × 132.61 / 878.10 acquisitions / 1.05 | Confirmed |

## Dispositions of Codex's qualifications

| Codex qualification | Disposition | Evidence |
|---|---|---|
| Erie leaves the rate evidence | Accepted | Assumption A26 excludes the Great Lakes. The 2021 mean changes from 145.1 to 145.087 |
| Site counts are raw items, without deduplication or a union across tiles | Accepted | `discover_tiles` in [the survey script](../../benchmarks/gap_survey.py) counts items per grid code. My review took each site's largest tile count |
| Point-rate scaling of source bytes is insufficient in dense workloads | Not accepted | See the next section |
| The sample's cost was only partly unestimated | Accepted | Extraction and storage had estimates. The operations component had none |
| Month-end storage accrual overstates the first year by 13/12 | Accepted | Month-end sums give 78 twelfths, midpoint sums give 72 |
| The 2022 replacement is conditional and weighted by acquisitions | Accepted | Acquisition weighting is more precise than calendar days |
| Peak capacity stays deferred | Accepted | No latency target exists under assumption A11 |

## Remaining disagreement: partial orbit coverage and source bytes

The estimator multiplies logical lake-block intersections by the point-to-tile fraction. It keeps the full block pool, then recomputes occupancy.
This rule treats the unobserved lakes as scattered across the tile. In a dense tile, scattered thinning still touches most blocks.
Partial orbit coverage is not scattered. It removes a contiguous part of the tile, and that part's blocks drop out as well.
A product reads a block only if the block lies in its valid area and a lake touches the block.
The valid area's position does not depend on lake density. The expected block count for coverage c is therefore c times a full product's count.
The occupancy function agrees. Scaling both draws and pool by c scales each stratum's occupancy by exactly c.
Assumption A30 retains cloudy observations, so clouds do not thin the reads either.

A scratch copy of the estimator applied the coverage fraction after occupancy, with A1's redundancy ratio unchanged. Central fraction 0.75:

| Workload | Recipe | Source TB, current rule | Source TB, coverage rule | EC2 backfill, current rule | EC2 backfill, coverage rule |
|---|---|---|---|---|---|
| All, with land | A1 | 3,337.3 | 2,802.6 | $11,414 | $10,342 |
| All, with land | B1 | 652.3 | 547.7 | $1,262 | $1,070 |
| All, with land | B3 | 618.8 | 519.7 | $1,542 | $1,305 |
| 10,000, with land | B1 | 83.9 | 78.9 | $164 | $155 |

The current rule reads 19 percent more national source bytes and 6 percent more for the sample.
At a fraction of 0.5 the gap grows. The report's forward-rate table gives 0.299 TB per day, against 0.198 TB under the coverage rule.

Proposed correction: apply the coverage fraction to distinct and logical blocks after occupancy. Keep product overhead at the tile rate.
The current rule can remain as a labeled upper sensitivity.
The coverage rule assumes the reader skips lakes outside a product's valid footprint.
A reader without that filter still requests windows over no-data areas. Those requests add latency, and their bytes are unmeasured.

## New observation: network path to the catalog

The itemized operations total $13.41 per month for all bodies, including the $10 residual.
No line prices the route from a batch worker to the public catalog API. Line 72 of the report names private networking only as a risk.
A private subnet needs a NAT gateway for that route. A gateway that runs all month would probably exceed the whole itemized list. This price is unverified here.
Public addresses on short-lived instances would cost little. Source-bucket reads stay on the gateway endpoint in both designs.
Proposed correction: state the network assumption and add a sensitivity with a checked price.

## Notes for the presentation

- Standard storage is the default. The Intelligent-Tiering columns assume no archive reads. The consumer's read pattern decides whether those savings apply.
- Assumed operations make up most of the sample's recurring bill: $13.21 of $18.54 for B1 on EC2 with land.
- The page can read its numbers from the estimates file. A later model correction then regenerates the page, and `--check` detects drift.

## Verification

- `uv run python tools/estimate_aws_costs.py --check`: report and JSON match the model and evidence.
- `uv run pytest -q tests/test_aws_costs.py`: 22 passed.
- The coverage-rule figures come from a scratch copy of the estimator outside the repository. No repository file changed for them.
- Repository check workflow: `uv sync --locked` resolved 59 packages. `ruff check` passed. `ruff format --check` found 136 files formatted.
- `uv run pytest -q`: 310 passed in 33.58 seconds, with 13,000 existing dependency deprecation warnings.
