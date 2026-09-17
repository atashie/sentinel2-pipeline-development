# Wording pass over the presentation, 2026-09-17

Implementer: Claude Code (AI coding agent), directed by the repository owner. Status: ready for owner and Codex review after the checks recorded below.

Scope: every visible sentence on the [page](../s2-options.html), the map view descriptions in its script, and the inventory issue lines the page prints. No fact, number, link, figure, or layout changed. No script contacted a provider.

## The owner's direction

Clean up the page's language with two rule sets. Plain English for the summary text: the hero, chapter introductions, "The choice", "Why both matter", takeaways, and the closing line. Simplified Technical English for tables, captions, technical-detail bullets, source notes, map details, and the issue bullets.

## What the page already passed

Before this pass, no visible sentence exceeded 25 words. The page had no semicolon, no "should", no em dash, and none of the banned vocabulary. The earlier [plain-language pass](2026-09-11-plain-language-pass.md) and Codex's prose audit of 2026-09-17 had removed those.

## What changed

The [template](../../tools/s2-options.template.html) diff has 145 changed lines. The changes fall into eight kinds.

| Kind | Rule | Examples |
|---|---|---|
| Modals | "may", "could", and "would" become "can" or a restructured sentence | "A pond only 10 m across can have no pixel entirely inside it." "If a reader applies the catalog's offset again, it subtracts the offset twice." |
| Tense | Present perfect becomes simple past or present | "Local prototypes timed preparation and extraction." "We did not benchmark them here." |
| Conditions first | A condition precedes its command | "If Collection 1 lacks the product, use the older copy." "When an analysis combines grids, make the resampling explicit." |
| "-ing" clauses | A trailing participle clause becomes a sentence | "Time covers per-file access and decoding. It excludes digest and statistics work." |
| Contrast constructions | "X, rather than Y" becomes two statements | "This measures one recipe. It does not set a limit for lazy reading." "The illustration groups information. It does not specify a quality join." |
| One name per thing | "retain" and "preserve" become "keep". The per-pixel "coverage" becomes "water fraction". "near-land" becomes "nearby land". "buffered support" becomes "buffered area". "product segments" becomes "datastrips". "satellite pass" becomes "acquisition" on the Prototyping tab. "the older archive" becomes "the older copy". "primary rule" and "primary roles" become "primary-tile rule" and "primary-tile roles" | The route step "Preserve" is now "Keep". "Do methods agree on values?" replaces "Do methods preserve values?" |
| Abstract subjects and false limbs | A concrete subject does the work | "A catalog entry does not prove a usable water observation." "Grid coverage does not prove valid measurements." "A run that fits on a laptop is not proof of a run without memory pressure." |
| Spelling | The page's own text uses American spelling throughout | "meter", "center", "colored", "water vapor", "cataloging" |

Two renderer strings changed for the same reasons: the coverage strip's title now says "older copy", and the Stage 3 table cell says "not read in Stage 2". The renderer test expects the new cell text.

Six inventory `plain` lines changed, in issues I-05, I-08, I-09, I-16, I-26, and I-30. They lose "may", one present perfect, and one "-ing" clause. The inventory's other fields are untouched. `tools/collate_checks.py --check` still matches.

"Coverage" now means one thing on the page: which tiles, months, or extents cover a place. The per-pixel quantity is "water fraction" everywhere, including the record card.

## What did not change

- Every measured number, date, machine label, and link. The rendered table rows are generated from the frozen results.
- Contrasts that carry information stay: "Blue means a higher index, not better water quality", "Near-infrared measures reflected light, not temperature", "Working picture, not a selected layout".
- Passive sentences whose participle is an adjective or whose agent is unknown: "The fallback order is settled", "Run order and network conditions were uncontrolled", "No production workflow is selected".
- The headlines "Share open files before reading whole tiles" and "Change how the reads are shared" keep their rhythm.
- Spelling in the inventory. The owner then chose American spelling for the whole repository, applied in the [spelling record](2026-09-17-american-spelling.md).
- The attribution sentence "Contains modified Copernicus Sentinel data (2025), served by Element 84".

## Checks

| Check | Result |
|---|---|
| `uv sync --locked`, `ruff check`, `ruff format --check` | Pass. One renderer line was rewrapped to 100 characters |
| `uv run pytest -q` | 200 passed in 12.65 seconds, existing library deprecation warnings only |
| The three `--check` tools and `git diff --check` | Inventory, page, and gap report match their inputs |
| Sentence audit of every visible sentence, 8,451 words | No sentence over 25 words. No "should", "may", "might", "could", "would", present perfect, semicolon, contraction, Latin abbreviation, trailing "-ing" clause, or em dash outside the inventory's own lines |
| Term scan | No "retain", "preserve", "near-land", "buffered support", "product segment", "rather than", or "older archive" in the visible text |
| Cached headless Chromium, 1280 px, both tabs | The page renders as before. Longer table cells wrap inside their columns. Text changes only |

The audit script is a session scratch file, not part of the repository.

## Limits

The tone of the rewritten sentences is the owner's call. The pass applied the rules of the two skills, and broke a rule only where the sentence would otherwise read worse. The Discovery risk bullets keep the inventory's wording, so the Discovery tab still mixes "pass" from the inventory with "acquisition" from the template.

## Proposed next step

Owner and Codex review of the wording. Then the review of the [documentation and presentation update](2026-09-17-documentation-and-presentation.md) continues as planned. No commit, push, or deployment was performed.
