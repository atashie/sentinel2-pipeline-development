# Stage 4 plan review, 2026-09-16

Reviewer: Claude Code (AI coding agent), directed by the repository owner.
Reviewed: [Codex's stage 4 plan](2026-09-16-stage-4-plan.md) of 2026-09-16.

The plan is sound in its question, its sample, and its coverage accounting. Eight points need a change before implementation.
One is a hazard the plan does not name: the lazy stack can mosaic two tiles into one grid unless the plan forbids it.
The others narrow the scope, fix the acquisition ranking and the primary label, and state what the run is expected to show.

Scope: the plan's claims were checked against the [stage 3 result](../../benchmarks/results/tile-extraction.json), the saved catalog items under `data/tile-extraction/`, [assumption A22](../assumptions.md), [decision 0003](../decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md), and the [draft contract](../data-contract.md).
No provider script ran. No pixel was read. This review adds this file and its index row, and commits nothing.

## What holds

- The sample's facts are right. Lanier's four candidate tiles are 16SGC, 16SGD, 17SKT, and 17SKU, in UTM zones 16 and 17. Lake Lanier lies 69.0, 62.5, 70.3, and 62.6 percent inside them, so no tile holds it. Lake Okeechobee lies 90.0 percent inside 17RNK, 22.7 inside 17RNL, 16.1 inside 17RMK, and 0.4 inside 17RML.
- Stage 3's two Lanier items come from different datatakes, `GS2B_20251015T162149` on relative orbit 40 and `GS2B_20251022T161229` on orbit 140. Its two Okeechobee items share `GS2C_20251031T160521`. The plan's grouping rule is therefore necessary for Lanier and already satisfied for Okeechobee.
- Collection 1 items carry `s2:datatake_id`, `s2:datastrip_id`, `s2:product_uri`, and `platform`. They carry no `sat:relative_orbit`. The relative orbit is the `R040` field of the product URI. Grouping by datatake id is sufficient and needs no orbit field.
- The three notions of coverage, geometry, footprint, and observed data, are the right split. Summed shares double-count overlaps, as the plan says.
- Both paths on frozen inputs, serial workers, the corrected cache, the memory guard, and rotation match stage 3's practice. So do workload totals per repetition before medians.
- The sample answers the plan's first question. Both anchors need more than one tile. Okeechobee's 100 m and 1,000 m lakes lie entirely in 17RNK and 17RNL, and Lanier's 10 m pond in 16SGD and 17SKT. One datatake observes each of them twice. 17RML holds 0.4 percent of Lake Okeechobee, a near-land-only candidate in practice.

## Findings

### 1. High: forbid the lazy stack from loading two tiles into one grid

The plan keeps the lazy stack and says it "retains Stage 3's shared graph". It does not say how the stack meets several tiles.
`odc.stac.load` accepts items from several tiles and reprojects them onto one GeoBox. That is a mosaic, issue I-30, and the store never mosaics.
Stage 3 avoided it by passing one item and an explicit GeoBox on that item's grid, [tile_extraction.py](../../benchmarks/tile_extraction.py).

Change: state that every lazy graph holds one item on that item's native grid, in both paths. Add an acceptance check with a fixture. Two items in different CRSs must yield two graphs, and a call that would merge them must be refused.

### 2. Medium: the fragment store is scope beyond the question

The plan asks for bounded array fragments, a deterministic stream per lake, validation through that stream, and separate timing of writing, grouping, and validation.
That is a small storage layer, and no storage layout is selected. Its timings would describe a format this assessment has not chosen.

The equality question needs less. A contribution is one lake, acquisition group, tile, item, band, and resolution. Stage 3's lake-band records already carry its value digest, pixel-set digest, window, and counts.
Assembly is the canonical ordering of a lake's contribution keys. Two paths agree when their ordered keys and every contribution's digests agree.

Change: keep contributions as stage 3's records with the group and tile added. Compare ordered keys and digests. One fixture checks that shuffled completion gives the same assembly and that a repeated contribution is rejected. Report output bytes as the size measure and time no fragment writing.

### 3. Medium: give every contribution a primary or overlap label now

The plan leaves ambiguous roles unresolved pending the owner. The contract requires `tile_role` on every record, so an unlabeled stage 4 output cannot be checked against it.
The gap is A22's second clause. "Farthest from the tile edge" has no single reading when the buffered polygon crosses every candidate's edge.

Change: propose one reading for the owner's acceptance and apply it provisionally. The primary tile is the one holding the largest share of the buffered polygon, ties by the smaller tile id. It equals the first clause when a tile holds the polygon entirely, and stage 3 already computes the shares. Report the literal reading beside it for the two anchors, the depth of the polygon's farthest point inside each tile. The owner then sees whether the two readings differ. Label every contribution and keep every one regardless of label.

### 4. Medium: state the hypothesis and the new information

Stage 3 measured the parts of this comparison that do not cross tiles. One process per lake pays a size probe and a header read per file, 10 of 15 requests, finding 19. Blocks one lake loads serve the next within an open file.
The tile-first path is therefore expected to need fewer requests and bytes. A run that confirms it adds little.

Change: write the expectation into the plan and say what result would change a workflow choice. Name the measurements that are new. The anchor's bytes per extra tile against its share inside that tile. The area observed twice by one datatake. The support left uncovered after the tile union and after the footprint union. Name the inventory finding, F-26, and the workflow claims it binds.

### 5. Medium: two methods, not four

The plan keeps the naive clip, the raster mask, the index lists, and the lazy stack. Stage 3 showed the three mask methods identical on 200 lake-bands across three read patterns, finding 22. The naive clip differed exactly where preparation predicted, on the partial lakes in 16SGD, 17SKT, 17RNK, and 17RNL included.
Neither method interacts with how work is organized across tiles. Four methods double the run for no new information.

Change: run the raster mask and the lazy stack. Eleven lakes and eight tiles give 114 workers over three repetitions instead of 228. Add a method back only if a cross-tile selection question appears.

### 6. Low: the geometry audit needs densified boundaries

A tile extent is a rectangle in its own UTM zone. Transformed into another zone it is a curve. A straight 110 km edge transformed as two endpoints misses that curve by meters. The area error is far above the 1e-6 relative tolerance the plan reuses.

Change: densify tile boundaries before transforming them. Compute every area in the one reference CRS. Confirm the polygon's round trip through that CRS against the tolerance. Note that the polygon's own vertices are dense enough.

### 7. Low: fix the group ranking in the plan, not before the catalog run

The plan asks for the ranking to be documented before the catalog run. The plan is that document.

Change: a group is a datatake id. It is eligible when the tiles it holds cover the lakes' support by geometry union, with the uncovered remainder reported. Rank eligible groups by complete footprint support for every member tile present. Then take the highest tile cloud cover in the group, lowest first, then the latest datatake. Record the rejected groups. A candidate tile the datatake did not produce is a missing tile, reported as such, never replaced by another date.

### 8. Low: reuse the readers and the masks

Change: the lake-first worker calls stage 3's extraction per tile with a single-lake member list. Both paths then share one reader code path and one accounting. Stage 3's saved masks for 16SGD, 17SKT, 17RNK, and 17RNL are reusable under their digests. New masks are needed for 16SGC, 17SKU, 17RMK, and 17RML.

## Codex's three questions

1. Yes. With every candidate tile enumerated, the sample holds partial coverage, observations repeated by one datatake, a cross-zone case, and a near-land-only candidate. Whether any support needs three tiles is unknown until the union is computed.
2. Yes, as two work units. The process counts differ by design, so report per-worker and per-workload totals, and state the expectation of finding 4.
3. Not yet. Findings 1, 2, 3, and 7 must be settled first.

## Verification and next step

- `uv run pytest -q`: 168 passed. The documentation tests parametrise over every Markdown file, which is why the count rose from 166 with Codex's two new files.
- No provider script ran, and no pixel was read. This review and its index row are the only changes here. Nothing is committed.

Codex's [stage 3 rerun review](2026-09-16-codex-stage-3-rerun-review.md) holds four documentation corrections addressed to Claude Code. They are separate from this plan review and remain open.

Next step: Codex incorporates the accepted points and revises the plan. Implementation and any provider run wait for the owner's authorization.
