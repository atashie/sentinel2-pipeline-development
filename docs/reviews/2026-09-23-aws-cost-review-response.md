# AWS cost review response, 2026-09-23

Author: Codex, directed by the repository owner.
Status: earlier review retained. [Daily-update refinements](2026-09-23-aws-cost-daily-update-response.md) subsequently revise acquisition rates and recurring costs.

The owner supplied nine findings on the initial [cost analysis](../aws-cost-analysis.md).
This response changes the estimate, evidence checks, sensitivities, and tests. It launches no provider script or AWS workload.
The [decision](../decisions/0006-aws-cost-review-refinements.md) records the authorized methodological refinement.

## Acceptance checks and boundaries

Check source bytes against actual cohort blocks, preserving the original model's errors.
Separate fitted parameters from holdout results and unvalidated national transfers.
Verify CPU service, memory, worker packing, source payer, storage retrieval, access clocks, and discount scope.
Regenerate the report and JSON, then run the repository check workflow.
Cloud execution, exact national eligibility, scientific validation, and production selection remain deferred.

## Findings and dispositions

| Finding | Disposition | Result |
|---|---|---|
| 1. Missing byte back-test | Fixed, with corrected interpretation | Added native-block aggregates, original-model checks, cross-cohort byte checks, and a separately labeled spatial fit |
| 1. National bytes are necessarily about twice too high | Corrected with evidence | Florida reads 20.55 percent of decoded source coverage. It cannot directly validate or refute a saturated national tile |
| 2. A1 penalty exceeds measured reuse ratios | Fixed | Central byte ratios stay within the observed envelope. Repeated-read extrapolation has its own cost table and warning |
| 3. Latency and concurrency dominate a slight reader difference | Fixed | Equal central B concurrency, twelve network sensitivities, and exposed worker-time components |
| 4. Preparation ignores packing | Fixed with qualification | Separate preparation worker count and memory limit. Four-worker savings require feasible per-worker memory |
| 5. Only one storage class | Fixed | Standard, Standard-IA, and Intelligent-Tiering scenarios include retrieval, monitoring, eligibility, and access age |
| 6. Purchasing discounts only named | Fixed | Spot and existing Savings Plan sensitivities discount compute, preserve other charges, and state restart or commitment conditions |
| 7. Lambda memory changes price but not CPU service | Fixed | Memory-linked CPU allocation changes duration, subject to explicit serial-work and thread assumptions |
| 8. Serving egress deferred | Fixed | Price full-history scans and new-output transfers through qualified internet and Oregon-to-Virginia examples |
| 9. Tiny-object floor distorts sample request costs | Fixed through an explicit layout alternative | Cross-tile object compaction reduces object count without changing payload bytes or provenance |

## Evidence and important qualifications

The [byte-check script](../../tools/backtest_source_bytes.py) reads frozen local plans and SQLite selections in read-only mode.
Its [aggregate](../cost-analysis/cohort-blocks.json) records plan, database, generator, and measurement hashes.
CI uses that aggregate and the committed measurement evidence, without requiring local raw geometry.

The original geometry-conditioned back-test predicts Florida B1/B3 bytes approximately 50 percent high.
It predicts dispersed B1/B3 bytes approximately 20 percent low.
The original requested-to-decoded coefficient is low in both cohorts once their actual unique blocks are supplied.
That decomposition explains why applying a blanket 2.5-fold national reduction would not follow from the evidence.

Requested-to-decoded ratios transferred between cohorts predict B1 within 3.5 percent and B3 within 5.6 percent.
Those are actual holdouts of byte conversion, conditional on known blocks.
The new spatial mass is fitted to Florida, predicting 99 red-band blocks there.
Its dispersed holdout predicts 158.04 against 162, but provides weak evidence about dense national behavior.
Multiple concentration assumptions fit the dense observation. No second dense cohort validates the national extrapolation.

Preparation was previously modeled as one worker on an instance. That was a conservative allocation, not a four-core utilization measurement.
The revised central case packs two preparation workers. The four-worker sensitivity explicitly lowers the permitted per-worker memory.
Thus the review's automatic fourfold correction would also require a memory and parallelism assumption.

The original equal-cost sample GET behavior was real under its specified partition count.
We changed the layout rather than hiding that cost behind a numerical minimum-size floor.
Compaction requires an index and selective access. Its implementation remains unvalidated.

The Lambda sensitivity disproves a universal twofold cost conclusion within this model.
A one-GiB configuration can cost less than the central EC2 configuration, conditional on memory fit.
CPU parallelism, network limits, and hardware equivalence remain assumptions. The report selects neither platform.

## Independent checks

A research agent gathered new AWS price and service claims.
A separate checking agent using a different model verified the [new source record](../assessment-checks/aws-cost-review-sources.json).
Regional and publication-time price qualifications remain visible. The IA GET rate remains explicitly unverified.

A separate numerical checker derived the block aggregate and reviewed the revised equations.
All twelve scenarios passed independent byte-unit, daily/history, block-bound, instance-billing, and total-cost checks.
The checker identified an unused byte knob and minor IA request-accounting inaccuracies. Both were corrected.

## Verification

The original near-saturation regression expected buffer-induced source changes below 0.1 percent.
It failed after spatial recalibration produced approximately 1.4 percent. The assertion was replaced with the intended source-versus-storage relationship.
The revised test requires increased source reading to remain smaller proportionally than increased retained storage.
The Lambda test now checks memory-dependent duration and CPU thread limits rather than asserting constant runtime.

The repository check workflow passed:

- `uv sync --locked`: 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, with 132 files formatted.
- `uv run pytest -q`: 300 passed in 30.11 seconds, with 13,000 existing dependency deprecation warnings.

The focused accounting and documentation suite passed 104 tests in 0.20 seconds.
Both offline generators passed `--check`: source-byte aggregates and the cost report with its JSON artifact.
The four existing artifact checks passed: inventory, sensor bands, assessment presentation, and gap report.
`git diff --check` passed. Benchmark sources, measured results, and the HTML presentation have no changes.
The working tree had no staged files at the start. No changes were staged by this response.

## Proposed next step

Review the revised assumptions, conditional conclusions, and access-pattern sensitivities.
The next useful measurement would test a second dense geography and representative AWS memory, request concurrency, compression, and compaction behavior.
No extraction, infrastructure deployment, purchase, commit, push, or publication occurred.
