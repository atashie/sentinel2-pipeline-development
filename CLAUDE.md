# sentinel2-pipeline-development

Assessment of options for ingesting Sentinel-2 surface reflectance from public AWS repositories
into an internal store that serves per-water-body pixel values to a water-quality modeling project.
The consumer is a model, not a person. The deliverable is an assessment: prototypes, measurements,
cost estimates, and technical specifications for the engineering team. This repository does not
build the production system. `README.md` is the human overview. `docs/README.md` indexes every document.

## Development workflow

Current phase: discovery accepted on 2026-09-10. [Decision 0003](docs/decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md)
selects Earth Search and the 2021 scenario. The next step is the data gap survey in [docs/work-plan.md](docs/work-plan.md),
which precedes any substantial analysis. [Decision 0001](docs/decisions/0001-scope-and-sequence.md) records scope and sequence.
No access route, processing workflow, compute platform, or storage layout is selected.

Follow [docs/development-workflow.md](docs/development-workflow.md). Complete one authorized step, then pause for owner, Codex, and Claude Code review.
Do not start the next step or publish changes while that review remains pending.
Codex reads [AGENTS.md](AGENTS.md), which points here. Keep shared conventions in this file.

## Commands

```sh
uv sync --locked                          # pinned environment, Python 3.12.13
uv run pytest                             # documentation and inventory tests, no network
uv run ruff check . && uv run ruff format --check .
uv run python tools/collate_checks.py          # rebuild the inventory from check records, no network
uv run python tools/render_options.py          # regenerate docs/s2-options.html, no network
uv run python tools/collate_checks.py --check && uv run python tools/render_options.py --check
```

CI runs, in order: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`. Run `/check` before you finish a change.

No script in this repository contacts AWS yet. When one exists, it runs only to produce a measurement
that a document cites, and only when the user invokes it. Requester-pays buckets charge the reader.
Record bucket, region, and payer in every result.

## Layout

| Path | What it is |
|---|---|
| `docs/` | Assumptions, protocol, best practices, contract draft, discovery plan, work plan, decisions, reviews |
| `docs/options-inventory.json` | Canonical assessment dataset: issues, candidates, claims, sources, findings |
| `docs/assessment-checks/` | Research drafts and independent check records that bind claims |
| `docs/references/` | Supplied reference documents and their provenance |
| `benchmarks/` | Measurement scripts and `workloads.json`. `results/*.json` are evidence |
| `examples/` | Public water-body manifest format for prototypes. Never customer data |
| `tests/` | Documentation link check and inventory schema check. No network |
| `tools/` | `collate_checks.py` rebuilds the inventory from check records. `render_options.py` renders it to HTML |
| `data/` | Local downloads and stores. Ignored by git |
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
- Earth Search is the access route (assumption A13, decision 0003). Collection 1 COG assets first, the older
  collection's JPEG 2000 assets as fallback. Non-AWS and managed options are context, never compared for selection.
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

Each gotcha points to its canonical claim in [docs/s2-best-practices.md](docs/s2-best-practices.md) or its issue in the
inventory. Numbers live there, not here. Read the claim before relying on it.

- Bands have three native resolutions, and every water body is stored as three pixel classes per resolution
  (assumption A20). A 10 m pond has no interior pixel. Claim G3, practice P6.
- **Cross-tile mosaicking is a MAJOR CONCERN (issue I-30). The store never mosaics.** Tiles overlap and differ
  in their overlap. Every record carries its tile and a primary or overlap marker under assumption A22. Claim G11,
  practice P2, decisions 0002 and 0003.
- The radiometric offset arrives in different states per route and per item. Read the conversion from the
  asset's own metadata. Never hard-code it. Claim R1, practice P8, issue I-05.
- Acquisition date is not processing baseline. Collection 1 reprocessed the archive. Claims G7 and G8, issue I-08.
- The scale driver is expected to be distinct tile-dates read, not water-body count (assumption A17,
  unmeasured). Issue I-20.
- The scene classification is a land product with conditional cloud dilation. Store codes, not names.
  Claims Q1, Q4, and Q8, issue I-01.
- Reprocessed products replace originals at the source. Key values by tile, sensing time, baseline, and
  product. Claim R2, practice P9.
- The supplied PDF's summary table is truncated in its render. Do not cite the table. Cite the pages it cites.
