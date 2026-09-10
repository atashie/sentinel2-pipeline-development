# Sentinel-2 facts and practices for per-water-body extraction, 2026-09-09

This document collects the Sentinel-2 facts that bear on extracting pixel values for small standing water bodies, and the practices that follow from them.
Every fact carries a claim status from the [assessment protocol](assessment-protocol.md). On 2026-09-09 every fact is `unverified`. The named test converts it to `documented` or `measured` during discovery.

The main input is the supplied geolocation report listed in [references/](references/README.md). It is AI-generated and cites primary ESA pages.
Its numbers appear here as unverified claims with the page to recheck. It covers geolocation only. Section 4 lists what it does not cover.

Practices are design guidance for this project. They cite the claims and assumptions they rest on. A practice is not a source claim and carries no status.

## 1. Tiling and pixel indexing

| # | Claim | Status | Test |
|---|---|---|---|
| G1 | Products are tiled on the fixed MGRS grid in UTM/WGS84. Each tile has a fixed origin and extent. A given tile, row, and column maps to the same ground location on every date. | unverified | Read the ESA Level-1C tiling grid page and the tiling KML. Confirm origin and extent for two tiles over the pilot set. |
| G2 | Tiles are about 110 km square and overlap their neighbours. One location can fall in two tiles and in two UTM zones. | unverified | Count tiles per pilot polygon from the tiling KML. |
| G3 | Bands come at 10 m (B2, B3, B4, B8), 20 m (B5, B6, B7, B8A, B11, B12), and 60 m (B1, B9, B10). Level-2A omits B10. The 20 m and 60 m grids nest inside the 10 m grid. | unverified | Read the ESA MSI overview and Level-2A product pages. Inspect one product's band geotransforms. |
| G4 | Level-2A shares the Level-1C grid. Atmospheric correction changes values, not geometry. | unverified | Compare geotransforms of an L1C and an L2A product for the same tile and date. |

- **Practice P1.** Rasterize each water-body polygon once per tile and per resolution into row and column index sets (assumption A9 in [assumptions.md](assumptions.md)). Store the tile id, the resolution, the index set, and the polygon version. Reuse it for every date. Re-rasterize when the polygon changes.
- **Practice P2.** Where a polygon falls in more than one tile, choose one tile per water body by a recorded rule, or keep all and deduplicate by sensing time. Record the choice.
- **Practice P3.** Extract each band at its native resolution. Do not resample 20 m or 60 m bands to 10 m for storage. A common grid is a documented derivation, not stored data.

## 2. Geolocation and multi-temporal registration

| # | Claim | Status | Test |
|---|---|---|---|
| G5 | Absolute geolocation is better than 6 m at 95 percent for L1C and L2A after geometric refinement. | unverified | Recheck the ESA geometric refinement announcement and the latest Data Quality Report. |
| G6 | Multi-temporal registration is better than 5 m at 95 percent between products on the same relative orbit, or 0.3 pixel at 2 sigma for 10 m bands. | unverified | Same pages. |
| G7 | Geometric refinement with the Global Reference Image entered operations in August 2021. Before it, multi-temporal error often exceeded 12 m. | unverified | Same pages plus a 2021 Data Quality Report. |
| G8 | Collection 1 reprocessing reprocessed the older archive under a newer baseline. Whether it applied refinement to 2015 to 2021 products is unknown here. | unverified | Read the Collection 1 L1C and L2A pages. Check the refinement flag in reprocessed product metadata over the pilot set. |
| G9 | Refinement fails where ground control points cannot be extracted. Cloud, large water surfaces, and isolated islands are cited causes. Such products keep the unrefined sensor-model geometry. | unverified | Find the metadata field that records refinement status. Count unrefined scenes over the pilot set by year. |
| G10 | Residual misregistration grows with terrain slope and DEM error. Flat terrain is sub-pixel. Steep terrain can reach 0.5 to 1 pixel at 10 m. | unverified | Literature recheck. Measure shoreline stability over a flat and a mountainous pilot reservoir. |

- **Practice P4.** Record the processing baseline and, when available, the refinement status with every extracted value. The 2017 and 2021 history scenarios differ in registration quality (assumption A10).
- **Practice P5.** Do not apply image-to-image co-registration in the ingestion store. It changes values and needs a reference date. Record misregistration as a quality attribute. A consumer that needs pixel-level alignment can apply it downstream.
- **Practice P6.** Report, for every water body and resolution, the count of interior pixels and the count of shoreline pixels. A body 10 m across (assumption A7) has zero interior pixels at 20 m. The consumer needs the counts to weigh the values.
- **Practice P7.** Where a body is large enough, flag shoreline pixels, one pixel in from the mask edge, so the consumer can exclude mixed pixels. Do not drop them in storage.

## 3. Radiometry and product versions

| # | Claim | Status | Test |
|---|---|---|---|
| R1 | Level-2A stores reflectance as integers with a quantification value. From processing baseline 04.00 an additive offset applies. Reflectance = (DN + offset) / quantification. | unverified | Read the ESA processing baseline page. Read the product metadata of one pre-04.00 and one post-04.00 product. |
| R2 | Each product records its processing baseline in its name and metadata. Reprocessed products of the same scene exist beside the originals. | unverified | List products for one tile and date on the chosen route. |
| R3 | Level-2A is produced by Sen2Cor, a land-oriented atmospheric correction. Its accuracy over inland water is not part of the ESA validation. | unverified | Read the Level-2A algorithm page and the Data Quality Report validation section. Search for inland-water validation. |

- **Practice P8.** Read offset and quantification from product metadata for every product. Store DN, offset, and quantification, or store scaled reflectance with the baseline. Never hard-code the offset.
- **Practice P9.** Key stored values by tile, sensing time, processing baseline, and product id. Keep reprocessed products as new revisions. Never overwrite.
- **Practice P10.** Serve Level-2A values as delivered (assumption A1). Whether Level-1C plus a water-specific correction belongs in the store is a discovery question, not a practice.

## 4. Quality layers and water-specific interference

The supplied report does not cover this section. Every claim comes from the implementer's prior knowledge and needs a source.

| # | Claim | Status | Test |
|---|---|---|---|
| Q1 | Level-2A carries a scene classification layer at 20 m and 60 m. Its classes include water, cloud shadow, dark area, cloud probability tiers, snow and ice, and unclassified. | unverified | Read the Level-2A product page. Inspect the layer for one product. |
| Q2 | Level-2A carries cloud probability and snow probability layers. | unverified | Same page. Inspect one product. |
| Q3 | Level-1C carries quality masks for detector footprint, defective pixels, saturation, and technical quality. Their format changed across baselines from vector to raster. | unverified | Read the Level-1C product page. Inspect masks for one old and one new product. |
| Q4 | The scene classification misclassifies dark or turbid water as cloud shadow, dark area, or cloud, and misses thin cloud over water. | unverified | Compare classes with a public water mask over the pilot set for one year. |
| Q5 | No Level-2A layer flags sun glint over water. | unverified | Read the Level-2A product page. Literature recheck for glint detection from delivered bands. |
| Q6 | Adjacency effects from bright land raise the apparent reflectance of small water bodies. The effect is strongest within a few hundred metres of shore. | unverified | Literature recheck. Compare interior and shoreline values on the pilot set. |
| Q7 | Sentinel-2A and 2B together revisit the equator every five days. Higher latitudes see more frequent overlap. A third satellite joined the constellation. | unverified | Read the ESA mission overview page. Count scenes per pilot tile per month. |

- **Practice P11.** Store every quality layer that a route delivers, at native resolution, keyed like the bands. Derive the quality flags of assumption A2 from these layers plus documented tests. Record the derivation version.
- **Practice P12.** Never drop a pixel because of a flag. Store the value and the flag. The consumer decides.
- **Practice P13.** Treat the scene classification water class as a hint, not as the water mask. The polygon defines the water body (assumption A9).

## 5. Open questions for discovery

- Which route delivers which quality layers, and in what format?
- Does any route deliver a cloud mask other than the scene classification, for example a machine-learning cloud probability?
- Which routes carry Collection 1 reprocessed products, and how far back does Level-2A coverage go on each?
- Is glint detectable from the delivered bands alone at 10 m ponds?
- Does refinement status appear in product metadata on every route?
- Does any route serve raw pixels through a server-side extraction, or only aggregates?

## 6. Pages to recheck

The supplied report cites these page titles. Locate each on the named domain during discovery and record its URL and access date in the inventory sources.

| Page title | Domain | Claims |
|---|---|---|
| Sentinel-2 Level-1C product tiling grid released | sentinel.esa.int | G1, G2 |
| User Guides, Sentinel-2 MSI, Level-1C Product and Level-2A Product | sentinel.esa.int | G3, G4, Q1, Q2, Q3 |
| Forthcoming deployment of the Copernicus Sentinel-2 products geometric refinement | sentinels.copernicus.eu | G5, G6, G7 |
| Access to the Copernicus Sentinel-2 Global Reference Image | sentinel.esa.int | G7, G9 |
| Collection 1 Level-1C and Collection 1 Level-2A | sentinel.esa.int | G8 |
| Data Quality Report Sentinel-2 L1C MSI, 2023 to 2025 issues | sentiwiki.copernicus.eu | G5, G6, G8 |
| S2 Processing and S2 Products | sentiwiki.copernicus.eu | G9, R1, R2, R3 |
| Level 2A Data Quality Report | sentinel.esa.int | R3 |
