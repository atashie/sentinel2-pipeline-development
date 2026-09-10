# Benchmarks

Scripts that produce evidence. Each writes one JSON file to `results/`. The file carries `measured_at`, a `limitations` list, and the product IDs or catalog snapshot it depends on. It also carries the code version and the bucket, region, and payer. The results are read in [../docs/measurements.md](../docs/measurements.md). Never edit a result file by hand. Rerun the script.

No script exists on 2026-09-09. Scripts arrive with the prototyping step in [../docs/work-plan.md](../docs/work-plan.md).

`workloads.json` declares the workload matrix for the [assessment protocol](../docs/assessment-protocol.md). Its water-body counts are assumption A6 and its history starts are assumption A10 in [../docs/assumptions.md](../docs/assumptions.md).

The scale driver is expected to be distinct tile-dates read, not water-body count (assumption A17, unmeasured). Every result reports both.

## Rules

- Declare tolerances before you look at a difference. Never change a tolerance to make a check pass.
- Label every number: bytes transferred, requests, pixels read, or output bytes.
- Scripts that read products contact a provider and can cost money. Run them one at a time, only when the user invokes them.
- Fixture benchmarks use synthetic rasters. Say so wherever their numbers appear.
