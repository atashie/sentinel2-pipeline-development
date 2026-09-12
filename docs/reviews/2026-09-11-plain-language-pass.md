# Plain-language pass over the Discovery page, 2026-09-11

Implementer: Claude Code (AI coding agent), directed by the repository owner. Scope: every visible sentence on the Discovery page, including map captions and the JavaScript view descriptions. No fact changed. No layout changed.

## The owner's direction

Plainer English. Fewer contrast constructions of the form "not this, but that". Plain labels, for example "initial preference" instead of "our lean". Shorter where possible.

## What changed

- About forty sentences reworded across the hero, all five Discovery sections, the map captions, and the phase placeholders. Fragment stacks such as "Read less. Reuse work. Preserve meaning." became one sentence. "Our lean" became "Initial preference". "Source-access charge" became "Cost to read".
- Status tails of the form "Schematic, not an extraction result" became "Schematic only" or a separate short sentence. Where the contrast carries information, for example that near-infrared measures reflected light rather than temperature, it stays.
- Codex's expandable archive-history block kept its facts and counts. Two of its sentences were split or simplified.
- The inventory's issue lines, which the page prints as bullets, were reviewed and left unchanged. They are already plain.

## Evidence

Every reworded sentence carries the same claim as before, sourced to the same documents. The [template](../../tools/s2-options.template.html) diff against the [previous record](2026-09-11-archive-section-condensed.md) is the change.

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. 47 files formatted |
| `uv run pytest` | 67 passed |
| The three `--check` tools | Inventory, page, and report match their inputs |
| Sentence audit of every visible sentence and the map view descriptions | No sentence over 25 words, no semicolon, no "should" |
| Scan for contrast constructions | Four remain, each carrying information: two "not requester pays" cells, one Copernicus-only note, and near-infrared measuring light rather than temperature |
| Headless Chromium, 1440 px | The page renders as before. Text changes only |

## Limits

The page's tone is now the owner's call to judge. The pass did not touch the inventory, the measurements, or the decisions.

## Proposed next step

Owner review of the wording. Then commit authorization, the first Vercel deployment, decision 0004, and prototyping. No commit, push, or deployment was performed.
