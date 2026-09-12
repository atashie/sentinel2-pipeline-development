# sentinel2-pipeline-development

Assessment of options for ingesting Sentinel-2 surface reflectance from public AWS repositories
into an internal store that serves per-water-body pixel values to a water-quality modeling project.
The consumer is a model, not a person. The deliverable is an assessment: prototypes, measurements,
cost estimates, and technical specifications for the engineering team. This repository does not
build the production system. `README.md` is the human overview and the document index.

## Current phase

Discovery and the gap surveys are complete. The presentation was revised and reviewed on 2026-09-11.
The [latest review](docs/reviews/2026-09-11-prototyping-handoff.md) records corrections, verification, and remaining questions.
The next session begins Phase 2, Prototyping, scoped jointly by the owner, Codex, and Claude Code.
Start with the handoff in [docs/work-plan.md](docs/work-plan.md).
No processing workflow, compute platform, or storage layout is selected. No workflow prototype has run.
[Decision 0004](docs/decisions/0004-cog-fallback-and-presentation-clarifications.md) consolidates the agreed COG fallback and presentation direction.
Earlier scope decisions remain active except where explicitly revised.

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
uv sync --locked                          # pinned environment, Python 3.12.13
uv run pytest                             # documentation, inventory, survey, and report tests, no network
uv run ruff check . && uv run ruff format --check .
uv run python tools/collate_checks.py          # rebuild the inventory from check records, no network
uv run python tools/render_options.py          # regenerate docs/s2-options.html, no network
uv run python tools/gap_report.py              # regenerate the gap survey report, no network
uv run python tools/collate_checks.py --check && uv run python tools/render_options.py --check && uv run python tools/gap_report.py --check
```

CI runs, in order: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`. Run `/check` before you finish a change.

Two scripts contact providers: `benchmarks/gap_survey.py` queries catalog metadata from the Earth Search API
and the Copernicus catalogs, and `benchmarks/fallback_survey.py` adds header-only requests on public GeoTIFF objects.
Neither reads a pixel. Such scripts run only to produce a measurement that a document cites, and only when the user
invokes them. Requester-pays buckets charge the reader. Record bucket or endpoint, region, and payer in every result.

The separate educational map builder, [tools/build_discovery_maps.py](tools/build_discovery_maps.py), reads pixels only with `--download` and explicit authorization.
The owner authorized one public image crop for the presentation on 2026-09-11. This does not authorize workflow prototypes or additional surveys.

## Layout

| Path | What it is |
|---|---|
| `docs/` | Assumptions, best practices, contract draft, work plan, gap survey plan, measurements, decisions, current reviews, Vercel configuration and hosting note |
| `docs/archive/` | Ignored by git. Superseded reviews and plans, kept locally until deleted. Nothing links to it |
| `docs/options-inventory.json` | Canonical assessment dataset: issues, candidates, claims, sources, probes, findings |
| `docs/assessment-checks/` | Research drafts and independent check records that bind claims. Evidence, not prose |
| `docs/references/` | Supplied reference documents and their provenance |
| `benchmarks/` | Survey scripts, `workloads.json`, and the survey sites. `results/*.json` are evidence |
| `examples/` | Public water-body manifest format for prototypes. Never customer data |
| `tests/` | Documentation link check, inventory schema check, survey and report fixture tests. No network |
| `tools/` | Inventory and report renderers, the Discovery presentation template, and its educational map builder. See [tools/README.md](tools/README.md) |
| `data/` | Local downloads, raw listings, and stores. Ignored by git |
| `src/` | Prototype code, once a prototype step is authorized. Does not exist yet |

## Conventions

- A claim about a data source, service, or tool carries one status: `documented` (cites a dated primary
  page), `measured` (cites a result JSON), or `unverified` (names the test needed).
- A planning assumption carries `sourced` or `unsourced`. The list is `docs/assumptions.md`.
  Do not restate an assumption elsewhere. Link to it.
- One fact has one home. Link to it. Do not copy it.
- Assessment facts live in `docs/options-inventory.json`. Follow [its format](docs/assessment-data-format.md).
- Keep unvalidated specifications null. Every populated claim needs primary evidence and an independent check.
- The assessment has four phases: discovery, prototyping, integration specs, and tradeoffs. Discovery compares
  access routes, processing workflows, compute platforms, and storage layouts. It does not rank vendors.
- Earth Search is the access route (assumption A13, decisions 0003 and 0004). Collection 1 GeoTIFF assets first, the older
  collection's GeoTIFF assets as fallback. Non-AWS and managed options are context, never compared for selection.
- The store serves raw band values and quality flags. It serves no derived water-quality index (assumption A1).
- Customer polygons never enter this repository. Prototypes use public water-body polygons (assumption A8).
- Specifications name no orchestrator (assumption A12). Describe work as idempotent units with declared inputs and outputs.
- AI-generated research, including the supplied PDF, is not independent evidence. Recheck its claims against
  primary pages before marking them `documented`.
- Refer to colleagues by role, never by name. Do not name customers or their current vendors. This repository can become public.
- Never edit `benchmarks/results/*.json` by hand. Rerun the script that wrote it.
- Timestamps carry a UTC offset. Dates are ISO 8601. No relative dates in documents.
- Documents use plain English. Descriptive sentences: 25 words maximum. Procedure steps: imperative,
  20 words maximum. No semicolons. No "should": write "must" or state a fact.
- Python: ruff, line length 100, rules `E F I B UP`. Use Python 3.12 for development and CI.
- Do not commit anything under `data/`. Large artifacts belong in linked storage.

## Gotchas

Each gotcha points to its canonical claim in [docs/s2-best-practices.md](docs/s2-best-practices.md), its issue in the
inventory, or its finding in [docs/measurements.md](docs/measurements.md). Numbers live there, not here.

- Bands have three native resolutions, and every water body is stored as three pixel classes per resolution
  (assumption A20). A 10 m pond has no interior pixel. Claim G3, practice P6.
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
  unmeasured). Issue I-20.
- The scene classification is a land product with conditional cloud dilation. Store codes, not names.
  Claims Q1, Q4, and Q8, issue I-01.
- Both collections can hold multiple products per acquisition. The older collection has more competing versions in the sample.
  Source retention is not guaranteed. Preserve local revisions. Claim R2, practice P9, issue I-16.
- Both Earth Search collections are Element 84's GeoTIFF conversions of the same ESA product, in two public buckets.
  The ESA-format copy on AWS is the JPEG 2000 bucket with the Sinergise readme, context only. Its registry entry is
  also Element 84's, and no page names the bucket owner. Neither GeoTIFF bucket is requester pays. Inventory claims
  `operator` and `source_dataset`, findings F-21 and F-22, probe PR-08.
- The supplied PDF's summary table is truncated in its render. Do not cite the table. Cite the pages it cites.
