# Work plan

No dated milestones exist (assumption A19 in [assumptions.md](assumptions.md)). Steps run in order.
Each step follows the [three-party review workflow](development-workflow.md). A checked box means the work exists in this repository with evidence.

## Step 0: initialize, done 2026-09-09, review pending

- [x] Conventions, rules, skills, check workflow, CI.
- [x] Assumptions with provenance. Decision 0001. Draft contract. Best-practices claims with status.
- [x] Canonical inventory skeleton with seeded candidates and no populated claims.
- [x] Discovery plan with question, candidates, bounds, method, and acceptance.
- [ ] Owner, Codex, and Claude Code review of the initialization.

## Step 1: discovery

Acceptance is in [discovery-plan.md](discovery-plan.md).

- [ ] Access routes, processing workflows, compute platforms, and storage layouts inventoried with sourced claims.
- [ ] Best-practices claims rechecked against primary pages.
- [ ] Renderer written. HTML discovery view generated from the inventory.
- [ ] Discovery review written. Prototype candidates proposed, not selected.

## Step 2: selection

- [ ] Owner selects prototype candidates. Recorded in a new decision.

## Step 3: prototyping

- [ ] Public pilot manifest derived from a public water-body dataset by a checked-in script.
- [ ] Bounded prototypes of the selected candidates on the pilot set. Fixture tests, no network.
- [ ] Live probes with recorded bytes, requests, cost, and limitations. Results in `benchmarks/results/`.
- [ ] Quality-flag derivation prototyped and measured against the pilot set.
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
