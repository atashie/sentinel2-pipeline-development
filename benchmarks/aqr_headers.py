"""Probe T1: layout and file headers of the USGS ACOLITE aquatic reflectance bucket.

Runs only when the user invokes it. Unsigned requests, no credentials. It lists the bucket's
version and tile prefixes, then the objects of three tile-dates. For each object it sends a
HEAD request. It reads each scene's settings text file whole and opens each GeoTIFF header
through GDAL. It decodes no pixel. For each tile-date it also fetches the matching Earth Search
Level-2A items, to compare the 20 m grids. Probe T1 of the replan record,
docs/reviews/2026-10-13-acolite-first-replan.md.

    uv run python benchmarks/aqr_headers.py --dry-run
    uv run python benchmarks/aqr_headers.py
    uv run python benchmarks/aqr_headers.py --scene 17SKU:2025-10-15 --output data/smoke.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from s2proto import aqr, harness  # noqa: E402

ES_ROOT = "https://earth-search.aws.element84.com/v1"
ES_ORDER = ["sentinel-2-c1-l2a", "sentinel-2-l2a"]
ES_GRID_ASSET = "rededge1"
# Stage 1's tile-date, stage 3's Lake Tahoe tile-date, and the first scene of July 2022 on the
# stage 1 tile, a month when Collection 1 on Earth Search is nearly empty (finding 1).
DEFAULT_SCENES = ["17SKU:2025-10-15", "10SGJ:2025-10-20", "17SKU:2022-07"]
GDAL_ENV = {
    "CPL_DEBUG": "ON",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "2",
}
SETTINGS_KEYS = [
    "acolite_version",
    "aerosol_correction",
    "dsf_aot_estimate",
    "dsf_tile_dimensions",
    "dsf_residual_glint_correction",
    "glint_correction",
    "l2w_mask",
    "l2w_mask_wave",
    "l2w_mask_threshold",
    "l2w_mask_negative_rhow",
    "l2w_mask_cirrus",
    "l2w_mask_high_toa",
    "s2_target_res",
    "resolved_geometry",
    "output_geotiff",
    "l2r_export_geotiff",
    "l2w_export_geotiff",
    "l2w_parameters",
    "dem_pressure",
]


def parse_scene_spec(spec: str) -> dict:
    """TILE:YYYY-MM-DD selects that day. TILE:YYYY-MM selects the month's first acquisition."""
    tile, _, when = spec.partition(":")
    tile = tile.upper().removeprefix("T")
    if len(tile) != 5 or not tile[:2].isdigit():
        raise ValueError(f"bad tile in {spec!r}")
    digits = when.replace("-", "")
    if len(digits) not in (6, 8) or not digits.isdigit():
        raise ValueError(f"bad date in {spec!r}")
    return {"spec": spec, "tile": tile, "date": digits, "first_in_month": len(digits) == 6}


def plan(scenes: list[dict]) -> list[str]:
    lines = [
        f"Bucket {aqr.BUCKET}, region {aqr.REGION}, unsigned requests, no credentials.",
        "1. List the bucket root with a delimiter: version prefixes.",
        f"2. List {aqr.VERSION_PREFIX} with a delimiter, every page: tile prefixes.",
    ]
    for spec in scenes:
        prefixes = ", ".join(
            f"{aqr.VERSION_PREFIX}T{spec['tile']}/{p}_MSIAQR_{spec['date']}" for p in aqr.PLATFORMS
        )
        rule = "the month's first acquisition" if spec["first_in_month"] else "every product"
        lines.append(f"3. {spec['spec']}: list {prefixes}. Keep {rule}.")
    lines += [
        "4. Per kept object: one HEAD request. Per kept scene: GET the settings text file whole.",
        "5. Per kept GeoTIFF: open the header through GDAL /vsicurl/. No pixel is decoded.",
        f"6. Per tile-date: search {', '.join(ES_ORDER)} on Earth Search for the same tile",
        f"   and day, full items. Compare the {ES_GRID_ASSET} 20 m grid with the product grid.",
        "Writes benchmarks/results/aqr-headers.json and raw files under data/aqr-headers/.",
    ]
    return lines


def header_summary(src) -> dict:
    """What a GeoTIFF header states. Reads no pixel block."""
    return {
        "driver": src.driver,
        "width": src.width,
        "height": src.height,
        "count": src.count,
        "dtypes": list(src.dtypes),
        "nodata": src.nodata,
        "scales": list(src.scales),
        "offsets": list(src.offsets),
        "crs": src.crs.to_string() if src.crs else None,
        "epsg": src.crs.to_epsg() if src.crs else None,
        "transform": [round(v, 6) for v in list(src.transform)[:6]],
        "resolution": list(src.res),
        "block_shapes": [list(shape) for shape in src.block_shapes],
        "overviews": src.overviews(1),
        "image_structure": src.tags(ns="IMAGE_STRUCTURE"),
        "dataset_tags": src.tags(),
        "band_tags": src.tags(1),
        "descriptions": list(src.descriptions),
        "units": list(src.units),
        "mask_flags": [[flag.name for flag in flags] for flags in src.mask_flag_enums],
    }


def grid_comparison(aqr_header: dict, item: dict) -> dict:
    """Compare an aquatic reflectance grid with an Earth Search asset grid from catalog metadata."""
    asset = item.get("assets", {}).get(ES_GRID_ASSET, {})
    transform = asset.get("proj:transform") or item.get("properties", {}).get("proj:transform")
    shape = asset.get("proj:shape") or item.get("properties", {}).get("proj:shape")
    code = (
        asset.get("proj:code")
        or item.get("properties", {}).get("proj:code")
        or (
            f"EPSG:{item['properties']['proj:epsg']}" if "proj:epsg" in item["properties"] else None
        )
    )
    out = {
        "item_id": item.get("id"),
        "asset": ES_GRID_ASSET,
        "es_transform": transform,
        "es_shape": shape,
        "es_crs": code,
        "aqr_transform": aqr_header["transform"],
        "aqr_shape": [aqr_header["height"], aqr_header["width"]],
        "aqr_crs": f"EPSG:{aqr_header['epsg']}" if aqr_header.get("epsg") else aqr_header["crs"],
    }
    if not transform or not shape:
        out["aligned"] = None
        out["reason"] = "The catalog item states no grid for the asset."
        return out
    a, _, c, _, e, f = aqr_header["transform"]
    es_a, _, es_c, _, es_e, es_f = transform[:6]
    out["origin_offset_pixels"] = [round((c - es_c) / es_a, 6), round((f - es_f) / es_e, 6)]
    out["same_pixel_size"] = abs(a - es_a) < 1e-6 and abs(e - es_e) < 1e-6
    out["same_crs"] = out["aqr_crs"] == code
    out["same_shape"] = list(shape) == out["aqr_shape"]
    out["aligned"] = (
        out["same_crs"]
        and out["same_pixel_size"]
        and all(abs(v - round(v)) < 1e-6 for v in out["origin_offset_pixels"])
    )
    return out


def list_all(client, prefix: str, delimiter: str | None, note: str) -> tuple[list, list, list]:
    keys, prefixes, headers = [], [], []
    token = None
    for page in range(1, 1000):
        text, response_headers = client.get_text(
            aqr.list_url(prefix, delimiter, token), f"{note} page {page}"
        )
        headers.append(
            {k: v for k, v in response_headers.items() if k.startswith("x-amz-") and "id" not in k}
        )
        listing = aqr.parse_listing(text)
        keys.extend(listing["keys"])
        prefixes.extend(listing["prefixes"])
        if not listing["truncated"]:
            return keys, prefixes, headers
        token = listing["next_token"]
    raise RuntimeError(f"listing did not end: {prefix}")


def select(spec: dict, scenes: dict[str, dict]) -> list[dict]:
    chosen = sorted(scenes.values(), key=lambda s: (s["sensing"], s["product"]))
    if spec["first_in_month"] and chosen:
        first = chosen[0]["sensing"]
        chosen = [s for s in chosen if s["sensing"] == first]
    return chosen


def es_items(client, tile: str, day: str) -> dict[str, list[dict]]:
    date_text = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    out = {}
    for collection in ES_ORDER:
        body = {
            "collections": [collection],
            "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
            "datetime": f"{date_text}T00:00:00Z/{date_text}T23:59:59Z",
            "limit": 50,
        }
        result = client.post_json(f"{ES_ROOT}/search", body, f"items {collection} {tile} {day}")
        out[collection] = result.get("features", [])
    return out


def probe_scene(client, scene: dict, raw_dir: Path) -> dict:
    import rasterio

    record = {key: scene[key] for key in scene if key != "layers"}
    record["layers"] = {}
    for layer, obj in sorted(scene["layers"].items()):
        url = aqr.object_url(obj["key"])
        head = client.head(url, f"head {layer}")
        entry = dict(obj)
        entry["head"] = {
            "status": head["status"],
            "content_length": head["headers"].get("content-length"),
            "content_type": head["headers"].get("content-type"),
            "etag": (head["headers"].get("etag") or "").strip('"'),
            "last_modified": head["headers"].get("last-modified"),
            "request_charged": head["headers"].get("x-amz-request-charged"),
            "storage_class": head["headers"].get("x-amz-storage-class"),
            "metadata": {k: v for k, v in head["headers"].items() if k.startswith("x-amz-meta-")},
        }
        if obj["key"].endswith(".txt"):
            raw, meta = client.get_bytes(url, f"settings {scene['product']}")
            path = raw_dir / Path(obj["key"]).name
            path.write_bytes(raw)
            settings = aqr.parse_settings(raw.decode(errors="replace"))
            entry["settings"] = {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "lines": len(raw.decode(errors="replace").splitlines()),
                "saved": str(path.relative_to(ROOT)),
                "selected": {k: settings.get(k) for k in SETTINGS_KEYS},
                "all": settings,
                "get": meta,
            }
        else:
            with (
                harness.Timer() as timer,
                rasterio.Env(**GDAL_ENV),
                harness.GdalLogCapture() as capture,
            ):
                with rasterio.open(f"/vsicurl/{url}") as src:
                    entry["header"] = header_summary(src)
                lines = capture.take()
            entry["gdal"] = harness.parse_gdal_log(lines) | {"seconds": timer.seconds}
        record["layers"][layer] = entry
        print(f"  {scene['product']} {layer}: {entry['head']['status']}", flush=True)
    return record


def summarize(records: list[dict], pairs: list[dict], versions: list[str], tiles: list[str]):
    tifs = [
        (scene["product"], layer, entry)
        for scene in records
        for layer, entry in scene["layers"].items()
        if "header" in entry
    ]

    def values(fn):
        return aqr.counter_dict(
            json.dumps(fn(entry["header"]), sort_keys=True) for *_, entry in tifs
        )

    settings = [
        entry["settings"]
        for scene in records
        for entry in scene["layers"].values()
        if "settings" in entry
    ]
    layer_sets = Counter(" ".join(sorted(scene["layers"])) for scene in records)
    zones = Counter(tile[:2] for tile in tiles)
    statuses = Counter(
        entry["head"]["status"] for scene in records for entry in scene["layers"].values()
    )
    charged = Counter(
        str(entry["head"]["request_charged"])
        for scene in records
        for entry in scene["layers"].values()
    )
    return {
        "versions": versions,
        "tile_prefixes": len(tiles),
        "tile_prefixes_by_utm_zone": dict(sorted(zones.items())),
        "scenes_probed": len(records),
        "layer_sets": dict(layer_sets),
        "geotiffs_probed": len(tifs),
        "dtypes": values(lambda h: h["dtypes"]),
        "nodata": values(lambda h: h["nodata"]),
        "scales_offsets": values(lambda h: [h["scales"], h["offsets"]]),
        "crs": values(lambda h: h["crs"]),
        "resolution": values(lambda h: h["resolution"]),
        "shape": values(lambda h: [h["height"], h["width"]]),
        "block_shapes": values(lambda h: h["block_shapes"]),
        "overviews": values(lambda h: h["overviews"]),
        "image_structure": values(lambda h: h["image_structure"]),
        "settings_selected": aqr.counter_dict(
            json.dumps(s["selected"], sort_keys=True) for s in settings
        ),
        "settings_digests": sorted(s["sha256"] for s in settings),
        "head_statuses": aqr.counter_dict(statuses.elements()),
        "request_charged_headers": dict(charged),
        "grid_alignment": [
            {k: p.get(k) for k in ("product", "item_id", "aligned", "origin_offset_pixels")}
            for p in pairs
        ],
        "header_requests": sum(entry["gdal"]["requests"] for *_, entry in tifs),
        "header_bytes_requested": sum(entry["gdal"]["bytes"] for *_, entry in tifs),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--scene", action="append", help="TILE:YYYY-MM-DD or TILE:YYYY-MM")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results/aqr-headers.json")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    args = parser.parse_args(argv)
    specs = [parse_scene_spec(s) for s in (args.scene or DEFAULT_SCENES)]
    for line in plan(specs):
        print(line)
    if args.dry_run:
        return 0

    import rasterio

    measured_at = harness.utc_now()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S%z")
    raw_dir = ROOT / "data" / "aqr-headers" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = harness.Client(pause=0.1)

    _, versions, root_headers = list_all(client, "", "/", "root")
    _, tile_prefixes, _ = list_all(client, aqr.VERSION_PREFIX, "/", "tiles")
    tiles = sorted(p.rstrip("/").rsplit("/", 1)[-1].removeprefix("T") for p in tile_prefixes)
    (raw_dir / "tile-prefixes.json").write_text(json.dumps(tiles))
    print(f"{len(versions)} version prefixes, {len(tiles)} tile prefixes", flush=True)

    records, pairs, selections = [], [], []
    for spec in specs:
        objects = []
        for platform in aqr.PLATFORMS:
            prefix = f"{aqr.VERSION_PREFIX}T{spec['tile']}/{platform}_MSIAQR_{spec['date']}"
            found, _, _ = list_all(client, prefix, None, f"scene {spec['spec']} {platform}")
            objects.extend(found)
        scenes, unparsed = aqr.group_scenes(objects)
        chosen = select(spec, scenes)
        selections.append(
            {
                "spec": spec["spec"],
                "products_listed": sorted(scenes),
                "products_kept": [s["product"] for s in chosen],
                "unparsed_keys": unparsed,
            }
        )
        if not chosen:
            print(f"{spec['spec']}: no aquatic reflectance product", flush=True)
            continue
        days = sorted({s["sensing"][:8] for s in chosen})
        items = {day: es_items(client, spec["tile"], day) for day in days}
        for scene in chosen:
            record = probe_scene(client, scene, raw_dir)
            records.append(record)
            reference = record["layers"].get("B05", {}).get("header")
            day_items = items[scene["sensing"][:8]]
            for collection in ES_ORDER:
                for item in day_items.get(collection, []):
                    product = aqr.parse_product(
                        (item["properties"].get("s2:product_uri") or "").removesuffix(".SAFE")
                    )
                    if not product or product["sensing"] != scene["sensing"]:
                        continue
                    pair = {"product": scene["product"], "collection": collection}
                    pair |= {"es_baseline": product["baseline"], "es_platform": product["platform"]}
                    if reference:
                        pair |= grid_comparison(reference, item)
                    pairs.append(pair)
                    (raw_dir / f"{item['id']}.json").write_text(json.dumps(item))

    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": harness.code_version(),
        "script": "benchmarks/aqr_headers.py",
        "probe": "T1, docs/reviews/2026-10-13-acolite-first-replan.md",
        "machine": harness.machine_info(),
        "endpoints": {
            "bucket": aqr.BUCKET,
            "region": aqr.REGION,
            "endpoint": aqr.ENDPOINT,
            "credentials": "none, unsigned requests",
            "payer": (
                "Bucket owner. Every request was unsigned, so no requester was charged. "
                "A requester-pays bucket refuses unsigned requests."
            ),
            "root_listing_headers": root_headers,
            "earth_search": ES_ROOT,
        },
        "gdal_env": GDAL_ENV,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "scene_specs": [s["spec"] for s in specs],
        "selections": selections,
        "scenes": records,
        "earth_search_pairs": pairs,
        "summary": summarize(records, pairs, versions, tiles),
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "request_log": client.log,
        "requests": aqr.counter_dict(f"{entry['host']} {entry['method']}" for entry in client.log),
        "limitations": [
            "Headers, listings, and settings text only. No pixel was decoded, so masking, value "
            "ranges, and negative values are untested. Probe T4 reads pixels.",
            "GDAL requests and bytes come from its debug log of requested ranges, the first "
            "bytes of each file. They include no decoded block.",
            "Three tile-dates. The layer set, encoding, and settings of other scenes can differ.",
            "Grid alignment compares the Level-2A 20 m grid from catalog metadata, not from the "
            "Level-2A file headers.",
            "Object last-modified times describe the bucket copy, not when USGS processed a scene.",
            "The payer statement rests on unsigned requests succeeding. No price page was read.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n")
    print(f"Wrote {args.output} with {len(records)} scenes and {len(client.log)} requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
