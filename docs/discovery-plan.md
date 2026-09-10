# Discovery plan, prepared 2026-09-09

Status: proposed. Starts after the owner accepts the initialization review. Authority: [decision 0001](decisions/0001-scope-and-sequence.md).

## Question

Which combinations of access route, processing workflow, compute platform, and storage layout can serve raw Sentinel-2 band values and quality flags? The service covers thousands of water bodies, from 10 m ponds upward, in the United States today and globally later. What documented cost and data-quality risk does each combination carry?

## Bounds

- Documentation research and catalog metadata queries only. No product reads. No prototype code.
- Catalog queries are limited to STAC or equivalent searches that return metadata. Record every endpoint queried.
- Output: [options-inventory.json](options-inventory.json) populated, HTML discovery view generated, [s2-best-practices.md](s2-best-practices.md) claims rechecked, a dated review in [reviews/](reviews/README.md).
- The renderer in `tools/` is written in this step. It uses the standard library and performs no network access.

## Candidates to research

Candidate IDs match [options-inventory.json](options-inventory.json). Every candidate starts with null specifications and a question list.

### Access routes

| ID | Candidate | Class |
|---|---|---|
| `ar-earth-search-cogs` | Earth Search STAC over the Sentinel-2 cloud-optimized GeoTIFF bucket on AWS Open Data | public AWS |
| `ar-aws-requester-pays` | Sentinel-2 Level-2A and Level-1C requester-pays buckets on AWS in JPEG 2000, with notifications | public AWS |
| `ar-cdse` | Copernicus Data Space Ecosystem object store, catalogs, and processing APIs | non-AWS |
| `ar-planetary-computer` | Microsoft Planetary Computer STAC and Azure storage | non-AWS |
| `ar-google-earth-engine` | Google Earth Engine Sentinel-2 collections | managed |
| `ar-sentinel-hub` | Sentinel Hub APIs, commercial | managed |
| `ar-nasa-hls` | NASA Harmonized Landsat Sentinel-2 at 30 m | non-AWS, likely fails assumption A7 |

### Processing workflows

| ID | Candidate | Note |
|---|---|---|
| `wf-mask-once-windowed` | Rasterize polygons to tile indices once, then read only needed windows per scene with range requests | Reference design, assumption A9 |
| `wf-full-tile-then-mask` | Fetch whole tile bands per scene to owned storage, then extract | Simplest, most transfer |
| `wf-datacube` | Build or consume per-tile time cubes, then slice by mask | Zarr or Icechunk |
| `wf-lazy-array-stack` | STAC plus lazy array stacking with chunked computation, rasterizing polygons on the fly | odc-stac, stackstac, xarray, Dask |
| `wf-server-side-extraction` | Provider computes statistics or exports pixels for polygons | May fail assumption A1 unless raw pixels are exported |
| `wf-chip-archive` | Cut a small raster chip per water body per scene, store chips, extract later | Keeps context around the pond |

### Compute platforms

`cp-serverless-functions`, `cp-batch-containers`, `cp-kubernetes-dask`, `cp-spark-cluster`, `cp-provider-compute`. Record what each needs to be idempotent without naming an orchestrator (assumption A12).

### Storage layouts

`sl-parquet-object-store`, `sl-zarr-icechunk`, `sl-lakehouse-table`, `sl-chip-archive`. Record size per water-body-scene, query patterns, revision handling, and immutability.

## Method

1. One research agent per dimension drafts claims with source URL, access date, quoted text, and a proposed value. Drafts go to `assessment-checks/<dimension>-research.json`.
2. A different agent checks each draft claim against its page. It records `confirmed`, `corrected`, or `not_verifiable` with a reason. Records go to `assessment-checks/<dimension>-checks.json`.
3. One agent rechecks every claim in [s2-best-practices.md](s2-best-practices.md) against the pages in its section 6 and updates status and citation.
4. The parent agent collates confirmed and corrected claims into the inventory. Unconfirmed claims stay null with a reason in `gaps`.
5. The parent writes findings and combinations that cite claim IDs only.
6. The parent writes the renderer, generates the HTML, and runs the [check workflow](../.claude/skills/check/SKILL.md).
7. The parent writes the review with dispositions, limits, and the proposed next step.

Checkers use a different model or agent family from the researcher where the environment allows. Record which model checked which claim.

## Acceptance

- Every candidate has every applicable field, either a claim ID or null.
- Every claim cites a source with an access date and links a check record.
- No populated claim lacks a `confirmed` or `corrected` check.
- Every best-practices claim is `documented`, `measured`, or `unverified` with a recorded attempt.
- The HTML renders without external requests. Tables are readable without JavaScript.
- The check workflow passes.
- The review names prototype candidates as a proposal, not a selection, and identifies the next step without starting it.
