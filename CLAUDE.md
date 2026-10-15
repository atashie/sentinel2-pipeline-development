# sentinel2-pipeline-development

Assessment of options for ingesting Sentinel-2 surface reflectance from public AWS repositories
into an internal store that serves per-water-body pixel values to a water-quality modeling project.
The consumer is a model, not a person. The deliverable is an assessment: prototypes, measurements,
cost estimates, and technical specifications for the engineering team. This repository does not
build the production system. `README.md` is the human overview and the document index.

## Current phase

The owner re-scoped the assessment on 2026-10-13, [decision 0008](docs/decisions/0008-acolite-aquatic-reflectance-first.md).
On 2026-10-14 the owner made the two sources standalone options, [decision 0009](docs/decisions/0009-standalone-options-join-deferred.md): ACOLITE only or Sen2Cor only.
Neither fills or flags the other, and the scene join is deferred. ACOLITE stays the initial primary source, assumption A52.
The [replan record](docs/reviews/2026-10-13-acolite-first-replan.md) owns the owner's directions, the tests T1 to T9, and the phases A to F.
Phase A restated the planning documents on 2026-10-13. Its [record](docs/reviews/2026-10-13-phase-a-rescope.md) awaits owner review.
Phase B, Discovery II, ran on 2026-10-13 under owner authorization. Its [record](docs/reviews/2026-10-13-phase-b-discovery-ii.md) awaits review.
Phase B bound the primary product's documented facts and ran metadata probes T1 to T3, measurement findings 26 to 28. One authorized crop is finding 29.
The owner authorized Phase C step 1, probe T4, on 2026-10-13. It measured pixel validity on the pilot lakes, findings 30 to 33. Its [record](docs/reviews/2026-10-13-phase-c-t4-validity.md) awaits review.
On 2026-10-14 the owner decided that shoreline and near-land values stay with the primary product, issue I-35. The [direction record](docs/reviews/2026-10-14-standalone-options-direction.md) awaits review.
The owner authorized probes T5 and T6 on 2026-10-14. T5, findings 34 and 35, and T6, findings 36 and 37, ran that day. Their [record](docs/reviews/2026-10-14-phase-c-t5-t6.md) awaits review.
The same day the cost model was re-parameterized per option from T1, T2, and T6. Its [record](docs/reviews/2026-10-14-phase-c-cost-options.md) awaits review.
The workload supervisor needs 5 GiB of free memory to start a worker. Each later Phase C step needs owner authorization.
Discovery and the gap surveys for the Level-2A route are complete. Prototyping has laptop measurements for Stages 1 to 4 on Level-2A files, the reference series.
Claude Code [reviewed Stage 4](docs/reviews/2026-09-16-claude-stage-4-full-run-review.md) and verified its extraction evidence.
The owner accepted the [response](docs/reviews/2026-09-16-codex-stage-4-review-response.md) on 2026-09-17. It corrects interpretation and future selection.
The measured results remain frozen. Ambiguous primary-tile roles still require an owner decision.
Start with [docs/work-plan.md](docs/work-plan.md). The inventory and the Discovery tab describe the primary product. The Prototyping tab still describes the Level-2A series until Phase C.
No processing workflow, compute platform, or storage layout is selected. Measurements remain on the owner's laptop under assumption A25.
The owner, Codex, and Claude Code develop each authorized step together under the workflow below.

## Workflow

The owner, Codex, and Claude Code review every step. Complete one authorized step, then stop.

1. Read this file, the applicable rules, the latest review, and the relevant decisions. Preserve other contributors' changes.
2. State the step, its acceptance checks, and what is deferred.
3. Implement it with tests and documentation. Run `/check`.
4. Write a dated record under `docs/reviews/`: what changed, evidence, limits, dispositions of prior findings
   (`fixed`, `accepted and deferred`, `corrected with evidence`), and the proposed next step without starting it.
5. Stop for review. Silence, passing tests, and an AI review are not owner approval.
   Never commit, push, publish, or start the next step without the owner's explicit authorization.

Research uses a research agent and a separate checking agent per claim. Only confirmed or corrected claims
populate the inventory. Scripts that contact a provider run only when the user invokes them.
Codex reads [AGENTS.md](AGENTS.md), which points here. Keep shared conventions in this file.

## Commands

```sh
uv sync --locked                          # pinned environment, Python 3.12.13, with the prototype group
uv run pytest                             # documentation, inventory, survey, and report tests, no network
uv run ruff check . && uv run ruff format --check .
uv run python tools/collate_checks.py          # rebuild the inventory from check records, no network
uv run python tools/collate_sensor_bands.py    # rebuild the sensor band dataset from its check records, no network
uv run python tools/render_options.py          # regenerate docs/s2-options.html, no network
uv run python tools/gap_report.py              # regenerate the gap survey report, no network
uv run python tools/build_pilot_manifest.py    # rebuild the pilot manifest from the saved run, no network
uv run python benchmarks/raw_access.py --dry-run   # print the stage 1 plan, no network
uv run python benchmarks/lake_extraction.py --dry-run   # print the stage 2 plan, no network
uv run python benchmarks/tile_extraction.py --dry-run   # print the stage 3 plan, no network
uv run python benchmarks/cross_tile_extraction.py --dry-run   # print the stage 4 workload, no network
uv run python benchmarks/lazy_reader_workloads.py            # print the larger-workload plan, no network
uv run python benchmarks/aqr_validity.py --dry-run   # print the probe T4 plan and its declared rules, no network
uv run python benchmarks/aqr_pairs.py --dry-run      # print the probe T5 plan and its declared rules, no network
uv run python benchmarks/aqr_workloads.py            # print the probe T6 plan, no network
uv run python tools/collate_checks.py --check && uv run python tools/collate_sensor_bands.py --check && uv run python tools/render_options.py --check && uv run python tools/gap_report.py --check
python3 ~/github/cc-skills/html-review-comments/scripts/inject.py tools/s2-options.template.html --config "$(cat tools/review-layer.json)" --check   # review-comment layer, no network
```

CI runs, in order: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`. Run `/check` before you finish a change.

Two scripts contact providers: `benchmarks/gap_survey.py` queries catalog metadata from the Earth Search API
and the Copernicus catalogs, and `benchmarks/fallback_survey.py` adds header-only requests on public GeoTIFF objects.
Neither reads a pixel. Such scripts run only to produce a measurement that a document cites, and only when the user
invokes them. Requester-pays buckets charge the reader. Record bucket or endpoint, region, and payer in every result.
`tools/build_pilot_manifest.py --fetch` contacts the USGS hydrography service for polygons only, and runs only when the owner asks.
`benchmarks/aqr_validity.py` reads pilot-lake windows from the USGS aquatic reflectance bucket and Level-2A scene classification windows. It runs only when the user invokes it.
`benchmarks/aqr_pairs.py` reads the same windows from the USGS bucket and the paired Collection 1 bands.
`benchmarks/aqr_workloads.py` replays stages 2 to 4 and readers B1 and B3 on the USGS bucket. Each runs only when the user invokes it.
`benchmarks/raw_access.py` and `benchmarks/copy_difference.py` read pixels from both public GeoTIFF buckets. `benchmarks/lake_extraction.py` reads lake windows from the Collection 1 bucket. `benchmarks/tile_extraction.py` reads every lake of a tile, windowed or whole. They run only when the user invokes them. `--dry-run` contacts nothing. `--reuse DIR` still queries the catalog, then repeats only what a saved pass did not measure. `--resummarize RESULT` recomputes a summary offline.

`benchmarks/cross_tile_extraction.py` separates metadata selection from imagery extraction.
See its [implementation record](docs/reviews/2026-09-16-stage-4-implementation.md) for modes, review gates, resource limits, and proposed commands.

`benchmarks/lazy_reader_workloads.py --execute RUN_DIR` prepares both larger cohorts and stops after printing the preflight.
It invokes `tools/build_workload_manifests.py` for public boundaries, then queries catalogs and source headers.
`--extract RUN_DIR` reads pixels for configurations whose workers have never launched. Both commands resume the same owned directory.
The owner authorized the full comparison on 2026-09-18. Its [review response](docs/reviews/2026-09-18-lazy-reader-review-response.md) records corrections and current commands.
Memory limits and all fourteen configurations remain unchanged. The owner authorized recording geometry non-convergence and continuing the experiment.
The [continuation record](docs/reviews/2026-09-18-geometry-diagnostic-resume.md) owns the audited source-supersession procedure.
The [original execution record](docs/reviews/2026-09-19-larger-workload-execution.md) records three complete workers, eleven failures, and sleep-related timing limits.
On 2026-09-21, the owner authorized replacing the twelve sleep-affected attempts and retaining the two unaffected observations.
The replacements completed. All fourteen comparisons have matching outputs and no sleep overlap. No worker exceeded the memory limits.
The [rerun record](docs/reviews/2026-09-21-sleep-rerun.md) owns results, resource measurements, the recovered startup pause, provenance, and verification.
The [review response](docs/reviews/2026-09-22-sleep-rerun-review-response.md) qualifies timing comparisons and carries consistent component boundaries into the next experiment's design.
`tools/rerun_sleep_workloads.py --extract RUN_DIR` runs replacements under verified macOS sleep prevention.
`--execute RUN_DIR --accept-source-change REASON` archives source-dependent preparation before rebuilding it. Any extraction launch forbids source supersession.

The separate educational map builder, [tools/build_discovery_maps.py](tools/build_discovery_maps.py), reads pixels only with `--download` and explicit authorization.
The owner authorized one public image crop for the presentation on 2026-09-11. This does not authorize workflow prototypes or additional surveys.

## Layout

| Path | What it is |
|---|---|
| `docs/` | Assumptions, best practices, contract draft, work plan, gap survey plan, measurements, decisions, current reviews, the sensor band dataset, Vercel configuration and hosting note |
| `docs/archive/` | Ignored by git. Superseded reviews and plans, kept locally until deleted. Nothing links to it |
| `docs/options-inventory.json` | Canonical assessment dataset: issues, candidates, claims, sources, probes, findings |
| `docs/assessment-checks/` | Research drafts and independent check records that bind claims. Evidence, not prose |
| `docs/references/` | Supplied reference documents and their provenance |
| `benchmarks/` | Survey and prototype measurement scripts, `workloads.json`, and the survey sites. `results/*.json` are evidence |
| `examples/` | The public pilot water-body manifest, its region configuration, and the format. Never customer data |
| `tests/` | Documentation link check, inventory schema check, survey, report, manifest, harness, and prototype fixture tests. No network |
| `tools/` | Inventory and report renderers, the Discovery presentation template, its map builder, and the pilot manifest builder. See [tools/README.md](tools/README.md) |
| `data/` | Local downloads, raw listings, and stores. Ignored by git |
| `src/` | Prototype code. `s2proto/harness.py` is the shared measurement harness. `s2proto/masks.py` computes the pixel classes. Not production code |

## Conventions

- A claim about a data source, service, or tool carries one status: `documented` (cites a dated primary
  page), `measured` (cites a result JSON), or `unverified` (names the test needed).
- A planning assumption carries `sourced` or `unsourced`. The list is `docs/assumptions.md`.
  Do not restate an assumption elsewhere. Link to it.
- One fact has one home. Link to it. Do not copy it.
- Assessment facts live in `docs/options-inventory.json`. Follow [its format](docs/assessment-data-format.md).
  Sensor band facts for the presentation live in `docs/sensor-bands.json`, bound from research and check records the same way.
- Keep unvalidated specifications null. Every populated claim needs primary evidence and an independent check.
- The assessment has four phases: discovery, prototyping, integration specs, and tradeoffs. Discovery compares
  access routes, processing workflows, compute platforms, and storage layouts. It does not rank vendors.
- Two source options are compared, each used alone (assumption A13, decision 0009). ACOLITE only is the USGS ACOLITE aquatic reflectance product,
  the primary product, for water pixels in the lower 48 states. Phase B documented or measured its metadata facts on 2026-10-13. Probe T4 measured pixel validity on the pilot lakes, findings 30 to 33.
  ACOLITE is treated as designed for water and is the initial primary source. Form no view on whether ACOLITE or Sen2Cor performs better until the company's own experiments (assumption A52).
  Sen2Cor only is Earth Search Level-2A: Collection 1 GeoTIFF assets first, the older collection's GeoTIFF assets as fallback (decision 0004).
  Neither option fills or flags the other. Do not design a scene join until evidence proves the model needs one. Non-AWS and managed options are context, never compared for selection.
- The store serves raw band values and quality flags. It serves no derived water-quality index (assumption A1).
- Customer polygons never enter this repository. Prototypes use public water-body polygons (assumption A8).
- Specifications name no orchestrator (assumption A12). Describe work as idempotent units with declared inputs and outputs.
- AI-generated research, including the supplied PDF, is not independent evidence. Recheck its claims against
  primary pages before marking them `documented`.
- Refer to colleagues by role, never by name. Do not name customers or their current vendors. This repository can become public.
- Never edit `benchmarks/results/*.json` by hand. Rerun the script that wrote it.
- Never edit the review-comment block in `tools/s2-options.template.html` by hand. Rerun `inject.py` with `tools/review-layer.json`, then regenerate the page.
- Timestamps carry a UTC offset. Dates are ISO 8601. No relative dates in documents.
- Documents use plain English and American spelling. Descriptive sentences: 25 words maximum. Procedure steps:
  imperative, 20 words maximum. No semicolons. No "should": write "must" or state a fact. Quoted source text stays verbatim.
- Python: ruff, line length 100, rules `E F I B UP`. Use Python 3.12 for development and CI.
- Do not commit anything under `data/`. Large artifacts belong in linked storage.

## Gotchas

Each gotcha points to its canonical claim in [docs/s2-best-practices.md](docs/s2-best-practices.md), its issue in the
inventory, or its finding in [docs/measurements.md](docs/measurements.md). Numbers live there, not here.

- Measurement findings 1 to 25 and the gotchas below describe Level-2A files from Earth Search, the reference series of
  assumption A50. Findings 26 to 29 describe the primary product's metadata and one crop. Findings 30 to 33 describe its pixels.
  Findings 34 and 35 compare the two options' values. Findings 36 and 37 describe access on the primary product. Decision 0008.
- Inside the primary product's scene, every pilot-lake pixel holds a value in every band and class. No-data marks pixels ACOLITE
  flags out of scene. NDWI is (B03 - B8A) / (B03 + B8A) times 10,000. Findings 30 and 32.
- Each primary product is a standalone observation. The bucket can hold two products of one pass on one tile, one per datastrip. Keep both, never the latest only. Finding 30, decision 0009.
- GDAL reports scale 1 and offset 0 for the primary product, its defaults. USGS documents a factor of 10,000. In every pixel probe T4
  read, the flags layer holds the ACOLITE flag integer times 10,000, and land pixels carry values with flags. Findings 26, 29, and 30.
- USGS documents ACOLITE 20221114.0, but the probed settings files carry the keys of release 20250402.0. Read the processor
  version per scene, never from the documentation. Finding 26, issue I-34.
- The primary product holds about half of Earth Search's acquisitions, mostly from original Level-1C baselines. Under ACOLITE only, the rest stay missing.
  A deferred Level-2A join by tile, platform, and sensing start would reach the same baseline for 51 percent. Its key identifies a pass, not one item.
  The Level-1C datastrip identified one Collection 1 item for each of 59 products, finding 34. Probes use it for pairing only. Decision 0009 still defers any join.
  Findings 27, 28, and 30, issues I-32 and I-40.
- Level-2A bands have three native resolutions, and the primary product has one 20 m grid. Every water body is stored as
  three pixel classes per source grid (assumption A20). A 10 m pond has no interior pixel. Claim G3, practice P6.
- **Cross-tile mosaicking is a MAJOR CONCERN (issue I-30). The store never mosaics.** Tiles overlap and differ
  in their overlap. Every record carries its tile and a primary or overlap marker under assumption A22. Claim G11,
  practice P2, decisions 0002 and 0003. Seven of twenty survey sites lie in two to four tiles, measurement finding 8.
- Collection 1 on Earth Search is nearly empty from January to November 2022 everywhere, and holds 05.09 originals
  for December 2022 to December 2023. The older collection's GeoTIFFs cover 2022. One Alaska tile is on no
  collection for 52 months. Measurement findings 1 to 3 and 10, issue I-08.
- The radiometric offset arrives in different states per route and per item. The provider's per-item flag and the
  asset's declared offset disagree for most 04.00 items. Read nothing from metadata alone. Claim R1, practice P8,
  issue I-05, measurement finding 5.
- Acquisition date is not processing baseline. A date and platform key does not identify one product. Claims G7
  and G8, issue I-08, measurement finding 7.
- The scale driver is expected to be distinct tile-dates read, not water-body count (assumption A17,
  partially tested on the pilot). Issue I-20 and measurement findings 19, 24, and 25.
- The scene classification is a land product with conditional cloud dilation. Store codes, not names.
  Claims Q1, Q4, and Q8, issue I-01.
- Both collections can hold multiple products per acquisition. The older collection has more competing versions in the sample.
  Source retention is not guaranteed. Preserve local revisions. Claim R2, practice P9, issue I-16.
- One tile and datatake can contain overlapping datastrips. Item identity distinguishes them. Catalog footprints also need pixel-level validity checks. Measurement finding 23.
- Both Earth Search collections are Element 84's GeoTIFF conversions of the same ESA product, in two public buckets.
  The ESA-format copy on AWS is the JPEG 2000 bucket with the Sinergise readme, context only. Its registry entry is
  also Element 84's, and no page names the bucket owner. Neither GeoTIFF bucket is requester pays. Inventory claims
  `operator` and `source_dataset`, findings F-21 and F-22, probe PR-08.
- On one product and three bands, the older copy's integer is Collection 1's minus 1,000, clamped to 1, on every pixel checked. The offset is already applied and reflectance at or below zero is lost. Its catalog still declares the offset. Its cloud and snow assets are JPEG 2000 links outside the GeoTIFF benchmark, and its aerosol and water-vapor grids differ. Measurement findings 14 and 15.
- On the primary product, small lakes take the same 15 requests and about 40 percent of Level-2A's bytes. The saving is in the red and near-infrared
  files. A 2,048-pixel lazy chunk covers four times the ground at 20 m. B1 and B3 take more CPU per requested megabyte. Findings 36 and 37.
- Small-lake reads usually fit in one internal block per file. 24 of 25 in the pilot took 15 requests and 3 to 4 MB for five files, whatever the pixel count. One lake across a block boundary cost 20 requests. Requests are HTTP requests, not blocks. GDAL's all-touched rasterization and the coverage threshold select differently on a few hundred pixels out of millions. Pixel classes come from exact areas, `src/s2proto/masks.py`, and every distance is measured to the real boundary, never to a tile edge. Measurement findings 16 and 17.
- Catalog grid codes are not normalized. The same Alaska tile appears as `MGRS-05VMG` and `MGRS-5VMG`. Measurement finding 18. `benchmarks/tile_extraction.py` normalizes them.
- Reading every lake of a tile in one process cuts the requests by more than half against one process per lake. A block one lake loaded serves the next, and reopening a file per lake forfeits the block cache. A whole-tile read costs many times the windowed bytes at the pilot's density. The lazy stack's per-lake computes on a shared graph re-read whole chunks. `rasterio.Env` takes `GDAL_CACHEMAX` in bytes, and the environment variable takes megabytes. The stage 3 run of 2026-09-15 held a 512-byte cache and was rerun. Measurement findings 19 to 22.
- The supplied PDF's summary table is truncated in its render. Do not cite the table. Cite the pages it cites.
