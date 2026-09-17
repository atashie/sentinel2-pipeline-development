# 0002. AWS source, pixel classes, and tile provenance, 2026-09-10

Status: active. Refines [decision 0001](0001-scope-and-sequence.md), which stays active.

## Context

The owner reviewed the discovery review, archived on 2026-09-10, and gave five directions.
The discovery inventory had compared seven access routes on equal terms. It had left the pixel selection rule for small ponds and the handling of overlapping tiles open.
The response to that feedback, also archived, records each direction and its disposition.

## Decision

- AWS-hosted Sentinel-2 is the source. The company is confident in that choice. Non-AWS and managed options stay in the inventory as context and are not compared for selection.
- The choice between the two AWS routes remains open: the Earth Search cloud-optimized GeoTIFF route and the Sinergise JPEG 2000 route. They are compared on ingestion and processing issues, not on price alone.
- Discovery focuses on the issues of ingesting and processing Sentinel-2 and on comparing workflows, compute platforms, and storage layouts. The inventory carries an issue register with evidence, consequence, and status per issue.
- Every water body is stored as three pixel classes per resolution, computed once per tile from the polygon. Interior pixels lie entirely inside the polygon. Shoreline pixels intersect it partially. Near-land pixels do not intersect it and lie within the near-land distance.
- The near-land distance is 100 m, measured from the polygon edge to the pixel center. It is provisional, assumption A21.
- Every record carries its tile and a tile role marker, primary or overlap. Values from two tiles are never averaged. The rule that names the primary tile is set in prototyping and recorded.
- Cloud dilation, issue I-01, is an open issue to revisit. The store keeps the scene classification code and the cloud probability so the rule can change later.
- Adjacency, issue I-02, is documented lightly and deferred to the modeling team. The store carries context for them: aerosol optical thickness, edge distance, and the near-land class.

## Rationale for the tile provenance marker

Level-2A is processed per tile. In the overlap between neighbors the classification can differ and the aerosol and reflectance are generally different, claim G11 in [s2-best-practices.md](../s2-best-practices.md).
Some tools fuse overlapping items by first valid pixel or stitch tiles and hide the grid, finding F-05 in the inventory. A value without its tile cannot be traced or reproduced.
The DEM-related component of orthorectification error cancels within a relative orbit and adds across orbits, claim G10. The relative orbit is kept so a consumer can remove that one component.

## Consequences

- Assumptions A13, A20, and A21 change in [assumptions.md](../assumptions.md).
- The [draft contract](../data-contract.md) gains `pixel_class`, `coverage_fraction`, `edge_distance_m`, and `tile_role`.
- Inventory candidates carry a role. Seven are context. The HTML shows them collapsed under each dimension.
- A 10 m pond has no interior pixel at any resolution. Its record is shoreline and near-land pixels. The consumer sees the class and the coverage fraction.
- The strict interior rule meets registration error of a few meters, issue I-15. It is accepted now and revisited after measurement.
- Findings about non-AWS routes remain as documented facts. They no longer drive selection.

## Review triggers

- Prototyping measures pixel-class counts on the pilot set and the near-land distance proves too small or too large.
- Either AWS route fails to expose a required layer or the refinement flag.
- The owner revisits cloud dilation, or the modeling team returns adjacency handling to the store.
