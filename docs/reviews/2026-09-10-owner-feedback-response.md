# Response to owner feedback on discovery, 2026-09-10

Author: Claude Code (AI coding agent), directed by the repository owner. Subject: the owner's five directions on the [discovery review](2026-09-10-discovery.md), given on 2026-09-10.
[Decision 0002](../decisions/0002-aws-source-pixel-classes-tile-provenance.md) records the directions. This response records what changed and what remains for the owner. Nothing is committed.

## Directions and dispositions

| Direction | Disposition | Where |
|---|---|---|
| Document cloud dilation clearly. Revisit later. | fixed | Issue I-01, status `open`, with evidence Q8, Q1, Q2, G8 and the consequence for small ponds. Decision 0002. |
| Adjacency is not a blocker. Document lightly. The modeling team addresses it. | fixed | Issue I-02, status `deferred`. Practice P7 revised. The contract carries aerosol optical thickness, edge distance, and the near-land class as context. |
| Three pixel classes per water body: interior, shoreline, near-land within about 100 m. | fixed | Assumptions A20 and A21. Decision 0002. Contract fields `pixel_class`, `coverage_fraction`, `edge_distance_m`. Practices P1 and P6. CLAUDE.md gotcha. Issue I-03 `decided`. |
| Add a tile provenance marker and document the rationale. | fixed | Contract field `tile_role`. Practice P2. Rationale section in decision 0002. Issue I-04 `decided`. |
| AWS is the source. Alternatives are context. Focus discovery on ingestion and processing issues and on comparing workflows. | fixed | Assumption A13. Decision 0002. Candidate `role` with seven context candidates collapsed in the HTML. Issue register of 26 issues rendered first in the Discovery tab. Protocol, discovery plan, README, and work plan revised. |

## Changed artifacts

- [options-inventory.json](../options-inventory.json): `issues` list, candidate `role`, revised `selection`. Claims, sources, and check records are unchanged.
- [render_options.py](../../tools/render_options.py): renders the issue register first and collapses context candidates under each dimension.
- [test_inventory.py](../../tests/test_inventory.py): checks roles, issue statuses, and that every issue cites evidence that exists.
- [assessment-data-format.md](../assessment-data-format.md): documents `issues`, `role`, and the new checks.
- [data-contract.md](../data-contract.md), [s2-best-practices.md](../s2-best-practices.md), [assumptions.md](../assumptions.md), [assessment-protocol.md](../assessment-protocol.md), [discovery-plan.md](../discovery-plan.md), [work-plan.md](../work-plan.md), [examples/README.md](../../examples/README.md), CLAUDE.md, README.md.

## What did not change

Findings F-01 to F-20, the 319 claims, the 120 sources, and the check records stand as delivered. The discovery review stays as history with a note pointing here.
Findings about non-AWS routes remain documented facts. They no longer bear on selection.

## Open items for the owner

- **Which AWS route.** The Earth Search cloud-optimized GeoTIFF route and the Sinergise JPEG 2000 route differ on quality layers (I-26), file format and read cost (I-19), early Level-2A coverage and provenance (I-17), and payer (I-18). Two of those are cheap probes. Two are prototype measurements.
- **History scenario.** Which of the 2017 and 2021 scenarios a prototype serves first, issue I-08.
- **Primary-tile rule.** Set in prototyping and recorded, per decision 0002.

## Checks

The [check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10 after the revision: `uv sync --locked`, `ruff check`, `ruff format --check`, and `pytest` with 40 tests. The tests run the collation and render checks. A static parse of the HTML found the issue table, three collapsed context sections, and no external resource. No browser check ran.

## Next step, not started

Codex review of this revision. Then the owner's decisions above. Then a bounded prototype step per [work-plan.md](../work-plan.md).
