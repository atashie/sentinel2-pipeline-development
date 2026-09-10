---
paths:
  - "docs/options-inventory.json"
  - "docs/assessment-checks/**"
  - "tools/**"
---

# Rules for the assessment dataset

- `docs/options-inventory.json` is the canonical dataset. Follow `docs/assessment-data-format.md`.
- Candidates are access routes, processing workflows, compute platforms, and storage layouts. They are not a vendor ranking.
- Every candidate has every field that applies to its dimension. A field is a claim ID or null. Null means unknown, never zero, false, or absent.
- Every populated claim cites a source with an access date and links a check record in `docs/assessment-checks/`. The check names its checker.
- A changed claim loses its earlier confirmation. Recheck the page and update the record before regenerating the HTML.
- Prices keep their unit, currency notation, plan, and conditions in the claim note. A subscription price is not a measured workload cost.
- Findings and combinations cite claim IDs. They do not introduce new facts.
- After any change, regenerate the HTML with the renderer in `tools/` and run the check workflow. Until the renderer exists, run `uv run pytest tests/test_inventory.py`.
