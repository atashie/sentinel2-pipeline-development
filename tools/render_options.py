"""Render the colleague-facing assessment page. Standard library only, no network.

Edit s2-options.template.html for the narrative and layout. The renderer fills the markers:
survey counts and the monthly coverage strip from the gap survey report, the risk and cost
bullets from the inventory's plain-language lines, map facts from the provenance record,
pilot counts from the manifest, prototype tables from saved results, the sensor band tables
from the bound sensor band dataset, the AWS cost table from the generated cost estimates, and
the input digests.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import statistics
from collections import Counter
from datetime import UTC, date, datetime, timedelta
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
CROSS_TILE_EXTRACTION = RESULTS / "cross-tile-extraction.json"
LAZY_WORKLOADS = RESULTS / "lazy-reader-workloads.json"
WORKLOAD_AUDIT = RESULTS / "lazy-reader-workloads-audit.json"
COST_ESTIMATES = DOCS / "cost-analysis" / "estimates.json"
COST_INPUTS = DOCS / "cost-analysis" / "inputs.json"
COST_MODEL = ROOT / "tools" / "estimate_aws_costs.py"
# Workload key: whether it is the national population, and whether it keeps nearby land.
COST_WORKLOADS = {
    "all_land": (True, True),
    "all_water_shore": (True, False),
    "sample_land": (False, True),
    "sample_water_shore": (False, False),
}
COST_RECIPES = {"A1": ("lake-first", 1), "B1": ("tile-first", 1), "B3": ("tile-first", 3)}
REGION_LABELS = {
    "tahoe": "Tahoe",
    "lanier": "Lanier",
    "okeechobee": "Okeechobee",
    "grand-st-marys": "Grand Lake St. Marys",
    "washington": "Washington",
    "iliamna": "Iliamna",
}
METHOD_LABELS = {
    "naive-clip": "Boundary clip",
    "raster-mask": "Prepared mask",
    "index-lists": "Stored positions",
    "lazy-stack": "Prepared mask",
}
WORKFLOW_LABELS = {
    "lake-first": "A · Each lake separately",
    "tile-first": "B · Share image windows",
    "whole-tile": "C · Read the whole image",
}
READER_LABELS = {
    1: "Direct raster reads",
    2: "Large-chunk lazy reads",
    3: "Source-block lazy reads",
}
METHOD_READERS = {"naive-clip": 1, "raster-mask": 1, "index-lists": 1, "lazy-stack": 2}
# Presentation identities only. Frozen result keys and experiment settings remain separate.
WORKLOAD_CONFIGURATIONS = {
    "A-raster": ("lake-first", 1),
    "A-lazy": ("lake-first", 3),
    "B-raster": ("tile-first", 1),
    "B-lazy-control": ("tile-first", 2),
    "B-lazy": ("tile-first", 3),
    "C-raster": ("whole-tile", 1),
    "C-lazy": ("whole-tile", 3),
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
SENSOR_BANDS = DOCS / "sensor-bands.json"
# Short chip labels for the water-quality uses. The legend carries the full label and definition.
USE_SHORT = {
    "chlorophyll": "Chlorophyll",
    "turbidity": "Turbidity",
    "cdom": "Dissolved organics",
    "temperature": "Temperature",
    "correction": "Correction",
    "extent": "Water extent",
}
# Uses that support a retrieval without carrying the water signal themselves.
SUPPORT_USES = {"correction", "extent"}
ACCESS_LABELS = {"public": "Public data", "commercial": "Commercial imagery"}
# The two sensors shown before the reader picks, left then right.
DEFAULT_SENSORS = ("sentinel-2-msi", "landsat-9-oli-tirs")
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
    """Gray at nothing present, teal at everything present."""
    low, high = (228, 232, 227), (22, 104, 100)
    f = max(0.0, min(1.0, fraction))
    r, g, b = (round(a + (b - a) * f) for a, b in zip(low, high, strict=True))
    return f"#{r:02x}{g:02x}{b:02x}"


def coverage_strip(rows: list[dict]) -> str:
    """Two rows of monthly cells: the Collection 1 copy alone, then with the older copy added."""
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
        "the surveyed tiles, from the Collection 1 copy alone and with the older copy added."
        "</title>",
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


def lake_method_rows(result: dict) -> str:
    """Show both ends of the size range, with each method's own resource measurements."""
    rows = {(r["size_label"], r["method"]): r for r in result["summary"]["by_size_class_method"]}
    parts = []
    for size, label in (
        ("10 m", "Smallest ponds · 10 m size class"),
        ("anchor", "Larger reference lakes"),
    ):
        parts.append(
            f'<tbody><tr class="result-group"><th colspan="6" scope="rowgroup">{label}</th></tr>'
        )
        for method, description in METHOD_LABELS.items():
            row = rows.get((size, method))
            reader = METHOD_READERS[method]
            selection = "Nearby land omitted" if method == "naive-clip" else "All three classes"
            cells = (
                f'<th scope="row" class="workflow-a"><a href="#reader-{reader}">'
                f'A{reader} · {description}</a><span class="cell-note">'
                f"{READER_LABELS[reader]}</span></th><td>{selection}</td>"
            )
            if not row:
                cells += '<td colspan="4">Not measured</td>'
            elif "read_seconds_median" not in row:
                cells += '<td colspan="4">No successful read</td>'
            else:
                cells += (
                    f"<td>{row['read_seconds_median']:.2f} s</td>"
                    f"<td>{row['requests_median']:,}</td>"
                    f"<td>{row['bytes_requested_median'] / 1e6:.2f} MB</td>"
                    f"<td>{megabytes_label(row['peak_rss_bytes_max'])}</td>"
                )
            parts.append("<tr>" + cells + "</tr>")
        parts.append("</tbody>")
    return "\n".join(parts)


def workflow_cell(workflow: str, reader: int, note: str = "") -> str:
    """Identify the recipe while preserving visible experiment-specific qualifications."""
    letter, label = WORKFLOW_LABELS[workflow].split(" · ", 1)
    detail = f'<span class="cell-note">{html.escape(note)}</span>' if note else ""
    return (
        f'<th scope="row" class="workflow-{letter.lower()}">'
        f'<a href="#reader-{reader}">{letter}{reader} · {label}</a>{detail}</th>'
    )


EXCLUDED_RUNS = (
    ("runs_with_memory_pressure", "under memory pressure"),
    ("runs_with_errors", "with errors"),
    ("failed", "failed"),
    ("stopped_for_memory", "stopped for memory"),
)


def _read_metric_cells(row: dict | None) -> str:
    """Keep absent and excluded measurements explicit across five resource columns."""
    if not row:
        return '<td colspan="5">Not measured</td>'
    if "read_seconds_median" not in row:
        left_out = ", ".join(f"{row[k]} {text}" for k, text in EXCLUDED_RUNS if row.get(k))
        return f'<td colspan="5">No clean run: {left_out or "nothing measured"}</td>'
    used, runs = row.get("timings_from_runs"), row.get("runs")
    basis = f"{used} of {runs} runs" if used is not None and runs else "Repetitions not recorded"
    memory = row.get("peak_rss_bytes_max")
    return (
        f"<td>{row['read_seconds_median']:.2f} s</td>"
        f"<td>{row['requests_median']:,}</td>"
        f"<td>{row['bytes_requested_median'] / 1e6:.2f} MB</td>"
        f"<td>{megabytes_label(memory) if memory is not None else 'Not recorded'}</td>"
        f"<td>{basis}</td>"
    )


def tile_extraction_rows(result: dict, *, tile_ids: set[str] | None = None) -> str:
    """Group alternatives by identical tile workload, keeping the earlier baseline separate."""
    rows = {
        (r["tile"], r["pattern"], r["method"]): r
        for r in result["summary"]["by_tile_pattern_method"]
    }
    parts = []
    for tile in result["summary"]["tiles"]:
        if tile_ids is not None and tile["tile"] not in tile_ids:
            continue
        windowed = rows.get((tile["tile"], "tile-by-tile", "raster-mask"))
        base = (windowed or {}).get("baseline_stage_2") or {}
        with_baseline = base.get("lakes_with_baseline", [])
        if not base.get("comparable") or not with_baseline:
            baseline_cells = '<td colspan="5">No matching individual-lake comparison</td>'
        else:
            basis = "Sum of lake medians"
            if len(with_baseline) != tile["lakes"]:
                basis += f" · only {len(with_baseline)} of {tile['lakes']} lakes"
            baseline_cells = (
                f"<td>{base['read_seconds']:.2f} s</td><td>{base['requests']:,}</td>"
                f"<td>{base['bytes_requested'] / 1e6:.2f} MB</td>"
                f"<td>Not summarized</td><td>{basis}</td>"
            )
        partly = tile.get("lakes_partly_inside") or 0
        lakes = f"{tile['lakes']} lakes" + (f", {partly} partly inside" if partly else "")
        region = html.escape(REGION_LABELS.get(tile["region"], tile["region"]))
        parts.append(
            '<tbody><tr class="result-group"><th colspan="7" scope="rowgroup">'
            f"{region} · {html.escape(tile['tile'])} · {lakes}</th></tr>"
        )
        parts.append(
            "<tr>"
            + workflow_cell("lake-first", 1, "Separate process per lake")
            + f"<td>{READER_LABELS[1]}</td>"
            + baseline_cells
            + "</tr>"
        )
        for pattern, method, workflow, note in (
            (
                "lake-by-lake",
                "raster-mask",
                "lake-first",
                "One process, reopen files for each lake",
            ),
            ("tile-by-tile", "raster-mask", "tile-first", "Keep files open across lakes"),
            ("whole-tile", "raster-mask", "whole-tile", "Load complete band grids first"),
            (
                "tile-by-tile",
                "lazy-stack",
                "tile-first",
                "Shared graph, compute each lake separately",
            ),
        ):
            reader = METHOD_READERS[method]
            parts.append(
                "<tr>"
                + workflow_cell(workflow, reader, note)
                + f"<td>{READER_LABELS[reader]}</td>"
                + _read_metric_cells(rows.get((tile["tile"], pattern, method)))
                + "</tr>"
            )
        parts.append("</tbody>")
    return "\n".join(parts)


def machine_label(machine: dict) -> str:
    memory = machine.get("memory_total_bytes") or 0
    return (
        f"{machine['cpu_count']}-core {machine['machine']} laptop, {memory / 2**30:.1f} GiB memory"
    )


def cross_tile_rows(result: dict) -> str:
    """Whole-workload medians and ranges from clean repetitions, never per-worker averages."""
    rows = {(r["path"], r["method"]): r for r in result["summary"]["medians"]}
    parts = []
    for method in ("raster-mask", "lazy-stack"):
        for path in ("lake-first", "tile-first"):
            row = rows.get((path, method))
            times = [
                w["end_to_end_seconds"]
                for w in result["summary"]["workloads"]
                if (w["path"], w["method"]) == (path, method) and w["clean"]
            ]
            reader = METHOD_READERS[method]
            cells = workflow_cell(path, reader) + f"<td>{READER_LABELS[reader]}</td>"
            if not row or not times or not row.get("clean_repetitions"):
                cells += '<td colspan="4">No clean complete repetition</td>'
            else:
                cells += (
                    f"<td>{row['wall_seconds']:.2f} s"
                    f'<br><span class="small">{min(times):.2f}–{max(times):.2f} s</span></td>'
                    f"<td>{row['requests']:,}</td><td>{row['bytes_requested'] / 1e6:.2f} MB</td>"
                    f"<td>{row['clean_repetitions']} included"
                    f", {row['excluded_repetitions']} excluded</td>"
                )
            parts.append("<tr>" + cells + "</tr>")
    return "\n".join(parts)


def cross_tile_markers(result: dict) -> dict[str, str]:
    """Headline numbers refer to this frozen experiment and its complete reference workload."""
    summary = result["summary"]
    if not summary["complete"] or not summary["equal"]:
        raise ValueError("Cross-tile narrative requires complete, equal contributions")
    rows = {(r["path"], r["method"]): r for r in summary["medians"]}
    lake = rows[("lake-first", "raster-mask")]
    tile = rows[("tile-first", "raster-mask")]
    lazy_ratio = (
        rows[("tile-first", "lazy-stack")]["bytes_requested"]
        / rows[("lake-first", "lazy-stack")]["bytes_requested"]
    )
    markers = {
        "CROSS_ROWS": cross_tile_rows(result),
        "CROSS_DATE": html.escape(result["measured_at"][:10]),
        "CROSS_MACHINE": html.escape(machine_label(result["machine"])),
        "CROSS_RUNS": str(len(result["runs"])),
        "CROSS_EXPECTED": str(summary["expected_contributions_per_workload"]),
        "CROSS_LAZY_BYTES": f"{lazy_ratio:.2f}",
    }
    for key in ("lakes", "tiles", "acquisitions", "memberships"):
        markers[f"CROSS_{key.upper()}"] = str(summary[key])
    metrics = (("REQUESTS", "requests"), ("BYTES", "bytes_requested"), ("TIME", "wall_seconds"))
    for key, metric in metrics:
        markers[f"CROSS_SAVED_{key}"] = f"{100 * (1 - tile[metric] / lake[metric]):.1f}"
    for region, anchor in (("lanier", "nhd-34974901"), ("okeechobee", "nhd-120024129")):
        coverage = result["plan"]["selection"][region]["coverage"][anchor]
        markers[f"CROSS_{region.upper()}_OVERLAP"] = (
            f"{100 * coverage['support_overlap_m2'] / coverage['support_area_m2']:.2f}"
        )
    return markers


def plain_number(value: float) -> str:
    """Whole numbers without a decimal, otherwise one decimal, with thousands separators."""
    text = f"{value:,.1f}"
    return text[:-2] if text.endswith(".0") else text


def wavelength_label(band: dict) -> str:
    """The band's range in nanometers, from the source's range or its center and bandwidth."""
    if band["range_nm"] is not None:
        low, high = band["range_nm"]
    else:
        low = band["center_nm"] - band["width_nm"] / 2
        high = band["center_nm"] + band["width_nm"] / 2
    return f"{plain_number(low)}–{plain_number(high)}"


def use_chip(use_id: str, uses: dict[str, dict]) -> str:
    kind = " support" if use_id in SUPPORT_USES else ""
    label = html.escape(uses[use_id]["label"], quote=True)
    return f'<span class="use{kind}" title="{label}">{USE_SHORT[use_id]}</span>'


def variant_note(sensor: dict) -> list[str]:
    """How far the other satellites' centers and bandwidths in the source stray from the table."""
    names: dict[str, None] = {}
    centers, widths = [(0.0, "")], [(0.0, "")]
    for band in sensor["bands"]:
        for name, values in (band.get("variants") or {}).items():
            names[name] = None
            centers.append((abs(values["center_nm"] - band["center_nm"]), band["id"]))
            widths.append((abs(values["width_nm"] - band["width_nm"]), band["id"]))
    if not names:
        return []

    def joined(items: list[str]) -> str:
        return (
            " and ".join(items) if len(items) < 3 else ", ".join(items[:-1]) + f", and {items[-1]}"
        )

    def largest(pairs: list[tuple[float, str]]) -> tuple[float, str]:
        # Name every band that ties for the largest difference, not only the last one.
        top = max(value for value, _ in pairs)
        bands = sorted({band for value, band in pairs if band and math.isclose(value, top)})
        return top, joined(bands)

    center, width = largest(centers), largest(widths)
    return [
        f"{joined(list(names))} differ from these values by up to {plain_number(center[0])} nm "
        f"in center wavelength, on {center[1]}, and {plain_number(width[0])} nm in bandwidth, "
        f"on {width[1]}."
    ]


def sensor_band_table(sensor: dict, uses: dict[str, dict], gaps: int = 0) -> str:
    """One sensor's bands: id, name, wavelength range, pixel size, and documented uses."""
    label = html.escape(sensor["label"])
    meta = " · ".join(
        html.escape(part)
        for part in (
            sensor["platform"],
            sensor["instrument"],
            sensor["operator"],
            ACCESS_LABELS[sensor["access"]],
        )
    )
    rows, footnotes = [], []
    for band in sensor["bands"]:
        marker = ""
        if band["note"]:
            footnotes.append(f"<li>{html.escape(band['note'])}</li>")
            marker = f"<sup>{len(footnotes)}</sup>"
        chips = " ".join(use_chip(use["use"], uses) for use in band["uses"])
        rows.append(
            f'<tr><th scope="row">{html.escape(band["id"])}{marker}</th>'
            f"<td>{html.escape(band['name'])}</td>"
            f"<td>{wavelength_label(band)}</td><td>{plain_number(band['resolution_m'])}</td>"
            f"<td>{chips or '<span class="muted">none named</span>'}</td></tr>"
        )
    notes = [html.escape(note) for note in sensor["notes"]] + variant_note(sensor)
    if gaps:
        plural = "band" if gaps == 1 else "bands"
        notes.append(f"{gaps} {plural} did not verify and are not listed.")
    footnote_list = f'<ol class="band-footnotes">{"".join(footnotes)}</ol>' if footnotes else ""
    items = "".join(f"<li>{note}</li>" for note in notes)
    return (
        f'<div class="band-table" data-sensor="{html.escape(sensor["id"], quote=True)}">'
        f'<h4>{label}</h4><p class="small muted">{meta}</p>'
        f'<div class="table-scroll" role="region" aria-label="{label} bands" tabindex="0">'
        '<table class="plans bands"><thead><tr><th scope="col">Band</th><th scope="col">Name</th>'
        '<th scope="col">Wavelength (nm)</th><th scope="col">Pixel (m)</th>'
        '<th scope="col">Water-quality use</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>{footnote_list}"
        '<details class="tech"><summary>Notes on this table</summary>'
        f"<ul>{items}</ul></details></div>"
    )


def sensor_options(sensors: list[dict], selected: str) -> str:
    if selected not in {sensor["id"] for sensor in sensors}:
        raise ValueError(f"Default sensor {selected} is not in the dataset")
    return "".join(
        f'<option value="{html.escape(s["id"], quote=True)}"'
        f"{' selected' if s['id'] == selected else ''}>{html.escape(s['label'])}</option>"
        for s in sensors
    )


def use_legend(uses: list[dict]) -> str:
    by_id = {use["id"]: use for use in uses}
    items = "".join(
        f"<li>{use_chip(use['id'], by_id)} <b>{html.escape(use['label'])}.</b> "
        f"{html.escape(use['definition'])}</li>"
        for use in uses
    )
    return f'<ul class="use-legend">{items}</ul>'


def sensor_sources(dataset: dict) -> str:
    """Source links grouped by publisher, in the dataset's order, then the reading rules."""
    groups: dict[str, list[str]] = {}
    for source in dataset["sources"]:
        title = html.escape(source["title"].split(" | ")[0])
        link = f'<a href="{html.escape(source["url"], quote=True)}">{title}</a>'
        groups.setdefault(html.escape(source["publisher"]), []).append(link)
    links = " ".join(f"{publisher}: {', '.join(items)}." for publisher, items in groups.items())
    checked = html.escape(dataset["verification"]["checker"]["finished_at"][:10])
    return (
        f"<b>Documented:</b> {links} Researched and independently checked {checked}. "
        "Where a source lists a center wavelength and a bandwidth, the range is the center plus "
        "and minus half the bandwidth. A use is listed when a cited source names the band, or "
        "names a wavelength inside it. These are documented uses. They do not validate a model."
    )


def sensor_band_markers(dataset: dict) -> dict[str, str]:
    uses = {use["id"]: use for use in dataset["uses"]}
    tables = "".join(
        sensor_band_table(
            sensor,
            uses,
            sum(g["claim_id"].startswith(f"band-{sensor['id']}-") for g in dataset["gaps"]),
        )
        for sensor in dataset["sensors"]
    )
    return {
        "SENSOR_TABLES": tables,
        "SENSOR_OPTIONS_LEFT": sensor_options(dataset["sensors"], DEFAULT_SENSORS[0]),
        "SENSOR_OPTIONS_RIGHT": sensor_options(dataset["sensors"], DEFAULT_SENSORS[1]),
        "SENSOR_LEGEND": use_legend(dataset["uses"]),
        "SENSOR_SOURCES": sensor_sources(dataset),
        "SENSOR_COUNT": str(len(dataset["sensors"])),
        "SENSOR_BAND_COUNT": str(sum(len(sensor["bands"]) for sensor in dataset["sensors"])),
    }


def workload_rerun_note(result: dict | None) -> str:
    """How many sleep-affected attempts were replaced, for the method notes."""
    lineage = (result or {}).get("rerun")
    if not lineage:
        return ""
    retained = lineage.get("retained_configurations", [])
    return (
        "<p><b>Sleep-affected attempts were rerun.</b> "
        f"{len(lineage['replacement_configurations'])} replacements use the same frozen "
        f"inputs and memory limits. {len(retained)} unaffected results retain their original "
        "dates and source versions. Replacement lazy readers use saved metadata without "
        "live catalog lookups. "
        '<a href="reviews/2026-09-21-sleep-rerun.md">Rerun review</a>.</p>'
    )


def workload_comparison(result: dict | None, execution_audit: dict | None = None) -> str:
    """Keep all planned alternatives visible, and never rank partial work as complete."""
    sections = []
    lineage = (result or {}).get("rerun")
    retained = {tuple(key) for key in (lineage or {}).get("retained_configurations", [])}
    interrupted = {
        (row["cohort"], row["configuration"])
        for row in (execution_audit or {}).get("rows", [])
        if row["sleep_intervals_overlapping"]
    }
    if interrupted:
        sections.append(
            '<p class="note-line"><strong>Sleep interrupted this experiment.</strong> '
            f"{len(interrupted)} attempts overlapped laptop sleep. Their elapsed times do not "
            "establish uninterrupted workload performance. "
            '<a href="reviews/2026-09-19-larger-workload-execution.md">Execution review</a>.</p>'
        )
    for cohort, label in [
        ("dispersed", "100 lakes across the continental U.S."),
        ("florida", "1,000 lakes concentrated in Florida"),
    ]:
        data = (result or {}).get("cohorts", {}).get(cohort, {})
        rows = {row["configuration"]: row for row in data.get("comparisons", [])}
        rendered = []
        for key, (workflow, reader) in WORKLOAD_CONFIGURATIONS.items():
            row = rows.get(key, {})
            complete = row.get("status") == "complete"
            valid = complete and row.get("matches_all_complete_outputs") is True
            state = "Complete · outputs agree" if valid else row.get("status", "Not measured")
            if row.get("status") == "complete" and not valid:
                state = "Complete · agreement unverified"
            sleeping = (cohort, key) in interrupted
            if sleeping:
                state += " · sleep interrupted"
            if (cohort, key) in retained:
                state += " · retained original"
            timed = complete and not sleeping
            seconds = f"{row['extraction_seconds']:,.1f} s" if timed else "—"
            cpu = row.get("cpu", {})
            cpu_seconds = (
                f"{cpu['user'] + cpu['system']:,.1f} s"
                if complete and "user" in cpu and "system" in cpu
                else "—"
            )
            reader_seconds = (
                f"{row['read_and_extract_seconds']:,.1f} s"
                if timed and "read_and_extract_seconds" in row
                else "—"
            )
            io = row.get("io", {})
            requests = f"{io['requests']:,}" if complete and "requests" in io else "—"
            megabytes = (
                f"{io['bytes_requested'] / 1e6:,.1f} MB"
                if complete and "bytes_requested" in io
                else "—"
            )
            peak = row.get("supervision", {}).get("peak_aggregate_rss_bytes")
            memory = f"{peak / 1024**3:.2f} GiB" if peak is not None else "—"
            note = "Control for this comparison" if key == "B-lazy-control" else ""
            rendered.append(
                "<tr>"
                + workflow_cell(workflow, reader, note)
                + "".join(
                    f"<td>{html.escape(str(value))}</td>"
                    for value in (
                        READER_LABELS[reader],
                        state,
                        reader_seconds,
                        seconds,
                        cpu_seconds,
                        requests,
                        megabytes,
                        memory,
                    )
                )
                + "</tr>"
            )
        preflight = data.get("preflight", {})
        coverage = (
            f"<p>{preflight['products']:,} source products · {preflight['tiles']:,} tiles · "
            f"{preflight['tile_dates']:,} tile-dates · "
            f"{preflight['lake_product_memberships']:,} lake-product memberships.</p>"
            if preflight
            else "<p>Exact products and image coverage await input selection.</p>"
        )
        unconverged = preflight.get("unconverged_geometry_count", 0)
        if unconverged:
            coverage += (
                f'<p class="small muted">{unconverged} '
                f"{'lake uses' if unconverged == 1 else 'lakes use'} a recorded approximation "
                "for image selection. Every reader uses the same prepared pixel selections.</p>"
            )
        sections.append(
            f'<h3 class="comparison-heading">{label}</h3>{coverage}'
            '<p class="scroll-hint">Scroll horizontally to compare all columns.</p>'
            '<div class="table-scroll" role="region" tabindex="0" '
            f'aria-label="{html.escape(label)} workflow and reader comparison">'
            '<table class="plans results-table">'
            "<caption>Seven workflow and reader combinations. Codes identify recipes, "
            "with settings and timing qualifications in the method notes below.</caption>"
            '<thead><tr><th scope="col">Workflow + reader</th><th scope="col">Reader</th>'
            '<th scope="col">Status</th><th scope="col">Read + extract</th>'
            '<th scope="col">Total extraction</th><th scope="col">Worker CPU</th>'
            '<th scope="col">Requests</th><th scope="col">Requested bytes</th>'
            '<th scope="col">Peak benchmark RAM</th></tr></thead>'
            "<tbody>" + "\n".join(rendered) + "</tbody></table></div>"
        )
    if result:
        partial_note = ""
        if any(
            row.get("status") == "incomplete"
            for data in result.get("cohorts", {}).values()
            for row in data.get("comparisons", [])
        ):
            partial_note = (
                "Incomplete attempts retain their partial measurements in the evidence file. "
                "Their times do not appear as completed comparisons. Their RAM peaks cover only "
                "the work reached before failure. "
            )
        history_note = (
            'Earlier attempts remain in the <a href="../benchmarks/results/'
            'lazy-reader-workloads-before-sleep-rerun.json">preserved original result</a>. '
            if lineage
            else ""
        )
        sections.append(
            '<p class="source-note"><a href="../benchmarks/results/lazy-reader-workloads.json">'
            "Execution evidence, completion checks, resource limits, and cleanup audit</a>. "
            "Worker CPU sums user and system CPU seconds. Peak RAM includes the supervisor "
            "and worker processes, sampled every 0.1 seconds. Shorter spikes can be missed. "
            f"{partial_note}{history_note}GDAL counters exclude Python catalog requests.</p>"
        )
    return "\n".join(sections)


def workload_audit():
    if not WORKLOAD_AUDIT.exists() or not LAZY_WORKLOADS.exists():
        return None
    value = json.loads(WORKLOAD_AUDIT.read_text())
    if value["result_sha256"] != hashlib.sha256(LAZY_WORKLOADS.read_bytes()).hexdigest():
        raise ValueError("workload audit does not match the current result")
    return value


def usd(value: float, cents: bool = False) -> str:
    """Whole dollars for one-time costs, cents for monthly charges, as in the cost report."""
    return f"${value:,.2f}" if cents else f"${value:,.0f}"


def cost_rows(data: dict, workload: str, case: str = "base") -> tuple[dict, dict]:
    """The backfill estimate and the forward-update estimate for one workload and case."""
    picked = []
    for key in ("estimates", "daily_updates"):
        rows = [r for r in data[key] if (r["workload"], r["case"]) == (workload, case)]
        if len(rows) != 1:
            raise ValueError(f"Expected one {key} row for {workload} {case}, found {len(rows)}")
        picked.append(rows[0])
    return picked[0], picked[1]


def cost_workload_label(row: dict, land_m: str) -> str:
    """Population and pixel classes, with the body count and buffer from the estimates."""
    national, land = COST_WORKLOADS[row["workload"]]
    scope = (
        f"All contiguous US water bodies ({row['bodies']:,})"
        if national
        else f"{row['bodies']:,}-lake sample"
    )
    pixels = f"water + shoreline + {land_m} m nearby land" if land else "water + shoreline only"
    return f"{scope} · {pixels}"


def cost_table_rows(data: dict, land_m: str) -> str:
    """One group per workload with its storage, then each recipe's processing costs."""
    parts = []
    for workload in COST_WORKLOADS:
        row, daily = cost_rows(data, workload)
        label = cost_workload_label(row, land_m)
        stored = row["historical_dynamic_TiB"] * 1024 + row["static_geometry_GiB"]
        parts.append(
            '<tbody><tr class="result-group"><th colspan="6" scope="rowgroup">'
            f'{label}<span class="cell-note">Storage at completion: '
            f"{stored:,.0f} GiB of records and geometry · S3 Standard "
            f"{usd(row['s3_monthly_at_cutoff_usd'], True)} per month, rising by "
            f"{usd(daily['s3_monthly_added_after_one_year_usd'], True)} over the first year"
            "</span></th></tr>"
        )
        for code, (workflow, reader) in COST_RECIPES.items():
            backfill, forward = row["recipes"][code], daily["recipes"][code]
            parts.append(
                "<tr>"
                + workflow_cell(workflow, reader, READER_LABELS[reader])
                + f"<td>{backfill['historical_requested_TB_decimal']:,.0f} TB</td>"
                + f"<td>{usd(backfill['historical_ec2_total_including_prep_put_usd'])}</td>"
                + f"<td>{usd(backfill['historical_lambda_total_including_ec2_prep_put_usd'])}</td>"
                + f"<td>{usd(forward['ec2_ingest_usd_per_month'], True)}</td>"
                + f"<td>{usd(forward['lambda_ingest_usd_per_month'], True)}</td></tr>"
            )
        parts.append("</tbody>")
    return "\n".join(parts)


def cost_estimates() -> dict:
    """Load the generated estimates, refusing a file older than its inputs or its model."""
    data = json.loads(COST_ESTIMATES.read_text())
    for key, source in (("input_sha256", COST_INPUTS), ("model_sha256", COST_MODEL)):
        if data[key] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError(
                f"Cost estimates predate {source.name}. Run tools/estimate_aws_costs.py first."
            )
    return data


def cost_markers(data: dict, inputs: dict) -> dict[str, str]:
    """The cost table and the experiment definitions, from the estimates and their inputs."""
    if data["status"] != "estimated, not measured":
        raise ValueError(f"Unexpected cost estimate status: {data['status']}")
    national, _ = cost_rows(data, "all_land")
    operations = sorted(
        {cost_rows(data, w)[1]["operations"]["monthly_total_usd"] for w in COST_WORKLOADS}
    )
    residuals = {
        cost_rows(data, w)[1]["operations"]["monthly_components_usd"]["residual_allowance"]
        for w in COST_WORKLOADS
    }
    if len(residuals) != 1:
        raise ValueError("Workloads carry different residual operations allowances")
    cap = max(c["a1_b1_byte_ratio"] for c in data["calibration"]["byte_calibration"]["cohorts"])
    for workload in ("all_land", "all_water_shore"):
        recipes = cost_rows(data, workload)[0]["recipes"]
        bytes_a1, bytes_b1 = (recipes[c]["historical_requested_TB_decimal"] for c in ("A1", "B1"))
        if not math.isclose(bytes_a1 / bytes_b1, cap, rel_tol=1e-9):
            raise ValueError("National A1 bytes no longer sit at the largest measured A1/B1 ratio")
    cutoff = date.fromisoformat(inputs["end_exclusive"]) - timedelta(days=1)
    land_m = f"{1000 * inputs['land_radius_km']:,.0f}"
    return {
        "COST_ROWS": cost_table_rows(data, land_m),
        "COST_REVISED": html.escape(inputs["revision_date"]),
        "COST_A1_CAP": f"{cap:.1f}",
        "COST_START": html.escape(inputs["start"]),
        "COST_CUTOFF": cutoff.isoformat(),
        "COST_BODIES": f"{national['bodies']:,}",
        "COST_SAMPLE": f"{inputs['sample_size']:,}",
        "COST_LAND_M": land_m,
        "COST_EC2_VCPU": plain_number(inputs["ec2_instance_vcpu"]),
        "COST_EC2_GIB": plain_number(inputs["ec2_instance_memory_gib"]),
        "COST_LAMBDA_GIB": plain_number(inputs["lambda_memory_gib"]),
        "COST_OPS": " to ".join(dict.fromkeys(usd(v, True) for v in operations)),
        "COST_RESIDUAL": usd(residuals.pop(), True),
        "COST_TAKEAWAY_B1": usd(
            national["recipes"]["B1"]["historical_ec2_total_including_prep_put_usd"]
        ),
        "COST_TAKEAWAY_B3": usd(
            national["recipes"]["B3"]["historical_ec2_total_including_prep_put_usd"]
        ),
        "COST_TAKEAWAY_S3": usd(national["s3_monthly_at_cutoff_usd"], True),
    }


def build_html(inventory: Path = INVENTORY) -> str:
    issues = {issue["id"]: issue for issue in json.loads(inventory.read_text())["issues"]}
    check_placement(issues)
    report = json.loads(REPORT.read_text())
    maps = json.loads(MAPS.read_text())
    pilot = json.loads(PILOT.read_text())
    workloads = json.loads(LAZY_WORKLOADS.read_text()) if LAZY_WORKLOADS.exists() else None
    pilot_props = [feature["properties"] for feature in pilot["features"]]
    pilot_tiers = Counter(p["tier"] for p in pilot_props)
    pilot_classes = sorted({p["size_class_m"] for p in pilot_props if p["tier"] == "pilot"})
    pilot_regions = sorted({p["region"] for p in pilot_props})
    totals = next(f for f in report["findings"] if f["id"] == "GS-10")["numbers"]["totals"]
    raw_results = [json.loads(path.read_text()) for path in RAW_ACCESS]
    copy_difference = json.loads(COPY_DIFFERENCE.read_text())
    lake_extraction = json.loads(LAKE_EXTRACTION.read_text())
    tile_extraction = json.loads(TILE_EXTRACTION.read_text())
    cross_tile_extraction = json.loads(CROSS_TILE_EXTRACTION.read_text())
    sensor_bands = json.loads(SENSOR_BANDS.read_text())
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
        "LAKE_METHOD_ROWS": lake_method_rows(lake_extraction),
        "LAKE_CLASS_ROWS": pixel_class_rows(lake_extraction),
        "LAKE_DATE": html.escape(lake_extraction["measured_at"][:10]),
        "LAKE_MACHINE": html.escape(machine_label(lake_extraction["machine"])),
        "LAKE_LAKES": str(lake_extraction["summary"]["lakes"]),
        "LAKE_TILES": str(lake_extraction["summary"]["distinct_tiles"]),
        "LAKE_RUNS": f"{len(lake_extraction['runs']):,}",
        "LAKE_DIGEST": hashlib.sha256(LAKE_EXTRACTION.read_bytes()).hexdigest(),
        "TILE_ROWS": tile_extraction_rows(tile_extraction, tile_ids={"10SGJ"}),
        "TILE_DETAIL_ROWS": tile_extraction_rows(
            tile_extraction,
            tile_ids={r["tile"] for r in tile_extraction["summary"]["tiles"]} - {"10SGJ"},
        ),
        "TILE_DATE": html.escape(tile_extraction["measured_at"][:10]),
        "TILE_MACHINE": html.escape(machine_label(tile_extraction["machine"])),
        "TILE_LAKES": str(tile_extraction["summary"]["lakes"]),
        "TILE_TILES": str(tile_extraction["summary"]["distinct_tiles"]),
        "TILE_RUNS": f"{len(tile_extraction['runs']):,}",
        "TILE_DIGEST": hashlib.sha256(TILE_EXTRACTION.read_bytes()).hexdigest(),
        "CROSS_DIGEST": hashlib.sha256(CROSS_TILE_EXTRACTION.read_bytes()).hexdigest(),
        **cross_tile_markers(cross_tile_extraction),
        "SENSOR_DIGEST": hashlib.sha256(SENSOR_BANDS.read_bytes()).hexdigest(),
        **sensor_band_markers(sensor_bands),
        "COST_DIGEST": hashlib.sha256(COST_ESTIMATES.read_bytes()).hexdigest(),
        **cost_markers(cost_estimates(), json.loads(COST_INPUTS.read_text())),
        "WORKLOAD_COMPARISON": workload_comparison(workloads, workload_audit()),
        "WORKLOAD_RERUN_NOTE": workload_rerun_note(workloads),
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
