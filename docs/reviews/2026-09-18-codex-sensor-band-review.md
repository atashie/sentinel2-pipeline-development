# Sensor band accuracy review, 2026-09-18

Reviewer: Codex, with separate Sentinel, Landsat/MODIS, and PlanetScope checking agents.

The numerical band specifications match their cited agency and vendor tables. Several application claims and explanatory notes need qualification.
The water-quality column cannot yet carry its blanket claim that every displayed use is documented for that sensor.

## Scope and method

This reviews the [comparison implementation](2026-09-17-sensor-band-comparison.md), [bound dataset](../sensor-bands.json), research records, check records, and renderer.
The review covers all 100 band rows, all Sentinel-2 platform variants, 152 use assignments, six definitions, and supporting sensor notes.
Sources were reopened on 2026-09-18. Existing agent confirmations were treated as claims to check, rather than evidence.

The acceptance checks were correct transcription, explicit product and resolution distinctions, and evidence that supports each application's stated scope.
No imagery was downloaded, provider measurement script executed, or model validated.
This step adds this review and its index entry. Presentation and dataset corrections remain the proposed follow-up.

## Findings

### F1. Distinguish demonstrated uses, supporting roles, and wavelength-based inferences

Priority: P2. Disposition: prior blanket confirmation corrected with evidence. Presentation correction remains open.

The dataset distinguishes 85 `named` assignments from 67 `wavelength` assignments.
[The renderer](../../tools/render_options.py) discards that distinction when building chips and calls all assignments documented uses.
A wavelength falling inside a band does not establish that band's performance or the suitability of a transferred algorithm.

Documented: [Soomets et al.](https://spectralevolution.s3.us-east-2.amazonaws.com/assets/Water_quality_PSR-3500.pdf), Sections 2 and 4, tested MSI and OLCI using their spectral responses.
The research extends that study's CDOM wavelength examples to Landsat, SLSTR, MODIS, and PlanetScope.
Those extensions are inferences, even when physically plausible.

Documented: [NASA's emissive-band applications](https://mcst.gsfc.nasa.gov/calibration/emissive-bands) identifies MODIS B21 with fires and volcanoes.
The [SST algorithm document](https://modis.gsfc.nasa.gov/data/atbd/atbd_mod25.pdf), printed page 4, lists B20, B22, B23, B31, and B32.
The B21 water-temperature chip instead rests on a broad specification-table category.
Its water-temperature assignment remains unverified without a specific retrieval citation.

MODIS B16's separate chlorophyll assignment similarly needs evidence beyond membership in the ocean-color band group.
Its atmospheric-correction role is supported.
Conversely, B15's chlorophyll role has direct support as a fluorescence baseline in [NASA's fluorescence algorithm](https://modis.gsfc.nasa.gov/data/atbd/atbd_mod22.pdf).
Its generic citation can be strengthened without removing that use.

Documented: [Vanhellemont's SuperDove study](https://www.vliz.be/imisdocs/publications/389100.pdf), Section 2.5, supports red, red-edge, and NIR chlorophyll combinations.
Its introduction describes the yellow band's phycocyanin potential tentatively. The study also tests networks using seven or eight bands.
Retain those distinctions instead of presenting the introductory suggestion as a demonstrated yellow-band pigment retrieval.
Its NIR glint correction requires water with negligible NIR water-leaving signal.

Required correction: expose evidence type beside each use and preserve the distinction between direct retrieval and supporting measurements.
Keep transferred uses explicitly provisional unless a study names the actual sensor or establishes the transfer.
Retain study conditions and tentative language when the source does not demonstrate a retrieval.
The existing disclaimer about model validation does not resolve the source-attribution problem.

### F2. Calculated wavelength intervals are not measured passband boundaries

Priority: P2. Disposition: interpretation corrected with evidence. Presentation correction remains open.

[The renderer's `wavelength_label`](../../tools/render_options.py) turns every center and bandwidth into center plus or minus half the bandwidth.
Documented: [ESA defines Sentinel-2's equivalent wavelength](https://sentiwiki.copernicus.eu/web/s2-mission) as the spectral response's barycenter, excluding solar irradiance.
A barycenter and width do not uniquely determine the response's endpoints.

Documented: [Planet's specification page](https://docs.planet.com/data/imagery/planetscope/) publishes both center/FWHM values and separate wavelength ranges.
For Coastal Blue, the current calculation yields 433–453 nm, while Planet's range table gives 431–452 nm.
The existing footnote acknowledges the source values, but the main cell still presents the calculated interval without an approximation label.
The note describing discrepancies of 1 nm also needs correction. Coastal Blue's lower endpoint differs by 2 nm.

Required correction: display the original center and bandwidth, or explicitly label calculated intervals as approximations.
Retain published ranges where a source supplies them. Avoid treating calculated intervals as evidence of algorithm compatibility.

### F3. Correct the atmospheric-correction definition

Priority: P2. Disposition: prior definition corrected with evidence. Dataset correction remains open.

The definition says water vapor, aerosols, clouds, and glint all add signal.
Documented: [ESA's processing description](https://sentiwiki.copernicus.eu/web/s2-processing) retrieves water vapor from absorption using B8A and B09.
Water-vapor absorption attenuates the reflected signal.
Replace the additive-only explanation with scattering, absorption, and contamination that alter the measured signal.

### F4. Keep CDOM distinct from all dissolved organic matter

Priority: P3. Disposition: label corrected with evidence. Presentation correction remains open.

The chips say "Dissolved organics," and the full label says "Dissolved organic matter."
The definition and cited retrievals concern colored dissolved organic matter, or CDOM.
Documented: [Soomets et al.](https://spectralevolution.s3.us-east-2.amazonaws.com/assets/Water_quality_PSR-3500.pdf) estimates CDOM absorption and treats it as a carbon proxy.
Use "CDOM" or "Colored dissolved organics" to avoid implying direct measurement of the entire dissolved organic pool.

### F5. Narrow three statements in the supporting notes

Priority: P3. Disposition: source interpretations corrected with evidence. Dataset correction remains open.

| Existing statement | Evidence and correction |
|---|---|
| Per-satellite values exist for Sentinel-2 only | Documented: ESA supplies platform-specific [OLCI](https://sentiwiki.copernicus.eu/web/s3-olci-instrument) and [SLSTR](https://sentiwiki.copernicus.eu/web/s3-slstr-instrument) spectral responses. Describe the displayed Sentinel-3 values as nominal or representative. |
| The chlorophyll review establishes general Landsat unsuitability | The cited paragraph discusses Landsat/ETM+ spectral placement. Restrict the limitation to algorithms requiring missing red-edge measurements. |
| No source names Sentinel-2 B11 for water extent | Documented: the already-cited [ESA processing page](https://sentiwiki.copernicus.eu/web/s2-processing), step 5.2, names B2/B11 for water-body detection. Say the selected assignment list is incomplete. |

The Landsat attribution was checked against [the cited review's Section 4.1](https://www.mdpi.com/152160).
That section also reports successful Landsat applications. It does not support a blanket inability to estimate chlorophyll.
Empty use cells mean no selected assignment, rather than no established use.

## Confirmed specifications and necessary scope

Status: documented. The following groups account for every band row.
The confirmations concern the source's stated specification, not every platform's exact spectral response or every delivered product.

| Table | Coverage and result | Primary evidence |
|---|---|---|
| Sentinel-2 MSI | All 13 bands and all 26 B/C variant pairs match. The 10/20/60 m groups are correct. B10 is correctly excluded from L2A. | [Mission tables 3–4](https://sentiwiki.copernicus.eu/web/s2-mission), [products](https://sentiwiki.copernicus.eu/web/s2-products) |
| Landsat 9 | All 11 names and wavelength ranges match. Reflective, panchromatic, and thermal sampling distinctions are correct with the existing thermal footnotes. | [USGS band designations](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites) |
| Sentinel-3 OLCI | All 21 centers, bandwidths, and function labels match. Full and reduced resolution descriptions are correct. | [ESA OLCI products](https://sentiwiki.copernicus.eu/web/olci-products) |
| Sentinel-3 SLSTR | All 11 rows match. The 500 m and 1 km groups are correct. Nine spectral channels plus two fire channels explain the count. | [ESA SLSTR products](https://sentiwiki.copernicus.eu/web/slstr-products) |
| MODIS | All 36 wavelength ranges and unit conversions match. The 250/500/1,000 m groups are correct nominal sampling values. | [NASA specifications](https://modis.gsfc.nasa.gov/about/specifications.php) |
| PlanetScope SuperDove | All eight names, centers, and FWHM values match. These describe PSB.SD, rather than all Planet imagery or older Dove instruments. | [Planet specifications](https://docs.planet.com/data/imagery/planetscope/) |

Documented: [EUMETSAT's OLCI algorithm document](https://www-cdn.eumetsat.int/files/2024-01/EUMETSAT_OC-SAC_ATBD_v5.2_web.pdf), pages 27–28, supports the selected Oa09 and Oa16 values.
The conflicting ESA instrument-page numbers are already disclosed. They do not justify changing the dataset's chosen values.

Documented: Landsat's thermal observations have native 100 m sampling and delivered 30 m pixels, as the table's footnotes correctly state.
The pixel-size column is not uniformly a native-resolution comparison.
Display native sampling and delivered grid spacing separately when readers compare resolvable water-body detail.

Documented: [Planet's June 2026 specification](https://assets.planet.com/docs/Planet_PSScene_Imagery_Product_Spec_letter_screen.pdf), Tables 2-A and 3-E, confirms the existing 3.7–4.2 m GSD note.
It also confirms 3.0 m orthorectified pixels. The original checker disclosed that it could not verify this distinction.
This review resolves that evidence gap using the directly accessible specification. The stated numbers can stay.
Section 2.1 also confirms the existing 2022-04-29 transition statement about new eight-band SuperDove acquisitions.

Documented: [Vanhellemont's study](https://www.vliz.be/imisdocs/publications/389100.pdf), Section 2.3.1, reports different acquisition sampling among the SuperDove bands it evaluated.
It describes approximately 3 m sampling for blue through red, 6 m for red-edge/NIR, and 12 m for coastal blue.
All were delivered on 3 m grids. These study-specific acquisition details require qualification before applying them to the entire current fleet.
The current table's "Pixel (m)" label is defensible. It does not establish equal native resolving detail across all eight bands.

Documented: [USGS surface-reflectance documentation](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance) limits Landsat 8/9 surface reflectance to B1–B7.
The [Level-2 guide](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/LSDS-1619_Landsat8-9-Collection2-Level2-Science-Product-Guide-v6.pdf) supplies surface temperature from B10.
The comparison lists instrument bands. Add that scope explicitly so readers do not interpret every row as a ready-made surface-reflectance or temperature product.

The public/commercial distinction, stated platform identities, and launch years agree with the mission and vendor pages.
The named Sentinel atmospheric-screening, NDWI, OLCI function, and SLSTR temperature assignments have direct support in their cited documentation.
SLSTR S7's surface-temperature contribution needs its nighttime condition when discussing actual retrievals.
That condition is documented in the [EUMETSAT SLSTR guide](https://user.eumetsat.int/resources/user-guides/sentinel-3-slstr-level-1-data-guide).

## Verification and limits

The six use definitions were checked against their cited explanations. F3 and F4 record the needed corrections.
The 152 assignments were traced by source and evidence type. F1 records why their blanket confirmation is too strong.
This review does not declare every inferred use false or require validation of a project model.

| Check | Result |
|---|---|
| `uv sync --locked` | Pass. 56 installed packages checked. |
| `uv run ruff check .` | Pass. |
| `uv run ruff format --check .` | Pass. 93 files already formatted. |
| `uv run pytest -q` | 215 passed in 12.01 seconds. Existing dependency deprecation warnings remain. |
| `uv run pytest -q tests/test_docs.py` after final source additions | 61 passed in 0.13 seconds. |
| Inventory, sensor-band, presentation, and gap-report `--check` commands | Pass. Generated files match their current inputs. |
| `git diff --check` | Pass. |

Tests establish structural consistency, not scientific validity of the assigned uses.
The sensor-band and gap-report commands required approved access to the existing uv cache outside the workspace.
Concurrent section 02 presentation changes and their review record were preserved.

## Proposed next step

Correct the research and check records, then regenerate the dataset and presentation with visible evidence and resolution distinctions.
Preserve confirmed specifications and the existing Sentinel-2 preference.
Submit that correction step for review under the repository workflow.
