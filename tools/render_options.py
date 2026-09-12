"""Render the colleague-facing Discovery page. Standard library only, no network.

Edit s2-options.template.html for the narrative and layout. The renderer fills the markers:
survey counts and the monthly coverage strip from the gap survey report, the risk and cost
bullets from the inventory's plain-language lines, map facts from the provenance record, and
the digests of those three inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INVENTORY = DOCS / "options-inventory.json"
REPORT = DOCS / "reviews" / "2026-09-10-gap-survey-report.json"
MAPS = DOCS / "assets" / "discovery" / "provenance.json"
TEMPLATE = Path(__file__).with_name("s2-options.template.html")
OUTPUT = DOCS / "s2-options.html"

# Inventory issues shown as bullets under each risk category, in page order.
RISK_GROUPS = {
    "RISK_LAND": ["I-03", "I-15", "I-10", "I-09", "I-28", "I-02"],
    "RISK_FLAGS": ["I-01", "I-12", "I-14", "I-13", "I-11", "I-26"],
    "RISK_TILES": ["I-30", "I-04"],
    "RISK_VERSIONS": ["I-05", "I-06", "I-29", "I-16", "I-17", "I-19"],
    "RISK_GRID": ["I-07"],
    "RISK_MISSING": ["I-08", "I-24", "I-25", "I-27"],
}
# Issues about cost and daily operation, shown in the workload section.
COST_ITEMS = ["I-20", "I-21", "I-22", "I-23"]
# The JPEG 2000 bucket stays off the page at the owner's direction of 2026-09-11.
OFF_PAGE = {"I-18"}


def check_placement(issues: dict[str, dict]) -> None:
    """Every inventory issue appears once on the page, unless it is deliberately off it."""
    placed = [i for ids in RISK_GROUPS.values() for i in ids] + COST_ITEMS
    if len(placed) != len(set(placed)):
        raise ValueError("An issue is placed twice on the page")
    unplaced = set(issues) - set(placed) - OFF_PAGE
    unknown = set(placed) - set(issues)
    if unplaced or unknown:
        raise ValueError(f"Unplaced issues {sorted(unplaced)}, unknown issues {sorted(unknown)}")


def bullets(issues: dict[str, dict], ids: list[str]) -> str:
    items = "".join(f"<li>{html.escape(issues[i]['plain'])}</li>" for i in ids)
    return f"<ul>{items}</ul>"


def risk_block(issues: dict[str, dict], ids: list[str]) -> str:
    label = "1 specific issue" if len(ids) == 1 else f"{len(ids)} specific issues"
    return f'<details class="issues"><summary>{label}</summary>{bullets(issues, ids)}</details>'


def shade(fraction: float) -> str:
    """Grey at nothing present, teal at everything present."""
    low, high = (228, 232, 227), (22, 104, 100)
    f = max(0.0, min(1.0, fraction))
    r, g, b = (round(a + (b - a) * f) for a, b in zip(low, high, strict=True))
    return f"#{r:02x}{g:02x}{b:02x}"


def coverage_strip(rows: list[dict]) -> str:
    """Two rows of monthly cells: Collection 1 alone, then with the older collection added."""
    cell, left, top, height, gap = 10, 150, 16, 22, 6
    width = left + len(rows) * cell + 8
    total = top + 2 * (height + gap) + 20
    series = [
        ("Collection 1 copy", lambda r: r["collection1"]),
        ("With the older copy", lambda r: r["collection1"] + r["older_collection_fill"]),
    ]
    parts = [
        f'<svg viewBox="0 0 {width} {total}" role="img" aria-labelledby="coverage-title">',
        '<title id="coverage-title">Monthly share of expected observations present across '
        "the surveyed tiles, from Collection 1 alone and with the older collection added.</title>",
    ]
    for j, (label, count) in enumerate(series):
        y = top + j * (height + gap)
        parts.append(
            f'<text x="{left - 8}" y="{y + 15}" text-anchor="end" font-size="12">{label}</text>'
        )
        for i, row in enumerate(rows):
            fraction = count(row) / row["reference"] if row["reference"] else 0.0
            tip = f"{row['month']}: {min(fraction, 1.0):.0%} of {row['reference']} expected"
            parts.append(
                f'<rect x="{left + i * cell}" y="{y}" width="{cell - 1}" height="{height}" '
                f'fill="{shade(fraction)}"><title>{tip}</title></rect>'
            )
    for i, row in enumerate(rows):
        if row["month"].endswith("-01"):
            year = row["month"][:4]
            parts.append(
                f'<text x="{left + i * cell}" y="{total - 5}" font-size="11">{year}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def build_html(inventory: Path = INVENTORY) -> str:
    issues = {issue["id"]: issue for issue in json.loads(inventory.read_text())["issues"]}
    check_placement(issues)
    report = json.loads(REPORT.read_text())
    maps = json.loads(MAPS.read_text())
    totals = next(f for f in report["findings"] if f["id"] == "GS-10")["numbers"]["totals"]
    for entry in maps["images"].values():
        path = MAPS.parent / entry["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Map differs from its provenance record: {path}")
    replacements = {
        "MISSING": f"{totals['missing']:,}",
        "FALLBACK": f"{totals['complete_cog']:,}",
        "OTHER_FORMAT": f"{totals['jp2_only']:,}",
        "UNCOVERED": f"{totals['uncovered']:,}",
        "FALLBACK_PERCENT": f"{100 * totals['complete_cog'] / totals['missing']:.0f}",
        "COVERAGE_STRIP": coverage_strip(report["coverage_by_month"]),
        "COST_BULLETS": bullets(issues, COST_ITEMS),
        **{key: risk_block(issues, ids) for key, ids in RISK_GROUPS.items()},
        "VALID_PERCENT": f"{100 * maps['images']['true-color']['valid_fraction']:.1f}",
        "MAP_DATE": html.escape(maps["sensing_time"][:10]),
        "MAP_SENSING_TIME": datetime.fromisoformat(maps["sensing_time"])
        .astimezone(UTC)
        .strftime("%Y-%m-%d %H:%M:%S UTC"),
        "MAP_PLACE": html.escape(maps["place"]),
        "MAP_ITEM_URL": html.escape(maps["item_url"], quote=True),
        "INVENTORY_DIGEST": hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "REPORT_DIGEST": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
        "MAP_DIGEST": hashlib.sha256(MAPS.read_bytes()).hexdigest(),
    }
    rendered = TEMPLATE.read_text()
    for key, value in replacements.items():
        rendered = rendered.replace(f"@@{key}@@", value)
    if re.search(r"@@[A-Z_]+@@", rendered):
        raise ValueError("Unfilled template marker")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail when the generated page is stale"
    )
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    rendered = build_html(args.inventory)
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            print(f"{args.output} is stale. Run tools/render_options.py.")
            return 1
        print("The Discovery page matches its template, evidence inputs, and map assets.")
        return 0
    args.output.write_text(rendered)
    print(f"Wrote {args.output} ({len(rendered.encode()):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
