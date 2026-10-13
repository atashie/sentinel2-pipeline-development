# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pillow==12.3.0", "rasterio==1.5.1"]
# ///
"""Build educational map images from one public Sentinel-2 window.

Run with `uv run tools/build_discovery_maps.py --download` only when authorized.
`--download-aqr` reads the same window from the USGS aquatic reflectance product of the same
pass, only when authorized. The owner authorized that one crop on 2026-10-13.
Without either flag, use cached arrays under data/discovery-map. This is a display
example, not a processing benchmark or a water-quality product.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import transform
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "discovery-map"
OUTPUT = ROOT / "docs" / "assets" / "discovery"
ITEM_ID = "S2B_T17SKU_20251015T162249_L2A"
ITEM_URL = (
    "https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/" + ITEM_ID
)
BANDS = ("red", "green", "blue", "nir")
SIZE = 800
CENTER = (-83.94, 34.28)
AQR_HOST = "https://usgs-wma-sentinel-2-aqr-acolite-dsf.s3.us-west-2.amazonaws.com/"
AQR_PRODUCT = "S2B_MSIAQR_20251015T162149_N0511_R040_T17SKU_20251015T195355"
AQR_LAYERS = ("B04", "B03", "B02", "NDWI", "l2_flags")
# USGS documents int16 values scaled by 10,000 with no-data -32768. The file headers state
# scale 1 and offset 0, so the scale comes from the documentation, not the file.
AQR_SCALE = 1e-4
AQR_NODATA = -32768


def download() -> None:
    """Read four 10 m bands and one 20 m classification window using HTTP ranges."""
    CACHE.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ITEM_URL, timeout=30) as response:
        raw = response.read()
    item = json.loads(raw)
    assert item["properties"]["storage:requester_pays"] is False
    (CACHE / "item.json").write_bytes(raw)
    arrays = {}
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MAX_RETRY=0,
        GDAL_HTTP_TIMEOUT=30,
        CPL_CURL_VERBOSE=True,
    ):
        for name in (*BANDS, "scl"):
            asset = item["assets"][name]
            if not asset["href"].startswith(
                "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/"
            ):
                raise ValueError("Unexpected asset host")
            with rasterio.open(asset["href"]) as src:
                if name == "red":
                    x, y = transform("EPSG:4326", src.crs, [CENTER[0]], [CENTER[1]])
                    row, col = src.index(x[0], y[0])
                    # Even offsets align the 10 m and 20 m grid cell edges.
                    window = Window(
                        (col - SIZE // 2) // 2 * 2, (row - SIZE // 2) // 2 * 2, SIZE, SIZE
                    )
                    grid = src.window_transform(window)
                    crs = src.crs.to_string()
                scl = name == "scl"
                expected = 20 if scl else 10
                assert src.res == (expected, expected)
                if not scl:
                    assert src.window_transform(window) == grid
                read_window = (
                    Window(window.col_off / 2, window.row_off / 2, SIZE / 2, SIZE / 2)
                    if scl
                    else window
                )
                arrays[name] = src.read(
                    1,
                    window=read_window,
                    out_shape=(SIZE, SIZE),
                    resampling=Resampling.nearest,
                )
                assert arrays[name].shape == (SIZE, SIZE)
    np.savez_compressed(CACHE / "pixels.npz", **arrays)
    (CACHE / "read.json").write_text(
        json.dumps(
            {
                "retrieved_at": datetime.now(UTC).isoformat(),
                "catalog_bytes": len(raw),
                "crs": crs,
                "transform": list(grid)[:6],
                "window": [window.col_off, window.row_off, SIZE, SIZE],
            },
            indent=2,
        )
        + "\n"
    )


def download_aqr() -> None:
    """Read the map window at 20 m from the aquatic reflectance product of the same pass."""
    read = json.loads((CACHE / "read.json").read_text())
    col, row = read["window"][0], read["window"][1]
    if col % 2 or row % 2:
        raise ValueError("The 10 m window must start on a 20 m cell edge")
    window = Window(col // 2, row // 2, SIZE // 2, SIZE // 2)
    arrays, files = {}, {}
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MAX_RETRY=0,
        GDAL_HTTP_TIMEOUT=30,
        CPL_CURL_VERBOSE=True,
    ):
        for layer in AQR_LAYERS:
            url = f"{AQR_HOST}version_01/T17SKU/{AQR_PRODUCT}_{layer}.tif"
            with rasterio.open(url) as src:
                assert src.res == (20.0, 20.0) and src.crs.to_string() == read["crs"]
                expected = list(read["transform"])
                expected[0], expected[4] = 20.0, -20.0
                grid = src.window_transform(window)
                assert [round(v, 6) for v in list(grid)[:6]] == expected, "grids differ"
                arrays[layer] = src.read(1, window=window)
                files[layer] = {
                    "href": url,
                    "dtype": src.dtypes[0],
                    "nodata": src.nodata,
                    "header_scale": src.scales[0],
                    "header_offset": src.offsets[0],
                }
    np.savez_compressed(CACHE / "aqr-pixels.npz", **arrays)
    (CACHE / "aqr-read.json").write_text(
        json.dumps(
            {
                "retrieved_at": datetime.now(UTC).isoformat(),
                "product": AQR_PRODUCT,
                "window_20m": [window.col_off, window.row_off, SIZE // 2, SIZE // 2],
                "files": files,
            },
            indent=2,
        )
        + "\n"
    )


def palette(values: np.ndarray, colors: list[str]) -> np.ndarray:
    """Interpolate a fixed -1 to +1 legend. Never fit colors to this image."""
    rgb = np.array([tuple(bytes.fromhex(c)) for c in colors])
    positions = np.linspace(-1, 1, len(rgb))
    return np.stack([np.interp(values, positions, rgb[:, c]) for c in range(3)], axis=-1)


def build() -> None:
    item = json.loads((CACHE / "item.json").read_text())
    read = json.loads((CACHE / "read.json").read_text())
    with np.load(CACHE / "pixels.npz") as archive:
        raw = {name: archive[name] for name in (*BANDS, "scl")}
    valid = np.isin(raw["scl"], [4, 5, 6, 7])
    bands = {}
    for name in BANDS:
        meta = item["assets"][name]["raster:bands"][0]
        valid &= raw[name] != meta["nodata"]
        bands[name] = raw[name].astype("float32") * meta["scale"] + meta["offset"]

    def rgb(names, upper):
        return (
            np.clip(np.stack([bands[n] for n in names], axis=-1) / upper, 0, 1) ** (1 / 2.2) * 255
        )

    def index(a, b):
        top, bottom = bands[a], bands[b]
        # Near-infrared over clear water sits at the offset floor, so a fifth of the water
        # pixels fall slightly below zero. Keep them. Only a zero denominator is unusable.
        usable = valid & (top + bottom > 1e-6)
        values = np.zeros(top.shape, dtype="float32")
        np.divide(top - bottom, top + bottom, out=values, where=usable)
        return np.clip(values, -1, 1), usable

    ndvi, vi_valid = index("nir", "red")
    ndwi, wi_valid = index("green", "nir")
    views = {
        "true-color": (rgb(["red", "green", "blue"], 0.3), valid),
        "false-color": (rgb(["nir", "red", "green"], [0.5, 0.3, 0.3]), valid),
        "red": (rgb(["red"] * 3, 0.3), valid),
        "nir": (rgb(["nir"] * 3, 0.5), valid),
        "ndvi": (palette(ndvi, ["183c58", "a3bbc5", "e9dfbd", "83a560", "245641"]), vi_valid),
        "ndwi": (palette(ndwi, ["9c6d40", "d7bc8c", "eee9dc", "68b8c4", "15556f"]), wi_valid),
    }
    aqr = None
    if (CACHE / "aqr-pixels.npz").exists():
        aqr = json.loads((CACHE / "aqr-read.json").read_text())
        with np.load(CACHE / "aqr-pixels.npz") as archive:
            delivered = {name: archive[name] for name in AQR_LAYERS}
        # Each 20 m cell becomes 2 x 2 display pixels, so both views share one extent.
        delivered = {k: np.repeat(np.repeat(v, 2, axis=0), 2, axis=1) for k, v in delivered.items()}
        present = np.ones((SIZE, SIZE), dtype=bool)
        for name in ("B04", "B03", "B02"):
            present &= delivered[name] != AQR_NODATA
        if np.any(delivered["l2_flags"] % 10000):
            raise ValueError("Flag values are not multiples of 10,000")
        flags = delivered["l2_flags"] // 10000
        stretch = np.stack(
            [delivered[n].astype("float32") * AQR_SCALE for n in ("B04", "B03", "B02")], axis=-1
        )
        aqr_rgb = np.clip(stretch / 0.3, 0, 1) ** (1 / 2.2) * 255
        views["aqr-true-color"] = (aqr_rgb, present)
        views["aqr-water-flag"] = (aqr_rgb.copy(), present & (flags == 0))
        aqr["flag_counts_20m"] = {
            str(int(k)): int(v) // 4
            for k, v in zip(*np.unique(flags, return_counts=True), strict=True)
        }
        aqr["present_fraction"] = float(present.mean())
    OUTPUT.mkdir(parents=True, exist_ok=True)
    products = {}
    for name, (pixels, mask) in views.items():
        pixels[~mask] = (221, 225, 226)
        path = OUTPUT / f"{name}.png"
        Image.fromarray(np.rint(pixels).astype("uint8")).save(path, optimize=True)
        products[name] = {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "valid_fraction": float(mask.mean()),
        }
    a, b, c, d, e, f = read["transform"]
    x0, y0 = c, f
    assert b == d == 0 and a == 10 and e == -10
    bounds = [x0, y0 - SIZE * 10, x0 + SIZE * 10, y0]
    manifest = {
        "purpose": "Illustrative band views, not a benchmark or water-quality estimate",
        "place": "Lake Lanier, Georgia",
        "item_id": item["id"],
        "item_url": ITEM_URL,
        "product_uri": item["properties"]["s2:product_uri"],
        "sensing_time": item["properties"]["datetime"],
        "collection": item["collection"],
        "region": "us-west-2",
        "payer": "Public unsigned reads. Item declares requester pays false.",
        "attribution": "Contains modified Copernicus Sentinel data (2025), served by Element 84.",
        "license_url": "https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice",
        **read,
        "bounds": bounds,
        "width": SIZE,
        "height": SIZE,
        "pixel_size_m": 10,
        "assets": {name: item["assets"][name] for name in (*BANDS, "scl")},
        "calibration": "Apply asset scale and offset once before display or indices.",
        "display": (
            "RGB and red: 0 to 0.3 reflectance. NIR: 0 to 0.5. Gamma 2.2. "
            "Fixed index range -1 to 1."
        ),
        "index_formulas": {"ndvi": "(nir-red)/(nir+red)", "ndwi": "(green-nir)/(green+nir)"},
        "quality": (
            "Show SCL 4,5,6,7 only. Nearest-neighbor expansion from 20 m. Other pixels are gray."
        ),
        "index_validity": (
            "Keep negative inputs. Exclude denominators <= 0.000001. Clip each index to -1..1."
        ),
        "limitations": [
            "One scene and crop, chosen for low scene cloud cover. No field validation.",
            "Illustrative screening does not guarantee cloud-free or artifact-free pixels.",
            "Bands retain their native grid. No tile mosaic or reflectance resampling.",
            "Display stretches and indices show spectral contrast, not concentrations.",
            "Small index denominators can exaggerate minor band differences. "
            "Display clipping also flattens extremes. The cause of visible texture is unverified.",
            "No performance measurements. GDAL transfer logs can be saved locally from stderr.",
        ],
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256((CACHE / "pixels.npz").read_bytes()).hexdigest(),
        "images": products,
    }
    if aqr is not None:
        manifest["aquatic_reflectance"] = {
            **aqr,
            "bucket": "usgs-wma-sentinel-2-aqr-acolite-dsf",
            "region": "us-west-2",
            "payer": "Public unsigned reads. The bucket owner pays.",
            "attribution": (
                "Contains modified Copernicus Sentinel data (2025), processed with ACOLITE "
                "by the U.S. Geological Survey."
            ),
            "calibration": "Stored integers times 0.0001, from the USGS documentation. "
            "The file headers state scale 1 and offset 0.",
            "display": "Red, green, and blue at 0 to 0.3 reflectance, gamma 2.2, as above. "
            "Each 20 m cell is drawn as 2 x 2 display pixels.",
            "flags": "l2_flags holds the ACOLITE flag integer times 10,000 in this crop. "
            "aqr-water-flag shows pixels whose flag integer is 0. Others are gray.",
            "input_sha256": hashlib.sha256((CACHE / "aqr-pixels.npz").read_bytes()).hexdigest(),
            "limitations": [
                "One crop of one scene. Not probe T4, which measures validity on the pilot lakes.",
                "The flag interpretation rests on the settings file's flag exponents.",
            ],
        }
    (OUTPUT / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    kib = math.ceil(sum(p["bytes"] for p in products.values()) / 1024)
    print(f"Wrote {len(products)} maps, {kib} KiB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Fetch one bounded public-data crop"
    )
    parser.add_argument(
        "--download-aqr",
        action="store_true",
        help="Fetch the same window from the USGS aquatic reflectance product",
    )
    args = parser.parse_args()
    if args.download:
        download()
    if args.download_aqr:
        download_aqr()
    build()
