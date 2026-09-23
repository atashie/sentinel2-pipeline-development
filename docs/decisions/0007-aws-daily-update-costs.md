# 0007. AWS daily update cost scenarios, 2026-09-23

Status: active. Refines acquisition rates and recurring accounting in [decision 0006](0006-aws-cost-review-refinements.md).

## Context

The owner requested integration of the [daily-update review](../reviews/2026-09-23-claude-aws-cost-daily-update-review.md), with explicit disagreements.
The existing daily estimate prorated backfill and omitted important recurring terms.

## Decision

Use the saved survey to distinguish tile acquisitions from assumed point observations.
Revise both historical and forward rates, preserving the earlier frequency as a sensitivity.
Model daily batch overhead, prepared-geometry reloads, compaction, itemized service consumption, storage accrual, and conditional reprocessing.
Report the input horizons across all workloads, recipes, compute platforms, and stress cases.
Keep same-region serving and existing workload eligibility. No catalog query or AWS workload is authorized by this refinement.
The canonical assumptions are [A30 and A35–A45](../assumptions.md#aws-cost-analysis).

## Consequences

Point coverage and national frequency remain extrapolations from purpose-selected metadata evidence.
Forecasts begin after a completed backfill and separate growing retention from update processing.
Service examples and batch cadence are planning assumptions, not production selections or owner service-level commitments.
The [response record](../reviews/2026-09-23-aws-cost-daily-update-response.md) owns review dispositions and verification.

## Review triggers

- National metadata or valid-pixel evidence replaces rate assumptions.
- Measured overheads or a latency target replaces average-day capacity assumptions.
- Access patterns, reprocessing policy, or water-body changes alter retained output.
