# sentinel2-pipeline-development

Assessment of options for ingesting Sentinel-2 surface reflectance from public AWS repositories
into an internal store that serves per-water-body pixel values to a water-quality modeling project.
The consumer is a model, not a person. The deliverable is an assessment: prototypes, measurements,
cost estimates, and technical specifications for the engineering team. This repository does not
build the production system. `README.md` is the human overview. `docs/README.md` indexes every document.

## Development workflow

Current phase: initialized on 2026-09-09, awaiting owner review. The next step is discovery, specified in
[docs/discovery-plan.md](docs/discovery-plan.md). [Decision 0001](docs/decisions/0001-scope-and-sequence.md) records scope and sequence.
No access route, processing workflow, compute platform, or storage layout is selected.

Follow [docs/development-workflow.md](docs/development-workflow.md). Complete one authorized step, then pause for owner, Codex, and Claude Code review.
Do not start the next step or publish changes while that review remains pending.
Codex reads [AGENTS.md](AGENTS.md), which points here. Keep shared conventions in this file.

## Commands

```sh
uv sync --locked                          # pinned environment, Python 3.12.13
uv run pytest                             # documentation and inventory tests, no network
uv run ruff check . && uv run ruff format --check .
```

CI runs, in order: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`. Run `/check` before you finish a change.

No script in this repository contacts AWS yet. When one exists, it runs only to produce a measurement
that a document cites, and only when the user invokes it. Requester-pays buckets charge the reader.
Record bucket, region, and payer in every result.

## Layout

| Path | What it is |
|---|---|
| `docs/` | Assumptions, protocol, best practices, contract draft, discovery plan, work plan, decisions, reviews |
| `docs/options-inventory.json` | Canonical assessment dataset: candidates, claims, sources, findings |
| `docs/assessment-checks/` | Research drafts and independent check records that bind claims |
| `docs/references/` | Supplied reference documents and their provenance |
| `benchmarks/` | Measurement scripts and `workloads.json`. `results/*.json` are evidence |
| `examples/` | Public water-body manifest format for prototypes. Never customer data |
| `tests/` | Documentation link check and inventory schema check. No network |
| `tools/` | Assessment renderer, once discovery produces data |
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
- Sentinel-2 via AWS is the preferred route (assumption A13). Alternatives are assessed on the same criteria.
  Preference is not selection.
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

- Sentinel-2 bands have three native resolutions: 10 m, 20 m, and 60 m. A 10 m pond covers at most one
  10 m pixel and a fraction of a 20 m pixel. Report pixel counts per resolution for every water body.
  Never resample without recording the policy. See [docs/s2-best-practices.md](docs/s2-best-practices.md).
- Tiles overlap, and a water body can sit in two tiles or two UTM zones. Choose one tile per water body
  before counting scenes, or count the duplicates. Practice P2 in the best-practices document.
- Level-2A reflectance carries an additive offset from a later processing baseline onward. Read the offset
  and quantification value from product metadata. Never hard-code them. Claim R1 in the best-practices document.
- Geometric refinement changed in 2021. The 2017 and 2021 history scenarios differ in registration quality,
  not only in length. Claims G5 to G9 in the best-practices document.
- The scale driver is distinct tile-dates read, not water-body count (assumption A17, unmeasured).
  A benchmark that reads one tile says nothing about ten thousand water bodies.
- The scene classification layer is a land product. Treat its water, shadow, and cloud classes over small
  ponds as unverified until measured. Claim Q4 in the best-practices document.
- Reprocessed products exist beside originals. Key values by tile, sensing time, and processing baseline,
  never by product name alone. Practice P9 in the best-practices document.
- The supplied PDF's summary table is truncated in its render. Do not cite the table. Cite the pages it cites.
