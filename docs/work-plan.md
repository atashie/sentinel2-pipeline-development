# Work plan

No dated milestones exist (assumption A19 in [assumptions.md](assumptions.md)). Steps run in order.
Each step follows the [three-party review workflow](development-workflow.md). A checked box means the work exists in this repository with evidence.

## Step 0: initialize, done 2026-09-09, review accepted

- [x] Conventions, rules, skills, check workflow, CI.
- [x] Assumptions with provenance. Decision 0001. Draft contract. Best-practices claims with status.
- [x] Canonical inventory skeleton with seeded candidates and no populated claims.
- [x] Discovery plan with question, candidates, bounds, method, and acceptance.
- [x] Owner, Codex, and Claude Code review of the initialization. [Codex review](reviews/2026-09-09-codex-initialization-review.md), accepted by the owner on 2026-09-09.

## Step 1: discovery, delivered 2026-09-10 and revised the same day, Codex review pending

Acceptance is in [discovery-plan.md](discovery-plan.md).

- [x] Access routes, processing workflows, compute platforms, and storage layouts inventoried with sourced claims. [Inventory](options-inventory.json), [HTML](s2-options.html).
- [x] Best-practices claims rechecked against primary pages. [Recheck record](assessment-checks/best-practices-recheck.json).
- [x] Renderer written. HTML discovery view generated from the inventory.
- [x] Discovery review written. Prototype candidates proposed, not selected. [Review](reviews/2026-09-10-discovery.md).
- [x] Owner feedback on 2026-09-10, recorded in [decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md) and the [response](reviews/2026-09-10-owner-feedback-response.md).
- [x] Issue register of ingestion and processing issues, each with evidence and a status.
- [x] Codex review of the revision. [Codex discovery review](reviews/2026-09-10-codex-discovery-review.md), answered in the [response](reviews/2026-09-10-codex-discovery-response.md).
- [x] Codex follow-up on the response. [Follow-up](reviews/2026-09-10-codex-discovery-follow-up.md), answered in the [second response](reviews/2026-09-10-codex-follow-up-response.md).
- [x] Owner acceptance of the discovery step on 2026-09-10, [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md).

## Step 2: selection

- [x] Source: AWS-hosted Sentinel-2, [decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md).
- [x] Extraction geometry: three pixel classes and a tile provenance marker, decision 0002.
- [x] History scenario: 2021 onward first, [decision 0003](decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md). The 2017 to 2020 tier is deferred.
- [x] Route: Earth Search, Collection 1 first with the older collection's JPEG 2000 assets as fallback, decision 0003.
- [x] Primary-tile rule: provisional, assumption A22, decision 0003. **Cross-tile mosaicking is a MAJOR CONCERN, issue I-30.**
- [ ] Owner selects the workflow, platform, and layout to prototype. Recorded in a new decision.

## Step 3a: data gap survey, before any substantial analysis

Required by decision 0003. Catalog metadata only. No imagery is read.

- [ ] Survey plan: pilot tiles, collections, months from 2021-01-01 to the present, and the quality assets to list per item.
- [ ] Survey script under `benchmarks/`, writing evidence JSON to `benchmarks/results/` with endpoints, counts, and limitations.
- [ ] Gaps documented in [measurements.md](measurements.md), including the 2022 gap the probe found.
- [ ] Fill policy for each gap decided by the owner and recorded in a new decision.

## Step 3: prototyping

- [ ] Public pilot manifest derived from a public water-body dataset by a checked-in script.
- [ ] Bounded prototypes of the selected candidates on the pilot set. Fixture tests, no network.
- [ ] Live probes with recorded bytes, requests, cost, and limitations. Results in `benchmarks/results/`.
- [ ] Quality-flag derivation prototyped and measured against the pilot set.
- [ ] **Cross-tile measurement: differences between tiles over the same pixels and dates, per band and quality layer, issue I-30.**
- [ ] Contract revised from evidence. Processing version introduced.

## Step 4: integration specifications

- [ ] Orchestrator-agnostic specification of units of work, inputs, outputs, idempotency, retry, backfill, and reprocessing.
- [ ] Storage layout, partitioning, revision handling, and query interface specified.
- [ ] Monitoring, accounting, and alert conditions specified.

## Step 5: tradeoffs and cost

- [ ] Cost curves for 1,000 and 10,000 water bodies, 2017-onward and 2021-onward, backfill and steady state.
- [ ] Data-quality risks per option with the evidence for each.
- [ ] Recommendation with the evidence gaps that remain.

## Step 6: presentation

- [ ] Four-phase HTML complete: discovery, prototyping, integration specs, tradeoffs.
- [ ] Engineering review with the platform team's architecture lead and engineering lead.

Production build and rollout belong to the engineering team, outside this repository.
