# Sentinel-2 ingestion options for water-quality modeling

**Re-scoped on 2026-10-13, [decision 0008](docs/decisions/0008-acolite-aquatic-reflectance-first.md), and on 2026-10-14, [decision 0009](docs/decisions/0009-standalone-options-join-deferred.md). Two source options are compared, each used alone. ACOLITE only is the USGS aquatic reflectance product, for water pixels in the lower 48 states. Sen2Cor only is Earth Search Level-2A. The scene join is deferred. Stages 1 to 4 have reviewed laptop measurements on Level-2A files, now the reference series. Phase B probed the primary product's layout, coverage, and join with metadata, and read one authorized pixel crop. Phase C probe T4 measured pixel validity on the pilot lakes. Probe T5 compared the two options' values on the same pixels, and T6 replayed the access tests on the primary product. Workflow, platform, and layout remain open.**
The [replan record](docs/reviews/2026-10-13-acolite-first-replan.md) sets the phases and the tests. The [Phase A record](docs/reviews/2026-10-13-phase-a-rescope.md) restated the planning documents. The [Phase B record](docs/reviews/2026-10-13-phase-b-discovery-ii.md) adds check records, probes T1 to T3, and the Discovery rewrite. Both await owner review.
The owner accepted the Stage 4 response on 2026-09-17. The [presentation](docs/s2-options.html) and inventory include the corrected findings.
Related records include the [documentation update](docs/reviews/2026-09-17-documentation-and-presentation.md), [wording pass](docs/reviews/2026-09-17-presentation-wording-pass.md), and [spelling follow-up](docs/reviews/2026-09-17-american-spelling.md).
Further records cover the [sensor bands](docs/reviews/2026-09-17-sensor-band-comparison.md), [section 02 heading](docs/reviews/2026-09-18-access-problem-first.md), and [lazy-reader workload review](docs/reviews/2026-09-18-claude-lazy-reader-workload-review.md).
Phase C, Prototyping II, runs one authorized step at a time. The [T4 record](docs/reviews/2026-10-13-phase-c-t4-validity.md) awaits owner review. The [direction record](docs/reviews/2026-10-14-standalone-options-direction.md) of 2026-10-14 awaits review.
The [T5 and T6 record](docs/reviews/2026-10-14-phase-c-t5-t6.md) awaits review. The [cost analysis](docs/aws-cost-analysis.md) now estimates both options, with its own [record](docs/reviews/2026-10-14-phase-c-cost-options.md).
The [work plan](docs/work-plan.md) tracks the broader assessment and remaining review gates.
The authorized [larger-workload comparison](docs/reviews/2026-09-18-lazy-reader-workload-plan.md) now has separate, resumable preflight and extraction commands.
The [review response](docs/reviews/2026-09-18-lazy-reader-review-response.md) records implemented corrections and disagreements.
**Current ingest status:** twelve sleep-affected attempts were rerun, retaining two unaffected results. All fourteen comparisons completed with matching outputs and no sleep overlap. The [rerun record](docs/reviews/2026-09-21-sleep-rerun.md) owns results, resource measurements, and verification.

**Start here:** the [assessment presentation](docs/s2-options.html) explains Discovery, the partial results from Stages 1 to 4, and offline AWS cost estimates.
It is written for engineering and business colleagues. Integration Specs and Tradeoffs & Issues remain placeholders.
Discovery describes the three archives and the primary product. Prototyping still reports the Level-2A series until Phase C.
Open the HTML locally with its `assets/discovery/` directory beside it. [Hosting](docs/vercel-hosting.md) is prepared, with no deployment recorded.

This repository assesses how to ingest Sentinel-2 reflectance from public AWS repositories into an
internal store that serves per-water-body pixel values to a water-quality modeling project. Water pixels in the
lower 48 states come from the USGS ACOLITE aquatic reflectance product or, as the other option, ESA Level-2A surface
reflectance from Earth Search. Each option is used alone. The company runs on AWS. It serves thousands of standing water bodies in the
United States today, down to 10 m ponds. The initial scope is the lower 48 states. Expansion beyond the United
States needs a workflow redraft, and the infrastructure must still be able to scale.

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
| [docs/decisions/](docs/decisions/README.md) | Why something was decided, including the ACOLITE-first re-scope |
| [docs/work-plan.md](docs/work-plan.md) | How options are judged, and the ordered steps with what is open |
| [docs/s2-best-practices.md](docs/s2-best-practices.md) | Sentinel-2 facts and practices for per-water-body extraction, with claim status |
| [docs/data-contract.md](docs/data-contract.md) | Draft v2 of what the store serves from two source products. Not selected |
| [docs/measurements.md](docs/measurements.md) | What was measured, and what the numbers do not show |
| [docs/aws-cost-analysis.md](docs/aws-cost-analysis.md) | Estimated AWS costs per standalone option for national and sampled workloads |
| [docs/gap-survey-plan.md](docs/gap-survey-plan.md) | Data gap survey: sites, collections, gap definitions, rerun steps |
| [docs/s2-options.html](docs/s2-options.html) | Discovery story, satellite map examples, partial Prototyping results, and AWS cost estimates |
| [docs/vercel-hosting.md](docs/vercel-hosting.md) | Prepared Vercel configuration and deployment instructions |
| [docs/options-inventory.json](docs/options-inventory.json) | The canonical assessment dataset. [Format](docs/assessment-data-format.md), [check records](docs/assessment-checks/README.md) |
| [docs/sensor-bands.json](docs/sensor-bands.json) | Band tables and documented water-quality uses for six sensors, bound from checked records for the presentation |
| [docs/reviews/](docs/reviews/README.md) | The current review cycle and the generated gap survey report |
| [docs/references/](docs/references/README.md) | Supplied reference documents and their provenance |
| [benchmarks/README.md](benchmarks/README.md) | Survey scripts, workloads, and how to rerun a measurement |
| [examples/README.md](examples/README.md) | The public pilot water-body manifest, its regions, and the format |
| [tools/README.md](tools/README.md) | Deterministic scripts that rebuild the inventory, HTML, and report |
| [CLAUDE.md](CLAUDE.md) | Conventions, workflow, and gotchas for AI coding agents. [AGENTS.md](AGENTS.md) points Codex here |

Code is MIT licensed. Upstream data keep their own licenses and attribution. Large artifacts do not belong
in git. This repository claims no production deployment and no integration with a fitted water-quality model.
