# Owner direction: the primary-tile rule and the compression analysis, 2026-10-15

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: recorded. Awaiting review by Codex and the owner.

## For the owner

- Each water body now has one fixed primary tile, chosen in the UTM zone of its centroid first, then by the largest buffered share. [Decision 0010](../decisions/0010-primary-tile-rule.md) records it.
- Shares within 1 percentage point tie, and the smaller tile id wins. A date when the primary tile lacks data is missing.
- The cost compression analysis stays at a high level. The [cost analysis](../aws-cost-analysis.md#two-standalone-options) now lists its limits in four lines.
- Two parts of decision 0010 are this record's readings, listed below for correction.

## Step and authorization

After the T7 commit cycle, Claude Code described the two open calls in chat, with options and recommendations. The owner replied:

> "Call 1: a high level comparison is fine for now; simply succinctly note any limitations of our compression analysis and let's move on; a small difference here is not going to substantially alter our decision. Recarding the decisions and your recommendations: 1) agreed; 2) agreed; 3) agreed; 4) agreed"

The four numbered items were the decisions the chat listed for the primary-tile rule, each with its recommended answer:

| Item | Question | Recommended answer, now agreed |
|---|---|---|
| 1 | Fixed per water body, or chosen per date | One fixed tile per water body |
| 2 | The measure | The largest share of the buffered polygon inside the tile |
| 3 | The tie margin and tiebreak | Shares within 1 percentage point tie. The smaller tile id wins |
| 4 | Zone preference | Tiles in the UTM zone of the polygon's centroid come first |

This step records the direction in a decision, the assumptions, the contract, the practices, the inventory, the page, and the cost analysis. It runs no provider script.
Deferred: applying the rule to stored memberships, any fill from overlap tiles, and the Prototyping tab rebuild.

## How this record reads the direction

- **No switching.** The chat's recommendation added that a date without data on the primary tile is missing, with overlap values kept. Decision 0010 includes it, matching decision 0009's treatment of missing scenes.
- **Both options.** The chat recommended the same tile under ACOLITE only and Sen2Cor only. Decision 0010 includes that too. Both options share the tiling.
- **Compression.** The owner's call keeps the central estimates as they are: ACOLITE only with whole-object scaling, Sen2Cor only under decision 0006. No new measurement is planned.

## What changed

| Area | Change |
|---|---|
| [Decision 0010](../decisions/0010-primary-tile-rule.md) | New. Replaces the primary tile provision of decision 0003 and the provisional rule of assumption A22 |
| [Decisions index](../decisions/README.md) and [decision 0003](../decisions/0003-earth-search-2021-first-gap-survey-cross-tile.md) | The new row, and a note that 0010 replaced the provision |
| [assumptions.md](../assumptions.md) | Row A22 states the decided rule, status sourced |
| [data-contract.md](../data-contract.md) and [s2-best-practices.md](../s2-best-practices.md) | `tile_role` and practice P2 cite decision 0010 |
| [Inventory](../options-inventory.json) | Issue I-30's consequence and decision, and the next steps |
| [aws-cost-analysis.md](../aws-cost-analysis.md#two-standalone-options) | The limits of the compression analysis, with the owner's direction |
| Page and planning documents | Two page sentences, the [work plan](../work-plan.md), and [CLAUDE.md](../../CLAUDE.md) |

## Verification

| Command | Outcome |
|---|---|
| `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .` | Pass |
| `uv run pytest -q` | 401 passed, 13,000 existing warnings |
| `collate_checks`, `collate_sensor_bands`, `render_options`, `gap_report`, and `estimate_aws_costs`, each with `--check` | All current |
| The review-layer `inject.py --check` | Up to date |
| Style scans of the changed Markdown and inventory text | Only the owner's verbatim quote and one earlier sentence of practice P2 exceed 25 words |

## Proposed next step

The owner named the Prototyping tab rebuild as the next step, after a memory compaction. It contacts no provider.
