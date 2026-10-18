# Session handoff for a new computer, 2026-10-18

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: recorded. The owner asked for this handoff, its commit, and its push. It starts no step.

## For the owner

- The next session opens on a different computer from a fresh clone. This record says where the work stands and what the clone lacks.
- No step is in progress. The owner is reviewing the rebuilt Prototyping tab by hand.
- A fresh clone failed one link test. A record of 2026-09-18 linked a file under the ignored `data/` folder. This step makes that link plain text.
- The 4.3 GB `data/` folder stays on the old computer unless the owner copies it. Two generator checks and the T7 dry run need it.

## Step and authorization

The owner wrote:

> "We are going to close out this session here and start up again on a different computer. Make a new for our next session to pick up, then commit and push"

This record is that handoff. The step changes no code, result file, or page, and it contacts no provider.
Deferred: every open thread listed below.

## Where the work stands

- The last commit before this record is `6d9a8dc`, pushed to `origin/main` on 2026-10-15. The working tree was clean.
- The latest step is the [Prototyping tab rebuild](2026-10-15-prototyping-tab-rebuild.md). That step fixed Codex's nine accuracy findings and ran the plain-English pass.
- Decisions in force: [0008](../decisions/0008-acolite-aquatic-reflectance-first.md), ACOLITE first, [0009](../decisions/0009-standalone-options-join-deferred.md), standalone options with the join deferred, and [0010](../decisions/0010-primary-tile-rule.md), one fixed primary tile.
- Assumption A52 holds. The assessment forms no view on which atmospheric correction performs better.
- Phase C's pixel probes T4 to T7 are complete. Probe T8 and the optional T9 remain, each with its own authorization.

These records await the owner's review:

| Date | Record | Status |
|---|---|---|
| 2026-10-13 | [Phase A re-scope](2026-10-13-phase-a-rescope.md) | Awaiting owner review |
| 2026-10-13 | [Phase B, Discovery II](2026-10-13-phase-b-discovery-ii.md) | Awaiting Codex and the owner |
| 2026-10-13 | [Phase B claim validation](2026-10-13-phase-b-claim-validation.md) | Corrections applied, awaiting owner review |
| 2026-10-13 | [Processor performance direction](2026-10-13-processor-performance-direction.md) | Awaiting owner review |
| 2026-10-13 | [Probe T4, pixel validity](2026-10-13-phase-c-t4-validity.md) | Awaiting further review |
| 2026-10-14 | [Standalone options direction](2026-10-14-standalone-options-direction.md) | Awaiting Codex and the owner |
| 2026-10-14 | [Probes T5 and T6](2026-10-14-phase-c-t5-t6.md) | Awaiting review |
| 2026-10-14 | [Cost model per option](2026-10-14-phase-c-cost-options.md) | Awaiting review |
| 2026-10-14 | [Adversarial review response](2026-10-14-adversarial-review-response.md) | Awaiting review |
| 2026-10-15 | [Probe T7, overlapping tiles](2026-10-15-phase-c-t7-overlap.md) | Awaiting review |
| 2026-10-15 | [Primary tile and compression direction](2026-10-15-primary-tile-and-compression-direction.md) | Awaiting Codex and the owner |
| 2026-10-15 | [Prototyping tab rebuild](2026-10-15-prototyping-tab-rebuild.md) | Awaiting the owner's review by hand, with five choices listed for correction |

## Setting up the new computer

1. Clone the repository and open it in Claude Code.
2. Read [CLAUDE.md](../../CLAUDE.md), this record, and the [rebuild record](2026-10-15-prototyping-tab-rebuild.md).
3. Install `uv`.
4. Run `uv sync --locked`. It pins Python 3.12.13 and the prototype group.
5. Run `/check`, or the four CI steps under [Commands](../../CLAUDE.md#commands).
6. Run the `--check` of `collate_checks`, `collate_sensor_bands`, `render_options`, `gap_report`, and `estimate_aws_costs`.
7. Clone the owner's `cc-skills` repository to `~/github/cc-skills`.
8. Run the review-comment layer check from [CLAUDE.md](../../CLAUDE.md#commands). It uses the cloned `inject.py`.
9. If Codex reviews continue, install and sign in to the Codex CLI.

The last Codex review ran `codex exec -s read-only -C <repository>`, with the prompt on standard input and `-o` naming the output file.
The step 6 checks need no local data. They passed in a fresh clone, listed under verification.

## What stays on the old computer

The `data/` folder holds 4.3 GB of raw listings, frozen plans, run directories, and declared-rule timestamps.
Git ignores it, and assumption A25 keeps measurements on the owner's laptop. Copying it is the owner's call. Never commit it.

| What needs it | Folder | Size |
|---|---|---|
| `tools/backtest_source_bytes.py --check` | `data/lazy-reader-workloads/2026-09-21-sleep-rerun/` | 465 MB |
| `tools/backtest_aqr_source_bytes.py --check` | `data/aqr-workloads/2026-10-14-run/` | 744 MB |
| `benchmarks/aqr_overlap.py --dry-run` and any T7 rerun | `data/aqr-workloads/2026-10-14-run/` and `data/cross-tile-extraction/full-plan.catalog.json` | 744 MB and part of 384 MB |
| The rules-declared-first timestamps of probes T4 to T7 | `declared-before-run.txt` in each probe folder | Small |
| The checkpoint of the 2026-09-18 restart | `data/restart-handoff/` | 340 KB |

Without `data/`, the two back-test checks stop with "Saved local frozen inputs are required. No data will be fetched."
The other dry runs in [CLAUDE.md](../../CLAUDE.md#commands) work in a fresh clone.
`docs/archive/` holds 12 superseded documents, also ignored by git. Nothing links to it.
Claude Code's memory folder on the old computer does not travel. The next section carries what matters from it.

## Working practices carried over

- The owner asked for "more plain english and less AI-ese like 'not this, but that'". Use plain labels such as "initial preference", and keep text short.
- New results go in the current phase's tab as brief definitions and one table, without editorializing. Later tabs stay placeholders unless the owner asks.
- Commits go straight to `main`, usually one per authorized step, and only on the owner's word.
- Quote every heredoc delimiter, `<<'EOF'`. On 2026-10-15 an unquoted heredoc ran a probe command through backticks. The [T7 record](2026-10-15-phase-c-t7-overlap.md) discloses it.
- Before stopping a background launcher, check whether it already started workers. On 2026-10-14 this interrupted one T6 run, replaced with the owner's authorization.
- Never run `pytest` while `render_options.py` writes the page.
- Check each AI reviewer's claim against the sources before acting on it. One claim in the 2026-10-14 adversarial review was wrong.
- `test_supervisor_stops_a_real_worker_and_descendant` can fail under memory pressure and pass alone. Never change the harness memory limits to fit a run.
- Under assumption A52, argue neither processor's accuracy from the literature.

## Open threads

Each thread needs the owner's authorization.

| Thread | Where it is recorded |
|---|---|
| The owner's hand review of the Prototyping tab and its five listed choices | [Rebuild record](2026-10-15-prototyping-tab-rebuild.md#choices-this-record-made) |
| Probe T8, retention: object timestamps and entity tags over several weeks, plus a written question to USGS. It reads no pixel | [Replan record](2026-10-13-acolite-first-replan.md) |
| Probe T9, one self-run ACOLITE scene, only if the owner asks | Replan record |
| T5 reruns for the floating-point threshold, a relative diagnostic, and a stratum without the masking flag bit | [Review response](2026-10-14-adversarial-review-response.md) |
| A request back-test for ACOLITE only, item S9 | Review response |
| The four Lanier overlap pairs across UTM zones 16 and 17, listed and not compared | [Measurements](../measurements.md), finding 39 |
| `inputs.json` still carries `revision_date` 2026-09-23. Changing it regenerates the estimates, a cost-model step | Rebuild record, choice 5 |
| Finding 35 and the T5 heading still say "same pixels". The page links to that heading | Rebuild record |
| Findings of the 2026-09-23 [final accuracy review](2026-09-23-claude-final-page-accuracy-review.md) on text outside the rebuilt tab | Rebuild record, limits |
| Phases D to F: scientific checks, integration specs, and tradeoffs | [Work plan](../work-plan.md) and the replan record |

The owner closed the compression analysis on 2026-10-15 by keeping it at a high level. No new measurement is planned.

## What changed

| File | Change |
|---|---|
| This record | New |
| [Reviews index](README.md) | One row for this record |
| [CLAUDE.md](../../CLAUDE.md) | One sentence pointing to this record |
| [Geometry blocker assessment](2026-09-18-claude-geometry-blocker-assessment.md) | The refinement log path is plain text, marked as ignored by git. Its link into `data/` broke `test_relative_links_resolve` in a fresh clone |

## Verification

A fresh clone of `6d9a8dc` in a scratch folder, with no `data/` folder, gave these results:

- `uv sync --locked` from the local uv cache, `ruff check`, and `ruff format --check` passed.
- `pytest` passed 408 tests and failed 1, the link fixed above.
- The `--check` of `collate_checks`, `collate_sensor_bands`, `render_options`, `gap_report`, and `estimate_aws_costs` passed.
- The review-comment layer check passed.
- Every documented dry run passed except T7's, which needs `data/`.
- The two back-test checks stopped as expected.

With this step's changes copied into that clone, `pytest` passed all 410 tests in 38 s, and the five checks still passed.
In this working tree, `/check` passed 410 tests in 38 s.

## Limits

- The broken link entered in `b0e911c` on 2026-09-22. CI runs on every push, so GitHub CI has probably failed since then. The `gh` CLI is not installed here, so this record did not check.
- The fresh clone reused this computer's uv cache. A new computer downloads the locked packages instead.
- The list of open threads comes from the records above. Their own text governs.

## Proposed next step

The owner finishes the hand review of the Prototyping tab. The next session starts no step until the owner authorizes one.
