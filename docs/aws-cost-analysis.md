# AWS Sentinel-2 cost analysis, revised 2026-09-23

Status: offline planning estimate for owner review. History remains 2021-01-01 through 2026-09-22 for comparison with the initial analysis.

**Source-block coverage and archive access patterns dominate this estimate. Neither lake count nor selected output pixels alone predicts the bill.**
The central national cases read a substantial fraction of modeled source blocks.
The count-uniform sample reads roughly 84 TB to retain approximately 72 GiB with the land buffer.
Those volumes are modeled expectations, not measured national throughput or results from an actual random sample.

The [review response](reviews/2026-09-23-aws-cost-review-response.md) addresses all nine findings.
The initial model lacked byte back-tests and important sensitivities. Its national A1 headline extrapolated far beyond observed reuse ratios.
The revised report tests byte accounting against both cohorts and separates calibration, holdout checks, and national extrapolation.
Storage class, network concurrency, preparation packing, Lambda memory, purchasing options, serving transfer, and object compaction now have explicit scenarios.

The [assumption registry](assumptions.md#aws-cost-analysis) owns scope and provenance.
[Inputs](cost-analysis/inputs.json) own numeric assumptions. [Estimates](cost-analysis/estimates.json) contain generated results, components, and sensitivities.
[Source-byte checks](cost-analysis/cohort-blocks.json) bind the frozen geometry and measurement evidence.
The original [source checks](assessment-checks/aws-cost-analysis-sources.json) and [additional checks](assessment-checks/aws-cost-review-sources.json) qualify AWS prices and service constraints.

## Scope and central accounting

The four workloads cover all eligible contiguous-US water bodies and a count-uniform sample, each with and without the agreed land buffer.
The Great Lakes are excluded. Natural lakes, reservoirs, and permanent artificial ponds down to the agreed minimum size remain included.
A1 processes lakes separately. B1 shares direct raster access. B3 shares computed source blocks.
All three retain identical logical output within a workload. No recipe receives a storage-volume advantage.

**Same-region serving remains the owner-confirmed baseline.** Source access, ingestion, output storage, and the model consumer share Oregon.
**Documented:** S3 ingress and S3 transfer to same-region AWS services incur no transfer charge. Requests and storage remain billable.
[AWS S3 pricing](https://aws.amazon.com/s3/pricing/).
The frozen [provider record](../benchmarks/results/lazy-reader-workloads.json) identifies source buckets, region, and payer.
Source-request charges remain with that source's payer. Source traffic still consumes compute time and network capacity.
The network path assumes same-region S3 gateway access. Paid NAT traffic is excluded and can dominate these source volumes.
**Documented:** S3 gateway endpoints add no endpoint charge. [AWS gateway documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html).

All costs are USD planning estimates. Price proxies, geographic assumptions, and hardware extrapolations prevent quote-level precision.
Backfill totals include preparation, extraction, scratch storage, and modeled writes. Storage accruing during backfill is additional.
Lambda totals include EC2 preparation. Forward budgets include itemized operations and an explicit residual allowance.
The central A1 byte ratio is constrained to the observed envelope. The extrapolation table explicitly shows the alternative outside that envelope.

## Daily updates and accumulated costs

The [daily-update review](reviews/2026-09-23-claude-aws-cost-daily-update-review.md) correctly identified missing forward rates, overheads, and storage accrual.
The [response](reviews/2026-09-23-aws-cost-daily-update-response.md) records every disposition and the remaining disagreements.
[Decision 0007](decisions/0007-aws-daily-update-costs.md) records the revised method.

**Measured:** The [saved gap survey](../benchmarks/results/gap-survey.json) contains acquisition counts for purpose-selected tiles and footprint item counts for site points.
The eligible evidence subset removes Alaska, non-US sites, and the Erie site. Removing Erie from evidence does not exclude neighboring ponds in its tile.
The generated evidence contains the selected tile identifiers, annual counts, and latest monthly distribution.
Issue I-25 in the [inventory](options-inventory.json) identifies variable acquisition frequency.
These sites do not establish national orbital overlap or complete valid-pixel coverage.

The site-point values count catalog items, including possible duplicates. They are neither deduplicated observation counts nor unions across overlapping tiles.
The midpoint between half-tile and full-tile observation rates is a planning scenario, not the survey's observed national mean.
Low and high cases use the endpoint fractions. Applying those fractions backward through history is another unverified extrapolation.
Historical tile counts integrate complete saved months, then extrapolate the remaining cutoff days using the recent rate.
The earlier frequency remains a sensitivity. Backfill and forward estimates now use distinct time periods with consistent definitions.

Point frequency scales retained output. Tile frequency scales product processing and prepared-geometry reads.
Logical lake-block intersections per product receive the point-to-tile activity fraction before the model recomputes block occupancy.
Dense products can still read most modeled blocks when only some lakes have observations. Source bytes therefore do not scale directly with point frequency.
Tile overlap and retained routine revisions remain separate multipliers.

Each daily batch reloads prepared geometry per processed product. Geometry GETs, transfer time, and deserialization work are charged.
EC2 starts a small fleet, enlarged when average work cannot finish within a day. This arithmetic minimum is not a peak-capacity recommendation.
Lambda partitions product work and monthly compaction separately. Each bounded task receives startup time.
Monthly compaction reads daily objects, writes packed objects, and incurs compute charges. Its assumed throughput includes reading and rewriting payloads.
Unchanged geometry avoids preparation reruns. New water bodies and changed polygons remain outside this update scenario.

The operations example itemizes scheduling, queue requests, ledger requests and storage, logs, alarms, metrics, registry storage, and catalog reconciliation compute.
**Documented:** [Independent price checks](assessment-checks/aws-cost-daily-sources.json) confirm the cited service units and qualified regional proxies.
Consumption, payload sizes, log retention, and residual contingency remain unsourced assumptions. Gross estimates exclude shared free allowances.
This example does not select an orchestrator or implementation. Private networking, verbose logs, or per-lake ledgers can change its costs substantially.
The old fixed allowance remains only in explicitly labeled historical-proration JSON comparators.

Forecasts start with a completed backfill at the historical cutoff and constant forward rates. Horizons use average months of 365.25 divided by twelve days.
Month-end bills show the run rate at that horizon. Cumulative bills integrate uniform arrivals within each month.
This avoids charging the entire month's new output as though it existed on the first day.
Standard pricing applies marginal capacity tiers. Intelligent-Tiering begins with freshly written history in frequent access and no subsequent archive reads.
Daily temporary objects remain Standard until monthly compaction. Compacted objects then begin their own access clocks.
Frequent serving can erase Intelligent-Tiering savings. The separate serving sensitivities price transfer, while consumer compute remains excluded.

Annual reprocessing reserves replace a stated fraction of the fixed cutoff history, retaining one new copy per replaced acquisition.
Their storage growth and horizon budgets are included in the JSON. Reserves are expectations, not evenly arriving campaigns or capacity guarantees.
The routine revision multiplier is removed before charging each additional replacement. Existing geometry remains reusable.
The named 2022 replacement uses acquisition-weighted coverage, rather than the fraction of calendar days alone.
It is conditional on replacement assets becoming usable and the owner electing to reprocess. Neither event is predicted by this model.
Campaign estimates assume shared batch infrastructure. Dedicated campaign launches and extra reconciliation require additional allowances.

The busiest measured month is reported as a monthly count, not a busiest-day measurement.
No daily distribution or latency target establishes a peak fleet. The original one-hour daily capacity column has been removed.
AWS overhead measurements, national metadata sampling, and production choices remain deferred.

<!-- BEGIN GENERATED COST TABLES -->

### Saved survey acquisition evidence, 23 selected tiles

| Period | Mean acquisitions per tile |
| --- | --- |
| 2021 | 145.087 |
| 2022 | 144.739 |
| 2023 | 143.870 |
| 2024 | 147.826 |
| 2025 | 172.174 |
| 2025-09 through 2026-08 | 174.174 |

Largest recent monthly count: 358 acquisitions across the selected tiles in 2026-08. This is not a measured daily peak.

### Historical-rate revision with other central assumptions fixed

| Workload | Legacy history GiB | Revised history GiB | Legacy B1 backfill | Revised B1 backfill |
| --- | --- | --- | --- | --- |
| All, with land | 22,933.6 | 36,140.2 | $690.35 | $1,262.04 |
| All, water + shore | 8,853.2 | 13,951.4 | $675.32 | $1,234.22 |
| 10,000, with land | 45.9 | 72.3 | $96.64 | $163.80 |
| 10,000, water + shore | 17.7 | 27.9 | $94.00 | $159.07 |

### Retained storage and central B1 recurring budget

| Workload | History GiB | New GiB/day | S3/month | B1 EC2 total/month |
| --- | --- | --- | --- | --- |
| All, with land | 36,140.2 | 19.626 | $832.29 | $867.82 |
| All, water + shore | 13,951.4 | 7.576 | $321.29 | $355.86 |
| 10,000, with land | 72.3 | 0.039 | $1.66 | $18.54 |
| 10,000, water + shore | 27.9 | 0.015 | $0.64 | $17.44 |

History excludes reusable geometry. S3 includes it. Total uses cutoff retention, forward ingestion, itemized operations, and the residual allowance.

### Geography and selected pixels per acquisition epoch

| Workload | Tiles | Historical tile-dates | 10 m Mpx | 20 m Mpx | 60 m Mpx |
| --- | --- | --- | --- | --- | --- |
| All, with land | 1,050 | 922,005 | 3,846.322 | 961.580 | 106.842 |
| All, water + shore | 1,050 | 922,005 | 1,407.630 | 381.315 | 58.216 |
| 10,000, with land | 867 | 761,463 | 7.693 | 1.923 | 0.214 |
| 10,000, water + shore | 867 | 761,463 | 2.815 | 0.763 | 0.116 |

Mpx means million grid cells, before overlap and revision multipliers. Tile-dates exclude repeated product revisions.

### Backfill cost and elapsed time

| Workload | Recipe | EC2 cost | Lambda cost | 32 EC2 hours | 64 Lambda hours |
| --- | --- | --- | --- | --- | --- |
| All, with land | A1 | $11,414 | $23,527 | 1,961.7 | 2,044.4 |
| All, with land | B1 | $1,262 | $2,631 | 216.4 | 231.2 |
| All, with land | B3 | $1,542 | $2,836 | 264.6 | 248.9 |
| All, water + shore | A1 | $11,302 | $23,291 | 1,942.6 | 2,024.2 |
| All, water + shore | B1 | $1,234 | $2,576 | 212.0 | 226.5 |
| All, water + shore | B3 | $1,510 | $2,777 | 259.3 | 243.9 |
| 10,000, with land | A1 | $199 | $418 | 34.2 | 36.3 |
| 10,000, with land | B1 | $164 | $346 | 28.2 | 30.1 |
| 10,000, with land | B3 | $200 | $373 | 34.3 | 32.3 |
| 10,000, water + shore | A1 | $193 | $406 | 33.2 | 35.2 |
| 10,000, water + shore | B1 | $159 | $336 | 27.3 | 29.2 |
| 10,000, water + shore | B3 | $194 | $362 | 33.3 | 31.4 |

### Extraction work and capacity

| Workload | Recipe | Source TB | CPU hours | EC2 for 7 days |
| --- | --- | --- | --- | --- |
| All, with land | A1 | 3,337.3 | 25,249 | 374 |
| All, with land | B1 | 652.3 | 4,060 | 42 |
| All, with land | B3 | 618.8 | 6,603 | 51 |
| All, water + shore | A1 | 3,285.8 | 24,859 | 371 |
| All, water + shore | B1 | 642.2 | 3,997 | 41 |
| All, water + shore | B3 | 609.3 | 6,501 | 50 |
| 10,000, with land | A1 | 89.9 | 680 | 7 |
| 10,000, with land | B1 | 83.9 | 522 | 6 |
| 10,000, with land | B3 | 79.6 | 850 | 7 |
| 10,000, water + shore | A1 | 86.9 | 658 | 7 |
| 10,000, water + shore | B1 | 81.4 | 506 | 6 |
| 10,000, water + shore | B3 | 77.2 | 824 | 7 |

### Forward daily work and storage growth

| Workload | Products/day | Output GiB/day | Geometry GiB/day | S3 monthly charge added/day | S3 monthly charge added/year |
| --- | --- | --- | --- | --- | --- |
| All, with land | 525.7 | 19.626 | 23.148 | $0.4514 | $164.88 |
| All, water + shore | 525.7 | 7.576 | 8.907 | $0.1743 | $63.65 |
| 10,000, with land | 434.2 | 0.039 | 0.046 | $0.0009 | $0.33 |
| 10,000, water + shore | 434.2 | 0.015 | 0.018 | $0.0003 | $0.13 |

### Daily ingestion, including startup, geometry, requests, and compaction

| Workload | Recipe | EC2 hours/day | Lambda slot-hours/day | EC2/day | Lambda/day | EC2/month | Lambda/month |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All, with land | A1 | 34.27 | 71.32 | $6.240 | $12.851 | $189.93 | $391.16 |
| All, with land | B1 | 3.94 | 8.82 | $0.727 | $1.598 | $22.12 | $48.63 |
| All, with land | B3 | 4.78 | 9.43 | $0.879 | $1.708 | $26.74 | $51.98 |
| All, water + shore | A1 | 33.84 | 70.41 | $6.162 | $12.688 | $187.56 | $386.20 |
| All, water + shore | B1 | 3.77 | 8.45 | $0.695 | $1.531 | $21.15 | $46.61 |
| All, water + shore | B3 | 4.59 | 9.05 | $0.845 | $1.640 | $25.70 | $49.91 |
| 10,000, with land | A1 | 0.73 | 1.85 | $0.140 | $0.341 | $4.25 | $10.38 |
| 10,000, with land | B1 | 0.62 | 1.64 | $0.120 | $0.303 | $3.67 | $9.21 |
| 10,000, with land | B3 | 0.73 | 1.72 | $0.140 | $0.317 | $4.26 | $9.64 |
| 10,000, water + shore | A1 | 0.71 | 1.82 | $0.136 | $0.334 | $4.15 | $10.18 |
| 10,000, water + shore | B1 | 0.61 | 1.61 | $0.118 | $0.297 | $3.59 | $9.04 |
| 10,000, water + shore | B3 | 0.71 | 1.69 | $0.137 | $0.311 | $4.16 | $9.46 |

These are average-day work totals, not peak-day capacity or a latency promise. Retention and shared operations are separate.

### Illustrative daily operations, monthly gross costs

| Component | All, with land | All, water + shore | 10,000, with land | 10,000, water + shore |
| --- | --- | --- | --- | --- |
| scheduler | $0.0000 | $0.0000 | $0.0000 | $0.0000 |
| queue | $0.0384 | $0.0384 | $0.0317 | $0.0317 |
| ledger requests | $0.0680 | $0.0680 | $0.0562 | $0.0562 |
| ledger storage at cutoff | $0.2478 | $0.2478 | $0.2047 | $0.2047 |
| logs ingest | $0.8001 | $0.8001 | $0.6608 | $0.6608 |
| logs retained | $0.0142 | $0.0142 | $0.0117 | $0.0117 |
| alarms | $0.5000 | $0.5000 | $0.5000 | $0.5000 |
| metrics | $1.5000 | $1.5000 | $1.5000 | $1.5000 |
| registry | $0.2000 | $0.2000 | $0.2000 | $0.2000 |
| catalog and reconciliation compute | $0.0457 | $0.0457 | $0.0457 | $0.0457 |
| residual allowance | $10.0000 | $10.0000 | $10.0000 | $10.0000 |

### Storage accrual without reprocessing or reads

| Workload | Month | Standard/month | IT/month | Cumulative extra Standard for updates | Cumulative all Standard | Cumulative all IT |
| --- | --- | --- | --- | --- | --- | --- |
| All, with land | 12 | $997.16 | $196.67 | $989.26 | $10,976.71 | $3,508.45 |
| All, with land | 36 | $1,320.42 | $254.31 | $8,868.04 | $38,830.41 | $9,052.41 |
| All, with land | 60 | $1,635.84 | $311.94 | $24,368.30 | $74,305.58 | $15,979.61 |
| All, water + shore | 12 | $384.94 | $75.92 | $381.89 | $4,237.39 | $1,354.37 |
| All, water + shore | 36 | $512.24 | $98.17 | $3,437.00 | $15,003.50 | $3,494.52 |
| All, water + shore | 60 | $639.53 | $120.42 | $9,547.21 | $28,824.71 | $6,168.64 |
| 10,000, with land | 12 | $1.99 | $0.39 | $1.98 | $21.95 | $7.02 |
| 10,000, with land | 36 | $2.65 | $0.51 | $17.81 | $77.73 | $18.11 |
| 10,000, with land | 60 | $3.31 | $0.62 | $49.46 | $149.34 | $31.98 |
| 10,000, water + shore | 12 | $0.77 | $0.15 | $0.76 | $8.47 | $2.71 |
| 10,000, water + shore | 36 | $1.02 | $0.20 | $6.87 | $30.01 | $7.01 |
| 10,000, water + shore | 60 | $1.28 | $0.24 | $19.09 | $57.65 | $12.38 |

### Monthly bill at each horizon, including updates, operations, and retention

| Workload | Recipe | Month | EC2 Standard | Lambda Standard | EC2 IT | Lambda IT |
| --- | --- | --- | --- | --- | --- | --- |
| All, with land | A1 | 12 | $1,200.55 | $1,401.79 | $400.06 | $601.29 |
| All, with land | A1 | 36 | $1,523.91 | $1,725.14 | $457.79 | $659.03 |
| All, with land | A1 | 60 | $1,839.43 | $2,040.66 | $515.53 | $716.76 |
| All, with land | B1 | 12 | $1,032.74 | $1,059.26 | $232.25 | $258.76 |
| All, with land | B1 | 36 | $1,356.10 | $1,382.62 | $289.98 | $316.50 |
| All, with land | B1 | 60 | $1,671.61 | $1,698.13 | $347.72 | $374.23 |
| All, with land | B3 | 12 | $1,037.37 | $1,062.61 | $236.88 | $262.11 |
| All, with land | B3 | 36 | $1,360.73 | $1,385.97 | $294.61 | $319.85 |
| All, with land | B3 | 60 | $1,676.24 | $1,701.48 | $352.34 | $377.58 |
| All, water + shore | A1 | 12 | $585.96 | $784.61 | $276.94 | $475.59 |
| All, water + shore | A1 | 36 | $713.36 | $912.00 | $299.29 | $497.94 |
| All, water + shore | A1 | 60 | $840.75 | $1,039.40 | $321.64 | $520.28 |
| All, water + shore | B1 | 12 | $419.55 | $445.02 | $110.53 | $136.00 |
| All, water + shore | B1 | 36 | $546.95 | $572.41 | $132.88 | $158.34 |
| All, water + shore | B1 | 60 | $674.34 | $699.80 | $155.23 | $180.69 |
| All, water + shore | B3 | 12 | $424.11 | $448.31 | $115.09 | $139.29 |
| All, water + shore | B3 | 36 | $551.50 | $575.71 | $137.44 | $161.64 |
| All, water + shore | B3 | 60 | $678.90 | $703.10 | $159.78 | $183.99 |
| 10,000, with land | A1 | 12 | $19.49 | $25.63 | $17.89 | $24.03 |
| 10,000, with land | A1 | 36 | $20.23 | $26.37 | $18.09 | $24.23 |
| 10,000, with land | A1 | 60 | $20.98 | $27.11 | $18.29 | $24.42 |
| 10,000, with land | B1 | 12 | $18.91 | $24.45 | $17.31 | $22.85 |
| 10,000, with land | B1 | 36 | $19.65 | $25.19 | $17.51 | $23.05 |
| 10,000, with land | B1 | 60 | $20.39 | $25.93 | $17.70 | $23.25 |
| 10,000, with land | B3 | 12 | $19.51 | $24.88 | $17.91 | $23.28 |
| 10,000, with land | B3 | 36 | $20.25 | $25.63 | $18.10 | $23.48 |
| 10,000, with land | B3 | 60 | $20.99 | $26.37 | $18.30 | $23.68 |
| 10,000, water + shore | A1 | 12 | $18.17 | $24.20 | $17.55 | $23.58 |
| 10,000, water + shore | A1 | 36 | $18.51 | $24.53 | $17.68 | $23.70 |
| 10,000, water + shore | A1 | 60 | $18.84 | $24.87 | $17.80 | $23.83 |
| 10,000, water + shore | B1 | 12 | $17.61 | $23.06 | $16.99 | $22.44 |
| 10,000, water + shore | B1 | 36 | $17.94 | $23.40 | $17.12 | $22.57 |
| 10,000, water + shore | B1 | 60 | $18.28 | $23.73 | $17.24 | $22.70 |
| 10,000, water + shore | B3 | 12 | $18.18 | $23.48 | $17.57 | $22.86 |
| 10,000, water + shore | B3 | 36 | $18.52 | $23.82 | $17.69 | $22.99 |
| 10,000, water + shore | B3 | 60 | $18.86 | $24.15 | $17.82 | $23.11 |

### Cumulative backfill, updates, operations, and retention

| Workload | Recipe | Month | EC2 Standard | Lambda Standard | EC2 IT | Lambda IT |
| --- | --- | --- | --- | --- | --- | --- |
| All, with land | A1 | 12 | $24,831.46 | $39,358.46 | $17,363.20 | $31,890.19 |
| All, with land | A1 | 36 | $57,567.72 | $76,924.26 | $27,789.71 | $47,146.26 |
| All, with land | A1 | 60 | $97,927.80 | $122,113.90 | $39,601.82 | $63,787.92 |
| All, with land | B1 | 12 | $12,665.40 | $14,353.04 | $5,197.13 | $6,884.78 |
| All, with land | B1 | 36 | $41,374.16 | $43,698.19 | $11,596.15 | $13,920.18 |
| All, with land | B1 | 60 | $77,706.75 | $80,667.17 | $19,380.78 | $22,341.20 |
| All, with land | B3 | 12 | $13,000.80 | $14,597.58 | $5,532.53 | $7,129.31 |
| All, with land | B3 | 36 | $41,820.59 | $44,023.12 | $12,042.59 | $14,245.11 |
| All, with land | B3 | 60 | $78,264.22 | $81,072.49 | $19,938.24 | $22,746.51 |
| All, water + shore | A1 | 12 | $17,951.01 | $32,324.60 | $15,067.99 | $29,441.58 |
| All, water + shore | A1 | 36 | $33,542.82 | $52,683.90 | $22,033.84 | $41,174.93 |
| All, water + shore | A1 | 60 | $52,192.11 | $76,100.68 | $29,536.03 | $53,444.61 |
| All, water + shore | B1 | 12 | $5,886.68 | $7,533.51 | $3,003.66 | $4,650.49 |
| All, water + shore | B1 | 36 | $17,484.68 | $19,742.62 | $5,975.70 | $8,233.64 |
| All, water + shore | B1 | 60 | $32,140.15 | $35,009.21 | $9,484.08 | $12,353.13 |
| All, water + shore | B3 | 12 | $6,216.89 | $7,774.26 | $3,333.88 | $4,891.25 |
| All, water + shore | B3 | 36 | $17,924.21 | $20,062.53 | $6,415.23 | $8,553.55 |
| All, water + shore | B3 | 60 | $32,689.00 | $35,408.26 | $10,032.93 | $12,752.19 |
| 10,000, with land | A1 | 12 | $430.76 | $723.51 | $415.83 | $708.57 |
| 10,000, with land | A1 | 36 | $907.50 | $1,347.52 | $847.88 | $1,287.90 |
| 10,000, with land | A1 | 60 | $1,402.01 | $1,989.31 | $1,284.65 | $1,871.95 |
| 10,000, with land | B1 | 12 | $388.51 | $637.59 | $373.58 | $622.66 |
| 10,000, with land | B1 | 36 | $851.26 | $1,233.36 | $791.64 | $1,173.74 |
| 10,000, with land | B1 | 60 | $1,331.79 | $1,846.91 | $1,214.43 | $1,729.55 |
| 10,000, with land | B3 | 12 | $431.67 | $669.06 | $416.73 | $654.12 |
| 10,000, with land | B3 | 36 | $908.70 | $1,275.17 | $849.08 | $1,215.55 |
| 10,000, with land | B3 | 60 | $1,403.52 | $1,899.06 | $1,286.16 | $1,781.70 |
| 10,000, water + shore | A1 | 12 | $410.10 | $694.89 | $404.34 | $689.13 |
| 10,000, water + shore | A1 | 36 | $850.20 | $1,279.64 | $827.20 | $1,256.64 |
| 10,000, water + shore | A1 | 60 | $1,298.35 | $1,872.44 | $1,253.07 | $1,827.17 |
| 10,000, water + shore | B1 | 12 | $369.35 | $612.07 | $363.59 | $606.31 |
| 10,000, water + shore | B1 | 36 | $795.95 | $1,169.59 | $772.95 | $1,146.59 |
| 10,000, water + shore | B1 | 60 | $1,230.61 | $1,735.16 | $1,185.34 | $1,689.89 |
| 10,000, water + shore | B3 | 12 | $411.18 | $642.57 | $405.42 | $636.81 |
| 10,000, water + shore | B3 | 36 | $851.63 | $1,210.11 | $828.64 | $1,187.12 |
| 10,000, water + shore | B3 | 60 | $1,300.14 | $1,785.72 | $1,254.87 | $1,740.45 |

IT assumes no archive reads and starts the completed backfill in frequent access. Cumulative totals exclude storage during backfill and consumer compute.

### Annual reprocessing sensitivity, retaining each replacement

| Workload | Recipe | 5% EC2/year | 5% Lambda/year | 20% EC2/year | 20% Lambda/year | 20% new GiB/year |
| --- | --- | --- | --- | --- | --- | --- |
| All, with land | A1 | $545.03 | $1,126.87 | $2,180.12 | $4,507.47 | 6,883.8 |
| All, with land | B1 | $61.59 | $140.09 | $246.34 | $560.38 | 6,883.8 |
| All, with land | B3 | $74.91 | $149.74 | $299.65 | $598.98 | 6,883.8 |
| All, water + shore | A1 | $538.21 | $1,112.60 | $2,152.82 | $4,450.40 | 2,657.4 |
| All, water + shore | B1 | $58.80 | $134.28 | $235.22 | $537.13 | 2,657.4 |
| All, water + shore | B3 | $71.93 | $143.78 | $287.70 | $575.13 | 2,657.4 |
| 10,000, with land | A1 | $10.11 | $29.92 | $40.45 | $119.66 | 13.8 |
| 10,000, with land | B1 | $8.43 | $26.53 | $33.73 | $106.10 | 13.8 |
| 10,000, with land | B3 | $10.15 | $27.77 | $40.59 | $111.07 | 13.8 |
| 10,000, water + shore | A1 | $9.82 | $29.31 | $39.30 | $117.25 | 5.3 |
| 10,000, water + shore | B1 | $8.21 | $26.04 | $32.82 | $104.18 | 5.3 |
| 10,000, water + shore | B3 | $9.87 | $27.25 | $39.47 | $108.99 | 5.3 |

### Conditional replacement of January through November 2022

| Workload | Recipe | EC2 event | Lambda event | Additional retained GiB |
| --- | --- | --- | --- | --- |
| All, with land | A1 | $1,646.18 | $3,403.54 | 5,197.9 |
| All, with land | B1 | $186.01 | $423.13 | 5,197.9 |
| All, with land | B3 | $226.26 | $452.28 | 5,197.9 |
| All, water + shore | A1 | $1,625.57 | $3,360.45 | 2,006.6 |
| All, water + shore | B1 | $177.61 | $405.58 | 2,006.6 |
| All, water + shore | B3 | $217.24 | $434.28 | 2,006.6 |
| 10,000, with land | A1 | $30.54 | $90.36 | 10.4 |
| 10,000, with land | B1 | $25.47 | $80.12 | 10.4 |
| 10,000, with land | B3 | $30.65 | $83.87 | 10.4 |
| 10,000, water + shore | A1 | $29.67 | $88.54 | 4.0 |
| 10,000, water + shore | B1 | $24.78 | $78.66 | 4.0 |
| 10,000, water + shore | B3 | $29.80 | $82.30 | 4.0 |

### Forward-rate sensitivity with other central assumptions fixed

| Workload | Rate scenario | Tile/year | Point/year | Output GiB/day | B1 source TB/day |
| --- | --- | --- | --- | --- | --- |
| All, with land | Legacy 73 | 73.0 | 73.0 | 10.968 | 0.166 |
| All, with land | Recent tile, half point | 174.2 | 87.1 | 13.084 | 0.299 |
| All, with land | Recent tile, full point | 174.2 | 174.2 | 26.168 | 0.397 |
| All, water + shore | Legacy 73 | 73.0 | 73.0 | 4.234 | 0.164 |
| All, water + shore | Recent tile, half point | 174.2 | 87.1 | 5.051 | 0.294 |
| All, water + shore | Recent tile, full point | 174.2 | 174.2 | 10.102 | 0.391 |
| 10,000, with land | Legacy 73 | 73.0 | 73.0 | 0.022 | 0.024 |
| 10,000, with land | Recent tile, half point | 174.2 | 87.1 | 0.026 | 0.032 |
| 10,000, with land | Recent tile, full point | 174.2 | 174.2 | 0.052 | 0.057 |
| 10,000, water + shore | Legacy 73 | 73.0 | 73.0 | 0.008 | 0.023 |
| 10,000, water + shore | Recent tile, half point | 174.2 | 87.1 | 0.010 | 0.031 |
| 10,000, water + shore | Recent tile, full point | 174.2 | 174.2 | 0.020 | 0.056 |

### Daily ingestion combined stress cases

| Workload | Recipe | Low EC2/day | High EC2/day | Low Lambda/day | High Lambda/day |
| --- | --- | --- | --- | --- | --- |
| All, with land | A1 | $0.706 | $184.240 | $1.672 | $376.675 |
| All, with land | B1 | $0.133 | $9.414 | $0.381 | $20.673 |
| All, with land | B3 | $0.162 | $10.709 | $0.401 | $21.380 |
| All, water + shore | A1 | $0.695 | $183.882 | $1.648 | $375.908 |
| All, water + shore | B1 | $0.129 | $9.055 | $0.372 | $19.905 |
| All, water + shore | B3 | $0.157 | $10.351 | $0.391 | $20.612 |
| 10,000, with land | A1 | $0.027 | $1.113 | $0.092 | $2.419 |
| 10,000, with land | B1 | $0.024 | $0.875 | $0.086 | $1.945 |
| 10,000, with land | B3 | $0.027 | $0.988 | $0.088 | $2.007 |
| 10,000, water + shore | A1 | $0.026 | $1.082 | $0.091 | $2.353 |
| 10,000, water + shore | B1 | $0.023 | $0.848 | $0.085 | $1.886 |
| 10,000, water + shore | B3 | $0.027 | $0.957 | $0.087 | $1.945 |

### Combined storage stress cases

| Workload | Low GiB | Base GiB | High GiB | Low S3/month | High S3/month |
| --- | --- | --- | --- | --- | --- |
| All, with land | 7,892.9 | 36,140.2 | 202,044.5 | $181.95 | $4,499.42 |
| All, water + shore | 3,915.9 | 13,951.4 | 56,467.7 | $90.27 | $1,294.39 |
| 10,000, with land | 17.1 | 72.3 | 392.3 | $0.39 | $9.03 |
| 10,000, water + shore | 5.6 | 27.9 | 170.0 | $0.13 | $3.91 |

### Combined backfill stress cases

| Workload | Recipe | Low EC2 | Base EC2 | High EC2 | Low–high Lambda |
| --- | --- | --- | --- | --- | --- |
| All, with land | A1 | $1,271 | $11,414 | $337,880 | $2,899–$692,354 |
| All, with land | B1 | $217 | $1,262 | $17,041 | $501–$36,971 |
| All, with land | B3 | $269 | $1,542 | $19,426 | $538–$38,285 |
| All, water + shore | A1 | $1,255 | $11,302 | $337,751 | $2,863–$692,109 |
| All, water + shore | B1 | $213 | $1,234 | $16,912 | $493–$36,726 |
| All, water + shore | B3 | $265 | $1,510 | $19,297 | $530–$38,040 |
| 10,000, with land | A1 | $32 | $199 | $1,915 | $73–$4,140 |
| 10,000, with land | B1 | $26 | $164 | $1,478 | $61–$3,260 |
| 10,000, with land | B3 | $33 | $200 | $1,686 | $65–$3,374 |
| 10,000, water + shore | A1 | $31 | $193 | $1,860 | $71–$4,019 |
| 10,000, water + shore | B1 | $26 | $159 | $1,429 | $59–$3,150 |
| 10,000, water + shore | B3 | $32 | $194 | $1,630 | $64–$3,261 |

### Measured-cohort byte back-tests

| Held-out cohort | Recipe | Observed MB | Predicted MB | Error |
| --- | --- | --- | --- | --- |
| dispersed | B-raster | 569.7 | 589.3 | +3.5% |
| dispersed | B-lazy | 534.9 | 564.6 | +5.6% |
| florida | B-raster | 352.0 | 340.2 | -3.3% |
| florida | B-lazy | 337.3 | 319.5 | -5.3% |

Predictions use the other cohort's requested/decoded ratio and the held-out cohort's actual blocks. They do not validate national block occupancy.

### National buffered latency and effective-concurrency sensitivity

| Latency ms | B1 concurrency | B3 concurrency | B1 EC2 backfill | B3 EC2 backfill |
| --- | --- | --- | --- | --- |
| 3.0 | 1 | 1 | $1,029 | $1,321 |
| 3.0 | 1 | 2 | $1,029 | $1,273 |
| 3.0 | 2 | 2 | $979 | $1,273 |
| 3.0 | 4 | 4 | $954 | $1,250 |
| 10.0 | 1 | 1 | $1,262 | $1,542 |
| 10.0 | 1 | 2 | $1,262 | $1,384 |
| 10.0 | 2 | 2 | $1,096 | $1,384 |
| 10.0 | 4 | 4 | $1,013 | $1,305 |
| 30.0 | 1 | 1 | $1,927 | $2,174 |
| 30.0 | 1 | 2 | $1,927 | $1,700 |
| 30.0 | 2 | 2 | $1,428 | $1,700 |
| 30.0 | 4 | 4 | $1,179 | $1,463 |

### National buffered source-block coverage sensitivity

| Available block fraction | B1 source TB | B1 EC2 backfill |
| --- | --- | --- |
| 20% | 269.6 | $558 |
| 45% | 496.4 | $975 |
| 70% | 652.3 | $1,262 |
| 95% | 779.6 | $1,496 |

### A1 measured-ratio scenario versus repeat-read extrapolation

| Workload | Central EC2 | Extrapolated EC2 | Extrapolated A1/B1 source bytes |
| --- | --- | --- | --- |
| All, with land | $11,414 | $55,797 | 39.0× |
| All, water + shore | $11,302 | $53,882 | 38.2× |
| 10,000, with land | $199 | $187 | 1.0× |
| 10,000, water + shore | $193 | $182 | 1.0× |

### National buffered preparation packing

| Workers/instance | GiB/worker | Preparation instance-hours | Preparation charge |
| --- | --- | --- | --- |
| 1 | 3 | 398.8 | $72.49 |
| 2 | 3 | 199.4 | $36.25 |
| 4 | 1.5 | 99.7 | $18.12 |

### Storage-class monthly sensitivities

| Workload | Standard | IA, no reads | IA, one scan | IT, mature cold | IT, monthly scan |
| --- | --- | --- | --- | --- | --- |
| All, with land | $832.29 | $459.00 | $841.02 | $167.54 | $833.13 |
| All, water + shore | $321.29 | $177.19 | $324.66 | $64.68 | $321.62 |
| 10,000, with land | $1.66 | $0.92 | $1.68 | $0.34 | $1.67 |
| 10,000, water + shore | $0.64 | $0.35 | $0.65 | $0.13 | $0.64 |

Storage-class rows exclude compute and operations overhead. Cold cases require objects to age after ingestion without historical reads. IA retrieval and an unverified request-price allowance are included.

### National buffered purchase-option sensitivity

| Recipe | Purchase assumption | EC2 backfill |
| --- | --- | --- |
| A1 | On-Demand | $11,414 |
| A1 | Spot 60% discount | $5,180 |
| A1 | Spot 70% discount | $3,951 |
| A1 | Existing Savings Plan 30% discount | $8,064 |
| B1 | On-Demand | $1,262 |
| B1 | Spot 60% discount | $592 |
| B1 | Spot 70% discount | $460 |
| B1 | Existing Savings Plan 30% discount | $902 |
| B3 | On-Demand | $1,542 |
| B3 | Spot 60% discount | $718 |
| B3 | Spot 70% discount | $556 |
| B3 | Existing Savings Plan 30% discount | $1,099 |

### National buffered Lambda memory and CPU sensitivity

| Recipe | Allocated GiB | Allocated vCPU | Billed worker-hours | Backfill charge |
| --- | --- | --- | --- | --- |
| A1 | 1 | 0.58 | 155,825 | $9,398 |
| B1 | 1 | 0.58 | 18,560 | $1,154 |
| B3 | 1 | 0.58 | 24,169 | $1,491 |
| A1 | 2 | 1.16 | 130,444 | $15,700 |
| B1 | 2 | 1.16 | 14,397 | $1,768 |
| B3 | 2 | 1.16 | 16,840 | $2,061 |
| A1 | 3 | 1.74 | 130,444 | $23,527 |
| B1 | 3 | 1.74 | 14,397 | $2,631 |
| B3 | 3 | 1.74 | 15,532 | $2,836 |
| A1 | 6 | 3.47 | 130,444 | $47,007 |
| B1 | 6 | 3.47 | 14,397 | $5,223 |
| B3 | 6 | 3.47 | 15,187 | $5,508 |

### Serving transfer sensitivity before account allowances

| Workload | Volume | Decimal GB | Internet at $0.09/GB | Oregon to Virginia |
| --- | --- | --- | --- | --- |
| All, with land | one full history scan | 38,805.25 | $3,492.47 | $776.11 |
| All, with land | 30 days of new output | 632.21 | $56.90 | $12.64 |
| All, water + shore | one full history scan | 14,980.22 | $1,348.22 | $299.60 |
| All, water + shore | 30 days of new output | 244.06 | $21.96 | $4.88 |
| 10,000, with land | one full history scan | 77.61 | $6.98 | $1.55 |
| 10,000, with land | 30 days of new output | 1.26 | $0.11 | $0.03 |
| 10,000, water + shore | one full history scan | 29.96 | $2.70 | $0.60 |
| 10,000, water + shore | 30 days of new output | 0.49 | $0.04 | $0.01 |

### Compaction across small tile partitions

| Workload | Tile-month objects | Packed objects | Packed mean MiB | Packed scan GET cost |
| --- | --- | --- | --- | --- |
| All, with land | 289,122 | 289,179 | 128.0 | $0.11567 |
| All, water + shore | 217,350 | 111,780 | 127.8 | $0.04471 |
| 10,000, with land | 179,505 | 621 | 119.2 | $0.00025 |
| 10,000, water + shore | 179,505 | 414 | 69.0 | $0.00017 |

<!-- END GENERATED COST TABLES -->

## What the source-byte checks establish

**Measured:** Florida B1 requested 352 MB across four products. Its selected native blocks covered 20.55 percent of decoded full-image bytes.
That is materially different from the original national assumption of a 70 percent available block pool.
Comparing Florida's bytes directly with a saturated national tile therefore cannot establish a universal 2.5-fold correction.
The [aggregate check](cost-analysis/cohort-blocks.json) preserves exact block counts, native byte weights, source hashes, and limitations.

The proper original-model back-test substitutes actual cohort geometry while retaining the old occupancy and byte parameters.
It predicts Florida B1 and B3 bytes approximately 50 percent high, and dispersed bytes approximately 20 percent low.
A second check using actual unique blocks shows that the old compressed-byte coefficient was low in both cohorts.
Spatial coverage error and requested-byte conversion error had partly offset each other. A blanket multiplier would conceal that distinction.

The revised model first estimates decoded native block bytes, then applies measured requested-to-decoded ratios separately for B1 and B3.
These ratios include compression, HTTP range overhead, and cache effects. They are not pure file-compression ratios.
A genuine cross-cohort check uses one cohort's ratio to predict the other cohort's requested bytes.
The B1 residuals are within 3.5 percent. B3 residuals are within 5.6 percent.
Those checks condition on known blocks. They do not validate a national block-count prediction or AWS throughput.

For source occupancy, one concentration parameter is fitted to Florida's 99 unique red-band blocks.
The fit predicts 158.04 dispersed blocks against 162 observed, a 2.45 percent shortfall.
Florida's zero residual is a calibration result, not a holdout success.
The available pool and concentrated-cell fraction remain assumptions. Different parameter combinations fit Florida equally well.
The sparse holdout weakly distinguishes those combinations. No independent dense cohort establishes national concentration.
The coverage sensitivity varies the available pool explicitly.
Tile occupancy retains separate geographic assumptions, rather than copying Florida's within-image clustering to national tile counts.

Native-resolution payload expansion is approximately 3.3006 times the measured five-asset set, compared with a simple asset-count factor of 3.4.
The payload includes the conservative ten-meter AOT/WVP allowance. Additional bands' compression remains unmeasured.
The central national source volume therefore need not fall by the review's proposed factor after correcting both errors.

## A1's penalty and request latency

The measured A1/B1 byte ratios are approximately 1.003 for dispersed lakes and 5.116 for Florida.
The central model interpolates those ratios against repeated block work, clamping outside the observed range.
This is an observed-envelope scenario, not proof that national A1 cannot exceed the Florida ratio.
The repeat-read alternative retains the unsourced per-lake cache assumption and explicitly labels its national result as extrapolation.
The initial $27,175 headline is superseded. Neither its magnitude nor the revised extrapolated magnitude is a measured national penalty.

The central network scenario now gives B1 and B3 equal effective concurrency.
The sensitivity table varies request service time and both symmetric and asymmetric concurrency.
Effective concurrency includes internal range handling. A Python loop or Dask thread count does not establish HTTP concurrency.
Request coalescing and caching are already partly reflected in measured requested bytes, but production request grouping remains unmeasured.
The JSON exposes CPU, transfer, latency, and output components separately.
The table shows that reader ordering can reverse under different latency and concurrency assumptions.
A small central difference cannot select a reader conclusively.

## Compute capacity, preparation, and Lambda

The [saved trials](../benchmarks/results/lazy-reader-workloads.json) calibrate worker CPU per requested megabyte separately from source-byte conversion.
The [timing qualifications](reviews/2026-09-22-sleep-rerun-review-response.md) remain active. Laptop elapsed time is never presented as measured AWS time.

```text
CPU work = requested MB × measured CPU-seconds/MB × hardware/workload multiplier
worker duration = CPU service + bulk transfer + effective request latency + output work
EC2 instance-hours = worker duration / packed workers / 3,600
preparation instance-hours = preparation CPU-hours / utilization / preparation workers
```

Operations and retry allowances multiply those durations. Adding service components assumes no overlap across CPU, bulk transfer, and output work.
The central instance has four vCPUs and eight GiB RAM, with two three-GiB extraction workers and instance overhead.
Preparation now exposes its own worker count and memory budget. The central case packs two workers.
The four-worker sensitivity requires at most 1.5 GiB per worker after reserved memory.
Thus fourfold preparation savings are conditional on memory fit and parallelism, not guaranteed by four available vCPUs.
The original serial preparation allowance was conservative but insufficiently explained.

**Documented:** c7i.xlarge has a 1.562 Gbps network baseline, distinct from its burst capacity.
[AWS instance specifications](https://docs.aws.amazon.com/ec2/latest/instancetypes/co.html).
The modeled two-worker transfer rates remain below that baseline in aggregate.
The 32-instance schedule uses 64 extraction workers, after preparation on the same fleet.
Lambda schedules use 64 invocations after EC2 preparation. These compare worker counts, not equal allocated CPU or memory.
Ideal partitioning, available capacity, and bounded large-lake work remain assumptions.

**Documented:** Lambda CPU allocation grows with memory, with one vCPU equivalent at 1,769 MiB.
Ordinary invocation duration is limited to 900 seconds. [AWS Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).
The revised model divides CPU service by allocated CPU, subject to per-reader thread limits and an explicit serial fraction.
B1 and A1 are modeled as single-threaded CPU work. B3's central scenario assigns half its CPU work to two-thread-capable work.
These are scaling assumptions, not measured AWS speedups. Output serialization remains single-threaded and network service remains separate.
The one-to-six-GiB sensitivity reports changed durations as well as changed prices.

The one-GiB Lambda case can cost less than the central two-worker EC2 case, if its workload fits memory.
Therefore, the former blanket conclusion that Lambda costs approximately twice EC2 is withdrawn.
Three-GiB Lambda remains more expensive in the central comparison. Neither comparison establishes the optimum configuration.
All-band memory, package size, bounded batching, cold starts, checkpointing, and retained block reuse still require validation.
Geometry correctness and [convergence limits](reviews/2026-09-18-claude-geometry-blocker-assessment.md) are separate from the modeled preparation budget.

Storage during backfill is approximately half the completed archive's monthly bill multiplied by elapsed months, assuming linear growth.
An always-on instance incurs idle charges. The displayed recurring compute estimates assume instances stop after ingestion.

## Storage classes and access patterns

**Documented:** Standard-IA has a 30-day minimum duration, minimum billable object size, and retrieval charges.
Intelligent-Tiering moves eligible objects after 30 and 90 days without access. Reading an object resets its access clock.
[AWS S3 pricing](https://aws.amazon.com/s3/pricing/) and [Intelligent-Tiering documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/intelligent-tiering-overview.html).
The [new source record](assessment-checks/aws-cost-review-sources.json) qualifies regional rate proxies and the unverified IA GET allowance.

The IA scenario keeps recent output and static geometry in Standard, then transitions older immutable output.
It includes retrieval charges, a request allowance, and a separate one-time transition estimate in the JSON.
Early deletion, rewrite, or compaction of IA objects can introduce minimum-duration charges outside that retained-output scenario.
At roughly one full historical scan monthly, modeled retrieval charges consume the storage savings.
The request-price uncertainty is minor at the compacted object counts but remains explicitly unverified.

The cold Intelligent-Tiering scenario assumes historical objects have aged without access after ingestion.
Acquisition dates do not make a freshly backfilled archive immediately cold.
The first month remains at frequent-access prices. Continuing updates occupy the recent and intermediate tiers.
The modeled mature state includes monitoring and uses Archive Instant Access, without optional asynchronous restoration tiers.
A full scan every thirty days keeps the archive effectively in frequent access, eliminating the modeled cold-history benefit.
Small objects below the automatic-tiering threshold remain frequent and are not charged monitoring.
These access-dependent scenarios are alternatives, not additive charges or selected storage policies.

## Spot and Savings Plans

The purchase table assumes 60 or 70 percent Spot discounts on extraction compute, with ten percent additional interruption work.
Preparation remains On-Demand. Scratch storage follows extra runtime. PUTs and retained S3 storage receive no compute discount.
Those percentages are unsourced sensitivities, not current capacity offers.
**Documented:** Spot uses interruptible spare capacity, while Savings Plans require an hourly spending commitment over one or three years.
[AWS purchasing guide](https://docs.aws.amazon.com/decision-guides/latest/decision-guides/ec2-purchasing-options-aws-how-to-choose.html).

The Savings Plan row assumes a thirty-percent marginal discount under an existing usable commitment.
It does not justify buying a new commitment for this one backfill.
For illustration, committing thirty-two instances for one year at that discounted planning rate costs approximately $35,026, even when unused.
Capacity availability, checkpoint effectiveness, and deadlines can outweigh a nominal discount.

## Object layout and serving transfer

The initial three-objects-per-tile-month layout produced approximately 179,505 tiny objects for the buffered sample.
Similar GET costs for national and sampled archives were a consequence of that layout, not an S3 arithmetic error.
A numerical minimum-size floor cannot combine objects physically.
The revised central layout explicitly compacts small tile partitions into larger per-grid monthly objects across tiles.
Tile and water-body provenance remain intact. This is packaging, not imagery mosaicking.

The compaction table compares both layouts without padding payload bytes or deleting memberships.
Object counts approximate equal volumes across grid-month groups. Actual skew and final partial objects will change counts.
A lookup index and selective range reads are required to avoid unnecessary retrieval during per-body queries.
Their production implementation and access amplification remain unmeasured.
Daily temporary writes and monthly compaction writes remain charged separately.

The in-region transfer baseline remains zero.
The new serving table additionally prices one full history scan and thirty days of new output outside that baseline.
It uses a flat $0.09 per GB internet proxy and the documented Oregon-to-North-Virginia rate.
[AWS S3 transfer pricing](https://aws.amazon.com/s3/pricing/).
Gross internet rows exclude shared account allowances and volume discounts. The JSON separately shows an unused-allowance case.
The internet rate comes from a qualified Ireland example, not a verified current Oregon quotation.

Storage uses verified binary billing units. Transfer and retrieval scenarios explicitly assume decimal GB because the cited prices state GB without a universal metering definition.
Using binary transfer GB instead would lower these modeled transfer charges by approximately 6.9 percent.
Transferred volume is served output, not all source imagery read during ingestion.
Consumer-model execution, query-engine compute, and repeated lookup amplification are outside the specified serving demand.

## Population and retained-pixel model

**Documented:** EPA reports approximately 5.6 million mapped lake, pond, and reservoir objects before eligibility screening.
Its larger-lake frame and the LAGOS perennial inventory have different size and artificial-basin exclusions.
[EPA technical report](https://www.epa.gov/system/files/documents/2024-08/national-lakes-assessment-2022_tsd_august2024_2.pdf) and [LAGOS-US LOCUS](https://aslopubs.onlinelibrary.wiley.com/doi/10.1002/lol2.10203).
No complete permanent-water census down to the requested minimum size was established.
The national cases therefore retain the explicit population, area, and shoreline stress assumptions.
The published area anchor's Great Lakes exclusion remains an inference, not independently confirmed eligibility.

The model retains EPA's larger size-bin counts as proxies and assigns the remaining population to sub-hectare bodies.
Assumed bin means close the total-area target. Shoreline complexity and within-bin moments determine estimated perimeter.
The expected count-uniform sample area is national area multiplied by sample count divided by national count.
Rare large lakes create substantial realized-sample variability. The JSON retains multiple uncalibrated tail-variance sensitivities, without confidence intervals.
The low and high sample cases vary population and area independently to avoid reversing expected area per sampled body.

For total water area A, perimeter P, body count N, buffer radius d, and grid width r:

```text
added buffer area ≈ retained_fraction × (dP + πd²N)
water-and-shore cells ≈ A/r² + 2P/(πr) + N
buffered cells ≈ max(water-and-shore cells, buffered_area/r²)
```

The buffer selects exterior pixel centers under A21. It receives no additional all-touched correction at the outer boundary.
Concavity, islands, surrounding water, and grid alignment remain geometric approximations.
Neighboring bodies may retain duplicate pixel memberships while sharing source reads.
The source-block fit does not alter these retained-output equations.

Historical and forward acquisition frequencies use the distinct survey-based scenarios described above. Cloudy observations remain included.
The [existing gap survey](measurements.md) documents missing coverage and fallback complications.
No new catalog query establishes a complete history. Missing source layers remain missing.

Stored payloads retain integer native-grid values, flags, dictionary-encoded metadata, and reusable geometry.
Compression, layout overhead, revisions, and overlapping observations remain explicit assumptions.
Verbose per-pixel rows, retained raw imagery, extra replicas, or frequent output rewrites can increase storage substantially.
One object per lake observation would also change request economics by orders of magnitude.

## Reproduction, limits, and next evidence

```sh
uv run python tools/estimate_aws_costs.py
uv run python tools/estimate_aws_costs.py --check
uv run pytest -q tests/test_aws_costs.py
```

With the preserved local frozen plans and databases, rebuild the source-byte aggregate independently:

```sh
uv run python tools/backtest_source_bytes.py --check
```

The normal tests use the checked-in aggregate and measurement hashes. They do not require local raw geometry or contact a provider.
Prices remain qualified historical or regional proxies. No AWS performance, memory, or live capacity measurement was added.
Combined stress cases are not confidence intervals, maximum bills, or recommended purchases.
Operations consumption and residual contingency are assumptions, not measurements, engineering estimates, or guarantees.
Taxes, labor, scientific algorithm development, and consumer-model training remain outside the infrastructure estimate.

The strongest next evidence would narrow geographic coverage, real output encoding, AWS request concurrency, memory fit, and access frequency.
A representative AWS calibration requires separate authorization. This revision performs offline arithmetic and source-document research only.
