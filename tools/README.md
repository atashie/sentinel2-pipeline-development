# Tools

The four scripts in the table use the standard library and make no network requests.

| Script | Reads | Writes | Check mode |
|---|---|---|---|
| [collate_checks.py](collate_checks.py) | `docs/assessment-checks/*-research.json` and `*-checks.json`, the current inventory | `docs/options-inventory.json` | `--check` fails when the inventory is stale |
| [collate_sensor_bands.py](collate_sensor_bands.py) | `docs/assessment-checks/sensor-bands-research.json` and `sensor-bands-checks.json` | `docs/sensor-bands.json` | `--check` fails when the dataset is stale |
| [render_options.py](render_options.py) | [Presentation template](s2-options.template.html), inventory issue `plain` lines, gap survey report, map provenance and image digests, pilot manifest, Stage 1 to 4 results, sensor band dataset, AWS cost estimates and inputs | `docs/s2-options.html` | `--check` fails when the HTML or map assets are stale. Rendering fails when the cost estimates predate their inputs or model |
| [gap_report.py](gap_report.py) | `benchmarks/results/gap-survey.json`, `benchmarks/results/fallback-survey.json`, the probe record | `docs/reviews/2026-09-10-gap-survey-report.json` | `--check` fails when the report is stale |

[../docs/assessment-data-format.md](../docs/assessment-data-format.md) defines the formats and the regeneration order.

## Offline AWS cost model

[estimate_aws_costs.py](estimate_aws_costs.py) reads explicit planning inputs and frozen laptop measurements. It contacts no provider.
The model also reads frozen acquisition counts and separates historical estimates from forward daily costs and retention forecasts.
The [analysis](../docs/aws-cost-analysis.md) explains assumptions, formulas, uncertainty, and qualified price sources.

```sh
uv run python tools/estimate_aws_costs.py
uv run python tools/estimate_aws_costs.py --check
```

Use the pinned Python environment for reproducible floating-point output.

[backtest_source_bytes.py](backtest_source_bytes.py) audits saved block geometry and requested bytes across the two larger-workload cohorts.
It reads frozen local plans and SQLite selections without contacting a provider or changing benchmark evidence.
It writes [cohort-blocks.json](../docs/cost-analysis/cohort-blocks.json). Its `--check` mode requires those preserved local inputs.
The regular accounting tests use the checked-in aggregate and do not require those local inputs.

## Discovery map examples

[build_discovery_maps.py](build_discovery_maps.py) creates six display images from one public Lake Lanier observation.
It uses separately pinned NumPy, Rasterio, and Pillow dependencies through `uv` script metadata. The project's test environment stays unchanged.

After explicit authorization for a public-data download:

```sh
uv run tools/build_discovery_maps.py --download
```

This reads four 10 m band windows and one 20 m classification window through HTTP range requests.
The source item, arrays, and retrieval record stay under ignored `data/discovery-map/`.
GDAL prints request details to stderr. Redirect them to a local log when recording a download.

Rebuild from the cached arrays without contacting a provider:

```sh
uv run tools/build_discovery_maps.py
uv run python tools/render_options.py
```

The renderer takes the displayed sensing date and time from the source provenance, rather than from the product-name timestamp.
The small display images and [provenance record](../docs/assets/discovery/provenance.json) live beside the HTML.
Share the page with its `assets/discovery/` directory. It opens directly from disk and loads no external services.
These are educational displays, not a selected processing workflow or a performance benchmark.

## Pilot manifest builder

[build_pilot_manifest.py](build_pilot_manifest.py) derives [../examples/water-bodies-public-pilot.geojson](../examples/water-bodies-public-pilot.geojson) from [../examples/pilot-regions.json](../examples/pilot-regions.json) and the USGS National Hydrography Dataset. Standard library only.
With `--fetch` it contacts The National Map hydro service for polygons, and saves every response under ignored `data/pilot-manifest/<time>/`. It reads no imagery and no catalog.
Without `--fetch` it rebuilds the manifest from the newest saved run and contacts nothing.
It verifies the configuration and saved-response digests before loading that run. The saved responses are required and remain outside git.
Selection rules, terms, and the request log are recorded in the manifest. The format and limits are in [../examples/README.md](../examples/README.md).

## Larger workload manifests

[build_workload_manifests.py](build_workload_manifests.py) selects separate public cohorts for the [larger workload comparison](../benchmarks/lazy_reader_workloads.py).
The supervised runner invokes it during an explicitly requested execution. It fetches boundary metadata only.
It reuses the pilot's source codes, preserves public identifiers, and removes the pilot's upper candidate-area limit.
The [implementation record](../docs/reviews/2026-09-18-lazy-reader-workload-implementation.md) describes deterministic selection and memory limits.

[audit_workload_execution.py](audit_workload_execution.py) checks a finished run against frozen sources, inputs, launch records, cleanup, and saved macOS sleep events.
It contacts no provider and writes a separate audit without changing the benchmark result.
For replacement runs, it verifies retained observations, frozen plan equivalence, prior complete signatures, and coverage by saved sleep guards.
Before resuming a paused replacement run, preserve its released guard session:

```sh
uv run python tools/audit_workload_execution.py RUN_DIR --archive-session --reason 'Record the startup refusal and reason for resuming.'
```

This archives guard assertions, power events, the interim result, and their hashes without contacting a provider.
The final audit checks every archived session alongside the latest session.
The [original execution record](../docs/reviews/2026-09-19-larger-workload-execution.md) records the first attempt's evidence and timing limits.

[rerun_sleep_workloads.py](rerun_sleep_workloads.py) prepares an explicitly authorized replacement directory from a saved sleep audit.
It preserves original evidence, verifies copied input hashes, and retains unaffected complete observations.
Its extraction mode acquires and monitors macOS sleep assertions before invoking the existing bounded runner.
The [rerun record](../docs/reviews/2026-09-21-sleep-rerun.md) owns commands, authorization, provenance, and verification.
