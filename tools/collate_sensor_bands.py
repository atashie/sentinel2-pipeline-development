"""Bind the sensor band comparison from its research draft and its check record.

Reads docs/assessment-checks/sensor-bands-research.json and sensor-bands-checks.json.
Writes docs/sensor-bands.json with only the uses, sensors, and bands whose check is
confirmed or corrected, carrying the checker's approved values. A band the checker could
not verify leaves the table and is listed as a gap. Standard library only. No network.
`--check` fails when the dataset is stale.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHECKS = DOCS / "assessment-checks"
RESEARCH = CHECKS / "sensor-bands-research.json"
CHECK_RECORD = CHECKS / "sensor-bands-checks.json"
OUTPUT = DOCS / "sensor-bands.json"
BINDING_VERDICTS = {"confirmed", "corrected"}
VERDICTS = BINDING_VERDICTS | {"not_verifiable"}
BAND_FIELDS = ("name", "center_nm", "width_nm", "range_nm", "resolution_m", "variants", "note")
SENSOR_FIELDS = (
    "label",
    "platform",
    "instrument",
    "operator",
    "access",
    "wavelength_form",
    "notes",
    "source_ids",
)
USE_FIELDS = ("label", "definition", "source_ids")
METHOD = (
    "One research agent drafted every band and every water-quality use with a verbatim quote "
    "and a locator. A checking agent on a different model opened every cited page and recorded "
    "confirmed, corrected, or not_verifiable per use, sensor, and band. Only confirmed and "
    "corrected records bind. tools/collate_sensor_bands.py rebuilt this dataset from those records."
)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def index_checks(checks: dict) -> dict[str, dict]:
    """Checks by claim id. A malformed record fails collation instead of binding silently."""
    by_claim: dict[str, dict] = {}
    for check in checks["checks"]:
        claim_id, verdict = check["claim_id"], check["verdict"]
        if check["id"] != f"chk-{claim_id}":
            raise ValueError(f"Check {check['id']} does not name its claim {claim_id}")
        if verdict not in VERDICTS:
            raise ValueError(f"Unknown verdict {verdict!r} on {check['id']}")
        if claim_id in by_claim:
            raise ValueError(f"Claim {claim_id} is checked twice")
        if verdict in BINDING_VERDICTS and not isinstance(check.get("approved"), dict):
            raise ValueError(f"Binding check {check['id']} carries no approved values")
        by_claim[claim_id] = check
    return by_claim


def gap(claim_id: str, check: dict | None) -> dict:
    if check is None:
        return {"claim_id": claim_id, "verdict": None, "reason": "No check record"}
    return {"claim_id": claim_id, "verdict": check["verdict"], "reason": check["reason"]}


def bind_band(sensor_id: str, draft: dict, check: dict, uses: set[str]) -> dict:
    """The checker's approved values, with the draft's basis and sources for each kept use."""
    approved = check["approved"]
    centered, ranged = approved.get("center_nm") is not None, approved.get("range_nm") is not None
    if centered == ranged or (centered and approved.get("width_nm") is None):
        raise ValueError(f"Band {sensor_id} {draft['id']} needs exactly one wavelength form")
    drafted = {use["use"]: use for use in draft["uses"]}
    kept = []
    for use_id in approved["uses"]:
        if use_id not in drafted:
            raise ValueError(f"Check for {sensor_id} {draft['id']} adds an undrafted use {use_id}")
        if use_id not in uses:
            continue
        entry = drafted[use_id]
        kept.append(
            {"use": use_id, "basis": entry["basis"], "source_ids": sorted(entry["source_ids"])}
        )
    band = {"id": draft["id"]}
    band.update({field: approved.get(field) for field in BAND_FIELDS})
    band["uses"] = kept
    band["check"] = check["id"]
    return band


def collate(research: dict, checks: dict) -> dict:
    by_claim = index_checks(checks)
    known_uses = {use["id"] for use in research["uses"]}
    gaps: list[dict] = []
    uses: list[dict] = []
    for draft in research["uses"]:
        check = by_claim.get(f"use-{draft['id']}")
        if check is None or check["verdict"] not in BINDING_VERDICTS:
            gaps.append(gap(f"use-{draft['id']}", check))
            continue
        use = {"id": draft["id"]}
        use.update({field: check["approved"][field] for field in USE_FIELDS})
        use["check"] = check["id"]
        uses.append(use)
    bound_uses = {use["id"] for use in uses}

    sensors: list[dict] = []
    for draft in research["sensors"]:
        sensor_claim = f"sensor-{draft['id']}"
        check = by_claim.get(sensor_claim)
        if check is None or check["verdict"] not in BINDING_VERDICTS:
            gaps.append(gap(sensor_claim, check))
            continue
        sensor = {"id": draft["id"]}
        sensor.update({field: check["approved"][field] for field in SENSOR_FIELDS})
        sensor["check"] = check["id"]
        sensor["bands"] = []
        for band in draft["bands"]:
            for use in band["uses"]:
                if use["use"] not in known_uses:
                    raise ValueError(f"Band {draft['id']} {band['id']} names an unknown use")
            band_claim = f"band-{draft['id']}-{band['id']}"
            band_check = by_claim.get(band_claim)
            if band_check is None or band_check["verdict"] not in BINDING_VERDICTS:
                gaps.append(gap(band_claim, band_check))
                continue
            sensor["bands"].append(bind_band(draft["id"], band, band_check, bound_uses))
        sensors.append(sensor)

    cited: set[str] = set()
    for use in uses:
        cited.update(use["source_ids"])
    for sensor in sensors:
        cited.update(sensor["source_ids"])
        for band in sensor["bands"]:
            for use in band["uses"]:
                cited.update(use["source_ids"])
    sources = [source for source in research["sources"] if source["id"] in cited]
    missing = cited - {source["id"] for source in sources}
    if missing:
        raise ValueError(f"Bound records cite unknown sources {sorted(missing)}")
    checked = {claim for claim in by_claim if by_claim[claim]["verdict"] in BINDING_VERDICTS}
    return {
        "schema_version": 1,
        "purpose": research["purpose"],
        "collated_from": {
            "research": str(RESEARCH.relative_to(DOCS)),
            "checks": str(CHECK_RECORD.relative_to(DOCS)),
        },
        "sources": sources,
        "uses": uses,
        "sensors": sensors,
        "gaps": gaps,
        "verification": {
            "researcher": research["researcher"],
            "checker": checks["checker"],
            "method": METHOD,
            "bound_checks": len(checked),
            "limitations": list(research["limitations"]) + list(checks["limitations"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when the dataset is stale")
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--checks", type=Path, default=CHECK_RECORD)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    dataset = collate(load(args.research), load(args.checks))
    text = json.dumps(dataset, indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != text:
            print(f"{args.output} is stale. Run tools/collate_sensor_bands.py.")
            return 1
        print("The sensor band dataset matches its research and check records.")
        return 0
    args.output.write_text(text)
    bands = sum(len(sensor["bands"]) for sensor in dataset["sensors"])
    print(
        f"Wrote {args.output}: {len(dataset['sensors'])} sensors, {bands} bands, "
        f"{len(dataset['uses'])} uses, {len(dataset['gaps'])} gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
