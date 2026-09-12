# 0004. COG fallback and presentation clarifications, 2026-09-11

Status: active. Clarifies [decision 0003](0003-earth-search-2021-first-gap-survey-cross-tile.md), which remains active except for its fallback format.

## Context

The owner requested the older collection's COGs as fallback before the additional gap survey.
The [survey](../measurements.md) confirmed usable COG assets in its metadata and header checks. Pixel values remain untested.
The owner's presentation directions are recorded in the [first review](../reviews/2026-09-11-presentation-review.md) and [second review](../reviews/2026-09-11-owner-review-round-two.md).
This record consolidates those directions. It introduces no new selection.

## Decision

- Prefer Collection 1 COG assets, with the older collection's COG assets for backfill. This replaces decision 0003's JPEG 2000 fallback wording.
- Retain JPEG 2000 for context and possible reference checks. Missing quality layers and uncovered periods remain fill-policy questions.
- Explain the Sentinel-2 preference through finer pixels, revisit opportunities, red-edge bands, currency, and consistent instrument design.
- Treat the illustrated row per pixel per native grid as a candidate. Physical layout remains open.

## Consequences

Assumptions A13 and A23 reflect the owner's recorded direction. A3 explicitly includes B8A, without confirming the proposed band set.
The work plan and inventory use COG fallback terminology. They carry unresolved fill-policy questions into prototype planning.
No processing workflow, compute platform, storage layout, or prototype run is selected by this clarification.

## Review triggers

Revisit the fallback preference if pixel checks reveal blocking differences, access changes, or uncovered periods require another route.
Use prototype evidence and model requirements to settle the remaining choices.
