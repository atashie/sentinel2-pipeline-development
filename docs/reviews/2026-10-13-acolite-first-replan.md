# ACOLITE-first replan: owner direction, document changes, tests, and phases, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: proposed plan. This step adds this record and [proposed decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md). Nothing else changes. No provider script ran.
The owner has not authorized any phase below. Each phase runs as one or more authorized steps under the workflow in [CLAUDE.md](../../CLAUDE.md).

## Why the plan changes

On 2026-10-13 the owner asked for a literature analysis of Sen2Cor's suitability for water quality.
Five research notes and a report were produced with separate research agents. They sit under `data/research/`, outside git.
They are AI-generated input, not evidence, under the [documentation rules](../../.claude/rules/docs.md). Every fact below drawn from them is `unverified` until a check record confirms it.
The repository already holds one documented piece of the answer. Claim R3 in [s2-best-practices.md](../s2-best-practices.md) records that ESA validates Level-2A reflectance at land sites only.

The analysis reported these inputs. Each names the primary page to recheck.

| Input | Primary source to recheck | Status |
|---|---|---|
| The Sen2Cor Algorithm Theoretical Basis Document states the processor "is not designed for applications over water or on coastal regions". | ESA STEP, S2-PDGS-MPC-L2A-ATBD, issue 2.10 | unverified |
| Peer-reviewed intercomparisons over inland water rank Sen2Cor behind POLYMER, C2RCC, and ACOLITE, except in turbid water at the green to red-edge bands. | Warren et al. 2019, doi 10.1016/j.rse.2019.03.018, and the studies the report lists | unverified |
| No study evaluates Sen2Cor 2.12 or 2.13, the processors behind baselines 05.11 to 05.13. | ESA STEP release pages for Sen2Cor 2.11 to 2.13 | unverified |
| USGS publishes "Sentinel-2 ACOLITE-DSF Aquatic Reflectance for the Conterminous United States" on AWS Open Data, in us-west-2, readable without credentials. | AWS Open Data registry entry `usgs_aqr`, USGS ScienceBase DOI 10.5066/P904243C | unverified |
| The USGS product is 20 m, eleven bands plus NDWI, ACOLITE version 20221114.0, negatives retained, no cloud or shadow layer, scenes added daily. | The same two pages and the USGS data page | unverified |
| ACOLITE processes Level-1C only and reads local product bundles. | ACOLITE manual and `acolite/sentinel2/l1_convert.py` on GitHub | unverified |
| ACOLITE's aerosol estimate depends on the processed window, so a clipped run and a whole-tile run give different values. | ACOLITE manual, settings `limit` and `dsf_aot_estimate`, and the developer's forum guidance | unverified |

## Owner direction, 2026-10-13

The owner read the analysis and gave eight directions. They are the authority for [decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md).

1. The initial scope is the lower 48 states. The assessment must state clearly that the ACOLITE choice requires a workflow redraft, with additional hurdles, before any expansion beyond the United States.
2. Level-2A keeps four roles. It may serve land monitoring in parallel. It may supply flags that the ACOLITE product lacks, such as cloud and shadow, still to be determined. The modeling team may compare Sen2Cor and ACOLITE values in a modeling context. The assessment must determine whether the route holds enough raw data to reprocess to ACOLITE values with the published algorithm. If not, it must name an alternative raw source.
3. "Reverse engineer" means running ACOLITE from Level-1C to fill gaps.
4. Self-run ACOLITE is documented as context only, with a complexity estimate. The owner expects runs clipped to the water bodies of interest. Whole-tile runs are wasteful.
5. The 20 m grid of the ACOLITE product is accepted.
6. The product's NDWI layer is stored as a delivered layer.
7. The frozen Level-2A results stay as reference, pared down. Attention moves to the most production-relevant tests.
8. Licensing is outside this assessment. The owner handles it with legal counsel.

One caveat belongs beside direction 4. The analysis reports that ACOLITE's dark spectrum fitting estimates aerosol from the darkest pixels of the processed window.
A run clipped to one lake therefore uses a different aerosol estimate than the USGS whole-tile run. The developer recommends fixing the aerosol for small windows.
Clipping cuts memory and time, as the owner expects. It also means self-run values will not reproduce the USGS values. Both statements are `unverified` until checked and, if the owner wants numbers, measured.

## Owner direction on processor performance, 2026-10-13

After the [Phase B validation review](2026-10-13-phase-b-claim-validation.md), the owner gave a further direction the same day:

> "Let's hold off on forming a strong opinion on sen2cor vs acolite in terms of performance modeling water quality until we run our own experiments. In the meantime, we can defer to authority with the assumption that acolite is optimized for this purpose and is our initial primary resource"

Assumption A52 in [assumptions.md](../assumptions.md) records it. [Decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) keeps its provisions.
Where those experiments run, and against which reference, is an open owner decision in Phase D of the [work plan](../work-plan.md).

## Owner direction on standalone options, 2026-10-14

After the [T4 record](2026-10-13-phase-c-t4-validity.md) showed that the join key can match two items of one pass, the owner directed:

> "Treat acolite scenes as standalone products; they should include flags within the data to indicate that a pixel is masked due to data quality issues. We can defer joining scenes until we prove beyond a shadow of a doubt that we'd need to do so, and for now treat our options as "acolite only" or "sen2cor only""

[Decision 0009](../decisions/0009-standalone-options-join-deferred.md) records it and amends direction 2 above. Level-2A's flag, land-value, and fallback roles pause. Its comparison role becomes the Sen2Cor-only option.
The tables below keep the plan as proposed on 2026-10-13. These parts no longer apply: T3 as the store's join, the two-source join prototype in Phase C, and the Level-2A match in Phase E.
The [work plan](../work-plan.md) carries the current steps. The [direction record](2026-10-14-standalone-options-direction.md) lists every changed document.

## What carries over and what changes

| Element | Carries over | Needs rework |
|---|---|---|
| The store never mosaics. Every record carries its tile and a primary or overlap marker. | Yes | Overlap differences must be measured on the ACOLITE product. ACOLITE fits aerosol per tile. |
| Three pixel classes with exact coverage fractions and edge distances. | Yes | The primary product has one grid, 20 m. Bodies of 10 m and 30 m have no interior pixel on it. |
| Shared-window readers beat whole-tile reads and lazy chunk reads. | In principle | Every number was measured on Level-2A files. None describes the ACOLITE product. |
| The gap survey, the offset findings, and the copy differences. | As facts about the supplementary route | The primary route has no coverage, latency, or encoding measurement. |
| The cost model and its sensitivities. | The structure | Bytes per pixel, files per scene, blocks per tile, grids, coverage, and acquisition counts change. A join step appears. |
| The draft data contract. | Identity and accounting fields | Two source products per water body, ACOLITE provenance, delivered NDWI, and masked-pixel semantics. |
| The public pilot manifest and both larger cohorts. | Yes, all in the lower 48 except the Alaska region | The Alaska region leaves the primary scope and stays as a Level-2A-only case. |

### Repository documents

| Document | Change | Phase |
|---|---|---|
| [decisions/0008](../decisions/0008-acolite-aquatic-reflectance-first.md) | Activate after owner authorization. | A |
| [assumptions.md](../assumptions.md) | Revise A3, A4, A13, and A20. Add rows for the primary product, the Level-2A roles, the self-run context, the delivered NDWI, and the reference series. | A |
| [data-contract.md](../data-contract.md) | Draft v2 with source-product provenance: product family, processor and version, the Level-1C baseline from the product name, and the aerosol mode. Add the settings-file digest, the quality source product, a mask reason, and NDWI as a delivered layer. | A, revised after T1 |
| [work-plan.md](../work-plan.md) | Replace the open Phase 2 items and stage 5 with the phases below. | A |
| [CLAUDE.md](../../CLAUDE.md) and [README.md](../../README.md) | Current phase, route statement, and gotchas once measured. | A, then per phase |
| [s2-best-practices.md](../s2-best-practices.md) | New section on atmospheric correction over water. Revise practice P10. | B |
| [options-inventory.json](../options-inventory.json) and [assessment-checks/](../assessment-checks/README.md) | New access-route candidate for the USGS product and a context candidate for self-run ACOLITE. New claims with research drafts and check records. New issues, probes, findings, and combinations. Earth Search's role changes. | B |
| [gap-survey-plan.md](../gap-survey-plan.md) | Add the USGS coverage survey and the join test. | B |
| [measurements.md](../measurements.md) | New findings per test. The existing findings stay as the Level-2A series. | B, C |
| [aws-cost-analysis.md](../aws-cost-analysis.md) and `cost-analysis/inputs.json` | Re-parameterize from T1 and T6. Add the join work and the second source's storage. | C |
| [examples/README.md](../../examples/README.md) | Note that the Alaska region lies outside the primary product. | A |
| `benchmarks/` | New metadata survey and validity scripts. A source option for the extraction scripts. | B, C |
| `tools/s2-options.template.html` and `tests/` | The tab changes below. The archive-naming test grows to four archives. | B, C |

### Discovery tab

- Section 01, sensors. Small edit. The primary product carries eleven bands on one grid and omits B9 and B10.
- Section 02, archives. Full rewrite. The question becomes which of three public archives serves which purpose. The USGS bucket is primary for water pixels in the lower 48. Collection 1 and the older copy are supplementary. The coverage chart gains the USGS product's coverage from T2.
- Section 03, risks. Add the atmospheric correction as the lead risk, with the rechecked literature. Revise three risks. The primary product has no cloud, shadow, or snow layer. Its processor version is pinned while the Level-1C baseline keeps changing. Its 10 m bands are averaged to 20 m before delivery.
- Section 04, processing. The product search gains a second source and a join. The stored record example becomes one 20 m row with two product identities and the per-scene settings file.
- Section 05, maps. Add an aquatic reflectance view of the same Lake Lanier date, if the owner authorizes one more image download.
- Expansion statement. One plain paragraph states that service beyond the United States needs a workflow redraft. The hurdles are Level-1C access, compute, processor provenance, the missing cloud mask, and validation.
- Issue register. Nine new issues:
  - A land processor over water.
  - No cloud mask in the primary product.
  - Coverage limited to the lower 48.
  - A pinned processor version with an unknown reprocessing policy.
  - Processor-masked non-water pixels.
  - One 20 m grid.
  - No catalog beyond bucket listing.
  - A single-agency dependency with no service commitment.
  - The share-alike license on derived data. Recorded, not assessed, under direction 8.

### Prototyping tab

- Section 00, takeaways. Rewrite from T4 to T7. Every current number is Level-2A specific.
- Section 01, what we tested. The nine-recipe grid and both cohorts stand. The source changes to the USGS product.
- Section 02, main comparison. Rebuild from the T6 replay of readers B1 and B3.
- Section 03, costs. Rebuild from the re-parameterized model.
- Section 04, earlier experiments. Pare down to a Level-2A reference series: one table with the stage, its question, its headline, and its record. Remove the collapsed panels from the page. The records and [measurements.md](../measurements.md) keep every number.

## Tests

Every test contacts a provider. Each runs only when the owner invokes it, under the [benchmark rules](../../.claude/rules/benchmarks.md). Order follows cost. T1 to T3 and T8 read no pixel.

| # | Test | Reads pixels | Proposed evidence | Settles |
|---|---|---|---|---|
| T1 | Bucket layout and file headers for the stage 1 tile-date and two others. | No | `benchmarks/results/aqr-headers.json` | Data type, no-data, scale, CRS, block size, compression, overviews, settings file content, and masked non-water pixels. |
| T2 | Coverage survey of the USGS product on the survey tiles in the lower 48, against Earth Search Level-1C and Level-2A acquisition counts. | No | `benchmarks/results/aqr-coverage.json` | Missing scenes, duplicates, baseline mix, 2022 coverage, and latency from object timestamps. |
| T3 | Join test: every USGS scene to an Earth Search Level-2A item by tile, sensing time, and baseline. | No | In the T2 result | Whether quality layers can always be attached, and the join key. |
| T4 | Validity on the pilot lakes, per band and pixel class. | Yes | `benchmarks/results/aqr-validity.json` | How many shoreline and near-land pixels the processor masks. NDWI against the SCL water class. Negatives. Unmasked cloud. |
| T5 | Paired values: the same windows from Collection 1 on the same tile-dates. | Yes | `benchmarks/results/aqr-pairs.json` | Where the two corrections disagree, per band and pixel class. |
| T6 | Access replay: stages 2 to 4 and readers B1 and B3 on the USGS product, same cohorts, same harness. | Yes | `benchmarks/results/aqr-workloads.json` | Requests, bytes, time, memory, and the cost inputs. |
| T7 | Overlap test on the lakes in two tiles, from T6's reads. | Yes | In the T6 result | Whether per-tile aerosol fitting widens tile disagreement. |
| T8 | Retention check: object timestamps and entity tags over several weeks, plus a written question to USGS. | No | `benchmarks/results/aqr-retention.json` | Whether scenes are replaced or versioned. |
| T9 | Optional: one self-run ACOLITE scene from a Copernicus account, clipped to the pilot lakes, compared to the USGS scene. | Yes | `benchmarks/results/acolite-self-run.json` | Feasibility, run time, memory, and whether clipped values match. Context only under direction 4. |

Rules for the tests:

- Declare tolerances for T4, T5, and T7 before reading any difference.
- Record bucket, region, and payer in every result. Both buckets are expected to answer unsigned requests. The result proves it.
- Reuse the pilot manifest, the frozen cohorts, the harness, and the pixel-class code. Change the source, not the method.
- T1 decides the contract draft. If the processor masks shoreline or near-land pixels, those classes come from Level-2A. If values are 32-bit floats, storage per pixel doubles.
- T9 needs a Copernicus Data Space account and local disk for one Level-1C product. It runs only if the owner asks for numbers behind the complexity estimate.

### Raw-data sufficiency

Direction 2 asks whether the route holds enough raw data to reproduce ACOLITE values. This is research, not a provider test.
The inventory already records that Earth Search indexes a Level-1C collection whose assets point into the requester-pays JPEG 2000 bucket in eu-central-1. The GeoTIFF buckets hold Level-2A only.
Phase B answers three questions with check records. Does ACOLITE accept any Level-2A input? Can a reader clip Level-1C band files to a lake before download, given claim R6 on JPEG 2000 markers from baseline 05.12? Which raw sources exist outside AWS, and at what terms?
The expected answer is that the GeoTIFF store cannot be reprocessed to ACOLITE values. Level-1C from AWS, the Copernicus Data Space, or Google is then the raw source. The check records decide.

## Phases

| Phase | Work | Acceptance | Gate |
|---|---|---|---|
| A. Re-scope | Activate decision 0008. Revise the assumptions, the contract draft, the work plan, CLAUDE.md, README.md, and the examples note. | Links resolve, tests pass, every changed assumption cites the decision. | Owner |
| B. Discovery II | Research drafts and check records for the inputs above and the raw-data questions. T1, T2, T3. New candidates, claims, issues, probes, findings. Discovery tab rewrite. | Every documented claim binds a source and a check. Probes recorded. The coverage chart comes from T2. | Codex, Claude Code, then owner |
| C. Prototyping II | T4 to T7. A two-source join prototype. Cost re-parameterization. Prototyping tab rebuilt with the ACOLITE series and the pared Level-2A reference. | Per test, as today: declared tolerances, result files, findings, records. | Per step |
| D. Scientific checks | Interpret T5 and T7 as the first validation items. Replace the stage 5 list. T9 only on request. | Findings with limits. No in situ claim. | Owner |
| E. Integration specs | Units of work: discover new USGS scenes, match the Level-2A item, extract per tile, publish with both provenances. Revision rules for two sources. Storage layout. Monitoring. | Orchestrator-agnostic, idempotent, declared inputs and outputs. | Owner and the platform team |
| F. Tradeoffs | Hosted ACOLITE against self-run against Level-2A. Risk register. Cost curves. Recommendation with the evidence gaps, including the expansion hurdles. | Every row cites a claim, a finding, or a result file. | Owner |

Phase A and T1 are independent. The owner can authorize both at once.

## Deferred and out of scope

- Expansion beyond the United States. Recorded as a hurdle list, not designed.
- Self-run ACOLITE as a prototyped workflow. Context only, with a complexity estimate.
- The modeling comparison of Sen2Cor and ACOLITE values. The modeling team owns it. The store must serve both products for the same pixels so it is possible.
- Licensing. The owner handles it with legal counsel.
- The Alaska pilot region. Outside the primary product. It stays in the manifest as a Level-2A-only case.
- The primary-tile tie rule of assumption A22. Still an owner decision, now to be informed by T7.

## Proposed next step

Phase A. Activate decision 0008 and revise the planning documents listed above. No provider script. Then stop for review.
T1 can run as the step after, or in parallel if the owner authorizes it with Phase A.
