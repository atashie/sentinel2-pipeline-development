# Tools

The three renderers use the standard library and make no network requests.

| Script | Reads | Writes | Check mode |
|---|---|---|---|
| [collate_checks.py](collate_checks.py) | `docs/assessment-checks/*-research.json` and `*-checks.json`, the current inventory | `docs/options-inventory.json` | `--check` fails when the inventory is stale |
| [render_options.py](render_options.py) | [Presentation template](s2-options.template.html), the inventory's issue `plain` lines, gap survey report counts and monthly coverage, map provenance and image digests | `docs/s2-options.html` | `--check` fails when the HTML or map assets are stale |
| [gap_report.py](gap_report.py) | `benchmarks/results/gap-survey.json`, `benchmarks/results/fallback-survey.json`, the probe record | `docs/reviews/2026-09-10-gap-survey-report.json` | `--check` fails when the report is stale |

[../docs/assessment-data-format.md](../docs/assessment-data-format.md) defines the formats and the regeneration order.

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
Selection rules, terms, and the request log are recorded in the manifest. The format and limits are in [../examples/README.md](../examples/README.md).
