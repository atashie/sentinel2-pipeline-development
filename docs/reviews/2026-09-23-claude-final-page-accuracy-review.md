# Claude Code final accuracy review of the assessment page, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: review complete. No page, template, renderer, or evidence file changed. Fixes await owner authorization.

The owner asked for a final technical accuracy review of the whole [assessment page](../s2-options.html).
Today's sessions changed it three times: the [page accuracy fixes](2026-09-23-page-accuracy-fixes.md), the [cost section fixes](2026-09-23-cost-section-accuracy-fixes.md), and the [answer-first Prototyping order](2026-09-23-prototyping-flow.md).

## Method

- A text extraction of the page was compared with the last commit. 162 lines were new or changed, 148 of them in Prototyping.
- Three agents checked separate areas against repository evidence: Discovery, Prototyping measurements, and AWS costs. None edited a file.
- Claude Code checked text outside those extractions: image alt text, figure titles, map view descriptions, the scale bar, section cross-references, and the placeholder tabs.
- Claude Code reproduced every finding below rated above minor before recording it.

No number on the page was found wrong. Over 350 values matched their evidence.
They include all 60 cost table values, all 98 section 02 table cells, and every archive history count.
All 138 coverage cells match, apart from one rounding.

## Findings in text changed today

| # | Page text | Problem | Evidence | Proposed wording |
|---|---|---|---|---|
| 1 | Section 00: the separate-lake workflow took "11 percent more with source-block lazy reads" | Misleading. The retained A3 total includes obsolete catalog setup larger than the gap | A3 setup 176.1 s against B3 9.0 s in `lazy-reader-workloads.json`. The [rerun record](2026-09-21-sleep-rerun.md) estimates 167–170 s of it as obsolete. Without it, A3 takes about 340 s against B3's 457 s | "Their separate-lake workflow took 30 percent less total time with direct raster reads. The lazy-reader pair shows no clear direction, because the retained A3 time includes older catalog setup." |
| 2 | Discovery, issue I-08: "ESA finished reprocessing 2015 to 2021 in 2024 and 2022 to 2023 in 2025. The route holds them in two collections" | Wrong for 2022 and 2023. The page's own archive table shows the route holds mainly 03.01, 04.00, and 05.09 for those years, not the reprocessed 05.10 | Archive table rows for 2022 and 2023. Collection 1 in 2023: 4,036 at 05.09 and 221 at 05.10 | "The route holds the reprocessed 2015 to 2021 products. For 2022 and 2023 it holds mostly earlier versions, split across two collections." |
| 3 | Section 03: "Source reads use an S3 gateway endpoint, with no NAT charges." | States an assumption as fact. Beside the operations total, it also reads as "no NAT anywhere" | The [cost report](../aws-cost-analysis.md) says the network path "assumes" gateway access. The catalog route is an open review item | "The model assumes source reads use an S3 gateway endpoint, so it includes no NAT charges for them." |
| 4 | Section 03: "Section 02 supplies CPU time per megabyte and requested bytes per source block." | Overstated. Section 02 measured five layers. The model scales the payload to 17 layers, 3.3 times the measured set | `calibration` in the estimates. `seventeen_to_five_ratio` 3.3006 in the [cohort blocks](../cost-analysis/cohort-blocks.json). National block counts come from a fitted occupancy model | "Section 02 supplies CPU time per requested megabyte and requested bytes per decoded byte on five layers. The other layers, national block counts, network time, and overheads are assumed." |
| 5 | Section 01 grid: "Section 04.2 also measured A2 and C2 but shows neither." | Section 04.2's notes report a C2 result | Page text: "Its C2 whole-image computations opened each 10 m file 36 times" | "Section 04.2 also measured A2 and C2, but its tables show neither." |
| 6 | Section 03: "Most 2022 dates come from the older copy." | True of the data, but the model prices those dates as Collection 1 reads with 17 layers | The older copy lacks cloud and snow layers for most 2022 items, per [measurements](../measurements.md). The calibration used Collection 1 only | "Most 2022 dates would come from the older copy. The model prices them as Collection 1 reads." |
| 7 | Section 03 label: "All contiguous US water bodies (5,000,000)" | The population is eligible bodies only. Assumption A26 excludes the Great Lakes | [Assumptions](../assumptions.md#aws-cost-analysis) A26 | "All eligible contiguous US water bodies (5,000,000)" |
| 8 | Discovery, issue I-17: version 00.01 "which ESA never issued" | Slightly stronger than the evidence | Issue text: "a value that matches no ESA baseline" | "which matches no ESA processing baseline" |

## Findings in text already committed

| # | Page text | Problem | Evidence | Proposed wording |
|---|---|---|---|---|
| 9 | Discovery sensor table: PlanetScope "3.0 m pixel size" and "3.7 m to 4.2 m" GSD note, under "independently checked" | The checker could not confirm it | `chk-sensor-planetscope` in `sensor-bands-checks.json` says it "Could not independently confirm" the note | Mark the note unverified, or keep only the confirmed 3 m resolution |
| 10 | Sections 00 and 02: B1 reads "each lake's rectangle" or "each lake's window" | In section 02, B1 reads one window per required source block for each lake | `raster_asset` in `benchmarks/workload_readers.py`. The result states "Raster windows follow required native blocks" | "Read each required source-block window for each lake, reusing cached data when available." |
| 11 | Section 04.3: "The selected groups did not change." | No version 3 selection run or audit supports it | [Measurements](../measurements.md) say only that the measured groups hold one product per tile | "The measured groups contain one product per tile, so the datastrip defect does not affect these results." |
| 12 | Discovery bridge: "Windowed reads per lake, whole-tile reads shared across lakes, and precomputed pixel selections" | Does not match the tested workflows. Every main recipe uses prepared selections | Section 01 defines workflows A, B, and C | "Reading each lake separately, sharing image windows, and reading whole images offer different tradeoffs." |
| 13 | Issue I-25: "Orbit overlap increases at high latitude" | No check record in the repository supports the latitude part | Claim Q7's quote mentions adjacent-orbit overlap only | "Overlap between adjacent orbits adds revisits, and one pass can produce multiple products for a tile." |
| 14 | Issue I-03: "Common tools keep a pixel only when its center falls inside the polygon." | Center selection is a default. The prototype's clip used all-touched | `all_touched=True` in `src/s2proto/masks.py` | "By default, common tools keep a pixel only when its center falls inside the polygon." |
| 15 | Issue I-09: the flag "sits in a metadata file that the route does not always deliver" | Delivery is untested. The issue's status is probe | Issue I-09 text: "may not expose it" | "…sits in a metadata file that the route may not deliver. That is untested." |

## Minor findings

- Section 00: "Both shared-window readers processed Florida faster." B2 also shares windows and was slower in Florida. Write "B1 and B3 both".
- Issue I-02: "most in red and near-infrared" goes beyond the source, which says "potentially due to" those bands.
- Issue I-07: the stacking library resamples to 10 m by default, with nearest neighbor. "Look sharper than they are" misdescribes nearest-neighbor upsampling.
- Issue I-15: "shifts by several meters" is an upper range. Write "can shift by up to several meters".
- Issue I-11: "look like water" is the repository's inference. The source says "very low reflectance".
- Access section: "two public collections" sits beside a described third archive. Write "mainly as two public GeoTIFF collections".
- Access section: "Both copies can hold several processing versions of one observation." Collection 1 had one mixed-version pair in the sample.
- Copy table: the aerosol and water-vapor grid sizes list Collection 1 first under an "Older minus Collection 1" header.
- PlanetScope note: band edges differ by up to 2 nm, not 1 nm.
- Coverage strip: the 2022-12 cell shows 100 percent for 353 of 354.
- The 76 percent fill figure includes an Alaska tile that nothing covers. Outside it, the older copy fills 3,840 of 3,860.
- Discovery: "The AWS cost saving is unmeasured" is true. Section 03 now estimates it.
- Section 00 cost line: "Stored records" cost includes 46 GiB of prepared geometry.
- Section 01 grid: section 03 reports A1, B1, and B3 costs, and the grid does not list it.
- Removing the former remaining-decisions section left no mention of the Stage 4 no-data entries on the page. The owner directed that removal.
- Discovery: "The store keeps every band" rests on assumption A3, which is unsourced. The page does not say so.

## Correction to an earlier record

The [cost presentation record](2026-09-23-cost-presentation.md) said section 07's definitions state the Great Lakes exclusion. They do not. That line is corrected in the record.

## Verified without findings

- Map facts match the provenance record: place, date, 97.8 percent valid, the 8 by 8 km window, and the 1 km scale bar.
- The stretches, index formulas, and six view descriptions also match it.
- Check records C1, C4, C5, and C6 support the reprocessing dates, the Sentinel-2A campaign, the restored NHD note, and the readme wording.
- All section cross-references after the reorder point to the right sections.
- The cost table's storage headings equal history plus geometry, all within the first S3 price tier.

## Verification

- `uv run python tools/render_options.py --check`: the page matches its template and inputs.
- `uv run python tools/estimate_aws_costs.py --check`: the estimates match their inputs, evidence, and model.
- The agents' scratch files are outside the repository. `git status` shows no change from this review except this record, the index row, and the corrected line in the cost presentation record.

## Proposed next step

With owner authorization, apply findings 1 to 8 first, then 9 to 15. Findings 2, 8, and 13 to 15 change inventory `plain` lines. Finding 9 changes a sensor band note and needs its check record. Not started.
