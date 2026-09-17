"""Stage 2, one lake at a time: four extraction methods on the pilot lakes.

Runs only when the user invokes it. It contacts the Earth Search STAC API to choose one
Collection 1 acquisition per pilot region, then reads windows of that acquisition from the
public bucket, one lake at a time, with four methods. Nothing is written back to a provider.

    uv run python benchmarks/lake_extraction.py --dry-run                    # plan, no network
    uv run python benchmarks/lake_extraction.py --regions lanier --repeat 1  # one region, once
    uv run python benchmarks/lake_extraction.py                              # every lake, 3 times

Methods:

    naive-clip    Project the polygon and clip per scene. The baseline. No classes, no coverage.
    raster-mask   Precomputed class, coverage, and edge-distance arrays per tile and resolution,
                  the reference design of assumption A9 and practice P1. A mask lookup per scene.
    index-lists   The same precomputation stored as row and column lists.
    lazy-stack    The precomputed mask applied to a lazy array stack built with odc-stac.

Preparation, the mask computation, runs once per lake in its own process and is timed apart
from the per-scene extraction runs. Every extraction run is a fresh process with cold caches.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from s2proto import harness, masks  # noqa: E402

ES_ROOT = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"
BUCKET = "e84-earth-search-sentinel-data"
MANIFEST = ROOT / "examples" / "water-bodies-public-pilot.geojson"
METHODS = ["naive-clip", "raster-mask", "index-lists", "lazy-stack"]
BAND_SETS = {
    "default": ["red", "nir", "swir16", "coastal", "scl"],
    "reflectance": [
        "coastal",
        "blue",
        "green",
        "red",
        "rededge1",
        "rededge2",
        "rededge3",
        "nir",
        "nir08",
        "nir09",
        "swir16",
        "swir22",
    ],
    "quality": ["scl", "aot", "wvp", "cloud", "snow"],
}
BAND_SETS["all"] = BAND_SETS["reflectance"] + BAND_SETS["quality"]
DEFAULT_WINDOW = ("2025-06-01", "2025-10-31")
FULLY = 0.999
"""A lake counts as inside a tile or a footprint when this share of its area is inside."""
GDAL_ENV = {
    "CPL_DEBUG": "ON",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
}
LAZY_CHUNK = 2048
TOLERANCES = {
    "values": (
        "Stored integers extracted by different methods for the same pixel must be identical. "
        "Zero tolerance. Compared through a digest of the values in row-major order."
    ),
    "pixel_sets": (
        "raster-mask, index-lists, and lazy-stack must select identical pixel sets. Zero "
        "tolerance. naive-clip selects what GDAL's all-touched rasterization marks. Its "
        "difference from interior plus shoreline is counted in preparation and reported. It is "
        "not tolerated away."
    ),
    "coverage": (
        f"Coverage within {masks.FRACTION_TOLERANCE} of a whole pixel counts as interior and "
        f"within {masks.FRACTION_TOLERANCE} of zero as outside. Coverage summed over pixels must "
        "equal the polygon area inside the tile within 1e-6 relative."
    ),
    "grid": (
        "lazy-stack output must sit on the requested native window exactly. Any other grid "
        "is recorded as a mismatch and its values are not compared."
    ),
    "timing": "No tolerance. Three repetitions by default, medians reported, every run listed.",
}
METHOD_NOTES = {
    "naive-clip": (
        "Project the polygon and clip per scene. Binary mask of touched pixels, no classes."
    ),
    "raster-mask": (
        "Precomputed class, coverage, and edge-distance arrays, a lookup per scene. "
        "Assumption A9, practice P1."
    ),
    "index-lists": "The same precomputation as row and column lists.",
    "lazy-stack": (
        f"odc-stac lazy load on the mask's native window, {LAZY_CHUNK} pixel chunks, then "
        "the mask lookup."
    ),
}
IMPLEMENTATION = {"script": 2, "masks": masks.MASK_VERSION}
"""Bumped when a worker's behavior changes. Saved results from another version are not reused."""
MASK_PARAMETERS = {
    "near_land_m": masks.NEAR_LAND_M,
    "tolerance": masks.FRACTION_TOLERANCE,
    "edge_distance_cap_m": masks.EDGE_DISTANCE_CAP_M,
    "block_m": masks.BLOCK_M,
    "mask_version": masks.MASK_VERSION,
}
CLASS_RECORD_BYTES = 4 + 4 + 1 + 2
"""Row and column as int32, class as uint8, and one uint16 value, per extracted pixel."""
NAIVE_RECORD_BYTES = 4 + 4 + 2


# ---------------------------------------------------------------- pure helpers


def load_lakes(
    path: Path = MANIFEST,
    regions: list[str] | None = None,
    lake_ids: list[str] | None = None,
    tiers: list[str] | None = None,
) -> list[dict]:
    """Manifest features, filtered. Each keeps its properties, geometry, and bbox."""
    manifest = json.loads(path.read_text())
    lakes = []
    for feature in manifest["features"]:
        props = feature["properties"]
        if regions and props["region"] not in regions:
            continue
        if lake_ids and props["water_body_id"] not in lake_ids:
            continue
        if tiers and props["tier"] not in tiers:
            continue
        lakes.append(feature)
    return lakes


def size_label(lake: dict) -> str:
    props = lake["properties"]
    return "anchor" if props["tier"] == "large" else f"{props['size_class_m']} m"


def lakes_bbox(lakes: list[dict]) -> list[float]:
    boxes = [lake["bbox"] for lake in lakes]
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def lake_placement(lake: dict, item: dict) -> dict:
    """How much of the lake lies inside the item's tile and inside its data footprint."""
    grid = masks.TileGrid.from_item(item)
    polygon = masks.project(lake["geometry"], grid.epsg)
    footprint = masks.project(item["geometry"], grid.epsg)
    return {
        "water_body_id": lake["properties"]["water_body_id"],
        "in_tile": round(masks.fraction_inside(polygon, grid.extent()), 6),
        "in_footprint": round(masks.fraction_inside(polygon, footprint), 6),
    }


def choose_scene(items: list[dict], lakes: list[dict]) -> dict:
    """One tile and one item for a region.

    The tile holds the most lakes entirely, ties broken by the summed share inside, then by
    the smaller tile id. The item covers the most of those lakes with its data footprint, ties
    broken by the lowest cloud cover, then by the latest creation time.
    """
    by_tile: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        code = item.get("properties", {}).get("grid:code")
        if code:
            by_tile[code.removeprefix("MGRS-")].append(item)
    if not by_tile:
        return {"tile": None, "item": None, "lakes": [], "candidates": [], "note": "no item"}
    candidates = []
    for tile, tile_items in sorted(by_tile.items()):
        placements = [lake_placement(lake, tile_items[0]) for lake in lakes]
        inside = [p for p in placements if p["in_tile"] >= FULLY]
        candidates.append(
            {
                "tile": tile,
                "items": len(tile_items),
                "lakes_fully_in_tile": len(inside),
                "summed_share_in_tile": round(sum(p["in_tile"] for p in placements), 6),
            }
        )
    best_score = max((c["lakes_fully_in_tile"], c["summed_share_in_tile"]) for c in candidates)
    tile = min(
        c["tile"]
        for c in candidates
        if (c["lakes_fully_in_tile"], c["summed_share_in_tile"]) == best_score
    )
    best = next(c for c in candidates if c["tile"] == tile)
    scored = []
    for item in by_tile[tile]:
        placements = [lake_placement(lake, item) for lake in lakes]
        in_tile = [p for p in placements if p["in_tile"] >= FULLY]
        covered = sum(1 for p in in_tile if p["in_footprint"] >= FULLY)
        props = item.get("properties", {})
        scored.append(
            (
                covered,
                -(props.get("eo:cloud_cover") if props.get("eo:cloud_cover") is not None else 101),
                props.get("created") or "",
                item,
                placements,
            )
        )
    scored.sort(key=lambda s: (s[0], s[1], s[2]), reverse=True)
    covered, _, _, item, placements = scored[0]
    return {
        "tile": tile,
        "item": item,
        "lakes": placements,
        "candidates": candidates,
        "note": (
            f"tile {tile} holds {best['lakes_fully_in_tile']} of {len(lakes)} lakes entirely. "
            f"Item {item.get('id')} covers {covered} of them with its footprint, cloud cover "
            f"{item.get('properties', {}).get('eo:cloud_cover')}."
        ),
    }


def trim_item(item: dict) -> dict:
    props = item.get("properties", {})
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "datetime": props.get("datetime"),
        "platform": props.get("platform"),
        "product_uri": props.get("s2:product_uri"),
        "processing_baseline": props.get("s2:processing_baseline"),
        "created": props.get("created"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "nodata_pixel_percentage": props.get("s2:nodata_pixel_percentage"),
        "boa_offset_applied": props.get("earthsearch:boa_offset_applied"),
        "grid_code": props.get("grid:code"),
        "epsg": props.get("proj:epsg") or props.get("proj:code"),
    }


def resolve_assets(item: dict, keys: list[str], grid: masks.TileGrid) -> dict:
    """GeoTIFF assets on the tile grid, with their resolution. Others are listed, not read."""
    assets, missing, skipped = [], [], []
    for key in keys:
        asset = item.get("assets", {}).get(key)
        if not asset or "href" not in asset:
            missing.append(key)
            continue
        href = asset["href"]
        media = (asset.get("type") or "").lower()
        reason = None
        if "://" in href and not href.startswith("https://"):
            reason = f"href scheme {href.split('://', 1)[0]} is outside this HTTPS benchmark"
        elif media and "tiff" not in media:
            reason = f"media type {asset.get('type')} is not GeoTIFF"
        else:
            reason = masks.asset_mismatch(grid, asset)
        if reason:
            skipped.append({"key": key, "href": href, "reason": reason})
            continue
        bands = asset.get("raster:bands") or [{}]
        assets.append(
            {
                "key": key,
                "href": href,
                "resolution": masks.asset_resolution(asset),
                "nodata": bands[0].get("nodata"),
                "dtype": bands[0].get("data_type"),
                "file_size": asset.get("file:size"),
            }
        )
    return {"assets": assets, "missing": missing, "skipped": skipped}


def plan_runs(lakes: list[dict], methods: list[str], repeat: int) -> list[dict]:
    runs = []
    for lake in lakes:
        for method in methods:
            for repetition in range(1, repeat + 1):
                runs.append(
                    {
                        "water_body_id": lake["properties"]["water_body_id"],
                        "region": lake["properties"]["region"],
                        "size_label": size_label(lake),
                        "method": method,
                        "repetition": repetition,
                    }
                )
    return runs


def read_seconds(run: dict) -> float:
    """Sum of the per-band open, read, build, and compute timers. Excludes digests."""
    keys = ("open_seconds", "read_seconds", "build_seconds", "compute_seconds")
    return round(sum(band.get(key, 0.0) for band in run["bands"] for key in keys), 3)


def blocks_in_window(window: dict, block_shape: list[int] | None) -> int | None:
    """Internal blocks a window intersects, from its offsets and the file's block shape."""
    if not block_shape or window["height"] <= 0 or window["width"] <= 0:
        return None
    rows = (window["row_off"] + window["height"] - 1) // block_shape[0] - (
        window["row_off"] // block_shape[0]
    )
    cols = (window["col_off"] + window["width"] - 1) // block_shape[1] - (
        window["col_off"] // block_shape[1]
    )
    return (rows + 1) * (cols + 1)


def blocks_touched(run: dict) -> int | None:
    """Blocks intersected over a run's bands, or None when a band lacks a block shape."""
    counts = []
    for band in run.get("bands", []):
        if "window" not in band or "error" in band:
            continue
        blocks = band.get("blocks_touched")
        if blocks is None:
            blocks = blocks_in_window(band["window"], band.get("block_shape"))
        if blocks is None:
            return None
        counts.append(blocks)
    return sum(counts) if counts else None


def _lake_rows(groups: dict[tuple, list[dict]]) -> list[dict]:
    """Medians over repetitions for one lake and method."""
    rows = []
    for (lake_id, method), runs in sorted(groups.items()):
        ok = [r for r in runs if "error" not in r]
        row = {
            "water_body_id": lake_id,
            "method": method,
            "size_label": runs[0]["size_label"],
            "runs": len(runs),
            "failed": len(runs) - len(ok),
            "no_pixel_in_tile": bool(ok) and all(r["totals"]["bands"] == 0 for r in ok),
        }
        if ok and not row["no_pixel_in_tile"]:
            row.update(
                {
                    "wall_seconds_median": round(
                        statistics.median(r["wall_seconds"] for r in ok), 3
                    ),
                    "read_seconds_median": round(statistics.median(read_seconds(r) for r in ok), 3),
                    "setup_seconds_median": round(
                        statistics.median(r["setup"]["seconds"] for r in ok), 3
                    ),
                    "requests_median": int(statistics.median(r["totals"]["requests"] for r in ok)),
                    "bytes_requested_median": int(
                        statistics.median(r["totals"]["bytes_requested"] for r in ok)
                    ),
                    "pixels_in_windows": ok[0]["totals"]["pixels_in_windows"],
                    "pixels_extracted": ok[0]["totals"]["pixels_extracted"],
                    "output_bytes": ok[0]["totals"]["output_bytes"],
                    "blocks_touched": blocks_touched(ok[0]),
                    "peak_rss_bytes_max": max(r["peak_rss_bytes"] for r in ok),
                    "cpu_seconds_median": round(
                        statistics.median(r["cpu"]["user"] + r["cpu"]["system"] for r in ok), 3
                    ),
                }
            )
        rows.append(row)
    return rows


def _class_rows(lake_rows: list[dict]) -> list[dict]:
    """Medians across the lakes of a size class, from each lake's own medians."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in lake_rows:
        groups[(row["size_label"], row["method"])].append(row)
    rows = []
    for (size_label, method), lakes in sorted(groups.items()):
        ok = [r for r in lakes if "read_seconds_median" in r]
        row = {
            "size_label": size_label,
            "method": method,
            "lakes": len(ok),
            "lakes_without_a_pixel_in_the_tile": sum(1 for r in lakes if r["no_pixel_in_tile"]),
            "runs": sum(r["runs"] for r in lakes),
            "failed": sum(r["failed"] for r in lakes),
        }
        if ok:
            keys = (
                "wall_seconds_median",
                "read_seconds_median",
                "setup_seconds_median",
                "cpu_seconds_median",
            )
            row.update({key: round(statistics.median(r[key] for r in ok), 3) for key in keys})
            for key in ("requests_median", "bytes_requested_median"):
                row[key] = int(statistics.median(r[key] for r in ok))
            for key in ("pixels_in_windows", "pixels_extracted", "output_bytes"):
                row[f"{key}_median"] = int(statistics.median(r[key] for r in ok))
            blocks = [r["blocks_touched"] for r in ok if r.get("blocks_touched") is not None]
            row["blocks_touched_median"] = int(statistics.median(blocks)) if blocks else None
            row["blocks_touched_max"] = max(blocks) if blocks else None
            row["peak_rss_bytes_max"] = max(r["peak_rss_bytes_max"] for r in ok)
        rows.append(row)
    return rows


def _preparation_rows(preparation: dict[str, dict], lakes_by_id: dict[str, dict]) -> list[dict]:
    """Per size class: preparation time and pixel counts per class and resolution, medians."""
    groups: dict[str, list[dict]] = defaultdict(list)
    outside: dict[str, int] = defaultdict(int)
    for lake_id, prep in preparation.items():
        if "error" in prep or lake_id not in lakes_by_id:
            continue
        if prep["fraction_in_tile"] == 0:
            outside[size_label(lakes_by_id[lake_id])] += 1
            continue
        groups[size_label(lakes_by_id[lake_id])].append(prep)
    rows = []
    for label, preps in sorted(groups.items()):
        resolutions = sorted({res for p in preps for res in p["resolutions"]}, key=int)
        classes = {}
        for res in resolutions:
            counts = [p["resolutions"][res]["counts"] for p in preps if res in p["resolutions"]]
            names = ("interior", "shoreline", "near_land", "naive_only", "classes_only")
            classes[res] = {
                name: int(statistics.median(c.get(name, 0) for c in counts)) for name in names
            }
            classes[res]["all_classes_median"] = int(
                statistics.median(c["interior"] + c["shoreline"] + c["near_land"] for c in counts)
            )
            classes[res]["interior_max"] = max(c["interior"] for c in counts)
        rows.append(
            {
                "size_label": label,
                "lakes": len(preps),
                "lakes_without_a_pixel_in_the_tile": outside.get(label, 0),
                "prepare_seconds_median": round(
                    statistics.median(p["wall_seconds"] for p in preps), 3
                ),
                "prepare_seconds_max": max(p["wall_seconds"] for p in preps),
                "peak_rss_bytes_max": max(p["peak_rss_bytes"] for p in preps),
                "fraction_in_tile_min": min(p["fraction_in_tile"] for p in preps),
                "classes": classes,
            }
        )
    return rows


def run_status(run: dict) -> str:
    """failed, no_pixel_in_tile, band_errors, or ok."""
    if "error" in run:
        return "failed"
    if run["totals"]["bands"] == 0 and run["totals"]["band_errors"] > 0:
        errors = {b.get("error") for b in run["bands"] if "error" in b}
        if errors == {"no pixel of this lake in the tile"}:
            return "no_pixel_in_tile"
    if run["totals"]["band_errors"] > 0:
        return "band_errors"
    return "ok"


def summarize(
    runs: list[dict], preparation: dict[str, dict], lakes: list[dict], plan: dict | None = None
) -> dict:
    """Medians per lake and method, then per size class, plus the equality checks.

    Equality compares value digests and pixel-set digests separately. A comparison is complete
    only when every planned method and repetition contributed a band record.
    """
    plan = plan or {"methods": METHODS, "repeat": max((r["repetition"] for r in runs), default=1)}
    by_lake: dict[tuple, list[dict]] = defaultdict(list)
    for run in runs:
        by_lake[(run["water_body_id"], run["method"])].append(run)
    lake_rows = _lake_rows(by_lake)
    lakes_by_id = {lake["properties"]["water_body_id"]: lake for lake in lakes}
    digests: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    present: dict[tuple, set] = defaultdict(set)
    for run in runs:
        for band in run.get("bands", []):
            if band.get("key", "").startswith("stack-") or "digest_all" not in band:
                continue
            slot = digests[(run["water_body_id"], band["key"], band["resolution"])]
            present[(run["water_body_id"], band["key"], band["resolution"])].add(
                (run["method"], run["repetition"])
            )
            if run["method"] == "naive-clip":
                slot["naive_wet"].add(band["digest_all"])
                slot["naive_pixels"].add(band.get("digest_pixels"))
            else:
                slot["classes_all"].add(band["digest_all"])
                slot["classes_wet"].add(band["digest_wet"])
                slot["classes_pixels"].add(band.get("digest_pixels"))
                slot["classes_pixels_wet"].add(band.get("digest_pixels_wet"))
    expected = {(m, r) for m in plan["methods"] for r in range(1, plan["repeat"] + 1)}
    equality = []
    for (lake_id, key, resolution), slot in sorted(digests.items()):
        counts = (
            preparation.get(lake_id, {})
            .get("resolutions", {})
            .get(str(resolution), {})
            .get("counts", {})
        )
        naive_differs = bool(counts.get("naive_only") or counts.get("classes_only"))
        known = {d for d in slot["classes_pixels"] if d} if slot["classes_pixels"] else set()
        equality.append(
            {
                "water_body_id": lake_id,
                "band": key,
                "resolution": resolution,
                "complete": expected <= present[(lake_id, key, resolution)],
                "missing": sorted(
                    f"{m}:{r}" for m, r in expected - present[(lake_id, key, resolution)]
                ),
                "mask_methods_identical": (
                    len(slot["classes_all"]) == 1 if slot["classes_all"] else None
                ),
                "mask_pixel_sets_identical": (
                    len(known) == 1 if known and None not in slot["classes_pixels"] else None
                ),
                "naive_matches_interior_and_shoreline": (
                    slot["naive_wet"] == slot["classes_wet"]
                    if slot["naive_wet"] and slot["classes_wet"]
                    else None
                ),
                "naive_pixel_set_matches": (
                    slot["naive_pixels"] == slot["classes_pixels_wet"]
                    if slot["naive_pixels"] - {None} and slot["classes_pixels_wet"] - {None}
                    else None
                ),
                "naive_set_differs_in_preparation": naive_differs,
            }
        )
    tiles = sorted({r["tile"] for r in runs if "tile" in r})
    tile_dates = sorted({(r["tile"], r["item_id"]) for r in runs if "item_id" in r})
    statuses = [run_status(r) for r in runs]
    return {
        "lakes": len(lakes),
        "distinct_tiles": len(tiles),
        "distinct_tile_dates": len(tile_dates),
        "runs": {
            "planned": len(runs),
            "with_pixels": statuses.count("ok"),
            "without_a_pixel_in_the_tile": statuses.count("no_pixel_in_tile"),
            "with_band_errors": statuses.count("band_errors"),
            "failed": statuses.count("failed"),
        },
        "by_size_class_method": _class_rows(lake_rows),
        "by_lake_method": lake_rows,
        "preparation_by_size_class": _preparation_rows(preparation, lakes_by_id),
        "equality": equality,
        "equality_incomplete": sum(1 for e in equality if not e["complete"]),
    }


# ---------------------------------------------------------------- workers


def grid_from_spec(spec: dict) -> masks.TileGrid:
    return masks.TileGrid(**spec["grid"])


def prepare_worker(spec: dict) -> dict:
    """Masks and index lists for one lake at every resolution, timed per resolution."""
    started = harness.utc_now()
    cpu_before = harness.cpu_seconds()
    grid = grid_from_spec(spec)
    with harness.Timer() as project_timer:
        polygon = masks.project(spec["geometry"], grid.epsg)
    in_tile = masks.fraction_inside(polygon, grid.extent())
    area_in_tile = polygon.intersection(grid.extent()).area
    resolutions = {}
    with harness.Timer() as wall:
        for resolution in spec["resolutions"]:
            mask = masks.compute_mask(polygon, grid, resolution)
            mask_path = Path(spec["mask_paths"][str(resolution)])
            index_path = Path(spec["index_paths"][str(resolution)])
            masks.save_mask(mask, mask_path)
            written = masks.save_index_lists(mask, index_path)
            area = mask.counts.get("coverage_area_m2", 0.0)
            resolutions[str(resolution)] = {
                "window": mask.window.as_dict(),
                "counts": mask.counts,
                "timings": mask.timings,
                "parameters": mask.parameters,
                "coverage_area_relative_error": (
                    round(abs(area - area_in_tile) / area_in_tile, 12) if area_in_tile else None
                ),
                "mask_file_bytes": mask_path.stat().st_size,
                "index_file_bytes": written["bytes"],
                "mask_sha256": harness.sha256_bytes(mask_path.read_bytes()),
                "index_sha256": harness.sha256_bytes(index_path.read_bytes()),
            }
    return {
        "water_body_id": spec["water_body_id"],
        "started_at": started,
        "polygon_sha256": spec["polygon_sha256"],
        "grid": spec["grid"],
        "mask_parameters": spec.get("mask_parameters"),
        "implementation": spec.get("implementation"),
        "project_seconds": project_timer.seconds,
        "fraction_in_tile": round(in_tile, 6),
        "wall_seconds": wall.seconds,
        "cpu": harness.cpu_delta(cpu_before, harness.cpu_seconds()),
        "peak_rss_bytes": harness.peak_rss_bytes(),
        "resolutions": resolutions,
    }


def digest_values(values) -> str:
    """Digest of the values as 64-bit integers, so the file's dtype does not matter."""
    import numpy as np

    contiguous = np.ascontiguousarray(values, dtype="<i8")
    if contiguous.size == 0:
        return harness.sha256_bytes(b"")
    return harness.sha256_bytes(memoryview(contiguous).cast("B"))


def read_window(href: str, window: masks.Window) -> tuple[dict, object]:
    import rasterio
    from rasterio.windows import Window as RioWindow

    with harness.Timer() as open_timer:
        dataset = rasterio.open(href)
    with dataset:
        info = {
            "dtype": str(dataset.dtypes[0]),
            "nodata": dataset.nodata,
            "block_shape": list(dataset.block_shapes[0]),
        }
        with harness.Timer() as read_timer:
            array = dataset.read(
                1, window=RioWindow(window.col_off, window.row_off, window.width, window.height)
            )
    info.update({"open_seconds": open_timer.seconds, "read_seconds": read_timer.seconds})
    return info, array


def digest_pixels(rows, cols, classes=None) -> str:
    """Digest of tile rows, columns, and classes, so two methods can prove the same pixel set."""
    import numpy as np

    rows = np.asarray(rows, dtype="<i8")
    cols = np.asarray(cols, dtype="<i8")
    classes = np.zeros_like(rows) if classes is None else np.asarray(classes, dtype="<i8")
    stacked = np.ascontiguousarray(np.stack([rows, cols, classes], axis=1))
    if stacked.size == 0:
        return harness.sha256_bytes(b"")
    return harness.sha256_bytes(memoryview(stacked).cast("B"))


def extracted_record(values, classes, nodata, naive: bool, rows=None, cols=None) -> dict:
    """Counts, digests, and output bytes for one band's extracted values.

    Rows and columns are tile coordinates of the extracted pixels, in the same order as the
    values. They feed the pixel-set digests beside the value digests.
    """
    import numpy as np

    values = np.asarray(values)
    record: dict = {
        "pixels_extracted": int(values.size),
        "nodata_extracted": int((values == nodata).sum()) if nodata is not None else None,
        "value_min": int(values.min()) if values.size else None,
        "value_max": int(values.max()) if values.size else None,
        "digest_all": digest_values(values),
    }
    if naive:
        record["counts"] = {"naive": int(values.size)}
        record["digest_wet"] = record["digest_all"]
        record["output_bytes"] = int(values.size) * NAIVE_RECORD_BYTES
        if rows is not None:
            record["digest_pixels"] = digest_pixels(rows, cols)
            record["digest_pixels_wet"] = record["digest_pixels"]
    else:
        classes = np.asarray(classes)
        record["counts"] = {
            name: int((classes == code).sum()) for name, code in masks.CLASS_CODES.items()
        }
        wet = classes != masks.CLASS_CODES["near_land"]
        record["digest_wet"] = digest_values(values[wet])
        record["output_bytes"] = int(values.size) * CLASS_RECORD_BYTES
        if rows is not None:
            rows, cols = np.asarray(rows), np.asarray(cols)
            record["digest_pixels"] = digest_pixels(rows, cols, classes)
            record["digest_pixels_wet"] = digest_pixels(rows[wet], cols[wet])
    return record


def gdal_totals(capture: harness.GdalLogCapture) -> dict:
    gdal = harness.parse_gdal_log(capture.take())
    return {
        "requests": gdal["requests"] + gdal["size_requests"],
        "bytes_requested": gdal["bytes"],
        "size_requests": gdal["size_requests"],
    }


def window_record(asset: dict, window: masks.Window, info: dict, array) -> dict:
    return {
        "key": asset["key"],
        "href": asset["href"],
        "resolution": asset["resolution"],
        "window": window.as_dict(),
        "pixels_in_window": int(array.size),
        "bytes_in_window": int(array.nbytes),
        "blocks_touched": blocks_in_window(window.as_dict(), info.get("block_shape")),
        **info,
    }


def extract_naive(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list[dict]]:
    import numpy as np

    grid = grid_from_spec(spec)
    with harness.Timer() as setup:
        polygon = masks.project(spec["geometry"], grid.epsg)
    bands = []
    for asset in spec["assets"]:
        with harness.Timer() as clip:
            window, selected = masks.naive_mask(polygon, grid, asset["resolution"])
        if window.empty:
            bands.append({"key": asset["key"], "error": "no pixel of this lake in the tile"})
            continue
        info, array = read_window(asset["href"], window)
        record = window_record(asset, window, info, array)
        record["clip_seconds"] = clip.seconds
        record.update(gdal_totals(capture))
        rows, cols = np.nonzero(selected)
        record.update(
            extracted_record(
                array[selected],
                None,
                info["nodata"],
                naive=True,
                rows=rows + window.row_off,
                cols=cols + window.col_off,
            )
        )
        bands.append(record)
    return {"kind": "project polygon", "seconds": setup.seconds}, bands


def _load_masks(spec: dict) -> tuple[dict, dict[int, masks.Mask]]:
    with harness.Timer() as setup:
        loaded = {int(res): masks.load_mask(Path(path)) for res, path in spec["mask_paths"].items()}
    return {"kind": "load masks", "seconds": setup.seconds}, loaded


def extract_raster_mask(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list[dict]]:
    import numpy as np

    setup, loaded = _load_masks(spec)
    bands = []
    for asset in spec["assets"]:
        mask = loaded[asset["resolution"]]
        if mask.window.empty:
            bands.append({"key": asset["key"], "error": "no pixel of this lake in the tile"})
            continue
        info, array = read_window(asset["href"], mask.window)
        record = window_record(asset, mask.window, info, array)
        record.update(gdal_totals(capture))
        selected = mask.selected()
        rows, cols = np.nonzero(selected)
        record.update(
            extracted_record(
                array[selected],
                mask.pixel_class[selected],
                info["nodata"],
                False,
                rows=rows + mask.window.row_off,
                cols=cols + mask.window.col_off,
            )
        )
        bands.append(record)
    return setup, bands


def extract_index_lists(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list[dict]]:
    with harness.Timer() as setup:
        loaded = {
            int(res): masks.load_index_lists(Path(path))[0]
            for res, path in spec["index_paths"].items()
        }
    bands = []
    for asset in spec["assets"]:
        lists = loaded[asset["resolution"]]
        window = masks.lists_window(lists)
        if window.empty:
            bands.append({"key": asset["key"], "error": "no pixel of this lake in the tile"})
            continue
        info, array = read_window(asset["href"], window)
        record = window_record(asset, window, info, array)
        record.update(gdal_totals(capture))
        values = array[lists["rows"] - window.row_off, lists["cols"] - window.col_off]
        record.update(
            extracted_record(
                values,
                lists["pixel_class"],
                info["nodata"],
                False,
                rows=lists["rows"],
                cols=lists["cols"],
            )
        )
        bands.append(record)
    return {"kind": "load index lists", "seconds": setup.seconds}, bands


def extract_lazy_stack(spec: dict, capture: harness.GdalLogCapture) -> tuple[dict, list[dict]]:
    import numpy as np
    import odc.stac
    import pystac
    from odc.geo.geobox import GeoBox

    setup, loaded = _load_masks(spec)
    with harness.Timer() as item_timer:
        item = pystac.Item.from_dict(json.loads(Path(spec["item_path"]).read_text()))
    setup = {
        "kind": "load masks and item",
        "seconds": round(setup["seconds"] + item_timer.seconds, 4),
    }
    grid = grid_from_spec(spec)
    by_resolution: dict[int, list[dict]] = defaultdict(list)
    for asset in spec["assets"]:
        by_resolution[asset["resolution"]].append(asset)
    bands = []
    for resolution, assets in sorted(by_resolution.items()):
        mask = loaded[resolution]
        if mask.window.empty:
            bands.extend(
                {"key": a["key"], "error": "no pixel of this lake in the tile"} for a in assets
            )
            continue
        geobox = GeoBox(
            (mask.window.height, mask.window.width),
            mask.window.transform(grid, resolution),
            f"EPSG:{grid.epsg}",
        )
        with harness.Timer() as build:
            stack = odc.stac.load(
                [item],
                bands=[a["key"] for a in assets],
                geobox=geobox,
                chunks={"x": LAZY_CHUNK, "y": LAZY_CHUNK},
                groupby="id",
            )
        stack_record = {
            "key": f"stack-{resolution}m",
            "resolution": resolution,
            "build_seconds": build.seconds,
            "chunk": LAZY_CHUNK,
            "grid_matches": bool(stack.odc.geobox == geobox),
            "returned_transform": list(stack.odc.geobox.affine)[:6],
        }
        stack_record.update(gdal_totals(capture))
        bands.append(stack_record)
        selected = mask.selected()
        sel_rows, sel_cols = np.nonzero(selected)
        for asset in assets:
            with harness.Timer() as compute:
                array = stack[asset["key"]].isel(time=0).compute().values
            record = {
                "key": asset["key"],
                "href": asset["href"],
                "resolution": resolution,
                "window": mask.window.as_dict(),
                "pixels_in_window": int(array.size),
                "bytes_in_window": int(array.nbytes),
                "dtype": str(array.dtype),
                "nodata": asset.get("nodata"),
                "compute_seconds": compute.seconds,
            }
            record.update(gdal_totals(capture))
            if not stack_record["grid_matches"]:
                record["error"] = "returned grid differs from the requested window"
                bands.append(record)
                continue
            values = array[selected]
            if np.issubdtype(values.dtype, np.floating):
                nan = np.isnan(values)
                record["nan_extracted"] = int(nan.sum())
                values = np.where(nan, asset.get("nodata") or 0, values)
            record.update(
                extracted_record(
                    values,
                    mask.pixel_class[selected],
                    asset.get("nodata"),
                    False,
                    rows=sel_rows + mask.window.row_off,
                    cols=sel_cols + mask.window.col_off,
                )
            )
            bands.append(record)
    return setup, bands


EXTRACTORS = {
    "naive-clip": extract_naive,
    "raster-mask": extract_raster_mask,
    "index-lists": extract_index_lists,
    "lazy-stack": extract_lazy_stack,
}


def extract_worker(spec: dict) -> dict:
    """One lake, one method, one repetition. Reads every asset window of the scene."""
    import rasterio

    started = harness.utc_now()
    net_before = harness.net_counters()
    cpu_before = harness.cpu_seconds()
    with harness.Timer() as wall, rasterio.Env(**GDAL_ENV), harness.GdalLogCapture() as capture:
        setup, bands = EXTRACTORS[spec["method"]](spec, capture)
    if spec.get("log_path"):
        Path(spec["log_path"]).write_text("\n".join(capture.all_lines) + "\n")
    ok = [b for b in bands if "error" not in b]
    extracted = [b for b in ok if "digest_all" in b]
    return {
        **{k: spec[k] for k in ("water_body_id", "region", "size_label", "method", "repetition")},
        "tile": spec["tile"],
        "item_id": spec["item_id"],
        "started_at": started,
        "wall_seconds": wall.seconds,
        "cpu": harness.cpu_delta(cpu_before, harness.cpu_seconds()),
        "peak_rss_bytes": harness.peak_rss_bytes(),
        "net": harness.net_delta(net_before, harness.net_counters()),
        "setup": setup,
        "inputs": spec.get("inputs"),
        "bands": bands,
        "totals": {
            "bands": len(extracted),
            "band_errors": len(bands) - len(ok),
            "requests": sum(b.get("requests", 0) for b in ok),
            "bytes_requested": sum(b.get("bytes_requested", 0) for b in ok),
            "pixels_in_windows": sum(b.get("pixels_in_window", 0) for b in ok),
            "pixels_extracted": sum(b.get("pixels_extracted", 0) for b in ok),
            "output_bytes": sum(b.get("output_bytes", 0) for b in ok),
        },
        "gdal_env": GDAL_ENV,
    }


# ---------------------------------------------------------------- parent


def search_region(client: harness.Client, bbox: list[float], window: tuple[str, str]) -> list[dict]:
    """Every Collection 1 item intersecting the box in the window, following next links."""
    body = {
        "collections": [COLLECTION],
        "bbox": bbox,
        "datetime": f"{window[0]}T00:00:00Z/{window[1]}T23:59:59Z",
        "limit": 100,
    }
    items: list[dict] = []
    for page in range(1, 21):
        result = client.post_json(f"{ES_ROOT}/search", body, f"search page {page}")
        items.extend(result.get("features", []))
        link = next((x for x in result.get("links", []) if x.get("rel") == "next"), None)
        if not link:
            break
        if link.get("body"):
            body = {**body, **link["body"]} if link.get("merge") else link["body"]
        else:
            body = {**body, "token": link.get("href", "").rsplit("token=", 1)[-1]}
    return items


def run_in_subprocess(task: str, spec: dict, spec_path: Path) -> dict:
    spec_path.write_text(json.dumps(spec))
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), f"--{task}-worker", str(spec_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **GDAL_ENV},
    )
    if completed.returncode != 0:
        keys = ("water_body_id", "region", "size_label", "method", "repetition")
        return {**{k: spec[k] for k in keys if k in spec}, "error": completed.stderr[-3000:]}
    return json.loads(completed.stdout.strip().splitlines()[-1])


def reuse_mismatch(saved: dict, spec: dict, keys: tuple[str, ...]) -> str | None:
    """Why a saved result cannot stand in for the requested run, or None when it can.

    Extraction results are bound to their inputs: the polygon digest, the grid, the mask file
    digests, the mask parameters, and the implementation version. A saved run with any band
    error is never reused.
    """
    for key in keys:
        if saved.get(key) != spec.get(key):
            return f"{key} differs"
    if "assets" in spec:
        if any("error" in b for b in saved.get("bands", [])):
            return "saved run has a band error"
        saved_assets = sorted(
            (b.get("key"), b.get("href")) for b in saved.get("bands", []) if "href" in b
        )
        wanted = sorted((a["key"], a["href"]) for a in spec["assets"])
        if saved_assets != wanted:
            return "assets differ: another product, band set, or a failed band"
        if saved.get("gdal_env") != GDAL_ENV:
            return "reader configuration differs"
        if saved.get("inputs") != spec.get("inputs"):
            return "inputs differ: polygon, grid, masks, mask parameters, or implementation"
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


def polygon_digest(lake: dict) -> str:
    return hashlib.sha256(json.dumps(lake["geometry"], sort_keys=True).encode()).hexdigest()


def print_plan(lakes: list[dict], runs: list[dict], bands: list[str], methods: list[str]) -> None:
    print(
        f"{len(lakes)} lakes, {len(methods)} methods, {len(runs)} extraction runs. "
        "Scenes resolve from the catalog at run time."
    )
    print(f"  bands: {', '.join(bands)}")
    by_region: dict[str, list[dict]] = defaultdict(list)
    for lake in lakes:
        by_region[lake["properties"]["region"]].append(lake)
    for region, region_lakes in by_region.items():
        labels = ", ".join(
            f"{lake['properties']['water_body_id']} ({size_label(lake)})" for lake in region_lakes
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
    parser.add_argument("--methods", nargs="+", default=METHODS, choices=METHODS)
    parser.add_argument(
        "--bands",
        nargs="+",
        default=["default"],
        help="Asset keys, or a set name: default, reflectance, quality, all",
    )
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--window", nargs=2, default=list(DEFAULT_WINDOW), metavar=("START", "END"))
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks" / "results" / "lake-extraction.json"
    )
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "lake-extraction")
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
        bands.extend(BAND_SETS.get(band, [band]))
    lakes = load_lakes(args.manifest, args.regions, args.lakes, args.tiers)
    if not lakes:
        print("no lake matches the selection")
        return 1
    runs = plan_runs(lakes, args.methods, args.repeat)
    if args.dry_run:
        print_plan(lakes, runs, bands, args.methods)
        return 0

    measured_at = harness.utc_now()
    raw_dir = args.raw_dir / measured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = harness.Client(pause=args.pause)
    by_region: dict[str, list[dict]] = defaultdict(list)
    for lake in lakes:
        by_region[lake["properties"]["region"]].append(lake)

    scenes: dict[str, dict] = {}
    for region, region_lakes in by_region.items():
        items = search_region(client, lakes_bbox(region_lakes), tuple(args.window))
        scene = choose_scene(items, region_lakes)
        print(f"{region}: {len(items)} items in the window. {scene['note']}", flush=True)
        if scene["item"] is None:
            scenes[region] = {**scene, "assets": None}
            continue
        item_path = raw_dir / "items" / f"{region}.json"
        item_path.parent.mkdir(parents=True, exist_ok=True)
        item_path.write_text(json.dumps(scene["item"], indent=1) + "\n")
        grid = masks.TileGrid.from_item(scene["item"])
        resolved = resolve_assets(scene["item"], bands, grid)
        for skip in resolved["skipped"]:
            print(f"  {region}: skipping {skip['key']}, {skip['reason']}", flush=True)
        if resolved["missing"]:
            print(f"  {region}: missing {resolved['missing']}", flush=True)
        scenes[region] = {
            "tile": scene["tile"],
            "item": trim_item(scene["item"]),
            "item_path": str(item_path),
            "grid": dataclasses.asdict(grid),
            "lakes": scene["lakes"],
            "candidates": scene["candidates"],
            "note": scene["note"],
            "assets": resolved,
        }

    preparation: dict[str, dict] = {}
    for lake in lakes:
        props = lake["properties"]
        lake_id, region = props["water_body_id"], props["region"]
        scene = scenes[region]
        if scene.get("assets") is None:
            preparation[lake_id] = {"water_body_id": lake_id, "error": "no scene for the region"}
            continue
        resolutions = sorted({a["resolution"] for a in scene["assets"]["assets"]})
        spec = {
            "water_body_id": lake_id,
            "geometry": lake["geometry"],
            "polygon_sha256": polygon_digest(lake),
            "grid": scene["grid"],
            "resolutions": resolutions,
            "mask_paths": {
                str(r): str(raw_dir / "masks" / f"{lake_id}-{r}m.npz") for r in resolutions
            },
            "index_paths": {
                str(r): str(raw_dir / "index" / f"{lake_id}-{r}m.npz") for r in resolutions
            },
            "mask_parameters": MASK_PARAMETERS,
            "implementation": IMPLEMENTATION,
        }
        name = f"prepare-{lake_id}"
        result, reason = reusable_result(
            args.reuse,
            name,
            spec,
            ("water_body_id", "polygon_sha256", "grid", "mask_parameters", "implementation"),
        )
        if result is not None and args.reuse:
            for key, digest_key in (("mask_paths", "mask_sha256"), ("index_paths", "index_sha256")):
                for res, path in spec[key].items():
                    source = args.reuse / Path(path).relative_to(raw_dir)
                    expected = result["resolutions"].get(res, {}).get(digest_key)
                    if not source.exists():
                        result, reason = None, f"saved {key} for {res} m missing"
                        break
                    if harness.sha256_bytes(source.read_bytes()) != expected:
                        result, reason = None, f"saved {key} for {res} m differs from its record"
                        break
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    Path(path).write_bytes(source.read_bytes())
                if result is None:
                    break
        if reason:
            print(f"  {name}: not reusing the saved result, {reason}", flush=True)
        if result is None:
            result = run_in_subprocess("prepare", spec, raw_dir / f"{name}.spec.json")
        (raw_dir / f"{name}.result.json").write_text(json.dumps(result, indent=1) + "\n")
        preparation[lake_id] = result
        if "error" in result:
            print(f"{name}: FAILED {result['error'][-200:]}", flush=True)
            continue
        counts = " ".join(
            f"{r}m {v['counts']['interior']}/{v['counts']['shoreline']}/{v['counts']['near_land']}"
            for r, v in result["resolutions"].items()
        )
        print(
            f"{name}: {result['wall_seconds']:.1f} s, in tile {result['fraction_in_tile']:.3f}, "
            f"interior/shoreline/near-land {counts}, peak {result['peak_rss_bytes'] / 1e9:.2f} GB",
            flush=True,
        )

    lake_by_id = {lake["properties"]["water_body_id"]: lake for lake in lakes}
    results = []
    for index, run in enumerate(runs, 1):
        name = f"{index:03d}-{run['water_body_id']}-{run['method']}-{run['repetition']}"
        scene = scenes[run["region"]]
        prep = preparation[run["water_body_id"]]
        if scene.get("assets") is None or "error" in prep:
            results.append({**run, "error": "no scene or no masks for this lake"})
            print(f"{index}/{len(runs)} {name}: SKIPPED, no scene or no masks", flush=True)
            continue
        spec = {
            **run,
            "tile": scene["tile"],
            "item_id": scene["item"]["id"],
            "item_path": scene["item_path"],
            "grid": scene["grid"],
            "geometry": lake_by_id[run["water_body_id"]]["geometry"],
            "assets": scene["assets"]["assets"],
            "mask_paths": {
                str(r): str(raw_dir / "masks" / f"{run['water_body_id']}-{r}m.npz")
                for r in sorted({a["resolution"] for a in scene["assets"]["assets"]})
            },
            "index_paths": {
                str(r): str(raw_dir / "index" / f"{run['water_body_id']}-{r}m.npz")
                for r in sorted({a["resolution"] for a in scene["assets"]["assets"]})
            },
            "log_path": str(raw_dir / f"{name}.gdal.log"),
        }
        spec["inputs"] = {
            "polygon_sha256": prep["polygon_sha256"],
            "grid": scene["grid"],
            "mask_digests": {
                res: {"mask": v.get("mask_sha256"), "index": v.get("index_sha256")}
                for res, v in prep["resolutions"].items()
            },
            "mask_parameters": prep.get("mask_parameters"),
            "implementation": IMPLEMENTATION,
        }
        result, reason = reusable_result(
            args.reuse, name, spec, ("water_body_id", "method", "repetition", "tile", "item_id")
        )
        if reason:
            print(f"  {name}: not reusing the saved result, {reason}", flush=True)
        if result is None:
            result = run_in_subprocess("extract", spec, raw_dir / f"{name}.spec.json")
        (raw_dir / f"{name}.result.json").write_text(json.dumps(result, indent=1) + "\n")
        results.append(result)
        if "error" in result:
            print(f"{index}/{len(runs)} {name}: FAILED {result['error'][-200:]}", flush=True)
            continue
        totals = result["totals"]
        reused = " (reused)" if "reused_from" in result else ""
        print(
            f"{index}/{len(runs)} {name}{reused}: {result['wall_seconds']:.1f} s, "
            f"{totals['bytes_requested'] / 1e6:.1f} MB requested, {totals['requests']} requests, "
            f"{totals['pixels_extracted']} pixels, peak {result['peak_rss_bytes'] / 1e9:.2f} GB",
            flush=True,
        )

    output = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": harness.code_version(),
        "script": "benchmarks/lake_extraction.py",
        "stage": "2, one lake at a time",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2. Transfer times include "
            "that path. Assumption A25. Repeat from us-west-2 when AWS access exists."
        ),
        "endpoints": {
            "c1": {
                "label": "Collection 1 copy",
                "collection": COLLECTION,
                "bucket": BUCKET,
                "region": "us-west-2",
                "payer": (
                    "provider. Public bucket read with unsigned requests. The registry lists "
                    "RequesterPays false, finding F-22."
                ),
            }
        },
        "catalog": {
            "root": ES_ROOT,
            "collection": COLLECTION,
            "window": list(args.window),
            "rule": choose_scene.__doc__.strip(),
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
        "methods": METHOD_NOTES,
        "bands": bands,
        "tolerances": TOLERANCES,
        "plan": {
            "methods": args.methods,
            "repeat": args.repeat,
            "lakes": len(lakes),
            "runs": len(runs),
        },
        "scenes": scenes,
        "preparation": preparation,
        "runs": results,
        "pixels_read_between": pixels_read_between(results),
        "reused_runs": sum(1 for r in results if "reused_from" in r),
        "reused_from": str(args.reuse) if args.reuse else None,
        "implementation": IMPLEMENTATION,
        "summary": summarize(
            results, preparation, lakes, {"methods": args.methods, "repeat": args.repeat}
        ),
        "summary_generated_at": harness.utc_now(),
        "catalog_request_log": client.log,
        "raw_dir": str(raw_dir),
        "limitations": [
            "Runs on the owner's laptop over the internet, outside us-west-2. Every transfer "
            "time includes that path. Assumption A25.",
            "Requests and bytes come from GDAL's debug log of requested ranges, what the reader "
            "asked for, not what the network delivered. Network counters are machine-wide.",
            "One Collection 1 item per region, chosen by the rule under catalog. Timings are for "
            "that acquisition. Cloud cover changes compression and so bytes, not the method.",
            "Only the part of a lake inside the chosen tile is extracted. The share inside is "
            "recorded per lake. Lakes across tiles are stage 4 work.",
            "Preparation is timed in its own process per lake, all resolutions together, and "
            "excluded from the extraction runs. Extraction runs load the saved masks from disk "
            "and time that as setup.",
            "Wall seconds per run include digests and statistics. The per-band timers exclude "
            "them. Every run is a fresh process, so GDAL caches start cold. Provider-side and "
            "operating-system caches are not controlled.",
            "Output bytes are the size of row, column, class, and value fields per extracted "
            "pixel, not a stored file. No storage layout is selected.",
            "Edge distance is exact up to the cap in the mask parameters. Farther interior "
            "pixels carry no distance.",
            "The naive method's pixel set is what GDAL's all-touched rasterization marks. Its "
            "difference from the exact interior and shoreline set is counted in preparation.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=1) + "\n")
    print(f"wrote {args.output}: {run_counts_label(output['summary']['runs'])}", flush=True)
    return 0


def run_counts_label(counts: dict) -> str:
    return (
        f"{counts['planned']} runs, {counts['with_pixels']} with pixels, "
        f"{counts['without_a_pixel_in_the_tile']} without a pixel in the tile, "
        f"{counts['with_band_errors']} with band errors, {counts['failed']} failed"
    )


def pixels_read_between(results: list[dict]) -> list[str] | None:
    """First and last start time of the runs that read a pixel."""
    starts = sorted(
        r["started_at"] for r in results if "error" not in r and r["totals"]["bands"] > 0
    )
    return [starts[0], starts[-1]] if starts else None


def resummarize(path: Path) -> int:
    """Recompute a result file's summary from its own runs and preparation. No network.

    Everything measured stays as it is. Only `summary`, `summary_generated_at`, and
    `pixels_read_between` change, and the implementation that summarized is recorded.
    """
    result = json.loads(path.read_text())
    manifest = ROOT / result["manifest"]["path"]
    lakes = load_lakes(manifest, lake_ids=list(result["preparation"]))
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != result["manifest"]["sha256"]:
        print(f"{manifest} differs from the manifest the run used. Not summarized.")
        return 1
    result["summary"] = summarize(result["runs"], result["preparation"], lakes, result.get("plan"))
    result["summary_generated_at"] = harness.utc_now()
    result["summary_implementation"] = IMPLEMENTATION
    result["pixels_read_between"] = pixels_read_between(result["runs"])
    path.write_text(json.dumps(result, indent=1) + "\n")
    print(f"summarized {path}: {run_counts_label(result['summary']['runs'])}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
