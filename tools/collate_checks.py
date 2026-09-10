"""Rebuild the evidence-derived parts of docs/options-inventory.json from check records.

Reads docs/assessment-checks/<dimension>-research.json and <dimension>-checks.json for every
dimension that has both. Rebuilds sources, claims, candidate specs and questions, gaps,
not_assessed, and verification. Preserves selection, scope, fields, findings, and combinations.
Standard library only. No network. `--check` fails when the inventory is stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHECKS = DOCS / "assessment-checks"
INVENTORY = DOCS / "options-inventory.json"
ASSESSED_ON = "2026-09-09"
BINDING_VERDICTS = {"confirmed", "corrected"}
SOURCE_KEYS = ("id", "url", "title", "publisher", "accessed_on", "page_updated")
METHOD = (
    "One research agent per dimension drafted claims with quotes and access dates. A checking "
    "agent on a different model fetched every cited page and recorded confirmed, corrected, or "
    "not_verifiable. Only confirmed and corrected records bind claims. Estimates cite documented "
    "claims and are labeled. tools/collate_checks.py rebuilt this dataset from those records."
)


def dimension_files(dimension: str) -> tuple[Path, Path]:
    slug = dimension.replace("_", "-")
    return CHECKS / f"{slug}-research.json", CHECKS / f"{slug}-checks.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def collate(inventory: dict) -> dict:
    out = json.loads(json.dumps(inventory))
    applicable = {
        dim: [f["id"] for f in out["fields"] if dim in f["applies_to"]] for dim in out["dimensions"]
    }
    sources: dict[str, dict] = {}
    claims: list[dict] = []
    gaps: list[dict] = []
    not_assessed: list[dict] = []
    checkers: list[str] = []
    limits: list[str] = []
    questions: dict[str, list[str]] = {}
    dimensions_done: list[str] = []

    for dim in out["dimensions"]:
        research_path, checks_path = dimension_files(dim)
        if not (research_path.exists() and checks_path.exists()):
            continue
        dimensions_done.append(dim)
        research, checks = load(research_path), load(checks_path)
        draft_sources = {s["id"]: s for s in research["sources"]}
        drafts = {c["id"]: c for c in research["claims"]}
        verdicts = {c["claim_id"]: c for c in checks["checks"]}
        checkers.append(f"{dim}: research {research['researcher']['model']}")
        checkers.append(f"{dim}: checks {checks['checker']['model']}")
        limits.extend(research.get("limitations", []))
        limits.extend(checks.get("limitations", []))
        for item in research.get("not_assessed", []):
            not_assessed.append(
                {
                    "name": item.get("name") or item.get("option"),
                    "why": item.get("why") or item.get("reason"),
                    "seen_on": item.get("seen_on"),
                    "dimension": dim,
                }
            )
        notes = research.get("candidate_notes", {})
        if isinstance(notes, list):
            notes = {n["candidate"]: n for n in notes}
        for cand_id, note in notes.items():
            if note.get("questions_open"):
                questions[cand_id] = list(note["questions_open"])

        documented_ids: set[str] = set()
        for draft in research["claims"]:
            if draft.get("proposed_status") != "documented":
                continue
            check = verdicts.get(draft["id"])
            if check is None:
                gaps.append(_gap(draft, "no check record"))
                continue
            if check["verdict"] not in BINDING_VERDICTS:
                gaps.append(_gap(draft, f"{check['verdict']}: {check.get('reason', '')}".strip()))
                continue
            source_ids = check.get("source_ids") or draft["source_ids"]
            missing = [s for s in source_ids if s not in draft_sources]
            if missing:
                gaps.append(_gap(draft, f"source ids not in research file: {missing}"))
                continue
            for sid in source_ids:
                sources.setdefault(sid, {k: draft_sources[sid].get(k) for k in SOURCE_KEYS})
            claims.append(
                {
                    "id": draft["id"],
                    "candidate": draft["candidate"],
                    "field": draft["field"],
                    "value": check["approved_value"],
                    "unit": check.get("approved_unit"),
                    "note": check.get("approved_note") or draft["note"],
                    "status": "documented",
                    "source_ids": source_ids,
                    "check": {"file": f"assessment-checks/{checks_path.name}", "id": check["id"]},
                }
            )
            documented_ids.add(draft["id"])

        for draft in research["claims"]:
            if draft.get("proposed_status") != "estimated":
                continue
            basis = [b for b in draft.get("basis", []) if b in documented_ids]
            if not basis or not draft.get("reasoning"):
                gaps.append(_gap(draft, "estimate without a documented basis"))
                continue
            claims.append(
                {
                    "id": draft["id"],
                    "candidate": draft["candidate"],
                    "field": draft["field"],
                    "value": draft["value"],
                    "unit": draft.get("unit"),
                    "note": draft["note"],
                    "status": "estimated",
                    "basis": basis,
                    "reasoning": draft["reasoning"],
                }
            )
        del drafts

    claims.sort(key=lambda c: c["id"])
    by_candidate_field: dict[tuple[str, str], list[str]] = {}
    for claim in claims:
        by_candidate_field.setdefault((claim["candidate"], claim["field"]), []).append(claim["id"])

    for cand in out["candidates"]:
        if cand["dimension"] not in dimensions_done:
            if dimensions_done:
                cand["specs"] = dict.fromkeys(applicable[cand["dimension"]])
            continue
        specs = {}
        for field in applicable[cand["dimension"]]:
            ids = by_candidate_field.get((cand["id"], field), [])
            exact = f"cl-{cand['id']}-{field}"
            specs[field] = exact if exact in ids else (ids[0] if ids else None)
        cand["specs"] = specs
        if cand["id"] in questions:
            cand["questions"] = questions[cand["id"]]

    out["assessed_on"] = ASSESSED_ON if dimensions_done else None
    out["sources"] = [sources[k] for k in sorted(sources)]
    out["claims"] = claims
    out["gaps"] = gaps
    out["not_assessed"] = not_assessed
    out["verification"] = {
        "method": METHOD,
        "checkers": checkers,
        "dimensions_collated": dimensions_done,
        "limits": " ".join(dict.fromkeys(limits)) if limits else "No dimension collated yet.",
    }
    return out


def _gap(draft: dict, reason: str) -> dict:
    return {
        "candidate": draft["candidate"],
        "field": draft["field"],
        "claim_id": draft["id"],
        "reason": reason,
    }


def dump(inventory: dict) -> str:
    return json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the inventory is stale")
    args = parser.parse_args(argv)
    current = load(INVENTORY)
    rebuilt = dump(collate(current))
    if args.check:
        if INVENTORY.read_text() != rebuilt:
            print("docs/options-inventory.json is stale. Run tools/collate_checks.py.")
            return 1
        print("docs/options-inventory.json matches the check records.")
        return 0
    INVENTORY.write_text(rebuilt)
    inv = json.loads(rebuilt)
    print(
        f"collated {len(inv['claims'])} claims, {len(inv['sources'])} sources, "
        f"{len(inv['gaps'])} gaps for {inv['verification']['dimensions_collated']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
