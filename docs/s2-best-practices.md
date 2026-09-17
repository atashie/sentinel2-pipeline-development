# Sentinel-2 facts and practices for per-water-body extraction, 2026-09-09

This document collects the Sentinel-2 facts that bear on extracting pixel values for small standing water bodies, and the practices that follow from them.
Every fact carries a claim status from [CLAUDE.md](../CLAUDE.md). A `documented` fact cites a source in section 7 and a verdict in the [recheck record](assessment-checks/best-practices-recheck.json).
Section 6 lists the facts that remain `unverified` after the recheck, with the test each still needs.

The first draft came from the supplied geolocation report listed in [references/](references/README.md). The recheck on 2026-09-09 read the primary pages, confirmed nine claims, corrected ten, and contradicted one.
The report had conflated the Global Reference Image accuracy with product accuracy. It missed the two-stage 2021 rollout. The first draft's own adjacency claim, which did not come from the report, gave a distance the cited study does not support.

Practices are design guidance for this project. They cite the claims and assumptions they rest on. A practice is not a source claim and carries no status.
Practices are provisional until selected jointly. Review each when the relevant assessment part develops. [Decision 0002](decisions/0002-aws-source-pixel-classes-tile-provenance.md) selects P1, P2, P6, and P7 as written below.
The ingestion and processing issues these claims raise are registered in the inventory and rendered first in the [Discovery tab](s2-options.html#issues).

## 1. Tiling and pixel indexing

| # | Claim | Status | Source |
|---|---|---|---|
| G1 | Products are tiled on the MGRS-derived UTM grid. Each tile is fixed by its UTM code, the anchorage point of its upper-left pixel, its pixel size, and its size in lines and columns. A given tile, row, and column resolves to the same ground coordinate on every date. | documented | S4 |
| G2 | Tiles are 110 km by 110 km ortho-images on a 100 km grid step, so neighbors overlap. The tiling ensures overlap at UTM zone borders, so one location can fall in two tiles and two zones. | documented | S1, S4 |
| G3 | Bands come at 10 m (B2, B3, B4, B8), 20 m (B5, B6, B7, B8A, B11, B12), and 60 m (B1, B9, B10). Level-2A omits B10. All resolutions share the same upper-left corner, so the coarser grids nest inside the 10 m grid. | documented | S3, S1, S4 |
| G4 | Level-2A uses the same tiling, encoding, and filling structure as Level-1C and inherits its geometric performance. Atmospheric correction changes values, not geometry. | documented | S4, S8 |
| G11 | Level-2A is processed per tile. In the overlap between adjacent tiles the scene classification can differ for a few pixels, and aerosol optical depth and surface reflectance are generally different. | documented | S1 |

- **Practice P1.** Rasterize each water-body polygon once per tile and per resolution (assumption A9 in [assumptions.md](assumptions.md)). For every pixel within the near-land distance, store the coverage fraction, the edge distance, and the pixel class: interior, shoreline, or near-land (assumptions A20 and A21). Store the tile id, the resolution, the polygon version, and the tile role. Reuse it for every date. Re-rasterize when the polygon changes.
- **Practice P2.** Every record carries its tile and a tile role marker, primary or overlap (decision 0002). Where a polygon falls in more than one tile, keep every tile as a separate keyed record and name one primary by the provisional rule of assumption A22. Never average values across tiles for the same ground pixel and date (G11). **MAJOR CONCERN: cross-tile mosaicking must be thoroughly investigated before any stitched value is trusted, issue I-30 and decision 0003. The store never mosaics.**
- **Practice P3.** Extract each band at its native resolution. Do not resample 20 m or 60 m bands to 10 m for storage. A common grid is a documented derivation, not stored data.

## 2. Geolocation and multi-temporal registration

| # | Claim | Status | Source |
|---|---|---|---|
| G5 | Absolute geolocation of refined Level-1C products is validated as less than 10 m. The June 2026 Data Quality Report measures a mean circular error at 95 percent of 6.08 m for Sentinel-2A, 6.12 m for Sentinel-2B, and 6.41 m for Sentinel-2C. The 6 m figure describes the Global Reference Image, not the products. | documented | S5, S7 |
| G6 | Multi-temporal registration of refined products is better than 4.5 m at 95 percent confidence, on the same or different repeat orbits. The mission requirement is 0.3 spatial sampling distance at 2 sigma, which is 3 m at 10 m, 6 m at 20 m, and 18 m at 60 m. Across refined and unrefined products together the June 2026 report measures less than 6 m. | documented | S5 |
| G7 | Geometric refinement against the Global Reference Image entered operations over the Euro-Africa region on 30 March 2021 and worldwide on 23 August 2021. Original processing of a 2017 history therefore spans three registration regimes. Collection 1 reprocessing (G8) removes that split where refinement succeeded. | documented | S2, S7 |
| G8 | Collection 1 reprocessed the whole archive from 4 July 2015 to 13 December 2023. It used baseline 05.00 for acquisitions to 31 December 2021, 05.10 from 1 January 2022, and 05.11 for a few products across the whole range. The improvements up to baseline 04.00, including geometric refining, were generalized to the archive. | documented | S2 |
| G9 | Refinement is a candidate for every observation that intersects the Global Reference Image. It is disabled when quality criteria fail, the fallback case, and absent where no reference image covers the datastrip, the unrefined case. Cloud, sea cover, short passes over isolated islands, Svalbard, high-latitude islands, and Antarctica are cited causes. Such products keep the sensor-model geometry. | documented | S7, S5, S2 |
| G12 | The refining status is reported in the XML tag `Image_Refining` of the Datastrip metadata, with attribute `flag` set to `REFINED` or `NOT_REFINED`. | documented | S7, S4 |
| G10 | One component of residual misregistration is a lateral off-nadir offset caused by the difference between the orthorectification DEM and the true surface. It grows with DEM error and with distance from nadir. With unchanged elevation error and repeat viewing geometry, that component can cancel between same-orbit images. Different tracks can introduce a relative displacement. Other registration errors remain. Scope rechecked on 2026-09-11 in the [presentation source checks](assessment-checks/discovery-presentation-sources.json). | documented | S9 |

- **Practice P4.** Record the processing baseline, the relative orbit, and the platform with every extracted value. Record the refinement status from the Datastrip metadata where the route exposes it, and null where it does not (G12). Distinguish acquisition date from processing baseline. Original processing of a 2017 history spans three registration regimes, and a Collection 1 archive carries refined geometry for the same acquisitions where refinement succeeded (G7, G8, assumption A10).
- **Practice P5.** Do not apply image-to-image co-registration in the ingestion store. It changes values and needs a reference date. A consumer can filter to one relative orbit to remove the DEM-related component of misregistration (G10). That removes one source of inconsistency, not all. A consumer that needs pixel-level alignment can apply co-registration downstream.
- **Practice P6.** Report, for every water body and resolution, the pixel count in each class: interior, shoreline, and near-land (assumption A20). A body 10 m across (assumption A7) has no interior pixel at any resolution. Its record is shoreline and near-land pixels only, and the consumer sees that from the counts.
- **Practice P7.** The shoreline class marks pixels mixed between land and water. The near-land class gives the consumer the surrounding land. Neither corrects adjacency, which can extend well beyond a shoreline buffer (Q6) and belongs to the modeling team, issue I-02. Store all three classes. Never drop a pixel for its class.

## 3. Radiometry and product versions

| # | Claim | Status | Source |
|---|---|---|---|
| R1 | From baseline 04.00, deployed on 25 January 2022, Level-2A digital numbers carry an additive offset `BOA_ADD_OFFSET` and Level-1C carry `RADIO_ADD_OFFSET`. Reflectance is (DN + offset) / quantification value. The current offset is -1000 for all bands. The quantification value is read from the product. Digital number 0 stays NO_DATA and is never run through the formula. | documented | S1, S6 |
| R2 | Each product records its baseline in its name, the `Nxxyy` field, and in its metadata. Reprocessed products do not always sit beside originals. The Copernicus Data Space Ecosystem removed Collection 0 products up to 13 December 2023 and keeps only baselines 05.00, 05.10, and 05.11. | documented | S1, S2 |
| R3 | Level-2A surface reflectance is validated at vegetation, arid, forest, and agricultural sites. No inland water site appears. The scene classification is validated as clear versus cloud on products with under 20 percent water pixels. | documented | S6 |
| R4 | A Level-2A product is about 800 MB per 110 km tile and is available within 8 hours of sensing. A Level-1C product is about 700 MB and available within 6 hours. | documented | S8 |
| R5 | Operational baselines: 05.10 from 13 December 2023, 05.11 from 23 July 2024, and 05.12 from 4 February 2026 under product specification 15.1. Baseline 05.13 with specification 15.2 is scheduled for 21 September 2026, announced and not yet operational. Reprocessing baselines for older acquisitions are separate: 05.00 to 2021 and 05.10 for 2022 to 2023, with 05.11 on a few products across the range. So the baseline is not a function of sensing date. | documented | S2, S13, S11, S14 |
| R6 | Baseline 05.12 introduces tile-part length markers in the JPEG 2000 images. The markers give the position and size of each JPEG 2000 tile, so decoders reach small regions more efficiently. They apply to Level-1C and Level-2A products under specification 15.1. | documented | S12, S11 |

- **Practice P8.** Read the conversion state from the delivered asset's metadata for every product. The offset is at `General_Info/Product_Image_Characteristics/BOA_ADD_OFFSET_VALUES_LIST/BOA_ADD_OFFSET` in the user product metadata (R1). Some routes applied the offset for some items and publish per-asset scale and offset for the remainder, recorded in the inventory field `offset_delivery`. ESA metadata and catalog metadata use different conventions, mapped in the [draft contract](data-contract.md). Store which source supplied the conversion beside the value. Treat DN 0 as no data. Never hard-code the offset.
- **Practice P9.** Key stored values by tile, sensing time, processing baseline, and product id. Keep reprocessed products as new revisions. Never overwrite. Upstream services can delete superseded products (R2). Retain ingested revisions locally without relying on indefinite source retention. Expect several baselines across any history, and treat each new operational baseline as a structural change to review (G8, R5, issue I-29). Measured on 2026-09-10 in [measurements.md](measurements.md): Both Earth Search collections contain acquisitions with multiple products. The older collection has more competing versions in the sample. Neither survey establishes a retention guarantee.
- **Practice P10.** Serve Level-2A values as delivered (assumption A1). Level-2A is not validated over inland water (R3). Whether Level-1C plus a water-specific correction belongs in the store is a discovery question, not a practice.

## 4. Quality layers and water-specific interference

| # | Claim | Status | Source |
|---|---|---|---|
| Q1 | Level-2A carries a scene classification layer produced at 20 m and resampled to 60 m by mode. Its twelve classes are 0 NO_DATA, 1 SATURATED_OR_DEFECTIVE, 2 CAST_SHADOWS, 3 CLOUD_SHADOWS, 4 VEGETATION, 5 NOT_VEGETATED, 6 WATER, 7 UNCLASSIFIED, 8 CLOUD_MEDIUM_PROBABILITY, 9 CLOUD_HIGH_PROBABILITY, 10 THIN_CIRRUS, and 11 SNOW or ICE. Class 2 was DARK_FEATURES until baseline 05.11 renamed it. | documented | S2 |
| Q2 | Level-2A carries cloud probability and snow probability layers at 20 m and 60 m. They are the two quality indicators of the scene classification algorithm. | documented | S1, S6, S2 |
| Q3 | Level-1C quality masks are `MSK_CLASSI` (opaque cloud, cirrus, snow and ice), `MSK_QUALIT` (lost and degraded packets, defective pixels, no data, partially corrected crosstalk, saturated pixels), and `MSK_DETFOO` (the twelve detector footprints). Before January 2022 the same content was split across six GML vector masks. | documented | S2, S1 |
| Q4 | ESA documents that dark areas are misclassified as cloud shadows, most often at high solar zenith angle, and that topographic shadows were misclassified as water before baseline 04.00. Semi-transparent clouds and cloud edges were under-detected before 04.00. Very low clouds and fog are omitted. ESA's own validation excludes water-dominated scenes. The behavior over small, dark, or turbid ponds is unmeasured. | documented | S1, S6 |
| Q5 | The documented Level-2A layers are aerosol optical thickness, water vapor, scene classification, cloud probability, snow probability, and the masks inherited from Level-1C. None flags sun glint. ESA documents glint as an image feature, an odd-even detector stripe over water, not as a flagged condition. This rests on an enumerated list, not on an explicit statement. | documented | S1 |
| Q6 | Adjacency effects from surrounding land bias water observations. One lake study found chlorophyll retrieval errors higher within 5 km of shore than beyond. That comparison of two distance groups does not isolate a radius for delivered Level-2A reflectance. Effects can extend well beyond a shoreline buffer, with magnitude depending on setting and processing. | documented | S10 |
| Q7 | The nominal constellation is two satellites five days apart in revisit. Since 21 January 2025 the pair is Sentinel-2B and Sentinel-2C. Sentinel-2C launched on 5 September 2024 and replaced Sentinel-2A. Since March 2025 Sentinel-2A runs an extension campaign that adds revisits over Europe and tropical Africa and South America. Adjacent-orbit overlap raises revisit further, under different viewing conditions. | documented | S3 |
| Q8 | Since Sen2Cor 2.10, Level-2A baseline 04.00 and later, the scene classification dilates cloud by 80 m, cloud shadow by 40 m, and snow by 20 m. Only clouds with probability above 65 percent and larger than three pixels are dilated. Cloud dilation is suppressed in shoreline regions and at soil and snow boundaries. Over urban areas only clouds above 1000 pixels are dilated. Conditions re-read from S2 on 2026-09-10. | documented | S2 |
| Q9 | The Level-2A no-data mask is common to all bands, computed at 20 m, and oversampled to 10 m. This can fill 10 m pixels at the swath edge with interpolated data and very low reflectance. ESA recommends filtering with the per-band `MSK_DETFOO` from the Level-2A `QI_DATA` folder. | documented | S1 |
| Q10 | The scene classification post-processing uses the DEM to clean pixels first classified as water, cloud shadow, or cloud medium probability, and reclassifies topographic shadow as cast shadow. The atmospheric correction uses water bodies as reference areas for aerosol retrieval. The auxiliary water map is a 150 m product. | documented | S2, S8 |
| Q11 | Products with a mean sun zenith angle above 70 degrees are processed with the angle clipped to 70 degrees, which under-corrects the atmosphere. ESA states their surface reflectance is not for quantitative analysis. The angle is in the granule metadata field `Mean_Sun_Angle/ZENITH_ANGLE`. | documented | S1 |

- **Practice P11.** Store every quality layer that a route delivers, at native resolution, keyed like the bands. Store scene classification codes, never names (Q1). Treat `MSK_DETFOO` as a required layer, not an optional one (Q9). Carry the product-level sun zenith angle (Q11). Derive the quality flags of assumption A2 from these layers plus documented tests. Record the derivation version.
- **Practice P12.** Never drop a pixel because of a flag. Store the value and the flag. The consumer decides. A qualifying cloud within 80 m can flag every pixel of a 10 m pond (Q8). The stored value is the only way to revisit that decision.
- **Practice P13.** Treat the scene classification water class as a hint, not as the water mask. It depends on a DEM and a 150 m water map that cannot resolve a 10 m pond (Q10). The polygon defines the water body (assumption A9).
- **Practice P14.** Derive the quality flags per resolution the layer was produced at. The 60 m scene classification is a mode resample of the 20 m layer, so a 10 m pond can sit under one 60 m class and several 20 m classes (Q1).

## 5. Open questions for discovery

Each question below is tracked with its status in the issue register in the [Discovery tab](s2-options.html#issues).

- Which route delivers which quality layers, and in what format? Does any route expose the Datastrip metadata that carries `Image_Refining` (G12)?
- Does any route deliver a cloud mask other than the scene classification, for example a machine-learning cloud probability?
- Which routes carry Collection 1 reprocessed products, and which still carry the Collection 0 originals the primary service deleted (R2)? Answered for Earth Search on 2026-09-11: the collections can carry conversions of the same ESA product. Collection 1 holds baseline 05.00 and later, including operational originals. Both contain multiple-product acquisitions. The sample establishes neither complete version histories nor future retention. Measurement finding 7 and probe PR-08 in the inventory.
- Is glint detectable from the delivered bands alone at 10 m ponds? The ESA product carries no flag (Q5).
- Does adjacency correction belong to the consumer, or does any route offer a water-specific correction? The store serves delivered values (assumption A1).
- Does any route serve raw pixels through a server-side extraction, or only aggregates?

## 6. Still unverified

| Item | Status | Test |
|---|---|---|
| The pre-refinement multi-temporal error figure the supplied report gave as 12 m. | unverified | Locate a 2020 or early 2021 Data Quality Report. The current SentiWiki documents page lists reports from late 2025 onward only. |
| The 0.5 to 1 pixel steep-terrain misregistration figure the supplied report gave. | unverified | Read the European Journal of Remote Sensing study on DEM influence, doi 10.1080/22797254.2018.1478676. The publisher domain returned 403 on 2026-09-09. |
| Per-class accuracy of the scene classification water class over small inland water bodies. | unverified | Compare classes with a public water mask over the pilot set for one year. No ESA validation covers it (R3, Q4). |
| The specific adjacency range for inland water from the aquatic literature. | unverified | Read doi 10.3390/rs14081829 and doi 10.1016/j.rse.2019.03.018. Both publisher domains returned 403 on 2026-09-09. |
| Every metadata field name above, as observed in a real product. | unverified | Open one Level-1C and one Level-2A product per baseline on the chosen route and read `Image_Refining`, the offset list, and the masks. No product was opened in discovery. |

## 7. Sources

All pages were read on 2026-09-09, except S11 to S14 on 2026-09-10. The Q8 dilation conditions were re-read from S2 on 2026-09-10. The domain `sentinel.esa.int` did not resolve from the research environment, so its user guides were read from their SentiWiki and Sentinel Online equivalents. Data Quality Report and Product Specification Document links carry query strings that ESA may change. The stable entry point is the [SentiWiki S2 documents page](https://sentiwiki.copernicus.eu/web/s2-documents).

| ID | Source |
|---|---|
| S1 | [S2 Products, SentiWiki](https://sentiwiki.copernicus.eu/web/s2-products) |
| S2 | [S2 Processing, SentiWiki](https://sentiwiki.copernicus.eu/web/s2-processing) |
| S3 | [S2 Mission, SentiWiki](https://sentiwiki.copernicus.eu/web/s2-mission) |
| S4 | [Sentinel-2 Products Specification Document, issue 15.1, 2025-12-05](https://sentiwiki.copernicus.eu/__attachments/a_c32842b6d2a9d74e8c0419c1daee9034103ec69daf2e5b0b377815180e360620/S2-PDGS-CS-DI-PSD-V15.1.pdf) |
| S5 | [Data Quality Report, Sentinel-2 L1C MSI, June 2026, issue 124.0](https://sentiwiki.copernicus.eu/__attachments/a_c1c656cd00b820f1842def8fc114a177b31002188d9ba50a08d98b909c9e5989/OMPC.CS.DQR.001.05-2026%20-%20i124r0%20-%20MSI%20L1C%20DQR%20June%202026.pdf) |
| S6 | [Data Quality Report, Sentinel-2 MSI L2A, May 2026, issue 97.0](https://sentiwiki.copernicus.eu/__attachments/a_678c1e7e8cff6c024154c784d1257e3fdd6a8d37f0fd3dce736adfc8d5c63dab/OMPC.CS.DQR.002.04-2026-i97r0-MSI-L2A-DQR-May-2026.pdf) |
| S7 | [Forthcoming deployment of the Copernicus Sentinel-2 products geometric refinement, Sentinel Online, 2021-03-22](https://sentinels.copernicus.eu/-/forthcoming-deployment-of-the-copernicus-sentinel-2-products-geometric-refinement) |
| S8 | [Copernicus Sentinel-2 Collection 1 MSI Level-2A, Sentinel Online](https://sentinels.copernicus.eu/web/sentinel/sentinel-data-access/sentinel-products/sentinel-2-data-products/collection-1-level-2a) |
| S9 | [Empirical correction of systematic orthorectification error in Sentinel-2 velocity fields for Greenlandic outlet glaciers, The Cryosphere 16, 2022](https://tc.copernicus.org/articles/16/2629/2022/) |
| S11 | [Deployment of Sentinel-2 Processing Baseline 05.12 on 4 February, Sentinel Online, 2026-01-29](https://sentinels.copernicus.eu/web/sentinel/-/deployment-of-sentinel-2-processing-baseline-in-version-05.12-on-4-february) |
| S12 | [Introduction of Tile-part Length (TLM) markers in Sentinel-2 JPEG2000 images, Sentinel Online, 2025-12-10](https://sentinels.copernicus.eu/web/sentinel/-/introduction-of-tile-part-length-tlm-markers-in-sentinel-2-jpeg2000-images) |
| S13 | [Sentinel-2 L2A processing baseline table, Copernicus Data Space documentation](https://documentation.dataspace.copernicus.eu/Data/Others/Sentinel2_L2A_baseline.html), accessed 2026-09-10. Lists 05.11 as operational from 2024-07-23 and does not yet list 05.12 |
| S14 | [Deployment of Copernicus Sentinel-2 Processing Baseline 05.13 on 21 September 2026, Sentinel Online, 2026-09-04](https://sentinels.copernicus.eu/-/deployment-of-copernicus-sentinel-2-processing-baseline-05.13-on-21-september-2026), accessed 2026-09-10 |
| S10 | [Suitability of different in-water algorithms for eutrophic and absorbing waters applied to Sentinel-2 MSI and Sentinel-3 OLCI data, Frontiers in Remote Sensing, 2024](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2024.1423332/full) |

The recheck was performed by an AI agent and recorded in [best-practices-recheck.json](assessment-checks/best-practices-recheck.json), with a verbatim quote per verdict. It is a documentation check, not a product inspection.
