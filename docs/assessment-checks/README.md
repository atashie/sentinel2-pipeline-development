# Assessment checks

Research drafts and independent check records that bind claims in [options-inventory.json](../options-inventory.json).
Empty on 2026-09-09. The [discovery plan](../discovery-plan.md) says what lands here and how.

| File pattern | Purpose |
|---|---|
| `<dimension>-research.json` | Draft claims from a research agent: source, access date, quoted text, proposed value |
| `<dimension>-checks.json` | Verdicts from a different agent: `confirmed`, `corrected`, or `not_verifiable`, with reasons and checker identity |
| `best-practices-recheck.json` | Verdicts on the claims in [s2-best-practices.md](../s2-best-practices.md) |

Only confirmed or corrected values populate the inventory. Checks verify documentation. They are not measurements, human approval, or independent verification of the provider's data.
