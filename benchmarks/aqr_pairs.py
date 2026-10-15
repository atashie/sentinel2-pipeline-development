"""Probe T5: paired values of the two standalone options on the same pixels.

Runs only when the user invokes it. Unsigned requests, no credentials. It takes the 59 scenes
probe T4 read, benchmarks/results/aqr-validity.json, and pairs each primary product with the
Collection 1 Level-2A item of the same datastrip, src/s2proto/aqr_pairing.py. For each pilot lake
it reads the product's 11 bands and flags layer, and the same pixels of the item's 11 bands and
scene classification. It reports where the two corrections differ per band, pixel class, and
quality subset, under rules fixed before the run, src/s2proto/pairs.py. It stores statistics,
never pixel values. Probe T5 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.

Decision 0009 keeps the two options standalone. The pairing serves this comparison only.

    uv run python benchmarks/aqr_pairs.py --dry-run
    uv run python benchmarks/aqr_pairs.py
    uv run python benchmarks/aqr_pairs.py --tile 17SKU --month 2025-10 --output data/t5.json
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
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks")]
import aqr_validity as t4  # noqa: E402

from s2proto import aqr, aqr_pairing, harness, masks, pairs, validity  # noqa: E402

T4_RESULT = ROOT / "benchmarks/results/aqr-validity.json"
ES_ROOT = t4.ES_ROOT
L1C = "sentinel-2-l1c"
C1 = "sentinel-2-c1-l2a"
RESOLUTION = 20
GDAL_ENV = t4.GDAL_ENV
SOURCE_FILES = [
    "benchmarks/aqr_pairs.py",
    "benchmarks/aqr_validity.py",
    "src/s2proto/pairs.py",
    "src/s2proto/aqr_pairing.py",
    "src/s2proto/validity.py",
    "src/s2proto/aqr.py",
    "src/s2proto/masks.py",
    "src/s2proto/harness.py",
]
LIMITATIONS = [
    "The 59 scenes are probe T4's: five tiles, one scene per tile and month of 2025, chosen "
    "from what the primary product holds. Its cloud screening removes most cloudy scenes.",
    "Neither product is a reference. A difference is not an error in either. No in situ "
    "observation enters, and the comparison ranks neither correction, assumption A52.",
    "The primary product averages its 10 m bands to 20 m. This probe averages the Collection 1 "
    "10 m bands over the same four pixels. B01 takes the containing 60 m pixel. Both are "
    "declared choices, rule P3, and add their own difference.",
    "Pixel classes come from NHD polygons, whose shorelines are not observations of a given date.",
    "Pooled statistics are pixel observations summed over scenes. Large lakes dominate them. "
    "The summary also splits by tile and size and reports the spread of per-record medians.",
    "Quantiles come from integer histograms of 1e-04 bins, clipped at plus or minus 0.5. "
    "The clipped count is reported per stratum.",
    "GDAL requests and bytes are byte ranges requested, from its debug log. Laptop over the "
    "internet, outside us-west-2, assumption A25. Times are not production estimates.",
    "No pixel value is stored. Only counts and statistics.",
]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1) + "\n")


def source_digests() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def t4_scenes(path: Path = T4_RESULT) -> tuple[list[dict], dict]:
    result = json.loads(path.read_text())
    scenes = [
        s
        for s in result["scenes"]
        if s.get("product") and not s.get("skipped") and s.get("lakes_read")
    ]
    return scenes, result["tiles"]


def layer_url(scene: dict, layer: str) -> str:
    folder = scene["settings"]["key"].rsplit("/", 1)[0]
    return aqr.object_url(f"{folder}/{scene['product']}_{layer}.tif")


def plan(scenes: list[dict]) -> list[str]:
    tiles = Counter(s["tile"] for s in scenes)
    lines = [
        f"Bucket {aqr.BUCKET}, region {aqr.REGION}, unsigned requests, no credentials.",
        f"Earth Search {ES_ROOT}, collections {L1C} and {C1}, unsigned requests.",
        f"Scenes: {len(scenes)} from probe T4, {T4_RESULT.relative_to(ROOT)}.",
        "  " + ", ".join(f"{tile} {count}" for tile, count in sorted(tiles.items())) + ".",
        "1. Per scene: search Earth Search for the tile and day in both collections.",
        "2. Pair the product with the Collection 1 item of the same datastrip, rule P1.",
        "3. Check every Collection 1 header against the product grid, rule P2.",
        f"4. Per pilot lake: read the {RESOLUTION} m window of the lake's three pixel classes,",
        f"   masks version {masks.MASK_VERSION}, from the product's bands",
        f"   {', '.join(validity.BANDS)} and l2_flags.",
        "   Read the same pixels of the item's 11 bands and scene classification,",
        "   10 m windows twice the size and 60 m windows that contain them.",
        "5. Accumulate differences per band, pixel class, and quality subset. Store statistics.",
        "Writes benchmarks/results/aqr-pairs.json and raw files under data/aqr-pairs/.",
        "Rules and tolerances, fixed before the run:",
    ]
    lines += [f"  {key}: {text}" for key, text in pairs.TOLERANCES.items()]
    return lines


def search(client, collection: str, tile: str, day: str, raw_dir: Path) -> list[dict]:
    date_text = f"{day[:4]}-{day[4:6]}-{day[6:8]}"
    body = {
        "collections": [collection],
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "datetime": f"{date_text}T00:00:00Z/{date_text}T23:59:59Z",
        "limit": 50,
    }
    result = client.post_json(f"{ES_ROOT}/search", body, f"items {collection} {tile} {day}")
    features = result.get("features", [])
    write_json(raw_dir / "items" / f"{tile}-{day}-{collection}.json", features)
    return features


def origin_offsets(header: dict, grid: masks.TileGrid, resolution: int) -> dict:
    a, _, c, _, e, f = header["transform"]
    offsets = [(c - grid.x0) / resolution, (grid.y0 - f) / resolution]
    aligned = (
        header["epsg"] == grid.epsg
        and abs(a - resolution) < 1e-9
        and abs(e + resolution) < 1e-9
        and all(abs(v) <= validity.GRID_TOLERANCE_PIXELS for v in offsets)
    )
    return {"resolution": resolution, "origin_offset_pixels": offsets, "aligned": aligned}


def scale_offset(asset: dict) -> tuple[float, float]:
    band = (asset.get("raster:bands") or [{}])[0]
    return float(band.get("scale", 1.0)), float(band.get("offset", 0.0))


def size_group(meta: dict) -> str:
    return "anchor" if meta["tier"] == "large" else f"{meta['size_class_m']} m"


class Accumulator:
    def __init__(self):
        self.strata: dict[tuple, pairs.Moments] = {}

    def get(self, kind: str, group: str, band: str, name: str, quality: str) -> pairs.Moments:
        key = (kind, group, band, name, quality)
        if key not in self.strata:
            self.strata[key] = pairs.Moments(values=kind == "all")
        return self.strata[key]

    def table(self, kind: str) -> dict:
        out: dict = {}
        for (k, group, band, name, quality), moments in sorted(self.strata.items()):
            if k != kind:
                continue
            out.setdefault(group, {}).setdefault(quality, {}).setdefault(name, {})[band] = (
                pairs.summarize(moments)
            )
        return out


def c1_values(sources, assets, band: str, w, scl_shape) -> tuple:
    """Collection 1 values of one band on the product's 20 m window, in units, and validity."""
    from rasterio.windows import Window

    key = aqr_pairing.C1_BANDS[band]
    scale, offset = scale_offset(assets[key])
    resolution = assets[key]["resolution"]
    if resolution == 20:
        raw = sources[key].read(1, window=Window(w.col_off, w.row_off, w.width, w.height))
        values, valid = raw.astype("float64"), raw != pairs.C1_NODATA
    elif resolution == 10:
        raw = sources[key].read(
            1, window=Window(w.col_off * 2, w.row_off * 2, w.width * 2, w.height * 2)
        )
        values, valid = pairs.block_mean_10m(raw)
    else:
        r0, c0, h, wd = pairs.window_60m(w.row_off, w.col_off, w.height, w.width)
        raw = sources[key].read(1, window=Window(c0, r0, wd, h))
        values, valid = pairs.parent_60m(raw, w.row_off, w.col_off, w.height, w.width)
    if values.shape != scl_shape:
        raise ValueError(f"{band} window shape {values.shape} differs from {scl_shape}")
    return (values * scale + offset) * pairs.UNIT, valid


def read_scene(scene, l1c_items, c1_items, lakes, acc) -> tuple[dict, list]:
    import numpy as np
    import rasterio
    from rasterio.windows import Window

    parsed = aqr.parse_product(scene["product"])
    pairing = aqr_pairing.pair_product(
        {"product": scene["product"], "tile": parsed["tile"], "platform": parsed["platform"]},
        l1c_items,
        c1_items,
    )
    info = {
        key: scene[key]
        for key in ("region", "tile", "month", "product", "sensing_time", "baseline")
    }
    info["pairing"] = pairing
    records: list[dict] = []
    if pairing["c1_item"] is None:
        info["skipped"] = f"no pair, {pairing['status']}"
        return info, records
    item = next(i for i in c1_items if i["id"] == pairing["c1_item"])
    props = item["properties"]
    grid = lakes["grid"]
    assets = {}
    for key in [*aqr_pairing.C1_BANDS.values(), "scl"]:
        asset = dict(item["assets"][key])
        asset["resolution"] = int(asset["proj:transform"][0])
        assets[key] = asset
    info["c1"] = {
        "item": item["id"],
        "datastrip_id": props.get("s2:datastrip_id"),
        "product_uri": props.get("s2:product_uri"),
        "processing_baseline": props.get("s2:processing_baseline"),
        "created": props.get("created"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "boa_offset_applied": props.get("earthsearch:boa_offset_applied"),
        "declared_scale_offset": {
            band: scale_offset(assets[key]) for band, key in aqr_pairing.C1_BANDS.items()
        },
        "bucket": assets["scl"]["href"].split("/")[2],
    }
    diag: dict[str, list] = {"B11": [], "B12": []}
    with (
        harness.Timer() as timer,
        rasterio.Env(**GDAL_ENV),
        harness.GdalLogCapture() as capture,
    ):
        product = {
            layer: rasterio.open(f"/vsicurl/{layer_url(scene, layer)}")
            for layer in (*validity.BANDS, "l2_flags")
        }
        c1 = {key: rasterio.open(f"/vsicurl/{a['href']}") for key, a in assets.items()}
        try:
            checks = {
                key: origin_offsets(t4.header_of(src), grid, assets[key]["resolution"])
                for key, src in c1.items()
            }
            checks.update(
                {
                    f"product_{layer}": origin_offsets(t4.header_of(src), grid, RESOLUTION)
                    for layer, src in product.items()
                }
            )
            info["grid_checks"] = {
                "aligned": all(c["aligned"] for c in checks.values()),
                "misaligned": sorted(k for k, c in checks.items() if not c["aligned"]),
            }
            if not info["grid_checks"]["aligned"]:
                info["skipped"] = "a header is off the product grid, rule P2"
                return info, records
            for water_body_id, lake in lakes["lakes"].items():
                mask = lake["mask"]
                if mask.window.empty:
                    continue
                w = mask.window
                window = Window(w.col_off, w.row_off, w.width, w.height)
                flags = product["l2_flags"].read(1, window=window)
                decoded, missing, not_multiple = validity.decode_flags(flags)
                scl = c1["scl"].read(1, window=window)
                clear_water = (decoded == 0) & ~missing & ~not_multiple & (scl == pairs.SCL_WATER)
                classes = pairs.class_masks(mask.pixel_class)
                meta = lake["meta"]
                groups = (("all", "all"), ("tile", scene["tile"]), ("size", size_group(meta)))
                summary: dict = {}
                for band in validity.BANDS:
                    a_raw = product[band].read(1, window=window)
                    a = a_raw.astype("float64")
                    s, s_valid = c1_values(c1, assets, band, w, scl.shape)
                    comparable = (a_raw != pairs.NODATA) & s_valid
                    for name, in_class in classes.items():
                        for quality, extra in (("all", None), ("both_clear_water", clear_water)):
                            selected = comparable & in_class
                            if extra is not None:
                                selected = selected & extra
                            av, sv = a[selected], s[selected]
                            for kind, group in groups:
                                acc.get(kind, group, band, name, quality).add(av, sv)
                            summary.setdefault(name, {}).setdefault(quality, {})[band] = (
                                pairs.record_summary(av, sv)
                            )
                    if band in diag:
                        key = aqr_pairing.C1_BANDS[band]
                        raw = c1[key].read(1, window=window)
                        water = classes["interior"] & (scl == pairs.SCL_WATER) & (raw != 0)
                        diag[band].append(raw[water])
                records.append(
                    {
                        "region": scene["region"],
                        "tile": scene["tile"],
                        "month": scene["month"],
                        "product": scene["product"],
                        "c1_item": item["id"],
                        "water_body_id": water_body_id,
                        "tier": meta["tier"],
                        "size_class_m": meta["size_class_m"],
                        "strata": summary,
                    }
                )
        finally:
            for src in [*product.values(), *c1.values()]:
                src.close()
        lines = capture.take()
    info["offset_diagnostic"] = {}
    for band, parts in diag.items():
        values = np.concatenate(parts) if parts else np.array([])
        info["offset_diagnostic"][band] = {
            "interior_scl_water_pixels": int(values.size),
            "stored_p01": float(np.percentile(values, 1)) if values.size else None,
            "stored_p50": float(np.percentile(values, 50)) if values.size else None,
        }
    product_lines = [line for line in lines if aqr.BUCKET in line]
    other = [line for line in lines if aqr.BUCKET not in line]
    info["gdal"] = {
        "product": harness.parse_gdal_log(product_lines),
        "c1": harness.parse_gdal_log(other),
    }
    info["seconds"] = timer.seconds
    info["lakes_read"] = len(records)
    return info, records


def spreads(records: list[dict]) -> dict:
    out: dict = {}
    for name in pairs.CLASSES:
        for quality in pairs.QUALITIES:
            for band in validity.BANDS:
                medians = [
                    r["strata"][name][quality][band]["median"]
                    for r in records
                    if r["strata"].get(name, {}).get(quality, {}).get(band, {}).get("n", 0)
                    >= pairs.MIN_RECORD_PIXELS
                ]
                out.setdefault(name, {}).setdefault(quality, {})[band] = pairs.spread(medians)
    return out


def verdicts(pooled: dict) -> dict:
    out: dict = {}
    for quality, by_class in pooled.items():
        for name, by_band in by_class.items():
            out.setdefault(quality, {})[name] = {
                "agree": sorted(b for b, s in by_band.items() if s.get("verdict") == "agree"),
                "differs": sorted(b for b, s in by_band.items() if s.get("verdict") == "differs"),
                "no_pixels": sorted(b for b, s in by_band.items() if not s.get("n")),
            }
    return out


def summarize(scenes: list[dict], records: list[dict], acc: Accumulator) -> dict:
    read = [s for s in scenes if s.get("lakes_read")]
    pooled = acc.table("all").get("all", {})
    return {
        "scenes_selected": len(scenes),
        "scenes_paired": sum(1 for s in scenes if s["pairing"].get("c1_item")),
        "scenes_read": len(read),
        "pairing_status": aqr.counter_dict(s["pairing"]["status"] for s in scenes),
        "skipped": {s["product"]: s["skipped"] for s in scenes if s.get("skipped")},
        "distinct_tiles": len({s["tile"] for s in read}),
        "distinct_tile_dates": len({(s["tile"], s["sensing_time"][:10]) for s in read}),
        "lakes": len({r["water_body_id"] for r in records}),
        "scene_lake_records": len(records),
        "c1_buckets": aqr.counter_dict(s["c1"]["bucket"] for s in read),
        "declared_scale_offset": aqr.counter_dict(
            json.dumps(s["c1"]["declared_scale_offset"]["B04"]) for s in read
        ),
        "boa_offset_applied": aqr.counter_dict(s["c1"]["boa_offset_applied"] for s in read),
        "pooled": pooled,
        "verdicts": verdicts(pooled),
        "by_tile": acc.table("tile"),
        "by_size": acc.table("size"),
        "record_median_spread": spreads(records),
        "offset_diagnostic": {s["product"]: s["offset_diagnostic"] for s in read},
        "gdal_product_requests": sum(s["gdal"]["product"]["requests"] for s in read),
        "gdal_product_bytes_requested": sum(s["gdal"]["product"]["bytes"] for s in read),
        "gdal_c1_requests": sum(s["gdal"]["c1"]["requests"] for s in read),
        "gdal_c1_bytes_requested": sum(s["gdal"]["c1"]["bytes"] for s in read),
        "read_seconds": round(sum(s["seconds"] for s in read), 2),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tile", action="append", help="limit to these tiles, for a smoke run")
    parser.add_argument("--month", action="append", help="YYYY-MM, for a smoke run")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results/aqr-pairs.json")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    args = parser.parse_args(argv)

    scenes, tiles = t4_scenes()
    scenes = [
        s
        for s in scenes
        if (not args.tile or s["tile"] in args.tile)
        and (not args.month or s["month"] in args.month)
    ]
    if not scenes:
        parser.error("no T4 scene matches the selection")
    for line in plan(scenes):
        print(line)
    if args.dry_run:
        return 0

    import rasterio

    measured_at = harness.utc_now()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S%z")
    raw_dir = ROOT / "data" / "aqr-pairs" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "plan.txt").write_text(
        "\n".join([measured_at, *(f"{v}  {k}" for k, v in source_digests().items()), *plan(scenes)])
        + "\n"
    )
    client = harness.Client(pause=0.1)
    acc = Accumulator()
    infos, records, lake_sets = [], [], {}
    for scene in scenes:
        tile = scene["tile"]
        if tile not in lake_sets:
            meta = tiles[tile]["grid"]
            grid = masks.TileGrid(meta["epsg"], meta["x0"], meta["y0"])
            lake_sets[tile] = {"grid": grid, "lakes": t4.tile_masks(scene["region"], tile, grid)}
        day = scene["product"].split("_")[2][:8]
        l1c_items = search(client, L1C, tile, day, raw_dir)
        c1_items = search(client, C1, tile, day, raw_dir)
        info, found = read_scene(scene, l1c_items, c1_items, lake_sets[tile], acc)
        infos.append(info)
        records.extend(found)
        print(
            f"{tile} {scene['month']} {scene['product']}: pair {info['pairing']['status']} "
            f"{info['pairing'].get('c1_item')}, {len(found)} lakes, {info.get('seconds')} s, "
            f"{info.get('gdal', {}).get('c1', {}).get('bytes', 0) / 1e6:.1f} MB from Collection 1",
            flush=True,
        )

    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "completed_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": source_digests(),
        "script": "benchmarks/aqr_pairs.py",
        "probe": "T5, docs/reviews/2026-10-13-acolite-first-replan.md",
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
            "earth_search_collections": [L1C, C1],
            "c1_buckets": sorted({i["c1"]["bucket"] for i in infos if i.get("c1")}),
            "credentials": "none, unsigned requests",
            "payer": (
                "Bucket owners. Every request was unsigned, so no requester was charged. "
                "A requester-pays bucket refuses unsigned requests."
            ),
        },
        "gdal_env": GDAL_ENV,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "t4_result": {
            "path": str(T4_RESULT.relative_to(ROOT)),
            "sha256": hashlib.sha256(T4_RESULT.read_bytes()).hexdigest(),
        },
        "manifest": {
            "path": str(t4.MANIFEST.relative_to(ROOT)),
            "sha256": hashlib.sha256(t4.MANIFEST.read_bytes()).hexdigest(),
        },
        "band_map": aqr_pairing.C1_BANDS,
        "tolerances": pairs.TOLERANCES,
        "mask_parameters": {
            "resolution_m": RESOLUTION,
            "near_land_m": masks.NEAR_LAND_M,
            "mask_version": masks.MASK_VERSION,
        },
        "scenes": infos,
        "records": records,
        "summary": summarize(infos, records, acc),
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "request_log": client.log,
        "requests": aqr.counter_dict(f"{e['host']} {e['method']}" for e in client.log),
        "limitations": LIMITATIONS,
    }
    write_json(args.output, result)
    print(f"Wrote {args.output} with {len(infos)} scenes and {len(records)} scene-lake records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
