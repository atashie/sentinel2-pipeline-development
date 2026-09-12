# 0001. Scope and sequence, 2026-09-09

Status: active.

## Context

The owner started this repository on 2026-09-09 to assess options for ingesting Sentinel-2 data from public AWS repositories for water-quality modeling.
Before initialization, the implementer reviewed the weather feature repository as the style guide and read the supplied geolocation report.
The implementer then asked fourteen clarifying questions. The owner's answers on 2026-09-09 are the authority for every `sourced` row in [assumptions.md](../assumptions.md).

## Decision

- Scope is data ingestion for ready integration into a modeling project. The store serves raw band values and quality flags, not derived indices.
- Service area is the United States today. Infrastructure must scale globally. Thousands of water bodies, down to 10 m across, are served.
- Customer polygons stay in the company's database. Prototypes use public polygons.
- The reference design rasterizes polygons once to tile indices. Other workflows are compared against it. It is not selected.
- Two history scenarios are specified: 2017 onward and 2021 onward. Both near-real-time ingestion and backfill are required.
- No orchestrator is mandated. Specifications stay orchestrator-agnostic.
- Sentinel-2 via AWS is the strongly preferred route. Managed and non-AWS alternatives are assessed on the same criteria for comparison.
- Compute and storage cost estimation is a goal. No budget exists.
- The sequence is: initialize, discover, select, prototype, specify integration, weigh tradeoffs, present.
- Each step follows the workflow in [CLAUDE.md](../../CLAUDE.md) with owner, Codex, and Claude Code review.
- Discovery focuses on workflows and data-processing options, not on ranking vendors. It uses a team of research and checking subagents.
- Validation against field observations, dated milestones, and the join with weather features are out of scope for this assessment.

## Consequences

- No candidate has preferred status because of existing code. No code exists on 2026-09-09.
- Out-of-scope items are recorded as assumptions so that nobody assumes them silently.
- The supplied report is AI-generated. Its claims stay `unverified` until discovery rechecks them.
- The discovery plan, archived on 2026-09-10 after execution, was the specification of the next step. It started after the owner accepted the initialization review.

## Review triggers

- The owner changes the band list, geography, size floor, history scenarios, or the derived-flag exception.
- Discovery finds that the reference mask-once design cannot meet a stated requirement.
- Selection of prototype candidates. Record it in a new decision after the discovery review.
