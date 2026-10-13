# 0008. ACOLITE aquatic reflectance first for the lower 48, Level-2A supplementary, 2026-10-13

Status: active. The owner authorized it on 2026-10-13 with Phase A of the [replan record](../reviews/2026-10-13-acolite-first-replan.md). The [Phase A record](../reviews/2026-10-13-phase-a-rescope.md) lists the documents it changed.
It replaces the route provision of [decision 0003](0003-earth-search-2021-first-gap-survey-cross-tile.md) for water pixels in the lower 48 states. Earth Search becomes the supplementary route there.
The Collection 1 first, older copy fallback order of [decision 0004](0004-cog-fallback-and-presentation-clarifications.md) stays in force within that role.
It keeps the pixel classes, the tile provenance marker, and the cross-tile caution of [decisions 0002](0002-aws-source-pixel-classes-tile-provenance.md) and 0003.

## Context

On 2026-10-13 the owner asked for a literature analysis of whether Sen2Cor, the processor behind every Earth Search Level-2A collection, suits water quality.
The analysis, AI-generated input under the documentation rules, reported that ESA designs and validates Sen2Cor for land. Claim R3 in [s2-best-practices.md](../s2-best-practices.md) already records the land-only validation.
It also reported a public alternative on AWS Open Data, in the same region as Earth Search. That is the USGS "Sentinel-2 ACOLITE-DSF Aquatic Reflectance for the Conterminous United States".
The owner's eight directions and the inputs to recheck are in the [replan record](../reviews/2026-10-13-acolite-first-replan.md).

## Decision

- **Primary source.** For water pixels in the lower 48 states, the USGS ACOLITE aquatic reflectance product is the primary source. Its facts are `unverified` until check records and the T1 to T3 probes confirm them.
- **Supplementary source.** Earth Search Level-2A, Collection 1 first and the older copy as fallback, is supplementary. It has four roles. It supplies quality flags the primary product lacks. It serves land and near-land values for land monitoring. It gives the modeling team values to compare with ACOLITE. It is the fallback where the primary product has no scene.
- **Scope.** The initial scope is the lower 48 states. Service beyond the United States needs a workflow redraft. The assessment states this and lists the hurdles.
- **Gap filling.** Running ACOLITE from Level-1C is the gap-fill route. It is documented as context with a complexity estimate, not prototyped.
- **Raw data.** The assessment determines whether the route holds Level-1C data sufficient to reproduce ACOLITE values with the published algorithm. If not, it names alternative raw sources.
- **Grid.** The primary product's 20 m grid is accepted. Pixel classes for it are computed at 20 m. Assumption A7 stands. A 10 m body has shoreline and near-land pixels only on that grid. On the pilot, 10 of the 30 lakes inside their tile have no interior pixel at 20 m, [finding 18](../measurements.md#18-pixel-classes-per-size-class-and-lakes-outside-the-chosen-tile).
- **Delivered NDWI.** The product's NDWI layer is stored as a delivered layer. The store still derives no index of its own.
- **Reference series.** The frozen Level-2A measurements stay as reference, pared down on the page. The production-relevant tests take their place.
- **Licensing.** Outside this assessment. The owner handles it with legal counsel.

## Consequences

- Assumptions A3, A4, A13, and A20 change in [assumptions.md](../assumptions.md). Rows A46 to A51 record the primary product, the Level-2A roles, the self-run context, the delivered NDWI, the reference series, and the licensing scope.
- The inventory gains an access-route candidate for the USGS product and a context candidate for self-run ACOLITE. Earth Search's role changes. New issues, probes, findings, and combinations follow.
- The data contract gains source-product provenance and serves two product families for the same water body.
- Every measured number on the page is relabeled as the Level-2A series until the ACOLITE replay exists.
- The cost analysis is re-parameterized after the header probe and the access replay.
- The Alaska pilot region leaves the primary scope and stays as a Level-2A-only case.

## Review triggers

- The header probe shows that the product masks shoreline or near-land pixels, or uses an encoding that breaks the integer-plus-conversion contract.
- The coverage survey shows gaps or latency that the supplementary route cannot fill.
- The join test fails for a material share of scenes.
- USGS publishes a new version prefix, changes the ACOLITE version, or changes access terms.
- The company expands service beyond the lower 48 states.
- The legal review changes what the company may store or redistribute.
