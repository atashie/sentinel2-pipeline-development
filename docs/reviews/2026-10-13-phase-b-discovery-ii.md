# Phase B, Discovery II: check records, probes T1 to T3, and the Discovery rewrite, 2026-10-13

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered and committed as 4e89ea2 on the owner's instruction of 2026-10-13. Awaiting review by Codex and the owner.
An eight-agent [validation review](2026-10-13-phase-b-claim-validation.md) followed the commit. Its corrections are applied in this record and the documents it names.

## For the owner

- Decision 0008 rests on Sen2Cor's design statement, its land-only validation, and the product's availability. It does not rest on a measured accuracy advantage. The literature read shows no consistent ranking of ACOLITE and Sen2Cor.
- The work plan now carries your decision on whether an accuracy comparison belongs in the assessment, Phase D.
- USGS documents ACOLITE 20221114.0, but the three settings files read carry the keys of release 20250402.0. Issue I-34.
- The join rule is a Phase C choice. Collection 1 first gives 51 percent baseline agreement, and either collection gives 58 percent.

## Step and authorization

The owner wrote "Please proceed with implementing phase b" on 2026-10-13. Phase B is defined in the [replan record](2026-10-13-acolite-first-replan.md).
Two questions went back to the owner before any provider contact. The owner answered both on 2026-10-13:

- Run probes T1 to T3 as part of Phase B: "Run T1-T3 in Phase B (Recommended)".
- Read one more image crop of Lake Lanier from the USGS bucket for the maps section: "Yes, one crop".

The owner later wrote "proceed" while this step was running. This record reads it as continuing Phase B, not as authorizing Phase C.

Acceptance checks from the replan record: every documented claim binds a source and a check, probes are recorded, and the coverage chart comes from T2. All three hold, evidence below.

## What changed

| Area | Change |
|---|---|
| Check records | Three research and check pairs under [assessment-checks/](../assessment-checks/README.md): the USGS product, self-run ACOLITE, and the water-correction literature with Level-1C sources. |
| [collate_checks.py](../../tools/collate_checks.py) | Binds supplementary pairs named `<dimension>-<topic>-research.json` beside each dimension's pair. A draft without its checks binds nothing. Output for the existing pairs is unchanged. New test `tests/test_collate_checks.py`. |
| [Inventory](../options-inventory.json) | Candidate `ar-usgs-acolite-aqr`, role `primary`, and context candidate `wf-acolite-self-run`. Earth Search becomes `supplementary`, a new role in the [format](../assessment-data-format.md). Ten issues I-31 to I-40, probes PR-09 to PR-11, findings F-27 to F-30, combinations C-09 and C-10. The four Earth Search combinations become `supplementary`. The selection block cites decision 0008. |
| Probes | [aqr_headers.py](../../benchmarks/aqr_headers.py) for T1 and [aqr_coverage.py](../../benchmarks/aqr_coverage.py) for T2 and T3, with pure helpers in [s2proto/aqr.py](../../src/s2proto/aqr.py) and fixture tests in `tests/test_aqr_probes.py`. The harness client gained HEAD and text requests. |
| [measurements.md](../measurements.md) | Findings 26 to 29 and what Phase B does not show. |
| [test_inventory.py](../../tests/test_inventory.py) | The best-practices claim pattern accepts the new W rows beside G, R, and Q. No assertion was weakened. |
| [test_presentation.py](../../tests/test_presentation.py) | Names four archives, ties the archive numbers to the T2 result, and checks the two new map views. |
| [data-contract.md](../data-contract.md) | Encoding, grid, flags, join key, and time fields answered from the probes. New fields `acolite_flags` and `quality_baseline_match`. `conversion_source` gains `provider_documentation`. |
| [s2-best-practices.md](../s2-best-practices.md) | New section 5 on atmospheric correction over water. Practice P10 revised. Claim R5 updated for baseline 05.13. Sections 5 to 7 renumbered 6 to 8. |
| [gap-survey-plan.md](../gap-survey-plan.md) | The USGS coverage survey and the join test, with rerun steps. The route sentence now dates Earth Search's former role. |
| Discovery tab | [Template](../../tools/s2-options.template.html) and [renderer](../../tools/render_options.py): three archives, the correction as the lead risk, the join, and the expansion statement. Also a second coverage strip from T2, ten issues placed, and two map views from the crop. |
| [Map builder](../../tools/build_discovery_maps.py) | `--download-aqr` reads the authorized crop. The six earlier images are byte-identical after the rebuild. |
| Planning documents | [assumptions.md](../assumptions.md) A3, A4, A13, A46, and A47. The [work plan](../work-plan.md), [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), the [examples note](../../examples/README.md), and the benchmark and tool READMEs. |

## Evidence

Provider contact, all unsigned, all owner-authorized:

| Run | Requests | Read |
|---|---|---|
| Design reconnaissance before T1 existed | 3 bucket listings, logged under `data/aqr-recon/` | Listings only |
| T1, `uv run python benchmarks/aqr_headers.py` | 18 bucket GETs, 42 HEADs, 6 Earth Search searches, 39 GDAL header ranges | Three settings files whole, 638,976 header bytes requested, no pixel |
| T2 smoke run on tile 17SKU, output under `data/` and then deleted | 12 bucket listing pages, 6 Earth Search pages | Listings only |
| T2 and T3, `uv run python benchmarks/aqr_coverage.py` | 281 bucket listing pages, 216 Earth Search requests | Listings only, 90 MB and 66 MB of responses |
| Crop, the `--download-aqr` function of the map builder | 5 HEAD or GET responses and 15 range reads | One 400 by 400 window of five layers |

Payer: the bucket owner for every USGS request. A requester-pays bucket refuses unsigned requests, and every T1 response was HTTP 200 without a charge header.
Check records: USGS product 49 confirmed and 1 corrected. Self-run ACOLITE 48 confirmed and 9 corrected, plus 3 estimates the parent agent reviewed and accepted. Water correction: 36 confirmed and 10 corrected.
Collation bound 436 inventory claims with no gap. The [presentation](../s2-options.html) renders from the inventory, the two probe results, and the map provenance.
`/check` on 2026-10-13: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q` passed, 342 tests in 32.89 s.
The collation, sensor-band, renderer, gap-report, and review-layer `--check` commands all report their outputs current.
A style scan covered the added Markdown lines, the new inventory strings, and the template's added text. It found no semicolon, no forbidden modal verb, and no sentence over 25 words.

## What the probes found

Findings 26 to 29 in [measurements.md](../measurements.md#phase-b-probes-on-the-usgs-aquatic-reflectance-product-2026-10-13) own the numbers. In short:

- Each of the three probed scenes is 14 objects: eleven 20 m bands, NDWI, a flags layer, and a settings file. Values are 16-bit integers. The headers carry no reflectance scale.
- The grid matches the Level-2A 20 m grid. The settings name tiled aerosol estimation on 300-pixel tiles at 20 m and no residual glint correction. Their keys match a later ACOLITE release than the documented one.
- From 2018 the product holds 41 to 61 percent of Earth Search's acquisitions per year on 24 lower-48 tiles. Cloudy and partial acquisitions are missing most often.
- Its inputs from 2018 to 2022 are mostly original Level-1C baselines. 92 percent of scenes join to a Level-2A item of the same pass. 51 percent join to the same baseline with Collection 1 first, and 58 percent with either collection.
- Published scenes sensed from 2026-06-15 appeared a median 0.33 days after sensing, a statistic biased low. Most of the history arrived in batches.
- The bucket also holds Alaska scenes, although USGS documents the conterminous United States.
- In the one crop, every pixel of the five layers read carries a value, and the flags mark non-water pixels. USGS documents the bands as water-leaving reflectance, which ACOLITE itself masks.

## What the literature checks found

Section 5 of [s2-best-practices.md](../s2-best-practices.md#5-atmospheric-correction-over-water) holds the claims, W1 to W11.

- The Sen2Cor algorithm document states the processor is not designed for applications over water or coastal regions. ESA still lists that issue as current. Claim W1.
- The replan input that intercomparisons rank Sen2Cor behind POLYMER, C2RCC, and ACOLITE is not supported as one statement. Claims W5 to W8.
- Three of the four studies put C2RCC, and Polymer where tested, ahead of both Sen2Cor and ACOLITE. Their order of Sen2Cor and ACOLITE changes with the study and the metric.
- One study found Sen2Cor second-best by median spectral angle over inland water, ahead of Acolite, but worst across all its sites. ACIX-Aqua did not test Sen2Cor.
- Another study found ACOLITE better than Sen2Cor in eutrophic Spanish lakes. A 2026 study found Sen2Cor's pooled fit slightly better than ACOLITE's in two Chinese reservoirs, and its chlorophyll error lowest.
- The paper documenting the USGS product could not be read. Two further studies with both processors are unrecorded leads, section 7 of the best-practices document.
- The studies that name versions tested older processors than the USGS product or Earth Search use. No claim above describes pond-sized waters.

So decision 0008 rests on the processor's design statement and ESA's land-only validation, claims W1 and R3. It does not rest on a demonstrated accuracy advantage of ACOLITE over Sen2Cor for these waters.
The modeling comparison of both corrections on the same pixels, which the store enables, is the relevant test. This record raises it for the owner. It does not change decision 0008.

- Sen2Cor 2.13.01 and baseline 05.13 add water-specific aerosol changes. 05.13 entered operations in September 2026, on a date the quality report gives two ways. Claims R5 and W3.
- Level-1C on AWS is JPEG 2000 in a requester-pays bucket. Some Earth Search Level-1C items point their assets at the Level-2A bucket. Claim W9.
- Whether a reader can clip Level-1C JPEG 2000 before download is unsettled. GDAL documents that its OpenJPEG driver ignores tile-part length markers, but newer OpenJPEG uses them. Claim W10.

## Decision 0008 review triggers

[Decision 0008](../decisions/0008-acolite-aquatic-reflectance-first.md) lists triggers for revisiting it. Phase B bears on three:

- Masking of shoreline or near-land pixels: none in the one crop. Probe T4 decides at scale.
- An encoding that breaks the integer-plus-conversion contract: no. The scale comes from the documentation, recorded as `provider_documentation` in the contract.
- A join that fails for a material share of scenes: 8 percent find no Level-2A item. 41 percent join to another baseline with Collection 1 first, and 34 percent find no same-baseline item in either collection. Whether that is material is the owner's call.
- Gaps the supplementary route cannot fill: not met on the survey tiles. Every acquisition Earth Search lists without a USGS scene is in Earth Search by definition. The fill policy decides how it is used.

## Limits

- No pixel test describes the primary product. Masking, validity per pixel class, and agreement with Level-2A wait for probes T4 and T5.
- The crop is one scene, chosen for the presentation. Its flag encoding, multiples of 10,000, is observed, not documented.
- Earth Search is the coverage reference, and it lists nothing on the survey tiles before 2017. Completeness against ESA is not measured.
- Object timestamps describe the bucket copy. They do not show retention or replacement, probe T8.
- Candidate questions in the inventory come from the research files and predate the probes. Several are answered by findings 26 to 29.
- The page was checked by tests and by reading the rendered HTML, not in a browser. The browser extension was not connected.
- Check records are documentation checks by AI agents on two models. They are not human review.

## Dispositions

| Item | Disposition |
|---|---|
| Replan input: the Sen2Cor ATBD statement on water | Fixed. Confirmed verbatim in issue 2.10, still current. Claim W1. |
| Replan input: intercomparisons rank Sen2Cor behind POLYMER, C2RCC, and ACOLITE | Corrected with evidence. Not supported as one statement. Each study's own result is a separate claim, W5 to W8. |
| Replan input: no study evaluates Sen2Cor 2.12 or 2.13 | Accepted and deferred. An absence cannot be documented. It stays `unverified` in section 7 of the best-practices document, with the search recorded. |
| Replan input: the USGS product on AWS, region, and unsigned access | Fixed. Confirmed by check records and by probe T1. |
| Replan input: 20 m, eleven bands plus NDWI, ACOLITE 20221114.0, negatives retained, no cloud layer, added daily | Corrected with evidence. All confirmed except the layer list: a flags layer and a processing log also exist. Daily additions hold for recent scenes only. |
| Replan input: ACOLITE processes Level-1C only from local bundles | Fixed. Confirmed, with a remote Zarr input and a whole-product download helper added. |
| Replan input: the aerosol estimate depends on the processed window | Corrected with evidence. Confirmed for the window. The developer advises one fixed estimate per lake window, not a user-set value. The size of the difference is unmeasured. |
| Raw-data question: does ACOLITE accept Level-2A? | Fixed. No. Finding F-29. |
| Raw-data question: can a reader clip Level-1C JPEG 2000 before download? | Accepted and deferred. The documentation conflicts. Carried into Phase C as a one-product probe. |
| Raw-data question: which raw sources exist outside AWS? | Fixed. The Copernicus service, with quotas, and a Google Cloud bucket of unstated level. The Planetary Computer has no Level-1C. |
| Phase A limit: the gap survey plan's route sentence | Fixed. |
| Phase A limit: the inventory selection block, the presentation, and practice P10 | Fixed. |
| Replan: nine new issues | Corrected with evidence. Ten. I-40 records the measured coverage gap from T2. |
| Replan: the archive-naming test grows to four archives | Fixed. `tests/test_presentation.py` names all four buckets. |

## Proposed next step

Phase C, first step: probe T4, validity per band and pixel class on the pilot lakes, with tolerances declared before any read.
It reads pixel windows from the USGS bucket, so it needs explicit owner authorization. It reuses the pilot manifest, the pixel-class code, and the harness.
This step does not start it.
