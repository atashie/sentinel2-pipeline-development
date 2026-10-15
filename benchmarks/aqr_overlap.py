"""Probe T7: each option's values for the same pixels in two overlapping tiles.

Runs only when the user invokes it. Unsigned requests, no credentials, no catalog query. Probe T6's
stage 4 plan fixes the lakes in two tiles, the acquisitions, and the primary products. The saved
Level-2A stage 4 catalog holds the Collection 1 item paired with each product. For every pair of
tiles in one UTM zone that share a lake, the probe reads the lake's overlap pixels from both
tiles, for both options. It reports how often the two tiles of one option disagree, and whether
ACOLITE's tiles disagree more or less than Sen2Cor's on the same pixels, under rules fixed before
the run, src/s2proto/overlap.py. It stores statistics, never pixel values.

Decision 0009 keeps the two options standalone. Each option is compared only with itself.

    uv run python benchmarks/aqr_overlap.py --dry-run
    uv run python benchmarks/aqr_overlap.py
    uv run python benchmarks/aqr_overlap.py --pair lanier:16SGC-16SGD --output data/t7.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks")]
import aqr_validity as t4  # noqa: E402

from s2proto import aqr, aqr_pairing, harness, masks, overlap, pairs, validity  # noqa: E402

STAGE4 = ROOT / "data/aqr-workloads/2026-10-14-run/stage4.json"
CATALOG = ROOT / "data/cross-tile-extraction/full-plan.catalog.json"
RESULT = ROOT / "benchmarks/results/aqr-overlap.json"
RESOLUTION = overlap.RESOLUTION
GDAL_ENV = t4.GDAL_ENV
SOURCE_FILES = [
    "benchmarks/aqr_overlap.py",
    "benchmarks/aqr_validity.py",
    "src/s2proto/overlap.py",
    "src/s2proto/pairs.py",
    "src/s2proto/aqr_pairing.py",
    "src/s2proto/validity.py",
    "src/s2proto/aqr.py",
    "src/s2proto/masks.py",
    "src/s2proto/harness.py",
]
LIMITATIONS = [
    "Two acquisitions, 2025-10-15 at Lake Lanier and 2025-10-31 at Lake Okeechobee, and the "
    "lakes of probe T6's stage 4 plan. Pairs across UTM zones are listed and not compared.",
    "Each option is compared with itself. A tile disagreement is a difference in processing, "
    "not an error of either tile, and ranks neither correction, assumption A52.",
    "Overlap pixels sit near tile edges, where each tile's processing has less context. "
    "The result describes those pixels, not tile interiors.",
    "Collection 1 10 m bands are averaged to 20 m and B01 takes its 60 m parent, rule P3. "
    "The same resampling applies to both tiles of a pair.",
    "Pixel classes come from NHD polygons, whose shorelines are not observations of a date.",
    "Pooled statistics are pixel observations summed over pairs. Lake Okeechobee dominates "
    "them. The summary also splits by pair, and pixels are not independent.",
    "GDAL requests and bytes are byte ranges requested, from its debug log. Laptop over the "
    "internet, outside us-west-2, assumption A25. Times are not production estimates.",
    "No pixel value is stored. Only counts and statistics.",
]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digests() -> dict[str, str]:
    return {name: digest(ROOT / name) for name in SOURCE_FILES}


def load_inputs() -> tuple[list[dict], dict, dict]:
    """T6 stage 4 scenes with their Collection 1 items, and the lakes by id."""
    stage4 = json.loads(STAGE4.read_text())
    catalog = json.loads(CATALOG.read_text())
    items = {item["id"]: item for group in catalog.values() for item in group}
    scenes = []
    for s in stage4["plan"]["scenes"]:
        paired = s["item"]["properties"]["aqr:paired_item"]
        c1 = items[paired]
        scenes.append(
            {
                "region": s["region"],
                "tile": s["tile"],
                "product": s["item"]["id"],
                "product_folder": s["item"]["assets"]["red"]["href"].rsplit("_", 1)[0],
                "c1": c1,
                "epsg": int(c1["properties"]["proj:epsg"]),
                "members": sorted(s["members"]),
            }
        )
    lakes = {f["id"]: f for f in stage4["plan"]["lakes"]}
    return scenes, lakes, stage4


def plan_lines(same: list[dict], cross: list[dict]) -> list[str]:
    lines = ["Probe T7 rules, fixed before any pixel is read:"]
    lines += [f"  {key}: {text}" for key, text in overlap.TOLERANCES.items()]
    lines.append(f"Inputs: {STAGE4.relative_to(ROOT)} sha256 {digest(STAGE4)}")
    lines.append(f"        {CATALOG.relative_to(ROOT)} sha256 {digest(CATALOG)}")
    lines.append(
        f"Buckets: {aqr.BUCKET} and the Collection 1 bucket, {aqr.REGION}, unsigned, no "
        "credentials. No catalog query."
    )
    lines.append(f"Same-zone pairs compared: {len(same)}")
    lines += [f"  {p['region']} {p['tile_a']}-{p['tile_b']}: {', '.join(p['lakes'])}" for p in same]
    lines.append(f"Cross-zone pairs listed, not compared: {len(cross)}")
    lines += [
        f"  {p['region']} {p['tile_a']}-{p['tile_b']}: {', '.join(p['lakes'])}" for p in cross
    ]
    return lines


def c1_dn(source, asset: dict, window: tuple[int, int, int, int]):
    """Stored Collection 1 integers on a 20 m window, P3 resampling, and validity."""
    from rasterio.windows import Window

    row, col, height, width = window
    resolution = int(asset["proj:transform"][0])
    if resolution == 20:
        raw = source.read(1, window=Window(col, row, width, height))
        return raw.astype("float64"), raw != pairs.C1_NODATA
    if resolution == 10:
        raw = source.read(1, window=Window(col * 2, row * 2, width * 2, height * 2))
        return pairs.block_mean_10m(raw)
    r0, c0, h, w = pairs.window_60m(row, col, height, width)
    raw = source.read(1, window=Window(c0, r0, w, h))
    return pairs.parent_60m(raw, row, col, height, width)


def scale_offset(asset: dict) -> tuple[float, float]:
    band = (asset.get("raster:bands") or [{}])[0]
    return float(band.get("scale", 1.0)), float(band.get("offset", 0.0))


def layer_check(header: dict, grid: masks.TileGrid, resolution: int) -> bool:
    a, _, c, _, e, f = header["transform"]
    return (
        header["epsg"] == grid.epsg
        and abs(a - resolution) < 1e-9
        and abs(e + resolution) < 1e-9
        and abs((c - grid.x0) / resolution) <= overlap.GRID_TOLERANCE_PIXELS
        and abs((grid.y0 - f) / resolution) <= overlap.GRID_TOLERANCE_PIXELS
    )


class Accumulator:
    def __init__(self):
        self.strata: dict[tuple, pairs.Moments] = {}
        self.flags: dict[tuple, list[int]] = {}

    def add(self, key: tuple, a, b) -> None:
        if key not in self.strata:
            self.strata[key] = pairs.Moments()
        self.strata[key].add(a, b)

    def flag(self, key: tuple, differ: int, total: int) -> None:
        counts = self.flags.setdefault(key, [0, 0])
        counts[0] += differ
        counts[1] += total


def tile_summary(m: pairs.Moments) -> dict:
    out = pairs.summarize(m)
    if out["n"]:
        out["mean_units"] = {
            "tile_a": out["mean_units"]["product"],
            "tile_b": out["mean_units"]["c1"],
        }
        out.pop("share_negative")
        out["verdict"] = overlap.verdict(m.n, m.disagree)
    return out


def read_pair(pair: dict, scenes: dict, lakes: dict, acc: Accumulator) -> tuple[dict, list]:
    import numpy as np
    import rasterio

    a, b = scenes[pair["tile_a"]], scenes[pair["tile_b"]]
    grids = {t: masks.TileGrid.from_item(s["c1"]) for t, s in ((a["tile"], a), (b["tile"], b))}
    ga, gb = grids[a["tile"]], grids[b["tile"]]
    info = {key: pair[key] for key in ("region", "tile_a", "tile_b", "lakes")}
    info["products"] = [a["product"], b["product"]]
    info["c1_items"] = [a["c1"]["id"], b["c1"]["id"]]
    offset = overlap.origin_offset(ga, gb)
    whole = overlap.whole_offset(offset)
    info["offset_pixels_20m"] = list(offset)
    records: list[dict] = []
    if ga.epsg != gb.epsg or whole is None:
        info["skipped"] = "tile grids differ, rule O2"
        return info, records
    b01_sen2cor = whole[0] % 3 == 0 and whole[1] % 3 == 0
    info["b01_sen2cor_compared"] = b01_sen2cor
    band_keys = {band: aqr_pairing.C1_BANDS[band] for band in validity.BANDS}
    declared = {
        band: [scale_offset(s["c1"]["assets"][key]) for s in (a, b)]
        for band, key in band_keys.items()
    }
    if any(x != y for x, y in declared.values()):
        info["skipped"] = "Collection 1 scale or offset differ between tiles, rule O4"
        return info, records
    label = f"{pair['region']} {pair['tile_a']}-{pair['tile_b']}"
    with (
        harness.Timer() as timer,
        rasterio.Env(**GDAL_ENV),
        harness.GdalLogCapture() as capture,
    ):
        product = {
            t: {
                layer: rasterio.open(f"/vsicurl/{s['product_folder']}_{layer}.tif")
                for layer in (*validity.BANDS, "l2_flags")
            }
            for t, s in ((a["tile"], a), (b["tile"], b))
        }
        c1 = {
            t: {
                key: rasterio.open(f"/vsicurl/{s['c1']['assets'][key]['href']}")
                for key in [*band_keys.values(), "scl"]
            }
            for t, s in ((a["tile"], a), (b["tile"], b))
        }
        try:
            failed = []
            for t, grid in grids.items():
                for layer, src in product[t].items():
                    if not layer_check(t4.header_of(src), grid, RESOLUTION):
                        failed.append(f"{t} product {layer}")
                for key, src in c1[t].items():
                    resolution = int(scenes[t]["c1"]["assets"][key]["proj:transform"][0])
                    if not layer_check(t4.header_of(src), grid, resolution):
                        failed.append(f"{t} c1 {key}")
            info["grid_checks"] = {"aligned": not failed, "misaligned": failed}
            if failed:
                info["skipped"] = "a layer is off its tile grid, rule O2"
                return info, records
            for water_body_id in pair["lakes"]:
                feature = lakes[water_body_id]
                polygon = masks.project(feature["geometry"], ga.epsg)
                mask = masks.compute_mask(polygon, ga, RESOLUTION)
                w = mask.window
                if w.empty:
                    continue
                clipped = overlap.overlap_windows((w.row_off, w.col_off, w.height, w.width), whole)
                if clipped is None:
                    continue
                win_a, win_b = clipped
                r, c = win_a[0] - w.row_off, win_a[1] - w.col_off
                pixel_class = mask.pixel_class[r : r + win_a[2], c : c + win_a[3]]
                classes = pairs.class_masks(pixel_class)
                if not any(m.any() for m in classes.values()):
                    continue
                windows = {a["tile"]: win_a, b["tile"]: win_b}

                def window(t, windows=windows):
                    from rasterio.windows import Window

                    row, col, height, width = windows[t]
                    return Window(col, row, width, height)

                decoded = {}
                for t in windows:
                    flags = product[t]["l2_flags"].read(1, window=window(t))
                    value, missing, not_multiple = validity.decode_flags(flags)
                    decoded[t] = (value, ~missing & ~not_multiple)
                scl = {t: c1[t]["scl"].read(1, window=window(t)) for t in windows}
                ta, tb = a["tile"], b["tile"]
                clear = {
                    "acolite": (decoded[ta][0] == 0)
                    & decoded[ta][1]
                    & (decoded[tb][0] == 0)
                    & decoded[tb][1],
                    "sen2cor": (scl[ta] == pairs.SCL_WATER) & (scl[tb] == pairs.SCL_WATER),
                }
                flags_valid = {
                    "acolite": decoded[ta][1] & decoded[tb][1],
                    "sen2cor": (scl[ta] != 0) & (scl[tb] != 0),
                }
                flags_differ = {
                    "acolite": decoded[ta][0] != decoded[tb][0],
                    "sen2cor": scl[ta] != scl[tb],
                }
                for name, in_class in classes.items():
                    for option in overlap.OPTIONS:
                        valid = in_class & flags_valid[option]
                        acc.flag(
                            (option, name),
                            int((valid & flags_differ[option]).sum()),
                            int(valid.sum()),
                        )
                summary: dict = {}
                for band, key in band_keys.items():
                    values, comparable = {}, {}
                    raw = {t: product[t][band].read(1, window=window(t)) for t in windows}
                    values["acolite"] = {t: raw[t].astype("float64") for t in windows}
                    comparable["acolite"] = (raw[ta] != pairs.NODATA) & (raw[tb] != pairs.NODATA)
                    scale, offset_value = declared[band][0]
                    factor, shift = (
                        round(scale * pairs.UNIT, 9),
                        round(offset_value * pairs.UNIT, 6),
                    )
                    s2 = {
                        t: c1_dn(c1[t][key], scenes[t]["c1"]["assets"][key], windows[t])
                        for t in windows
                    }
                    values["sen2cor"] = {t: s2[t][0] * factor + shift for t in windows}
                    comparable["sen2cor"] = s2[ta][1] & s2[tb][1]
                    if band == "B01" and not b01_sen2cor:
                        comparable["sen2cor"] = np.zeros_like(comparable["sen2cor"])
                    shared = comparable["acolite"] & comparable["sen2cor"]
                    both_clear = clear["acolite"] & clear["sen2cor"]
                    for name, in_class in classes.items():
                        for option in overlap.OPTIONS:
                            own = comparable[option] & in_class
                            subsets = {
                                "all": own,
                                "own_clear_water": own & clear[option],
                                "shared": shared & in_class,
                                "shared_clear_water": shared & in_class & both_clear,
                            }
                            for subset, selected in subsets.items():
                                va = values[option][ta][selected]
                                vb = values[option][tb][selected]
                                for group in ("all", label):
                                    acc.add((option, subset, name, band, group), va, vb)
                                if subset in ("all", "shared"):
                                    summary.setdefault(option, {}).setdefault(
                                        subset, {}
                                    ).setdefault(name, {})[band] = pairs.record_summary(va, vb)
                records.append(
                    {
                        "region": pair["region"],
                        "tile_a": ta,
                        "tile_b": tb,
                        "water_body_id": water_body_id,
                        "window_a": list(win_a),
                        "window_b": list(win_b),
                        "pixels": {name: int(m.sum()) for name, m in classes.items()},
                        "strata": summary,
                    }
                )
        finally:
            for group in (*product.values(), *c1.values()):
                for src in group.values():
                    src.close()
        lines = capture.take()
    product_lines = [line for line in lines if aqr.BUCKET in line]
    other = [line for line in lines if aqr.BUCKET not in line]
    info["gdal"] = {
        "product": harness.parse_gdal_log(product_lines),
        "c1": harness.parse_gdal_log(other),
    }
    info["seconds"] = timer.seconds
    info["lakes_read"] = len(records)
    return info, records


def summarize(infos: list[dict], records: list[dict], acc: Accumulator) -> dict:
    pooled: dict = {}
    by_pair: dict = {}
    for (option, subset, name, band, group), moments in sorted(acc.strata.items()):
        table = pooled if group == "all" else by_pair.setdefault(group, {})
        table.setdefault(option, {}).setdefault(subset, {}).setdefault(name, {})[band] = (
            tile_summary(moments)
        )
    widening: dict = {}
    for subset in ("shared", "shared_clear_water"):
        for name in pairs.CLASSES:
            for band in validity.BANDS:
                cells = [
                    acc.strata.get((option, subset, name, band, "all"))
                    for option in overlap.OPTIONS
                ]
                shares = [
                    m.disagree / m.n if m is not None and m.n >= pairs.MIN_RECORD_PIXELS else None
                    for m in cells
                ]
                widening.setdefault(subset, {}).setdefault(name, {})[band] = {
                    "acolite_share_beyond": None if shares[0] is None else round(shares[0], 4),
                    "sen2cor_share_beyond": None if shares[1] is None else round(shares[1], 4),
                    "result": overlap.widening(*shares),
                }
    flags = {
        option: {
            name: {
                "pixels": acc.flags.get((option, name), [0, 0])[1],
                "share_differ": round(
                    acc.flags[(option, name)][0] / acc.flags[(option, name)][1], 4
                )
                if acc.flags.get((option, name), [0, 0])[1]
                else None,
            }
            for name in pairs.CLASSES
        }
        for option in overlap.OPTIONS
    }
    return {
        "pairs_compared": sum(1 for i in infos if "skipped" not in i),
        "pairs_skipped": [i for i in infos if "skipped" in i],
        "pair_lake_records": len(records),
        "lakes": sorted({r["water_body_id"] for r in records}),
        "pooled": pooled,
        "by_pair": by_pair,
        "widening": widening,
        "flag_diagnostic": flags,
        "gdal_product_requests": sum(
            i.get("gdal", {}).get("product", {}).get("requests", 0) for i in infos
        ),
        "gdal_product_bytes_requested": sum(
            i.get("gdal", {}).get("product", {}).get("bytes", 0) for i in infos
        ),
        "gdal_c1_requests": sum(i.get("gdal", {}).get("c1", {}).get("requests", 0) for i in infos),
        "gdal_c1_bytes_requested": sum(
            i.get("gdal", {}).get("c1", {}).get("bytes", 0) for i in infos
        ),
        "read_seconds": round(sum(i.get("seconds", 0) for i in infos), 1),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--pair", action="append", help="REGION:TILEA-TILEB, for a smoke run")
    parser.add_argument("--lake", action="append", help="limit to these lakes, for a smoke run")
    parser.add_argument("--output", type=Path, default=RESULT)
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    args = parser.parse_args(argv)

    scenes, lakes, stage4 = load_inputs()
    same, cross = overlap.zone_pairs(scenes)
    if args.pair:
        same = [p for p in same if f"{p['region']}:{p['tile_a']}-{p['tile_b']}" in args.pair]
    if args.lake:
        same = [dict(p, lakes=[x for x in p["lakes"] if x in args.lake]) for p in same]
        same = [p for p in same if p["lakes"]]
    if not same:
        parser.error("no same-zone pair matches the selection")
    lines = plan_lines(same, cross)
    for line in lines:
        print(line)
    if args.dry_run:
        return 0

    import rasterio

    measured_at = harness.utc_now()
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%S%z")
    raw_dir = ROOT / "data" / "aqr-overlap" / stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "plan.txt").write_text(
        "\n".join([measured_at, *(f"{v}  {k}" for k, v in source_digests().items()), *lines]) + "\n"
    )
    by_tile = {s["tile"]: s for s in scenes}
    acc = Accumulator()
    infos, records = [], []
    for pair in same:
        info, found = read_pair(pair, by_tile, lakes, acc)
        infos.append(info)
        records.extend(found)
        print(
            f"{pair['region']} {pair['tile_a']}-{pair['tile_b']}: {len(found)} lakes, "
            f"{info.get('skipped', 'compared')}, {info.get('seconds')} s, "
            f"{info.get('gdal', {}).get('product', {}).get('bytes', 0) / 1e6:.1f} MB product, "
            f"{info.get('gdal', {}).get('c1', {}).get('bytes', 0) / 1e6:.1f} MB Collection 1",
            flush=True,
        )
    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "completed_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": source_digests(),
        "script": "benchmarks/aqr_overlap.py",
        "probe": "T7, docs/reviews/2026-10-13-acolite-first-replan.md",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2, assumption A25. "
            "Transfer times include that path."
        ),
        "endpoints": {
            "bucket": aqr.BUCKET,
            "region": aqr.REGION,
            "endpoint": aqr.ENDPOINT,
            "c1_buckets": sorted({s["c1"]["assets"]["scl"]["href"].split("/")[2] for s in scenes}),
            "catalog_queries": "none. Items come from the saved stage 4 catalogs.",
            "credentials": "none, unsigned requests",
            "payer": (
                "Bucket owners. Every request was unsigned, so no requester was charged. "
                "A requester-pays bucket refuses unsigned requests."
            ),
        },
        "gdal_env": GDAL_ENV,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "inputs": {
            "stage4_plan": {"path": str(STAGE4.relative_to(ROOT)), "sha256": digest(STAGE4)},
            "stage4_plan_internal_sha256": stage4["plan"]["sha256"],
            "c1_catalog": {"path": str(CATALOG.relative_to(ROOT)), "sha256": digest(CATALOG)},
        },
        "band_map": aqr_pairing.C1_BANDS,
        "tolerances": overlap.TOLERANCES,
        "mask_parameters": {
            "resolution_m": RESOLUTION,
            "near_land_m": masks.NEAR_LAND_M,
            "mask_version": masks.MASK_VERSION,
        },
        "cross_zone_pairs": cross,
        "pairs": infos,
        "records": records,
        "summary": summarize(infos, records, acc),
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "limitations": LIMITATIONS,
    }
    write_json(args.output, result)
    print(f"Wrote {args.output} with {len(infos)} pairs and {len(records)} pair-lake records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
