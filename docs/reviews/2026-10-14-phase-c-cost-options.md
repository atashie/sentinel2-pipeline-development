# Phase C, step 4: the cost model re-parameterized per standalone option, 2026-10-14

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered. Offline arithmetic only. Awaiting review.

## For the owner

- The cost model now estimates both standalone options. Sen2Cor-only values are unchanged, value for value.
- In the central case, ACOLITE only costs about a quarter of Sen2Cor only to backfill and to store.
- National B1 backfill on EC2 with the land buffer: $327 against $1,262. Retained history: 8,339 GiB against 36,140 GiB.
- The two options deliver different data. ACOLITE only keeps one 20 m grid and holds 55 percent of Earth Search's acquisitions on the survey tiles.
- The grid and layers alone cut storage and backfill by more than half. Fewer acquisitions then cut each by another 42 to 45 percent.
- On the 10,000-body sample, fixed operations dominate the monthly bill. ACOLITE only saves about a fifth of it there.
- ACOLITE only has no A1 estimate, because T6 replayed B1 and B3 only.
- No provider was contacted. The page's cost section still shows the Level-2A series until the Prototyping tab rebuild.

## Step and authorization

The owner wrote "proceed with the next steps" on 2026-10-14, after the [T5 and T6 record](2026-10-14-phase-c-t5-t6.md) proposed this step first.
Mid-step the owner wrote "when the next steps land, commit all recent updates and then spawn a team of adversarial review agents, then incorporate their findings, then commit and push, before proceeding to subsequent steps".
This record reads the first instruction as authorizing the recommended step, which contacts no provider. Probe T7 reads pixels and stays a separate step.
The second instruction sets what follows this record: a commit, an adversarial review, fixes, and a commit and push.

Acceptance checks, stated before the work:

1. The refactor leaves every Sen2Cor-only value unchanged.
2. Each changed ACOLITE-only input cites T1, T2, or T6, and a test ties it to the committed result.
3. Both estimate files and the report tables reproduce under `--check`.
4. `/check` passes.

Deferred: probes T7 and T8, the Prototyping tab rebuild, and the Phase F cost curves.
Also deferred: an A1 trial on the product, self-run ACOLITE costs, and any join cost under decision 0009.

## What changed

| Area | Change |
|---|---|
| [estimate_aws_costs.py](../../tools/estimate_aws_costs.py) | An option layer. Each option merges its measured inputs over the shared inputs. Grids, readers, acquisition evidence, and the settings file follow the option |
| [inputs.json](../cost-analysis/inputs.json) | Three shared keys with their Level-2A values, and an `options` block with each ACOLITE-only change and its basis |
| [estimates-acolite-only.json](../cost-analysis/estimates-acolite-only.json) | New generated estimates for ACOLITE only, with every component and sensitivity |
| [estimates.json](../cost-analysis/estimates.json) | Regenerated. Values unchanged. New `option` and `option_label` keys and new input and model digests |
| [backtest_aqr_source_bytes.py](../../tools/backtest_aqr_source_bytes.py) | New offline generator. The Level-2A byte audit's method, applied to T6's frozen plans |
| [aqr-cohort-blocks.json](../cost-analysis/aqr-cohort-blocks.json) | Its output: block counts, requested-to-decoded ratios, holdouts, and the delivered payload |
| [aws-cost-analysis.md](../aws-cost-analysis.md#two-standalone-options) | New section on the two options, with generated comparison tables. The rest is labeled as the shared model and Sen2Cor-only results |
| [assumptions.md](../assumptions.md) | Row A53, the per-option cost inputs |
| `tests/test_aws_costs.py` | Six new tests and one extended test, no network |
| [s2-options.html](../s2-options.html) | Regenerated. Only the cost digest in the generation comment changed |
| Planning documents | The [work plan](../work-plan.md), [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), and the [tools index](../../tools/README.md) |

## Method

Only inputs measured on the primary product changed. Every other input is shared, including every low and high stress value, assumption A53.

| Input | Sen2Cor only | ACOLITE only | Evidence |
|---|---|---|---|
| Grids and bytes kept per pixel | 10, 20, and 60 m, with 12, 15, and 4 bytes | 20 m, 28 bytes | T1 layer types, assumptions A46 and A49 |
| GeoTIFF layers per product | 17 | 13, plus one settings text file | T1 |
| Readers | A1, B1, B3 | B1, B3 | T6 |
| Requested bytes per decoded byte | Level-2A cohort checks | T6 cohort checks | [Product byte checks](../cost-analysis/aqr-cohort-blocks.json) |
| CPU seconds per requested MB | Larger-workload trials | T6 trials | [aqr-workloads.json](../../benchmarks/results/aqr-workloads.json) |
| Acquisitions | Gap survey, 23 tiles | T2 listings, the same 23 tiles and months | [aqr-coverage.json](../../benchmarks/results/aqr-coverage.json) |
| Central products per acquisition | 1.05, assumed | 1.0499, measured | T2, finding 27 |
| Conditional 2022 replacement | Collection 1's missing months | Not applicable | The product has its own 2022 coverage |

The product's 512-pixel blocks at 20 m cover 10.24 km, the Level-2A model's block ground. A tile holds 11 by 11 blocks on both sources.
T6's Florida cohort read the same 99 red blocks as the Level-2A trial. The Florida concentration fit gives 0.9885 on both sources.
The new byte audit counts each block once per layer and weights it by native type size. It copies the method of `tools/backtest_source_bytes.py`.
Each T6 cohort predicts the other's requested bytes within 7 percent for B1 and 2 percent for B3. Those checks condition on known blocks.
The model reads acquisition counts from the committed T2 result. It restricts them to the gap survey's tiles and complete months.
A comparator scenario applies Level-2A's acquisition history to the product's grid, layers, and byte ratios. It separates the acquisition effect from the rest.

## What the estimate shows

The [generated tables](../aws-cost-analysis.md#two-standalone-options) own the numbers. The central case, national with the land buffer:

| Quantity | Sen2Cor only | ACOLITE only |
|---|---|---|
| Retained history, GiB | 36,140.2 | 8,338.6 |
| S3 per month at the cutoff | $832.29 | $192.01 |
| B1 backfill on EC2 | $1,262 | $327 |
| B3 backfill on EC2 | $1,542 | $431 |
| B1 source read, TB | 652.3 | 106.2 |
| B1 recurring total per month on EC2 | $867.82 | $210.73 |
| Cumulative B1 bill at 60 months, EC2, Standard | $77,707 | $18,804 |

- With Level-2A's acquisition history, the product's model retains 15,106.6 GiB and its B1 backfill costs $563. The grid and layers alone cut each by more than half.
- Source bytes fall to 16 percent of Sen2Cor only's. Acquisitions give 0.55, payload per block 0.44, and requested-to-decoded ratio 0.67.
- CPU hours fall less than bytes. CPU seconds per requested MB are 1.5 to 1.7 times Level-2A's.
- The low and high stress cases keep the same order. ACOLITE only's high case retains 46,441.8 GiB, more than Sen2Cor only's central case.

## Sen2Cor-only values

The refactor ran against a copy of the previous `estimates.json`. A recursive comparison found zero differing values.
The only changes are the input and model digests and the two option labels. The page's cost numbers are unchanged.

## Evidence

No provider was contacted. The step read committed results and T6's frozen local inputs only.

| Input | Path | Digest in output |
|---|---|---|
| T6 result | `benchmarks/results/aqr-workloads.json` | `evidence_sha256` in both new files |
| T6 frozen plans and expected blocks | `data/aqr-workloads/2026-10-14-run/workloads/*/` | Plan and database digests in `aqr-cohort-blocks.json` |
| T1 headers | `benchmarks/results/aqr-headers.json` | `headers_sha256` |
| T2 listings | `benchmarks/results/aqr-coverage.json` | `coverage_sha256` |
| Level-2A byte checks | `docs/cost-analysis/cohort-blocks.json` | `reference_sha256` |

The T2 and T6 results record the bucket `usgs-wma-sentinel-2-aqr-acolite-dsf`, region us-west-2, and payer. Every request was unsigned, so the bucket owner paid.

## Verification

| Command | Outcome |
|---|---|
| `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` | Pass |
| `uv run pytest -q` | 382 passed, 13,000 existing warnings |
| `uv run python tools/estimate_aws_costs.py --check` | Both estimate files and the report tables match |
| `uv run python tools/backtest_aqr_source_bytes.py --check` | Product byte checks match T6's frozen local inputs |
| `uv run python tools/backtest_source_bytes.py --check` | Level-2A byte checks unchanged |
| `collate_checks`, `collate_sensor_bands`, `render_options`, and `gap_report`, each with `--check` | All current |
| The review-layer `inject.py --check` | Up to date |
| Recursive comparison of `estimates.json` before and after | Zero differing values |

## Limits

- ACOLITE only has no A1 estimate. T6 replayed B1 and B3 only.
- T6 read 5 of the 13 layers. The other 8 layers' compression is unmeasured.
- T2's counts include 544 of 18,641 listed scenes on the 23 tiles without the full layer set. The estimate prices them as complete products.
- Products per acquisition span every listed product of the 23 tiles from 2015 to 2026, not the cost window alone.
- Point-to-tile activity fractions keep the Level-2A assumption. T2 recorded only medians of partial coverage.
- The store keeps the flags layer at its native 4 bytes. A packed flag integer would shrink storage. That saving is unmeasured.
- Request latency is a large share of worker time in both options. Its inputs are shared assumptions, measured on neither source in AWS.
- Laptop CPU seconds calibrate both options. Every timing qualification of the reference series applies.
- The comparison prices different deliveries. It does not compare the corrections, assumption A52.

## Dispositions

| Prior item | Disposition |
|---|---|
| T5 and T6 record: proposed next step, the cost re-parameterization | Fixed. This step |
| Replan record: "Re-parameterize from T1 and T6. Add the join work and the second source's storage." | Re-parameterization fixed, using T2 as well. Join work and second-source storage accepted and deferred under decision 0009 |
| Decision 0005 review trigger: the consumer changes bands | Accepted. The method stands. The option layer carries the band change, and decision 0005 stays active |
| Work plan: costs from the primary product on the Prototyping tab | Accepted and deferred to the tab rebuild |

## Proposed next step

The owner's instruction sets the next actions: commit, an adversarial review, fixes, and a commit and push.
After that, this record recommends probe T7, overlap on the lakes in two tiles. It reads pixels and completes Phase C's probes.
The Prototyping tab rebuild follows, with every Phase C input in place. Probe T8, retention, reads no pixel and can run alongside.
This record starts none of them.
