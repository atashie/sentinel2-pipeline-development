# Decisions

One file per decision, numbered in order. A decision is `proposed`, `active`, or `superseded`. A proposed decision binds nothing until the owner authorizes it.
Record changes in a new decision and link both ways. Mark a replaced decision superseded.
For a partial change, name the replaced provision. The remaining provisions stay active.

| # | Decision | Date | Status |
|---|---|---|---|
| [0001](0001-scope-and-sequence.md) | Scope and sequence of the Sentinel-2 ingestion assessment | 2026-09-09 | active |
| [0002](0002-aws-source-pixel-classes-tile-provenance.md) | AWS source, three pixel classes per water body, tile provenance marker | 2026-09-10 | active |
| [0003](0003-earth-search-2021-first-gap-survey-cross-tile.md) | Earth Search route, 2021 scenario first, gap survey before analysis, cross-tile mosaicking as a major concern | 2026-09-10 | active |
| [0004](0004-cog-fallback-and-presentation-clarifications.md) | COG fallback and recorded presentation direction. Clarifies 0003's fallback format | 2026-09-11 | active |
| [0005](0005-aws-cost-scenarios.md) | National and sampled AWS cost scenarios, offline estimates, and same-region serving | 2026-09-22 | active |
| [0006](0006-aws-cost-review-refinements.md) | Cohort byte checks and explicit cost-driver sensitivities following review | 2026-09-23 | active |
| [0007](0007-aws-daily-update-costs.md) | Forward update costs, storage accrual, and acquisition-rate distinctions | 2026-09-23 | active |
| [0008](0008-acolite-aquatic-reflectance-first.md) | ACOLITE aquatic reflectance first for the lower 48, Level-2A supplementary. Replaces the route provision of 0003. Earth Search becomes supplementary under the fallback order of 0004. Its supplementary provision is replaced by 0009 | 2026-10-13 | active |
| [0009](0009-standalone-options-join-deferred.md) | Standalone options, ACOLITE only or Sen2Cor only, with the scene join deferred. Amends 0008 | 2026-10-14 | active |

Template: title, date, status, context, decision, consequences, and the conditions that trigger a review.
