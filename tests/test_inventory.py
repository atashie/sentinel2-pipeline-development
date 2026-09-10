"""The canonical inventory follows docs/assessment-data-format.md."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "options-inventory.json"
CLAIM_STATUSES = {"documented", "measured", "unverified"}
CLASSES = {"public-aws", "non-aws", "managed", "self-built"}
TOP_KEYS = {
    "schema_version",
    "assessed_on",
    "selection",
    "scope",
    "missing_value_policy",
    "dimensions",
    "fields",
    "sources",
    "claims",
    "candidates",
    "findings",
    "combinations",
    "gaps",
    "verification",
}


@pytest.fixture(scope="module")
def inventory():
    return json.loads(INVENTORY.read_text())


def test_top_level_keys(inventory):
    assert inventory["schema_version"] == 1
    assert TOP_KEYS <= set(inventory)


def test_referenced_documents_exist(inventory):
    docs = ROOT / "docs"
    assert (docs / inventory["selection"]["decision"]).exists()
    assert (docs / inventory["scope"]["assumptions"]).exists()


def test_fields_apply_to_known_dimensions(inventory):
    dimensions = set(inventory["dimensions"])
    ids = [field["id"] for field in inventory["fields"]]
    assert len(ids) == len(set(ids)), "duplicate field id"
    for field in inventory["fields"]:
        assert field["applies_to"], field["id"]
        assert set(field["applies_to"]) <= dimensions, field["id"]


def test_candidates_carry_every_applicable_field(inventory):
    claim_ids = {claim["id"] for claim in inventory["claims"]}
    ids = [candidate["id"] for candidate in inventory["candidates"]]
    assert len(ids) == len(set(ids)), "duplicate candidate id"
    for candidate in inventory["candidates"]:
        assert candidate["dimension"] in inventory["dimensions"], candidate["id"]
        assert candidate["class"] in CLASSES, candidate["id"]
        applicable = {
            field["id"]
            for field in inventory["fields"]
            if candidate["dimension"] in field["applies_to"]
        }
        specs = candidate["specs"]
        # A seeded candidate may carry an empty specs object. A populated one carries every key.
        if specs:
            assert set(specs) == applicable, f"{candidate['id']}: {set(specs) ^ applicable}"
        for field_id, value in specs.items():
            assert value is None or value in claim_ids, f"{candidate['id']}.{field_id}"


def test_claims_bind_sources_and_checks(inventory):
    source_ids = {source["id"] for source in inventory["sources"]}
    for claim in inventory["claims"]:
        assert claim["status"] in CLAIM_STATUSES, claim["id"]
        assert claim["source_ids"], claim["id"]
        assert set(claim["source_ids"]) <= source_ids, claim["id"]
        assert claim.get("note"), f"{claim['id']} needs a note"
        assert claim.get("check"), f"{claim['id']} needs a check binding"


def test_sources_are_dated_https(inventory):
    for source in inventory["sources"]:
        assert source["url"].startswith("https://"), source["id"]
        assert len(source["accessed_on"]) == 10, source["id"]


def test_findings_and_combinations_cite_claims(inventory):
    claim_ids = {claim["id"] for claim in inventory["claims"]}
    for item in inventory["findings"] + inventory["combinations"]:
        assert set(item.get("claim_ids", [])) <= claim_ids, item.get("id")
