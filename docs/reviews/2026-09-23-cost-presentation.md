# AWS cost estimates on the assessment page, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented and checked. Awaiting owner review.

The owner asked to update the [assessment page](../s2-options.html) with the new cost findings.
A first version filled the Tradeoffs & Issues tab. The owner redirected it the same day.
That tab stays out of scope. The costs belong in a brief Prototyping section 07, with definitions and one results table, without commentary.
The owner then renamed the workload labels and dropped the former section 07. This record describes the final version only. It contacted no provider. It changed no estimate, input, or model file.

## Step, acceptance checks, and deferrals

Step: add Prototyping section 07 with brief experiment definitions and one results table. Drop the former section 07, "Remaining decisions".

Acceptance checks:

- The Tradeoffs & Issues tab is unchanged from the last commit.
- Every cost, volume, count, date, and configuration value in section 07 comes from the [estimates](../cost-analysis/estimates.json) or [inputs](../cost-analysis/inputs.json) through the renderer.
- Rendering fails when the estimates predate their inputs or their model.
- The section defines the experiments and reports results without interpretation.
- The page tests, the review-layer check, and the repository check workflow pass.

Deferred: the Tradeoffs & Issues tab, the rest of the page's cost wording, any change to the cost model, and both open review items.

## What changed

| File | Change |
|---|---|
| [Template](../../tools/s2-options.template.html) | New section 07 and navigation link. The former section 07 and its link are removed. Footer date and digest comment |
| [Renderer](../../tools/render_options.py) | The cost table, workload labels, and definition markers read the estimates and inputs. A digest check refuses stale estimates. The two no-data markers of the removed section are gone |
| [Renderer tests](../../tests/test_render_options.py) | Five fixture tests cover the table, the definitions, refusals, and staleness |
| [Page tests](../../tests/test_presentation.py) | One test ties the rendered table and labels to the estimates and inputs, and checks the removed section is absent |
| [Page](../s2-options.html) | Regenerated |
| [README](../../README.md), [tools README](../../tools/README.md), [work plan](../work-plan.md), [review index](README.md) | Page description, renderer inputs, a Phase 2 line, and this record |

## Section 07

The section defines three things before the table:

- Workloads: all eligible water bodies in the contiguous states, assumed to number 5,000,000, and a random sample of 10,000. Each is priced with and without nearby land within 100 m.
- Recipes and platforms: A1, B1, and B3, calibrated from section 05. EC2 instances with 4 vCPU and 8 GiB. Lambda at 3 GiB.
- Periods and storage: backfill from 2021-01-01 to 2026-09-22, daily updates at the latest surveyed rate, and S3 Standard.

The table groups three recipe rows under each workload. Each workload label names its population and pixel classes:

- All US water bodies (5,000,000) · water + shoreline + 100 m nearby land
- All US water bodies (5,000,000) · water + shoreline only
- 10,000-lake sample · water + shoreline + 100 m nearby land
- 10,000-lake sample · water + shoreline only

The count comes from the estimates. The distance comes from the inputs, as in assumption A21.

Each group heading gives the stored history, the S3 Standard charge at completion, and its yearly increase.
Recipe rows give source imagery read, backfill on EC2 and Lambda, and daily updates per month on each platform.
A note gives itemized operations of $13.21 to $13.41 per month, including the assumed $10.00 allowance.
The source note links the analysis, the estimates, the assumptions, and the two open review items.

Dollar precision follows the [cost report](../aws-cost-analysis.md): whole dollars for backfill, cents for monthly charges.
Every value matches the report's backfill, extraction, daily ingestion, and retained storage tables.

## Dispositions of the presentation notes

| Note in the [response review](2026-09-23-claude-aws-cost-daily-update-response-review.md) | Disposition |
|---|---|
| Standard storage is the default, and Intelligent-Tiering savings depend on reads | Accepted and deferred. Section 07 names S3 Standard. Storage classes stay in the linked analysis |
| Assumed operations make up most of the sample's bill | Accepted and deferred. Section 07 states the operations charge and its allowance, without comparison, at the owner's direction |
| Bind page numbers to the estimates file | Fixed. The renderer reads the estimates and refuses stale files |

## Limits

- The section inherits every qualification of the analysis. It adds no evidence.
- Both open review items remain open. A rule change alters source-read and backfill figures after regeneration.
- Section 00 still says operating costs remain open. Its link to the removed section became plain text.
- The removed section held the page's only statement of the Stage 4 no-data entries. [Measurement findings](../measurements.md#prototype-stage-4-lakes-across-tiles-2026-09-16) still record them.
- "US" in the labels means the contiguous states without the Great Lakes, as assumption A26 defines. The section 07 definitions state the contiguous scope only. The [final accuracy review](2026-09-23-claude-final-page-accuracy-review.md) corrected this line.
- Headless Chrome rendered the section at 1,280 and 390 pixels wide. No live browser or screen reader was used.

## Verification

- `uv run python tools/render_options.py --check`: the page matches its template and inputs.
- `uv run python tools/estimate_aws_costs.py --check`: the estimates match their inputs, evidence, and model.
- Review-layer `inject.py --check`: up to date.
- `uv run pytest -q tests/test_render_options.py tests/test_presentation.py`: 22 passed.
- Repository check workflow: `uv sync --locked` resolved 59 packages. `ruff check` passed. `ruff format --check` found 137 files formatted.
- `uv run pytest -q`: 317 passed in 53.45 seconds, with 13,000 existing dependency deprecation warnings.

## Proposed next step

Owner review of section 07. Settling the two open review items would regenerate its figures. Neither has started.
