# Data contract, draft 2026-09-09

Status: draft under assessment. No field here is selected. The draft exists so that discovery candidates are compared against one target and so the modeling project can see what to expect.
Once a prototype exists, a change here is a contract change. It then needs a processing version bump, a documentation update, and a test.

## What the store serves

Raw band values and quality flags for every pixel that a water-body mask covers. Every scene that covers the water body is included. Assumptions A1, A2, and A3 in [assumptions.md](assumptions.md) set the content.
The storage layout is a discovery dimension. This section fixes the logical content, not the layout. Whether a record is one pixel or one water body with arrays is open.

| Group | Field | Meaning |
|---|---|---|
| Identity | `water_body_id` | Stable id from the manifest. Never reused. Keeps the later weather join possible (assumption A16) |
| Identity | `polygon_version` | Version of the polygon that produced the mask |
| Identity | `tile_id` | MGRS tile, for example `17RLP` |
| Identity | `sensing_time` | Scene sensing time, UTC |
| Identity | `product_id` | Product name as delivered by the route |
| Identity | `processing_baseline` | From product metadata. Practice P4 in [s2-best-practices.md](s2-best-practices.md) |
| Identity | `refinement_status` | Whether geometric refinement was applied, if the route exposes it. Null when unknown |
| Identity | `platform`, `relative_orbit` | Satellite and orbit, for same-orbit registration reasoning |
| Location | `resolution_m` | 10, 20, or 60 |
| Location | `row`, `col` | Pixel indices within the tile at that resolution |
| Location | `is_shoreline` | Whether the pixel touches the mask edge. Practice P7 |
| Value | `band` | Band name at native resolution. Practice P3 |
| Value | `dn` | Stored integer as delivered |
| Value | `offset`, `quantification_value` | From product metadata. Practice P8 |
| Quality | `scl_class`, `cloud_probability`, `snow_probability` | Delivered layers at native resolution, where the route has them. Practice P11 |
| Quality | `l1c_masks` | Delivered Level-1C quality masks, where the route has them |
| Quality | `flag_cloud`, `flag_shadow`, `flag_glint`, `flag_snow_ice`, `flag_sensor` | Derived flags of assumption A2, with `flag_version` |
| Accounting | `expected`, `present`, `missing`, `missing_reason` | Per water body and period. Never dropped, always counted |
| Time | `product_generation_time` | From product metadata |
| Time | `published_at` | The route's publication time, when the route exposes it |
| Time | `ingested_at`, `available_at` | Local times. `available_at` is when the record became queryable |

Reflectance is a documented derivation from `dn`, `offset`, and `quantification_value`. Whether the store materializes it is a discovery question.

## Time and revision semantics

- `available_at` is the local publication time, never the upstream time. A backfilled scene becomes visible on the day it is published locally.
- Publications are immutable. A reprocessed product of the same scene is a new revision beside the original. Nothing is overwritten. Practice P9.
- A query can select by exact revision, latest per scene, or as-of a cutoff. As-of returns what was queryable at that time.
- Missing values stay missing. Flagged values stay unchanged. Practice P12.

## Query semantics

The query interface accepts a water-body subset, a period, a band subset, a resolution, and an as-of cutoff. It returns records with provenance, quality, accounting, and freshness.
No query path contacts a provider. Serving reads local storage only.

## Not in the contract

Derived water-quality indices (assumption A1). Validation against field observations (assumption A15). Watershed aggregation, which is later work outside this assessment.
