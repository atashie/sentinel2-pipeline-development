"""Collation binds supplementary research and check pairs beside the dimension pair. No network."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "collate_checks", ROOT / "tools" / "collate_checks.py"
)
collate_checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collate_checks)

SOURCE = {
    "id": "src-a",
    "url": "https://example.org/a",
    "title": "A",
    "publisher": "P",
    "accessed_on": "2026-10-13",
    "page_updated": None,
}


def research(candidate, claim_id, extra=None):
    claims = [
        {
            "id": claim_id,
            "candidate": candidate,
            "field": "region",
            "value": "us-west-2",
            "unit": None,
            "note": "draft note",
            "source_ids": ["src-a"],
            "quote": "us-west-2",
            "locator": "table",
            "proposed_status": "documented",
        }
    ] + (extra or [])
    return {
        "dimension": "access_route",
        "researcher": {"model": "r"},
        "sources": [SOURCE],
        "claims": claims,
        "candidate_notes": {candidate: {"questions_open": [f"open {candidate}"]}},
        "limitations": [],
    }


def checks(claim_id, verdict="confirmed"):
    return {
        "dimension": "access_route",
        "checker": {"model": "c"},
        "checks": [
            {
                "id": f"chk-{claim_id}",
                "claim_id": claim_id,
                "verdict": verdict,
                "approved_value": "us-west-2",
                "approved_unit": None,
                "approved_note": "approved note",
                "source_ids": ["src-a"],
            }
        ],
        "limitations": [],
    }


def inventory():
    return {
        "dimensions": ["access_route"],
        "fields": [{"id": "region", "applies_to": ["access_route"]}],
        "candidates": [
            {"id": "ar-base", "dimension": "access_route", "specs": {}},
            {"id": "ar-extra", "dimension": "access_route", "specs": {}},
        ],
    }


def write(directory, name, data):
    (directory / name).write_text(json.dumps(data))


def test_supplementary_pair_binds_and_a_pending_draft_binds_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(collate_checks, "CHECKS", tmp_path)
    write(tmp_path, "access-route-research.json", research("ar-base", "cl-ar-base-region"))
    write(tmp_path, "access-route-checks.json", checks("cl-ar-base-region"))
    estimate = {
        "id": "cl-ar-extra-region-2",
        "candidate": "ar-extra",
        "field": "region",
        "value": "one region",
        "note": "n",
        "proposed_status": "estimated",
        "basis": ["cl-ar-extra-region"],
        "reasoning": "From the documented claim.",
    }
    extra = research("ar-extra", "cl-ar-extra-region", [estimate])
    write(tmp_path, "access-route-extra-research.json", extra)
    write(tmp_path, "access-route-pending-research.json", research("ar-extra", "cl-ar-pending"))

    pairs = collate_checks.dimension_files("access_route")
    assert [r.name for r, _ in pairs] == ["access-route-research.json"]
    write(tmp_path, "access-route-extra-checks.json", checks("cl-ar-extra-region"))
    pairs = collate_checks.dimension_files("access_route")
    assert [r.name for r, _ in pairs] == [
        "access-route-research.json",
        "access-route-extra-research.json",
    ]

    out = collate_checks.collate(inventory())
    claims = {c["id"]: c for c in out["claims"]}
    assert set(claims) == {"cl-ar-base-region", "cl-ar-extra-region", "cl-ar-extra-region-2"}
    assert (
        claims["cl-ar-extra-region"]["check"]["file"]
        == "assessment-checks/access-route-extra-checks.json"
    )
    assert claims["cl-ar-extra-region"]["note"] == "approved note"
    assert claims["cl-ar-extra-region-2"]["status"] == "estimated"
    specs = {c["id"]: c["specs"] for c in out["candidates"]}
    assert specs == {
        "ar-base": {"region": "cl-ar-base-region"},
        "ar-extra": {"region": "cl-ar-extra-region"},
    }
    assert "access_route (access-route-extra): checks c" in out["verification"]["checkers"]


def test_unconfirmed_supplementary_claim_becomes_a_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(collate_checks, "CHECKS", tmp_path)
    write(tmp_path, "access-route-research.json", research("ar-base", "cl-ar-base-region"))
    write(tmp_path, "access-route-checks.json", checks("cl-ar-base-region"))
    write(tmp_path, "access-route-extra-research.json", research("ar-extra", "cl-ar-extra-region"))
    write(
        tmp_path, "access-route-extra-checks.json", checks("cl-ar-extra-region", "not_verifiable")
    )
    out = collate_checks.collate(inventory())
    assert [g["claim_id"] for g in out["gaps"]] == ["cl-ar-extra-region"]
    assert {c["id"]: c["specs"] for c in out["candidates"]}["ar-extra"] == {"region": None}
