# Benchmarks

Scripts that produce evidence. Each writes one JSON file to `results/`. The file carries `measured_at`, a `limitations` list, and the product IDs or catalog snapshot it depends on. It also carries the code version and the bucket, region, and payer. The results are read in [../docs/measurements.md](../docs/measurements.md). Never edit a result file by hand. Rerun the script.

| Script | Contacts | Writes | Runs when |
|---|---|---|---|
| [gap_survey.py](gap_survey.py) | Earth Search STAC API, and the Copernicus Data Space Ecosystem catalogs as a reference count. Catalog metadata only, no imagery, no credentials | `results/gap-survey.json`, raw listings under `data/gap-survey/` | The user invokes it. Plan and rerun steps in [../docs/gap-survey-plan.md](../docs/gap-survey-plan.md) |
| [fallback_survey.py](fallback_survey.py) | The same catalogs, plus HEAD requests without credentials on a sample of GeoTIFF objects in the public `sentinel-cogs` bucket. Headers only, no pixel | `results/fallback-survey.json`, raw listings under `data/fallback-survey/` | The user invokes it, after `gap_survey.py`, whose result it reads |

`gap-survey-sites.json` lists the public water bodies the gap survey uses as points, with the reason for each. It stands in for the pilot manifest until [../examples/water-bodies-public-pilot.geojson](../examples/water-bodies-public-pilot.geojson) is populated.

Prototype benchmarks arrive with the prototyping step in [../docs/work-plan.md](../docs/work-plan.md).

`workloads.json` declares the workload matrix for the [work plan](../docs/work-plan.md). Its water-body counts are assumption A6 and its history starts are assumption A10 in [../docs/assumptions.md](../docs/assumptions.md).

The scale driver is expected to be distinct tile-dates read, not water-body count (assumption A17, unmeasured). Every result reports both.

## Rules

- Declare tolerances before you look at a difference. Never change a tolerance to make a check pass.
- Label every number: bytes transferred, requests, pixels read, or output bytes.
- Scripts that read products contact a provider and can cost money. Run them one at a time, only when the user invokes them.
- Fixture benchmarks use synthetic rasters. Say so wherever their numbers appear.
