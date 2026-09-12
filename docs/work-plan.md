# Work plan

No dated milestones exist (assumption A19 in [assumptions.md](assumptions.md)). Steps run in order under the workflow in [CLAUDE.md](../CLAUDE.md).
A checked box means the work exists in this repository with evidence.

## Next session: Phase 2, Prototyping

Discovery review and documentation reconciliation are recorded in the [handoff review](reviews/2026-09-11-prototyping-handoff.md).
Read that review, [measurements](measurements.md), and the [draft contract](data-contract.md) before selecting the first bounded comparison together.

- The public pilot polygons exist since 2026-09-11. Identify the input product used by the existing model.
- Choose the first methods, comparison cases, tolerances, and resource bounds with the owner, Codex, and Claude Code.
- Prioritize offset correctness and cross-tile differences alongside runtime, bytes, requests, memory, and output size.
- Carry unresolved fill policy, missing quality layers, Alaska scope, processing-version comparability, and record layout into those experiments.

The detailed prototype workflow will develop jointly. These questions do not require a complete infrastructure design before experiments begin.
No prototype or new provider read ran during this documentation review. Hosting the presentation is separate from prototype planning.

## How options are judged

An access route moves products to us. A processing workflow turns products into per-water-body records. A compute platform runs the workflow. A storage layout holds the records.
Two routes feeding one workflow test delivery. Two workflows on one route test processing. Every measurement says which it tests. The source and route are decided, with fallback format clarified in [decision 0004](decisions/0004-cog-fallback-and-presentation-clarifications.md). The other three dimensions are open.

| Criterion | What to record |
|---|---|
| Correctness | Tile grid and overlap handling, refinement status, offset handling, native-resolution reads, baseline tracking |
| Quality flags | Which cloud, shadow, glint, snow, and defect layers the option delivers or enables (assumption A2) |
| Raw pixel access | Whether raw per-pixel values can be served (assumption A1) |
| Completeness | Expected, present, and missing scenes per water body, and how the option accounts for them |
| Latency | Time from product publication to local availability (assumption A11) |
| Scaling | Behaviour as water bodies, distinct tiles, and history grow (assumption A17) |
| Cost | Compute, storage, requests, transfer, service fees, engineering effort (assumption A14) |
| Operability | Idempotency, retry, backfill, reprocessing, monitoring, orchestrator independence (assumption A12) |
| Global reach | Anything that limits use outside the United States (assumption A4) |
| Terms | License, attribution, retention, redistribution, commercial use |

Claims carry the statuses in [CLAUDE.md](../CLAUDE.md), plus `estimated` for a project inference that names the documented claims it rests on. [assessment-data-format.md](assessment-data-format.md) defines the binding.
Measurements report bytes transferred, requests made, pixels read, and output bytes as four numbers. They also report wall time, peak memory, publication-to-availability latency, expected and missing scenes per water body, and distinct tiles and tile-dates.
Workloads are in [../benchmarks/workloads.json](../benchmarks/workloads.json). Provider load rises gradually. Fault and load tests run against local fixtures or owned storage only.

Monthly cost uses measured rates. Prices stay null until measured or quoted from a dated page. Report backfill cost apart from steady state, and cost curves for 1,000 and 10,000 water bodies for both histories.

```
monthly_cost = compute_hours * compute_price + requests / 1000 * request_price
             + transfer_GB * transfer_price + retained_GB * storage_price
             + service_fees + engineering_hours * labor_rate
archive_GB(years) = bytes_per_water_body_scene * scenes_per_water_body_per_year
                  * water_bodies * years * revision_factor / 1e9
```

Out of scope: validation against field observations (A15), the join with weather features (A16), derived water-quality indices (A1).

## Step 0: initialize, done 2026-09-09, accepted

- [x] Conventions, rules, check workflow, CI. Assumptions with provenance. [Decision 0001](decisions/0001-scope-and-sequence.md). Draft contract. Best-practices claims with status. Inventory skeleton.
- [x] Codex review accepted by the owner on 2026-09-09. Archived.

## Step 1: discovery, done 2026-09-10, accepted

- [x] Access routes, processing workflows, compute platforms, and storage layouts inventoried with sourced, independently checked claims. [Inventory](options-inventory.json), [HTML](s2-options.html).
- [x] Best-practices claims rechecked against primary pages. [Recheck record](assessment-checks/best-practices-recheck.json).
- [x] Issue register of ingestion and processing issues, each with evidence and a status.
- [x] Owner feedback recorded in [decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md). Two Codex review cycles answered. Archived.
- [x] Owner acceptance on 2026-09-10, [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md).

## Step 2: selection

- [x] Source: AWS-hosted Sentinel-2, decision 0002.
- [x] Extraction geometry: three pixel classes and a tile provenance marker, decision 0002.
- [x] History scenario: 2021 onward first, decision 0003. The 2017 to 2020 tier is deferred.
- [x] Route: Earth Search, Collection 1 COGs first with older-collection COGs for backfill, decisions 0003 and 0004.
- [x] Primary-tile rule: provisional, assumption A22, decision 0003. **Cross-tile mosaicking is a MAJOR CONCERN, issue I-30.**
- [ ] Fill policy for each data gap and Alaska scope. Record the eventual choice in a new decision. Options are in the [gap survey review](reviews/2026-09-10-gap-survey.md) and the [report](reviews/2026-09-10-gap-survey-report.json).
- [ ] Agree the first bounded prototype comparison together. Workflow, platform, and layout choices develop from its evidence.

## Step 3a: data gap survey, delivered 2026-09-10, Codex review answered

Required by decision 0003. Catalog metadata and object headers only. No pixel is read.

- [x] Survey plan. [Plan](gap-survey-plan.md).
- [x] Survey script and evidence. [Script](../benchmarks/gap_survey.py), [result](../benchmarks/results/gap-survey.json).
- [x] Fallback survey at the asset level with a header-only existence check. [Script](../benchmarks/fallback_survey.py), [result](../benchmarks/results/fallback-survey.json).
- [x] Gaps documented in [measurements.md](measurements.md). Machine-readable [report](reviews/2026-09-10-gap-survey-report.json) generated by `tools/gap_report.py`.
- [x] [Codex review](reviews/2026-09-10-codex-gap-survey-review.md) answered in the [review record](reviews/2026-09-10-gap-survey.md). All five findings fixed or corrected with documentation.

## Step 3b: consolidate documentation, delivered 2026-09-10

The owner asked for a pared-down document set before the HTML view is rebuilt.

- [x] Superseded reviews and plans moved to `docs/archive/`, ignored by git, with an index there.
- [x] Workflow folded into [CLAUDE.md](../CLAUDE.md). Assessment criteria folded into this file. Document index folded into the root [README.md](../README.md).
- [x] Per-tile tables moved out of [measurements.md](measurements.md) into the report. Links repaired. Link test skips the archive.

## Step 3c: HTML view rebuilt on 2026-09-10, superseded

An inventory-driven page was rebuilt from scratch on 2026-09-10. The owner found it still too technical. The presentation below replaced it on 2026-09-11. The record of the earlier page is archived outside git.

## Discovery presentation, revised and reviewed 2026-09-11

The owner requested a narrative for engineering and business colleagues with limited geospatial background.
[Review record](reviews/2026-09-11-discovery-presentation.md).

- [x] Four tabs: Discovery, Prototyping, Integration Specs, and Tradeoffs & Issues. Only Discovery is populated.
- [x] Five sections explain the sensors, AWS archives, quality risks, processing effort, and real satellite examples.
- [x] Illustrations explain pixel size, shoreline classes, archive coverage, tile overlap, and a candidate stored record. Internal decision and issue IDs stay outside the presentation.
- [x] Paired Lake Lanier maps offer six band and index views, with source attribution and display limitations.
- [x] The owner supplied the direction on 2026-09-11, ten answers recorded in the [Claude Code review](reviews/2026-09-11-presentation-review.md).
- [x] Revision applying findings 1 to 8 of that review, delivered 2026-09-11. [Revision record](reviews/2026-09-11-presentation-revision.md).
- [x] Archive lineage and pull-cost comparison recorded as checked claims, a probe, and a finding, and the archive section rewritten, 2026-09-11. [Record](reviews/2026-09-11-archive-lineage.md).
- [x] Codex's independent archive comparison and history correction, then the archive section condensed with dispositions, 2026-09-11. [Record](reviews/2026-09-11-archive-section-condensed.md).
- [x] Plain-language pass over the whole page, 2026-09-11. [Record](reviews/2026-09-11-plain-language-pass.md).
- [x] Owner review round two applied: names, links, figure text, effort bars with technical detail, one row per pixel, 2026-09-11. [Record](reviews/2026-09-11-owner-review-round-two.md).
- [x] Codex reviewed the latest page and reconciled active documentation, 2026-09-11. [Handoff](reviews/2026-09-11-prototyping-handoff.md).
- [ ] Owner review of these corrections. Workflow selection and later phases remain open.

## Phase 2: Prototyping

- [x] Public pilot manifest derived from the USGS National Hydrography Dataset by [a checked-in script](../tools/build_pilot_manifest.py), 2026-09-11. [Manifest](../examples/water-bodies-public-pilot.geojson), [record](reviews/2026-09-11-pilot-manifest.md).
- [ ] Rerun the gap survey with `--manifest`, then the fallback survey and the report. The owner invokes it.
- [ ] Bounded prototypes of the selected candidates on the pilot set. Fixture tests, no network.
- [ ] Live probes with recorded bytes, requests, cost, and limitations. Results in `benchmarks/results/`.
- [ ] Offset pixel check, issue I-05. Read one 60 m band window from a GeoTIFF and from its JPEG 2000 alternate. Do it for a flag-true and a flag-false 04.00 item.
- [ ] Recheck of the 05.10 release note against claim R5, for the 05.09 products of 2023.
- [ ] Quality-flag derivation prototyped and measured against the pilot set.
- [ ] **Cross-tile measurement: differences between tiles over the same pixels and dates, per band and quality layer, issue I-30.**
- [ ] Contract revised from evidence. Processing version introduced.

## Phase 3: Integration Specs

- [ ] Orchestrator-agnostic specification of units of work, inputs, outputs, idempotency, retry, backfill, and reprocessing.
- [ ] Storage layout, partitioning, revision handling, and query interface specified.
- [ ] Monitoring, accounting, and alert conditions specified.

## Phase 4: Tradeoffs & Issues

- [ ] Cost curves for 1,000 and 10,000 water bodies, 2017-onward and 2021-onward, backfill and steady state.
- [ ] Data-quality risks per option with the evidence for each.
- [ ] Recommendation with the evidence gaps that remain.

## Final presentation

- [ ] Four-phase HTML complete: discovery, prototyping, integration specs, tradeoffs.
- [ ] Engineering review with the platform team's architecture lead and engineering lead.

Production build and rollout belong to the engineering team, outside this repository.
