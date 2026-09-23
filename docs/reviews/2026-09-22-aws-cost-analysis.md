# AWS cost analysis implementation, 2026-09-22

Author: Codex, directed by the repository owner.
Status: implemented for owner review. Repository verification is recorded below.
The estimates from this initial implementation are superseded by the [2026-09-23 response](2026-09-23-aws-cost-review-response.md).

## Authorized step and acceptance checks

The owner authorized the four workloads in [decision 0005](../decisions/0005-aws-cost-scenarios.md).
This step estimates costs and capacity from public source facts, existing measurements, and explicit assumptions.
It runs offline calculations, not new provider measurements or infrastructure.

Acceptance checks cover native-grid accounting, sample expectations, block reuse, source payer, binary storage units, and CPU versus billed time.
They also cover external-source independence, reproducible results, preserved benchmark evidence, and the repository check workflow.
AWS calibration, scientific validation, and production selection remain deferred.

## Changes and evidence

- Added the [analysis](../aws-cost-analysis.md), reproducible [inputs](../cost-analysis/inputs.json), and generated [estimates](../cost-analysis/estimates.json).
- Added the offline [estimator](../../tools/estimate_aws_costs.py) and [accounting tests](../../tests/test_aws_costs.py).
- Recorded scenario authority and assumption status in the decision and assumption registry.
- Linked the report from the repository overview and documented its regeneration commands.

The model reads frozen [larger-workload measurements](../../benchmarks/results/lazy-reader-workloads.json).
It binds the measurement, input, and estimator hashes without changing benchmark results or source code.
Its report tables regenerate from the same calculations as the JSON artifact.

Two research agents examined population evidence and AWS documentation separately.
A third agent independently checked every adopted external claim against primary sources.
The required different-model verification subsequently confirmed all nineteen qualified claims on 2026-09-23, without changing numeric inputs.
The [source record](../assessment-checks/aws-cost-analysis-sources.json) contains nineteen contextual checks with qualifications and provenance.
These scenario facts do not change candidate specifications in the inventory.

## Independent numerical review dispositions

| Finding | Disposition | Treatment |
|---|---|---|
| A1 metadata requests scaled only by source products | Fixed | Added per-lake reopening misses with explicit metadata-cache sensitivity |
| Band-block requests could be hidden by average request size | Fixed | Added a separate per-band block request proxy alongside byte-derived requests |
| Advertised EC2 bandwidth is burst capacity | Fixed | Checked sustained bandwidth and lowered transfer-service assumptions below its per-worker share |
| Large-lake variance was weakly specified | Fixed with qualification | Added three uncalibrated tail sensitivities and removed any confidence interpretation |
| Land buffer needs another all-touched edge correction | Corrected with selection semantics | A21 uses exterior pixel centers. The report distinguishes that expectation from polygon-intersection cells |
| Lambda batch arithmetic does not establish task feasibility | Accepted and deferred | Describe required bounded partitions, preserved reuse, checkpointing, and validation explicitly |
| Backfill excludes accumulating storage | Fixed in presentation | State exclusions and give the linear-growth storage formula and central example |
| Current Oregon rates are incompletely verified | Accepted and deferred | Preserve historical and regional qualifications, without presenting a current quotation |
| National census and exact sample are unavailable | Accepted and deferred | Use sourced anchors and unsourced stress assumptions. No exact eligibility or sampling claim |

Earlier Prototype timing qualifications remain active.
The model never substitutes laptop elapsed time for measured AWS throughput or converts CPU-seconds directly into instance charges.
It preserves identical output storage across recipes and distinguishes requested source bytes from retained output bytes.

## Verification

The targeted accounting suite passed before final report-table integration.
The initial system-Python generation differed in floating-point details from the pinned environment.
Regeneration under pinned Python resolved the reproducibility assertion without weakening the test.
Initial targeted lint checks found long lines. Formatting and line wrapping corrected them before the full gate.

The repository check workflow passed:

- `uv sync --locked`: 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, with 129 files formatted.
- `uv run pytest -q`: 291 passed in 29.97 seconds, with 13,000 existing dependency deprecation warnings.

The focused accounting suite passed: nine tests in 0.02 seconds.
The estimator's `--check` passed for JSON results and generated report tables.
The four existing artifact checks passed: inventory, sensor bands, assessment presentation, and gap report.
`git diff --check` passed.
The presentation and benchmark files have no changes. A browser check was unnecessary because the HTML presentation was not edited.
Final documentation-only updates received a focused link and accounting check.
That check passed 95 tests in 0.17 seconds. The numerical reviewer confirmed the corrected formulas and withdrew the buffer-edge finding.

## Limits and proposed next step

The central case is a planning model, not a quote, a complete census, or an AWS benchmark.
The broad sensitivities prevent treating a small B1/B3 difference as a reliable platform or reader ranking.
Exact population coverage, output encoding, quality algorithms, geometry memory, task partitioning, and consumer-query compute remain unresolved.

Review the assumptions and cost drivers before authorizing a representative AWS calibration.
No benchmark, infrastructure deployment, commit, push, or publication was performed.
