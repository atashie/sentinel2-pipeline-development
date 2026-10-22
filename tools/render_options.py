"""Render the colleague-facing assessment page. Standard library only, no network.

Edit s2-options.template.html for the narrative and layout. The renderer fills the markers:
survey counts and the monthly coverage strip from the gap survey report, the risk and cost
bullets from the inventory's plain-language lines, map facts from the provenance record,
pilot counts from the manifest, prototype tables and pixel checks from saved results, the sensor
band tables from the bound sensor band dataset, the AWS cost table from both options' generated
cost estimates, and the input digests.
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
AQR_COVERAGE = RESULTS / "aqr-coverage.json"
AQR_HEADERS = RESULTS / "aqr-headers.json"
AQR_VALIDITY = RESULTS / "aqr-validity.json"
AQR_PAIRS = RESULTS / "aqr-pairs.json"
AQR_WORKLOADS = RESULTS / "aqr-workloads.json"
AQR_OVERLAP = RESULTS / "aqr-overlap.json"
L2A_LATENCY = RESULTS / "l2a-latency.json"
COST_ESTIMATES = DOCS / "cost-analysis" / "estimates.json"
COST_ESTIMATES_ACOLITE = DOCS / "cost-analysis" / "estimates-acolite-only.json"
COST_INPUTS = DOCS / "cost-analysis" / "inputs.json"
COST_MODEL = ROOT / "tools" / "estimate_aws_costs.py"
GAP_SURVEY = RESULTS / "gap-survey.json"
COST_DEPENDENCIES = {
    "acolite": {
        "evidence_sha256": AQR_WORKLOADS,
        "cohort_blocks_sha256": DOCS / "cost-analysis" / "aqr-cohort-blocks.json",
        "survey_sha256": GAP_SURVEY,
        "coverage_sha256": AQR_COVERAGE,
    },
    "sen2cor": {
        "evidence_sha256": LAZY_WORKLOADS,
        "cohort_blocks_sha256": DOCS / "cost-analysis" / "cohort-blocks.json",
        "survey_sha256": GAP_SURVEY,
    },
}
# Workload key: whether it is the national population, and whether it keeps nearby land.
COST_WORKLOADS = {
    "all_land": (True, True),
    "all_water_shore": (True, False),
    "sample_land": (False, True),
    "sample_water_shore": (False, False),
}
# Recipes estimated for both options. A1 has no trial on the primary product.
COST_RECIPES = {"B1": ("tile-first", 1), "B3": ("tile-first", 3)}
# The two standalone source options of decision 0009, in page order.
SOURCE_OPTIONS = {"acolite": "ACOLITE only", "sen2cor": "Sen2Cor only"}
# Frozen result keys of the readers that ran on both options, and their recipes.
OPTION_READERS = {"B-raster": ("tile-first", 1), "B-lazy": ("tile-first", 3)}
WORKLOAD_COHORTS = {
    "dispersed": "Dispersed lakes across the continental U.S.",
    "florida": "Lakes concentrated in Florida",
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
    "RISK_CORRECTION": ["I-31", "I-35"],
    "RISK_LAND": ["I-03", "I-15", "I-10", "I-09", "I-28", "I-02"],
    "RISK_FLAGS": ["I-32", "I-01", "I-12", "I-14", "I-13", "I-11", "I-26"],
    "RISK_TILES": ["I-30", "I-04"],
    "RISK_VERSIONS": ["I-34", "I-05", "I-06", "I-29", "I-16", "I-17", "I-19"],
    "RISK_GRID": ["I-36", "I-07"],
    "RISK_MISSING": ["I-08", "I-24", "I-25", "I-27"],
    # Issues about the primary archive itself, shown in the archives section.
    "ARCHIVE_ITEMS": ["I-33", "I-40", "I-37", "I-38", "I-39"],
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


def aqr_coverage_strip(rows: list[dict]) -> str:
    """Monthly share of Earth Search acquisitions held by the USGS product and by Collection 1."""
    rows = [r for r in rows if r["reference"]]
    cell, left, top, height, gap = 10, 170, 16, 22, 6
    width = left + len(rows) * cell + 8
    total = top + 2 * (height + gap) + 20
    series = [("USGS aquatic reflectance", "aqr"), ("Collection 1 copy", "collection1")]
    parts = [
        f'<svg viewBox="0 0 {width} {total}" role="img" aria-labelledby="aqr-coverage-title">',
        '<title id="aqr-coverage-title">Monthly share of Earth Search acquisitions held by the '
        "USGS aquatic reflectance product and by the Collection 1 copy, across the surveyed "
        "lower-48 tiles.</title>",
    ]
    for j, (label, key) in enumerate(series):
        y = top + j * (height + gap)
        parts.append(
            f'<text x="{left - 8}" y="{y + 15}" text-anchor="end" font-size="12">{label}</text>'
        )
        for i, row in enumerate(rows):
            fraction = min(row[key] / row["reference"], 1.0)
            tip = f"{row['month']}: {fraction:.0%} of {row['reference']} acquisitions"
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


def coverage_recent_from(coverage: dict) -> str:
    """The first sensing date of the recent-latency window, from any tile record."""
    return coverage["tiles"][0]["latency_recent"]["sensed_from"]


def aqr_markers(coverage: dict, headers: dict) -> dict[str, str]:
    """Numbers the archive section states about the primary product, from probes T1 to T3."""
    summary = coverage["summary"]
    rows = summary["coverage_by_month"]
    shares = []
    for year in sorted({r["month"][:4] for r in rows}):
        reference = sum(r["reference"] for r in rows if r["month"].startswith(year))
        held = sum(r["aqr"] for r in rows if r["month"].startswith(year))
        # Full years with a reference, from the first year Earth Search covers in full.
        if reference and year >= "2018" and year < coverage["window"]["end"][:4]:
            shares.append(held / reference)
    joins = summary["join_totals"]
    scenes = sum(joins.values())
    joined = scenes - joins.get("none none", 0)
    exact = sum(v for k, v in joins.items() if k.startswith("exact"))
    if scenes != summary["scenes"]:
        raise ValueError("Join totals do not cover every scene")
    latency = summary["latency_recent"] | {"sensed_from": coverage_recent_from(coverage)}
    any_same = sum(
        counts.get("same_baseline_in_some_collection", 0)
        for counts in summary["join_any_collection_by_year"].values()
    )
    return {
        "AQR_COVERAGE_STRIP": aqr_coverage_strip(rows),
        "AQR_DATE": html.escape(coverage["measured_at"][:10]),
        "AQR_TILES": str(summary["tiles"]),
        "AQR_SCENES": f"{summary['scenes']:,}",
        "AQR_SHARE_LOW": f"{100 * min(shares):.0f}",
        "AQR_SHARE_HIGH": f"{100 * max(shares):.0f}",
        "AQR_FIRST_YEAR": "2018",
        "AQR_JOIN_PERCENT": f"{100 * joined / scenes:.0f}",
        "AQR_SAME_BASELINE_PERCENT": f"{100 * exact / scenes:.0f}",
        "AQR_ANY_BASELINE_PERCENT": f"{100 * any_same / scenes:.0f}",
        "AQR_RECENT_FROM": html.escape(latency["sensed_from"]),
        "AQR_LATENCY_HOURS": f"{24 * latency['median_days']:.0f}",
        "AQR_LATENCY_P90_DAYS": f"{latency['p90_days']:.1f}",
        "AQR_LATENCY_SCENES": f"{latency['scenes']:,}",
        "AQR_TILE_PREFIXES": f"{headers['summary']['tile_prefixes']:,}",
        "AQR_DIGEST": ", ".join(
            hashlib.sha256(path.read_bytes()).hexdigest() for path in (AQR_HEADERS, AQR_COVERAGE)
        ),
    }


def l2a_latency_markers(latency: dict, coverage: dict) -> dict[str, str]:
    """Sen2Cor arrival on the primary product's window, censored at its listing time."""
    matched = latency["summary"]["sentinel-2-c1-l2a"]["bucket_first_matched_cutoff"]
    if latency["window"]["start"] != coverage_recent_from(coverage):
        raise ValueError("The latency survey and the coverage survey use different windows")
    if matched["cutoff"] != coverage["measured_at"]:
        raise ValueError("The latency survey is not censored at the coverage listing time")
    return {
        "L2A_LATENCY_HOURS": f"{24 * matched['median_days']:.0f}",
        "L2A_LATENCY_P90_HOURS": f"{24 * matched['p90_days']:.0f}",
        "L2A_LATENCY_DIGEST": hashlib.sha256(L2A_LATENCY.read_bytes()).hexdigest(),
    }


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


def workflow_cell(workflow: str, reader: int, note: str = "") -> str:
    """Identify the recipe while preserving visible experiment-specific qualifications."""
    letter, label = WORKFLOW_LABELS[workflow].split(" · ", 1)
    detail = f'<span class="cell-note">{html.escape(note)}</span>' if note else ""
    return (
        f'<th scope="row" class="workflow-{letter.lower()}">'
        f'<a href="#reader-{reader}">{letter}{reader} · {label}</a>{detail}</th>'
    )


def machine_label(machine: dict) -> str:
    memory = machine.get("memory_total_bytes") or 0
    return (
        f"{machine['cpu_count']}-core {machine['machine']} laptop, {memory / 2**30:.1f} GiB memory"
    )


def cross_tile_markers(result: dict) -> dict[str, str]:
    """Headline numbers refer to this frozen experiment and its complete reference workload."""
    summary = result["summary"]
    if not summary["complete"] or not summary["equal"]:
        raise ValueError("Cross-tile narrative requires complete, equal contributions")
    rows = {(r["path"], r["method"]): r for r in summary["medians"]}
    lake = rows[("lake-first", "raster-mask")]
    tile = rows[("tile-first", "raster-mask")]
    markers = {
        "CROSS_DATE": html.escape(result["measured_at"][:10]),
        "CROSS_EXPECTED": str(summary["expected_contributions_per_workload"]),
    }
    for key in ("lakes", "tiles", "acquisitions", "memberships"):
        markers[f"CROSS_{key.upper()}"] = str(summary[key])
    metrics = (("REQUESTS", "requests"), ("BYTES", "bytes_requested"), ("TIME", "wall_seconds"))
    for key, metric in metrics:
        markers[f"CROSS_SAVED_{key}"] = f"{100 * (1 - tile[metric] / lake[metric]):.0f}"
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


def workload_audit():
    if not WORKLOAD_AUDIT.exists() or not LAZY_WORKLOADS.exists():
        return None
    value = json.loads(WORKLOAD_AUDIT.read_text())
    if value["result_sha256"] != hashlib.sha256(LAZY_WORKLOADS.read_bytes()).hexdigest():
        raise ValueError("workload audit does not match the current result")
    return value


def option_workloads(product: dict, reference: dict, audit: dict | None) -> list[dict]:
    """Readers B1 and B3 on each option and cohort. Refuse any run that is incomplete or unequal."""
    if audit is None:
        raise ValueError("The Level-2A rows need the sleep audit of their runs")
    audited: dict[tuple[str, str], list[dict]] = {}
    for row in audit["rows"]:
        audited.setdefault((row["cohort"], row["configuration"]), []).append(row)
    rows = []
    for cohort in WORKLOAD_COHORTS:
        sources = {
            "acolite": (product["workloads"][cohort], product["workloads"][cohort]),
            "sen2cor": (reference["cohorts"][cohort], reference["cohorts"][cohort]["preflight"]),
        }
        for key, (workflow, reader) in OPTION_READERS.items():
            for option, (data, counts) in sources.items():
                runs = [r for r in data["comparisons"] if r["configuration"] == key]
                if len(runs) != 1:
                    raise ValueError(f"Expected one {key} run for {option} {cohort}")
                run = runs[0]
                if (
                    run["status"] != "complete"
                    or run.get("matches_all_complete_outputs") is not True
                ):
                    raise ValueError(f"{option} {cohort} {key} lacks a complete, agreeing run")
                if option == "sen2cor":
                    checks = audited.get((cohort, key), [])
                    if len(checks) != 1:
                        raise ValueError(f"{cohort} {key} needs one sleep audit row")
                    if checks[0]["sleep_intervals_overlapping"]:
                        raise ValueError(f"{cohort} {key} overlapped laptop sleep")
                rows.append(
                    {
                        "cohort": cohort,
                        "option": option,
                        "workflow": workflow,
                        "reader": reader,
                        "lakes": counts["lakes"],
                        "products": counts["products"],
                        "seconds": run["extraction_seconds"],
                        "cpu": run["cpu"]["user"] + run["cpu"]["system"],
                        "requests": run["io"]["requests"],
                        "bytes": run["io"]["bytes_requested"],
                        "peak": run["supervision"]["peak_aggregate_rss_bytes"],
                        "date": run["started_at"][:10],
                    }
                )
    return rows


def option_workload_rows(rows: list[dict]) -> str:
    """One group per cohort, then each reader on each option."""
    parts = []
    for cohort, label in WORKLOAD_COHORTS.items():
        parts.append(
            '<tbody><tr class="result-group">'
            f'<th colspan="9" scope="rowgroup">{html.escape(label)}</th></tr>'
        )
        for row in (r for r in rows if r["cohort"] == cohort):
            values = (
                SOURCE_OPTIONS[row["option"]],
                f"{row['lakes']:,} · {row['products']:,}",
                f"{row['seconds']:,.1f} s",
                f"{row['cpu']:,.1f} s",
                f"{row['requests']:,}",
                f"{row['bytes'] / 1e6:,.1f} MB",
                f"{row['peak'] / 1024**3:.2f} GiB",
                row["date"],
            )
            parts.append(
                "<tr>"
                + workflow_cell(row["workflow"], row["reader"], READER_LABELS[row["reader"]])
                + "".join(f"<td>{html.escape(value)}</td>" for value in values)
                + "</tr>"
            )
        parts.append("</tbody>")
    return "\n".join(parts)


def percent_range(values: list[float]) -> str:
    """Whole percents, one value when they round alike, otherwise the lowest to the highest."""
    low, high = (f"{100 * value:.0f}" for value in (min(values), max(values)))
    return low if low == high else f"{low} to {high}"


def option_workload_markers(product: dict, reference: dict, audit: dict | None) -> dict[str, str]:
    """The main comparison and the takeaway numbers. Refuse any claim the runs contradict."""
    rows = option_workloads(product, reference, audit)
    pick = {(r["cohort"], r["option"], r["reader"]): r for r in rows}
    for cohort in WORKLOAD_COHORTS:
        for option in SOURCE_OPTIONS:
            b1, b3 = pick[(cohort, option, 1)], pick[(cohort, option, 3)]
            if not (
                b1["cpu"] < b3["cpu"]
                and b1["requests"] < b3["requests"]
                and b3["bytes"] < b1["bytes"]
                and b3["seconds"] < b1["seconds"]
            ):
                raise ValueError(f"B1 and B3 no longer split as the takeaways state: {option}")
    for option in SOURCE_OPTIONS:
        for reader in (1, 3):
            florida, dispersed = (
                pick[("florida", option, reader)],
                pick[("dispersed", option, reader)],
            )
            if not (
                florida["seconds"] < dispersed["seconds"] and florida["bytes"] < dispersed["bytes"]
            ):
                raise ValueError("Florida no longer runs faster on fewer bytes")
    florida = [(pick[("florida", "acolite", r)], pick[("florida", "sen2cor", r)]) for r in (1, 3)]
    if any(aco["requests"] < s2c["requests"] for aco, s2c in florida):
        raise ValueError("ACOLITE files no longer take more requests in Florida")
    if any(aco["bytes"] >= s2c["bytes"] for aco, s2c in florida):
        raise ValueError("ACOLITE files no longer take fewer bytes in Florida")
    disp = product["workloads"]["dispersed"]
    fl = product["workloads"]["florida"]

    def faster(cohort: str) -> str:
        b1, b3 = pick[(cohort, "acolite", 1)], pick[(cohort, "acolite", 3)]
        return f"{100 * (1 - b3['seconds'] / b1['seconds']):.0f}"

    return {
        "OPTION_WORKLOAD_ROWS": option_workload_rows(rows),
        "T6_DATE": html.escape(product["measured_at"][:10]),
        "T6_BYTE_SHARE": percent_range([aco["bytes"] / s2c["bytes"] for aco, s2c in florida]),
        "T6_MORE_REQUESTS": percent_range(
            [aco["requests"] / s2c["requests"] - 1 for aco, s2c in florida]
        ),
        "T6_DISP_B1_CPU": f"{pick[('dispersed', 'acolite', 1)]['cpu']:.1f}",
        "T6_DISP_B3_CPU": f"{pick[('dispersed', 'acolite', 3)]['cpu']:.1f}",
        "T6_B3_FASTER_DISP": faster("dispersed"),
        "T6_B3_FASTER_FL": faster("florida"),
        "T6_RAM_LOW": f"{min(r['peak'] for r in rows) / 1024**3:.2f}",
        "T6_RAM_HIGH": f"{max(r['peak'] for r in rows) / 1024**3:.2f}",
        "T6_DISP_LAKES": f"{disp['lakes']:,}",
        "T6_DISP_DROPPED": str(len(disp["dropped_lakes"])),
        "T6_DISP_PRODUCTS": f"{disp['products']:,}",
        "T6_DISP_TILES": f"{disp['tiles']:,}",
        "T6_DISP_SAME": f"{disp['same_acquisitions']['same_item_as_reference']:,}",
        "T6_FL_LAKES": f"{fl['lakes']:,}",
        "T6_FL_PRODUCTS": f"{fl['products']:,}",
        "T6_FL_SAME": f"{fl['same_acquisitions']['same_item_as_reference']:,}",
        "T6_FL_TILES": f"{fl['tiles']:,}",
    }


def no_data_exceptions(diagnostic: dict) -> None:
    """The page states one record where counts differ: ten bands hold values on two flagged
    near-land pixels, and B04 lacks two values. Refuse any other pattern."""
    mismatches = diagnostic["mismatches"]
    records = {(m["product"], m["water_body_id"], m["class"]) for m in mismatches}
    if len(records) != 1 or any(m["no_data"] >= m["out_of_scene_flag"] for m in mismatches):
        raise ValueError("Probe T4 no-data counts no longer follow the out-of-scene flag")
    ((product, _, cls),) = records
    bands = diagnostic["scenes_with_no_data"][product]["bands"]
    flagged = {m["out_of_scene_flag"] for m in mismatches}
    missing = {band: count for band, count in bands.items() if count}
    if cls != "near_land" or flagged != {2} or len(mismatches) != 10 or missing != {"B04": 2}:
        raise ValueError("Probe T4's no-data exception changed. Revise the pixel checks.")


def pixel_check_markers(validity: dict, pairs: dict, overlap: dict) -> dict[str, str]:
    """What the pixel checks state, from probes T4, T5, and T7 under their declared rules."""
    t4 = validity["summary"]
    if any(verdict["masked_by_processor"] for verdict in t4["verdicts"].values()):
        raise ValueError("Probe T4 found a class the processor masks")
    no_data_exceptions(t4["no_data_diagnostic"])
    t5 = pairs["summary"]
    if any(classes["agree"] for subset in t5["verdicts"].values() for classes in subset.values()):
        raise ValueError("Probe T5 found a band where the options agree")
    clear = t5["pooled"]["both_clear_water"]["interior"]
    pooled = overlap["summary"]["pooled"]
    differs = {
        (option, cls, band)
        for option, subsets in pooled.items()
        for classes in subsets.values()
        for cls, bands in classes.items()
        for band, stats in bands.items()
        if stats["verdict"] != "agree"
    }
    if differs != {("sen2cor", "shoreline", "B01"), ("sen2cor", "near_land", "B01")}:
        raise ValueError("Probe T7's pooled exceptions changed. Revise the pixel checks.")
    relative = overlap["diagnostics"]["relative_offsets"]

    def largest(option: str) -> str:
        offset, band = max(
            (abs(value), band)
            for pair in relative.values()
            for band, value in pair[option]["interior"].items()
            if value is not None
        )
        if band != "B01":
            raise ValueError(f"{option}'s largest tile offset moved from B01 to {band}")
        return f"{100 * offset:.0f}"

    shares = t4["shares"]
    cloud = shares["interior"]["cloud"]
    markers = {
        "T4_SCENES": str(t4["scenes_read"]),
        "T4_TILES": str(t4["distinct_tiles"]),
        "T4_LAKES": str(t4["lakes"]),
        "T4_CLOUD_UNFLAGGED": f"{100 * cloud['scl_cloud_unflagged_of_cloud']:.0f}",
        "T4_SHADOW_UNFLAGGED": f"{100 * cloud['scl_shadow_unflagged_of_shadow']:.0f}",
        "T5_LOW": f"{100 * min(b['share_disagree'] for b in clear.values()):.0f}",
        "T5_HIGH": f"{100 * max(b['share_disagree'] for b in clear.values()):.0f}",
        "T7_PAIRS": str(overlap["summary"]["pairs_compared"]),
        "T7_ACOLITE_MAX": largest("acolite"),
        "T7_SEN2COR_MAX": largest("sen2cor"),
    }
    for cls, key in (("interior", "INTERIOR"), ("shoreline", "SHORE"), ("near_land", "NEAR")):
        markers[f"T4_NONWATER_{key}"] = f"{100 * shares[cls]['flags']['bits']['swir']:.0f}"
        markers[f"T4_NOFLAG_{key}"] = f"{100 * shares[cls]['flags']['none']:.0f}"
    return markers


def workload_dates(result: dict) -> str:
    """The first and last run dates of the Level-2A larger-workload comparison."""
    dates = sorted(
        row["started_at"][:10]
        for cohort in result["cohorts"].values()
        for row in cohort["comparisons"]
    )
    return dates[0] if dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}"


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


def cost_table_rows(options: dict[str, dict], land_m: str) -> str:
    """One group per workload with each option's storage, then each recipe on each option."""
    parts = []
    for workload in COST_WORKLOADS:
        picked = {option: cost_rows(data, workload) for option, data in options.items()}
        if len({row["bodies"] for row, _ in picked.values()}) != 1:
            raise ValueError(f"The options estimate different body counts for {workload}")
        label = cost_workload_label(next(iter(picked.values()))[0], land_m)
        storage = []
        for option, (row, daily) in picked.items():
            stored = row["historical_dynamic_TiB"] * 1024 + row["static_geometry_GiB"]
            storage.append(
                f'<span class="cell-note">{SOURCE_OPTIONS[option]}: storage at completion '
                f"{stored:,.0f} GiB of records and geometry · S3 Standard "
                f"{usd(row['s3_monthly_at_cutoff_usd'], True)} per month, rising by "
                f"{usd(daily['s3_monthly_added_after_one_year_usd'], True)} over the first year"
                "</span>"
            )
        parts.append(
            '<tbody><tr class="result-group"><th colspan="7" scope="rowgroup">'
            f"{label}{''.join(storage)}</th></tr>"
        )
        for code, (workflow, reader) in COST_RECIPES.items():
            for option, (row, daily) in picked.items():
                backfill, forward = row["recipes"][code], daily["recipes"][code]
                parts.append(
                    "<tr>"
                    + workflow_cell(workflow, reader, READER_LABELS[reader])
                    + f"<td>{SOURCE_OPTIONS[option]}</td>"
                    + f"<td>{backfill['historical_requested_TB_decimal']:,.0f} TB</td>"
                    + f"<td>{usd(backfill['historical_ec2_total_including_prep_put_usd'])}</td>"
                    + "<td>"
                    + usd(backfill["historical_lambda_total_including_ec2_prep_put_usd"])
                    + "</td>"
                    + f"<td>{usd(forward['ec2_ingest_usd_per_month'], True)}</td>"
                    + f"<td>{usd(forward['lambda_ingest_usd_per_month'], True)}</td></tr>"
                )
        parts.append("</tbody>")
    return "\n".join(parts)


def cost_estimates() -> dict[str, dict]:
    """Load both options' estimates, refusing a file older than any input it records."""
    options = {}
    for option, path in (("acolite", COST_ESTIMATES_ACOLITE), ("sen2cor", COST_ESTIMATES)):
        data = json.loads(path.read_text())
        sources = {
            "input_sha256": COST_INPUTS,
            "model_sha256": COST_MODEL,
        } | COST_DEPENDENCIES[option]
        for key, source in sources.items():
            if data[key] != hashlib.sha256(source.read_bytes()).hexdigest():
                raise ValueError(
                    f"Cost estimates predate {source.name}. Run tools/estimate_aws_costs.py first."
                )
        if data["option"] != f"{option}_only":
            raise ValueError(f"{path.name} holds option {data['option']}")
        options[option] = data
    return options


def cost_markers(options: dict[str, dict], inputs: dict) -> dict[str, str]:
    """The cost table and the experiment definitions, from both options' estimates and inputs."""
    for data in options.values():
        if data["status"] != "estimated, not measured":
            raise ValueError(f"Unexpected cost estimate status: {data['status']}")
    sen2cor = options["sen2cor"]
    cap = max(c["a1_b1_byte_ratio"] for c in sen2cor["calibration"]["byte_calibration"]["cohorts"])
    for workload in ("all_land", "all_water_shore"):
        recipes = cost_rows(sen2cor, workload)[0]["recipes"]
        bytes_a1, bytes_b1 = (recipes[c]["historical_requested_TB_decimal"] for c in ("A1", "B1"))
        if not math.isclose(bytes_a1 / bytes_b1, cap, rel_tol=1e-9):
            raise ValueError("National A1 bytes no longer sit at the largest measured A1/B1 ratio")
    daily = [cost_rows(data, w)[1] for data in options.values() for w in COST_WORKLOADS]
    operations = [row["operations"]["monthly_total_usd"] for row in daily]
    residuals = {row["operations"]["monthly_components_usd"]["residual_allowance"] for row in daily}
    if len(residuals) != 1:
        raise ValueError("Workloads carry different residual operations allowances")
    national = {option: cost_rows(data, "all_land")[0] for option, data in options.items()}
    rates = {
        option: data["survey_rate_evidence"]["recent_annual_tile_rate"]
        for option, data in options.items()
    }
    ops = (min(operations), max(operations))
    share = options["acolite"]["survey_rate_evidence"]["historical_share_of_earth_search_any"]
    cutoff = date.fromisoformat(inputs["end_exclusive"]) - timedelta(days=1)
    land_m = f"{1000 * inputs['land_radius_km']:,.0f}"
    markers = {
        "COST_ROWS": cost_table_rows(options, land_m),
        "COST_A1_CAP": f"{cap:.1f}",
        "COST_START": html.escape(inputs["start"]),
        "COST_CUTOFF": cutoff.isoformat(),
        "COST_BODIES": f"{national['sen2cor']['bodies']:,}",
        "COST_SAMPLE": f"{inputs['sample_size']:,}",
        "COST_LAND_M": land_m,
        "COST_EC2_VCPU": plain_number(inputs["ec2_instance_vcpu"]),
        "COST_EC2_GIB": plain_number(inputs["ec2_instance_memory_gib"]),
        "COST_LAMBDA_GIB": plain_number(inputs["lambda_memory_gib"]),
        "COST_OPS": " to ".join(dict.fromkeys(usd(v, True) for v in ops)),
        "COST_RESIDUAL": usd(residuals.pop(), True),
        "COST_ACQ_SHARE": f"{100 * share:.0f}",
    }
    for option, key in (("acolite", "ACO"), ("sen2cor", "S2C")):
        recipes = national[option]["recipes"]
        markers[f"COST_RATE_{key}"] = f"{rates[option]:.1f}"
        markers[f"COST_TAKEAWAY_{key}_B1"] = usd(
            recipes["B1"]["historical_ec2_total_including_prep_put_usd"]
        )
        markers[f"COST_TAKEAWAY_{key}_S3"] = usd(national[option]["s3_monthly_at_cutoff_usd"], True)
    return markers


def build_html(inventory: Path = INVENTORY) -> str:
    issues = {issue["id"]: issue for issue in json.loads(inventory.read_text())["issues"]}
    check_placement(issues)
    report = json.loads(REPORT.read_text())
    maps = json.loads(MAPS.read_text())
    pilot = json.loads(PILOT.read_text())
    workloads = json.loads(LAZY_WORKLOADS.read_text())
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
    coverage = json.loads(AQR_COVERAGE.read_text())
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
        "LAKE_DATE": html.escape(lake_extraction["measured_at"][:10]),
        "LAKE_DIGEST": hashlib.sha256(LAKE_EXTRACTION.read_bytes()).hexdigest(),
        "TILE_DATE": html.escape(tile_extraction["measured_at"][:10]),
        "TILE_DIGEST": hashlib.sha256(TILE_EXTRACTION.read_bytes()).hexdigest(),
        "CROSS_DIGEST": hashlib.sha256(CROSS_TILE_EXTRACTION.read_bytes()).hexdigest(),
        **cross_tile_markers(cross_tile_extraction),
        "SENSOR_DIGEST": hashlib.sha256(SENSOR_BANDS.read_bytes()).hexdigest(),
        **sensor_band_markers(sensor_bands),
        **cost_markers(cost_estimates(), json.loads(COST_INPUTS.read_text())),
        **option_workload_markers(
            json.loads(AQR_WORKLOADS.read_text()), workloads, workload_audit()
        ),
        **pixel_check_markers(
            json.loads(AQR_VALIDITY.read_text()),
            json.loads(AQR_PAIRS.read_text()),
            json.loads(AQR_OVERLAP.read_text()),
        ),
        "WORKLOAD_DIGEST": hashlib.sha256(LAZY_WORKLOADS.read_bytes()).hexdigest(),
        "WORKLOAD_DATES": workload_dates(workloads),
        "T6_DIGEST": hashlib.sha256(AQR_WORKLOADS.read_bytes()).hexdigest(),
        "PIXEL_DIGEST": ", ".join(
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (AQR_VALIDITY, AQR_PAIRS, AQR_OVERLAP)
        ),
        "COST_DIGEST": ", ".join(
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (COST_ESTIMATES_ACOLITE, COST_ESTIMATES)
        ),
        **aqr_markers(coverage, json.loads(AQR_HEADERS.read_text())),
        **l2a_latency_markers(json.loads(L2A_LATENCY.read_text()), coverage),
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
