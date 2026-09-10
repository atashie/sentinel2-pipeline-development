# Sentinel-2 ingestion options for water-quality modeling

**Current phase on 2026-09-09: repository initialized. Discovery is the next step and awaits owner review.**
[Decision 0001](docs/decisions/0001-scope-and-sequence.md) records scope and sequence. Nothing is selected.

This repository assesses how to ingest Sentinel-2 surface reflectance from public AWS repositories into an
internal store that serves per-water-body pixel values to a water-quality modeling project. The company runs
on AWS. It serves thousands of standing water bodies in the United States today, down to 10 m ponds, and must
be able to scale globally.

The consumer is a model, not a person. So the store serves raw band values and quality flags, keeps every
pixel that a water-body mask covers, records when each scene became visible locally, and never contacts a
provider at query time. It serves no derived water-quality index. Modeling, validation against field data,
and the join with weather features are separate projects.

The deliverable is an assessment, not a production system. It compares access routes, processing workflows,
compute platforms, and storage layouts. It prototypes the leading options on public water-body polygons. It
measures cost at 1,000 and 10,000 water bodies for 2017-onward and 2021-onward histories. It ends in technical
specifications for the engineering team, who build the system.

**Status:** no code, no measurements, no selected option. [docs/work-plan.md](docs/work-plan.md) lists the
steps. [docs/assumptions.md](docs/assumptions.md) lists what is assumed and where each assumption came from.

## Quick start

Python 3.12.13 and `uv.lock` pin the environment.

```sh
uv sync --locked
uv run pytest
```

The tests check documentation links and the inventory schema. Nothing contacts AWS.

## Documents

| Read | For |
|---|---|
| [docs/README.md](docs/README.md) | Index of every document |
| [docs/assumptions.md](docs/assumptions.md) | Planning assumptions and where each came from |
| [docs/assessment-protocol.md](docs/assessment-protocol.md) | How options are assessed and what gets published |
| [docs/s2-best-practices.md](docs/s2-best-practices.md) | Sentinel-2 facts and practices for per-water-body extraction, with claim status |
| [docs/discovery-plan.md](docs/discovery-plan.md) | The next step: question, candidates, bounds, subagent plan, acceptance |
| [docs/data-contract.md](docs/data-contract.md) | Draft of what the store serves. Not selected |
| [docs/work-plan.md](docs/work-plan.md) | Ordered steps with acceptance checks. No dates |
| [docs/decisions/](docs/decisions/README.md) | Why something was decided |
| [docs/reviews/](docs/reviews/README.md) | Dated reviews of this repository |
| [docs/development-workflow.md](docs/development-workflow.md) | One-step implementation and owner, Codex, Claude Code review |
| [CLAUDE.md](CLAUDE.md) | Conventions for AI coding agents that work here |

Code is MIT licensed. Upstream data keep their own licenses and attribution. Large artifacts do not belong
in git. This repository claims no production deployment and no integration with a fitted water-quality model.
