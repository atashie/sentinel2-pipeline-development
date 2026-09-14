# Pilot manifest review and partial Prototyping results, 2026-09-12

Reviewer: Codex. Source research: `/root/independent_archives`. Independent source checker: `/root/check_archive_claims`, gpt-5.6-sol.

Scope: commit `67ecd1a`, its saved polygon responses, the manifest survey option, tests, documentation, and presentation.
The [initial record](2026-09-11-pilot-manifest.md) covers the first preparation item within the owner's Step 3 authorization.

The manifest is useful for testing geometry handling. Its saved inputs reproduce the committed result exactly.
This establishes a public test set, not validated shorelines or successful Sentinel-2 processing.
The Prototyping tab now shows this partial progress and separates it from the earlier Discovery measurements.

## Findings and dispositions

| Finding | Disposition |
|---|---|
| Changed configuration or cached responses silently retained the original retrieval provenance | **Fixed.** The builder now checks configuration and response digests before loading. Regression tests cover both mismatches and an unrecorded response |
| The 10 m class was described as pond width and the dataset's smallest mapped features | **Corrected with evidence.** It is the square root of area. Selection targets that value and establishes neither minimum mapping size nor actual width |
| Source currency and reservoir purpose were insufficiently qualified | **Corrected with evidence.** NHD is retired. Feature modification dates are not shoreline observations. Unspecified reservoir codes do not establish water-storage use |
| `--manifest` was treated as discovering the water bodies' tiles | **Accepted and deferred.** It finds candidate tiles from unbuffered boxes and recent Collection 1 footprints. It can add unrelated tiles and miss buffer-only coverage |
| The proposed rerun overwrote Discovery inputs while the report retained point-specific wording and dated interpretations | **Partly fixed.** The plan now uses separate pilot outputs. Report adaptation and scope validation remain pending before new coverage findings are presented |
| Prototyping remained a placeholder despite completed preparation | **Fixed.** The page shows manifest counts, purpose, checked preparation, and outstanding comparisons. Counts and the manifest digest are supplied by the renderer |
| Refetching always writes `polygon_version: 1` | **Accepted and deferred.** No geometry changed in this review. Define revision handling before refreshed geometry enters results that must distinguish polygon versions |

The standard-library builder and survey extension are proportionate to this preparation step. No new processing framework is needed for these corrections.
The existing tests check selection arithmetic and fixture requests. They do not establish current water presence, provider completeness, or processing performance.

## Evidence checked locally

Evidence: [committed manifest](../../examples/water-bodies-public-pilot.geojson), [region configuration](../../examples/pilot-regions.json), and saved responses under `data/pilot-manifest/20260912T001806Z/`.

- All saved-file SHA-256 digests and the configuration digest match the retrieval record.
- An offline rebuild to a temporary file matched the committed manifest byte for byte.
- The manifest contains 32 features across six regions, comprising 27 size-class selections and five larger anchor lakes.
- All five target size classes occur. Five polygons fall in the 10 m area-equivalent class, with recorded widths from 10.1 to 11.5 m.
- All 32 stored geometries and their original downloaded counterparts passed Shapely validity checks. All five anchor polygons cover their configured survey points.
- The manifest records 151,724 vertices. Lake Lanier contributes 84,468. These describe geometry complexity, not extraction runtime.
- Retrieval logged 13 HTTP requests and 10,809,589 response-body bytes. These were hydrography responses, not imagery transfers or a processing-cost benchmark.
- Feature modification dates range from 2002-02-26 through 2023-03-08. Retrieval time was 2026-09-12T00:18:06+00:00.
- Two selected records carry unspecified-purpose reservoir code 43600: the smallest Tahoe feature and Grand Lake.

Independent geometry diagnostics used Shapely 2.1.2, GEOS 3.13.1, Rasterio 1.5.1, and GDAL 3.12.4 from existing cached packages.
Validity checks used `shape(geometry).is_valid`. Anchor checks used `polygon.covers(Point(longitude, latitude))`.
An area diagnostic transformed stored coordinates to EPSG:6933 with `rasterio.warp.transform_geom`, then calculated Shapely area.
The builder's spherical area approximation differed by approximately −0.557% to +0.192% from that diagnostic.
This was a diagnostic without a declared acceptance tolerance. It establishes neither positional accuracy nor a production area method.

The downloaded responses remain outside git. A fresh checkout needs those files to reproduce the retrieval without another provider read.
Digest checks detect changed inputs against the saved log. They are not authentication of the provider or a complete software-version record.

## Source checks

The researcher and checker independently opened the primary USGS pages on 2026-09-12. Their confirmed qualifications follow.

- **Documented:** [Layer 12](https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/12?f=pjson) is Waterbody - Large Scale and supports polygon queries.
- **Documented:** [The service](https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer) displays a July 2026 refresh and cautions that mapped conditions may have changed.
- **Documented:** [USGS retired NHD on 2023-10-01](https://www.usgs.gov/national-hydrography). It remains available without maintenance.
- **Documented:** [FDate means last feature modification](https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-feature-classes), not the observation date of a shoreline.
- **Documented:** [Reservoir codes 43600, 43618, and 43619 leave purpose unspecified](https://www.usgs.gov/ngp-standards-and-specifications/national-hydrography-dataset-nhd-data-dictionary-feature-domains). Codes 43613, 43615, 43617, and 43621 explicitly describe water storage.
- **Documented:** [USGS positional-accuracy guidance](https://www.usgs.gov/faqs/what-positional-accuracy-national-hydrography-dataset-nhd) describes historical mapping standards and variation among contributed sources. It does not validate the selected small polygons.
- **Documented:** [The National Map terms](https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map) state that the data and services are free and public domain. They request the recorded acknowledgment.

**Inference:** these boundaries support geometry experiments. Their precision, feature codes, and modification dates do not establish accurate current water masks.
Source retirement alone does not invalidate their use as public test geometries or select a replacement polygon source for production.

## Survey and presentation limits

The manifest survey option constructs bounding-box requests correctly in fixtures. It has not run against the catalog for these 32 bodies.
Recent Collection 1 footprints determine discovery. A tile with no qualifying footprint remains undiscovered, even if another collection holds relevant history.
The boxes do not include the provisional near-land buffer. Exact polygon intersection and buffered coverage are not measured.
Earlier point observations establish overlap opportunities for some anchor lakes, not a complete tile list for every pilot polygon.

The [rerun plan](../gap-survey-plan.md#rerun) now preserves the original survey outputs. The existing report still describes point coverage and carries snapshot-specific interpretations.
Adapt and review that reporting path before generating a pilot report. No pilot result replaces the 20-point Discovery evidence during this review.

The HTML now labels Prototyping as partial results. It separates preparation from pixel correctness, coverage, runtime, and cost questions.
It keeps the educational satellite maps distinct from processing benchmarks. No workflow, platform, storage layout, or performance winner is selected.

## Verification

Initial baseline: `.venv/bin/python -m pytest -q`, 82 passed in 0.49 seconds.

- Required workflow passed in order: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q`.
- Ruff reported 54 files already formatted. Pytest reported 87 passed in 0.63 seconds.
- `tools/collate_checks.py --check`, `tools/gap_report.py --check`, and `tools/render_options.py --check` passed without network access.
- `tools/build_pilot_manifest.py --output /private/tmp/pilot-rebuilt.geojson`, followed by `cmp`, confirmed the corrected loader preserves the committed manifest exactly.
- Local browser checks completed on 2026-09-13. All four tabs, keyboard navigation, direct Prototyping links, displayed manifest counts, and 12 map selections passed.
- Prototyping fit 390, 768, 1024, and 1440 pixel viewports without page overflow. Desktop and mobile screenshots were inspected. No browser errors occurred.
- The first browser assertion expected mixed case, while CSS displayed uppercase. The temporary check was corrected to normalize case before passing.
- `git diff --check` passed. No staged changes existed or were added. Survey evidence, pilot geometry, and satellite image assets remain unchanged.

## Next review

The owner reviews [s2-options.html](../s2-options.html) with Claude Code.
Agree the next bounded test together, including the geometry cases, coverage scope, and tolerances it needs.
The fill policy, Alaska scope, quality layers, model input product, and record layout remain open where previously recorded.
No provider survey, satellite download, or processing comparison ran during this review. No files were committed, pushed, or published.
