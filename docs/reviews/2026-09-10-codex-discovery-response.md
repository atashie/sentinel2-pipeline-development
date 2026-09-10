# Response to the Codex discovery review, 2026-09-10

Author: Claude Code (AI coding agent), directed by the repository owner. Subject: the ten findings and the additions in the [Codex discovery review](2026-09-10-codex-discovery-review.md).
Every finding was checked against the cited page before it was accepted. Three pages were re-read on 2026-09-10: the Earth Search README, the SentiWiki processing page, and the two ESA baseline announcements. Nothing is committed.

## Dispositions

| Finding | Disposition | What changed |
|---|---|---|
| D01, Earth Search offset summary | fixed | The README states the offset was applied to some items during conversion. I-05, F-01, and P8 now say so. The contract replaces `offset`, `quantification_value`, and `offset_state` with `scale` and `offset` in one convention plus `conversion_source`, with the ESA-to-catalog mapping written out. |
| D02, sampled assets versus bucket contents | fixed | I-26 and F-07 report the two sampled items, name the confounding of collection, baseline, and format, and leave bucket contents unverified. I-26 is a probe. |
| D03, cloud dilation conditions | fixed, one point held | Q8 carries the five ESA conditions, re-read on 2026-09-10. I-01, P12, and the CLAUDE.md gotcha drop the unconditional claim. The usable-scene statement stays as a labeled expectation to measure, see below. I-12 is retitled and its text starts from spectral classification. |
| D04, coverage dates and the pre-Collection 1 collection | fixed | I-08, I-17, and F-08 carry the April 2024 qualifier and leave current completeness unverified. I-08 and I-17 name the pre-Collection 1 collection on the same route. |
| D05, acquisition date versus baseline, R5 stale, A10 calendar | fixed | G7 and P4 distinguish original processing from Collection 1. R5 records the 05.12 deployment on 2026-02-04. New claim R6 records the tile-part length markers, sources S11 and S12. I-19 carries the baseline dependency. The A10 note is corrected. |
| D06, tool defaults as asset facts | fixed | I-19, I-20, F-06, and F-14 label 512 pixels, 16 KB, and 1024 pixels as tool defaults. F-14 describes a plausible fit and a resource concern, not conclusions. |
| D07, storage charges as a partition rule | fixed | I-23 is `open` and states cost inputs only. F-16 says the same. The estimated claim's note conditions the standing cost on catalog registration and records that the parent revised it. |
| D08, snapshot expiry versus logical revisions | fixed | I-22, F-15, and the C-02 question separate physical snapshot time travel from logical revision rows with their own availability time. |
| D09, same-orbit cancellation | fixed | G10, P5, I-10, and the decision 0002 rationale limit the cancellation to the DEM-related component. |
| D10, adjacency distance and attribution | fixed | Q6 and I-02 describe the study's two distance groups without a universal radius. The discovery review and the best-practices preamble attribute the hundreds-of-metres figure to the first draft, not to the supplied PDF. |
| Completeness and recovery | fixed | New issue I-27. F-13 distinguishes provider SNS topics from S3 events on owned buckets. |
| JPEG 2000 windowed reads | fixed | New combination C-08 pairs the Sinergise route with windowed reads, so format and workflow no longer vary together. |
| Static pixel classes | fixed | New issue I-28, deferred to the modeling team with the glint and adjacency caveats. |
| I-21 mechanism selected | fixed | I-21 is `open`. Content-addressed publication is one mechanism, not selected. |
| Contract status line | fixed | The contract names what decision 0002 selects. |
| Non-AWS combinations | fixed | Combinations carry a role. C-04 to C-06 render collapsed as context. |
| CLAUDE.md drift | fixed | Gotchas are pointers to claims and issues. Numbers live in the canonical documents. |
| Test accepts any G, R, Q identifier | fixed | The test reads the claim rows of the best-practices document and requires the cited ID to exist. |

## Where this response holds a different view

D03 asks to remove the statement that usable scenes fall faster for small ponds. The statement is kept as an expectation to measure, labeled unmeasured, in I-01. The owner asked for the cloud dilation issue to be documented clearly for a later revisit. A labeled expectation with a named measurement is how this repository records a hypothesis, as assumption A17 does. It is not presented as a fact.

## Checks

The [check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10 after these changes. `uv run pytest -q` passed 42 tests, including the collation and render checks. A static parse of the HTML found the issue table with 28 issues and the collapsed context sections.

## Next step, not started

Owner acceptance of the discovery step comes first. Then the owner decides the AWS route and the history scenario. The primary-tile rule is set inside prototyping, per decision 0002. Then a bounded prototype step follows [work-plan.md](../work-plan.md).
