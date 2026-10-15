# 0009. Standalone options, ACOLITE only or Sen2Cor only, with the scene join deferred, 2026-10-14

Status: active. The owner gave the direction on 2026-10-14, quoted in the [direction record](../reviews/2026-10-14-standalone-options-direction.md).
It amends [decision 0008](0008-acolite-aquatic-reflectance-first.md). It replaces that decision's supplementary provision. The other provisions of 0008 stand.
The Collection 1 first, older copy fallback order of [decision 0004](0004-cog-fallback-and-presentation-clarifications.md) stays in force within the Sen2Cor-only option.

## Context

Decision 0008 gave Earth Search Level-2A four roles beside the USGS product: quality flags, land values, comparison values, and fallback scenes.
Two of those roles need a join from each USGS scene to a Level-2A item. Probe T3 measured that join by tile, platform, and sensing start, [finding 28](../measurements.md#28-level-2a-quality-layers-join-by-tile-platform-and-sensing-start-often-from-another-processing-of-the-same-pass).
The key identifies a pass, not one product. In probe T4 it matched two items for 2 of 59 scenes, and the rule took the wrong datastrip both times, [finding 30](../measurements.md#30-inside-the-products-scene-every-pilot-lake-pixel-holds-a-value-in-every-band-and-class).
The owner answered by making each source a standalone option.

## Decision

- **Standalone products.** Each USGS ACOLITE product is a standalone observation. Its quality comes from its own flags layer. Two products of one pass on one tile, one per datastrip, are two observations.
- **No scene join.** The store joins no Level-2A item to an ACOLITE record. A join is reconsidered only when evidence proves beyond doubt that the model needs it.
- **Two options.** The assessment compares two options, each used alone. ACOLITE only is the USGS product, for water pixels in the lower 48 states. Sen2Cor only is Earth Search Level-2A.
- **Neither option fills or flags the other.** Where the chosen option has no scene, the record is missing and counted.
- **Initial preference.** Assumption A52 stands. ACOLITE is treated as designed for water, and the USGS product is the initial primary source. It keeps the name primary product in this repository.
- **Paused roles.** Level-2A's quality, land-value, and fallback roles beside ACOLITE records pause. Its comparison role becomes the Sen2Cor-only option, which the company's own experiments compare with ACOLITE.
- **Self-run ACOLITE.** Running ACOLITE from Level-1C stays the documented gap-fill context of assumption A48. It uses the same processor, so it fits the ACOLITE-only option.

## Consequences

- Under ACOLITE only, the store has no cloud-shadow or snow flag. The product's flags mark non-water, cirrus, bright, negative, and out-of-scene pixels, findings 26 and 31. Issue I-32 is deferred.
- Under ACOLITE only, scenes the product lacks stay missing. From 2018 it holds 41 to 61 percent of Earth Search's acquisitions per year on the survey tiles, [finding 27](../measurements.md#27-the-product-holds-41-to-61-percent-of-earth-searchs-acquisitions-in-most-years-and-new-scenes-arrive-a-median-eight-hours-after-sensing). Issue I-40.
- Under ACOLITE only, water bodies outside the lower 48 states have no source. The Alaska pilot region is a Sen2Cor-only case.
- Assumptions A13, A46, and A47 change in [assumptions.md](../assumptions.md).
- The [data contract](../data-contract.md) loses its join fields. Each record carries one product family, and its flags come from its own product.
- The two-source join prototype and the quality-layer mapping across baselines are deferred in the [work plan](../work-plan.md). Costs, units of work, and tradeoffs are stated per option.
- The inventory lists both access routes as options compared for selection. Combination C-09 drops the join.
- The page describes two standalone options in its access and processing sections.

## Review triggers

- Evidence that the product's own flags leave pixels the model must screen unflagged. The owner judges whether it proves a join is needed.
- The company's own experiments compare the two options, assumption A52.
- The triggers of decision 0008 that do not concern the join.
