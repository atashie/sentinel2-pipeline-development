"""Fixture tests for the stage 2 lake extraction script. Synthetic tile, no network."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pyproj
import pytest
import rasterio
import shapely
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from s2proto import masks

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lake_extraction", ROOT / "benchmarks" / "lake_extraction.py"
)
lake_extraction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lake_extraction)

EPSG = 32617
X0, Y0 = 600000.0, 3800000.0
GRID = masks.TileGrid(EPSG, X0, Y0, 240, 240)
BANDS = {"red": 10, "nir": 10, "swir16": 20, "scl": 20, "coastal": 60}


def lonlat(geometry):
    transformer = pyproj.Transformer.from_crs(EPSG, 4326, always_xy=True)

    def to_lonlat(coords):
        lon, lat = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([lon, lat])

    return shapely.transform(geometry, to_lonlat)


def feature(water_body_id, polygon, size_class, tier="pilot", region="fixture"):
    geometry = lonlat(polygon)
    return {
        "type": "Feature",
        "bbox": list(geometry.bounds),
        "geometry": mapping(geometry),
        "properties": {
            "water_body_id": water_body_id,
            "name": water_body_id,
            "region": region,
            "tier": tier,
            "size_class_m": size_class,
            "width_m": polygon.area**0.5,
            "area_m2": polygon.area,
        },
    }


def write_band(path, resolution, seed, dtype="uint16"):
    size = 2400 // resolution
    rng = np.random.default_rng(seed)
    high = 12 if dtype == "uint8" else 10000
    data = rng.integers(1, high, size=(size, size), dtype=dtype)
    data[:2, :2] = 0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=1,
        dtype=dtype,
        crs=f"EPSG:{EPSG}",
        transform=from_origin(X0, Y0, resolution, resolution),
        nodata=0,
        tiled=True,
        blockxsize=16,
        blockysize=16,
        compress="deflate",
    ) as dataset:
        dataset.write(data, 1)
    return data


def make_item(directory, tile="17SKU", cloud=1.0, created="2025-10-15T21:53:41Z", footprint=None):
    """A Collection 1 style item whose assets are local GeoTIFFs."""
    footprint = footprint if footprint is not None else GRID.extent()
    assets = {}
    for key, resolution in BANDS.items():
        size = 2400 // resolution
        assets[key] = {
            "href": str(directory / f"{key}.tif"),
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "gsd": resolution,
            "proj:shape": [size, size],
            "proj:transform": [resolution, 0, X0, 0, -resolution, Y0],
            "raster:bands": [{"nodata": 0, "data_type": "uint8" if key == "scl" else "uint16"}],
        }
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "stac_extensions": ["https://stac-extensions.github.io/projection/v1.1.0/schema.json"],
        "id": f"S2B_T{tile}_{created[:10].replace('-', '')}_L2A",
        "collection": "sentinel-2-c1-l2a",
        "geometry": mapping(lonlat(footprint)),
        "bbox": list(lonlat(footprint).bounds),
        "properties": {
            "datetime": "2025-10-15T16:33:46Z",
            "created": created,
            "proj:epsg": EPSG,
            "grid:code": f"MGRS-{tile}",
            "eo:cloud_cover": cloud,
            "s2:product_uri": "S2B_MSIL2A_x.SAFE",
            "s2:processing_baseline": "05.11",
        },
        "links": [],
        "assets": assets,
    }


@pytest.fixture(scope="module")
def fixture_scene(tmp_path_factory):
    directory = tmp_path_factory.mktemp("scene")
    data = {}
    for index, (key, resolution) in enumerate(BANDS.items()):
        data[key] = write_band(
            directory / f"{key}.tif", resolution, index + 1, "uint8" if key == "scl" else "uint16"
        )
    item = make_item(directory)
    (directory / "item.json").write_text(json.dumps(item))
    lakes = [
        feature("lake-a", box(X0 + 503, Y0 - 1004, X0 + 550, Y0 - 957), 30),
        feature("lake-b", box(X0 + 1002, Y0 - 1006, X0 + 1008, Y0 - 1000), 10),
        feature("lake-c", box(X0 + 100, Y0 - 2300, X0 + 2300, Y0 - 100), 1000, tier="large"),
    ]
    manifest = {"type": "FeatureCollection", "features": lakes}
    (directory / "manifest.geojson").write_text(json.dumps(manifest))
    return {"dir": directory, "item": item, "lakes": lakes, "data": data}


def test_load_lakes_filters_and_labels(fixture_scene):
    path = fixture_scene["dir"] / "manifest.geojson"
    assert [lake["properties"]["water_body_id"] for lake in lake_extraction.load_lakes(path)] == [
        "lake-a",
        "lake-b",
        "lake-c",
    ]
    assert len(lake_extraction.load_lakes(path, tiers=["large"])) == 1
    assert len(lake_extraction.load_lakes(path, lake_ids=["lake-b"])) == 1
    assert lake_extraction.load_lakes(path, regions=["nowhere"]) == []
    lakes = lake_extraction.load_lakes(path)
    assert [lake_extraction.size_label(lake) for lake in lakes] == ["30 m", "10 m", "anchor"]
    bbox = lake_extraction.lakes_bbox(lakes)
    assert bbox[0] < bbox[2] and bbox[1] < bbox[3]
    runs = lake_extraction.plan_runs(lakes, lake_extraction.METHODS, 2)
    assert len(runs) == 3 * 4 * 2
    assert runs[0]["method"] == "naive-clip" and runs[-1]["repetition"] == 2


def test_lake_placement_and_scene_choice(fixture_scene):
    lakes = fixture_scene["lakes"]
    full = fixture_scene["item"]
    placement = lake_extraction.lake_placement(lakes[0], full)
    assert placement["in_tile"] == 1.0 and placement["in_footprint"] == 1.0
    east_grid = masks.TileGrid(EPSG, X0 + 1200, Y0, 240, 240)
    east = make_item(fixture_scene["dir"], tile="17SKV", footprint=east_grid.extent())
    for asset in east["assets"].values():
        asset["proj:transform"][2] = X0 + 1200
    half = lake_extraction.lake_placement(lakes[2], east)
    assert half["in_tile"] == pytest.approx(0.5, abs=0.01)
    partial = make_item(fixture_scene["dir"], cloud=0.1, footprint=box(X0, Y0 - 2400, X0 + 900, Y0))
    cloudier = make_item(fixture_scene["dir"], cloud=40.0, created="2025-10-16T00:00:00Z")
    scene = lake_extraction.choose_scene([east, partial, full, cloudier], lakes)
    assert scene["tile"] == "17SKU"
    assert scene["item"]["properties"]["eo:cloud_cover"] == 1.0
    assert [c["tile"] for c in scene["candidates"]] == ["17SKU", "17SKV"]
    assert scene["candidates"][0]["lakes_fully_in_tile"] == 3
    assert "holds 3 of 3 lakes" in scene["note"]
    scene = lake_extraction.choose_scene([cloudier, full], lakes)
    assert scene["item"]["properties"]["eo:cloud_cover"] == 1.0
    assert lake_extraction.choose_scene([], lakes)["item"] is None
    trimmed = lake_extraction.trim_item(full)
    assert trimmed["grid_code"] == "MGRS-17SKU" and trimmed["epsg"] == EPSG


def test_resolve_assets_skips_what_is_not_on_the_grid(fixture_scene):
    item = json.loads(json.dumps(fixture_scene["item"]))
    item["assets"]["cloud"] = {"href": "s3://bucket/x.jp2", "type": "image/jp2"}
    item["assets"]["snow"] = {"href": "https://bucket/x.jp2", "type": "image/jp2"}
    item["assets"]["aot"] = {
        "href": "https://bucket/aot.tif",
        "type": "image/tiff",
        "proj:shape": [80, 80],
        "proj:transform": [30, 0, X0, 0, -30, Y0],
    }
    resolved = lake_extraction.resolve_assets(
        item, ["red", "scl", "cloud", "snow", "aot", "wvp"], GRID
    )
    assert [a["key"] for a in resolved["assets"]] == ["red", "scl"]
    assert resolved["assets"][1]["resolution"] == 20 and resolved["assets"][1]["dtype"] == "uint8"
    assert resolved["missing"] == ["wvp"]
    reasons = {s["key"]: s["reason"] for s in resolved["skipped"]}
    assert "scheme s3" in reasons["cloud"]
    assert "not GeoTIFF" in reasons["snow"]
    assert "not 10, 20, or 60" in reasons["aot"]


def prepare(fixture_scene, tmp_path, lake_id):
    lake = next(x for x in fixture_scene["lakes"] if x["properties"]["water_body_id"] == lake_id)
    spec = {
        "water_body_id": lake_id,
        "geometry": lake["geometry"],
        "polygon_sha256": lake_extraction.polygon_digest(lake),
        "grid": {"epsg": EPSG, "x0": X0, "y0": Y0, "width_10m": 240, "height_10m": 240},
        "resolutions": [10, 20, 60],
        "mask_paths": {
            str(r): str(tmp_path / "masks" / f"{lake_id}-{r}m.npz") for r in (10, 20, 60)
        },
        "index_paths": {
            str(r): str(tmp_path / "index" / f"{lake_id}-{r}m.npz") for r in (10, 20, 60)
        },
    }
    return spec, lake_extraction.prepare_worker(spec)


def test_prepare_worker_writes_masks_and_counts(fixture_scene, tmp_path):
    spec, result = prepare(fixture_scene, tmp_path, "lake-a")
    assert result["fraction_in_tile"] == 1.0
    assert set(result["resolutions"]) == {"10", "20", "60"}
    ten = result["resolutions"]["10"]
    assert ten["counts"]["interior"] == 16 and ten["counts"]["shoreline"] == 14
    assert ten["coverage_area_relative_error"] < 1e-9
    assert ten["mask_file_bytes"] > 0 and ten["index_file_bytes"] > 0
    assert Path(spec["mask_paths"]["60"]).exists() and Path(spec["index_paths"]["60"]).exists()
    assert result["peak_rss_bytes"] > 0 and result["wall_seconds"] > 0
    _, tiny = prepare(fixture_scene, tmp_path, "lake-b")
    assert all(r["counts"]["interior"] == 0 for r in tiny["resolutions"].values())
    assert all(r["counts"]["shoreline"] == 1 for r in tiny["resolutions"].values())


def extraction_spec(fixture_scene, tmp_path, lake_id, method, prepared):
    lake = next(x for x in fixture_scene["lakes"] if x["properties"]["water_body_id"] == lake_id)
    item = fixture_scene["item"]
    assets = lake_extraction.resolve_assets(item, list(BANDS), GRID)["assets"]
    return {
        "water_body_id": lake_id,
        "region": "fixture",
        "size_label": lake_extraction.size_label(lake),
        "method": method,
        "repetition": 1,
        "tile": "17SKU",
        "item_id": item["id"],
        "item_path": str(fixture_scene["dir"] / "item.json"),
        "grid": prepared["grid"],
        "geometry": lake["geometry"],
        "assets": assets,
        "mask_paths": prepared["mask_paths"],
        "index_paths": prepared["index_paths"],
        "log_path": str(tmp_path / f"{lake_id}-{method}.gdal.log"),
    }


@pytest.mark.parametrize("lake_id", ["lake-a", "lake-b"])
def test_four_methods_extract_identical_values(fixture_scene, tmp_path, lake_id):
    spec, prepared = prepare(fixture_scene, tmp_path, lake_id)
    results = {}
    for method in lake_extraction.METHODS:
        results[method] = lake_extraction.extract_worker(
            extraction_spec(fixture_scene, tmp_path, lake_id, method, spec)
        )
    for method, result in results.items():
        assert result["totals"]["band_errors"] == 0, (method, result["bands"])
        assert result["totals"]["bands"] == 5
        assert result["wall_seconds"] > 0 and result["setup"]["seconds"] >= 0
        assert Path(spec_log := tmp_path / f"{lake_id}-{method}.gdal.log").exists(), spec_log
    reference = {b["key"]: b for b in results["raster-mask"]["bands"]}
    for method in ("index-lists", "lazy-stack"):
        for band in results[method]["bands"]:
            if band["key"].startswith("stack-"):
                assert band["grid_matches"] is True
                continue
            assert band["digest_all"] == reference[band["key"]]["digest_all"], (method, band)
            assert band["counts"] == reference[band["key"]]["counts"]
            assert band["window"] == reference[band["key"]]["window"]
            assert band["pixels_extracted"] == reference[band["key"]]["pixels_extracted"]
    differences = 0
    for band in results["naive-clip"]["bands"]:
        counts = prepared["resolutions"][str(band["resolution"])]["counts"]
        differs = bool(counts["naive_only"] or counts["classes_only"])
        differences += differs
        assert (band["digest_all"] != reference[band["key"]]["digest_wet"]) == differs
        assert band["counts"]["naive"] == counts["naive"]
        assert band["output_bytes"] == counts["naive"] * lake_extraction.NAIVE_RECORD_BYTES
    # GDAL's all-touched rasterization marks a neighbour of the tiny pond it does not touch.
    assert (differences > 0) == (lake_id == "lake-b")
    # The reference values are the fixture pixels at the mask's classified positions.
    mask = masks.load_mask(Path(spec["mask_paths"]["10"]))
    selected = mask.selected()
    rows, cols = np.nonzero(selected)
    expected = fixture_scene["data"]["red"][rows + mask.window.row_off, cols + mask.window.col_off]
    assert reference["red"]["digest_all"] == lake_extraction.digest_values(expected)
    assert reference["red"]["counts"] == {
        name: int((mask.pixel_class[selected] == code).sum())
        for name, code in masks.CLASS_CODES.items()
    }
    assert (
        reference["red"]["output_bytes"] == int(selected.sum()) * lake_extraction.CLASS_RECORD_BYTES
    )
    lake = next(x for x in fixture_scene["lakes"] if x["properties"]["water_body_id"] == lake_id)
    summary = lake_extraction.summarize(list(results.values()), {lake_id: prepared}, [lake])
    assert {r["method"] for r in summary["by_size_class_method"]} == set(lake_extraction.METHODS)
    row = next(r for r in summary["by_size_class_method"] if r["method"] == "raster-mask")
    assert row["lakes"] == 1 and row["runs"] == 1 and row["failed"] == 0
    assert row["pixels_extracted_median"] == results["raster-mask"]["totals"]["pixels_extracted"]
    assert summary["lakes"] == 1 and summary["distinct_tiles"] == 1
    assert summary["distinct_tile_dates"] == 1
    prep_row = summary["preparation_by_size_class"][0]
    assert (
        prep_row["lakes"] == 1
        and prep_row["classes"]["10"]["interior"]
        == (prepared["resolutions"]["10"]["counts"]["interior"])
    )
    lake_row = next(r for r in summary["by_lake_method"] if r["method"] == "index-lists")
    assert lake_row["size_label"] == lake_extraction.size_label(lake)
    assert all(e["mask_methods_identical"] for e in summary["equality"])
    for row in summary["equality"]:
        assert (
            row["naive_matches_interior_and_shoreline"] != row["naive_set_differs_in_preparation"]
        )
    assert len(summary["equality"]) == 5


def test_lake_outside_the_tile_reports_band_errors(fixture_scene, tmp_path):
    outside = feature("lake-x", box(X0 + 9000, Y0 - 1000, X0 + 9050, Y0 - 950), 30)
    fixture_scene["lakes"].append(outside)
    try:
        spec, prepared = prepare(fixture_scene, tmp_path, "lake-x")
        assert prepared["fraction_in_tile"] == 0.0
        result = lake_extraction.extract_worker(
            extraction_spec(fixture_scene, tmp_path, "lake-x", "raster-mask", spec)
        )
        assert result["totals"]["band_errors"] == 5 and result["totals"]["bands"] == 0
    finally:
        fixture_scene["lakes"].pop()


def test_reuse_mismatch_and_read_seconds():
    saved = {
        "water_body_id": "a",
        "method": "raster-mask",
        "repetition": 1,
        "tile": "17SKU",
        "item_id": "i",
        "bands": [{"key": "red", "href": "h", "open_seconds": 0.5, "read_seconds": 1.0}],
        "gdal_env": lake_extraction.GDAL_ENV,
    }
    spec = {**saved, "assets": [{"key": "red", "href": "h"}]}
    keys = ("water_body_id", "method", "repetition", "tile", "item_id")
    assert lake_extraction.reuse_mismatch(saved, spec, keys) is None
    assert (
        lake_extraction.reuse_mismatch(saved, {**spec, "item_id": "j"}, keys) == "item_id differs"
    )
    reordered = {
        **saved,
        "bands": [
            {"key": "nir", "href": "n"},
            {"key": "stack-10m", "build_seconds": 0.1},
            {"key": "red", "href": "h"},
        ],
    }
    two = {**spec, "assets": [{"key": "red", "href": "h"}, {"key": "nir", "href": "n"}]}
    assert lake_extraction.reuse_mismatch(reordered, two, keys) is None
    other = {**spec, "assets": [{"key": "red", "href": "other"}]}
    assert "assets differ" in lake_extraction.reuse_mismatch(saved, other, keys)
    stale = {**saved, "gdal_env": {}}
    assert "reader configuration" in lake_extraction.reuse_mismatch(stale, spec, keys)
    assert lake_extraction.read_seconds(saved) == 1.5
    assert lake_extraction.reusable_result(None, "x", spec, keys) == (None, None)


def test_dry_run_and_worker_entry_points(fixture_scene, tmp_path, capsys):
    manifest = str(fixture_scene["dir"] / "manifest.geojson")
    assert lake_extraction.main(["--dry-run", "--manifest", manifest, "--repeat", "1"]) == 0
    out = capsys.readouterr().out
    assert "3 lakes, 4 methods, 12 extraction runs" in out
    assert "lake-c (anchor)" in out
    assert lake_extraction.main(["--dry-run", "--manifest", manifest, "--regions", "none"]) == 1
    spec, _ = prepare(fixture_scene, tmp_path, "lake-a")
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(extraction_spec(fixture_scene, tmp_path, "lake-a", "index-lists", spec))
    )
    assert lake_extraction.main(["--extract-worker", str(path)]) == 0
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["method"] == "index-lists" and printed["totals"]["bands"] == 5
    prepare_path = tmp_path / "prepare.json"
    prepare_path.write_text(json.dumps(spec))
    assert lake_extraction.main(["--prepare-worker", str(prepare_path)]) == 0
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["water_body_id"] == "lake-a"


def test_blocks_in_window_counts_intersected_blocks():
    window = {"row_off": 0, "col_off": 0, "height": 4806, "width": 3872}
    assert lake_extraction.blocks_in_window(window, [1024, 1024]) == 20
    assert (
        lake_extraction.blocks_in_window(
            {"row_off": 10120, "col_off": 7436, "height": 2, "width": 2}, [1024, 1024]
        )
        == 1
    )
    crossing = {"row_off": 9181, "col_off": 100, "height": 59, "width": 10}
    assert lake_extraction.blocks_in_window(crossing, [1024, 1024]) == 2
    assert lake_extraction.blocks_in_window(window, None) is None
    assert (
        lake_extraction.blocks_in_window(
            {"row_off": 0, "col_off": 0, "height": 0, "width": 0}, [512, 512]
        )
        is None
    )
    run = {
        "bands": [
            {"window": window, "block_shape": [1024, 1024]},
            {"key": "stack-10m"},
            {"window": crossing, "blocks_touched": 2},
        ]
    }
    assert lake_extraction.blocks_touched(run) == 22
    assert lake_extraction.blocks_touched({"bands": [{"window": window}]}) is None


def test_reuse_is_bound_to_inputs_and_rejects_band_errors():
    inputs = {"polygon_sha256": "p", "grid": {"epsg": 1}, "mask_digests": {"10": {"mask": "m"}}}
    saved = {
        "water_body_id": "a",
        "method": "raster-mask",
        "repetition": 1,
        "tile": "17SKU",
        "item_id": "i",
        "inputs": inputs,
        "bands": [{"key": "red", "href": "h"}],
        "gdal_env": lake_extraction.GDAL_ENV,
    }
    keys = ("water_body_id", "method", "repetition", "tile", "item_id")
    spec = {**saved, "assets": [{"key": "red", "href": "h"}]}
    assert lake_extraction.reuse_mismatch(saved, spec, keys) is None
    moved = {**spec, "inputs": {**inputs, "grid": {"epsg": 2}}}
    assert "inputs differ" in lake_extraction.reuse_mismatch(saved, moved, keys)
    redrawn = {**spec, "inputs": {**inputs, "polygon_sha256": "q"}}
    assert "inputs differ" in lake_extraction.reuse_mismatch(saved, redrawn, keys)
    remasked = {**spec, "inputs": {**inputs, "mask_digests": {"10": {"mask": "n"}}}}
    assert "inputs differ" in lake_extraction.reuse_mismatch(saved, remasked, keys)
    broken = {**saved, "bands": [{"key": "red", "href": "h", "error": "grid"}]}
    assert "band error" in lake_extraction.reuse_mismatch(broken, spec, keys)
    empty = {**saved, "bands": [{"key": "red", "error": "no pixel of this lake in the tile"}]}
    assert "band error" in lake_extraction.reuse_mismatch(empty, spec, keys)


def test_equality_needs_pixel_digests_and_every_planned_run(fixture_scene, tmp_path):
    spec, prepared = prepare(fixture_scene, tmp_path, "lake-a")
    lake = next(x for x in fixture_scene["lakes"] if x["properties"]["water_body_id"] == "lake-a")
    only_mask = lake_extraction.extract_worker(
        extraction_spec(fixture_scene, tmp_path, "lake-a", "raster-mask", spec)
    )
    plan = {"methods": lake_extraction.METHODS, "repeat": 1}
    summary = lake_extraction.summarize([only_mask], {"lake-a": prepared}, [lake], plan)
    row = summary["equality"][0]
    assert row["complete"] is False and len(row["missing"]) == 3
    assert row["mask_methods_identical"] is True and row["mask_pixel_sets_identical"] is True
    assert row["naive_matches_interior_and_shoreline"] is None
    assert summary["equality_incomplete"] == 5
    assert summary["runs"] == {
        "planned": 1,
        "with_pixels": 1,
        "without_a_pixel_in_the_tile": 0,
        "with_band_errors": 0,
        "failed": 0,
    }
    band = only_mask["bands"][0]
    assert band["digest_pixels"] != band["digest_pixels_wet"]
    assert band["blocks_touched"] >= 1
    assert only_mask["inputs"] is None
    # A record without pixel digests, as the 2026-09-15 run saved, leaves the set check open.
    stripped = json.loads(json.dumps(only_mask))
    for b in stripped["bands"]:
        b.pop("digest_pixels", None)
        b.pop("digest_pixels_wet", None)
    summary = lake_extraction.summarize([stripped, only_mask], {"lake-a": prepared}, [lake], plan)
    assert summary["equality"][0]["mask_pixel_sets_identical"] is None
    assert lake_extraction.run_status(only_mask) == "ok"
    assert lake_extraction.run_status({"error": "x"}) == "failed"


def test_resummarize_rewrites_only_the_summary(fixture_scene, tmp_path):
    spec, prepared = prepare(fixture_scene, tmp_path, "lake-b")
    lake = next(x for x in fixture_scene["lakes"] if x["properties"]["water_body_id"] == "lake-b")
    runs = [
        lake_extraction.extract_worker(
            extraction_spec(fixture_scene, tmp_path, "lake-b", method, spec)
        )
        for method in ("naive-clip", "index-lists")
    ]
    manifest = fixture_scene["dir"] / "manifest.geojson"
    result = {
        "measured_at": "2026-09-15T13:21:37+00:00",
        "manifest": {
            "path": str(manifest.relative_to(ROOT))
            if manifest.is_relative_to(ROOT)
            else str(manifest),
            "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
        "plan": {"methods": ["naive-clip", "index-lists"], "repeat": 1},
        "preparation": {"lake-b": prepared},
        "runs": runs,
        "summary": {"stale": True},
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    if not manifest.is_relative_to(ROOT):
        result["manifest"]["path"] = str(manifest)
        path.write_text(json.dumps(result))
    lake_extraction.ROOT = Path("/") if not manifest.is_relative_to(ROOT) else ROOT
    try:
        assert lake_extraction.resummarize(path) == 0
    finally:
        lake_extraction.ROOT = ROOT
    written = json.loads(path.read_text())
    assert written["measured_at"] == "2026-09-15T13:21:37+00:00"
    assert written["summary"]["runs"]["with_pixels"] == 2
    assert written["summary"]["equality"][0]["complete"] is True
    assert written["pixels_read_between"] == [runs[0]["started_at"], runs[1]["started_at"]]
    assert "summary_generated_at" in written and written["summary_implementation"]
    assert written["runs"] == runs
    assert lake["properties"]["water_body_id"] == "lake-b"
