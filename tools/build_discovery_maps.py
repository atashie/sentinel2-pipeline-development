# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy==2.5.3", "pillow==12.3.0", "rasterio==1.5.1"]
# ///
"""Build educational map images from one public Sentinel-2 window.

Run with `uv run tools/build_discovery_maps.py --download` only when authorized.
Without --download, use cached arrays under data/discovery-map. This is a display
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
    (OUTPUT / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    kib = math.ceil(sum(p["bytes"] for p in products.values()) / 1024)
    print(f"Wrote {len(products)} maps, {kib} KiB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download", action="store_true", help="Fetch one bounded public-data crop"
    )
    args = parser.parse_args()
    if args.download:
        download()
    build()
