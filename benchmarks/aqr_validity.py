"""Probe T4: pixel validity of the USGS ACOLITE aquatic reflectance product on the pilot lakes.

Runs only when the user invokes it. Unsigned requests, no credentials. For each pilot tile in the
lower 48 states, the tile stage 2 chose, it lists the product's scenes of 2025 and keeps the
first complete scene of each month. For each kept scene it reads the settings file, then the
window of every pilot lake on that tile from all 11 bands, NDWI, and l2_flags. It joins the
scene to an Earth Search Level-2A item by tile, platform, and sensing start, finding 28, and
reads the same windows from that item's 20 m scene classification. It counts validity per band
and pixel class under rules fixed before the run, src/s2proto/validity.py. It stores counts,
never pixel values. Probe T4 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.

    uv run python benchmarks/aqr_validity.py --dry-run
    uv run python benchmarks/aqr_validity.py
    uv run python benchmarks/aqr_validity.py --tile 17SKU --month 2025-10 --output data/t4.json
    uv run python benchmarks/aqr_validity.py --resummarize benchmarks/results/aqr-validity.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from s2proto import aqr, harness, masks, validity  # noqa: E402

MANIFEST = ROOT / "examples/water-bodies-public-pilot.geojson"
STAGE_2_RESULT = ROOT / "benchmarks/results/lake-extraction.json"
# The tile stage 2 chose for each pilot region in the lower 48, scenes[region].tile in its
# result. Reusing them keeps the frozen cohorts, replan record rule 3. Alaska is outside the
# primary product's scope under decision 0008.
TILES = {
    "tahoe": "10SGJ",
    "lanier": "17SKU",
    "okeechobee": "17RNK",
    "grand-st-marys": "16TGK",
    "washington": "10TET",
}
YEAR = "2025"
MONTHS = [f"{YEAR}-{month:02d}" for month in range(1, 13)]
LAYERS = (*validity.BANDS, "NDWI", "l2_flags")
RESOLUTION = 20
TILE_PIXELS_20M = 5490
ES_ROOT = "https://earth-search.aws.element84.com/v1"
ES_ORDER = ["sentinel-2-c1-l2a", "sentinel-2-l2a"]
GDAL_CACHE_BYTES = 512 * 1024 * 1024
GDAL_ENV = {
    "CPL_DEBUG": "ON",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "GDAL_HTTP_TIMEOUT": "120",
    # rasterio.Env takes the cache in bytes. The environment variable takes megabytes.
    "GDAL_CACHEMAX": GDAL_CACHE_BYTES,
}
SOURCE_FILES = [
    "benchmarks/aqr_validity.py",
    "src/s2proto/validity.py",
    "src/s2proto/aqr.py",
    "src/s2proto/masks.py",
    "src/s2proto/harness.py",
]
SELECTION_RULE = (
    f"For each tile and each month of {YEAR}, list every product scene, keep those holding all "
    f"{len(aqr.OBSERVED_LAYERS)} objects of finding 26, and take the earliest sensing time. Among "
    "products with that sensing time, take the latest generation time. The rule uses names only."
)
JOIN_RULE = (
    "Search Earth Search for the tile and day. Match tile, platform, and sensing start from the "
    "product names, Collection 1 first, then the older collection, finding 28. Prefer an item of "
    "the same processing baseline. Among several, take the latest created time."
)
LIMITATIONS = [
    f"Five tiles and one scene per tile and month of {YEAR}. Earlier years, whose inputs are "
    "mostly original Level-1C baselines, finding 27, are not sampled.",
    "Scenes come from what the product holds. Its cloud screening removes most cloudy "
    "acquisitions, finding 27, so cloud counts describe the scenes it keeps.",
    "The scene classification is a land product with its own errors, claims Q1, Q4, and Q8. "
    "Agreement with it is a comparison, not a validation.",
    "Pixel classes come from NHD polygons, whose shorelines are not observations of a given date.",
    "Counts are pixel observations, summed over scenes. Large lakes dominate pooled shares. "
    "The summary also splits by tile and by size class.",
    "GDAL requests and bytes are byte ranges requested, from its debug log. Laptop over the "
    "internet, outside us-west-2, assumption A25. Times are not production estimates.",
    "No pixel value is stored in the result. Only counts.",
]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1) + "\n")


def source_digests() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def pilot_lakes(region: str) -> list[dict]:
    manifest = json.loads(MANIFEST.read_text())
    return [f for f in manifest["features"] if f["properties"]["region"] == region]


def plan(tiles: dict[str, str], months: list[str]) -> list[str]:
    lines = [
        f"Bucket {aqr.BUCKET}, region {aqr.REGION}, unsigned requests, no credentials.",
        f"Earth Search {ES_ROOT}, collections {', '.join(ES_ORDER)}, unsigned requests.",
        f"Tiles: {', '.join(f'{tile} ({region})' for region, tile in tiles.items())}.",
        f"Months: {months[0]} to {months[-1]}, {len(months)} months.",
        f"1. Per tile and platform: list {aqr.VERSION_PREFIX}T<tile>/<platform>_MSIAQR_{YEAR}.",
        f"2. Selection: {SELECTION_RULE}",
        f"3. Join: {JOIN_RULE}",
        "4. Per kept scene: GET the settings file whole. Read the flag exponents from it.",
        f"5. Per kept scene and pilot lake: read the {RESOLUTION} m window of the lake's three",
        f"   pixel classes, masks version {masks.MASK_VERSION}, from {', '.join(LAYERS)}.",
        "   Read the same window from the joined item's scene classification.",
        "6. Count validity per band and pixel class. Store counts only.",
        "Writes benchmarks/results/aqr-validity.json and raw files under data/aqr-validity/.",
        "Rules and tolerances, fixed before the run:",
    ]
    lines += [f"  {key}: {text}" for key, text in validity.TOLERANCES.items()]
    for region, tile in tiles.items():
        lakes = pilot_lakes(region)
        lines.append(f"  {tile}: {len(lakes)} pilot lakes of region {region}.")
    return lines


def list_all(client, prefix: str, note: str) -> list[dict]:
    keys, token = [], None
    for page in range(1, 1000):
        text, _ = client.get_text(aqr.list_url(prefix, None, token), f"{note} page {page}")
        listing = aqr.parse_listing(text)
        keys.extend(listing["keys"])
        if not listing["truncated"]:
            return keys
        token = listing["next_token"]
    raise RuntimeError(f"listing did not end: {prefix}")


def select_monthly(scenes: dict[str, dict], months: list[str]) -> list[dict]:
    """The selection rule: per month, the earliest complete scene, latest generation first."""
    complete = set(aqr.OBSERVED_LAYERS)
    out = []
    for month in months:
        digits = month.replace("-", "")
        in_month = [s for s in scenes.values() if s["sensing"].startswith(digits)]
        full = [s for s in in_month if set(s["layers"]) == complete]
        entry = {
            "month": month,
            "listed": len(in_month),
            "incomplete": sorted(s["product"] for s in in_month if s not in full),
            "chosen": None,
            "same_sensing": [],
        }
        if full:
            first = min(s["sensing"] for s in full)
            tied = sorted(
                (s for s in full if s["sensing"] == first),
                key=lambda s: (s["generation_time"], s["product"]),
                reverse=True,
            )
            entry["chosen"] = tied[0]
            entry["same_sensing"] = [s["product"] for s in tied[1:]]
        out.append(entry)
    return out


def normalize_item(item: dict, collection: str) -> dict:
    props = item.get("properties", {})
    scl = item.get("assets", {}).get("scl", {})
    return {
        "id": item.get("id"),
        "collection": collection,
        "product_uri": props.get("s2:product_uri"),
        "created": props.get("created"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "scl_href": scl.get("href"),
        "scl_transform": scl.get("proj:transform"),
        "scl_shape": scl.get("proj:shape"),
    }


def es_items(client, tile: str, day: str, raw_dir: Path) -> dict[str, list[dict]]:
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
        features = result.get("features", [])
        write_json(raw_dir / "items" / f"{tile}-{day}-{collection}.json", features)
        out[collection] = [normalize_item(f, collection) for f in features]
    return out


def choose_item(join: dict, items: dict[str, list[dict]]) -> dict | None:
    if not join["joined"]:
        return None
    ids = set(join["joined"]["ids"])
    pool = [i for i in items[join["joined"]["collection"]] if i["id"] in ids]
    return sorted(pool, key=lambda i: (i["created"] or "", i["id"]), reverse=True)[0]


def grid_check(header: dict, expected) -> dict:
    """Rule R1 between one file header and the expected 20 m tile transform."""
    a, _, c, _, e, f = header["transform"]
    offsets = [(c - expected.c) / RESOLUTION, (f - expected.f) / -RESOLUTION]
    out = {
        "epsg": header["epsg"],
        "transform": header["transform"],
        "shape": header["shape"],
        "origin_offset_pixels": [round(v, 9) for v in offsets],
        "same_pixel_size": abs(a - RESOLUTION) < 1e-9 and abs(e + RESOLUTION) < 1e-9,
        "same_shape": header["shape"] == [TILE_PIXELS_20M, TILE_PIXELS_20M],
    }
    out["aligned"] = (
        out["same_pixel_size"]
        and out["same_shape"]
        and all(abs(v) <= validity.GRID_TOLERANCE_PIXELS for v in offsets)
    )
    return out


def header_of(src) -> dict:
    return {
        "epsg": src.crs.to_epsg() if src.crs else None,
        "transform": [round(v, 6) for v in list(src.transform)[:6]],
        "shape": [src.height, src.width],
        "dtype": src.dtypes[0],
        "nodata": src.nodata,
    }


def tile_masks(region: str, tile: str, grid: masks.TileGrid) -> dict[str, dict]:
    """Pixel classes at 20 m for every pilot lake of the region, on the product's grid."""
    out = {}
    for feature in pilot_lakes(region):
        props = feature["properties"]
        polygon = masks.project(feature["geometry"], grid.epsg)
        mask = masks.compute_mask(polygon, grid, RESOLUTION)
        out[props["water_body_id"]] = {
            "mask": mask,
            "meta": {
                "water_body_id": props["water_body_id"],
                "name": props["name"],
                "tier": props["tier"],
                "size_class_m": props["size_class_m"],
                "share_in_tile": round(masks.fraction_inside(polygon, grid.extent()), 6),
                "window": mask.window.as_dict(),
                "counts": mask.counts,
            },
        }
    return out


def gdal_split(lines: list[str]) -> dict[str, dict]:
    product = [line for line in lines if aqr.BUCKET in line]
    other = [line for line in lines if aqr.BUCKET not in line]
    return {"product": harness.parse_gdal_log(product), "scl": harness.parse_gdal_log(other)}


def read_scene(region, tile, entry, items, lakes, raw_dir, client) -> tuple[dict, list[dict]]:
    import rasterio
    from rasterio.windows import Window

    scene = entry["chosen"]
    settings_key = scene["layers"]["settings"]["key"]
    raw, meta = client.get_bytes(aqr.object_url(settings_key), f"settings {scene['product']}")
    (raw_dir / "settings").mkdir(parents=True, exist_ok=True)
    (raw_dir / "settings" / Path(settings_key).name).write_bytes(raw)
    settings = aqr.parse_settings(raw.decode(errors="replace"))
    exponents = validity.flag_exponents(settings)
    join = aqr.join_scene(scene, items, ES_ORDER)
    item = choose_item(join, items)
    info = {
        "region": region,
        "tile": tile,
        "month": entry["month"],
        "product": scene["product"],
        "sensing_time": scene["sensing_time"],
        "baseline": scene["baseline"],
        "generation_time": scene["generation_time"],
        "listed_in_month": entry["listed"],
        "incomplete_in_month": entry["incomplete"],
        "same_sensing_not_chosen": entry["same_sensing"],
        "settings": {
            "key": settings_key,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "flag_exponents": exponents,
            "get": meta,
        },
        "join": {"status": join["status"], "joined": join["joined"], "matches": join["matches"]},
        "scl_item": item,
    }
    records = []
    with (
        harness.Timer() as timer,
        rasterio.Env(**GDAL_ENV),
        harness.GdalLogCapture() as capture,
    ):
        sources = {
            layer: rasterio.open(f"/vsicurl/{aqr.object_url(scene['layers'][layer]['key'])}")
            for layer in LAYERS
        }
        try:
            headers = {layer: header_of(src) for layer, src in sources.items()}
            expected = lakes["grid"].transform(RESOLUTION)
            checks = {layer: grid_check(h, expected) for layer, h in headers.items()}
            info["product_grid"] = {
                "aligned": all(c["aligned"] for c in checks.values()),
                "epsg": sorted({h["epsg"] for h in headers.values()}),
                "dtypes": aqr.counter_dict(h["dtype"] for h in headers.values()),
                "nodata": aqr.counter_dict(h["nodata"] for h in headers.values()),
                "misaligned_layers": [k for k, c in checks.items() if not c["aligned"]],
            }
            scl_src = None
            if item and item["scl_href"]:
                scl_src = rasterio.open(f"/vsicurl/{item['scl_href']}")
                scl_check = grid_check(header_of(scl_src), expected)
                scl_check["same_crs"] = header_of(scl_src)["epsg"] == lakes["grid"].epsg
                scl_check["aligned"] = scl_check["aligned"] and scl_check["same_crs"]
                info["scl_grid"] = scl_check
                if not scl_check["aligned"]:
                    scl_src.close()
                    scl_src = None
            if not info["product_grid"]["aligned"]:
                info["skipped"] = "a product layer is not on the tile's 20 m grid"
                return info, records
            for water_body_id, lake in lakes["lakes"].items():
                mask = lake["mask"]
                if mask.window.empty:
                    continue
                w = mask.window
                window = Window(w.col_off, w.row_off, w.width, w.height)
                arrays = {layer: src.read(1, window=window) for layer, src in sources.items()}
                scl = scl_src.read(1, window=window) if scl_src is not None else None
                counts = validity.class_counts(
                    mask.pixel_class,
                    {band: arrays[band] for band in validity.BANDS},
                    arrays["NDWI"],
                    arrays["l2_flags"],
                    exponents,
                    scl,
                )
                records.append(
                    {
                        "region": region,
                        "tile": tile,
                        "month": entry["month"],
                        "product": scene["product"],
                        "water_body_id": water_body_id,
                        "tier": lake["meta"]["tier"],
                        "size_class_m": lake["meta"]["size_class_m"],
                        "joined": scl is not None,
                        "classes": counts,
                    }
                )
            if scl_src is not None:
                scl_src.close()
        finally:
            for src in sources.values():
                src.close()
        lines = capture.take()
    info["gdal"] = gdal_split(lines)
    info["seconds"] = timer.seconds
    info["lakes_read"] = len(records)
    return info, records


def tables(pooled: dict[str, dict]) -> dict[str, dict]:
    """Shares per pixel class from pooled counts."""
    share = validity.share
    out = {}
    for name, c in pooled.items():
        pixels, joined = c.get("pixels"), c.get("joined_pixels")
        if not pixels:
            out[name] = {"pixels": 0}
            continue
        bands = {
            band: {
                "no_data": share(v["no_data"], pixels),
                "processor_masked": share(v["processor_masked"], joined),
                "negative": share(v["negative"], pixels),
                "above_one": share(v["above_one"], pixels),
            }
            for band, v in c["bands"].items()
        }
        flags = c["flags"]
        row = {
            "pixels": pixels,
            "joined_pixels": joined,
            "bands": bands,
            "ndwi": {k: share(v, pixels) for k, v in c["ndwi"].items()},
            "flags": {
                "no_data": share(flags["no_data"], pixels),
                "not_multiple": share(flags["not_multiple"], pixels),
                "none": share(flags["none"], pixels),
                "bits": {k: share(v, pixels) for k, v in flags["bits"].items()},
                "unknown_bits": share(flags["unknown_bits"], pixels),
            },
            "ndwi_recompute": {
                band: share(v["agree"], v["comparable"]) for band, v in c["ndwi_recompute"].items()
            },
        }
        water = c.get("water")
        if water:
            row["water"] = {
                test: {k: share(v, water["usable"]) for k, v in counts.items()}
                for test, counts in water.items()
                if isinstance(counts, dict)
            }
        cloud = c.get("cloud")
        if cloud:
            row["cloud"] = {
                "scl_cloud": share(cloud["scl_cloud"], joined),
                "scl_cloud_unflagged_of_cloud": share(
                    cloud["scl_cloud_unflagged"], cloud["scl_cloud"]
                ),
                "scl_shadow": share(cloud["scl_shadow"], joined),
                "scl_shadow_unflagged_of_shadow": share(
                    cloud["scl_shadow_unflagged"], cloud["scl_shadow"]
                ),
            }
        out[name] = row
    return out


def size_group(record: dict) -> str:
    return "anchor" if record["tier"] == "large" else f"{record['size_class_m']} m"


def no_data_diagnostic(records: list[dict]) -> dict:
    """Diagnostic added after the run, outside the declared rules: band no-data per scene,
    against the count of pixels carrying ACOLITE's out-of-scene flag in the same record."""
    by_scene: dict[str, dict] = {}
    mismatches = []
    compared = 0
    for record in records:
        for name, counts in record["classes"].items():
            if not counts.get("pixels"):
                continue
            out_of_scene = counts["flags"]["bits"].get("outofscene")
            scene = by_scene.setdefault(
                record["product"], {"out_of_scene_flag": 0, "ndwi_no_data": 0, "bands": {}}
            )
            scene["out_of_scene_flag"] += out_of_scene or 0
            scene["ndwi_no_data"] += counts["ndwi"]["no_data"]
            for band, values in counts["bands"].items():
                compared += 1
                scene["bands"][band] = scene["bands"].get(band, 0) + values["no_data"]
                if values["no_data"] != out_of_scene:
                    mismatches.append(
                        {
                            "product": record["product"],
                            "water_body_id": record["water_body_id"],
                            "class": name,
                            "band": band,
                            "no_data": values["no_data"],
                            "out_of_scene_flag": out_of_scene,
                        }
                    )
    return {
        "note": (
            "Counts per scene-lake record, class, and band. Equal counts do not prove the "
            "same pixels."
        ),
        "comparisons": compared,
        "mismatches": mismatches,
        "scenes_with_no_data": {
            product: values
            for product, values in sorted(by_scene.items())
            if values["out_of_scene_flag"] or any(values["bands"].values())
        },
    }


def summarize(scenes: list[dict], records: list[dict], tile_meta: dict) -> dict:
    read = [s for s in scenes if "skipped" not in s and s.get("lakes_read")]
    pooled = validity.pool(records)
    by_tile = validity.pool(records, key=lambda r: r["tile"])
    by_size = validity.pool(records, key=size_group)
    joined_records = [r for r in records if r["joined"]]
    masked = [
        {
            "product": r["product"],
            "water_body_id": r["water_body_id"],
            "class": name,
            "band": band,
            "processor_masked": v["processor_masked"],
        }
        for r in records
        for name, c in r["classes"].items()
        for band, v in c.get("bands", {}).items()
        if v.get("processor_masked")
    ]
    return {
        "distinct_tiles": len({s["tile"] for s in read}),
        "distinct_tile_dates": len({(s["tile"], s["sensing_time"][:10]) for s in read}),
        "scenes_selected": len(scenes),
        "scenes_read": len(read),
        "scenes_joined": sum(1 for s in read if s.get("scl_item") and "scl_grid" in s),
        "scenes_scl_aligned": sum(1 for s in read if s.get("scl_grid", {}).get("aligned")),
        "join_status": aqr.counter_dict(s["join"]["status"] for s in read),
        "joined_collection": aqr.counter_dict(
            (s["scl_item"] or {}).get("collection") for s in read
        ),
        "scl_same_baseline": sum(1 for s in read if s["join"]["status"].startswith("exact")),
        "months_without_scene": {
            tile: sorted(s["month"] for s in scenes if s["tile"] == tile and not s["product"])
            for tile in sorted({s["tile"] for s in scenes})
        },
        "lakes": len({r["water_body_id"] for r in records}),
        "lakes_outside_tile": sorted(
            lake["water_body_id"]
            for meta in tile_meta.values()
            for lake in meta["lakes"].values()
            if not lake["window"]["height"]
        ),
        "scene_lake_records": len(records),
        "scene_lake_records_joined": len(joined_records),
        "flag_exponents": aqr.counter_dict(
            json.dumps(s["settings"]["flag_exponents"], sort_keys=True) for s in read
        ),
        "settings_digests": len({s["settings"]["sha256"] for s in read}),
        "pooled_counts": pooled.get("all", {}),
        "verdicts": validity.class_verdicts(pooled.get("all", {})),
        "shares": tables(pooled.get("all", {})),
        "shares_by_tile": {tile: tables(c) for tile, c in sorted(by_tile.items())},
        "shares_by_size": {size: tables(c) for size, c in sorted(by_size.items())},
        "verdicts_by_tile": {
            tile: validity.class_verdicts(c) for tile, c in sorted(by_tile.items())
        },
        "processor_masked_cases": masked,
        "no_data_diagnostic": no_data_diagnostic(records),
        "join_multiple": [
            {
                "product": s["product"],
                "matched": [
                    m["id"] for m in s["join"]["matches"][s["join"]["joined"]["collection"]]
                ],
                "chosen": s["scl_item"]["id"],
            }
            for s in read
            if s["join"]["status"].endswith("_multiple")
        ],
        "gdal_product_requests": sum(s["gdal"]["product"]["requests"] for s in read),
        "gdal_product_bytes_requested": sum(s["gdal"]["product"]["bytes"] for s in read),
        "gdal_scl_requests": sum(s["gdal"]["scl"]["requests"] for s in read),
        "gdal_scl_bytes_requested": sum(s["gdal"]["scl"]["bytes"] for s in read),
        "read_seconds": round(sum(s["seconds"] for s in read), 2),
    }


def parse_month(value: str) -> str:
    datetime.strptime(value, "%Y-%m")
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tile", action="append", help="limit to these tiles, for a smoke run")
    parser.add_argument("--month", action="append", type=parse_month, help="YYYY-MM, smoke run")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks/results/aqr-validity.json"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    parser.add_argument("--resummarize", type=Path, help="recompute a result's summary offline")
    args = parser.parse_args(argv)

    if args.resummarize:
        result = json.loads(args.resummarize.read_text())
        result["summary"] = summarize(result["scenes"], result["records"], result["tiles"])
        result["summary_generated_at"] = harness.utc_now()
        result["summary_source_digests"] = source_digests()
        write_json(args.resummarize, result)
        print(f"Resummarized {args.resummarize}")
        return 0

    tiles = {r: t for r, t in TILES.items() if not args.tile or t in args.tile}
    months = args.month or MONTHS
    if not tiles:
        parser.error(f"no tile matches {args.tile}. Tiles: {', '.join(TILES.values())}")
    for line in plan(tiles, months):
        print(line)
    if args.dry_run:
        return 0

    import rasterio

    measured_at = harness.utc_now()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S%z")
    raw_dir = ROOT / "data" / "aqr-validity" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = harness.Client(pause=0.1)
    scenes, records, tile_meta = [], [], {}

    for region, tile in tiles.items():
        objects = []
        for platform in aqr.PLATFORMS:
            prefix = f"{aqr.VERSION_PREFIX}T{tile}/{platform}_MSIAQR_{YEAR}"
            objects.extend(list_all(client, prefix, f"scenes {tile} {platform} {YEAR}"))
        listed, unparsed = aqr.group_scenes(objects)
        selection = select_monthly(listed, months)
        lakes = None
        for entry in selection:
            if entry["chosen"] is None:
                scenes.append({"region": region, "tile": tile, "month": entry["month"]})
                scenes[-1] |= {"product": None, "listed_in_month": entry["listed"]}
                print(f"{tile} {entry['month']}: no complete scene", flush=True)
                continue
            scene = entry["chosen"]
            if lakes is None:
                with rasterio.Env(**GDAL_ENV):
                    key = scene["layers"]["B05"]["key"]
                    with rasterio.open(f"/vsicurl/{aqr.object_url(key)}") as src:
                        header = header_of(src)
                a, _, c, _, e, f = header["transform"]
                grid = masks.TileGrid(header["epsg"], c, f)
                lakes = {"grid": grid, "lakes": tile_masks(region, tile, grid)}
                tile_meta[tile] = {
                    "region": region,
                    "grid": {"epsg": grid.epsg, "x0": grid.x0, "y0": grid.y0},
                    "grid_from": scene["product"],
                    "listed_scenes": len(listed),
                    "unparsed_keys": unparsed,
                    "lakes": {k: v["meta"] for k, v in lakes["lakes"].items()},
                }
            items = es_items(client, tile, scene["sensing"][:8], raw_dir)
            info, found = read_scene(region, tile, entry, items, lakes, raw_dir, client)
            scenes.append(info)
            records.extend(found)
            print(
                f"{tile} {entry['month']} {scene['product']}: {len(found)} lakes, "
                f"join {info['join']['status']}, {info.get('seconds')} s, "
                f"{info.get('gdal', {}).get('product', {}).get('bytes', 0) / 1e6:.1f} MB",
                flush=True,
            )

    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "completed_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": source_digests(),
        "script": "benchmarks/aqr_validity.py",
        "probe": "T4, docs/reviews/2026-10-13-acolite-first-replan.md",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2, assumption A25. "
            "Transfer times include that path."
        ),
        "endpoints": {
            "bucket": aqr.BUCKET,
            "region": aqr.REGION,
            "endpoint": aqr.ENDPOINT,
            "earth_search": ES_ROOT,
            "scl_buckets": sorted(
                {
                    s["scl_item"]["scl_href"].split("/")[2]
                    for s in scenes
                    if s.get("scl_item") and s["scl_item"].get("scl_href")
                }
            ),
            "credentials": "none, unsigned requests",
            "payer": (
                "Bucket owners. Every request was unsigned, so no requester was charged. "
                "A requester-pays bucket refuses unsigned requests."
            ),
        },
        "gdal_env": GDAL_ENV,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "manifest": {
            "path": str(MANIFEST.relative_to(ROOT)),
            "sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        },
        "selection_rule": SELECTION_RULE,
        "join_rule": JOIN_RULE,
        "tolerances": validity.TOLERANCES,
        "mask_parameters": {
            "resolution_m": RESOLUTION,
            "near_land_m": masks.NEAR_LAND_M,
            "mask_version": masks.MASK_VERSION,
        },
        "tiles": tile_meta,
        "scenes": scenes,
        "records": records,
        "summary": summarize(scenes, records, tile_meta),
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "request_log": client.log,
        "requests": aqr.counter_dict(f"{entry['host']} {entry['method']}" for entry in client.log),
        "limitations": LIMITATIONS,
    }
    write_json(args.output, result)
    print(f"Wrote {args.output} with {len(scenes)} scenes and {len(records)} scene-lake records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
