# Sentinel-2 ingestion options for water-quality modeling

**Discovery review completed on 2026-09-11. Next session: Phase 2, Prototyping. Workflow, platform, and layout remain open.**
Read the [review and handoff](docs/reviews/2026-09-11-prototyping-handoff.md), then the [work plan](docs/work-plan.md).
[Decision 0002](docs/decisions/0002-aws-source-pixel-classes-tile-provenance.md) fixes three pixel classes per water body and a tile provenance marker. [Decision 0003](docs/decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md) selects Earth Search as the route and the 2021 scenario first. Workflow, platform, and layout remain open. **Cross-tile mosaicking is a MAJOR CONCERN under investigation, issue I-30.**

**Start here:** [Discovery presentation](docs/s2-options.html) explains the data, AWS archives, quality risks, processing work, and real map examples.
It is written for engineering and business colleagues. Prototyping, Integration Specs, and Tradeoffs & Issues are placeholders.
Vercel hosting is prepared but no deployment is recorded, see [docs/vercel-hosting.md](docs/vercel-hosting.md). Locally, open the HTML from disk with its `assets/discovery/` directory beside it.
The gap surveys are in [docs/measurements.md](docs/measurements.md) and the generated [report](docs/reviews/2026-09-10-gap-survey-report.json).

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

**Status:** two measurements, the [data gap survey and its fallback survey](docs/measurements.md). No prototype code. No selected workflow, platform, or layout. [docs/work-plan.md](docs/work-plan.md) lists the
steps. [docs/assumptions.md](docs/assumptions.md) lists what is assumed and where each assumption came from.

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
| [docs/s2-options.html](docs/s2-options.html) | The colleague-facing Discovery story, diagrams, and interactive satellite map examples |
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
