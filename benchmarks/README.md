# Benchmarks

Scripts that produce evidence. Each writes one JSON file to `results/`. The file carries `measured_at`, a `limitations` list, and the product IDs or catalog snapshot it depends on. It also carries the code version and the bucket, region, and payer. The results are read in [../docs/measurements.md](../docs/measurements.md). Never edit a result file by hand. Rerun the script.

| Script | Contacts | Writes | Runs when |
|---|---|---|---|
| [gap_survey.py](gap_survey.py) | Earth Search STAC API, and the Copernicus Data Space Ecosystem catalogs as a reference count. Catalog metadata only, no imagery, no credentials | `results/gap-survey.json`, raw listings under `data/gap-survey/` | The user invokes it. Plan and rerun steps in [../docs/gap-survey-plan.md](../docs/gap-survey-plan.md). `--manifest` surveys the pilot manifest's water bodies by bounding box |
| [fallback_survey.py](fallback_survey.py) | The same catalogs, plus HEAD requests without credentials on a sample of GeoTIFF objects in the public `sentinel-cogs` bucket. Headers only, no pixel | `results/fallback-survey.json`, raw listings under `data/fallback-survey/` | The user invokes it, after `gap_survey.py`, whose result it reads |
| [raw_access.py](raw_access.py) | Earth Search STAC API for one acquisition, then whole-tile GET and range reads of every GeoTIFF band on both public buckets. Unsigned, no credentials | `results/raw-access.json` and `results/raw-access-older-quality-all.json`, worker specs, GDAL logs, and per-run results under `data/raw-access/` | The user invokes it. Stage 1 of [../docs/work-plan.md](../docs/work-plan.md). `--dry-run` prints the plan and contacts nothing. `--reuse DIR` skips runs an interrupted pass already saved |
| [copy_difference.py](copy_difference.py) | The same catalog, then range reads of the named files of one product from both buckets | `results/copy-difference.json` | The user invokes it. Compares stored integers pixel by pixel between the copies |
| [lake_extraction.py](lake_extraction.py) | Earth Search STAC API for one Collection 1 item per pilot region. Then range reads of lake windows from the public bucket, one lake at a time, with four methods. Unsigned, no credentials | `results/lake-extraction.json`, saved items, masks, index lists, worker specs, GDAL logs, and per-run results under `data/lake-extraction/` | The user invokes it. Stage 2 of [../docs/work-plan.md](../docs/work-plan.md), run on 2026-09-15. `--dry-run` prints the plan and contacts nothing. `--reuse DIR` queries the catalog, then keeps the masks and runs a saved pass measured, bound to their inputs. `--resummarize RESULT` recomputes the summary from the saved runs and contacts nothing |
| [tile_extraction.py](tile_extraction.py) | Earth Search STAC API for the Collection 1 tiles and items that place every pilot lake. Then range reads of every lake of a tile, windowed or whole, with three read patterns and the stage 2 methods. Unsigned, no credentials | `results/tile-extraction.json`, saved items, masks, index lists, worker specs, GDAL logs, and per-run results under `data/tile-extraction/` | The user invokes it. Stage 3 of [../docs/work-plan.md](../docs/work-plan.md), run on 2026-09-15 with a 512-byte block cache by a unit error and rerun on 2026-09-16 with 512 MiB. The result is the rerun's. `--dry-run` prints the plan and contacts nothing. `--reuse DIR` and `--resummarize RESULT` work as for stage 2. The stage 2 result is its baseline |

Stage 4 is implemented in [cross_tile_extraction.py](cross_tile_extraction.py).
The [full run](../docs/reviews/2026-09-16-stage-4-full-run.md) completed and was reviewed.
The [response](../docs/reviews/2026-09-16-codex-stage-4-review-response.md) updates future selection and qualifies the interpretation. The recorded run stays frozen.
It compares lake-first and tile-first extraction with separate native tile records.
The [implementation record](../docs/reviews/2026-09-16-stage-4-implementation.md) owns its commands, input rules, resource limits, and verification.

The larger workload comparison uses [lazy_reader_workloads.py](lazy_reader_workloads.py).
It compares seven configurations for 100 dispersed U.S. lakes and 1,000 concentrated Florida lakes.
The [implementation record](../docs/reviews/2026-09-18-lazy-reader-workload-implementation.md) records selection, commands, memory controls, and cleanup.
The script prints its plan without arguments. `--execute` prepares provider metadata and geometry, then stops after printing the preflight.
`--extract` runs unattempted configurations from that frozen directory. The [review response](../docs/reviews/2026-09-18-lazy-reader-review-response.md) owns current commands and resume rules.
The [geometry continuation](../docs/reviews/2026-09-18-geometry-diagnostic-resume.md) records diagnostic non-convergence and explicit source supersession before extraction.
Each configuration runs once per run directory. Existing pilot evidence remains unchanged.
The owner authorized replacing twelve sleep-interrupted attempts on 2026-09-21, preserving original attempts and retaining two unaffected observations.
The [rerun record](../docs/reviews/2026-09-21-sleep-rerun.md) owns that exception and its guarded recovery commands.

`gap-survey-sites.json` lists the public water bodies the gap survey used as points on 2026-09-10, with the reason for each. The [pilot manifest](../examples/water-bodies-public-pilot.geojson) anchors its regions on these sites, and the survey takes either file.

Prototype scripts share the measurement harness in [../src/s2proto/harness.py](../src/s2proto/harness.py). Until AWS access exists they run on the owner's laptop over the internet, assumption A25 in [../docs/assumptions.md](../docs/assumptions.md).
Pixel classes come from [../src/s2proto/masks.py](../src/s2proto/masks.py): exact coverage fractions and edge distances per polygon, tile, and resolution, assumptions A20 and A21.

`workloads.json` declares the workload matrix for the [work plan](../docs/work-plan.md). Its water-body counts are assumption A6 and its history starts are assumption A10 in [../docs/assumptions.md](../docs/assumptions.md).

Every result reports water-body counts and distinct tile-dates. [Assumption A17](../docs/assumptions.md) records the scaling hypothesis and its partial evidence.

## Rules

- Declare tolerances before you look at a difference. Never change a tolerance to make a check pass.
- Label every number: bytes transferred, requests, pixels read, or output bytes.
- Scripts that read products contact a provider and can cost money. Run them one at a time, only when the user invokes them.
- Fixture benchmarks use synthetic rasters. Say so wherever their numbers appear.
