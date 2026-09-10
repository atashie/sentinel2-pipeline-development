"""The canonical inventory follows the rules in docs/assessment-data-format.md."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INVENTORY = DOCS / "options-inventory.json"
INVENTORY_STATUSES = {"documented", "measured", "estimated"}
CHECK_VERDICTS = {"confirmed", "corrected"}
CLASSES = {"public-aws", "non-aws", "managed", "self-built"}
ROLES = {"primary", "context"}
ISSUE_STATUSES = {"decided", "deferred", "open", "probe", "measure"}
ISSUE_FLAGS = {"major concern"}
PRACTICE_CLAIM = re.compile(r"[GRQ]\d{1,2}")
BEST_PRACTICES = DOCS / "s2-best-practices.md"
NEVER_ESTIMATED = {"unit_price", "monthly_price", "coverage_start_l2a", "license"}
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


@pytest.fixture(scope="module")
def claims(inventory):
    return {claim["id"]: claim for claim in inventory["claims"]}


def load_check(binding):
    path = DOCS / binding["file"]
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    for check in record.get("checks", []):
        if check.get("id") == binding["id"]:
            return check
    return None


def test_top_level_keys(inventory):
    assert inventory["schema_version"] == 2
    assert TOP_KEYS <= set(inventory)


def test_referenced_documents_exist(inventory):
    assert (DOCS / inventory["selection"]["decision"]).exists()
    assert (DOCS / inventory["scope"]["assumptions"]).exists()


def test_fields_apply_to_known_dimensions(inventory):
    dimensions = set(inventory["dimensions"])
    ids = [field["id"] for field in inventory["fields"]]
    assert len(ids) == len(set(ids)), "duplicate field id"
    for field in inventory["fields"]:
        assert field["applies_to"], field["id"]
        assert set(field["applies_to"]) <= dimensions, field["id"]


def test_candidates_carry_every_applicable_field(inventory, claims):
    ids = [candidate["id"] for candidate in inventory["candidates"]]
    assert len(ids) == len(set(ids)), "duplicate candidate id"
    assessed = inventory["assessed_on"] is not None
    for candidate in inventory["candidates"]:
        assert candidate["dimension"] in inventory["dimensions"], candidate["id"]
        assert candidate["class"] in CLASSES, candidate["id"]
        assert candidate.get("role", "primary") in ROLES, candidate["id"]
        applicable = {
            field["id"]
            for field in inventory["fields"]
            if candidate["dimension"] in field["applies_to"]
        }
        specs = candidate["specs"]
        if assessed or specs:
            assert set(specs) == applicable, f"{candidate['id']}: {set(specs) ^ applicable}"
        for field_id, value in specs.items():
            if value is None:
                continue
            claim = claims.get(value)
            assert claim is not None, f"{candidate['id']}.{field_id} -> {value}"
            assert claim["candidate"] == candidate["id"], f"{value} belongs to another candidate"
            assert claim["field"] == field_id, f"{value} is for field {claim['field']}"
            assert claim["status"] in INVENTORY_STATUSES, value


def test_sources_are_dated_https(inventory):
    ids = [source["id"] for source in inventory["sources"]]
    assert len(ids) == len(set(ids)), "duplicate source id"
    for source in inventory["sources"]:
        assert source["url"].startswith("https://"), source["id"]
        assert len(source["accessed_on"]) == 10, source["id"]
        assert source.get("title"), source["id"]


def test_documented_claims_bind_sources_and_checks(inventory, claims):
    source_ids = {source["id"] for source in inventory["sources"]}
    ids = list(claims)
    assert len(ids) == len(set(ids)), "duplicate claim id"
    for claim in inventory["claims"]:
        assert claim["status"] in INVENTORY_STATUSES, claim["id"]
        assert claim.get("note"), f"{claim['id']} needs a note"
        if claim["status"] == "estimated":
            continue
        assert claim["source_ids"], claim["id"]
        assert set(claim["source_ids"]) <= source_ids, claim["id"]
        assert claim.get("check"), f"{claim['id']} needs a check binding"
        check = load_check(claim["check"])
        assert check is not None, f"{claim['id']}: check record {claim['check']} not found"
        assert check["claim_id"] == claim["id"], claim["id"]
        assert check["verdict"] in CHECK_VERDICTS, f"{claim['id']}: {check['verdict']}"
        assert check["approved_value"] == claim["value"], claim["id"]


def test_estimated_claims_name_documented_basis(inventory, claims):
    for claim in inventory["claims"]:
        if claim["status"] != "estimated":
            continue
        assert claim["field"] not in NEVER_ESTIMATED, claim["id"]
        assert claim.get("basis"), f"{claim['id']} needs a basis"
        assert claim.get("reasoning"), f"{claim['id']} needs reasoning"
        for basis_id in claim["basis"]:
            basis = claims.get(basis_id)
            assert basis is not None, f"{claim['id']} cites missing {basis_id}"
            assert basis["status"] in {"documented", "measured"}, f"{claim['id']} -> {basis_id}"


def test_findings_and_combinations_cite_claims(inventory, claims):
    for item in inventory["findings"] + inventory["combinations"]:
        assert item.get("role", "primary") in ROLES, item.get("id")
        cited = item.get("claim_ids", [])
        assert cited, f"{item.get('id')} cites no claim"
        assert set(cited) <= set(claims), item.get("id")


def practice_claim_ids():
    return set(re.findall(r"^\| ([GRQ]\d{1,2}) \|", BEST_PRACTICES.read_text(), re.MULTILINE))


def test_probes_are_recorded(inventory):
    ids = [probe["id"] for probe in inventory.get("probes", [])]
    assert len(ids) == len(set(ids)), "duplicate probe id"
    for probe in inventory.get("probes", []):
        for key in ("date", "question", "result", "bears_on", "record"):
            assert probe.get(key), f"{probe['id']} needs {key}"
        assert len(probe["date"]) == 10, probe["id"]
        assert (DOCS / probe["record"]).exists(), f"{probe['id']} record missing"


def test_issues_cite_evidence(inventory, claims):
    practice_ids = practice_claim_ids()
    probe_ids = {probe["id"] for probe in inventory.get("probes", [])}
    assert practice_ids, "no claim rows found in the best-practices document"
    ids = [issue["id"] for issue in inventory.get("issues", [])]
    assert len(ids) == len(set(ids)), "duplicate issue id"
    for issue in inventory.get("issues", []):
        for key in ("title", "text", "consequence", "decision"):
            assert issue.get(key), f"{issue['id']} needs {key}"
        assert issue["status"] in ISSUE_STATUSES, issue["id"]
        assert issue.get("flag", "major concern") in ISSUE_FLAGS, issue["id"]
        assert issue["evidence"], f"{issue['id']} cites no evidence"
        for ref in issue["evidence"]:
            assert ref in claims or ref in practice_ids or ref in probe_ids, (
                f"{issue['id']} -> {ref}"
            )


def test_rendered_html_matches_inventory():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "render_options.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_inventory_matches_check_records():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "collate_checks.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
