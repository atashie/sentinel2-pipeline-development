# Codex's archive review applied, section 02 condensed, 2026-09-11

Implementer: Claude Code (AI coding agent), directed by the repository owner. Scope: review Codex's [independent archive comparison](2026-09-11-codex-archive-comparison.md) and [history correction](2026-09-11-archive-history-correction.md), then rewrite the Discovery page's archive section shorter, less prescriptive, and explicit about what remains unknown.

## Review of Codex's updates

Codex's two records are sound and change the page for the better. What they established:

- The two GeoTIFF copies overlap. Shared product identifiers occur in the saved listings, including a 2026-09-07 product cataloged in both within a minute. That is stronger evidence of parallel cataloging than probe PR-08's single 2025 item.
- The newer collection mixes processing histories too. It keeps 05.09 originals for 2023 where ESA now serves 05.10. "Longer, more consistent record" was the wrong phrase for Plan B. Longer, yes. Comparability is unmeasured.
- Quality layers differ. Older items for 2022 carry no cloud or snow probability. Some later older items link those layers as JPEG 2000. The newer collection serves every layer as GeoTIFF. Measurement finding 6.
- The explanation of why the newer copy lacks 2022 is an inference from the survey, and the page must say so. Codex's expandable history table, authorized by the owner, is kept verbatim.
- Two findings I recorded on 2026-09-11 as F-11 and F-12 never entered the inventory. Those ids already existed, and my insert guard skipped them silently. Codex caught it. They are now F-21 and F-22, and every reference is corrected.

One point where I read Codex's wording more narrowly. "Managed by Element 84" on the registry describes dataset management, as Codex says. Who owns the JPEG 2000 bucket is still stated nowhere, so the page keeps saying that.

| Codex finding | Disposition |
|---|---|
| 1, "only what ESA has reprocessed" and "every new pass" | Fixed by Codex in the table. The note line no longer promises consistency |
| 2, "same 22 files" and quality-layer delivery | Fixed. The page says 22 shared asset names, pixels not compared, and names the 2022 quality-layer gap in the table |
| 3, access charge versus processing cost | Fixed. "Source-access charge" replaces "who pays". Our own costs are named. The effort cards and the requester-pays prices are gone. Reading effort is called a judgment |
| 4, "one product per date" and "replaces the original" | Fixed. "Fewer competing versions in our sample" replaces both |
| F-11 and F-12 mislabeled | Corrected with evidence. Findings F-21 and F-22 added, references fixed |
| A13 and decision 0003 JPEG 2000 wording | Accepted and deferred to decision 0004 |
| Offset fidelity, comparability, asset completeness | Accepted and deferred to prototyping, as Codex proposed |

## What changed on the page

Section 02 is about half its previous visible length. It keeps the five-step lineage figure with shorter text and one table comparing the three copies. It keeps Codex's inference paragraph and expandable history, the measured coverage strip, and the two-plan table. Removed: the two comparison cards, the three effort cards, and one of two "why this matters" lines. Their content survives as one table row, one small paragraph, and the plans table.

The tone changed with the owner's direction. "First choice", "never touch the original", and "not used" became "likely the main source", "would read", and "context only". The heading now says why both copies exist is not clear. The new paragraph states what we infer and that the cause could sit in copying, conversion, or cataloging.

## Evidence

No new provider request. All facts on the page trace to the inventory claims and findings F-21 and F-22. The measured ones trace to measurement findings 1, 2, 6, 7, and 10, Codex's archive-history section, and probe PR-08.

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. 46 files formatted |
| `uv run pytest` | 66 passed, including Codex's tests and the archive-naming test |
| The three `--check` tools | Inventory, page, and report match their inputs |
| Headless Chromium, 1440 px and 390 px | The lineage figure, the three-copy table, the inference paragraph, the collapsed history, the coverage strip, and the plans table render. Tables scroll inside their containers on the phone |
| Sentence audit of the visible section and this record | No sentence over 25 words, no semicolon, no "should" |

## Limits

- The visible section is shorter. The expandable history table is unchanged and long by design.
- Reading effort and cost remain judgments. Nothing has been timed or priced from our side.
- Why Element 84 runs both copies is unknown. The page says so rather than guessing.

## Proposed next step

Owner review of the condensed section. Then commit authorization, the first Vercel deployment, decision 0004, and prototyping. No commit, push, or deployment was performed.
