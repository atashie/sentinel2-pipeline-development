# Phase B claim validation: eight independent reviews, verdicts, and corrections, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner. Reviewers: eight Claude Code subagents on Sonnet.
Status: corrections applied, awaiting owner review. Phase B itself is commit 4e89ea2.

## Step and authorization

On 2026-10-13 the owner wrote: "commit, then launch a team of review agents (haiku or sonnet) to validate or deny each of the new major claims / upturned findings. Collate their results then commit and push."
Phase B was committed as 4e89ea2. Eight reviewers then checked the new claims, one group each. This record collates their verdicts and lists the corrections.

## Method

Each reviewer was independent of the researcher, the checker, and the author of the claims it reviewed. Each wrote one verdict file under [phase-b-validation/](../assessment-checks/phase-b-validation/).
Verdicts are `validated`, `partially validated`, `denied`, or `unverifiable`. A partial verdict carries a suggested correction.

- Measured claims were recomputed offline from the saved evidence with each reviewer's own code. The evidence was the T1 headers, the T2 and T3 listings, and the crop arrays.
- Documented claims were rechecked against primary pages fetched fresh by the reviewer.
- One reviewer read every changed document for consistency and overclaims.
- No reviewer contacted the USGS bucket. Two reviewers made metadata-only calls to the Earth Search API, and one to an EODC catalog. No imagery was read.

| Group | File | Validated | Partial | Denied |
|---|---|---|---|---|
| Literature, claims W1 to W8 and R5 | [literature.json](../assessment-checks/phase-b-validation/literature.json) | 3 | 3 | 0 |
| USGS documentation | [usgs-docs.json](../assessment-checks/phase-b-validation/usgs-docs.json) | 8 | 0 | 0 |
| Probe T1, finding 26 | [t1-headers.json](../assessment-checks/phase-b-validation/t1-headers.json) | 3 | 3 | 0 |
| Probe T2, finding 27 | [t2-coverage.json](../assessment-checks/phase-b-validation/t2-coverage.json) | 7 | 1 | 0 |
| Probe T3, finding 28 | [t3-join.json](../assessment-checks/phase-b-validation/t3-join.json) | 3 | 3 | 0 |
| Crop and flags, finding 29 | [crop-flags.json](../assessment-checks/phase-b-validation/crop-flags.json) | 5 | 0 | 0 |
| Self-run ACOLITE, findings F-29 and F-30 | [acolite.json](../assessment-checks/phase-b-validation/acolite.json) | 5 | 2 | 0 |
| Consistency and overclaims | [consistency.json](../assessment-checks/phase-b-validation/consistency.json) | 0 | 6 | 0 |
| Total | | 34 | 18 | 0 |

No claim was denied. Every number the probes reported reproduced exactly from the raw evidence. The partial verdicts concern scope, wording, and interpretation.

## What the reviews upturned

- **Processor version.** The three settings files carry the default keys of ACOLITE release 20250402.0, apart from three run keys. Release 20221114.0, the version USGS documents, lacks 148 of them. Claude Code confirmed this against both releases' defaults files on GitHub. Finding 26, issue I-34.
- **Join metric.** The 51 percent baseline agreement depends on trying Collection 1 first. Allowing either collection gives 58 percent overall, and 84 percent instead of 13 percent for 2021. Finding 28.
- **Screening change.** The product's cloud screening tightened in 2023, and the partial-tile effect reverses from 2024. Finding 27.
- **Delivered quantity.** ACOLITE 20221114.0 removes flagged pixels from its water-leaving output. Land pixels in the crop carry values, so the delivered bands are another quantity, unnamed by USGS. Finding 29.
- **Log files.** USGS documents a processing log file per scene. None of the 263,590 listed objects is one. Finding 27.
- **Literature.** Three of four studies put C2RCC, and Polymer where tested, ahead of both Sen2Cor and ACOLITE. The order of Sen2Cor and ACOLITE changes with study and metric. The paper documenting the USGS product could not be read. Claims W5 to W8, section 7 of [s2-best-practices.md](../s2-best-practices.md).
- **Aerosol window.** The USGS 300-pixel tiles at 20 m are the same 6 km as ACOLITE's default 600 pixels at 10 m. Finding F-30 had contrasted them.
- **Payer evidence.** A missing charge header proves nothing, because S3 sends it only on request. Unsigned requests succeeding is the evidence. Finding 26 and the measurement intro.
- **Baseline 05.13.** The October 2026 quality report gives two deployment dates. Claim W3.

## Corrections applied

| File | Correction |
|---|---|
| [measurements.md](../measurements.md) | Finding 26 scoped to the three probed scenes, GDAL default scale stated, version mismatch and extra settings added. Finding 27: 2017 share, baseline sentence for 2015 to 2017, screening regimes, no-data periods, latency bias, log files, renamed heading. Finding 28: either-collection join, numbering caveat, pass-level key. Finding 29: five layers, flag meaning, ACOLITE masking, negative counts. Heading dated. |
| [benchmarks/aqr_coverage.py](../../benchmarks/aqr_coverage.py) and its result | The analysis adds the either-collection join and per-year cloud and no-data splits. The result was recomputed offline from the saved listings with `--from-raw`. No new provider contact. |
| [Map builder](../../tools/build_discovery_maps.py) and provenance | Per-band negative counts recorded. Images unchanged. |
| [s2-best-practices.md](../s2-best-practices.md) | W3 dates and attribution, W8 split with the Shan chlorophyll result, W10 date, P15 and P16, two unverified leads, R5. Heading dated. |
| [data-contract.md](../data-contract.md) | Processor version source, unified wording on missing layers, join numbers, the Phase C join prototype in place of test T3. |
| [Inventory](../options-inventory.json) | I-31 to I-35, I-39, and I-40 reworded. PR-09 to PR-11, F-27 to F-30, and C-10 corrected. |
| [processing-workflow-acolite-checks.json](../assessment-checks/processing-workflow-acolite-checks.json) | The developer's hedge restored in claim `scaling_water_bodies-2`, verdict now `corrected`. |
| Discovery and Prototyping tabs | Sen2Cor wording matched to W1 and R3. The lead risk states the literature result and W3. Header scope, version, latency window, either-collection join, and expansion note corrected. A banner labels the Prototyping results as the Level-2A series. |
| [Decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) | A dated evidence note. No provision changed. |
| Planning documents | [assumptions.md](../assumptions.md) intro, A4, and A47. [CLAUDE.md](../../CLAUDE.md) convention and gotchas. [work-plan.md](../work-plan.md) gap item, split Phase D item, and the owner's accuracy decision. [README.md](../../README.md), [aws-cost-analysis.md](../aws-cost-analysis.md), and the gap survey plan's relative dates. |
| [Phase B record](2026-10-13-phase-b-discovery-ii.md) | Status line, an owner summary, corrected findings, and both relevant review triggers. |

## Not changed, and why

- The estimated engineering-effort claim for self-run ACOLITE stays. Its reviewer suggested "low to medium for named scenes, medium to high to match USGS". Combination C-10 now asks that question.
- The candidate questions in the inventory come from the research files and are not regenerated. Several are answered by findings 26 to 29.
- Martins et al. (2017) and Li et al. (2023) are not inventory claims. They need research and check records first.
- The Prototyping tab carries one banner. Its full rebuild on the primary product is Phase C.
- The verdict files keep each reviewer's wording. The developer's forum name is replaced with a role.

## Evidence

`/check` on 2026-10-13: `uv sync --locked`, `uv run ruff check .`, and `uv run ruff format --check .` passed. `uv run pytest -q` gave 342 passed and 1 failed in 53.89 s.
The failure is `test_supervisor_stops_a_real_worker_and_descendant`: the worker finished instead of being stopped for memory. It passes when run alone, twice.
The committed tree 4e89ea2 fails the same way under the same conditions, and passed earlier the same day. Another session was loading the machine. No file this review changed touches that test or its module.
The collation, renderer, gap-report, sensor-band, and review-layer `--check` commands report their outputs current.

## Proposed next step

The owner compacts memory. Then Phase C, first step: probe T4, validity per band and pixel class on the pilot lakes, with tolerances declared before any read. It reads pixels and needs explicit authorization.
