# Discovery presentation revision, 2026-09-11

Reviewer and implementer: Codex. Scope: the owner's requested presentation redesign, with a small public satellite download explicitly authorized.
Audience: software engineers and business decision makers with limited geospatial background.

## What changed

[s2-options.html](../s2-options.html) now has four tabs. Only Discovery contains findings.
The other tabs are Prototyping, Integration Specs, and Tradeoffs & Issues. They contain short placeholders for later joint work.

Discovery tells five connected parts of the story:

- What the sensors measure, how Sentinel-2 differs from Landsat, and why smaller pixels matter around small water bodies.
- How the two AWS archives relate, why both are useful, and what the gap survey establishes.
- How shoreline mixing, atmosphere, tile overlap, processing changes, resolution, and missing dates can mislead analysis.
- Which processing tasks can be reused and which recur, with qualitative effort labels and questions for prototyping.
- Two views of the same real Lake Lanier observation, with six selectable band combinations or indices.

The presentation removes internal issue IDs, decision numbers, status catalogs, and exhaustive specification tables.
Repository evidence stays available through descriptive links. The inventory remains intact.
The [template](../../tools/s2-options.template.html) owns the narrative and layout.
The [renderer](../../tools/render_options.py) inserts measured survey counts and map metadata, and checks image digests.

## Evidence and imagery

The existing inventory, geospatial practices, contract, and survey report support the archive and processing narrative.
Additional sensor facts and band recipes received separate research and checking passes against primary Copernicus, USGS, and NASA pages.
The [source record](../assessment-checks/discovery-presentation-sources.json) names the agents, sources, verdicts, dates, and qualifications.

The owner approved real imagery with a small public-data download. The [map builder](../../tools/build_discovery_maps.py) read one 8 × 8 km window.
It read four 10 m reflectance bands and one 20 m scene-classification layer from the public Collection 1 bucket in AWS Oregon.
The [provenance record](../assets/discovery/provenance.json) records the product, asset URLs, grid, calibration, recipes, attribution, retrieval date, and digests.
Original arrays and the source item remain under ignored `data/discovery-map/`.

The builder logged 15 range GET requests and five HEAD requests, plus one catalog GET.
Returned Content-Range headers account for 20,113,473 raster response-body bytes. This excludes HTTP headers and catalog bytes.
A separate preliminary catalog GET selected and inspected the same observation. No requester-pays access or credentials were used.
These download facts are measured from the local request log. They are not workflow performance results.
The request log was copied into the local map cache. Display assets total approximately 5.7 MiB and load from local files.

All reflectance bands retain the same native grid. The classification layer uses nearest-neighbor expansion.
Asset scale and offset are applied before display and index calculation. Invalid inputs remain excluded rather than forced into an index range.
The maps disclose their color stretches, masking, fixed legends, and limitations. They make no water-quality concentration claim.

## Verification

The required check workflow passed:

- `uv sync --locked`: pinned environment resolved.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 40 files already formatted.
- `uv run pytest -q`: 57 tests passed in 0.20 seconds, including rendered-page freshness and image digest checks.

Headless Chromium opened the HTML directly from disk.
All four tabs, arrow-key and Home navigation, all six views in both map selectors, and their index legends passed browser checks.
No JavaScript errors occurred. There was no horizontal overflow at viewport widths of 390, 768, 1024, and 1440 pixels.
Desktop and mobile screenshots were inspected. The page loads its images locally without a map service.
New regression tests check local assets, links, phase structure, and the absence of internal register labels from the narrative.

## Disposition and limits

- **Fixed:** the previous presentation exposed the internal register and buried the audience-facing explanation. The narrative and examples replace that structure.
- **Fixed:** the page now has the four requested tabs, with later phases left open.
- **Accepted and deferred:** the precise sensor-comparison emphasis awaits the owner's answer. Finer pixels are labeled as a provisional project rationale.
- **Accepted and deferred:** effort labels are hypotheses, not measured timings or selected infrastructure. The underlying comparison remains future work.
- **Accepted and deferred:** archive consistency, complete fallback policy, and cross-tile differences remain prototype questions. This example does not settle them.

The page is designed to open from disk. Share its `assets/discovery/` directory with the HTML.
JavaScript enables tab and map switching. Discovery and its two initial maps remain readable without it.
The renderer's freshness check cannot establish semantic agreement between authored prose and every internal decision. Narrative changes still require review.

## Proposed next step

Review the presentation and refine its sensor rationale. Continue developing the workflow together after that review.
No production implementation, commit, push, or publication was performed.
