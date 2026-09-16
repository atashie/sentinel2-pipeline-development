"""Stage 3, many lakes in one tile: three read patterns and four methods per tile.

Runs only when the user invokes it. It contacts the Earth Search STAC API to choose the
Collection 1 tiles and acquisitions that place every pilot lake, then reads every lake of a
tile from the public bucket in one process per run. Nothing is written back to a provider.

    uv run python benchmarks/tile_extraction.py --dry-run                    # plan, no network
    uv run python benchmarks/tile_extraction.py --regions tahoe --repeat 1   # one region, once
    uv run python benchmarks/tile_extraction.py                              # every tile, 3 times

Read patterns, the loop order of one run:

    lake-by-lake  Lakes outermost. Every file is opened again for each lake and the lake's
                  window is read. Stage 2's order in one process instead of one per lake.
    tile-by-tile  Files outermost. Each file is opened once and every lake's window is read
                  from it before the next file. The lazy stack builds one graph per resolution
                  on the whole tile and computes each lake's window from it separately.
    whole-tile    Each file is read entirely once. Every lake is extracted from memory.

The methods are stage 2's: naive-clip, raster-mask, index-lists, lazy-stack. A method chooses
a lake's pixels. A pattern chooses what is read. Every run is a fresh process with cold caches,
started one at a time under a memory budget. Patterns and methods both rotate their order
between repetitions. Stage 2's per-lake numbers for the same acquisition are the baseline.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))

import lake_extraction as stage2  # noqa: E402

from s2proto import harness, masks  # noqa: E402

PATTERNS = ["lake-by-lake", "tile-by-tile", "whole-tile"]
PATTERN_NOTES = {
    "lake-by-lake": (
        "Lakes outermost. Every file is opened again for each lake and the lake's window is "
        "read. Stage 2's order in one process, so GDAL's caches stay warm between lakes. The "
        "lazy stack builds one graph per lake and resolution on the lake's window."
    ),
    "tile-by-tile": (
        "Files outermost. Each file is opened once and every lake's window is read from it "
        "before the next file. The lazy stack builds one graph per resolution on the whole "
        "tile and computes each lake's window from it separately. Decoded chunks are not "
        "retained between those computations."
    ),
    "whole-tile": (
        "Each file is read entirely once, one shared read, and every lake is extracted from memory."
    ),
}
METHODS = list(stage2.METHODS)
METHOD_NOTES = stage2.METHOD_NOTES
GDAL_CACHE_BYTES = 512 * 1024**2
GDAL_ENV = {**stage2.GDAL_ENV, "GDAL_CACHEMAX": GDAL_CACHE_BYTES}
"""Stage 2's reader configuration plus a block cache of 512 MiB. Stage 2 used GDAL's default.

`rasterio.Env` takes `GDAL_CACHEMAX` in bytes. The environment variable of the same name
takes an unsuffixed value below 100,000 as megabytes and a larger one as bytes, so this
integer means the same size in both places. The run of 2026-09-15 passed 512 here and so
held a 512-byte block cache. Its records show `GDAL_CACHEMAX: 512`. Every worker now
records the cache it held, in bytes.
"""
LAZY_CHUNK = stage2.LAZY_CHUNK
LAZY_WORKERS = 4
"""Dask threads for the lazy stack, fixed so concurrency does not follow the machine."""
MANIFEST = stage2.MANIFEST
DEFAULT_BASELINE = ROOT / "benchmarks" / "results" / "lake-extraction.json"
IMPLEMENTATION = {
    "script": 4,
    "stage_2_script": stage2.IMPLEMENTATION["script"],
    "masks": masks.MASK_VERSION,
}
"""Bumped when a worker's behaviour changes. Saved results from another version are not reused."""
GIB = 1024**3
MEMORY_DEFAULTS = {
    "budget_bytes": 4 * GIB,
    "reserve_bytes": int(1.5 * GIB),
    "pressure_bytes": 128 * 1024**2,
    "poll_seconds": 0.25,
    "wait_seconds": 60.0,
}
"""A worker is stopped above the budget. The reserve is a start check.

A worker waits to start until that much host memory is available. Nothing is held for it
while it runs.

Page-outs during a run at or above the pressure threshold mark the run as under memory
pressure. The host pages out a few kilobytes to megabytes during most runs on this laptop,
which the threshold keeps apart from swapping.
"""
TOLERANCES = {
    **stage2.TOLERANCES,
    "patterns": (
        "Every pattern must extract identical stored integers on identical pixel sets for the "
        "same lake, band, and method. Zero tolerance. Extraction from a whole tile in memory "
        "is compared with the windowed reads through the same digests."
    ),
    "stage_2": (
        "The interior and shoreline values of a lake must equal stage 2's mask methods for the "
        "same lake, band, and acquisition, and the naive values stage 2's naive method. Zero "
        "tolerance. A lake read from another acquisition has no comparison, which is recorded. "
        "Timing sums from stage 2 are compared only for the same band set."
    ),
    "membership": (
        "A lake whose polygon buffered by the near-land distance intersects the tile extent is "
        "a candidate member. Preparation verifies its selection. A candidate whose masks hold "
        "no pixel at any resolution is recorded as such, a valid outcome of the near-land "
        "rule, apart from failed preparation and missing data."
    ),
    "completeness": (
        "Expected lake-band records come from the chosen tiles' members, the requested bands, "
        "and the plan, before any record is examined. A band the scene could not resolve "
        "stays expected. A missing member, band, or repetition makes the comparison "
        "incomplete. Runs with errors or memory pressure are kept out of every timing median "
        "and counted."
    ),
    "order": (
        "Patterns and methods both rotate their order between repetitions. The plan records "
        "the order of every run. Rotation reduces an ordering bias. It does not remove "
        "network variation. No timing tolerance."
    ),
}
GRID_CODE = re.compile(r"^(?:MGRS-)?(\d{1,2})([C-HJ-NP-X])([A-HJ-NP-Z]{2})$")
GDAL_OPEN = re.compile(r"GDALOpen\(([^,]+),")
EMPTY = "no pixel of this lake in the tile"
READ_TIMERS = ("open_seconds", "read_seconds", "build_seconds", "compute_seconds")


# ---------------------------------------------------------------- pure helpers


def normalise_grid_code(code: str | None) -> str | None:
    """Tile id from a catalog grid code, with a two-digit zone. Codes vary, finding 18."""
    found = GRID_CODE.match(code or "")
    if not found:
        return None
    zone, band, square = found.groups()
    return f"{int(zone):02d}{band}{square}"


def lake_membership(lake: dict, item: dict) -> dict:
    """The lake's share inside the item's tile and footprint, and whether it is a candidate.

    A lake is a candidate member of a tile when its polygon buffered by the near-land distance
    intersects the tile extent. Preparation then verifies that a pixel of some class exists.
    The support is that buffered polygon cut to the tile, the area extraction can draw on.
    Its share inside the item's data footprint scores the item.
    """
    grid = masks.TileGrid.from_item(item)
    polygon, buffered = _projected(lake, grid.epsg)
    extent = grid.extent()
    footprint = masks.project(item["geometry"], grid.epsg)
    support = buffered.intersection(extent)
    return {
        "water_body_id": lake["properties"]["water_body_id"],
        "in_tile": round(masks.fraction_inside(polygon, extent), 6),
        "in_footprint": round(masks.fraction_inside(polygon, footprint), 6),
        "support_in_footprint": round(masks.fraction_inside(support, footprint), 6),
        "member": bool(not support.is_empty and support.area > 0),
    }


_GEOMETRY_CACHE: dict[tuple[str, str, int], tuple] = {}


def _projected(lake: dict, epsg: int) -> tuple:
    """The lake's polygon and its near-land buffer in one zone, computed once per run.

    Item scoring calls this for every candidate item, and buffering a large shoreline is slow.
    """
    key = (lake["properties"]["water_body_id"], stage2.polygon_digest(lake), epsg)
    if key not in _GEOMETRY_CACHE:
        polygon = masks.project(lake["geometry"], epsg)
        _GEOMETRY_CACHE[key] = (polygon, polygon.buffer(masks.NEAR_LAND_M))
    return _GEOMETRY_CACHE[key]


def _placing_score(tile: str, unplaced: set[str], places: dict, placements: dict) -> tuple:
    placed = [lake_id for lake_id in unplaced if tile in places[lake_id]]
    return len(placed), sum(placements[tile][lake_id]["in_tile"] for lake_id in placed)


def choose_tiles(items: list[dict], lakes: list[dict]) -> dict:
    """The tiles of a region that place every lake, and each tile's candidate members.

    A tile places a lake when it holds the lake entirely. A lake no tile holds entirely is
    placed by the tile with its largest share, ties broken by the smaller tile id. Tiles are
    chosen greedily: the tile placing the most unplaced lakes first, ties broken by the summed
    share of those lakes inside it, then by the smaller tile id. Every lake whose buffered
    polygon intersects a chosen tile is a candidate member of that tile.

    Each chosen tile records the score that chose it: the unplaced lakes it placed in its
    round and their summed share. The candidate table's `summed_share_in_tile` sums every
    lake's share inside the tile. It describes the tile and is not that score.
    """
    by_tile: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        code = normalise_grid_code(item.get("properties", {}).get("grid:code"))
        if code:
            by_tile[code].append(item)
    lake_ids = [lake["properties"]["water_body_id"] for lake in lakes]
    if not by_tile:
        return {"tiles": [], "candidates": [], "unplaced": lake_ids}
    placements = {
        tile: {
            placement["water_body_id"]: placement
            for placement in (lake_membership(lake, tile_items[0]) for lake in lakes)
        }
        for tile, tile_items in sorted(by_tile.items())
    }
    places: dict[str, set[str]] = {}
    for lake_id in lake_ids:
        entire = {t for t in placements if placements[t][lake_id]["in_tile"] >= stage2.FULLY}
        if entire:
            places[lake_id] = entire
            continue
        best = max(sorted(placements), key=lambda t: placements[t][lake_id]["in_tile"])
        places[lake_id] = {best} if placements[best][lake_id]["in_tile"] > 0 else set()
    candidates = [
        {
            "tile": tile,
            "items": len(by_tile[tile]),
            "places": sum(1 for lake_id in lake_ids if tile in places[lake_id]),
            "members": sum(1 for lake_id in lake_ids if placements[tile][lake_id]["member"]),
            "summed_share_in_tile": round(sum(p["in_tile"] for p in placements[tile].values()), 6),
        }
        for tile in sorted(placements)
    ]
    unplaced = {lake_id for lake_id in lake_ids if places[lake_id]}
    chosen: list[str] = []
    scores: dict[str, dict] = {}
    while unplaced:
        score = functools.partial(
            _placing_score, unplaced=set(unplaced), places=places, placements=placements
        )
        tile = max(sorted(placements), key=score)
        placed_now, share = score(tile)
        scores[tile] = {"places_unplaced": placed_now, "share_of_those": round(share, 6)}
        chosen.append(tile)
        unplaced -= {lake_id for lake_id in unplaced if tile in places[lake_id]}
    tiles = [
        {
            "tile": tile,
            "score": scores[tile],
            "items": by_tile[tile],
            "placed": [lake_id for lake_id in lake_ids if tile in places[lake_id]],
            "members": [
                placements[tile][lake_id]
                for lake_id in lake_ids
                if placements[tile][lake_id]["member"]
            ],
        }
        for tile in chosen
    ]
    return {
        "tiles": tiles,
        "candidates": candidates,
        "unplaced": [lake_id for lake_id in lake_ids if not places[lake_id]],
    }


def merge_tile_choices(per_region: dict[str, dict]) -> dict[str, dict]:
    """One entry per tile across regions, members and items merged, before an item is chosen."""
    merged: dict[str, dict] = {}
    for region, chosen in per_region.items():
        for tile in chosen["tiles"]:
            entry = merged.setdefault(
                tile["tile"],
                {"tile": tile["tile"], "regions": [], "items": [], "placed": [], "members": []},
            )
            entry["regions"].append(region)
            known_items = {item.get("id") for item in entry["items"]}
            entry["items"].extend(i for i in tile["items"] if i.get("id") not in known_items)
            entry["placed"].extend(x for x in tile["placed"] if x not in entry["placed"])
            known = {m["water_body_id"] for m in entry["members"]}
            entry["members"].extend(m for m in tile["members"] if m["water_body_id"] not in known)
    return merged


def choose_item(items: list[dict], lakes: list[dict]) -> dict:
    """One item for a tile.

    The item whose data footprint covers each member's support inside the tile, the buffered
    polygon cut to the tile, for the most members, wins. Ties are broken by the lowest cloud
    cover, then by the latest creation time.
    """
    scored = []
    for item in items:
        placements = [lake_membership(lake, item) for lake in lakes]
        covered = sum(1 for p in placements if p["support_in_footprint"] >= stage2.FULLY)
        props = item.get("properties", {})
        cloud = props.get("eo:cloud_cover")
        scored.append(
            (covered, -(cloud if cloud is not None else 101), props.get("created") or "", item)
        )
    scored.sort(key=lambda s: (s[0], s[1], s[2]), reverse=True)
    covered, _, _, item = scored[0]
    placements = [lake_membership(lake, item) for lake in lakes]
    return {
        "item": item,
        "lakes": placements,
        "covered": covered,
        "note": (
            f"item {item.get('id')} covers the support of {covered} of {len(lakes)} members "
            f"with its footprint, cloud cover {item.get('properties', {}).get('eo:cloud_cover')}."
        ),
    }


def rotated(items: list, shift: int) -> list:
    """The list shifted left by the given number of positions."""
    if not items:
        return []
    shift %= len(items)
    return items[shift:] + items[:shift]


def plan_order(patterns: list[str], methods: list[str], repetition: int) -> list[tuple]:
    """The pattern and method combinations of one repetition, both lists rotated.

    Repetition r shifts the patterns by r minus one positions and the methods by the same,
    so a pattern group and the methods within it both change position between repetitions.
    """
    shift = repetition - 1
    return [(p, m) for p in rotated(patterns, shift) for m in rotated(methods, shift)]


def plan_runs(tiles: list[dict], patterns: list[str], methods: list[str], repeat: int) -> list:
    runs = []
    for tile in tiles:
        for repetition in range(1, repeat + 1):
            for pattern, method in plan_order(patterns, methods, repetition):
                runs.append(
                    {
                        "tile": tile["tile"],
                        "region": tile["region"],
                        "pattern": pattern,
                        "method": method,
                        "repetition": repetition,
                        "lakes": len(tile["members"]),
                    }
                )
    return runs


def block_cells(window: dict, block_shape: list[int] | None) -> set[tuple[int, int]]:
    """The internal blocks a window intersects, as row and column indices in the block grid."""
    if not block_shape or window["height"] <= 0 or window["width"] <= 0:
        return set()
    r0 = window["row_off"] // block_shape[0]
    r1 = (window["row_off"] + window["height"] - 1) // block_shape[0]
    c0 = window["col_off"] // block_shape[1]
    c1 = (window["col_off"] + window["width"] - 1) // block_shape[1]
    return {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}


def chunks_for(window: dict, chunk: int, shared: bool) -> int:
    """Chunks of a lazy graph a window touches.

    A shared graph starts at the tile origin, so chunk boundaries sit at tile coordinates. A
    per-lake graph starts at the window, so its chunks are counted from the window's corner.
    """
    if window["height"] <= 0 or window["width"] <= 0:
        return 0
    if shared:
        return len(block_cells(window, [chunk, chunk]))
    return -(-window["height"] // chunk) * -(-window["width"] // chunk)


def read_seconds(run: dict) -> float:
    """Sum of the open, read, build, and compute timers over files and lakes. No extraction."""
    total = sum(b.get(k, 0.0) for b in run["bands"] for k in READ_TIMERS)
    total += sum(b.get(k, 0.0) for lake in run["lakes"] for b in lake["bands"] for k in READ_TIMERS)
    return round(total, 3)


def extract_seconds(run: dict) -> float:
    """Sum of the per-lake timers that pick pixels out of an array already in memory."""
    return round(
        sum(b.get("extract_seconds", 0.0) for lake in run["lakes"] for b in lake["bands"]), 3
    )


def setup_seconds(run: dict) -> float:
    """The run's own setup plus every lake's setup: projection, mask or list loading."""
    return round(
        run["setup"]["seconds"] + sum(lake["setup"]["seconds"] for lake in run["lakes"]), 3
    )


def run_status(run: dict) -> str:
    """stopped_for_memory, failed, lake_errors, or ok."""
    if run.get("memory_stop"):
        return "stopped_for_memory"
    if "error" in run:
        return "failed"
    if run["totals"]["band_errors"] or run["totals"]["lake_band_errors"]:
        return "lake_errors"
    return "ok"


def under_pressure(run: dict) -> bool:
    """Whether the host paged out memory while the run was working."""
    return bool(run.get("host_memory", {}).get("pressure"))


# ---------------------------------------------------------------- baseline, stage 2


def load_baseline(path: Path | None) -> dict | None:
    """Stage 2's per-lake medians and value digests, keyed by method family for comparison.

    The mask family holds raster-mask, index-lists, and lazy-stack. The naive family holds
    naive-clip. The two select different wet pixels on some lakes, so they never mix.
    """
    if path is None or not path.exists():
        return None
    result = json.loads(path.read_text())
    items = {region: (s.get("item") or {}).get("id") for region, s in result["scenes"].items()}
    rows = {(r["water_body_id"], r["method"]): r for r in result["summary"]["by_lake_method"]}
    digests: dict[tuple, set] = defaultdict(set)
    for run in result["runs"]:
        if "error" in run:
            continue
        family = "naive" if run["method"] == "naive-clip" else "mask"
        for band in run.get("bands", []):
            if "digest_wet" in band:
                digests[(run["water_body_id"], run["item_id"], band["key"], family)].add(
                    band["digest_wet"]
                )
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "measured_at": result["measured_at"],
        "stage": result.get("stage"),
        "bands": list(result.get("bands", [])),
        "items": items,
        "rows": rows,
        "digests": digests,
    }


def baseline_for(
    baseline: dict | None,
    item_id: str,
    lake_ids: list[str],
    method: str,
    lakes_by_id: dict,
    bands: list[str] | None = None,
) -> dict | None:
    """Sum of stage 2's per-lake medians for the lakes of a tile read from the same item.

    The sums are comparable only when the band set is stage 2's. Otherwise the row says so
    and carries no sum. Lakes without a baseline are named either way.
    """
    if baseline is None:
        return None
    with_baseline, without = [], []
    for lake_id in lake_ids:
        region = lakes_by_id[lake_id]["properties"]["region"]
        row = baseline["rows"].get((lake_id, method))
        if baseline["items"].get(region) != item_id or not row or "requests_median" not in row:
            without.append(lake_id)
        else:
            with_baseline.append(lake_id)
    record = {"lakes_with_baseline": with_baseline, "lakes_without_baseline": without}
    if bands is not None and sorted(bands) != sorted(baseline["bands"]):
        return {**record, "comparable": False, "reason": "band set differs from stage 2"}
    sums = {"requests": 0, "bytes_requested": 0, "read_seconds": 0.0, "wall_seconds": 0.0}
    for lake_id in with_baseline:
        row = baseline["rows"][(lake_id, method)]
        sums["requests"] += row["requests_median"]
        sums["bytes_requested"] += row["bytes_requested_median"]
        sums["read_seconds"] += row["read_seconds_median"]
        sums["wall_seconds"] += row["wall_seconds_median"]
    sums["read_seconds"] = round(sums["read_seconds"], 3)
    sums["wall_seconds"] = round(sums["wall_seconds"], 3)
    return {**record, "comparable": True, **sums}


# ---------------------------------------------------------------- summary


def _median(rows: list[dict], key: str, digits: int = 3):
    return round(statistics.median(r[key] for r in rows), digits)


def _combo_rows(groups, tiles_by_id, lakes_by_id, baseline, bands):
    """Per tile, pattern, and method: counts, and medians of the clean runs.

    A clean run has no error and no memory pressure. A combination without one keeps its
    counts and gets no median.
    """
    rows = []
    for (tile, pattern, method), runs in sorted(groups.items()):
        measured = [r for r in runs if "error" not in r]
        with_errors = [r for r in measured if run_status(r) == "lake_errors"]
        pressured = [r for r in measured if under_pressure(r)]
        timing_runs = [r for r in measured if r not in with_errors and r not in pressured]
        scene = tiles_by_id.get(tile, {})
        row = {
            "tile": tile,
            "region": runs[0]["region"],
            "pattern": pattern,
            "method": method,
            "lakes": len(scene.get("lakes", [])),
            "runs": len(runs),
            "failed": sum(1 for r in runs if run_status(r) == "failed"),
            "stopped_for_memory": sum(1 for r in runs if run_status(r) == "stopped_for_memory"),
            "runs_with_errors": len(with_errors),
            "runs_with_memory_pressure": len(pressured),
            "lake_band_errors": sum(r["totals"]["lake_band_errors"] for r in measured),
            "band_errors": sum(r["totals"]["band_errors"] for r in measured),
            "timings_from_runs": len(timing_runs),
        }
        if timing_runs:
            first = timing_runs[0]["totals"]
            row.update(
                {
                    "wall_seconds_median": _median(timing_runs, "wall_seconds"),
                    "read_seconds_median": round(
                        statistics.median(read_seconds(r) for r in timing_runs), 3
                    ),
                    "extract_seconds_median": round(
                        statistics.median(extract_seconds(r) for r in timing_runs), 3
                    ),
                    "setup_seconds_median": round(
                        statistics.median(setup_seconds(r) for r in timing_runs), 3
                    ),
                    "cpu_seconds_median": round(
                        statistics.median(
                            r["cpu"]["user"] + r["cpu"]["system"] for r in timing_runs
                        ),
                        3,
                    ),
                    "requests_median": int(
                        statistics.median(r["totals"]["requests"] for r in timing_runs)
                    ),
                    "bytes_requested_median": int(
                        statistics.median(r["totals"]["bytes_requested"] for r in timing_runs)
                    ),
                    "peak_rss_bytes_max": max(r["peak_rss_bytes"] for r in timing_runs),
                    "lakes_with_pixels": max(r["totals"]["lakes_with_pixels"] for r in measured),
                    "pixels_in_windows": first["pixels_in_windows"],
                    "pixels_extracted": first["pixels_extracted"],
                    "output_bytes": first["output_bytes"],
                    "opens_observed": first.get("opens_observed"),
                    "blocks_touched_sum": first.get("blocks_touched_sum"),
                    "blocks_touched_distinct": first.get("blocks_touched_distinct"),
                    "blocks_in_files": first.get("blocks_in_files"),
                }
            )
        if scene:
            row["baseline_stage_2"] = baseline_for(
                baseline,
                scene["item"]["id"],
                [lake["water_body_id"] for lake in scene["lakes"]],
                method,
                lakes_by_id,
                bands,
            )
        rows.append(row)
    return rows


def _lake_rows(runs: list[dict]) -> list[dict]:
    """Per tile, lake, pattern, and method: medians of the lake's own I/O and timers.

    Medians come from lake records without an error, in runs without memory pressure.
    Errors and pressured runs are counted over every run.
    """
    groups: dict[tuple, list[tuple[dict, bool]]] = defaultdict(list)
    for run in runs:
        if "error" in run:
            continue
        for lake in run["lakes"]:
            key = (run["tile"], lake["water_body_id"], run["pattern"], run["method"])
            groups[key].append((lake, under_pressure(run)))
    rows = []
    for (tile, lake_id, pattern, method), records in sorted(groups.items()):
        lakes = [lake for lake, _ in records]
        clean = [
            lake
            for lake, pressured in records
            if not pressured and not any("error" in b for b in lake["bands"])
        ]
        row = {
            "tile": tile,
            "water_body_id": lake_id,
            "size_label": lakes[0]["size_label"],
            "pattern": pattern,
            "method": method,
            "runs": len(lakes),
            "runs_clean": len(clean),
            "runs_under_memory_pressure": sum(1 for _, pressured in records if pressured),
            "band_errors": sum(1 for lake in lakes for b in lake["bands"] if "error" in b),
        }
        if clean:
            bands = [lake["bands"] for lake in clean]
            row.update(
                {
                    "requests_median": int(
                        statistics.median(sum(b.get("requests", 0) for b in bs) for bs in bands)
                    ),
                    "bytes_requested_median": int(
                        statistics.median(
                            sum(b.get("bytes_requested", 0) for b in bs) for bs in bands
                        )
                    ),
                    "read_seconds_median": round(
                        statistics.median(
                            sum(b.get(k, 0.0) for b in bs for k in READ_TIMERS) for bs in bands
                        ),
                        3,
                    ),
                    "extract_seconds_median": round(
                        statistics.median(
                            sum(b.get("extract_seconds", 0.0) for b in bs) for bs in bands
                        ),
                        3,
                    ),
                    "setup_seconds_median": round(
                        statistics.median(lake["setup"]["seconds"] for lake in clean), 3
                    ),
                    "pixels_extracted": sum(b.get("pixels_extracted", 0) for b in bands[0]),
                    "blocks_touched": (
                        sum(b["blocks_touched"] for b in bands[0] if "blocks_touched" in b)
                        if all(b.get("blocks_touched") is not None for b in bands[0])
                        else None
                    ),
                }
            )
        rows.append(row)
    return rows


def expected_lake_bands(tiles_by_id: dict, bands: list[str] | None = None) -> list[tuple]:
    """Every tile, member, band, and resolution the run called for.

    A requested band the scene could not resolve is expected too, with no resolution, so a
    failed asset never shrinks the expectation. The scene's resolved assets give the rest.
    """
    expected = []
    for tile, scene in sorted(tiles_by_id.items()):
        resolved = scene.get("assets", {}).get("assets", [])
        keys = [(a["key"], a["resolution"]) for a in resolved]
        resolved_keys = {a["key"] for a in resolved}
        keys += [(key, None) for key in bands or [] if key not in resolved_keys]
        for member in scene.get("lakes", []):
            for key, resolution in keys:
                expected.append((tile, member["water_body_id"], key, resolution))
    return expected


def _lake_band_order(key: tuple) -> tuple:
    return (*key[:3], key[3] if key[3] is not None else 0)


def _equality(runs, preparation, plan, tiles_by_id, baseline, bands=None) -> list[dict]:
    digests: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    present: dict[tuple, set] = defaultdict(set)
    for run in runs:
        if "error" in run:
            continue
        for lake in run["lakes"]:
            for band in lake["bands"]:
                if band.get("key", "").startswith("stack-") or "digest_all" not in band:
                    continue
                key = (run["tile"], lake["water_body_id"], band["key"], band["resolution"])
                present[key].add((run["pattern"], run["method"], run["repetition"]))
                slot = digests[key]
                if run["method"] == "naive-clip":
                    slot["naive_all"].add(band["digest_all"])
                    slot["naive_pixels"].add(band.get("digest_pixels"))
                else:
                    slot["classes_all"].add(band["digest_all"])
                    slot["classes_wet"].add(band["digest_wet"])
                    slot["classes_pixels"].add(band.get("digest_pixels"))
                    slot["classes_pixels_wet"].add(band.get("digest_pixels_wet"))
    planned = {
        (p, m, r)
        for p in plan["patterns"]
        for m in plan["methods"]
        for r in range(1, plan["repeat"] + 1)
    }
    resolved = {
        tile: {a["key"] for a in scene.get("assets", {}).get("assets", [])}
        for tile, scene in tiles_by_id.items()
    }
    keys = sorted(set(expected_lake_bands(tiles_by_id, bands)) | set(digests), key=_lake_band_order)
    rows = []
    for tile, lake_id, key, resolution in keys:
        slot = digests.get((tile, lake_id, key, resolution), defaultdict(set))
        counts = (
            preparation.get(f"{tile}/{lake_id}", {})
            .get("resolutions", {})
            .get(str(resolution), {})
            .get("counts", {})
        )
        item_id = tiles_by_id.get(tile, {}).get("item", {}).get("id")
        stage_2_mask = (
            baseline["digests"].get((lake_id, item_id, key, "mask")) if baseline else None
        )
        stage_2_naive = (
            baseline["digests"].get((lake_id, item_id, key, "naive")) if baseline else None
        )
        missing = planned - present[(tile, lake_id, key, resolution)]
        known_pixels = slot["classes_pixels"] - {None}
        known_naive_pixels = slot["naive_pixels"] - {None}
        rows.append(
            {
                "tile": tile,
                "water_body_id": lake_id,
                "band": key,
                "resolution": resolution,
                "asset_resolved": key in resolved.get(tile, set()),
                "records": len(present[(tile, lake_id, key, resolution)]),
                "complete": not missing,
                "missing": sorted(f"{p}/{m}:{r}" for p, m, r in missing),
                "mask_methods_identical": (
                    len(slot["classes_all"]) == 1 if slot["classes_all"] else None
                ),
                "mask_pixel_sets_identical": (
                    len(known_pixels) == 1
                    if known_pixels and None not in slot["classes_pixels"]
                    else None
                ),
                "naive_identical_across_patterns": (
                    len(slot["naive_all"]) == 1 if slot["naive_all"] else None
                ),
                "naive_pixel_sets_identical_across_patterns": (
                    len(known_naive_pixels) == 1
                    if known_naive_pixels and None not in slot["naive_pixels"]
                    else None
                ),
                "naive_matches_interior_and_shoreline": (
                    slot["naive_all"] == slot["classes_wet"]
                    if slot["naive_all"] and slot["classes_wet"]
                    else None
                ),
                "naive_pixel_set_matches": (
                    slot["naive_pixels"] == slot["classes_pixels_wet"]
                    if known_naive_pixels and slot["classes_pixels_wet"] - {None}
                    else None
                ),
                "naive_set_differs_in_preparation": bool(
                    counts.get("naive_only") or counts.get("classes_only")
                ),
                "matches_stage_2": (
                    slot["classes_wet"] == stage_2_mask
                    if stage_2_mask and slot["classes_wet"]
                    else None
                ),
                "naive_matches_stage_2": (
                    slot["naive_all"] == stage_2_naive
                    if stage_2_naive and slot["naive_all"]
                    else None
                ),
                "stage_2_mask_reference_consistent": (
                    len(stage_2_mask) == 1 if stage_2_mask else None
                ),
            }
        )
    return rows


def summarize(
    runs: list[dict],
    preparation: dict[str, dict],
    tiles: dict[str, dict],
    lakes: list[dict],
    plan: dict | None = None,
    baseline: dict | None = None,
    selection: dict | None = None,
    bands: list[str] | None = None,
) -> dict:
    """Medians per tile, pattern, and method, per-lake medians, and the equality checks.

    Expected coverage comes from the chosen tiles' members, the requested bands, and the
    plan. A requested band a scene could not resolve stays expected and is counted apart. A
    comparison is complete only when every planned pattern, method, and repetition
    contributed a record. Stage 2's sums for the same acquisition sit beside each row.
    """
    plan = plan or {
        "patterns": PATTERNS,
        "methods": METHODS,
        "repeat": max((r["repetition"] for r in runs), default=1),
    }
    if bands is None:
        bands = sorted(
            {a["key"] for s in tiles.values() for a in s.get("assets", {}).get("assets", [])}
        )
    lakes_by_id = {lake["properties"]["water_body_id"]: lake for lake in lakes}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for run in runs:
        groups[(run["tile"], run["pattern"], run["method"])].append(run)
    equality = _equality(runs, preparation, plan, tiles, baseline, bands)
    statuses = [run_status(r) for r in runs]
    tile_rows = []
    for tile, scene in sorted(tiles.items()):
        measured = [r for r in runs if r.get("tile") == tile and "error" not in r]
        members = scene.get("lakes", [])
        prepared = {
            m["water_body_id"]: preparation.get(f"{tile}/{m['water_body_id']}") for m in members
        }
        without_a_pixel = [
            lake_id
            for lake_id, prep in prepared.items()
            if prep
            and "error" not in prep
            and not any(
                sum(v["counts"][c] for c in masks.CLASS_CODES) for v in prep["resolutions"].values()
            )
        ]
        tile_rows.append(
            {
                "tile": tile,
                "region": scene.get("region"),
                "item_id": scene.get("item", {}).get("id"),
                "lakes": len(members),
                "lakes_entirely_inside": sum(1 for m in members if m["in_tile"] >= stage2.FULLY),
                "lakes_partly_inside": sum(1 for m in members if 0 < m["in_tile"] < stage2.FULLY),
                "lakes_near_land_only": sum(1 for m in members if m["in_tile"] == 0),
                "lakes_with_pixels": (
                    max(r["totals"]["lakes_with_pixels"] for r in measured) if measured else None
                ),
                "members_without_a_pixel": without_a_pixel,
                "members_failed_preparation": [
                    lake_id for lake_id, prep in prepared.items() if prep and "error" in prep
                ],
                "members_not_prepared": [lake_id for lake_id, prep in prepared.items() if not prep],
                "assets_missing": list(scene.get("assets", {}).get("missing", [])),
                "assets_skipped": [s["key"] for s in scene.get("assets", {}).get("skipped", [])],
                "placed": scene.get("placed"),
            }
        )
    unplaced = sorted(
        {lake_id for entry in (selection or {}).values() for lake_id in entry.get("unplaced", [])}
    )
    expected = expected_lake_bands(tiles, bands)
    return {
        "lakes": len(lakes),
        "unplaced_lakes": unplaced,
        "distinct_tiles": len(tiles),
        "distinct_tile_dates": len({(t, s.get("item", {}).get("id")) for t, s in tiles.items()}),
        "runs": {
            "planned": len(runs),
            "ok": statuses.count("ok"),
            "with_lake_errors": statuses.count("lake_errors"),
            "failed": statuses.count("failed"),
            "stopped_for_memory": statuses.count("stopped_for_memory"),
            "with_memory_pressure": sum(1 for r in runs if under_pressure(r)),
        },
        "expected_lake_bands": len(expected),
        "lake_bands_without_records": sum(1 for e in equality if e["records"] == 0),
        "lake_bands_without_asset": sum(1 for e in equality if not e["asset_resolved"]),
        "tiles": tile_rows,
        "by_tile_pattern_method": _combo_rows(groups, tiles, lakes_by_id, baseline, bands),
        "by_tile_lake_pattern_method": _lake_rows(runs),
        "equality": equality,
        "equality_incomplete": sum(1 for e in equality if not e["complete"]),
        "equality_stage_2_compared": sum(
            1
            for e in equality
            if e["matches_stage_2"] is not None or e["naive_matches_stage_2"] is not None
        ),
    }


# ---------------------------------------------------------------- workers


def prepare_worker(spec: dict) -> dict:
    """Stage 2's preparation for one lake on one tile, tagged with the tile."""
    return {**stage2.prepare_worker(spec), "tile": spec["tile"]}


@dataclasses.dataclass
class Selection:
    """One lake's pixels at one resolution: the read window and how the method picks them.

    Rows and columns are tile coordinates in the order the picker returns values.
    """

    window: masks.Window
    rows: np.ndarray
    cols: np.ndarray
    classes: np.ndarray | None
    naive: bool
    picker: Callable[[np.ndarray], np.ndarray]


def _pick_selected(selected: np.ndarray, array: np.ndarray) -> np.ndarray:
    return array[selected]


def _pick_indexed(rows: np.ndarray, cols: np.ndarray, array: np.ndarray) -> np.ndarray:
    return array[rows, cols]


def selections_for(
    lake: dict, method: str, grid: masks.TileGrid, resolutions: list[int]
) -> tuple[dict, dict[int, Selection]]:
    """The method's per-lake setup, timed: projection and clipping, or loading saved files."""
    out: dict[int, Selection] = {}
    with harness.Timer() as timer:
        if method == "naive-clip":
            polygon = masks.project(lake["geometry"], grid.epsg)
            for resolution in resolutions:
                window, selected = masks.naive_mask(polygon, grid, resolution)
                rows, cols = np.nonzero(selected)
                out[resolution] = Selection(
                    window,
                    rows + window.row_off,
                    cols + window.col_off,
                    None,
                    True,
                    functools.partial(_pick_selected, selected),
                )
            kind = "project polygon and clip"
        elif method == "index-lists":
            for resolution in resolutions:
                lists, _ = masks.load_index_lists(Path(lake["index_paths"][str(resolution)]))
                window = masks.lists_window(lists)
                out[resolution] = Selection(
                    window,
                    lists["rows"],
                    lists["cols"],
                    lists["pixel_class"],
                    False,
                    functools.partial(
                        _pick_indexed,
                        lists["rows"] - window.row_off,
                        lists["cols"] - window.col_off,
                    ),
                )
            kind = "load index lists"
        else:
            for resolution in resolutions:
                mask = masks.load_mask(Path(lake["mask_paths"][str(resolution)]))
                selected = mask.selected()
                rows, cols = np.nonzero(selected)
                out[resolution] = Selection(
                    mask.window,
                    rows + mask.window.row_off,
                    cols + mask.window.col_off,
                    mask.pixel_class[selected],
                    False,
                    functools.partial(_pick_selected, selected),
                )
            kind = "load masks"
    return {"kind": kind, "seconds": timer.seconds}, out


def observed_opens(lines: list[str], href: str | None = None) -> int:
    """Raster file opens in GDAL's log, of one file when its href is given.

    In-memory datasets, which the naive clip's rasterization opens, are never counted.
    """
    count = 0
    for line in lines:
        found = GDAL_OPEN.search(line)
        if not found or found.group(1).startswith("MEM:"):
            continue
        if href is None or found.group(1).endswith(href.split("://", 1)[-1]):
            count += 1
    return count


def io_totals(capture: harness.GdalLogCapture, log_path: str | None, href: str | None = None):
    """Requests, bytes, and observed raster opens since the last call, appended to the log.

    Opens are counted from GDAL's own open messages, so they include every open the reader
    made, in any thread, not the logical operation the script asked for.
    """
    lines = capture.take()
    if log_path and lines:
        with open(log_path, "a") as log:
            log.write("\n".join(lines) + "\n")
    gdal = harness.parse_gdal_log(lines)
    return {
        "requests": gdal["requests"] + gdal["size_requests"],
        "bytes_requested": gdal["bytes"],
        "size_requests": gdal["size_requests"],
        "opens_observed": observed_opens(lines, href),
    }


def _lake_record(lake: dict, setup: dict) -> dict:
    return {
        "water_body_id": lake["water_body_id"],
        "size_label": lake["size_label"],
        "setup": setup,
        "bands": [],
    }


def _band_record(asset: dict, whole: bool, lazy: dict | None = None) -> dict:
    record = {
        "key": asset["key"],
        "href": asset["href"],
        "resolution": asset["resolution"],
        "file_size": asset.get("file_size"),
        "whole": whole,
        "requests": 0,
        "bytes_requested": 0,
        "size_requests": 0,
        "opens_observed": 0,
    }
    if lazy:
        record.update({"opens": None, "loads": 0, "computes": 0, **lazy})
    else:
        record.update({"opens": 0, "open_seconds": 0.0})
    return record


def _lake_band(asset: dict, selection: Selection, nodata, block_shape, values, extra: dict) -> dict:
    window = selection.window.as_dict()
    record = {
        "key": asset["key"],
        "resolution": asset["resolution"],
        "window": window,
        "pixels_in_window": window["height"] * window["width"],
        "blocks_touched": (
            0 if selection.window.empty else stage2.blocks_in_window(window, block_shape)
        ),
        **extra,
    }
    record.update(
        stage2.extracted_record(
            values,
            selection.classes,
            nodata,
            selection.naive,
            rows=selection.rows,
            cols=selection.cols,
        )
    )
    return record


def _empty_band(asset: dict, selection: Selection, nodata) -> dict:
    """A member lake with no pixel of this method in the tile. Nothing is read."""
    values = np.zeros(0, dtype="int64")
    return _lake_band(asset, selection, nodata, None, values, {"note": EMPTY})


def _sub_array(array: np.ndarray, window: masks.Window) -> np.ndarray:
    return array[
        window.row_off : window.row_off + window.height,
        window.col_off : window.col_off + window.width,
    ]


def _timed_pick(selection: Selection, array: np.ndarray) -> tuple[np.ndarray, float]:
    with harness.Timer() as timer:
        values = selection.picker(array)
    return values, timer.seconds


def _close_band(band: dict, lake_bands: list[dict], grid: masks.TileGrid) -> None:
    """Fold the lake-level I/O of one file into its band record, with block or chunk counts."""
    for key in ("requests", "bytes_requested", "size_requests", "opens_observed"):
        band[key] += sum(b.get(key, 0) for b in lake_bands)
    band["lakes_with_pixels"] = sum(1 for b in lake_bands if b.get("pixels_extracted", 0) > 0)
    band["lake_errors"] = sum(1 for b in lake_bands if "error" in b)
    windows = [b["window"] for b in lake_bands if "window" in b and "error" not in b]
    if not band["whole"]:
        band["pixels_in_windows"] = sum(w["height"] * w["width"] for w in windows)
    height, width = grid.shape(band["resolution"])
    if band.get("block_shape"):
        shape = band["block_shape"]
        cells = [block_cells(w, shape) for w in windows]
        band["blocks_touched_sum"] = sum(len(c) for c in cells)
        band["blocks_touched_distinct"] = len(set().union(*cells)) if cells else 0
        band["blocks_in_file"] = -(-height // shape[0]) * -(-width // shape[1])
    elif band.get("chunk"):
        chunk = band["chunk"]
        band["chunks_touched_sum"] = sum(b.get("chunks_touched", 0) for b in lake_bands)
        if band.get("graph") == "shared":
            cells = [block_cells(w, [chunk, chunk]) for w in windows]
            band["chunks_touched_distinct"] = len(set().union(*cells)) if cells else 0
            band["chunks_in_file"] = -(-height // chunk) * -(-width // chunk)
        else:
            band["chunks_touched_distinct"] = None
            band["chunks_in_file"] = None


def run_rasterio(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list, list]:
    """The three patterns with rasterio windowed or whole reads, for the non-lazy methods."""
    import rasterio
    from rasterio.windows import Window as RioWindow

    grid = masks.TileGrid(**spec["grid"])
    pattern, method = spec["pattern"], spec["method"]
    log_path = spec.get("log_path")
    resolutions = sorted({a["resolution"] for a in spec["assets"]})
    bands = {a["key"]: _band_record(a, pattern == "whole-tile") for a in spec["assets"]}
    lakes: list[dict] = []
    selections: list[dict[int, Selection]] = []
    if pattern != "lake-by-lake":
        for lake in spec["lakes"]:
            setup, chosen = selections_for(lake, method, grid, resolutions)
            lakes.append(_lake_record(lake, setup))
            selections.append(chosen)

    if pattern == "lake-by-lake":
        for lake in spec["lakes"]:
            setup, chosen = selections_for(lake, method, grid, resolutions)
            record = _lake_record(lake, setup)
            lakes.append(record)
            for asset in spec["assets"]:
                selection = chosen[asset["resolution"]]
                band = bands[asset["key"]]
                if selection.window.empty:
                    record["bands"].append(_empty_band(asset, selection, asset.get("nodata")))
                    continue
                info, array = stage2.read_window(asset["href"], selection.window)
                io = io_totals(capture, log_path, asset["href"])
                band["opens"] += 1
                band.update({k: info[k] for k in ("dtype", "nodata", "block_shape")})
                values, picked = _timed_pick(selection, array)
                record["bands"].append(
                    _lake_band(
                        asset,
                        selection,
                        info["nodata"],
                        info["block_shape"],
                        values,
                        {
                            "open_seconds": info["open_seconds"],
                            "read_seconds": info["read_seconds"],
                            "extract_seconds": picked,
                            **io,
                        },
                    )
                )
            del chosen
            selection = None
    elif pattern == "tile-by-tile":
        for asset in spec["assets"]:
            band = bands[asset["key"]]
            with harness.Timer() as open_timer:
                dataset = rasterio.open(asset["href"])
            with dataset:
                info = {
                    "dtype": str(dataset.dtypes[0]),
                    "nodata": dataset.nodata,
                    "block_shape": list(dataset.block_shapes[0]),
                }
                band.update({**info, "opens": 1, "open_seconds": open_timer.seconds})
                band.update(io_totals(capture, log_path, asset["href"]))
                for record, chosen in zip(lakes, selections, strict=True):
                    selection = chosen[asset["resolution"]]
                    if selection.window.empty:
                        record["bands"].append(_empty_band(asset, selection, info["nodata"]))
                        continue
                    w = selection.window
                    with harness.Timer() as read_timer:
                        array = dataset.read(
                            1, window=RioWindow(w.col_off, w.row_off, w.width, w.height)
                        )
                    io = io_totals(capture, log_path, asset["href"])
                    values, picked = _timed_pick(selection, array)
                    record["bands"].append(
                        _lake_band(
                            asset,
                            selection,
                            info["nodata"],
                            info["block_shape"],
                            values,
                            {"read_seconds": read_timer.seconds, "extract_seconds": picked, **io},
                        )
                    )
    else:
        for asset in spec["assets"]:
            band = bands[asset["key"]]
            with harness.Timer() as open_timer:
                dataset = rasterio.open(asset["href"])
            with dataset:
                info = {
                    "dtype": str(dataset.dtypes[0]),
                    "nodata": dataset.nodata,
                    "block_shape": list(dataset.block_shapes[0]),
                }
                with harness.Timer() as read_timer:
                    array = dataset.read(1)
            band.update(
                {
                    **info,
                    "opens": 1,
                    "open_seconds": open_timer.seconds,
                    "read_seconds": read_timer.seconds,
                    "pixels_in_windows": int(array.size),
                    "bytes_in_window": int(array.nbytes),
                    **io_totals(capture, log_path, asset["href"]),
                }
            )
            for record, chosen in zip(lakes, selections, strict=True):
                selection = chosen[asset["resolution"]]
                if selection.window.empty:
                    record["bands"].append(_empty_band(asset, selection, info["nodata"]))
                    continue
                with harness.Timer() as pick_timer:
                    values = selection.picker(_sub_array(array, selection.window))
                record["bands"].append(
                    _lake_band(
                        asset,
                        selection,
                        info["nodata"],
                        info["block_shape"],
                        values,
                        {"extract_seconds": pick_timer.seconds},
                    )
                )
            del array
    for asset in spec["assets"]:
        _close_band(
            bands[asset["key"]],
            [b for lake in lakes for b in lake["bands"] if b["key"] == asset["key"]],
            grid,
        )
    return {"kind": "none", "seconds": 0.0}, [bands[a["key"]] for a in spec["assets"]], lakes


def _lazy_values(values: np.ndarray, nodata) -> tuple[np.ndarray, int | None]:
    """odc-stac can return floats with NaN for no-data. Restore the integer no-data value."""
    if np.issubdtype(values.dtype, np.floating):
        nan = np.isnan(values)
        return np.where(nan, nodata or 0, values), int(nan.sum())
    return values, None


def run_lazy(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list, list]:
    """The three patterns through odc-stac lazy arrays, for the lazy-stack method.

    Dask runs a fixed number of threads. Logical loads and computes are counted by the script.
    Raster opens are observed in GDAL's log, because one compute can open a file many times.
    """
    import dask

    workers = int(spec.get("dask_workers", LAZY_WORKERS))
    with dask.config.set(scheduler="threads", num_workers=workers):
        return _run_lazy(spec, capture, int(spec.get("chunk", LAZY_CHUNK)), workers)


def _run_lazy(spec: dict, capture, chunk: int, workers: int) -> tuple[dict, list, list]:
    import odc.stac
    import pystac
    from odc.geo.geobox import GeoBox

    grid = masks.TileGrid(**spec["grid"])
    pattern = spec["pattern"]
    log_path = spec.get("log_path")
    shared = pattern != "lake-by-lake"
    resolutions = sorted({a["resolution"] for a in spec["assets"]})
    by_resolution: dict[int, list[dict]] = defaultdict(list)
    for asset in spec["assets"]:
        by_resolution[asset["resolution"]].append(asset)
    with harness.Timer() as item_timer:
        item = pystac.Item.from_dict(json.loads(Path(spec["item_path"]).read_text()))
    setup = {"kind": "load item", "seconds": item_timer.seconds}
    crs = f"EPSG:{grid.epsg}"
    lazy = {"chunk": chunk, "dask_workers": workers, "graph": "shared" if shared else "per-lake"}

    def load(geobox, keys):
        return odc.stac.load(
            [item], bands=keys, geobox=geobox, chunks={"x": chunk, "y": chunk}, groupby="id"
        )

    def stack_record(resolution: int, build: float, matches: bool, stack) -> dict:
        return {
            "key": f"stack-{resolution}m",
            "resolution": resolution,
            "build_seconds": build,
            "grid_matches": matches,
            "returned_transform": list(stack.odc.geobox.affine)[:6],
            **lazy,
            **io_totals(capture, log_path),
        }

    def finish(record, asset, selection, values, extra):
        values, nan_count = _lazy_values(values, asset.get("nodata"))
        band = _lake_band(asset, selection, asset.get("nodata"), None, values, extra)
        band["chunks_touched"] = chunks_for(selection.window.as_dict(), chunk, shared)
        if nan_count is not None:
            band["nan_extracted"] = nan_count
        record["bands"].append(band)

    bands: list[dict] = []
    band_by_key = {a["key"]: _band_record(a, pattern == "whole-tile", lazy) for a in spec["assets"]}
    lakes: list[dict] = []
    selections: list[dict[int, Selection]] = []
    if shared:
        for lake in spec["lakes"]:
            lake_setup, chosen = selections_for(lake, "lazy-stack", grid, resolutions)
            lakes.append(_lake_record(lake, lake_setup))
            selections.append(chosen)

    if not shared:
        for lake in spec["lakes"]:
            lake_setup, chosen = selections_for(lake, "lazy-stack", grid, resolutions)
            record = _lake_record(lake, lake_setup)
            lakes.append(record)
            for resolution, assets in sorted(by_resolution.items()):
                selection = chosen[resolution]
                if selection.window.empty:
                    record["bands"].extend(
                        _empty_band(a, selection, a.get("nodata")) for a in assets
                    )
                    continue
                w = selection.window
                geobox = GeoBox((w.height, w.width), w.transform(grid, resolution), crs)
                with harness.Timer() as build:
                    stack = load(geobox, [a["key"] for a in assets])
                matches = bool(stack.odc.geobox == geobox)
                record["bands"].append(stack_record(resolution, build.seconds, matches, stack))
                for asset in assets:
                    band_by_key[asset["key"]]["loads"] += 1
                    band_by_key[asset["key"]]["computes"] += 1
                    with harness.Timer() as compute:
                        array = stack[asset["key"]].isel(time=0).compute().values
                    io = io_totals(capture, log_path, asset["href"])
                    if not matches:
                        record["bands"].append(
                            {
                                "key": asset["key"],
                                "error": "returned grid differs from the window",
                                **io,
                            }
                        )
                        continue
                    values, picked = _timed_pick(selection, array)
                    finish(
                        record,
                        asset,
                        selection,
                        values,
                        {"compute_seconds": compute.seconds, "extract_seconds": picked, **io},
                    )
            del chosen
            selection = None
    else:
        for resolution, assets in sorted(by_resolution.items()):
            height, width = grid.shape(resolution)
            geobox = GeoBox((height, width), grid.transform(resolution), crs)
            with harness.Timer() as build:
                stack = load(geobox, [a["key"] for a in assets])
            matches = bool(stack.odc.geobox == geobox)
            bands.append(stack_record(resolution, build.seconds, matches, stack))
            for asset in assets:
                band = band_by_key[asset["key"]]
                band["loads"] = 1
                if pattern == "whole-tile":
                    band["computes"] = 1
                    with harness.Timer() as compute:
                        array = stack[asset["key"]].isel(time=0).compute().values
                    band.update(
                        {
                            "compute_seconds": compute.seconds,
                            "dtype": str(array.dtype),
                            "pixels_in_windows": int(array.size),
                            "bytes_in_window": int(array.nbytes),
                            **io_totals(capture, log_path, asset["href"]),
                        }
                    )
                for record, chosen in zip(lakes, selections, strict=True):
                    selection = chosen[resolution]
                    if selection.window.empty:
                        record["bands"].append(_empty_band(asset, selection, asset.get("nodata")))
                        continue
                    if not matches:
                        record["bands"].append(
                            {"key": asset["key"], "error": "returned grid differs from the tile"}
                        )
                        continue
                    w = selection.window
                    if pattern == "whole-tile":
                        with harness.Timer() as pick_timer:
                            values = selection.picker(_sub_array(array, w))
                        finish(
                            record,
                            asset,
                            selection,
                            values,
                            {"extract_seconds": pick_timer.seconds},
                        )
                        continue
                    band["computes"] += 1
                    with harness.Timer() as compute:
                        part = (
                            stack[asset["key"]]
                            .isel(
                                time=0,
                                y=slice(w.row_off, w.row_off + w.height),
                                x=slice(w.col_off, w.col_off + w.width),
                            )
                            .compute()
                            .values
                        )
                    io = io_totals(capture, log_path, asset["href"])
                    values, picked = _timed_pick(selection, part)
                    finish(
                        record,
                        asset,
                        selection,
                        values,
                        {"compute_seconds": compute.seconds, "extract_seconds": picked, **io},
                    )
                if pattern == "whole-tile":
                    del array
    for asset in spec["assets"]:
        band = band_by_key[asset["key"]]
        _close_band(
            band, [b for lake in lakes for b in lake["bands"] if b["key"] == asset["key"]], grid
        )
        bands.append(band)
    return setup, bands, lakes


def extract_worker(spec: dict) -> dict:
    """One tile, one pattern, one method, one repetition. Every member lake, every asset."""
    import rasterio
    from rasterio.env import get_gdal_config

    started = harness.utc_now()
    net_before = harness.net_counters()
    cpu_before = harness.cpu_seconds()
    if spec.get("log_path"):
        Path(spec["log_path"]).write_text("")
    with harness.Timer() as wall, rasterio.Env(**GDAL_ENV), harness.GdalLogCapture() as capture:
        cache_bytes = int(get_gdal_config("GDAL_CACHEMAX"))
        if spec["method"] == "lazy-stack":
            setup, bands, lakes = run_lazy(spec, capture)
        else:
            setup, bands, lakes = run_rasterio(spec, capture)
        io_totals(capture, spec.get("log_path"))
    files = [b for b in bands if not b["key"].startswith("stack-")]
    lake_bands = [b for lake in lakes for b in lake["bands"] if "digest_all" in b]
    lake_stacks = [b for lake in lakes for b in lake["bands"] if b["key"].startswith("stack-")]
    io_records = bands + lake_stacks
    blocks_sum = [b.get("blocks_touched_sum") for b in files]
    blocks_distinct = [b.get("blocks_touched_distinct") for b in files]
    blocks_in_files = [b.get("blocks_in_file") for b in files]
    return {
        **{k: spec[k] for k in ("tile", "region", "pattern", "method", "repetition", "item_id")},
        "started_at": started,
        "wall_seconds": wall.seconds,
        "cpu": harness.cpu_delta(cpu_before, harness.cpu_seconds()),
        "peak_rss_bytes": harness.peak_rss_bytes(),
        "net": harness.net_delta(net_before, harness.net_counters()),
        "setup": setup,
        "inputs": spec.get("inputs"),
        "bands": bands,
        "lakes": lakes,
        "totals": {
            "lakes": len(lakes),
            "lakes_with_pixels": sum(
                1 for lake in lakes if any(b.get("pixels_extracted", 0) > 0 for b in lake["bands"])
            ),
            "bands": len(files),
            "band_errors": sum(1 for b in bands if "error" in b),
            "lake_band_errors": sum(1 for lake in lakes for b in lake["bands"] if "error" in b),
            "requests": sum(b.get("requests", 0) for b in io_records),
            "bytes_requested": sum(b.get("bytes_requested", 0) for b in io_records),
            "opens_observed": sum(b.get("opens_observed", 0) for b in io_records),
            "pixels_in_windows": sum(b.get("pixels_in_windows", 0) for b in files),
            "pixels_extracted": sum(b["pixels_extracted"] for b in lake_bands),
            "output_bytes": sum(b["output_bytes"] for b in lake_bands),
            "blocks_touched_sum": sum(blocks_sum)
            if all(x is not None for x in blocks_sum)
            else None,
            "blocks_touched_distinct": (
                sum(blocks_distinct) if all(x is not None for x in blocks_distinct) else None
            ),
            "blocks_in_files": (
                sum(blocks_in_files) if all(x is not None for x in blocks_in_files) else None
            ),
        },
        "gdal_env": GDAL_ENV,
        "gdal_cache_bytes": cache_bytes,
    }


# ---------------------------------------------------------------- parent


def host_memory() -> dict:
    import psutil

    virtual = psutil.virtual_memory()
    return {"total": int(virtual.total), "available": int(virtual.available)}


def run_in_subprocess(task: str, spec: dict, spec_path: Path, memory: dict | None = None) -> dict:
    """Run one worker in a fresh process under a memory budget.

    The worker waits to start until the host has the reserve available. While it runs, its
    resident memory is sampled. Above the budget it is stopped and the run is recorded as
    incomplete, with the partial GDAL log kept. Page-outs during the run mark memory pressure.
    """
    import psutil

    memory = {**MEMORY_DEFAULTS, **(memory or {})}
    spec_path.write_text(json.dumps(spec))
    keys = ("tile", "region", "water_body_id", "pattern", "method", "repetition")
    tag = {k: spec[k] for k in keys if k in spec}
    before = host_memory()
    waited = 0.0
    while before["available"] < memory["reserve_bytes"] and waited < memory["wait_seconds"]:
        time.sleep(2.0)
        waited += 2.0
        before = host_memory()
    record = {
        "budget_bytes": memory["budget_bytes"],
        "reserve_bytes": memory["reserve_bytes"],
        "total": before["total"],
        "available_before": before["available"],
        "waited_seconds": waited,
    }
    if before["available"] < memory["reserve_bytes"]:
        return {
            **tag,
            "error": "not started: available memory stayed below the reserve",
            "memory_stop": True,
            "host_memory": record,
        }
    swap_before = psutil.swap_memory()
    process = psutil.Popen(
        [sys.executable, str(Path(__file__).resolve()), f"--{task}-worker", str(spec_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, **{k: str(v) for k, v in GDAL_ENV.items()}},
    )
    peak, samples, stopped = 0, 0, None

    def sample() -> int | None:
        try:
            return process.memory_info().rss
        except psutil.Error:
            return None

    first = sample()
    if first is not None:
        peak, samples = first, 1
    while True:
        try:
            out, err = process.communicate(timeout=memory["poll_seconds"])
            break
        except subprocess.TimeoutExpired:
            rss = sample()
            if rss is None:
                continue
            peak, samples = max(peak, rss), samples + 1
            if rss > memory["budget_bytes"]:
                process.kill()
                stopped = (
                    f"stopped: worker resident memory {rss} bytes exceeded the budget "
                    f"{memory['budget_bytes']} bytes"
                )
                out, err = process.communicate()
                break
    swap_after = psutil.swap_memory()
    record.update(
        {
            "available_after": host_memory()["available"],
            "samples": samples,
            "peak_rss_observed": peak if samples else None,
            "swap_in_delta": int(swap_after.sin - swap_before.sin),
            "swap_out_delta": int(swap_after.sout - swap_before.sout),
            "pressure_bytes": memory["pressure_bytes"],
            "pressure": bool(swap_after.sout - swap_before.sout >= memory["pressure_bytes"]),
        }
    )
    if stopped:
        return {**tag, "error": stopped, "memory_stop": True, "host_memory": record}
    if process.returncode != 0:
        return {**tag, "error": err[-3000:], "host_memory": record}
    result = json.loads(out.strip().splitlines()[-1])
    result["host_memory"] = record
    return result


def reuse_mismatch(saved: dict, spec: dict, keys: tuple[str, ...]) -> str | None:
    """Why a saved result cannot stand in for the requested run, or None when it can.

    Extraction results are bound to their inputs: every member lake's polygon digest and mask
    digests, the grid, the mask parameters, and the implementation version. A saved run with
    any band or lake error is never reused.
    """
    for key in keys:
        if saved.get(key) != spec.get(key):
            return f"{key} differs"
    if "assets" in spec:
        if any("error" in b for b in saved.get("bands", [])):
            return "saved run has a band error"
        if any("error" in b for lake in saved.get("lakes", []) for b in lake.get("bands", [])):
            return "saved run has a lake error"
        saved_assets = sorted(
            (b.get("key"), b.get("href")) for b in saved.get("bands", []) if "href" in b
        )
        if saved_assets != sorted((a["key"], a["href"]) for a in spec["assets"]):
            return "assets differ: another product, band set, or a failed band"
        if saved.get("gdal_env") != GDAL_ENV:
            return "reader configuration differs"
        if saved.get("inputs") != spec.get("inputs"):
            return "inputs differ: lakes, polygons, grid, masks, mask parameters, or implementation"
    return None


def reusable_result(reuse_dir: Path | None, name: str, spec: dict, keys: tuple[str, ...]):
    if reuse_dir is None:
        return None, None
    path = reuse_dir / f"{name}.result.json"
    if not path.exists():
        return None, None
    saved = json.loads(path.read_text())
    if "error" in saved:
        return None, "saved run failed"
    reason = reuse_mismatch(saved, spec, keys)
    if reason:
        return None, reason
    saved["reused_from"] = str(path)
    return saved, None


def print_plan(lakes: list[dict], patterns: list[str], methods: list[str], repeat: int) -> None:
    by_region: dict[str, list[dict]] = defaultdict(list)
    for lake in lakes:
        by_region[lake["properties"]["region"]].append(lake)
    per_tile = len(patterns) * len(methods) * repeat
    print(
        f"{len(lakes)} lakes in {len(by_region)} regions, {len(patterns)} patterns, "
        f"{len(methods)} methods, {repeat} repetitions: {per_tile} runs per tile. "
        "Tiles resolve from the catalog at run time, at least one per region."
    )
    for repetition in range(1, repeat + 1):
        order = ", ".join(f"{p}/{m}" for p, m in plan_order(patterns, methods, repetition))
        print(f"  repetition {repetition}: {order}")
    for region, region_lakes in by_region.items():
        labels = ", ".join(
            f"{lake['properties']['water_body_id']} ({stage2.size_label(lake)})"
            for lake in region_lakes
        )
        print(f"  {region}: {labels}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--regions", nargs="+", help="Region ids from the manifest")
    parser.add_argument("--lakes", nargs="+", help="Water body ids from the manifest")
    parser.add_argument("--tiers", nargs="+", choices=["pilot", "large"])
    parser.add_argument("--tiles", nargs="+", help="Only these tile ids among the chosen ones")
    parser.add_argument("--patterns", nargs="+", default=PATTERNS, choices=PATTERNS)
    parser.add_argument("--methods", nargs="+", default=METHODS, choices=METHODS)
    parser.add_argument(
        "--bands",
        nargs="+",
        default=["default"],
        help="Asset keys, or a set name: default, reflectance, quality, all",
    )
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument(
        "--window", nargs=2, default=list(stage2.DEFAULT_WINDOW), metavar=("START", "END")
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks" / "results" / "tile-extraction.json"
    )
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "tile-extraction")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Stage 2 result whose per-lake medians and digests are compared with. Optional",
    )
    parser.add_argument(
        "--memory-budget-gb",
        type=float,
        default=MEMORY_DEFAULTS["budget_bytes"] / GIB,
        help="A worker above this resident size is stopped and its run recorded as incomplete",
    )
    parser.add_argument(
        "--memory-reserve-gb",
        type=float,
        default=MEMORY_DEFAULTS["reserve_bytes"] / GIB,
        help="A worker waits up to a minute for this much available memory before starting",
    )
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds between catalog requests")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and contact nothing")
    parser.add_argument(
        "--reuse",
        type=Path,
        help="Raw directory of an interrupted run. Its saved masks and successful runs are kept",
    )
    parser.add_argument(
        "--resummarize",
        type=Path,
        metavar="RESULT",
        help="Recompute the summary of a saved result from its own runs. Contacts nothing",
    )
    parser.add_argument("--prepare-worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--extract-worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.resummarize:
        return resummarize(args.resummarize)
    if args.prepare_worker:
        print(json.dumps(prepare_worker(json.loads(args.prepare_worker.read_text()))))
        return 0
    if args.extract_worker:
        print(json.dumps(extract_worker(json.loads(args.extract_worker.read_text()))))
        return 0

    bands = []
    for band in args.bands:
        bands.extend(stage2.BAND_SETS.get(band, [band]))
    lakes = stage2.load_lakes(args.manifest, args.regions, args.lakes, args.tiers)
    if not lakes:
        print("no lake matches the selection")
        return 1
    if args.dry_run:
        print_plan(lakes, args.patterns, args.methods, args.repeat)
        return 0

    memory = {
        **MEMORY_DEFAULTS,
        "budget_bytes": int(args.memory_budget_gb * GIB),
        "reserve_bytes": int(args.memory_reserve_gb * GIB),
    }
    baseline = load_baseline(args.baseline)
    if baseline is None:
        print(f"no stage 2 baseline at {args.baseline}. Rows carry no comparison.", flush=True)
    measured_at = harness.utc_now()
    raw_dir = args.raw_dir / measured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = harness.Client(pause=args.pause)
    lake_by_id = {lake["properties"]["water_body_id"]: lake for lake in lakes}
    by_region: dict[str, list[dict]] = defaultdict(list)
    for lake in lakes:
        by_region[lake["properties"]["region"]].append(lake)

    selection_log: dict[str, dict] = {}
    per_region: dict[str, dict] = {}
    for region, region_lakes in by_region.items():
        items = stage2.search_region(client, stage2.lakes_bbox(region_lakes), tuple(args.window))
        chosen = choose_tiles(items, region_lakes)
        per_region[region] = chosen
        selection_log[region] = {
            "items": len(items),
            "candidates": chosen["candidates"],
            "chosen": [t["tile"] for t in chosen["tiles"]],
            "scores": {t["tile"]: t["score"] for t in chosen["tiles"]},
            "unplaced": chosen["unplaced"],
        }
        print(
            f"{region}: {len(items)} items in the window, tiles {selection_log[region]['chosen']}"
            + (f", unplaced {chosen['unplaced']}" if chosen["unplaced"] else ""),
            flush=True,
        )

    scenes: dict[str, dict] = {}
    for tile_id, tile in merge_tile_choices(per_region).items():
        if args.tiles and tile_id not in args.tiles:
            continue
        members = [lake_by_id[m["water_body_id"]] for m in tile["members"]]
        picked = choose_item(tile["items"], members)
        item_path = raw_dir / "items" / f"{tile_id}.json"
        item_path.parent.mkdir(parents=True, exist_ok=True)
        item_path.write_text(json.dumps(picked["item"], indent=1) + "\n")
        grid = masks.TileGrid.from_item(picked["item"])
        resolved = stage2.resolve_assets(picked["item"], bands, grid)
        for skip in resolved["skipped"]:
            print(f"  {tile_id}: skipping {skip['key']}, {skip['reason']}", flush=True)
        if resolved["missing"]:
            print(f"  {tile_id}: missing {resolved['missing']}", flush=True)
        scenes[tile_id] = {
            "tile": tile_id,
            "region": tile["regions"][0],
            "regions": tile["regions"],
            "item": stage2.trim_item(picked["item"]),
            "item_path": str(item_path),
            "grid": dataclasses.asdict(grid),
            "lakes": picked["lakes"],
            "placed": tile["placed"],
            "note": picked["note"],
            "assets": resolved,
        }
        print(f"  {tile_id}: {len(picked['lakes'])} members. {picked['note']}", flush=True)

    preparation: dict[str, dict] = {}
    for tile_id, scene in scenes.items():
        resolutions = sorted({a["resolution"] for a in scene["assets"]["assets"]})
        for member in scene["lakes"]:
            lake_id = member["water_body_id"]
            lake = lake_by_id[lake_id]
            spec = {
                "tile": tile_id,
                "water_body_id": lake_id,
                "geometry": lake["geometry"],
                "polygon_sha256": stage2.polygon_digest(lake),
                "grid": scene["grid"],
                "resolutions": resolutions,
                "mask_paths": {
                    str(r): str(raw_dir / "masks" / f"{tile_id}-{lake_id}-{r}m.npz")
                    for r in resolutions
                },
                "index_paths": {
                    str(r): str(raw_dir / "index" / f"{tile_id}-{lake_id}-{r}m.npz")
                    for r in resolutions
                },
                "mask_parameters": stage2.MASK_PARAMETERS,
                "implementation": IMPLEMENTATION,
            }
            name = f"prepare-{tile_id}-{lake_id}"
            keys = (
                "tile",
                "water_body_id",
                "polygon_sha256",
                "grid",
                "mask_parameters",
                "implementation",
            )
            result, reason = reusable_result(args.reuse, name, spec, keys)
            if result is not None and args.reuse:
                result, reason = copy_saved_masks(result, spec, args.reuse, raw_dir)
            if reason:
                print(f"  {name}: not reusing the saved result, {reason}", flush=True)
            if result is None:
                result = run_in_subprocess("prepare", spec, raw_dir / f"{name}.spec.json", memory)
            (raw_dir / f"{name}.result.json").write_text(json.dumps(result, indent=1) + "\n")
            preparation[f"{tile_id}/{lake_id}"] = result
            if "error" in result:
                print(f"{name}: FAILED {result['error'][-200:]}", flush=True)
                continue
            counts = " ".join(
                "{}m {}/{}/{}".format(
                    r, v["counts"]["interior"], v["counts"]["shoreline"], v["counts"]["near_land"]
                )
                for r, v in result["resolutions"].items()
            )
            print(
                f"{name}: {result['wall_seconds']:.1f} s, in tile "
                f"{result['fraction_in_tile']:.3f}, interior/shoreline/near-land {counts}",
                flush=True,
            )

    tiles_for_plan = [
        {"tile": tile_id, "region": scene["region"], "members": scene["lakes"]}
        for tile_id, scene in scenes.items()
    ]
    runs = plan_runs(tiles_for_plan, args.patterns, args.methods, args.repeat)
    results = []
    for index, run in enumerate(runs, 1):
        name = f"{index:03d}-{run['tile']}-{run['pattern']}-{run['method']}-{run['repetition']}"
        scene = scenes[run["tile"]]
        resolutions = sorted({a["resolution"] for a in scene["assets"]["assets"]})
        members = []
        for member in scene["lakes"]:
            lake_id = member["water_body_id"]
            prep = preparation[f"{run['tile']}/{lake_id}"]
            if "error" in prep:
                continue
            members.append(
                {
                    "water_body_id": lake_id,
                    "size_label": stage2.size_label(lake_by_id[lake_id]),
                    "geometry": lake_by_id[lake_id]["geometry"],
                    "mask_paths": {
                        str(r): str(raw_dir / "masks" / f"{run['tile']}-{lake_id}-{r}m.npz")
                        for r in resolutions
                    },
                    "index_paths": {
                        str(r): str(raw_dir / "index" / f"{run['tile']}-{lake_id}-{r}m.npz")
                        for r in resolutions
                    },
                }
            )
        if not members:
            results.append({**run, "error": "no prepared lake in this tile"})
            print(f"{index}/{len(runs)} {name}: SKIPPED, no prepared lake", flush=True)
            continue
        spec = {
            **{k: run[k] for k in ("tile", "region", "pattern", "method", "repetition")},
            "item_id": scene["item"]["id"],
            "item_path": scene["item_path"],
            "grid": scene["grid"],
            "assets": scene["assets"]["assets"],
            "lakes": members,
            "chunk": LAZY_CHUNK,
            "dask_workers": LAZY_WORKERS,
            "log_path": str(raw_dir / f"{name}.gdal.log"),
        }
        spec["inputs"] = {
            "grid": scene["grid"],
            "lakes": [
                {
                    "water_body_id": m["water_body_id"],
                    "polygon_sha256": preparation[f"{run['tile']}/{m['water_body_id']}"][
                        "polygon_sha256"
                    ],
                    "mask_digests": {
                        res: {"mask": v.get("mask_sha256"), "index": v.get("index_sha256")}
                        for res, v in preparation[f"{run['tile']}/{m['water_body_id']}"][
                            "resolutions"
                        ].items()
                    },
                }
                for m in members
            ],
            "mask_parameters": stage2.MASK_PARAMETERS,
            "implementation": IMPLEMENTATION,
            "lazy": {"chunk": LAZY_CHUNK, "dask_workers": LAZY_WORKERS},
        }
        result, reason = reusable_result(
            args.reuse, name, spec, ("tile", "item_id", "pattern", "method", "repetition")
        )
        if reason:
            print(f"  {name}: not reusing the saved result, {reason}", flush=True)
        if result is None:
            result = run_in_subprocess("extract", spec, raw_dir / f"{name}.spec.json", memory)
        (raw_dir / f"{name}.result.json").write_text(json.dumps(result, indent=1) + "\n")
        results.append(result)
        if "error" in result:
            print(f"{index}/{len(runs)} {name}: FAILED {result['error'][-200:]}", flush=True)
            continue
        totals = result["totals"]
        reused = " (reused)" if "reused_from" in result else ""
        pressure = " (memory pressure)" if under_pressure(result) else ""
        print(
            f"{index}/{len(runs)} {name}{reused}{pressure}: {result['wall_seconds']:.1f} s, "
            f"{totals['bytes_requested'] / 1e6:.1f} MB requested, {totals['requests']} requests, "
            f"{totals['lakes_with_pixels']}/{totals['lakes']} lakes, "
            f"{totals['pixels_extracted']} pixels, peak {result['peak_rss_bytes'] / 1e9:.2f} GB",
            flush=True,
        )

    plan = {
        "patterns": args.patterns,
        "methods": args.methods,
        "repeat": args.repeat,
        "order": {
            str(rep): [f"{p}/{m}" for p, m in plan_order(args.patterns, args.methods, rep)]
            for rep in range(1, args.repeat + 1)
        },
        "tiles": len(scenes),
        "lakes": len(lakes),
        "runs": len(runs),
    }
    output = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": harness.code_version(),
        "script": "benchmarks/tile_extraction.py",
        "stage": "3, many lakes in one tile",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2. Transfer times include "
            "that path. Assumption A25. Repeat from us-west-2 when AWS access exists."
        ),
        "endpoints": {
            "c1": {
                "label": "Collection 1 copy",
                "collection": stage2.COLLECTION,
                "bucket": stage2.BUCKET,
                "region": "us-west-2",
                "payer": (
                    "provider. Public bucket read with unsigned requests. The registry lists "
                    "RequesterPays false, finding F-22."
                ),
            }
        },
        "catalog": {
            "root": stage2.ES_ROOT,
            "collection": stage2.COLLECTION,
            "window": list(args.window),
            "tile_rule": choose_tiles.__doc__.strip(),
            "item_rule": choose_item.__doc__.strip(),
            "membership_rule": lake_membership.__doc__.strip(),
        },
        "manifest": {
            "path": (
                str(args.manifest.relative_to(ROOT))
                if args.manifest.is_relative_to(ROOT)
                else str(args.manifest)
            ),
            "sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "lakes": len(lakes),
        },
        "lakes_requested": sorted(lake_by_id),
        "patterns": PATTERN_NOTES,
        "methods": METHOD_NOTES,
        "bands": bands,
        "tolerances": TOLERANCES,
        "plan": plan,
        "selection": selection_log,
        "tiles": scenes,
        "preparation": preparation,
        "runs": results,
        "pixels_read_between": pixels_read_between(results),
        "reused_runs": sum(1 for r in results if "reused_from" in r),
        "reused_from": str(args.reuse) if args.reuse else None,
        "implementation": IMPLEMENTATION,
        "gdal_env": GDAL_ENV,
        "lazy": {"chunk": LAZY_CHUNK, "dask_workers": LAZY_WORKERS, "scheduler": "threads"},
        "memory": memory,
        "baseline": (
            {k: baseline[k] for k in ("path", "sha256", "measured_at", "stage", "bands")}
            if baseline
            else None
        ),
        "summary": summarize(
            results, preparation, scenes, lakes, plan, baseline, selection_log, bands
        ),
        "summary_generated_at": harness.utc_now(),
        "catalog_request_log": client.log,
        "raw_dir": str(raw_dir),
        "limitations": LIMITATIONS,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=1) + "\n")
    print(f"wrote {args.output}: {run_counts_label(output['summary']['runs'])}", flush=True)
    return 0


LIMITATIONS = [
    "Runs on the owner's laptop over the internet, outside us-west-2. Every transfer time "
    "includes that path. Assumption A25.",
    "Requests and bytes come from GDAL's debug log of requested ranges, what the reader asked "
    "for, not what the network delivered. Network counters are machine-wide.",
    "One Collection 1 item per tile, chosen by the rules under catalog. Timings are for that "
    "acquisition. Cloud cover changes compression and so bytes, not the pattern.",
    "Tiles are chosen to place every lake. A lake partly inside a tile is read inside it only, "
    "and its share inside is recorded. Reading its other tiles is stage 4 work.",
    "Membership by buffer intersection is a candidate test. A member whose masks hold no "
    "pixel at any resolution is recorded as such. Agreement between methods on such a lake "
    "says nothing about data availability.",
    "Every run is one fresh process for one tile, so GDAL's caches are cold at the start and "
    "warm between lakes. The block cache is set in bytes and every run records the size it "
    "held, where stage 2 used GDAL's default. Provider-side and operating-system caches are "
    "not controlled.",
    "Preparation is timed in its own process per lake and tile and excluded from the runs. "
    "Runs load the saved masks or lists from disk and time that as setup per lake.",
    "Wall seconds per run include digests and statistics. The per-file and per-lake timers "
    "exclude them. Extraction from memory is timed apart from reading.",
    "The stage 2 baseline sums per-lake medians measured in separate processes on 2026-09-15, "
    "with masks of an earlier version. Its near-land sets differ on two lakes. Only lakes read "
    "from the same acquisition with the same band set are compared.",
    "Output bytes are the size of row, column, class, and value fields per extracted pixel, "
    "not a stored file. No storage layout is selected.",
    "The lazy stack runs on a fixed number of Dask threads and reads chunks of its own size, "
    "not the file's blocks. Chunk counts are relative to each graph's origin. Its block counts "
    "are unknown. Raster opens are observed in GDAL's log for every method.",
    "Workers run one at a time under a memory budget. The reserve is a start check on "
    "available host memory, not memory held for the worker. A stopped worker leaves an "
    "incomplete run with its partial log. Host page-outs at or above the recorded threshold "
    "mark memory pressure, and such runs stay out of every timing median. A rapid "
    "allocation spike can still escape the sampler.",
]


def copy_saved_masks(result: dict, spec: dict, reuse_dir: Path, raw_dir: Path):
    """Bring a reused preparation's files into the new raw directory, checking their digests."""
    for key, digest_key in (("mask_paths", "mask_sha256"), ("index_paths", "index_sha256")):
        for res, path in spec[key].items():
            source = reuse_dir / Path(path).relative_to(raw_dir)
            expected = result["resolutions"].get(res, {}).get(digest_key)
            if not source.exists():
                return None, f"saved {key} for {res} m missing"
            if harness.sha256_bytes(source.read_bytes()) != expected:
                return None, f"saved {key} for {res} m differs from its record"
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(source.read_bytes())
    return result, None


def run_counts_label(counts: dict) -> str:
    return (
        f"{counts['planned']} runs, {counts['ok']} complete, "
        f"{counts['with_lake_errors']} with lake errors, {counts['failed']} failed, "
        f"{counts['stopped_for_memory']} stopped for memory"
    )


def pixels_read_between(results: list[dict]) -> list[str] | None:
    """Earliest start and latest end of the runs that read a pixel. End is start plus wall."""
    spans = []
    for r in results:
        if "error" in r or not r["totals"]["lakes_with_pixels"]:
            continue
        end = datetime.fromisoformat(r["started_at"]) + timedelta(seconds=r["wall_seconds"])
        spans.append((r["started_at"], end.isoformat(timespec="seconds")))
    if not spans:
        return None
    return [min(start for start, _ in spans), max(end for _, end in spans)]


def resummarize(path: Path) -> int:
    """Recompute a result file's summary from its own runs and preparation. No network.

    Everything measured stays as it is. Only `summary`, `summary_generated_at`, and
    `pixels_read_between` change, and the implementation that summarized is recorded. A
    run's `gdal_env` keeps the cache value the run held, in the unit that run used. The
    lakes are the ones the run requested. A recorded baseline must be present and unchanged.
    """
    result = json.loads(path.read_text())
    manifest = ROOT / result["manifest"]["path"]
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != result["manifest"]["sha256"]:
        print(f"{manifest} differs from the manifest the run used. Not summarized.")
        return 1
    lake_ids = result.get("lakes_requested") or sorted(
        {key.split("/", 1)[1] for key in result["preparation"]}
    )
    lakes = stage2.load_lakes(manifest, lake_ids=lake_ids)
    baseline = None
    if result.get("baseline"):
        baseline_path = ROOT / result["baseline"]["path"]
        baseline = load_baseline(baseline_path)
        if baseline is None:
            print(f"{baseline_path} is missing. The run recorded it. Not summarized.")
            return 1
        if result["baseline"]["sha256"] != baseline["sha256"]:
            print(f"{baseline_path} differs from the baseline the run used. Not summarized.")
            return 1
    result["summary"] = summarize(
        result["runs"],
        result["preparation"],
        result["tiles"],
        lakes,
        result.get("plan"),
        baseline,
        result.get("selection"),
        result.get("bands"),
    )
    result["summary_generated_at"] = harness.utc_now()
    result["summary_implementation"] = IMPLEMENTATION
    result["pixels_read_between"] = pixels_read_between(result["runs"])
    path.write_text(json.dumps(result, indent=1) + "\n")
    print(f"summarized {path}: {run_counts_label(result['summary']['runs'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
