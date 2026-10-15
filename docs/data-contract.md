# Data contract, draft v2, updated 2026-10-14

Status: draft under assessment. [Decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md) selects the pixel classes and the tile provenance marker. [Decisions 0008](decisions/0008-acolite-aquatic-reflectance-first.md) and [0009](decisions/0009-standalone-options-join-deferred.md) set two standalone source options. No other field is selected.
The draft exists so that discovery candidates are compared against one target and so the modeling project can see what to expect.
Draft v2 adds source-product provenance for the primary product. Probes T1 to T3 of the [replan record](reviews/2026-10-13-acolite-first-replan.md) answered its encoding and join questions on 2026-10-13.
Probe T4 answered its masking question the same day, findings 30 to 33. On 2026-10-14 decision 0009 removed the join fields.
Findings [26 to 29](measurements.md#phase-b-probes-on-the-usgs-aquatic-reflectance-product-2026-10-13) and [30 to 33](measurements.md#phase-c-probe-t4-pixel-validity-on-the-pilot-lakes-2026-10-13) hold the evidence. The new fields stay candidates until a prototype exists.
Once a prototype exists, a change here is a contract change. It then needs a processing version bump, a documentation update, and a test.

## What the store serves

Reflectance values and quality flags for every pixel that a water-body mask covers, from one source option. Every scene of that option that covers the water body is included.
The ACOLITE-only option serves the USGS ACOLITE aquatic reflectance product, the primary product, for water pixels in the lower 48 states. Assumptions A13 and A46 in [assumptions.md](assumptions.md). It has one 20 m grid.
The Sen2Cor-only option serves Earth Search Level-2A, assumption A47. It has 10 m, 20 m, and 60 m grids. Neither option fills or flags the other, decision 0009.
Assumptions A1, A2, A3, and A49 set the content. Extraction geometry is three pixel classes per source grid, assumptions A20 and A21: interior, shoreline, and near-land. A 10 m pond has no interior pixel on any grid.
The storage layout remains open. The presentation illustrates one row per pixel and observation, containing bands from one native grid.
Alternatives include one row per pixel per band and arrays per water body. The field list describes logical content across these candidates.

| Group | Field | Meaning |
|---|---|---|
| Identity | `water_body_id` | Stable id from the manifest. Never reused. Keeps the later weather join possible (assumption A16) |
| Identity | `polygon_version` | Version of the polygon that produced the mask |
| Identity | `tile_id` | MGRS tile, for example `17RLP` |
| Identity | `tile_role` | `primary` or `overlap` under the rule of assumption A22 and [decision 0010](decisions/0010-primary-tile-rule.md): one fixed primary tile per water body. Rationale in [decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md). Values from two tiles are never averaged. **The store never mosaics. Cross-tile mosaicking is a MAJOR CONCERN under investigation, issue I-30** |
| Identity | `sensing_time` | Scene sensing time, UTC |
| Identity | `product_family` | `aquatic_reflectance` under the ACOLITE-only option or `level_2a` under the Sen2Cor-only option. Every record carries one. Decision 0009 |
| Identity | `product_id` | Product name as delivered by the route. For the primary product, the object name in the bucket. Two products of one pass on one tile, one per datastrip, are two records, finding 30 |
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
| Value | `ndwi` | The primary product's delivered NDWI layer, a signed 16-bit integer stored as delivered, assumption A49. Not an index the store derives. It is the normalized difference of the delivered B03 and B8A, times 10,000, finding 32. Null for Level-2A |
| Value | `mask_reason` | Why a pixel has no value: `processor_masked`, `no_data`, `outside_tile`, or `not_delivered`. Probe T4 found no processor-masked pixel inside the product's scene, finding 30. Its no-data pixels carry ACOLITE's out-of-scene flag, reason `no_data` |
| Quality | `scl_class`, `cloud_probability`, `snow_probability` | Delivered Level-2A layers at native resolution, where the route has them. Class codes, never names. Practice P11. Null under the ACOLITE-only option, decision 0009. The primary product has no dedicated cloud, cloud-shadow, or snow layer. Its flags mark non-water, cirrus, bright, and negative pixels, finding 26. They leave most classification shadow over water unflagged, finding 33 |
| Quality | `acolite_flags` | The primary product's `l2_flags` layer, stored as delivered. In probe T4 every value read was the ACOLITE flag integer times 10,000, and no pixel held no-data, finding 30. The settings file names the flag bits. Null for Level-2A |
| Quality | `detector_footprint` | `MSK_DETFOO`, required to detect oversampled no-data at swath edges, claim Q9 |
| Quality | `l1c_masks` | Other delivered Level-1C quality masks, where the route has them |
| Quality | `flag_cloud`, `flag_shadow`, `flag_glint`, `flag_snow_ice`, `flag_sensor` | Derived flags of assumption A2, with `flag_version`. For a primary-product record, derived from its own flags and bands only, decision 0009 |
| Accounting | `expected`, `present`, `missing`, `missing_reason` | Per water body, product family, and period. Never dropped, always counted |
| Time | `product_generation_time` | From product metadata. For the primary product, the settings file's write time, finding 26. The file states no time zone |
| Time | `published_at` | The route's publication time, when the route exposes it. For the primary product, the earliest object last-modified time of the scene. Batches wrote most of the history, finding 27 |
| Time | `ingested_at`, `available_at` | Local times. `available_at` is when the record became queryable |

Reflectance is a documented derivation from `dn`, `scale`, and `offset`. Whether the store materializes it is a discovery question.
Prototype checks must establish the conversion for each tested asset convention before trusting metadata with conflicting offset declarations.
Quality layers have their own grids. Their association with band pixels needs an explicit, tested rule.

## Two standalone options

- The store serves one option's records, decision 0009. Under ACOLITE only, no Level-2A record or layer enters. Under Sen2Cor only, no USGS record enters.
- Each primary-product scene is a standalone record. Its quality comes from its own `acolite_flags` layer.
- Where the chosen option has no scene, the record is missing and counted. No other option fills it.
- A pixel the primary product leaves without a value carries a `mask_reason`. A pixel it flags keeps its value and its flags.
- The company's own experiments compare the two options on the same pixels, assumption A52. The primary product's 20 m grid matches the Level-2A 20 m grid, finding 26.

### Joining the options, deferred

A join of a Level-2A item to a primary-product record waits until evidence proves the model needs it. These facts describe what a join would meet.

- A key of tile, platform, and sensing start finds an item for 92 percent of scenes. 51 percent match the same baseline with Collection 1 first, 58 percent with either, finding 28.
- The key identifies a pass, not one item. In probe T4 it matched two items, one per datastrip, for 2 of 59 scenes. The rule took the other datastrip's item both times, finding 30.
- Each product's settings file names its Level-1C input, which leads to its datastrip. That is a candidate key, untested at scale.
- A joined item can come from another processing of the same pass. Before 2022 its geometry can differ, claims G7 and G8.

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
Masking of shoreline and near-land pixels: none inside the product's scene in 59 scenes of 2025 on the pilot lakes, finding 30. Flags mark non-water pixels instead.
The replan record's rule takes those classes from Level-2A only if the processor masks them, so they stay with the primary product. The owner confirmed this on 2026-10-14, issue I-35.
Join: deferred under decision 0009. The facts are listed under [Joining the options, deferred](#joining-the-options-deferred).
Still open: which quality flags of assumption A2 the primary product alone supports.

## Not in the contract

Derived water-quality indices (assumption A1). Validation against field observations (assumption A15). Watershed aggregation, which is later work outside this assessment.
Self-run ACOLITE output, which is context under assumption A48.
