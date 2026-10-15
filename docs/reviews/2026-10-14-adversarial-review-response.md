# Adversarial review of the Phase C work and the response, 2026-10-14

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered. Offline only. No provider was contacted and no pixel was read. Awaiting review.

## For the owner

- Six AI review agents, each told to hunt for defects, read commit `ddbaebf`. They covered T4, T5, T6, the cost model, document consistency, and scientific framing.
- They reported 73 numbered findings, some overlapping, plus style nits. Most are fixed. One reviewer claim was wrong, and the rest are deferred, mostly for want of a rerun.
- No fix changed a measured count.
- The largest change is to the cost model. T6's five layers include the highly compressible flags layer, so their byte ratio understated ACOLITE only's full payload.
- With T1's whole-object sizes, ACOLITE only's national B1 backfill rises from $327 to $344. It stays about a quarter of Sen2Cor only's.
- The same check shows the Sen2Cor-only model overstates its own bytes. Its central case is unchanged, and a sensitivity shows the effect. Adopting it is the owner's call.
- T5's wording changed most. Clear water under rule P6 excludes ACOLITE's own negative values, so the negative-value comparison now uses all pixels.
- The pooled T5 medians are dominated by Lake Okeechobee. The sign of the difference varies between scenes of one lake, as well as between lakes.
- The reviews are AI work, like the work they reviewed. They are not owner approval.

## Step and authorization

The owner wrote "when the next steps land, commit all recent updates and then spawn a team of adversarial review agents, then incorporate their findings, then commit and push, before proceeding to subsequent steps".
The commit `ddbaebf` holds T4 to T6, the direction records, decision 0009, and the per-option cost model. Six read-only agents then reviewed it in parallel.
Each agent was told to stay offline, change no file, and report findings with evidence. Claude Code verified each claim before acting on it.
Deferred: every rerun that reads pixels, and every change to a committed result file.

## How findings were checked

Each numeric claim was recomputed from the committed result files or the saved settings files before any edit.
One reviewer claim was wrong. It said no settings key enables the Sentinel-2 mixed-pixel mask, but all 59 files set `l2w_mask_mixed=True`.
Result files stay as their scripts wrote them. Where a result field is misleading, the record and the findings now say so.

## Dispositions: cost model

| # | Finding | Disposition |
|---|---|---|
| C1 | T6's five layers include the int32 flags layer, which compresses to about 3 percent. Their ratio understated the 13-layer payload | Fixed. T1's whole-object sizes scale ACOLITE only's transfer and requests by 1.433. CPU keeps the calibrated bytes |
| C1 | The same check shows Level-2A's 17 assets compress better than its 5 measured ones | Accepted and deferred to the owner. Central Sen2Cor only is unchanged under decision 0006. A sensitivity and a whole-product check show both options scaled |
| C2, S10 | The shared point-to-tile fraction likely understates ACOLITE only | Fixed. The direction is stated, and a sensitivity gives both options at full point coverage |
| C3 | Products per acquisition counted 544 fragments among 886 extra products | Fixed. Complete products per acquisition, 1.0194, replace 1.0499. The text no longer calls repeats revisions |
| C4 | The comparator also carries the reader calibration | Fixed in the table note and the prose |
| C5 | Source payload was tied to retained bytes | Fixed. A separate source payload input exists |
| C6 | The comparison table hard-coded Sen2Cor-only inputs | Fixed. Both columns read the generated option inputs |
| C7 | Weak tests | Fixed. New tests tie counts to T1 and T2 fields, scaling to T1 sizes, and CPU to calibrated bytes |
| C8 | The byte audit trusts the plan's own digest, with no independent checker | Accepted and deferred. The reviewer recomputed both plan digests and they match |
| C9 | The 2.9 percent figure spans all years | Fixed. The text now prices complete products and names the period |
| C10 | "Does not apply" for the 2022 event | Fixed. No product-specific event is modeled |
| C11 | Cached evidence was passed by reference | Fixed. Callers receive copies |
| S8 | CPU per requested megabyte rises only because the measured layers compress well. Per decoded megabyte it is about equal | Fixed in finding 37, the cost analysis, PR-14, and the T5 and T6 record |
| S9 | The model gives ACOLITE only fewer requests per file and product than T6 measured | Fixed as a stated limit with its direction and size. A request back-test is deferred |
| S15 | The headline mixes in fewer acquisitions, and split datastrips are partial products | Fixed. The same-history comparator leads, and the limit is stated |

## Dispositions: probe T5

| # | Finding | Disposition |
|---|---|---|
| P1, S1 | Rule P6 removes ACOLITE's negative values from 450 to 700 nm, so the clear-water negative shares compared unlike selections | Fixed. Finding 35 and the record state the cause and report negative shares from all pixels. A diagnostic stratum without that flag bit needs a rerun and is deferred |
| P2 | Floating-point Collection 1 units can put a difference of exactly 50 units on either side of rule P7 | Accepted and deferred. Stated as a limit. A corrected share needs a rerun |
| P3, S2 | "Lower in every band" was pooled and driven by Lake Okeechobee, 65 percent of observations | Fixed. Finding 35 gives the share and the record-median medians, positive in B06 to B8A |
| S3 | The sign also varies between scenes of one lake | Fixed in finding 35, the record, PR-13, and I-31 |
| S4 | The 0.005 tolerance is absolute and has no stated basis | Fixed as a stated limit. The ranking sentence is gone. A relative diagnostic needs a rerun and is deferred |
| S5 | Rule P4 assumes both products hold one quantity | Fixed. Added to what T5 does not show and to the record's limits |
| P4 | The pairing key drops the baseline, and two edge cases could miss an item | Accepted and deferred. Stated as a limit. All 59 pairs share baseline 05.11 |
| P5, S6, D7 | I-31 framed the T5 numbers beside "not designed for water", and stated ACOLITE's design as fact | Fixed. I-31 says neither product is a reference, and its why cites assumption A52. The page sentence was changed the same way |
| P6 | Two counts came from different bands | Fixed. Both now use B01 |
| P7 | Wrong source keys for the declared scale and offset | Fixed |
| P8, S11 | "Matches the data" overstated diagnostic P9 | Fixed. 52 of 58 scenes lie from 964 to 1,149, consistent with an offset still in place |
| P9 | Per-tile values pool every pilot lake on the tile | Fixed in the wording |
| P10 | "Coastal and visible bands differ most" was untrue for B05 | Fixed. The sentence is gone |
| P11 | The script's limitation says the product averages its 10 m bands, without a source | Accepted and deferred. The result keeps the text its script wrote. Reviewers disagree on the method |
| P12 | Rule code lives in the script, and some rules lack tests | Accepted and deferred to any T5 rerun |
| S13 | Missing limits: USGS cloud screening and non-independent pixels | Fixed in what T5 does not show |

## Dispositions: probe T4

| # | Finding | Disposition |
|---|---|---|
| V1 | Finding 33's cloud shares include the wrong-item Lake Washington scene | Fixed. Finding 33 and the record give the shares without it. Lake Washington's unflagged share is 8.3 percent |
| V2 | The settings files supposedly carry no Sentinel-2 mixed-pixel key | Corrected with evidence. All 59 files set `l2w_mask_mixed=True`. The text now names the keys |
| V3 | The tile and size splits pass 1 percent through the same scene | Fixed in finding 30 and the record |
| V4, D5 | The no-data exception was inverted | Fixed in finding 30, the record, and PR-12 |
| V5 | Counts prove the same pixels where no-data covers a whole record | Fixed in finding 30 and the record's limits |
| V6 | The declared-rules header came from a shell command, not the dry run | Fixed in the T4, T5, and T6 records |
| V7, D4 | Stale "uncommitted" status lines | Fixed in five records |
| V8 | The NDWI formula was stated without its agreement share | Fixed in finding 32's title, the record, CLAUDE.md, and PR-12 |
| V9, S12 | "Interior water" and "unflagged shadow" treated a polygon class and the classification as truth | Fixed. The text says ACOLITE has no shadow test and names the classification's labels |
| V10 | The gotcha read as a general product fact | Fixed. CLAUDE.md names the 59 scenes of 2025 |
| V11 | Rule R1's product-grid check never compares the layers' EPSG | Accepted and deferred. No effect on this run |
| V12 | One verification sentence ran to 28 words | Fixed |

## Dispositions: probe T6

| # | Finding | Disposition |
|---|---|---|
| W1, D3 | Finding 36 mislabeled the stage 3 read orders as processes | Fixed. Reading file by file takes 62 to 82 percent of the requests of lake by lake |
| W2 | "32 to 43 percent in every method" excluded the lazy stack's 28 percent | Fixed in finding 36 and the record |
| W3 | Stage 4's during-run header field repeats stage 3's checks, and "100 layers" are 100 checks of 60 layers | Fixed in finding 36's preamble and the record's limits. The result file stays as written |
| W4 | The result file has no record of the interrupted attempt | Accepted and deferred. The run directory's `replacement.json` holds it, and the record says so |
| W5 | A launched extraction whose supervisor stopped kept the status not_started | Fixed in the driver for later runs, with a test. The record describes what the run printed |
| W6 | "Every method identical" included the naive clip, which differs where preparation predicts | Fixed in finding 36, the record, and PR-14 |
| W7 | The workload reference count merged both cohorts | Fixed in the driver for later runs. The record names the result field. Match counts are unaffected |
| W8 | The lazy stack's 65 to 114 percent came from stage 3, not stage 4 | Fixed in the record |
| W9 | One anchor and one percentage were missing or rounded wrongly | Fixed in finding 36 and finding 37 |
| W10 | Stale statements, a missing UTC, and Collection 1 metadata under product ids | Fixed, except the result's item metadata, which stays as written |
| W11 | Missing driver tests | One test added for the interrupted status. The rest are accepted and deferred |
| S7 | Elapsed times compare runs a month apart | Fixed. Findings 36 and 37 and the record state the confound |

## Dispositions: documents

| # | Finding | Disposition |
|---|---|---|
| D1 | Practice P10 still said to store both corrections side by side | Fixed. Each option stores one correction, decision 0009 |
| D2 | Finding F-28 said Level-2A stays necessary beside the product | Fixed. Its title now describes the ACOLITE-only option |
| D6 | The inventory's next steps were stale | Fixed |
| D8 | Decisions 0003 and 0004 and one inventory note still called Earth Search supplementary | Fixed. Each points to decision 0009. The scoping note was fixed in its research record and re-collated |
| D9 | The fill policy read two ways | Fixed. Self-run ACOLITE stays context until the owner decides, in decision 0009, A13, and A48 |
| D10 | The work plan stated an authorization as fact | Fixed. It quotes the owner |
| D11, S14 | T5 was called a validation item | Fixed in the work plan and the T4 limits |
| D12 | A52 listed a document that never cited it | Fixed. Practice P10 cites it now |
| Nits | A stale anchor, three stale sentences, missing units, a wrong citation, a stale replan status, contrast wording, and first person | Fixed |
| Nits | Some numbers appear in several documents | Accepted. The copies agree and name their home |

## Verification

| Command | Outcome |
|---|---|
| `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` | Pass |
| `uv run pytest -q` | 387 passed, 13,000 existing warnings |
| `uv run python tools/estimate_aws_costs.py --check` | Both estimate files and the report tables match |
| `uv run python tools/backtest_aqr_source_bytes.py --check` and `tools/backtest_source_bytes.py --check` | Both match their saved local inputs |
| `collate_checks`, `collate_sensor_bands`, `render_options`, and `gap_report`, each with `--check` | All current |
| The review-layer `inject.py --check` | Up to date |
| Recursive comparison of `estimates.json` with its version before this work | Zero differing values |
| Style scans of the changed Markdown and inventory text | Only the owner's verbatim quotes exceed 25 words |

## Limits

- The reviewers and the author are AI agents. Agreement between them is not independent evidence.
- Fixes that need new pixel reads are deferred. T5's float threshold, its relative diagnostic, and its unmasked stratum each need a rerun.
- Committed result files keep their recorded fields, misleading ones included. The documents now qualify those fields.

## Proposed next step

The owner's instruction sets the next action: commit and push this response.
After that, this record recommends probe T7, overlap on the lakes in two tiles. It reads pixels and completes Phase C's probes.
The owner's call on whole-object scaling for Sen2Cor only can come at any time. It changes only offline arithmetic.
