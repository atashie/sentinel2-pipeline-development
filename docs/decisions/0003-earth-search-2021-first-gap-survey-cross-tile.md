# 0003. Earth Search route, 2021 scenario first, gap survey, and cross-tile caution, 2026-09-10

Status: active. Builds on [decision 0002](0002-aws-source-pixel-classes-tile-provenance.md), which stays active.

The fallback format below is historical. [Decision 0004](0004-cog-fallback-and-presentation-clarifications.md) replaces it with the older collection's COG assets.
The other provisions remain active.

## Context

The owner accepted the discovery step on 2026-09-10 after the discovery review, two Codex reviews, and four bounded probes recorded in the inventory. The reviews were archived on 2026-09-10.
The probes showed three things. Earth Search's Collection 1 collection lacks June 2017 and June 2022 over a sampled box. Its older collection holds 2017 products at a provider baseline. The Sinergise buckets answer unsigned requests.

## Decision

- **Route.** Earth Search is the access route. Collection 1 cloud-optimized GeoTIFF assets are preferred. Where Collection 1 is missing, the JPEG 2000 assets that Earth Search's older collection references are the fallback. Direct use of the Sinergise buckets as a separate route is not pursued. This question is resolved. Revisit it only on a substantial issue: data that no Earth Search collection covers, a blocking access change, or a measured cost or performance failure.
- **History.** The 2021-onward scenario is prototyped first. Before any substantial analysis, a data gap survey runs over the pilot set: catalog metadata only, per collection, per tile, per month, from 2021-01-01 to the present. It documents every gap, including the 2022 gap the probe found, and the quality assets present per collection and month. The fill policy for gaps is decided after the survey in a new decision. The 2017 to 2020 tier is deferred to a later decision.
- **Primary tile.** The provisional rule of assumption A22 applies: the tile that contains the buffered polygon entirely, else the tile where the buffered polygon lies farthest from the tile edge, tie-broken by the smaller tile id. Every tile's values are stored with the primary or overlap marker of decision 0002.
- **Cross-tile mosaicking.** **MAJOR CONCERN. The owner requires a thorough investigation of cross-tile mosaicking before any stitched value is trusted.** The store never mosaics. The prototype measures differences between tiles over the same pixels on the same dates, per band and per quality layer, and reports them before any consumer-facing mosaic is specified. Issue I-30 carries this in the register.

## Consequences

- Assumptions A10, A13, and A22 change in [assumptions.md](../assumptions.md).
- The Sinergise bucket candidate and its whole-tile combination become context in the inventory. The JPEG 2000 fallback combination stays primary and is reworded to Earth Search's older collection.
- Issues I-08, I-17, I-18, and I-26 change status. Issue I-30 is added with a major-concern flag.
- [work-plan.md](../work-plan.md) gains a gap survey step before prototyping analysis and a cross-tile measurement inside prototyping.
- The gap survey is within discovery bounds: catalog metadata queries only, results written as evidence under `benchmarks/results/`.

## Review triggers

- The gap survey finds a period that no Earth Search collection covers for the pilot set.
- Earth Search changes access terms or removes a collection.
- The cross-tile measurement finds differences large enough to change the consumer contract.
- The owner reopens the 2017 to 2020 tier.
