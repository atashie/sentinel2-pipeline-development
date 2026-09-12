# Phase 2, step 1: public pilot manifest, 2026-09-11

Author: Claude Code (AI coding agent), directed by the repository owner.
On 2026-09-11 the owner authorized the commit and push of the Discovery work, then the start of Step 3. This record covers the first Phase 2 item in [work-plan.md](../work-plan.md).

## The step

A public pilot manifest derived from a public water-body dataset by a checked-in script, and the gap survey prepared to rerun on it.
Acceptance checks: fixture tests without network, every size class present, flat and mountain settings present. Also a measured two-tile body, provenance and terms recorded, and `/check` green.
Deferred: the survey rerun, which the owner invokes. The fill-policy decision. The first bounded comparison, agreed jointly. Any pixel read.

## What changed

- [tools/build_pilot_manifest.py](../../tools/build_pilot_manifest.py), new. Standard library only. `--fetch` contacts The National Map hydro service for polygons and saves every response under ignored `data/pilot-manifest/<time>/`. Without `--fetch` it rebuilds from the newest saved run.
- [examples/pilot-regions.json](../../examples/pilot-regions.json), new. Six regions, each anchored on a gap survey site, with a search box, a terrain setting, and a reason.
- [examples/water-bodies-public-pilot.geojson](../../examples/water-bodies-public-pilot.geojson), populated. 32 features, 3.5 MB, with the dataset, terms, request log, selection rules, and summary embedded.
- [benchmarks/gap_survey.py](../../benchmarks/gap_survey.py): `--manifest` takes the manifest's water bodies as sites and discovers tiles by bounding box. The result records the site mode. Point mode is unchanged.
- Tests: [tests/test_pilot_manifest.py](../../tests/test_pilot_manifest.py), ten tests over the pure helpers, a fixture build, and the committed manifest. One test in `tests/test_gap_survey.py` for the manifest option.
- Documentation: [examples/README.md](../../examples/README.md) rewritten with the full property table and limits. [tools/README.md](../../tools/README.md), [benchmarks/README.md](../../benchmarks/README.md), [gap-survey-plan.md](../gap-survey-plan.md), [work-plan.md](../work-plan.md), [CLAUDE.md](../../CLAUDE.md), and the root README updated.

## Dataset choice

The USGS National Hydrography Dataset, Waterbody - Large Scale layer, read through The National Map hydro service.
It carries ponds down to the 10 m size class and answers box queries without a bulk download. Its service text reads "Data Refreshed July, 2026".
USGS states on its terms page, checked 2026-09-11, that The National Map data are free and in the public domain. The manifest records the requested acknowledgment.
HydroLAKES was excluded because it targets lakes of 10 hectares and more. No non-US dataset was added. The pilot is United States only.

Probes before the choice, not evidence files:

- The layer's area attribute is rounded to three decimals for small ponds, so the script computes area from the returned geometry.
- The Okeechobee and Iliamna survey points lie inside their lakes, so those regions search a box on the shore.
- Iliamna Lake is 2,649 square kilometres with an estimated 120,000 vertices, so the Alaska region carries small lakes only.
- Lake Erie, Lake Mead, Lake Champlain, and the other very large survey lakes were not fetched.

## Selection

Per region and size class, the candidate whose width is nearest the class width, by absolute log ratio, ties to the smaller source id. Width is the square root of the area.
Candidates are lakes, ponds, and water-storage reservoirs under 5 square kilometres with a perennial or unspecified code. Intermittent ponds and treatment, disposal, cooling, evaporation, and pool codes are excluded.
Class bounds are the geometric midpoints between classes: 17.3 m, 54.8 m, 173.2 m, and 547.7 m. The 1,000 m class is open-ended.
Coordinates are rounded to six decimals before area and width are computed, so the tests recompute both from the stored geometry.

## Evidence

Retrieval: 13 requests to `hydro.nationalmap.gov`, 10.8 MB received, at 2026-09-12T00:18:06+00:00, code version `2bbcd01-dirty`. Every response is saved with its SHA-256 digest listed in the manifest.

| Region | Setting | Anchor lake | Candidates | Size classes found |
|---|---|---|---|---|
| tahoe | mountain | Lake Tahoe | 804 | 10, 30, 100, 300, 1000 |
| lanier | hills | Lake Sidney Lanier | 429 | 10, 30, 100, 300 |
| okeechobee | flat | Lake Okeechobee | 644 | 10, 30, 100, 300, 1000 |
| grand-st-marys | flat | Grand Lake | 179 | 10, 30, 100, 300 |
| washington | lowland | Lake Washington | 72 | 10, 30, 100, 300, 1000 |
| iliamna | hills | none | 926 | 30, 100, 300, 1000 |

Totals: 5 large and 27 pilot features, 151,724 vertices. Lake Lanier holds 84,468 of them. Grand Lake is the one MultiPolygon.
The five 10 m class bodies are 10.1 m to 11.5 m wide. The [gap survey](../measurements.md) found the Tahoe, Lanier, and Grand Lake sites in two, four, and three tiles by point discovery.

## Limits

- Tile membership is not in the manifest. The survey rerun discovers it from the catalog, by bounding box, which can add a tile the polygon does not touch.
- Whether a mapped 10 m pond holds water on a given date is unknown. The 10 m class picks are the dataset's smallest mapped features.
- Terrain settings are descriptions in the region configuration, not measurements.
- Area uses a spherical approximation. It serves the size classes, not measurement.
- The fetch ran under the owner's "start step 3" authorization. It read polygons only, from a public hydrography service, with no imagery, no catalog, and no credentials.
- The report tool's evidence text still says tiles come from footprints covering the point. Update it with the rerun.
- The Discovery page still describes the survey's twenty sites. The rerun will change the report the page reads.

## Dispositions of prior findings

- The handoff review's nine findings were fixed by Codex. None reopened. The owner authorized the commit on 2026-09-11 without new findings.
- Fill policy, Alaska scope, the 2023 baseline, and assumption A13's wording: accepted and deferred. They stay open under decision 0004 and enter the survey rerun and the first comparison.
- Which product the existing model was built on: accepted and deferred. The owner asks the modeling colleagues.

## Verification

- `uv sync --locked`, `ruff check`, `ruff format --check`: passed.
- `uv run pytest -q`: 82 passed.
- `collate_checks.py --check`, `render_options.py --check`, `gap_report.py --check`: all current.
- The committed manifest test recomputes area, width, class, vertex count, and bbox for all 32 features from the stored geometry.

## Proposed next step, not started

1. The owner runs the survey on the manifest, then the fallback survey and the report, as the [plan](../gap-survey-plan.md) lists. About 32 discovery requests plus full listings for any tile the point survey did not cover.
2. Then agree the first bounded comparison. Proposal: the offset pixel check (issue I-05) and the cross-tile measurement (issue I-30) first, on the Tahoe and Lanier bodies. Both sit in more than one tile. The offset check needs 04.00 items from the older copy.
