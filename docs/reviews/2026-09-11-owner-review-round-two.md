# Owner review, round two: names, links, figures, effort, and the stored record, 2026-09-11

Implementer: Claude Code (AI coding agent), directed by the repository owner. Scope: the owner's second review of the Discovery page. Seven requests, all applied to the template. No inventory or measurement changed.

## The requests and what changed

| Request | Change |
|---|---|
| Rename the archive table | "Three versions in AWS." |
| Link each copy in the Where row | The two GeoTIFF buckets link to their collections in the STAC Browser, the links the AWS registry itself lists. The JPEG 2000 bucket links to its registry entry |
| "Fill for 2022, if we fill it" | "Use for backfill only" |
| Explain the history table's columns and use consistent names | Columns are now "Version ESA used at the time" and "Version ESA reprocessed to later". A names line under the archive table defines Collection 1 copy, older copy, JPEG 2000 original, and processing version. "Newer copy", "older collection", "older archive", "baselines", and "current archive" are gone from the page. The coverage strip's row labels changed in the renderer |
| Larger text in the section 03 figures | Font sizes in the three drawings rose from 10.5 to 12 points to 14 to 16 points. The cards now sit two per row and each drawing fills its card, so the drawings render about 60 percent larger. Legend and caption text grew one point. Two labels moved to avoid a collision |
| Prominent, colour-coded effort bars with technical dropdowns | Bars are three times wider, labelled in 14-point bold, green for low, orange for medium, red for high, dashed grey for depends. Each of the five steps has a "Technical detail" dropdown with three or four bullets: reprojection, buffering, rasterization with coverage fractions, catalog queries, windowed range reads at native resolution, one conversion convention, append-only keyed writes, and the storage candidates to compare |
| Make the stored record clear | The record is now one row per pixel per observation, on the grid the pixel belongs to. The caption explains why a row belongs to one grid and gives a worked count. The card shows one 10 m shoreline pixel with position, class, coverage, the four bands, scale and offset with their source, quality codes, and provenance. Level-2A has 12 bands, corrected from 13 |

## Follow-up the same day

The owner asked to drop the third drawing in section 03, "Keep every processing version." It is removed. The two remaining drawings, shoreline classes and tile overlap, keep the larger layout. The versioning rule itself stays on the page in the risk card on processing changes and in the workload section.

The owner also found the shoreline drawing wrong: a cell the edge crossed was coloured as land. The drawing's cells are now classed from the edge path itself, by rasterizing it and taking each cell's water fraction. Interior is a full cell, shoreline is any crossed cell, nearby land is the rest. The result is 7 interior, 15 shoreline, and 38 land cells, with the edge drawn on top.

## The two column names, answered

"Version ESA used at the time" is the processing version ESA applied when it first processed those acquisitions, days after sensing. "Version ESA reprocessed to later" is the version ESA assigned when it re-ran old acquisitions through newer software, years later. Both products can exist. The older copy keeps both. The Collection 1 copy admits only 05.00 and later, from either run.

## The stored record, in more detail

Bands arrive on three grids, 10, 20, and 60 m, and the store keeps native resolution. So a row per pixel must belong to one grid. A 10 m row carries four bands, a 20 m row six, a 60 m row two. The [draft data contract](../data-contract.md) lists every field and leaves the physical shape open: one row per pixel with band columns, one row per pixel per band, or arrays per water body. The page presents the first as the working picture and names Parquet as one candidate, matching the owner's expectation. Nothing is selected. Decision 0002 and assumption A20 stand.

The technical dropdowns describe analyses, not a chosen workflow. They name no orchestrator, per assumption A12. Where they list alternatives, prototyping compares them.

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. 47 files formatted |
| `uv run pytest` | 68 passed |
| The three `--check` tools | Inventory, page, and report match their inputs |
| Name scan | No "newer copy", "older collection", "older archive", "baselines", or "current archive" left on the page |
| Sentence audit | No sentence over 25 words, no semicolon, no "should" |
| Headless Chromium, 1440 px, dropdowns forced open | The archive table with links, the enlarged drawings, the colour-coded effort bars with their technical detail, and the record card render |

## Limits

- The STAC Browser links open a third-party viewer over the catalog. They were listed by the AWS registry on 2026-09-11 and not otherwise checked.
- The example row's position, coverage, and quality values are illustrative. The date, tile, satellite, version, scale, and offset come from the map's real observation.
- Effort labels remain judgments.

## Proposed next step

Owner review. Then commit authorization, the first Vercel deployment, decision 0004, and prototyping. No commit, push, or deployment was performed.
