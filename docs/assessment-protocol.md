# Assessment protocol

This protocol says how the project assesses ingestion options and what it publishes about them. It keeps four things apart:

- An access route moves Sentinel-2 products to us: a bucket, a catalog, a notification feed, or an API.
- A processing workflow turns products into per-water-body records: how pixels are located, read, masked, flagged, and written.
- A compute platform runs the workflow: functions, containers, clusters, or a provider's own compute.
- A storage layout holds the records: file format, partitioning, indexing, and revision handling.

Two routes feeding the same workflow test delivery, not processing. Two workflows on the same route test processing. Every measurement says which one it tests.
Discovery focuses on processing workflows and their options, per [decision 0001](decisions/0001-scope-and-sequence.md). Routes, platforms, and layouts are the dimensions a workflow is placed in.

## Step 1: discover and collate before selecting

Selection remains open. The preferred route (assumption A13 in [assumptions.md](assumptions.md)) confers no selected status.

1. Inventory access routes on AWS, then managed and non-AWS alternatives.
2. Inventory processing workflows for per-water-body extraction, from the reference mask-once design (assumption A9) to full-tile and datacube designs.
3. Inventory compute platforms and storage layouts that each workflow can run on, naming no orchestrator (assumption A12).
4. Compare on the criteria below. Record documented facts with sources. Leave unknowns null.
5. Collate candidates, findings, unresolved questions, and combinations in the inventory and its HTML view.
6. Present for owner, Codex, and Claude Code review. Record the owner's selection of prototype candidates in a new decision.

Evaluate individual options and complementary combinations using the same criteria. Report documented cost terms separately from measured costs.
Leave unknowns explicit. Specify a bounded probe when documentation cannot settle an important question.
Check license, retention, redistribution, and commercial-use rights separately. Open data terms still carry attribution conditions.

## Criteria

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

## Claim statuses

Every claim in [options-inventory.json](options-inventory.json) and [s2-best-practices.md](s2-best-practices.md) carries one status.

| Status | Requirement |
|---|---|
| `documented` | Cites a dated primary page |
| `measured` | Names the code version, lockfile, sample, artifact checksums, environment, and result |
| `unverified` | Names the test that would settle it |

Every populated inventory claim links primary evidence and an independent AI check. [assessment-data-format.md](assessment-data-format.md) defines the binding.
AI checks verify documentation. They do not establish human approval, archive completeness, data quality, or measured costs.

## Scale and cost

Workloads are in [../benchmarks/workloads.json](../benchmarks/workloads.json): 1 to 10,000 water bodies, clustered and dispersed, two history starts, backfill and daily operation.
Increase provider load gradually. Run aggressive fault and load tests against local fixtures or owned storage only.

Measure these quantities:

- bytes transferred, requests made, pixels read, and output bytes, as four different numbers
- wall time and peak memory per scene and per water body
- publication-to-availability latency
- expected, present, and missing scenes per water body
- distinct tiles and distinct tile-dates read

Test daily operation, a 30-day backfill, and a one-year backfill separately. Keep all revisions in the accounting.

Monthly cost uses measured rates:

```
monthly_cost = compute_hours * compute_price + requests / 1000 * request_price
             + transfer_GB * transfer_price + retained_GB * storage_price
             + service_fees + engineering_hours * labor_rate
archive_GB(years) = bytes_per_water_body_scene * scenes_per_water_body_per_year
                  * water_bodies * years * revision_factor / 1e9
```

Prices stay null until measured or quoted from a dated page. Report cost curves for 1,000 and 10,000 water bodies and for the 2017 and 2021 histories.
Report backfill cost separately from steady-state cost. Report sensitivity to reprocessing frequency. Choose a spending ceiling only after the measurements are published (assumption A14).

## Out of scope

Validation against field observations (assumption A15). The join with weather features (assumption A16). Derived water-quality indices (assumption A1).
