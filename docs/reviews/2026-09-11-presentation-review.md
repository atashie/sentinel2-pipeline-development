# Claude Code review of the Discovery presentation, 2026-09-11

Reviewer: Claude Code (AI coding agent), directed by the repository owner. Reviewed work: Codex's [presentation revision](2026-09-11-discovery-presentation.md) of the same date.
Baseline: commit `943bb1b` plus the uncommitted changes of 2026-09-10 and 2026-09-11. Nothing was committed. Fixes land separately and cite this review.

## The owner's direction on 2026-09-11

The owner answered ten alignment questions before this review. The answers are the specification for the next revision.

1. **Why Sentinel-2.** Four reasons confirmed. Pixel size for small water bodies. Five-day revisit for the pair. Red-edge bands for chlorophyll and cyanobacteria retrievals. Archive currency. Add one more: one instrument design across the record, where Landsat missions differ in sensors and quality.
2. **Landsat's role.** The other major public option. The page mentions it once, chooses Sentinel-2, and moves on. It is not used for now.
3. **The two archives.** Present two plans as a tradeoff. Collection 1 alone is the simpler workflow with a gappier, shorter record. Adding the older archive gives a more consistent record at the cost of complexity. Omit the JPEG 2000 bucket.
4. **Where things go wrong.** Consolidate the thirty internal items into six to ten categories. Smaller items are bullets under a category, never a category of their own.
5. **Illustrated decisions.** AWS and Earth Search as the route. Collection 1 first with the older archive as fallback. Raw bands and flags stored, no derived index. Three pixel classes per resolution. Never mosaic, every tile kept with a primary marker. Key by tile, time, and processing version. Start at 2021 with a measured survey.
6. **Processing steps.** Four effort labels only: low, medium, high, depends. Timings, costs, and technical comparison belong to the Prototyping tab later.
7. **Maps.** One site is enough for Discovery. More examples come under Prototyping. The streaks in the index maps need an explanation.
8. **Other tabs.** Prototyping, Integration Specs, and Tradeoffs & Issues stay placeholders. Each gets its own session.
9. **Delivery.** Vercel, following the weather assessment repository's static `docs/vercel.json` pattern.
10. **Register.** Conversational text for now. The evidence-heavy view can join Tradeoffs & Issues later.

## What was checked

| Check | Outcome |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass, 40 files formatted |
| `uv run pytest -q` | 57 passed |
| `collate_checks.py --check`, `render_options.py --check`, `gap_report.py --check` | All three pass |
| Headless Chromium render, Playwright build 1234, 1440 px wide | Layout, diagrams, and tabs render as designed. Mobile widths not rechecked |
| Prose audit of the rendered text | No sentence over 25 words outside navigation strings. No "should", no semicolon, no internal ID, no person's name |
| Survey numbers on the page against finding GS-10 of the [report](2026-09-10-gap-survey-report.json) | 5,022 missing, 3,840 fallback sets, 1,177 uncovered, 5 other format. All match |
| Relative links and external requests | Every link resolves. The page requests nothing external |
| The six facts in the [sources record](../assessment-checks/discovery-presentation-sources.json), re-read on 2026-09-11 | All hold against their pages |
| Map arrays under `data/discovery-map/`, calibration from the [provenance record](../assets/discovery/provenance.json) | Index gaps explained, finding 6 |

The download of 2026-09-11 was authorized by the owner. It is recorded with product, asset URLs, bytes, region, and payer. No requester-pays access occurred.

## Findings

Severity: **must change** blocks colleague use, **improve** is required by the owner's direction, **note** is housekeeping.

### 1. The sensor rationale is incomplete and Landsat is framed as complementary. Must change

The page gives one reason for Sentinel-2, pixel size, labeled provisional. Landsat is "a complementary option". The owner's direction supplies the full rationale.
Five facts were fetched from primary pages on 2026-09-11 and sent to an independent checking agent. Four were confirmed and one corrected in wording. The verdicts are in the [sources record](../assessment-checks/discovery-presentation-sources.json).

- Sentinel-2A launched in 2015, 2B in 2017, 2C in 2024. Each carries the same single instrument, with four bands at 10 m, six at 20 m, three at 60 m. [SentiWiki mission page](https://sentiwiki.copernicus.eu/web/s2-mission).
- Landsat sensors changed across missions. MSS at 60 m flew on Landsat 1 to 5, and TM at 30 m on 4 and 5. ETM+ flew on 7, and OLI with TIRS on 8 and 9. Band designations differ between sensors. [USGS band designations](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites).
- Landsat 6 launched on 1993-10-05 and did not achieve orbit. [USGS Landsat 6](https://www.usgs.gov/landsat-missions/landsat-6).
- Landsat 7's Scan Line Corrector failed on 2003-05-31. Later scenes keep about 78 percent of their pixels. Science imaging was suspended on 2024-01-19. [USGS Landsat 7](https://www.usgs.gov/landsat-missions/landsat-7). This is the problematic mission the owner recalled.
- NASA's HLS S30 product is derived from Sentinel-2 at 30 m, on the same MGRS grid as its Landsat product, so the two stack. [NASA Earthdata HLSS30 v2.0](https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-2.0).

The owner has only used Sentinel-2 at 30 m, as supplied by geospatial colleagues. The likely product is HLS S30 or a similar Landsat-aligned resample. The 10 m bands are delivered at 10 m, and nothing in the archive requires coarsening them.
A 30 m product is a different product: nine times fewer pixels, a different atmospheric correction, and adjustments to match Landsat. The page must say this once. Prototyping must ask the modeling colleagues which product the model was built on.

One nuance to keep. The instrument design is constant, but the ground processing is not. Processing baselines change and are tracked separately, finding 4 of [measurements.md](../measurements.md).

Required change: rewrite section 01 in this order. What the model retrieves and which bands carry that signal. How Sentinel-2 and Landsat differ on pixel size, revisit, red-edge bands, record consistency, and currency. What Landsat offers that Sentinel-2 lacks, thermal bands and a record from 1972. The choice: Sentinel-2 now, Landsat parked. The 30 m note. Relabel the Landsat card "the other public option, not used for now".

### 2. The archive section presents the fallback as the plan, not as a tradeoff. Must change

Section 02 says "our intended fallback". The owner wants two plans side by side. The measured inputs are finding GS-10 of the report. Collection 1 holds 384 of 5,406 reference acquisitions in the surveyed tile-months. The older archive lists complete GeoTIFF sets for 3,840 of the 5,022 missing.
Plan A, Collection 1 alone: one archive, one convention, and a record that is nearly empty from January to November 2022. Plan B, both archives: most of 2022 recovered, plus a check of the offset state and processing version before every fallback read. The JPEG 2000 bucket is already absent from the page. Keep it absent.

Required change: a two-column comparison with the same rows for both plans. The rows are what you get, what you give up, what must be checked, and what remains open. The coverage strip of finding 4 belongs beside it.

### 3. The six risk categories have no sub-bullets. Improve

Section 03 has six well-chosen categories. The thirty internal items are absent, so a colleague cannot see what each category contains. The owner wants six to ten categories with smaller items as bullets. Proposed mapping, internal IDs for the implementer only:

| Category on the page | Internal items as bullets |
|---|---|
| Land leaks into a water pixel | I-03, I-15, I-10, I-09, I-28, I-02 |
| Clear-looking water can be misleading | I-01, I-12, I-14, I-13, I-11, I-26 |
| The same lake can arrive twice | I-30, I-04 |
| A processing change can look like a trend | I-05, I-06, I-29, I-16, I-17, I-19 |
| A sharper grid can imply false detail | I-07 |
| A missing date can be misread | I-08, I-24, I-25, I-27 |

I-20, I-21, I-22, and I-23 are about cost and daily operation. They belong as bullets in section 04, under what drives cost. I-18 concerns the JPEG 2000 bucket and stays off the page.
The inventory already carries a `plain` and a `why` line per item. The bullets can be written from those lines, so the page and the inventory say the same thing.

### 4. Four of the seven decisions are illustrated. Improve

Present: pixel size, archive fallback, shoreline classes, tile overlap. Missing: the route from catalog to bucket to store, and what one stored record holds. Also missing: the keying of reprocessed products, and the 2021 start with its survey.
For the last one, the renderer can draw a coverage strip per year from the report's monthly counts, so the illustration stays measured. The others are schematics.

### 5. Effort labels do not use the four categories. Improve

The five steps carry "low to moderate", "moderate, reusable", "main transfer and decoding cost", "moderate, method dependent", and "varies with layout and volume". Replace with low, medium, high, or depends, one per step, with reuse noted separately. The four prototyping questions at the end of the section are right and stay.

### 6. The index maps drop a fifth of the water pixels, in streaks. Must change

The owner asked why the NDWI and NDVI views show long streaks of missing water. The cause is in the map builder, not in the data.

- Near-infrared reflectance over clear water is close to zero. The stored value is scaled by 0.0001 and offset by −0.1, per the asset metadata in the provenance record. The median stored near-infrared value over water pixels is 1,012, against an offset of 1,000.
- After the offset, 19.6 percent of the pixels the scene classification calls water have a near-infrared reflectance below zero. Red and green never go below zero.
- The builder excludes any negative input from an index. Those pixels turn gray. The exclusion follows small along-track variations in the noise floor, so it appears as vertical streaks over open water.
- The provenance record shows the effect: valid fraction 0.978 for the band views and 0.908 for the two index views.

Required change in [build_discovery_maps.py](../../tools/build_discovery_maps.py): keep the scene-classification and no-data screening, and drop the non-negative input rule. Keep the denominator rule and clip each index to the legend range. With that rule 99.9 percent of water pixels receive an index value. Rebuild from the cached arrays, no download needed.
Add one caption sentence: clear water is nearly black in near-infrared, so a water index saturates there and shows the sensor's noise floor. The store is unaffected. It keeps raw values, negative ones included, under practice P8 of [s2-best-practices.md](../s2-best-practices.md).

Two smaller points. The pale patches in the true-color view are scene-classification class 2, dark area pixels, at shorelines and on water. They are 2.2 percent of the crop. One caption sentence explains them. The valid fraction per view already sits in the provenance record and can be shown under each map.

### 7. Delivery through Vercel needs a configuration and a hosting note. Improve

The weather repository serves its `docs/` directory as a static site with a rewrite from `/` to the page. The same works here. Add `docs/vercel.json` with framework null, empty install and build commands, output directory `.`, and a rewrite from `/` to `/s2-options.html`. Add a short hosting note with the deployment steps.
The page already requests nothing external and uses relative asset paths, so it deploys unchanged. Two consequences. Everything under `docs/` becomes readable on the web, including the inventory, the reviews, and the report. `docs/archive/` is ignored by git and is not deployed. The README's "open the HTML directly from disk" sentence changes to the deployment URL once one exists.

### 8. Documentation housekeeping. Note

- The 2026-09-10 HTML rebuild review describes a superseded page. Move it to `docs/archive/` under the owner's quarantine rule and drop its index row. Collapse the step 3c block in [work-plan.md](../work-plan.md) to one line.
- The inventory's `plain`, `why`, and `themes` fields are no longer read by the renderer. Finding 3 gives them a use. Otherwise mark them internal in [assessment-data-format.md](../assessment-data-format.md).
- The sources record lists the missing sensor emphasis as a limitation. The owner supplied it on 2026-09-11. Update the limitation when the facts above enter the page.
- The template's hash handling calls `history.replaceState`. Wrap it in a try block so a browser that refuses it on a `file:` origin keeps working.

### 9. What Codex did well. Note

The structure matches the owner's four tabs. The prose is plain and carries no internal register. The four diagrams explain more than the tables they replaced. The download was bounded, authorized, and recorded to the byte. The sources record separates research from checking. The tests keep external requests and internal IDs out of the page.

## Dispositions of Codex's deferred items

| Codex item | Disposition |
|---|---|
| Sensor-comparison emphasis awaits the owner | Supplied on 2026-09-11. Finding 1 |
| Effort labels are hypotheses, not timings | Accepted. The owner keeps qualitative labels for Discovery, finding 5 |
| Archive consistency and fallback policy remain prototype questions | Accepted. Discovery presents the tradeoff, finding 2. The fill-policy decision stays open |

## Proposed next step

One revision of the presentation that applies findings 1 to 8. Then owner review. No commit or push without the owner's authorization. The owner decides whether Codex or Claude Code implements the revision.
