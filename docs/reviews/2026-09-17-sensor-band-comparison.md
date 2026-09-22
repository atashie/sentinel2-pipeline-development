# Sensor band comparison on the presentation, 2026-09-17

Implementer: Claude Code (AI coding agent), directed by the repository owner, with a separate research agent and a separate checking agent. Status: ready for owner and Codex review after the checks recorded below.

Scope: one addition to section 01 of the [page](../s2-options.html). No benchmark ran. No script contacted a provider. No selection changed. The Sentinel-2 preference and the access route stand as before.

## The owner's direction

Add a dropdown to section 01 that shows the specific bands and resolutions of Landsat 9, Sentinel-2, Sentinel-3, MODIS, and Planet Labs imagery. Let a reader compare across them. Add a column that says which bands are considered useful for assessing water quality. The owner noted that the column needs research.

## What the page now has

A collapsed block under the two sensor cards, headed "Compare bands across 6 sensors". Open it and two panels appear, each with a selector. The left panel starts on Sentinel-2 MSI and the right on Landsat 9. Each panel offers six tables. They are Sentinel-2 MSI, Landsat 9 OLI-2 and TIRS-2, Sentinel-3 OLCI, Sentinel-3 SLSTR, MODIS on Terra and Aqua, and PlanetScope SuperDove.

Each table lists every band with its id, name, wavelength range in nanometers, and pixel size in meters. A last column lists the water-quality uses a cited source names for it. The uses are six chips. They are chlorophyll and cyanobacteria, turbidity and suspended sediment, dissolved organic matter, surface temperature, atmospheric correction and screening, and water extent and shoreline. A legend defines each. Band notes appear as numbered footnotes under the table. Source and provenance notes sit behind "Notes on this table". A source note lists every cited page by publisher.

Without JavaScript the block lists all six tables in order. Printing shows the two tables on screen. The page still makes no external request.

Sentinel-3 has two instruments with different bands and pixel sizes, so OLCI and SLSTR are separate entries. PlanetScope is commercial imagery, and the table says so. The other five are public data.

## How the facts were established

The band facts and the use column follow the repository's research-then-check pattern, the same one that binds the inventory.

1. A research agent on Opus drafted [sensor-bands-research.json](../assessment-checks/sensor-bands-research.json). It holds every band from the agency pages, with a verbatim quote and a locator. It holds every use with a quote from a source that names the band or a wavelength inside it. Agency pages: ESA SentiWiki for Sentinel-2 and Sentinel-3, USGS and NASA for Landsat 9, NASA for MODIS, Planet for PlanetScope. Uses come from the agency band-function columns where they exist. The rest come from USGS band and surface-water documents and from open-access papers on inland and coastal water quality.
2. A checking agent on Sonnet opened every cited page again and wrote [sensor-bands-checks.json](../assessment-checks/sensor-bands-checks.json). It holds one verdict per use, per sensor, and per band, with the values it stands behind.
3. [collate_sensor_bands.py](../../tools/collate_sensor_bands.py) bound only confirmed and corrected records into [sensor-bands.json](../sensor-bands.json). The renderer fills the tables from that file. The [format](../assessment-data-format.md) describes the records.

Counts: 29 sources, 6 uses, 6 sensors, and 100 bands. Sentinel-2 has 13, Landsat 9 11, OLCI 21, SLSTR 11, MODIS 36, and PlanetScope 8. The 152 use assignments split into 85 by a named band and 67 by a wavelength inside the band. The checker wrote 112 checks. All 112 are confirmed, none corrected, none unverifiable, so the bound dataset has no gap. Researcher: Claude Code research agent on Opus, 2026-09-17 12:11 to 12:49 local. Checker: Claude Code checking agent on Sonnet, 2026-09-17 12:55 to 13:20 local. The checker's timestamp was corrected once, by the checker, from a future time to the file's write time.

A use is listed when a cited source names the band, or names a wavelength inside the band's range. Where a source gives a center wavelength and a bandwidth, the page shows the center plus and minus half the bandwidth. Where the source gives a range, the page shows the range. Sentinel-2 values are Sentinel-2A's, with 2B and 2C recorded as variants and their largest differences stated under the table.

## Limits

- These are documented uses from agency pages and published studies. They do not validate a model, an index, or a band choice for this project. The modeling team decides which bands to use, as section 01 already says.
- Uses are selective. A band with no chip has no cited source naming it, which does not prove it is useless. MODIS ozone and cloud-top bands, the SLSTR fire bands, and the Landsat panchromatic band carry no use for that reason.
- Several MDPI, Elsevier, Optica, and Taylor and Francis pages block automated access. The researcher cited open-access copies in PubMed Central, the VLIZ repository, and a university repository instead. Four classic papers, on the cyanobacteria index, a red and near-infrared turbidity algorithm, NDWI, and MNDWI, are not cited. USGS and ESA documents stand in for them.
- The Landsat 9 OLI is documented by USGS as a copy of the Landsat 8 OLI. Landsat 8 statements in the literature apply to Landsat 9 by wavelength.
- Pixel size is the product pixel size. Landsat thermal bands are acquired at 100 m and delivered at 30 m. PlanetScope products are 3 m, with a ground sample distance near 3.7 m. The footnotes and notes say so.
- The ESA OLCI, SLSTR, and NASA MODIS pages give no band names. The tables carry the agency's function or primary-use text as the name.
- Access to the other sensors on AWS was not surveyed. They are context for the sensor choice, not access-route candidates.

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. `uv sync --locked` checked 56 packages. No lint finding. 91 files formatted |
| `uv run pytest -q` | 213 passed in 14.10 seconds, existing library deprecation warnings only. 200 before this step |
| The four `--check` tools and `git diff --check` | Inventory, sensor band dataset, page, and gap report match their inputs. No whitespace error |
| Prose audit of the block's visible sentences and the dataset's notes and definitions | No sentence over 25 words, no semicolon, no "should", no modal, no em dash, no contraction, and no British spelling in the page's own prose. Verbatim names keep the source spelling: the ESA instrument name, the ESA band name "Water vapour", and a paper title |
| Headless Chromium at 1280 and 390 pixels, block opened, both selectors | The script populates both panels from the library, hides the library, and opens the block from its anchor. No script error. No external request: the page's three `src` attributes are local. A copy with other defaults rendered PlanetScope and Sentinel-2 through the same update path. At 390 px the tables scroll inside their region, as the other tables do |

New fixture tests cover the collator's binding rules and refusals, the wavelength and number labels, and the table markup with footnotes and variants. Others cover the selectors, the legend, and per-sensor gap counts. Dataset tests require the six sensors and six uses, one wavelength form per band, and a bound check on every record. They require every use named on at least one band, and the page listing every bound band once.

## What did not change

Every other section, every measured number, the inventory, the map assets, and the benchmark results. The sensor cards keep their wording. The source note under the cards keeps its 2026-09-17 check.

## Proposed next step

Owner and Codex review of the comparison block and the bound dataset. Two choices for the owner: whether the block opens by default, and whether the provenance notes stay behind a disclosure. No commit, push, or deployment was performed.

Owner's answers on 2026-09-18: the block stays closed by default, and the footnotes stay for now. Recorded in the [section 02 record](2026-09-18-access-problem-first.md).
