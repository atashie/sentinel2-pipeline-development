# 0010. Primary tile per water body: one fixed tile, same UTM zone first, then the largest buffered share, 2026-10-15

Status: active. The owner gave the direction on 2026-10-15, quoted in the [direction record](../reviews/2026-10-15-primary-tile-and-compression-direction.md).
It replaces the provisional rule of assumption A22 and the primary tile provision of [decision 0003](0003-earth-search-2021-first-gap-survey-cross-tile.md).
Decision 0002's tile role marker stays. The store never mosaics, and issue I-30 stays open for the scientific comparison.

## Context

The provisional rule of 2026-09-10 named the tile that contains the buffered polygon, else the tile where it lies farthest from the edge.
Stage 4 applied it on 2026-09-16 and left 22 of 25 lake-tile memberships without a role. Small ponds sit inside several tiles, and Lake Lanier fits in none.
Probe T7 then measured how much the choice matters, [findings 38 and 39](../measurements.md#phase-c-probe-t7-each-option-across-two-overlapping-tiles-2026-10-15).
On one date, a lake's values differed between overlapping tiles by a median of up to 0.0055 reflectance, tens of percent of the dark-water signal.
A series that switches tile can step by that much. Tiles in another UTM zone also change the pixel grid.

## Decision

- **One fixed tile.** Each water body has one primary tile for every date. It is the same under ACOLITE only and Sen2Cor only.
- **Same zone first.** Candidates are the tiles whose extent meets the buffered polygon. Tiles in the UTM zone that holds the polygon's centroid come first.
- **Largest buffered share.** Among those, the primary tile holds the largest share of the buffered polygon inside its extent. The buffer is the near-land distance of assumption A21.
- **Ties.** Shares within 1 percentage point tie. The smaller tile id wins. A water body inside several tiles ties at 100 percent and takes the smaller tile id.
- **No switching.** A date when the primary tile holds no valid pixel of the water body is missing for it, and is counted.
- **Overlap tiles kept.** Values from the other tiles stay in the store with the overlap marker. The model team can test switching or other uses later.
- **Recorded inputs.** Each assignment records the polygon version and its digest, the margin, and the candidate shares.

## Consequences

- Every lake-tile membership gets a role. Stage 4's measured results stay frozen with their null roles. The rule applies to new work.
- Under ACOLITE only, both datastrip products of one pass on the primary tile stay standalone observations, decision 0009. The role belongs to the tile.
- The [data contract](../data-contract.md), assumption A22, practice P2, and issue I-30 refer to this rule.
- Dates when the primary tile lacks data add to each option's missing count. Overlap tiles could fill some of them, which this rule leaves to a later decision.

## Review triggers

- The company's own experiments show that switching tiles, or using several tiles, serves the model better.
- Tile offsets prove to persist or to vary with conditions on more dates than T7 measured.
- Expansion beyond the United States brings zones and tiles that this rule did not consider.
- A polygon revision changes a water body's candidate shares.
