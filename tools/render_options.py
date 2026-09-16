"""Render the colleague-facing assessment page. Standard library only, no network.

Edit s2-options.template.html for the narrative and layout. The renderer fills the markers:
survey counts and the monthly coverage strip from the gap survey report, the risk and cost
bullets from the inventory's plain-language lines, map facts from the provenance record,
pilot counts from the manifest, and the input digests.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INVENTORY = DOCS / "options-inventory.json"
REPORT = DOCS / "reviews" / "2026-09-10-gap-survey-report.json"
MAPS = DOCS / "assets" / "discovery" / "provenance.json"
PILOT = ROOT / "examples" / "water-bodies-public-pilot.geojson"
RESULTS = ROOT / "benchmarks" / "results"
RAW_ACCESS = [RESULTS / "raw-access.json", RESULTS / "raw-access-older-quality-all.json"]
COPY_DIFFERENCE = RESULTS / "copy-difference.json"
LAKE_EXTRACTION = RESULTS / "lake-extraction.json"
TILE_EXTRACTION = RESULTS / "tile-extraction.json"
REGION_LABELS = {
    "tahoe": "Tahoe",
    "lanier": "Lanier",
    "okeechobee": "Okeechobee",
    "grand-st-marys": "Grand Lake St. Marys",
    "washington": "Washington",
    "iliamna": "Iliamna",
}
METHOD_LABELS = {
    "naive-clip": "Naive clip",
    "raster-mask": "Raster mask",
    "index-lists": "Index lists",
    "lazy-stack": "Lazy stack",
}
SIZE_LABELS = {
    "10 m": "10 m class",
    "30 m": "30 m class",
    "100 m": "100 m class",
    "300 m": "300 m class",
    "1000 m": "1,000 m class",
    "anchor": "Anchor lakes",
}
GROUP_LABELS = {
    "10m": "Four 10 m bands",
    "20m": "Six 20 m bands",
    "60m": "Two 60 m bands",
    "quality": "Quality layers",
    "all": "Everything together",
}
COPY_LABELS = {"c1": "Collection 1 copy", "older": "older copy"}
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


def read_seconds(run: dict) -> float:
    """Sum of the per-file open, read, fetch, and decode timers, without digest and statistics."""
    keys = ("open_seconds", "read_seconds", "fetch_seconds", "decode_seconds")
    return sum(band.get(key, 0.0) for band in run["bands"] for key in keys)


def seconds_label(value: float) -> str:
    return f"{value:.1f} s" if value < 10 else f"{value:,.0f} s"


def raw_access_rows(results: list[dict]) -> str:
    """One table row per band group from the stage 1 results, later files overriding earlier."""
    rows: dict[tuple, dict] = {}
    bands: dict[tuple, int] = {}
    for result in results:
        runs_by_key: dict[tuple, list] = {}
        for run in result["runs"]:
            if "error" not in run:
                key = (run["copy"], run["group"], run["mode"])
                runs_by_key.setdefault(key, []).append(read_seconds(run))
        for row in result["summary"]["by_copy_group_mode"]:
            key = (row["copy"], row["group"], row["mode"])
            if row["failed"] < row["runs"]:
                rows[key] = {**row, "read_median": statistics.median(runs_by_key[key])}
        for copy, groups in result["assets"].items():
            for group, resolved in groups.items():
                bands[(copy, group)] = len(resolved["assets"])
    parts = []
    for group in GROUP_LABELS:
        cells = [f'<th scope="row">{GROUP_LABELS[group]}</th>']
        for copy in COPY_LABELS:
            ranged = rows.get((copy, group, "vsicurl"))
            whole = rows.get((copy, group, "whole-object"))
            count = bands.get((copy, group), 0)
            if ranged:
                megabytes = ranged["bytes_requested_median"] / 1e6
                cells.append(
                    f"<td>{count} files · {megabytes:,.0f} MB · "
                    f"{seconds_label(ranged['read_median'])} · "
                    f"{ranged['requests_median']} requests</td>"
                )
            else:
                cells.append("<td>failed</td>")
            if whole:
                megabytes = whole["bytes_requested_median"] / 1e6
                cells.append(
                    f"<td>{megabytes:,.0f} MB · {seconds_label(whole['read_median'])} · "
                    f"{whole['requests_median']} requests</td>"
                )
            else:
                cells.append("<td>failed</td>")
        peaks = [r["peak_rss_bytes_max"] for (c, g, m), r in rows.items() if g == group]
        cells.append(f"<td>{max(peaks) / 1e9:.1f} GB</td>" if peaks else "<td>failed</td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(parts)


def copy_difference_rows(result: dict) -> str:
    """One table row per compared asset from the copy difference result."""
    parts = []
    for key, entry in result["by_key"].items():
        comparison = entry.get("comparison")
        if not comparison or not comparison.get("same_shape"):
            shapes = (comparison or {}).get("shapes")
            note = "not compared"
            if shapes:
                note = (
                    f"different grids, {shapes[0][0]:,} × {shapes[0][1]:,} against "
                    f"{shapes[1][0]:,} × {shapes[1][1]:,}, not compared"
                )
            parts.append(
                f'<tr><th scope="row">{html.escape(key)}</th><td colspan="4">{note}</td></tr>'
            )
            continue
        valid = comparison["valid_in_both"]
        top = comparison["most_common_differences"][:1]
        if comparison["identical"]:
            summary = "identical"
        elif top:
            share = 100 * top[0]["pixels"] / valid if valid else 0
            summary = f"{top[0]['second_minus_first']:+,} on {share:.2f} % of valid pixels"
        else:
            summary = "no valid pixel in both"
        rule = comparison.get("offset_clamp_rule")
        if comparison["identical"]:
            rule_cell = "not applicable, values identical"
        elif rule is None:
            rule_cell = "not checked"
        elif rule["violations"] == 0:
            rule_cell = f"holds, {rule['first_at_or_below_offset']:,} pixels clamped"
        else:
            rule_cell = f"{rule['violations']:,} violations"
        parts.append(
            f'<tr><th scope="row">{html.escape(key)}</th>'
            f"<td>{comparison['differing_where_both_valid']:,} of {valid:,}</td>"
            f"<td>{summary}</td>"
            f"<td>{rule_cell}</td>"
            f"<td>{'yes' if comparison['nodata_agrees'] else 'no'}</td></tr>"
        )
    return "\n".join(parts)


def megabytes_label(value: int) -> str:
    return f"{value / 1e6:.1f} MB" if value < 1e7 else f"{value / 1e6:,.0f} MB"


def lake_extraction_rows(result: dict) -> str:
    """One table row per size class from the stage 2 summary: what is read and how long."""
    rows = {(r["size_label"], r["method"]): r for r in result["summary"]["by_size_class_method"]}
    prep = {r["size_label"]: r for r in result["summary"]["preparation_by_size_class"]}
    parts = []
    for size, label in SIZE_LABELS.items():
        reference = rows.get((size, "raster-mask"))
        if not reference or "read_seconds_median" not in reference:
            continue
        classes = prep.get(size, {}).get("classes", {}).get("10", {})
        stored = classes.get("all_classes_median")
        blocks = reference.get("blocks_touched_median")
        blocks_max = reference.get("blocks_touched_max")
        blocks_label = "" if blocks is None else f"{blocks} blocks"
        if blocks is not None and blocks_max != blocks:
            blocks_label = f"{blocks} to {blocks_max} blocks"
        cells = [
            f'<th scope="row">{label}</th>',
            f"<td>{reference['lakes']}</td>",
            f"<td>{stored:,}</td>" if stored is not None else "<td>not computed</td>",
            f"<td>{blocks_label} · {megabytes_label(reference['bytes_requested_median'])} · "
            f"{reference['requests_median']} requests</td>",
        ]
        peaks = []
        for method in METHOD_LABELS:
            row = rows.get((size, method))
            if not row or "read_seconds_median" not in row:
                cells.append("<td>failed</td>")
                continue
            cells.append(f"<td>{seconds_label(row['read_seconds_median'])}</td>")
            peaks.append(row["peak_rss_bytes_max"])
        cells.append(f"<td>{max(peaks) / 1e9:.1f} GB</td>" if peaks else "<td>failed</td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(parts)


def pixel_class_rows(result: dict) -> str:
    """One row per size class: median pixels per class at each resolution, and preparation time."""
    parts = []
    prep = {r["size_label"]: r for r in result["summary"]["preparation_by_size_class"]}
    for size, label in SIZE_LABELS.items():
        row = prep.get(size)
        if not row:
            continue
        cells = [f'<th scope="row">{label}</th>', f"<td>{row['lakes']}</td>"]
        for res in ("10", "20", "60"):
            classes = row["classes"].get(res)
            if not classes:
                cells.append("<td>not read</td>")
                continue
            cells.append(
                f"<td>{classes['interior']:,} · {classes['shoreline']:,} · "
                f"{classes['near_land']:,}</td>"
            )
        cells.append(f"<td>{seconds_label(row['prepare_seconds_median'])}</td>")
        parts.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(parts)


def io_label(requests: int, bytes_requested: int, seconds: float) -> str:
    return f"{requests} requests · {megabytes_label(bytes_requested)} · {seconds_label(seconds)}"


EXCLUDED_RUNS = (
    ("runs_with_memory_pressure", "under memory pressure"),
    ("runs_with_errors", "with errors"),
    ("failed", "failed"),
    ("stopped_for_memory", "stopped for memory"),
)


def _pattern_cell(row: dict | None) -> str:
    """Medians of the clean runs. A cell says when runs were left out, or none was clean."""
    if not row:
        return "<td>not run</td>"
    if "read_seconds_median" not in row:
        left_out = ", ".join(f"{row[k]} {text}" for k, text in EXCLUDED_RUNS if row.get(k))
        return f"<td>no clean run: {left_out or 'nothing measured'}</td>"
    label = io_label(
        row["requests_median"], row["bytes_requested_median"], row["read_seconds_median"]
    )
    used, runs = row.get("timings_from_runs"), row.get("runs")
    if used is not None and runs and used < runs:
        label += f", {used} of {runs} runs"
    return f"<td>{label}</td>"


def tile_extraction_rows(result: dict) -> str:
    """One table row per tile from the stage 3 summary: three read patterns beside stage 2."""
    rows = {
        (r["tile"], r["pattern"], r["method"]): r
        for r in result["summary"]["by_tile_pattern_method"]
    }
    parts = []
    for tile in result["summary"]["tiles"]:
        windowed = rows.get((tile["tile"], "tile-by-tile", "raster-mask"))
        if not windowed:
            continue
        base = windowed.get("baseline_stage_2") or {}
        with_baseline = base.get("lakes_with_baseline", [])
        if not base.get("comparable") or not with_baseline:
            stage_2 = "not read in stage 2"
        else:
            stage_2 = io_label(base["requests"], base["bytes_requested"], base["read_seconds"])
            if len(with_baseline) != tile["lakes"]:
                stage_2 = f"{len(with_baseline)} of {tile['lakes']} lakes: {stage_2}"
        partly = tile.get("lakes_partly_inside") or 0
        lakes = f"{tile['lakes']}" + (f", {partly} partly inside" if partly else "")
        region = html.escape(REGION_LABELS.get(tile["region"], tile["region"]))
        cells = [
            f'<th scope="row">{html.escape(tile["tile"])}, {region}</th>',
            f"<td>{lakes}</td>",
            f"<td>{stage_2}</td>",
            _pattern_cell(windowed),
            _pattern_cell(rows.get((tile["tile"], "whole-tile", "raster-mask"))),
            _pattern_cell(rows.get((tile["tile"], "tile-by-tile", "lazy-stack"))),
        ]
        parts.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(parts)


def machine_label(machine: dict) -> str:
    memory = machine.get("memory_total_bytes") or 0
    return f"{machine['cpu_count']}-core {machine['machine']} laptop, {memory / 1e9:.0f} GB memory"


def build_html(inventory: Path = INVENTORY) -> str:
    issues = {issue["id"]: issue for issue in json.loads(inventory.read_text())["issues"]}
    check_placement(issues)
    report = json.loads(REPORT.read_text())
    maps = json.loads(MAPS.read_text())
    pilot = json.loads(PILOT.read_text())
    pilot_props = [feature["properties"] for feature in pilot["features"]]
    pilot_tiers = Counter(p["tier"] for p in pilot_props)
    pilot_classes = sorted({p["size_class_m"] for p in pilot_props if p["tier"] == "pilot"})
    pilot_regions = sorted({p["region"] for p in pilot_props})
    totals = next(f for f in report["findings"] if f["id"] == "GS-10")["numbers"]["totals"]
    raw_results = [json.loads(path.read_text()) for path in RAW_ACCESS]
    copy_difference = json.loads(COPY_DIFFERENCE.read_text())
    lake_extraction = json.loads(LAKE_EXTRACTION.read_text())
    tile_extraction = json.loads(TILE_EXTRACTION.read_text())
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
        "PILOT_TOTAL": str(len(pilot_props)),
        "PILOT_REGIONS": str(len(pilot_regions)),
        "PILOT_PICKS": str(pilot_tiers["pilot"]),
        "PILOT_ANCHORS": str(pilot_tiers["large"]),
        "PILOT_CLASSES": ", ".join(f"{c:,}" for c in pilot_classes),
        "PILOT_TINY": str(sum(p["size_class_m"] == 10 for p in pilot_props)),
        "PILOT_DATE": html.escape(pilot["retrieval"]["accessed_at"][:10]),
        "PILOT_DIGEST": hashlib.sha256(PILOT.read_bytes()).hexdigest(),
        "RAW_ROWS": raw_access_rows(raw_results),
        "RAW_DATE": html.escape(raw_results[0]["measured_at"][:10]),
        "RAW_TILE": html.escape(raw_results[0]["catalog"]["tile"]),
        "RAW_SCENE_DATE": html.escape(raw_results[0]["catalog"]["date"]),
        "RAW_MACHINE": html.escape(machine_label(raw_results[0]["machine"])),
        "RAW_DIGESTS": ", ".join(hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW_ACCESS),
        "DIFF_ROWS": copy_difference_rows(copy_difference),
        "DIFF_DIGEST": hashlib.sha256(COPY_DIFFERENCE.read_bytes()).hexdigest(),
        "LAKE_ROWS": lake_extraction_rows(lake_extraction),
        "LAKE_CLASS_ROWS": pixel_class_rows(lake_extraction),
        "LAKE_DATE": html.escape(lake_extraction["measured_at"][:10]),
        "LAKE_MACHINE": html.escape(machine_label(lake_extraction["machine"])),
        "LAKE_LAKES": str(lake_extraction["summary"]["lakes"]),
        "LAKE_TILES": str(lake_extraction["summary"]["distinct_tiles"]),
        "LAKE_RUNS": f"{len(lake_extraction['runs']):,}",
        "LAKE_DIGEST": hashlib.sha256(LAKE_EXTRACTION.read_bytes()).hexdigest(),
        "TILE_ROWS": tile_extraction_rows(tile_extraction),
        "TILE_DATE": html.escape(tile_extraction["measured_at"][:10]),
        "TILE_MACHINE": html.escape(machine_label(tile_extraction["machine"])),
        "TILE_LAKES": str(tile_extraction["summary"]["lakes"]),
        "TILE_TILES": str(tile_extraction["summary"]["distinct_tiles"]),
        "TILE_RUNS": f"{len(tile_extraction['runs']):,}",
        "TILE_DIGEST": hashlib.sha256(TILE_EXTRACTION.read_bytes()).hexdigest(),
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
        print("The assessment page matches its template, evidence inputs, and map assets.")
        return 0
    args.output.write_text(rendered)
    print(f"Wrote {args.output} ({len(rendered.encode()):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
