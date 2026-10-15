# Phase C, step 5: probe T7, one option's values in two overlapping tiles, 2026-10-15

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: delivered. Probe T7 is complete. Awaiting review.

## For the owner

- T7 compared each option with itself, the same lake pixels in two overlapping tiles of one UTM zone. Eight tile pairs, two acquisitions, five lakes.
- Both options' tiles agree within 0.005 reflectance on nearly every overlap pixel. The one exception is Sen2Cor's 60 m B01 at the shore.
- ACOLITE's per-tile aerosol fitting does not widen tile disagreement against Sen2Cor's, in any band and class. That answers the replan record's T7 question for these pairs.
- Both options carry small tile offsets, a median of up to a few thousandths per pair. Picking one tile per lake picks those offsets, assumption A22.
- ACOLITE's flags differ between tiles less often than Sen2Cor's scene classification, most at the shore: 0.44 against 9.75 percent.
- No catalog was queried. The measured run requested 530 MB from the two public buckets, unsigned.
- A shell quoting error by Claude Code launched the probe a second time after the run. It was stopped within about three minutes and wrote no result, section below.

## Step and authorization

On 2026-10-14 the owner wrote "proceed with the next steps", then the commit and review sequence, ending "before proceeding to subsequent steps".
After the push of `519ded6`, this record took probe T7 as the next step. When the T7 design was under way, the owner wrote "proceed" on 2026-10-15.
[The replan record](2026-10-13-acolite-first-replan.md) defines T7: an overlap test on the lakes in two tiles. It asks whether per-tile aerosol fitting widens tile disagreement.
Stage 4 kept value digests, not values, so T7 reads pixels again. It reads only pixels. Every item comes from saved catalogs, so no catalog was queried.
Acceptance checks, per the replan record: declared tolerances, a result file, findings, and a record.
Deferred: probe T8, the Prototyping tab rebuild, pairs across UTM zones, and any change to decisions 0008 and 0009.

## What changed

| Area | Change |
|---|---|
| [overlap.py](../../src/s2proto/overlap.py) | New pure module. Rules O1 to O9, the zone pairing, the pixel offset between tiles, and the verdicts |
| [aqr_overlap.py](../../benchmarks/aqr_overlap.py) | New probe T7 script. Reads each lake's overlap pixels from both tiles of each option. `--dry-run` contacts nothing |
| `tests/test_aqr_overlap.py` | 7 fixture tests, no network. Pairing, offsets, clipping, verdicts, 60 m alignment, and exact quarter units |
| [aqr-overlap.json](../../benchmarks/results/aqr-overlap.json) | The result, written by the script |
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
| O7 | Tile agreement. Tiles agree when at least 90 percent of pixels differ by 0.005 reflectance or less. Under 100 pixels, no verdict |
| O8 | Widening. On the shared sets, ACOLITE widens tile disagreement when its share beyond 0.005 exceeds Sen2Cor's by more than 5 points |
| O9 | Diagnostic. The share of overlap pixels whose quality code differs between the tiles |

## Method

The probe takes T6's stage 4 plan: Lake Lanier on 2025-10-15 and Lake Okeechobee on 2025-10-31, with their tiles, products, and member lakes.
Each product's paired Collection 1 item comes from the saved Level-2A stage 4 catalog. Both inputs are local files whose digests the result records.
For a pair, one lake mask on tile A's 20 m grid maps onto tile B by a whole-pixel offset. The probe reads only the overlap pixels from both tiles.
It reads the product's 11 bands and flags layer, and the Collection 1 item's 11 bands and scene classification, for both tiles.
Differences are taken in stored integers, so Collection 1's declared offset cancels and quarter units stay exact. T5's floating-point limit at the threshold does not arise.

## What T7 found

[Findings 38 and 39](../measurements.md#phase-c-probe-t7-each-option-across-two-overlapping-tiles-2026-10-15) own the numbers. In short:

- All 8 same-zone pairs aligned on one grid, with whole 60 m offsets. The 4 Lanier pairs across zones 16 and 17 were listed and not compared.
- Under rule O7, each option's tiles agree in every band, class, and subset but one. Sen2Cor's B01 differs in shoreline and near-land, 15.1 and 12.3 percent beyond 0.005.
- Over interior pixels, at most 0.06 percent of any band other than B01 differs between tiles by more than 0.005, in either option.
- Median tile differences run from -9 to +2 units for ACOLITE and +1 to +25 for Sen2Cor. Per pair they reach 55 and 43 units in B01.
- Under rule O8, ACOLITE is similar to Sen2Cor everywhere, and narrows the disagreement in shoreline and near-land B01.

## An accidental second launch

After the measured run, Claude Code wrote this record through a shell command whose text was not quoted. The shell ran a command quoted in the text, the full probe.
That launch started at 12:10:18 UTC and was stopped about three minutes later, before it wrote a result. Its only file is `data/aqr-overlap/2026-10-15T121018+0000/plan.txt`.
Its output went to the failed command, so its requests are not logged. They were unsigned range reads from the same two public buckets, at most two pairs' worth.
The result file still holds the measured run of 12:02:03 UTC. Its contents and modification time predate the accidental launch.

## Evidence

| Run | Requests | Read |
|---|---|---|
| Dry run, offline offsets and window sizes | None | Local plan and catalog only |
| Smoke run, Lanier pair 16SGC-16SGD, one lake, output under the session scratchpad | 56 GDAL ranges per bucket | 8.7 MB from the product, 17.3 MB from Collection 1, 48 s |
| Full run, `uv run python benchmarks/aqr_overlap.py` | 624 product ranges, 627 Collection 1 ranges | 178.8 MB from the product, 351.6 MB from Collection 1, 349 s |
| Accidental launch at 12:10:18 UTC, stopped | Not logged | No result |

Payer: the bucket owners. Every request was unsigned. A requester-pays bucket refuses unsigned requests.
The buckets are `usgs-wma-sentinel-2-aqr-acolite-dsf` and `e84-earth-search-sentinel-data`, both in us-west-2. The machine was the owner's laptop over the internet, assumption A25.
The full run started at 12:02:03 UTC and completed at 12:07:52 UTC. Its source digests equal the declared ones. Logs are under `data/aqr-overlap/`, outside git.

## Verification

| Command | Outcome |
|---|---|
| `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` | Pass |
| `uv run pytest -q` | 395 passed, 13,000 existing warnings |
| `collate_checks`, `collate_sensor_bands`, `render_options`, `gap_report`, and `estimate_aws_costs`, each with `--check` | All current |
| The review-layer `inject.py --check` | Up to date |
| Style scans of the changed Markdown and inventory text | No sentence over 25 words, no semicolon, no forbidden modal |

## Limits

- Two acquisitions, both in October 2025, at two lakes. Lake Okeechobee holds 82 percent of interior observations.
- Corner pixels at Lake Okeechobee repeat across four pairs, and neighboring pixels are correlated.
- Overlap pixels lie near tile edges. Tile interiors may behave differently.
- Pairs across UTM zones need resampling, and none was compared.
- Each option is compared with itself. Neither tile and neither option is a reference, assumption A52.
- This record and its findings are an AI agent's work, reviewed by tests only so far.

## Dispositions

| Prior item | Disposition |
|---|---|
| Replan record: T7, the overlap test on lakes in two tiles | Fixed. Findings 38 and 39 |
| T5 and T6 record: T7 needs its own read, since stage 4 kept digests | Fixed. T7 read the overlap pixels |
| Review response and cost record: proposed next step T7 | Fixed |
| Issue I-30, cross-tile mosaicking | Accepted and deferred. T7 adds evidence on two acquisitions. The store still never mosaics, and the issue stays open |
| Replan record: the primary-tile tie rule of assumption A22, to be informed by T7 | Accepted and deferred. The rule stays the owner's decision |

## Proposed next step

Phase C's pixel probes are complete. This record recommends the Prototyping tab rebuild next, which contacts no provider.
Probe T8, retention, reads metadata only and can run alongside. Each needs the owner's authorization.
Two owner calls stay open: whole-object scaling for Sen2Cor only's cost, and the primary-tile rule.
This record starts none of them, and nothing from T7 is committed.
