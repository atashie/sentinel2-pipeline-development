# Phase C, step 5: probe T7, each option across two overlapping tiles, 2026-10-15

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered, committed as `826bb14` on the owner's instruction "same commit cycle fo t7", then revised after its adversarial review. Awaiting review.

## For the owner

- T7 compared each option with itself: the same lake pixels in two overlapping tiles of one UTM zone. Eight tile pairs, two acquisitions, five lakes.
- Pooled over pairs, both options' tiles agree within 0.005 reflectance on nearly every pixel. Sen2Cor's B01 at the shore is the pooled exception.
- Pair by pair, both options' tiles disagree more. ACOLITE's B01 differs on 79 to 100 percent of pixels at one Okeechobee corner pair. Sen2Cor's B01 differs at six pairs.
- Relative to the dark-water signal, tile offsets reach tens of percent in both options, up to 70 percent for ACOLITE and 36 percent for Sen2Cor.
- Pooled, rule O8 finds no widening by ACOLITE. Per pair it widens in 4 strata and narrows in 32. At that corner pair its offsets fall with wavelength, as an aerosol difference would.
- The test has little power below 0.005, where both options' shares sit near zero. The worst pairs involve corner tiles that hold 75 to 94 percent no-data.
- A shell quoting error by Claude Code launched the probe a second time after the run. It was stopped within minutes and wrote no result, section below.

## Step and authorization

On 2026-10-14 the owner wrote "proceed with the next steps", then the commit and review sequence, ending "before proceeding to subsequent steps".
After the push of `519ded6`, Claude Code took probe T7, the next step the review response proposed, and wrote its code and rules.
On 2026-10-15 the owner wrote "proceed". This record reads that message as authorizing T7. No pixel was read before it.
The owner then wrote "same commit cycle fo t7", which set the commit, review, and push that follow.
[The replan record](2026-10-13-acolite-first-replan.md) defines T7: an overlap test on the lakes in two tiles. It asks whether per-tile aerosol fitting widens tile disagreement.
Stage 4 kept only value digests, so T7 read pixels again. It read only pixels. Every item came from saved catalogs, so no catalog was queried.
Acceptance checks, per the replan record: declared tolerances, a result file, findings, and a record.
Deferred: probe T8, the Prototyping tab rebuild, pairs across UTM zones, and any change to decisions 0008 and 0009.

## What changed

| Area | Change |
|---|---|
| [overlap.py](../../src/s2proto/overlap.py) | New pure module. Rules O1 to O9, the zone pairing, the pixel offset between tiles, and the verdicts |
| [aqr_overlap.py](../../benchmarks/aqr_overlap.py) | New probe T7 script. Reads each lake's overlap pixels from both tiles of each option. `--dry-run` contacts nothing. `--resummarize` adds diagnostics offline |
| `tests/test_aqr_overlap.py` | 11 fixture tests, no network. Pairing, offsets in both axes, clipping, resampling, layer checks, verdicts, relative offsets, and exact quarter units |
| [aqr-overlap.json](../../benchmarks/results/aqr-overlap.json) | The result, written by the script, with diagnostics added by `--resummarize` |
| [measurements.md](../measurements.md#phase-c-probe-t7-each-option-across-two-overlapping-tiles-2026-10-15) | Findings 38 and 39 and what T7 does not show |
| [Inventory](../options-inventory.json) | Probe PR-15, bearing on issues I-30 and I-31 |
| Planning documents | The [work plan](../work-plan.md), [CLAUDE.md](../../CLAUDE.md), [README.md](../../README.md), and the [benchmarks index](../../benchmarks/README.md) |

## Rules declared before the read

One shell command wrote the UTC time, `shasum -a 256` source digests, and the `--dry-run` output to `data/aqr-overlap/declared-before-run.txt`. The time is 2026-10-15T12:00:45+00:00.
The smoke run started after that, and the full run used the same source digests. Rule P7's tolerance and agreement share carry over from T5.

| Rule | What it fixes |
|---|---|
| O1 | Pairs. Two tiles of one stage 4 region that share a UTM zone and a member lake. Pairs across zones are listed and not compared |
| O2 | Grid. One CRS, origins a whole number of 20 m pixels apart, every layer on its own tile grid within 1e-6 pixel. B01 needs whole 60 m offsets |
| O3 | Pixels. Classes from each lake's exact polygon on the shared 20 m grid. Overlap pixels lie inside both tiles |
| O4 | Units. Integers of 1e-04 reflectance. Collection 1 with rule P3's resampling and one declared scale and offset per band. Tile A minus tile B |
| O5 | Comparable. Both tiles hold data. The shared set holds pixels comparable in both options |
| O6 | Strata. Option, band, and pixel class. All pixels, own clear water in both tiles, the shared set, and shared clear water |
| O7 | Tile agreement, pooled over pairs and lakes. Tiles agree when at least 90 percent of pixels differ by 0.005 reflectance or less. Under 100 pixels, no verdict |
| O8 | Widening, pooled. On the shared sets, ACOLITE widens tile disagreement when its share beyond 0.005 exceeds Sen2Cor's by more than 5 points |
| O9 | Diagnostic. The share of overlap pixels whose quality code differs between the tiles |

## Method

The probe takes T6's stage 4 plan: Lake Lanier on 2025-10-15 and Lake Okeechobee on 2025-10-31, with their tiles, products, and member lakes.
Each product's paired Collection 1 item comes from the saved Level-2A stage 4 catalog. Both inputs are local files whose digests the result records.
For a pair, one lake mask on tile A's 20 m grid maps onto tile B by a whole-pixel offset. The probe reads only the overlap pixels from both tiles.
It reads the product's 11 bands and flags layer, and the Collection 1 item's 11 bands and scene classification, for both tiles.
Differences are taken in stored integers, so Collection 1's declared offset cancels and quarter units stay exact. T5's floating-point limit at the threshold does not arise.
After the review, `--resummarize` added post-run diagnostics from the stored per-pair statistics: per-pair verdicts, relative offsets, and tile metadata. None is a rule.

## What T7 found

[Findings 38 and 39](../measurements.md#phase-c-probe-t7-each-option-across-two-overlapping-tiles-2026-10-15) own the numbers. In short:

- All 8 same-zone pairs aligned on one grid, with whole 60 m offsets. The 4 Lanier pairs across zones 16 and 17 were listed and not compared.
- Pooled under rule O7, each option's tiles agree everywhere except Sen2Cor's shoreline and near-land B01, 12 to 19 percent beyond 0.005.
- Per pair, ACOLITE fails in 5 strata and Sen2Cor in 25. ACOLITE's failures sit at Okeechobee's corner, mostly B01 at 17RML-17RNK.
- Absolute median tile differences over interior pixels reach 55 units for ACOLITE and 43 for Sen2Cor, both in B01. Over dark water that is tens of percent of the signal.
- Pooled under rule O8, ACOLITE never widens the disagreement. Per pair it widens in 4 strata of the shared set and narrows in 32.

## An accidental second launch

After the measured run, Claude Code wrote this record through a shell heredoc whose delimiter was not quoted. A backticked command in the text ran as command substitution.
That command was the full probe. The launch broke the rule in CLAUDE.md that provider scripts run only when the user invokes them.
It started at 12:10:18 UTC, by its plan file `data/aqr-overlap/2026-10-15T121018+0000/plan.txt`. Claude Code stopped it a few minutes later, before it wrote a result.
Its output went to the failed command, so its reads are not logged. At the full run's pace, three minutes cover about the first three pairs.
That is roughly 80 MB from the product and 160 MB from Collection 1, unsigned, from the same two public buckets.
The result file holds the measured run of 12:02:03 UTC. Its contents and modification time predate the launch.
Claude Code now quotes every heredoc delimiter that carries document text.

## Evidence

| Run | Requests | Read |
|---|---|---|
| Dry run, offline offsets and window sizes | None | Local plan and catalog only |
| Smoke run, Lanier pair 16SGC-16SGD, one lake. Plan file under `data/aqr-overlap/2026-10-15T120052+0000/`, summary kept outside the repository | 56 GDAL ranges per bucket, from the run's printed summary | 8.7 MB from the product, 17.3 MB from Collection 1, 48 s |
| Full run, `uv run python benchmarks/aqr_overlap.py` | 624 product ranges, 627 Collection 1 ranges | 178.8 MB from the product, 351.6 MB from Collection 1, 349 s |
| Accidental launch at 12:10:18 UTC, stopped | Not logged | No result. An estimated 240 MB |
| Diagnostics, `--resummarize` | None | Stored statistics and the saved catalog |

The step requested about 556 MB in the logged runs, plus the unlogged launch. Payer: the bucket owners. Every request was unsigned.
The buckets are `usgs-wma-sentinel-2-aqr-acolite-dsf` and `e84-earth-search-sentinel-data`, both in us-west-2. The machine was the owner's laptop over the internet, assumption A25.
The full run started at 12:02:03 UTC and completed at 12:07:52 UTC. Its source digests equal the declared ones. Logs are under `data/aqr-overlap/`, outside git.

## Verification

| Command | Outcome |
|---|---|
| `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` | Pass |
| `uv run pytest -q` | 399 passed, 13,000 existing warnings |
| `uv run python benchmarks/aqr_overlap.py --resummarize benchmarks/results/aqr-overlap.json` | Diagnostics added. Every earlier field is unchanged |
| `collate_checks`, `collate_sensor_bands`, `render_options`, `gap_report`, and `estimate_aws_costs`, each with `--check` | All current |
| The review-layer `inject.py --check` | Up to date |
| Style scans of the changed Markdown and inventory text | No sentence over 25 words, no semicolon, no forbidden modal |

## Limits

- Two acquisitions, both in October 2025, at two lakes. Lake Okeechobee holds 82 percent of interior observations.
- The corner's 12,927 interior pixels repeat across six pairs. The replicate unit is closer to the 8 pair-dates than to the pixels.
- Both options' shares beyond 0.005 sit near zero in most bands, so rule O8 has little power there. Relative offsets carry more of the result.
- Signed differences depend on tile name order. Per-pair absolute medians and relative offsets avoid that.
- Overlap pixels lie at tile edges, and the worst pairs involve tiles with 75 to 94 percent no-data. Tile interiors may behave differently.
- Pairs across UTM zones need resampling, and none was compared. The small lakes contribute almost no interior pixels.
- Each option is compared with itself. Neither tile and neither option is a reference, assumption A52.
- This record and its findings are an AI agent's work, reviewed by AI agents.

## Adversarial review of 2026-10-15

Three read-only AI reviewers read `826bb14`: one on code and rules, one on findings and framing, and one on document consistency.
Each claim was checked before any edit. The code reviewer found the geometry, reads, units, and statistics correct.

| Finding | Disposition |
|---|---|
| The pooled verdicts were presented as true of every pair. ACOLITE's B01 fails at 17RML-17RNK, and per-pair O8 shows widening there | Fixed. Findings 38 and 39, PR-15, I-30, and this record give pooled and per-pair results. Per-pair diagnostics sit in the result |
| Offsets of "a few thousandths" understate a signal of about 0.005 to 0.01 over dark water | Fixed. Relative offsets are reported per pair |
| The test has little power, and "answers the question" overstated it | Fixed. The wording now states the power limit |
| The B01 explanation by 60 m footprint is contradicted, since the 60 m grids coincide | Fixed. The cause is stated as untested |
| Pooled signed medians mix arbitrary tile order | Fixed. Per-pair absolute medians replace the signed table |
| Corner pixels repeat across six pairs, not four | Fixed |
| Distinct tiles and tile-dates were missing | Fixed in the diagnostics: 8 and 8 |
| Comparing flag-difference shares across codes with different class counts | Fixed. The comparison is stated as not comparable |
| The A22 sentence implied a fixed bias | Fixed. It states a one-date step size and that persistence is untested |
| Stale status, authorization narrative, accidental-launch estimate, and smoke evidence | Fixed |
| The inventory's next steps still listed T7 | Fixed |
| Tests missed the core logic | Fixed in part. Four tests cover the row sign, resampling, layer checks, and relative offsets. Tests of the read loop stay deferred |
| The bucket field held a hostname, and the layer check ignored the shape | Fixed in the script for later runs. The result keeps its recorded field |
| GDAL's cache outlives closed files, so per-pair byte counts depend on order | Accepted. Stated here. Totals are unaffected |
| An exact 5-point tie could tip rule O8 through floating point | Accepted and deferred. No pooled share lies near a tie |
| No datastrip or ACOLITE settings per product in the result | Accepted and deferred. Added to what T7 does not show |

## Dispositions

| Prior item | Disposition |
|---|---|
| Replan record: T7, the overlap test on lakes in two tiles | Fixed. Findings 38 and 39 |
| T5 and T6 record: T7 needs its own authorization and read | Fixed. The owner's "proceed" of 2026-10-15, then the read |
| Review response and cost record: proposed next step T7 | Fixed |
| Issue I-30, cross-tile mosaicking | Accepted and deferred. T7 adds evidence on two acquisitions. The store still never mosaics, and the issue stays open |
| Replan record: the primary-tile tie rule of assumption A22, to be informed by T7 | Accepted and deferred. The rule stays the owner's decision |

## Proposed next step

Phase C's pixel probes are complete. The owner has named the Prototyping tab rebuild as the next step, after a memory compaction.
Probe T8, retention, reads metadata only and can run alongside. Two owner calls stay open: whole-object scaling for Sen2Cor only's cost, and the primary-tile rule.
