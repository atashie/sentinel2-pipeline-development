# Archive lineage and pull cost recorded, 2026-09-11

Implementer: Claude Code (AI coding agent), directed by the repository owner. Scope: the owner's questions of 2026-09-11 about the two Earth Search collections. They were answered from checked sources and one catalog probe. The answers were recorded in their canonical homes and carried onto the Discovery page.

## What the owner asked

- Is the older collection the official AWS dataset, and the newer one Element 84's?
- Does the newer collection hold anything the older lacks? Why a second bucket?
- How easy and how computationally costly is pulling from each, and who pays?

## What was found

Both Earth Search collections are Element 84's GeoTIFF conversions of the same ESA product. The ESA-format copy on AWS is the JPEG 2000 bucket whose readme Sinergise wrote. The three sit in a chain. ESA makes the product. The JPEG 2000 files land in AWS Frankfurt within hours of release. Element 84 converts them twice into two Oregon buckets and catalogs both.

One expectation was wrong. The registry entry for the JPEG 2000 dataset is also managed by Element 84, not Sinergise. No page read names the owner of that bucket. The repository keeps its short name, the Sinergise bucket, for the readme's author.

| Fact | Status | Home |
|---|---|---|
| The registry names Element 84 as managing the GeoTIFF dataset and lists both buckets, neither requester pays | documented | claim `cl-ar-earth-search-cogs-operator` |
| Collection 1 GeoTIFFs are generated from the ESA/Sinergise JPEG 2000 files, and each collection's bucket | documented | claim `cl-ar-earth-search-cogs-source_dataset` |
| Collection 1 is intended to replace the older collection and holds baseline 05.00 and later only | documented | claim `cl-ar-earth-search-cogs-reprocessed_products`, unchanged |
| The registry entry for the JPEG 2000 dataset is managed by Element 84. The page links Sinergise's readmes and names no bucket owner | documented | claim `cl-ar-aws-requester-pays-operator` |
| The JPEG 2000 bucket holds Copernicus Sentinel-2 data per tile in the original product layout | documented | claim `cl-ar-aws-requester-pays-source_dataset` |
| One product, tile 17SKU on 2025-10-15, is the same in both collections: same product file, generation time, 22 shared assets, grid, scale, and offset | measured, not independently checked | probe PR-08, [record](../assessment-checks/probes-2026-09-11.json) |
| Collection 1 adds a preview and per-file checksums and sizes. The older collection adds 16 JPEG 2000 links, a sequence suffix, and a per-item offset flag that contradicts the asset offset | measured, not independently checked | probe PR-08 |
| Both collections ingested the 2025-10-15 acquisition the same day, so the replacement has not happened | measured, not independently checked | probe PR-08 |
| Pulling from either GeoTIFF bucket costs the same per read. The older one needs a version check and an offset check per item. The JPEG 2000 bucket is in Frankfurt, its Level-1C bucket is requester pays, and its Level-2A pages disagree | finding from existing claims | finding F-22 |

Why Element 84 chose a new bucket rather than new keys in the old one is not documented anywhere read. The page does not speculate. Pixels were not compared between the two copies.

## What changed

- `docs/assessment-checks/access-route-research.json` and `access-route-checks.json`: four draft claims researched and checked by separate agents. See Checks.
- `docs/options-inventory.json`: fields `operator` and `source_dataset` for access routes, probe PR-08, findings F-22 on pull cost and F-21 on lineage, and the collated claims.
- `docs/assessment-checks/probes-2026-09-11.json`: the item comparison and documentation reads.
- `docs/s2-best-practices.md`: the open question on which routes carry Collection 1 products now carries its Earth Search answer.
- `docs/measurements.md`: two limits added, pixel equality between copies and continued ingestion.
- `docs/gap-survey-plan.md`: the fallback collection row names the operator and bucket.
- `CLAUDE.md`: a gotcha on the lineage and requester-pays status. `docs/work-plan.md`: this step.
- `tools/s2-options.template.html`: section 02 rewritten. A five-step lineage figure replaces the three-step route. A three-column table compares the copies on operator, bucket, region, payer, format, versions, holdings, and use. Two cards report the one-item comparison. Three cards give the pull effort as low, medium, and high. The coverage strip and the two-plan table stay, reworded to "GeoTIFF copies".
- `tests/test_presentation.py`: the page must name the three buckets, both operators, and requester-pays status.

The JPEG 2000 bucket appears on the page as the origin of the other two and as context. It is not offered as an option. The inventory issue about its payer status stays off the page, as the test requires.

## Checks

| Check | Result |
|---|---|
| Research agent, opus, 2026-09-11 | Seven draft records: four claims and three second-source records, all with verbatim quotes and locators. One new source, the registry YAML for the JPEG 2000 dataset |
| Checking agent, sonnet, 2026-09-11 | Every source re-fetched. All seven records confirmed. No correction. Two limitations added: registry management is not bucket ownership, and the Sinergise readme names no operator |
| `uv run python tools/collate_checks.py` | 326 claims, 121 sources, 0 gaps. The seven claims bound as documented and fill `operator` and `source_dataset` for both AWS candidates |
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. 43 files formatted |
| `uv run pytest` | 63 passed, including the new archive-naming test |
| The three `--check` tools | Inventory, page, and report all match their inputs |
| Headless Chromium, 1440 px and 390 px | The lineage figure, the three-copy table, the comparison cards, the pull cards, the coverage strip, and the plans table render. The table scrolls inside its own container on the phone |
| Sentence audit of section 02 and this record | No sentence over 25 words, no semicolon, no "should" |

## Limits

- One tile and one date were compared. The catalog comparison shows metadata equality, not pixel equality.
- The pull-effort labels are reasoned from documented claims, not measured. Prototyping measures them.
- The page says JPEG 2000 files are not laid out for small windowed reads over the network. That rests on claim R6 and the researcher's note on the requester-pays route. It is not measured.
- Assumption A13 still says "the older collection's JPEG 2000 assets as fallback". The survey and the owner's direction point at the older collection's GeoTIFF assets. The wording waits on decision 0004.

## Dispositions

| Prior item | Disposition |
|---|---|
| Owner review of the 2026-09-11 revision, pixel-size figure | Fixed the same day, recorded in the [revision record](2026-09-11-presentation-revision.md) |
| Owner's archive questions | Answered here and on the page |

## Proposed next step

Owner review of section 02. Then commit authorization, the first Vercel deployment, decision 0004 including the A13 wording, and prototyping. No commit, push, or deployment was performed.
