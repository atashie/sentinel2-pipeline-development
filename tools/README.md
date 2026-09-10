# Tools

The assessment renderer lives here once the discovery step writes it. It reads [../docs/options-inventory.json](../docs/options-inventory.json) and writes a standalone HTML view with the embedded dataset.
It uses the standard library and performs no network access. Until it exists, `uv run pytest tests/test_inventory.py` checks the dataset.
