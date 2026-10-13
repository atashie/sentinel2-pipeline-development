# Assessment checks

Research drafts, independent check records, and the best-practices recheck that bind claims in [options-inventory.json](../options-inventory.json).
A research agent drafted each claim and a different agent checked it against its page, per the workflow in [CLAUDE.md](../../CLAUDE.md). The check records carry the verification limits.
A supplementary pair named `<dimension>-<topic>-research.json` and `-checks.json` binds beside its dimension's pair, per the [format](../assessment-data-format.md#collation).

| File | Purpose | Agent |
|---|---|---|
| `access-route-research.json` | Access-route draft claims, primary sources, and queried endpoints | Researchers named in the records |
| `access-route-checks.json` | Independent verdicts on access-route claims | Checkers named in the records |
| `processing-workflow-research.json` | 98 draft claims on six workflows, 82 documented and 16 estimated, 38 sources | Opus researcher |
| `processing-workflow-checks.json` | 82 confirmed. Its limitations record a scope excursion by its forked sub-checkers and the audit that followed | Sonnet checker |
| `compute-platform-research.json` | 56 draft claims on five platforms, 51 documented and 5 estimated, 27 sources | Opus researcher |
| `compute-platform-checks.json` | 51 confirmed | Sonnet checker |
| `storage-layout-research.json` | 65 draft claims on four layouts, 55 documented and 10 estimated, 26 sources | Opus researcher |
| `storage-layout-checks.json` | 54 confirmed, 1 corrected | Sonnet checker |
| `best-practices-recheck.json` | 20 verdicts on [s2-best-practices.md](../s2-best-practices.md), 15 additional findings | Opus rechecker |
| [probes-2026-09-11.json](probes-2026-09-11.json) | One shared product compared across the two COG catalogs. Metadata only | Claude Code researcher and separate checker |
| [discovery-presentation-sources.json](discovery-presentation-sources.json) | Sensor, archive, and quality context, plus display recipes, checked 2026-09-11 | Codex researcher and separate gpt-5.6-sol checker |
| [sensor-bands-research.json](sensor-bands-research.json) | 100 bands on six sensors with quoted wavelengths, pixel sizes, and 152 use assignments from 29 sources, for the presentation's sensor comparison | Opus researcher |
| [sensor-bands-checks.json](sensor-bands-checks.json) | 112 confirmed: 6 uses, 6 sensors, 100 bands. Bound into [../sensor-bands.json](../sensor-bands.json) by `tools/collate_sensor_bands.py` | Sonnet checker |
| [aws-cost-analysis-sources.json](aws-cost-analysis-sources.json) | Qualified population, AWS price, transfer, and capacity facts for offline cost scenarios | Research and independent checking agents named in the record |
| [aws-cost-review-sources.json](aws-cost-review-sources.json) | Storage-class, serving-transfer, Spot, and Savings Plan sensitivities with price qualifications | Researcher and separate-model checker named in the record |
| [presentation-review-sources.json](presentation-review-sources.json) | Corrections from the whole-page accuracy review: reprocessing completion, tile overlap, swath-edge mask, Sentinel-2A campaign, NHDPlus HR status, and readme hosting | Claude Code researcher and separate claude-sonnet-5 checker |
| [aws-cost-daily-sources.json](aws-cost-daily-sources.json) | Scheduling, queue, ledger, logs, monitoring, and registry pricing proxies | Researcher and independent checker named in the record |
| [access-route-usgs-aqr-research.json](access-route-usgs-aqr-research.json) | 50 draft claims on the USGS aquatic reflectance product, 12 sources, 2026-10-13 | Opus researcher |
| [access-route-usgs-aqr-checks.json](access-route-usgs-aqr-checks.json) | 49 confirmed, 1 corrected. Bound by collation beside the access-route pair | Sonnet checker |
| [processing-workflow-acolite-research.json](processing-workflow-acolite-research.json) | 60 draft claims on self-run ACOLITE, 57 documented and 3 estimated, 21 sources, 2026-10-13 | Opus researcher |
| [processing-workflow-acolite-checks.json](processing-workflow-acolite-checks.json) | 48 confirmed, 9 corrected. The parent agent reviewed the 3 estimates | Sonnet checker |
| [water-correction-research.json](water-correction-research.json) | 46 draft claims on Sen2Cor over water, Sen2Cor versions, inland-water intercomparisons, and Level-1C sources, 33 sources, 2026-10-13. Feeds section 5 of [s2-best-practices.md](../s2-best-practices.md), not the inventory | Opus researcher |
| [water-correction-checks.json](water-correction-checks.json) | 36 confirmed, 10 corrected. Binds claims W1 to W11 in the best-practices document | Sonnet checker |

The original inventory pages were accessed on 2026-09-09. Only confirmed or corrected values populate the inventory.
Estimated claims are reviewed by the parent agent, not by a checker.
Presentation source checks and the sensor band records support explanatory context and do not add candidate specifications.
Checks verify documentation. They are not measurements, human approval, or independent verification of the provider's data. Researchers and checkers differ by model, not by organization.
