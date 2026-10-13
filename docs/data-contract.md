# Data contract, draft v2, updated 2026-10-13

Status: draft under assessment. [Decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md) selects the pixel classes and the tile provenance marker. [Decision 0008](decisions/0008-acolite-aquatic-reflectance-first.md) sets two source products for the same water body. No other field is selected.
The draft exists so that discovery candidates are compared against one target and so the modeling project can see what to expect.
Draft v2 adds source-product provenance for the primary product. Probes T1 to T3 of the [replan record](reviews/2026-10-13-acolite-first-replan.md) answered its encoding and join questions on 2026-10-13.
Findings 26 to 29 in [measurements.md](measurements.md#phase-b-probes-on-the-usgs-aquatic-reflectance-product-2026-10-13) hold the evidence. The new fields stay candidates until a prototype exists.
Once a prototype exists, a change here is a contract change. It then needs a processing version bump, a documentation update, and a test.

## What the store serves

Reflectance values and quality flags for every pixel that a water-body mask covers, from two source products. Every scene that covers the water body is included.
The primary product is the USGS ACOLITE aquatic reflectance product, for water pixels in the lower 48 states, assumptions A13 and A46 in [assumptions.md](assumptions.md). It has one 20 m grid.
The supplementary product is Earth Search Level-2A, assumption A47. It supplies quality layers, land and near-land values, comparison values, and the fallback scene. It has 10 m, 20 m, and 60 m grids.
Assumptions A1, A2, A3, and A49 set the content. Extraction geometry is three pixel classes per source grid, assumptions A20 and A21: interior, shoreline, and near-land. A 10 m pond has no interior pixel on any grid.
The storage layout remains open. The presentation illustrates one row per pixel and observation, containing bands from one native grid.
Alternatives include one row per pixel per band and arrays per water body. The field list describes logical content across these candidates.

| Group | Field | Meaning |
|---|---|---|
| Identity | `water_body_id` | Stable id from the manifest. Never reused. Keeps the later weather join possible (assumption A16) |
| Identity | `polygon_version` | Version of the polygon that produced the mask |
| Identity | `tile_id` | MGRS tile, for example `17RLP` |
| Identity | `tile_role` | `primary` or `overlap` under the provisional rule of assumption A22. Rationale in [decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md). Values from two tiles are never averaged. **The store never mosaics. Cross-tile mosaicking is a MAJOR CONCERN under investigation, issue I-30** |
| Identity | `sensing_time` | Scene sensing time, UTC |
| Identity | `product_family` | `aquatic_reflectance` for the primary product or `level_2a` for the supplementary product. Every record carries one. Decision 0008 |
| Identity | `product_id` | Product name as delivered by the route. For the primary product, the object name in the bucket |
| Identity | `processor`, `processor_version` | `acolite` or `sen2cor`. The primary product's settings file states no version. The USGS documentation names ACOLITE 20221114.0, but the probed settings carry the keys of release 20250402.0, finding 26. The version needs a per-scene source. The Level-1C baseline keeps changing, finding 27 |
| Identity | `processing_baseline` | For Level-2A, from product metadata. For the primary product, the Level-1C baseline from the object name, which repeats the Level-1C product name, finding 26. Practice P4 in [s2-best-practices.md](s2-best-practices.md) |
| Identity | `aerosol_mode` | How ACOLITE estimated aerosol for the scene, from the settings keys `dsf_aot_estimate` and `dsf_tile_dimensions`. Every file probed names tiled estimation on 300 by 300 pixel tiles, finding 26. Null for Level-2A. A self-run clipped to one lake uses a different estimate, assumption A48 |
| Identity | `settings_digest` | Digest of the per-scene settings file the primary product delivers. Records the processing configuration. Null for Level-2A |
| Identity | `refinement_status` | The `Image_Refining` flag from the Datastrip metadata, claim G12 in [s2-best-practices.md](s2-best-practices.md). Null where the route does not expose it |
| Identity | `mean_sun_zenith` | Product-level sun zenith angle. Above 70 degrees the product is under-corrected, claim Q11 |
| Identity | `platform`, `relative_orbit` | Satellite and orbit, for same-orbit registration reasoning |
| Location | `resolution_m` | 20 for the primary product, on the Level-2A 20 m grid of the same tile, finding 26. 10, 20, or 60 for Level-2A |
| Location | `row`, `col` | Pixel indices within the tile at that resolution |
| Location | `pixel_class` | `interior`, `shoreline`, or `near_land`, assumption A20. Computed once per tile and source grid from the polygon |
| Location | `coverage_fraction` | Fraction of the pixel area inside the polygon, 0 to 1 |
| Location | `edge_distance_m` | Distance from the pixel center to the polygon edge, negative inside the polygon. Context for the modeling team, issue I-02 |
| Value | `band` | Band name at native resolution. Practice P3. The primary product delivers B01 to B08, B8A, B11, and B12, all at 20 m, finding 26. Its 10 m bands arrive resampled |
| Value | `dn` | Stored value as delivered by the route. An unsigned 16-bit integer for Level-2A. A signed 16-bit integer for the primary product, with no-data -32768 and negative values kept, findings 26 and 29 |
| Value | `scale`, `offset` | Conversion to reflectance in one convention: reflectance = `dn` × `scale` + `offset`. From ESA product metadata, `scale` = 1 / `QUANTIFICATION_VALUE` and `offset` = `BOA_ADD_OFFSET` / `QUANTIFICATION_VALUE`. From catalog metadata, the published `raster:bands` scale and offset. For the primary product, the headers state scale 1 and offset 0. The USGS documentation states a factor of 10,000, so `scale` is 0.0001 and `offset` 0, finding 26. Practice P8 |
| Value | `conversion_source` | Which metadata supplied `scale` and `offset`: `esa_product_metadata`, `catalog_raster_bands`, `provider_pre_applied`, or `provider_documentation`. Earth Search applied the offset during conversion for some items, so the value is per asset, issue I-05. The gap survey measured that the provider's per-item flag and the asset's `raster:bands` offset disagree for most older-collection items from baseline 04.00, [measurements.md](measurements.md) |
| Value | `ndwi` | The primary product's delivered NDWI layer, a signed 16-bit integer stored as delivered, assumption A49. Not an index the store derives. Null for Level-2A |
| Value | `mask_reason` | Why a pixel has no value: `processor_masked`, `no_data`, `outside_tile`, or `not_delivered`. In one crop no pixel was processor-masked, and land kept its values, finding 29. Probe T4 decides at scale |
| Quality | `scl_class`, `cloud_probability`, `snow_probability` | Delivered Level-2A layers at native resolution, where the route has them. Class codes, never names. Practice P11. The primary product has no dedicated cloud, cloud-shadow, or snow layer. Its flags mark non-water, cirrus, bright, and negative pixels, finding 26 |
| Quality | `acolite_flags` | The primary product's `l2_flags` layer, stored as delivered. In one crop every value was the ACOLITE flag integer times 10,000, finding 29. The settings file names the flag bits. Null for Level-2A |
| Quality | `quality_source_product` | The Level-2A `product_id` whose quality layers were joined to a primary-product record, by tile, platform, and sensing start, finding 28. Null where the join found no item |
| Quality | `quality_baseline_match` | Whether the joined Level-2A item has the primary product's processing baseline. With Collection 1 tried first, false for most scenes sensed from 2017 to 2021, finding 28. Null without a join |
| Quality | `detector_footprint` | `MSK_DETFOO`, required to detect oversampled no-data at swath edges, claim Q9 |
| Quality | `l1c_masks` | Other delivered Level-1C quality masks, where the route has them |
| Quality | `flag_cloud`, `flag_shadow`, `flag_glint`, `flag_snow_ice`, `flag_sensor` | Derived flags of assumption A2, with `flag_version`. For a primary-product record, derived from the joined Level-2A layers or from the record itself |
| Accounting | `expected`, `present`, `missing`, `missing_reason` | Per water body, product family, and period. Never dropped, always counted |
| Time | `product_generation_time` | From product metadata. For the primary product, the settings file's write time, finding 26. The file states no time zone |
| Time | `published_at` | The route's publication time, when the route exposes it. For the primary product, the earliest object last-modified time of the scene. Batches wrote most of the history, finding 27 |
| Time | `ingested_at`, `available_at` | Local times. `available_at` is when the record became queryable |

Reflectance is a documented derivation from `dn`, `scale`, and `offset`. Whether the store materializes it is a discovery question.
Prototype checks must establish the conversion for each tested asset convention before trusting metadata with conflicting offset declarations.
Quality layers have their own grids. Their association with band pixels needs an explicit, tested rule.
Level-2A quality layers attached to a primary-product record need the same rule at 20 m, the Phase C join prototype.

## Two products for one water body

- A primary-product record and a Level-2A record for the same water body, tile, and sensing time are stored side by side. Neither replaces the other.
- The join key is the tile, the platform, and the sensing start from the product names, finding 28. The baseline is recorded in `quality_baseline_match`, not required. A failed join leaves `quality_source_product` null and keeps the record.
- The key identifies a pass, not one item. Preferring a same-baseline item in either collection raises baseline agreement from 51 to 58 percent, finding 28. The join rule is a Phase C decision.
- A joined Level-2A item can come from another processing of the same pass. Before 2022 its geometry can differ, claims G7 and G8. How its quality layers map onto the product's pixels is open.
- The modeling team's comparison of the two corrections needs both records for the same pixel. The primary product's 20 m grid matches the Level-2A 20 m grid, finding 26.
- Where the primary product has no scene, the Level-2A record is the fallback, assumption A47. The accounting counts the missing primary scene.
- A pixel the primary product leaves without a value carries a `mask_reason`. A pixel it flags keeps its value and its flags. The Level-2A record for the same pixel stays complete.

## Time and revision semantics

- `available_at` is the local publication time, never the upstream time. A backfilled scene becomes visible on the day it is published locally.
- Publications are immutable. A reprocessed product of the same scene is a new revision beside the original. Nothing is overwritten. Practice P9.
- The primary product's retention and versioning are unknown, test T8. A replaced object is a new revision beside the original, under the same rule.
- Retries preserve the existing publication and its availability time. Changed polygons, extraction rules, or quality processing produce new revisions.
- Prototype design must define duplicate detection and revision identity, including polygon and internal processing versions. ESA's processing baseline alone cannot identify our processing.
- A query can select by exact revision, latest per scene, or as-of a cutoff. As-of returns what was queryable at that time.
- Missing values stay missing. Flagged values stay unchanged. Practice P12.

## Query semantics

The query interface accepts a water-body subset, a period, a product family, a band subset, a resolution, and an as-of cutoff. It returns records with provenance, quality, accounting, and freshness.
No query path contacts a provider. Serving reads local storage only.

## Questions for the next contract revision

Discussion added 2026-09-16, pending a versioned contract revision. No fields or query semantics are adopted here.
[Stage 4 finding 23](measurements.md#23-tile-geometry-product-identity-and-band-validity-need-separate-accounting) exposes per-band no-data and distinct datastrips within one tile and datatake.
Which asset no-data definitions and validity masks accompany stored band values?
How will native quality grids be associated with band pixels without replacing each band's own validity state?
How will revision identity preserve separate datastrips, while primary-tile choices remain tied to polygon versions?

Questions added 2026-10-13 for probes T1 to T3 of the [replan record](reviews/2026-10-13-acolite-first-replan.md), with their answers:
Data type, no-data, and scale: signed 16-bit integers, -32768, and a documented factor of 10,000. The CRS is the tile's UTM zone on the Level-2A 20 m grid, finding 26.
Masking of shoreline and near-land pixels: none in one crop, where flags mark non-water pixels instead, finding 29. Probe T4 decides at scale.
Join: 92 percent of scenes join on tile, platform, and sensing start. 51 percent join to the same baseline with Collection 1 first, and 58 percent with either collection, finding 28.
Still open: which quality flags of assumption A2 the primary product alone supports. Also open: how a quality layer from another baseline maps onto its pixels.

## Not in the contract

Derived water-quality indices (assumption A1). Validation against field observations (assumption A15). Watershed aggregation, which is later work outside this assessment.
Self-run ACOLITE output, which is context under assumption A48.
