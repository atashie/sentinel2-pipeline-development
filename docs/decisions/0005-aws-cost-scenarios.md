# 0005. AWS cost scenarios, 2026-09-22

Status: active. Partially replaces A6's cost-curve ceiling. Existing benchmark scopes and production review gates remain active.

## Context

The owner requested an AWS cost assessment grounded in existing A1, B1, and B3 experiments.
The owner then confirmed geography, pixel selections, historical scope, random sampling, and same-region consumption.

## Decision

The canonical scope and model assumptions are [A26–A37](../assumptions.md#aws-cost-analysis).
Estimate nationwide workloads and count-uniform samples using those assumptions.
Separate initial preparation, historical extraction, daily ingestion, S3 retention, requests, and serving transfer.
Compare EC2 with ordinary on-demand Lambda functions, without selecting either platform.
Use existing measurements and independently checked external sources.
Run offline arithmetic and repository checks. No new imagery run or infrastructure deployment is authorized by this estimate.

## Consequences

National cost scenarios exceed the earlier benchmark ceiling.
The [cost report](../aws-cost-analysis.md) separates modeled expectations from measured performance and documented source facts.
The [inputs](../cost-analysis/inputs.json) and [estimator](../../tools/estimate_aws_costs.py) make sensitivity changes reproducible.
Exact population coverage, AWS throughput, current regional quotations, and production layout remain unresolved.

## Review triggers

- A filtered hydrography census or exact sample replaces population assumptions.
- Current Oregon quotations replace price proxies.
- Representative AWS trials replace runtime, memory, and compression assumptions.
- The consumer changes geography, history, pixel classes, bands, or serving location.
