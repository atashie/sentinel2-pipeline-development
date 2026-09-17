# Sentinel-2 ingestion options for water-quality modeling

**Prototyping is underway. Stages 1 to 4 have reviewed laptop measurements. AWS performance and scientific validation remain open. Workflow, platform, and layout remain open.**
The owner accepted the Stage 4 response on 2026-09-17. The [presentation](docs/s2-options.html) and inventory include the corrected findings.
Next: review the [documentation and presentation update](docs/reviews/2026-09-17-documentation-and-presentation.md) and the [wording pass over the page](docs/reviews/2026-09-17-presentation-wording-pass.md) with its [spelling follow-up](docs/reviews/2026-09-17-american-spelling.md). Stage 5 requires separate authorization.
The [work plan](docs/work-plan.md) tracks the broader assessment and remaining review gates.

**Start here:** the [assessment presentation](docs/s2-options.html) explains Discovery and the partial results from Stages 1 to 4.
It is written for engineering and business colleagues. Integration Specs and Tradeoffs & Issues remain placeholders.
Open the HTML locally with its `assets/discovery/` directory beside it. [Hosting](docs/vercel-hosting.md) is prepared, with no deployment recorded.

This repository assesses how to ingest Sentinel-2 surface reflectance from public AWS repositories into an
internal store that serves per-water-body pixel values to a water-quality modeling project. The company runs
on AWS. It serves thousands of standing water bodies in the United States today, down to 10 m ponds, and must
be able to scale globally.

The consumer is a model, not a person. So the store serves raw band values and quality flags, keeps every
pixel that a water-body mask covers, records when each scene became visible locally, and never contacts a
provider at query time. It serves no derived water-quality index. Modeling, validation against field data,
and the join with weather features are separate projects.

The deliverable is an assessment, not a production system. It registers the issues of ingesting and processing
Sentinel-2 from the AWS buckets and compares processing workflows, compute platforms, and storage layouts.
Non-AWS options are documented for context only. It prototypes the leading options on public water-body polygons. It
measures cost at 1,000 and 10,000 water bodies for 2017-onward and 2021-onward histories. It ends in technical
specifications for the engineering team, who build the system.

The [measurements](docs/measurements.md) hold survey and prototype evidence. The [public pilot](examples/README.md) defines the test polygons.
The [assumptions](docs/assumptions.md) and [decisions](docs/decisions/README.md) record scope and accepted choices.

## Quick start

Python 3.12.13 and `uv.lock` pin the environment.

```sh
uv sync --locked
uv run pytest
```

The tests check documentation links, the inventory schema, the survey logic, and the pilot manifest on fixtures. The tests contact nothing.

## Documents

| Read | For |
|---|---|
| [docs/assumptions.md](docs/assumptions.md) | Planning assumptions and where each came from |
| [docs/decisions/](docs/decisions/README.md) | Why something was decided, including the COG fallback clarification |
| [docs/work-plan.md](docs/work-plan.md) | How options are judged, and the ordered steps with what is open |
| [docs/s2-best-practices.md](docs/s2-best-practices.md) | Sentinel-2 facts and practices for per-water-body extraction, with claim status |
| [docs/data-contract.md](docs/data-contract.md) | Draft of what the store serves. Not selected |
| [docs/measurements.md](docs/measurements.md) | What was measured, and what the numbers do not show |
| [docs/gap-survey-plan.md](docs/gap-survey-plan.md) | Data gap survey: sites, collections, gap definitions, rerun steps |
| [docs/s2-options.html](docs/s2-options.html) | Discovery story, satellite map examples, and partial Prototyping results |
| [docs/vercel-hosting.md](docs/vercel-hosting.md) | Prepared Vercel configuration and deployment instructions |
| [docs/options-inventory.json](docs/options-inventory.json) | The canonical assessment dataset. [Format](docs/assessment-data-format.md), [check records](docs/assessment-checks/README.md) |
| [docs/reviews/](docs/reviews/README.md) | The current review cycle and the generated gap survey report |
| [docs/references/](docs/references/README.md) | Supplied reference documents and their provenance |
| [benchmarks/README.md](benchmarks/README.md) | Survey scripts, workloads, and how to rerun a measurement |
| [examples/README.md](examples/README.md) | The public pilot water-body manifest, its regions, and the format |
| [tools/README.md](tools/README.md) | Deterministic scripts that rebuild the inventory, HTML, and report |
| [CLAUDE.md](CLAUDE.md) | Conventions, workflow, and gotchas for AI coding agents. [AGENTS.md](AGENTS.md) points Codex here |

Code is MIT licensed. Upstream data keep their own licenses and attribution. Large artifacts do not belong
in git. This repository claims no production deployment and no integration with a fitted water-quality model.
