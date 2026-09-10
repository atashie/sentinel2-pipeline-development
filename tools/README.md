# Tools

Deterministic scripts. Standard library only. No network.

| Script | Reads | Writes | Check mode |
|---|---|---|---|
| [collate_checks.py](collate_checks.py) | `docs/assessment-checks/*-research.json` and `*-checks.json`, the current inventory | `docs/options-inventory.json` | `--check` fails when the inventory is stale |
| [render_options.py](render_options.py) | `docs/options-inventory.json`, check records for verdicts | `docs/s2-options.html` | `--check` fails when the HTML is stale |

[../docs/assessment-data-format.md](../docs/assessment-data-format.md) defines the formats and the regeneration order.
