# 0006. AWS cost review refinements, 2026-09-23

Status: active. Refines the offline method in [decision 0005](0005-aws-cost-scenarios.md). Workload scope and historical cutoff remain unchanged.

## Context

The owner supplied nine review findings about source bytes, extrapolation, concurrency, preparation, storage classes, purchasing, Lambda memory, serving transfer, and object layout.
The authorized response evaluates those findings and revises the offline analysis.

## Decision

Separate measured evidence, fitted parameters, holdout checks, and national extrapolation.
Retain the initial byte-model back-test so subsequent fits cannot hide its residuals.
Use native decoded bytes to calibrate source-byte conversion.
Expose occupancy uncertainty rather than applying a blanket correction across densities.
Present A1's observed-ratio scenario separately from extrapolated repeated reading.
Expose the additional cost drivers as explicit sensitivities, retaining same-region serving as the baseline.
Record revised assumptions in [A32–A41](../assumptions.md#aws-cost-analysis).

## Consequences

The [revised report](../aws-cost-analysis.md) supersedes the initial numerical comparison.
The [response record](../reviews/2026-09-23-aws-cost-review-response.md) owns finding dispositions and verification.
The workload descriptions remain estimates. No production recipe, storage layout, pricing commitment, or infrastructure purchase is selected.
Provider extraction and AWS calibration remain separate execution steps.

## Review triggers

- A second dense cohort tests the fitted spatial assumptions independently.
- AWS measurements replace assumed concurrency, preparation packing, or Lambda scaling.
- Serving access patterns or verified regional quotations replace sensitivity inputs.
