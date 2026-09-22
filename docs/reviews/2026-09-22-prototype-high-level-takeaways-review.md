# Prototyping high-level takeaways review, 2026-09-22

Author: Codex, directed by the repository owner.
Status: findings agreed and [implemented as section 00](2026-09-22-prototype-high-level-takeaways-implementation.md).
The discussion notes below preserve the reasoning behind the implementation.

The owner requested reviewing the complete results before agreeing on a concise introductory section.
This review evaluates the proposed B1/B3 shortlist, its resource tradeoffs, and the strongest messages for readers.
It changes no presentation, benchmark, or measured result.

## Evidence reviewed

- [Individual-lake results](../../benchmarks/results/lake-extraction.json): 384 runs, selection variants, size classes, and 150 prepared-selection equality records.
- [Shared-image results](../../benchmarks/results/tile-extraction.json): 324 runs and all 108 summarized combinations across nine tiles.
- [Multiple-tile results](../../benchmarks/results/cross-tile-extraction.json): complete-workload medians, ranges, contributions, and three repetitions per recipe.
- [Larger-workload results](../../benchmarks/results/lazy-reader-workloads.json): all fourteen completed configurations and both cohorts’ preflight coverage.
- [Execution audit](../../benchmarks/results/lazy-reader-workloads-audit.json): completion, memory stops, frozen inputs, and source integrity.
- The [corrected interpretation](2026-09-21-sleep-rerun.md#findings-and-interpretation), [timing qualifications](2026-09-22-sleep-rerun-review-response.md), and [reader walkthrough](2026-09-22-raster-lazy-extraction-walkthrough.md).

Ratios below were recomputed from the saved result summaries and complete configuration rows.
Total extraction is used for cross-reader elapsed comparisons. Read-plus-extract components have different boundaries.
Historical experiments retain their original timing scope, cache, thread settings, and selection qualifications.

## Proposed central message

**Inference:** The strongest direction is to read the required lake areas and reuse image data across lakes that share it.
B1 and B3 are the leading tested candidates for that shared-window approach.
The evidence supports this shortlist more strongly than a universal choice between its two readers.

The earlier repeated experiments support shared direct reads.
The newer, single-observation comparison adds B3 as a competitive alternative with different resource costs.
Neither the lazy label nor a shared graph guarantees that completed reads are reused.

## Findings supporting the message

### 1. Reading scope and reuse produce the largest observed differences

**Measured:** Earlier B1 results used 24–46 percent of matching separate-process A1 requests and 49–87 percent of their bytes.
Those comparisons combine historical lake medians with repeated tile medians, as disclosed in the [shared-image findings](../measurements.md#19-reading-every-lake-of-a-tile-in-one-process-cuts-requests-by-more-than-half).
The repeated multiple-tile experiment independently found 46 percent lower median workload time and 20.5 percent fewer bytes for B1 than A1.
Its [findings](../measurements.md#24-work-organization-changes-the-readers-costs-differently) retain the exact values and measurement basis.

**Measured:** In Florida, A1 took 5.9 times B1’s total extraction time. A3 took 10.4 times B3’s time.
Their requested-byte ratios were 5.1 and 4.8, respectively.
Whole-image C1 and C3 requested 4.3 and 4.6 times their corresponding B readers’ bytes, even with 1,000 Florida lakes.
For dispersed lakes, those whole-image byte ratios rose to 72.8 and 78.5.
Source: [larger-workload comparisons](../../benchmarks/results/lazy-reader-workloads.json).

**Measured:** Florida B2 took 43.9 times B3’s total extraction time and requested 61.6 times its bytes.
Their peak RAM was similar. B2 recorded repeated reads despite its shared graph.
Source: the [rerun interpretation](2026-09-21-sleep-rerun.md#findings-and-interpretation).
The B2/B3 comparison changes alignment and computation sharing together. It does not isolate either component’s performance effect.

**Proposed takeaway:** Read the required areas and reuse them across neighboring lakes.
Do not make whole-image reading or the B2 recipe the default based on these observations.
No measured threshold establishes when whole-image reading becomes preferable for a different workload.

### 2. B1 and B3 are a shortlist with meaningful tradeoffs

**Derived from measured results:** Percentage changes below compare B3 with B1 within each larger cohort.
Positive values mean B3 used more. Elapsed comparisons use total extraction.

| Resource | 100 dispersed lakes | 1,000 Florida lakes |
|---|---:|---:|
| Elapsed time | 7.9% lower | 33.5% lower |
| Worker CPU seconds | 126.4% higher | 15.6% higher |
| HTTP requests | 7.3% higher | 10.6% higher |
| Requested bytes | 6.1% lower | 4.2% lower |
| Peak aggregate RAM | 31.4% higher | 10.7% lower |

Source: [larger-workload results](../../benchmarks/results/lazy-reader-workloads.json).
The [walkthrough’s table](2026-09-22-raster-lazy-extraction-walkthrough.md#what-the-observations-say) gives the corresponding absolute elapsed, CPU, byte, and memory measurements.
Dispersed CPU totals were 10.8 seconds for B1 and 24.4 seconds for B3, despite their much longer elapsed durations.
Large relative CPU differences therefore coexist with modest absolute CPU totals in these trials.

**Inference:** B1 is a useful implementation baseline, with a direct reading loop and lower measured CPU and request counts.
B3 is a credible candidate when lower elapsed time matters, particularly for the concentrated workload tested.
Implementation simplicity follows the inspected code. Maintenance effort and engineering cost were not measured.
RAM has no consistent winner between B1 and B3.

**Proposed takeaway:** B3 finished sooner in these observations. B1 used less CPU and fewer requests.
Describing all their differences as small would obscure the Florida elapsed difference and the dispersed CPU difference.
Calling either generally more efficient would obscure the metric being optimized.

### 3. Lake count alone is an inadequate workload description

**Measured:** The 100-lake dispersed cohort needed 121 source products across 120 tiles.
The 1,000-lake Florida cohort needed four source products across four tiles.
Both B readers finished the Florida cohort sooner and requested fewer bytes, despite its larger lake count.
Source: [cohort preflights and comparisons](../../benchmarks/results/lazy-reader-workloads.json).

Dispersed A/B sharing reduced requested bytes by less than 0.3 percent for each reader.
Its A1 observation had lower elapsed time than B1. The retained A rows have different dates and source provenance.
These observations establish no consistent dispersed elapsed benefit from switching A to B.
The [corrected interpretation](2026-09-21-sleep-rerun.md#findings-and-interpretation) explains the limited reuse and timing caveats.

**Inference:** Describe workloads through source products, required blocks, lake sizes, and opportunities to reuse reads.
The two cohorts demonstrate why lake count is insufficient. They do not isolate concentration from geography, lake sizes, or product differences.

**Proposed takeaway:** Where lakes fall within images matters alongside how many lakes there are.

### 4. Extraction agreement and modest RAM are supporting results

**Measured:** All fourteen larger-workload configurations completed and agreed on their prepared extraction outputs.
B1/B3 peak aggregate RAM ranged from 0.223 to 0.332 GiB across the two cohorts.
Sources: [results](../../benchmarks/results/lazy-reader-workloads.json) and [execution audit](../../benchmarks/results/lazy-reader-workloads-audit.json).
Peaks include the extraction worker and supervisor, sampled every 0.1 seconds. Shorter spikes can be missed.

This does not establish a whole-pipeline memory budget.
Earlier selection and preparation had larger peaks, documented in the [multiple-tile record](../measurements.md#prototype-stage-4-lakes-across-tiles-2026-09-16).
Output agreement tests alternative reads of the same selected native pixels. It does not establish scientific quality or agreement between overlapping observations.

**Proposed treatment:** Include one compact supporting line about matching outputs and extraction RAM.
Keep the scope visible rather than presenting all processing as low-memory or production-validated.

## Proposed hierarchy for section 00

Lead with the shared-window direction and the B1/B3 shortlist, expressed in plain language before introducing codes.
Use three messages: read selectively and reuse, distinguish the two readers’ tradeoffs, and describe workloads beyond lake count.
Keep output agreement, RAM scope, and measurement limits in a short supporting note.

Possible simple imagery for later discussion:

- One image with several lake windows highlights the areas needed and the blocks they can share.
- Two reader cards distinguish elapsed time from CPU work, requests, bytes, and memory without a winner badge.
- A dispersed-versus-concentrated sketch explains why more lakes can require fewer source images.

The section does not need another implementation diagram, seven-configuration table, or hardware recommendation.
Detailed methods, uncertainty, and provenance remain linked from sections 01–07.

## Dispositions and limits

- Accepted: B1 and B3 as the proposed shared-window shortlist for discussion.
- Qualified: their tradeoffs are not uniformly small, and no reader wins every resource metric.
- Preserved: limited sharing benefits for dispersed lakes, differing historical settings, and the retained-row timing caveat.
- Accepted and deferred: synthesis, simple imagery, and implementation of section 00 after discussion.

The larger comparison has one completed observation per configuration on one laptop, with uncontrolled network conditions.
Earlier repeated experiments strengthen the shared-reading direction but do not provide repeated B3 measurements.
Elapsed time, worker CPU, requested bytes, and RAM are distinct measurements. They do not establish AWS throughput, billing, or production operating cost.
No new provider request, experiment, production choice, commit, or publication is part of this review.

## Verification

The repository check workflow passed:

- `uv sync --locked`: 59 packages resolved and 56 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, with 121 files already formatted.
- `uv run pytest -q`: 276 passed in 29.39 seconds, with 13,000 existing dependency deprecation warnings.
- `git diff --check`: passed.

SHA-256 comparisons confirm all thirteen result JSON files, the template, renderer, and generated page remain unchanged.
All twelve source digests still match the frozen rerun manifest.
No browser check was needed because the presentation did not change.

## Proposed next step

Discuss the message hierarchy and the degree of emphasis on B1 versus B3.
Then synthesize the agreed findings into section 00 with concise text and simple imagery.
