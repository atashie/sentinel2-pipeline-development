"""Fixture tests for the stage 3 tile extraction script. Synthetic tiles, no network."""

import copy
import hashlib
import importlib.util
import json
import sys
import weakref
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box
from test_lake_extraction import BANDS, EPSG, GRID, X0, Y0, feature, make_item, write_band

from s2proto import masks

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tile_extraction", ROOT / "benchmarks" / "tile_extraction.py"
)
tile_extraction = importlib.util.module_from_spec(SPEC)
sys.modules["tile_extraction"] = tile_extraction  # dataclasses resolve annotations by module
SPEC.loader.exec_module(tile_extraction)
stage2 = tile_extraction.stage2

EAST_X0 = X0 + 1200.0
"""A second tile starting 1.2 km east, so the tiles overlap by half."""
CHUNK = 128
"""Lazy chunk for the fixtures, so the 240-pixel tile spans several chunks."""
LAKE_IDS = ("lake-a", "lake-b", "lake-c", "lake-near", "lake-outer")


def east_item(directory, **kwargs):
    grid = masks.TileGrid(EPSG, EAST_X0, Y0, 240, 240)
    item = make_item(directory, tile="17SKV", footprint=grid.extent(), **kwargs)
    for asset in item["assets"].values():
        asset["proj:transform"][2] = EAST_X0
    return item


@pytest.fixture(scope="module")
def scene(tmp_path_factory):
    directory = tmp_path_factory.mktemp("tile")
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
        # 30 m east of the first tile's edge: near-land pixels only in that tile.
        feature("lake-near", box(X0 + 2430, Y0 - 1050, X0 + 2450, Y0 - 1030), 30),
        # 98 m east of the edge: the buffer touches the tile, but no pixel center is within
        # 100 m of the polygon at any resolution. A candidate member with no pixel.
        feature("lake-outer", box(X0 + 2498, Y0 - 1450, X0 + 2518, Y0 - 1430), 30),
    ]
    manifest = {"type": "FeatureCollection", "features": lakes}
    (directory / "manifest.geojson").write_text(json.dumps(manifest))
    return {"dir": directory, "item": item, "lakes": lakes, "data": data}


def lake(scene, lake_id):
    return next(x for x in scene["lakes"] if x["properties"]["water_body_id"] == lake_id)


def test_normalize_grid_code():
    assert tile_extraction.normalize_grid_code("MGRS-5VMG") == "05VMG"
    assert tile_extraction.normalize_grid_code("MGRS-05VMG") == "05VMG"
    assert tile_extraction.normalize_grid_code("17SKU") == "17SKU"
    assert tile_extraction.normalize_grid_code("MGRS-17SKU") == "17SKU"
    assert tile_extraction.normalize_grid_code("junk") is None
    assert tile_extraction.normalize_grid_code(None) is None


def test_membership_is_a_candidate_test_with_near_land_support(scene):
    item = scene["item"]
    near = tile_extraction.lake_membership(lake(scene, "lake-near"), item)
    assert near["in_tile"] == 0.0 and near["member"] is True
    assert near["support_in_footprint"] == 1.0
    outer = tile_extraction.lake_membership(lake(scene, "lake-outer"), item)
    assert outer["member"] is True and outer["in_tile"] == 0.0
    far = feature("lake-far", box(X0 + 9000, Y0 - 1000, X0 + 9050, Y0 - 950), 30)
    assert tile_extraction.lake_membership(far, item)["member"] is False
    inside = tile_extraction.lake_membership(scene["lakes"][0], item)
    assert inside["in_tile"] == 1.0 and inside["in_footprint"] == 1.0 and inside["member"]
    assert inside["support_in_footprint"] == 1.0


def test_choose_tiles_places_every_lake_and_lists_members(scene):
    west = scene["item"]
    east = east_item(scene["dir"])
    far = feature("lake-far", box(X0 + 90000, Y0 - 1000, X0 + 90050, Y0 - 950), 30)
    lakes = [*scene["lakes"], far]
    chosen = tile_extraction.choose_tiles([east, west], lakes)
    assert [t["tile"] for t in chosen["tiles"]] == ["17SKU", "17SKV"]
    first, second = chosen["tiles"]
    # The score that chose each tile: unplaced lakes it placed in its round, and their share.
    assert first["score"] == {"places_unplaced": 3, "share_of_those": 3.0}
    assert second["score"] == {"places_unplaced": 2, "share_of_those": 2.0}
    assert first["placed"] == ["lake-a", "lake-b", "lake-c"]
    assert [m["water_body_id"] for m in first["members"]] == list(LAKE_IDS)
    assert second["placed"] == ["lake-near", "lake-outer"]
    assert [m["water_body_id"] for m in second["members"]] == ["lake-c", "lake-near", "lake-outer"]
    near_in_east = next(m for m in second["members"] if m["water_body_id"] == "lake-near")
    assert near_in_east["in_tile"] == 1.0
    assert chosen["unplaced"] == ["lake-far"]
    candidates = {c["tile"]: c for c in chosen["candidates"]}
    assert candidates["17SKU"]["places"] == 3 and candidates["17SKV"]["places"] == 2
    assert candidates["17SKU"]["members"] == 5
    assert tile_extraction.choose_tiles([], lakes)["unplaced"] == [
        x["properties"]["water_body_id"] for x in lakes
    ]


def test_choose_tiles_merges_grid_code_spellings(scene):
    padded = json.loads(json.dumps(scene["item"]))
    padded["properties"]["grid:code"] = "MGRS-05SKU"
    padded["id"] = "padded"
    bare = json.loads(json.dumps(scene["item"]))
    bare["properties"]["grid:code"] = "MGRS-5SKU"
    chosen = tile_extraction.choose_tiles([bare, padded], scene["lakes"][:2])
    assert [t["tile"] for t in chosen["tiles"]] == ["05SKU"]
    assert len(chosen["tiles"][0]["items"]) == 2


def test_merge_tile_choices_joins_regions_before_an_item_is_chosen(scene):
    west = scene["item"]
    twin = json.loads(json.dumps(west))
    twin["id"] = "twin"
    north = tile_extraction.choose_tiles([west], scene["lakes"][:2])
    south = tile_extraction.choose_tiles([west, twin], scene["lakes"][1:3])
    merged = tile_extraction.merge_tile_choices({"north": north, "south": south})
    assert list(merged) == ["17SKU"]
    entry = merged["17SKU"]
    assert entry["regions"] == ["north", "south"]
    assert [i["id"] for i in entry["items"]] == [west["id"], "twin"]
    assert entry["placed"] == ["lake-a", "lake-b", "lake-c"]
    assert [m["water_body_id"] for m in entry["members"]] == ["lake-a", "lake-b", "lake-c"]


def test_choose_item_scores_footprint_over_the_near_land_support(scene):
    lakes = scene["lakes"][:3]
    full = scene["item"]
    partial = make_item(scene["dir"], cloud=0.1, footprint=box(X0, Y0 - 2400, X0 + 900, Y0))
    cloudier = make_item(scene["dir"], cloud=40.0, created="2025-10-16T00:00:00Z")
    picked = tile_extraction.choose_item([partial, cloudier, full], lakes)
    assert picked["item"]["properties"]["eo:cloud_cover"] == 1.0
    assert picked["covered"] == 3 and "support of 3 of 3 members" in picked["note"]
    later = make_item(scene["dir"], cloud=1.0, created="2025-10-17T00:00:00Z")
    assert tile_extraction.choose_item([full, later], lakes)["item"]["id"] == later["id"]
    # A near-land-only member: the clearer item misses its support, the cloudier one has it.
    near = [lake(scene, "lake-near")]
    clear_west = make_item(scene["dir"], cloud=0.1, footprint=box(X0, Y0 - 2400, X0 + 2000, Y0))
    cloudy_full = make_item(scene["dir"], cloud=5.0, created="2025-10-18T00:00:00Z")
    picked = tile_extraction.choose_item([clear_west, cloudy_full], near)
    assert picked["item"]["id"] == cloudy_full["id"] and picked["covered"] == 1
    assert picked["lakes"][0]["in_tile"] == 0.0 and picked["lakes"][0]["support_in_footprint"] == 1


def test_plan_order_rotates_patterns_and_methods():
    patterns, methods = tile_extraction.PATTERNS, tile_extraction.METHODS
    orders = [tile_extraction.plan_order(patterns, methods, rep) for rep in (1, 2, 3)]
    assert orders[0][0] == ("lake-by-lake", "naive-clip")
    assert orders[1][0] == ("tile-by-tile", "raster-mask")
    assert orders[2][0] == ("whole-tile", "index-lists")
    combos = sorted(orders[0])
    for order in orders:
        assert sorted(order) == combos
    # Within every pattern group the methods sit in a different order per repetition.
    for rep, order in enumerate(orders, 1):
        for start in range(0, len(order), len(methods)):
            group = [m for _, m in order[start : start + len(methods)]]
            assert group == tile_extraction.rotated(methods, rep - 1)
    leaders = {order[0][1] for order in orders}
    assert len(leaders) == 3
    assert tile_extraction.rotated([], 2) == []
    tiles = [{"tile": "17SKU", "region": "fixture", "members": [1, 2]}]
    runs = tile_extraction.plan_runs(tiles, ["whole-tile"], ["raster-mask"], 2)
    assert len(runs) == 2 and runs[1]["repetition"] == 2 and runs[0]["lakes"] == 2


def test_block_cells_and_chunks_depend_on_the_graph_origin():
    window = {"row_off": 9181, "col_off": 100, "height": 59, "width": 10}
    assert tile_extraction.block_cells(window, [1024, 1024]) == {(8, 0), (9, 0)}
    assert tile_extraction.block_cells(window, None) == set()
    assert tile_extraction.block_cells({**window, "height": 0}, [16, 16]) == set()
    local = {"row_off": 90, "col_off": 118, "height": 21, "width": 20}
    assert tile_extraction.chunks_for(local, 128, shared=True) == 2
    assert tile_extraction.chunks_for(local, 128, shared=False) == 1
    assert tile_extraction.chunks_for({**local, "width": 0}, 128, shared=True) == 0


def prepare(scene, tmp_path, lake_id, tile="17SKU"):
    feature_ = lake(scene, lake_id)
    spec = {
        "tile": tile,
        "water_body_id": lake_id,
        "geometry": feature_["geometry"],
        "polygon_sha256": stage2.polygon_digest(feature_),
        "grid": {"epsg": EPSG, "x0": X0, "y0": Y0, "width_10m": 240, "height_10m": 240},
        "resolutions": [10, 20, 60],
        "mask_paths": {
            str(r): str(tmp_path / "masks" / f"{tile}-{lake_id}-{r}m.npz") for r in (10, 20, 60)
        },
        "index_paths": {
            str(r): str(tmp_path / "index" / f"{tile}-{lake_id}-{r}m.npz") for r in (10, 20, 60)
        },
        "mask_parameters": stage2.MASK_PARAMETERS,
        "implementation": tile_extraction.IMPLEMENTATION,
    }
    return spec, tile_extraction.prepare_worker(spec)


def assets_for(scene):
    return stage2.resolve_assets(scene["item"], list(BANDS), GRID)["assets"]


def tile_spec(scene, tmp_path, prepared: dict, pattern, method, repetition=1):
    item = scene["item"]
    members = []
    for lake_id, (spec, _result) in prepared.items():
        feature_ = lake(scene, lake_id)
        members.append(
            {
                "water_body_id": lake_id,
                "size_label": stage2.size_label(feature_),
                "geometry": feature_["geometry"],
                "mask_paths": spec["mask_paths"],
                "index_paths": spec["index_paths"],
            }
        )
    return {
        "tile": "17SKU",
        "region": "fixture",
        "pattern": pattern,
        "method": method,
        "repetition": repetition,
        "item_id": item["id"],
        "item_path": str(scene["dir"] / "item.json"),
        "grid": prepared[next(iter(prepared))][0]["grid"],
        "assets": assets_for(scene),
        "lakes": members,
        "chunk": CHUNK,
        "dask_workers": 2,
        "log_path": str(tmp_path / f"{pattern}-{method}-{repetition}.gdal.log"),
    }


def tiles_for(scene, assets=None):
    return {
        "17SKU": {
            "tile": "17SKU",
            "region": "fixture",
            "item": stage2.trim_item(scene["item"]),
            "lakes": [tile_extraction.lake_membership(x, scene["item"]) for x in scene["lakes"]],
            "placed": ["lake-a", "lake-b", "lake-c"],
            "assets": {"assets": assets if assets is not None else assets_for(scene)},
        }
    }


@pytest.fixture(scope="module")
def prepared(scene, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("prepared")
    return {lake_id: prepare(scene, tmp_path, lake_id) for lake_id in LAKE_IDS}


@pytest.fixture(scope="module")
def all_runs(scene, prepared, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("runs")
    runs = {}
    for pattern in tile_extraction.PATTERNS:
        for method in tile_extraction.METHODS:
            spec = tile_spec(scene, tmp_path, prepared, pattern, method)
            RUN_LOGS[(pattern, method)] = spec["log_path"]
            runs[(pattern, method)] = tile_extraction.extract_worker(spec)
    return runs


def test_preparation_verifies_candidate_members(prepared):
    _, near = prepared["lake-near"]
    assert near["tile"] == "17SKU" and near["fraction_in_tile"] == 0.0
    ten = near["resolutions"]["10"]["counts"]
    assert ten["interior"] == 0 and ten["shoreline"] == 0 and ten["near_land"] > 0
    _, outer = prepared["lake-outer"]
    for record in outer["resolutions"].values():
        assert sum(record["counts"][c] for c in masks.CLASS_CODES) == 0
    _, small = prepared["lake-b"]
    assert small["resolutions"]["10"]["counts"]["naive_only"] > 0


def tile_spec_log(run):
    """The GDAL log a fixture run wrote, from its pattern, method, and repetition."""
    return str(RUN_LOGS[(run["pattern"], run["method"])])


RUN_LOGS: dict = {}


def band_of(run, lake_id, key):
    record = next(lk for lk in run["lakes"] if lk["water_body_id"] == lake_id)
    return next(b for b in record["bands"] if b.get("key") == key)


def test_every_pattern_and_method_agrees(scene, prepared, all_runs):
    for (pattern, method), run in all_runs.items():
        assert run["totals"]["band_errors"] == 0, (pattern, method, run["bands"])
        assert run["totals"]["lake_band_errors"] == 0, (pattern, method)
        # The naive clip has no near-land class, so the lake outside the tile gives it nothing.
        with_pixels = 3 if method == "naive-clip" else 4
        assert run["totals"]["lakes"] == 5 and run["totals"]["lakes_with_pixels"] == with_pixels
        assert run["totals"]["bands"] == 5 and run["wall_seconds"] > 0
        assert run["gdal_cache_bytes"] == tile_extraction.GDAL_CACHE_BYTES == 512 * 1024**2
        assert run["totals"]["opens_observed"] >= 1
        assert [lk["water_body_id"] for lk in run["lakes"]] == list(prepared)
        for record in run["lakes"]:
            assert record["setup"]["seconds"] >= 0
            keys = [b["key"] for b in record["bands"] if not b["key"].startswith("stack-")]
            assert keys == list(BANDS)
            for band in record["bands"]:
                if band["key"].startswith("stack-"):
                    assert band["grid_matches"] is True and band["dask_workers"] == 2
                    continue
                assert "digest_pixels" in band
                if band.get("note") == tile_extraction.EMPTY:
                    empty_for = (
                        ("lake-outer", "lake-near") if method == "naive-clip" else ("lake-outer",)
                    )
                    assert record["water_body_id"] in empty_for, (pattern, method, record)
                    assert band["pixels_extracted"] == 0 and band["blocks_touched"] == 0
                    continue
                assert "extract_seconds" in band and band["pixels_extracted"] > 0
    reference = all_runs[("tile-by-tile", "raster-mask")]
    ref = {
        (lk["water_body_id"], b["key"]): b
        for lk in reference["lakes"]
        for b in lk["bands"]
        if "digest_all" in b
    }
    naive_ref = all_runs[("lake-by-lake", "naive-clip")]
    for (pattern, method), run in all_runs.items():
        for record in run["lakes"]:
            for band in record["bands"]:
                if "digest_all" not in band:
                    continue
                if method == "naive-clip":
                    twin = band_of(naive_ref, record["water_body_id"], band["key"])
                    assert band["digest_all"] == twin["digest_all"], (pattern, band["key"])
                    assert band["digest_pixels"] == twin["digest_pixels"]
                    continue
                expected = ref[(record["water_body_id"], band["key"])]
                assert band["digest_all"] == expected["digest_all"], (pattern, method, band["key"])
                assert band["digest_pixels"] == expected["digest_pixels"]
                assert band["digest_wet"] == expected["digest_wet"]
                assert band["counts"] == expected["counts"]
                if band["pixels_extracted"]:  # empty windows carry each method's own offsets
                    assert band["window"] == expected["window"]
    # Observed opens come from GDAL's log. The rasterio paths open once per logical open.
    whole = all_runs[("whole-tile", "raster-mask")]
    red = next(b for b in whole["bands"] if b["key"] == "red")
    assert red["whole"] is True and red["pixels_in_windows"] == 240 * 240
    assert red["blocks_in_file"] == 15 * 15 and red["opens"] == 1 and red["opens_observed"] == 1
    # Lakes share blocks, so the per-lake sum exceeds the distinct count and can exceed the file.
    assert red["blocks_touched_distinct"] < red["blocks_touched_sum"]
    assert red["blocks_touched_distinct"] <= red["blocks_in_file"] < red["blocks_touched_sum"]
    assert red["requests"] == 0  # local files make no HTTP request
    windowed = all_runs[("tile-by-tile", "raster-mask")]
    red_w = next(b for b in windowed["bands"] if b["key"] == "red")
    assert red_w["whole"] is False and red_w["opens"] == 1 and red_w["opens_observed"] == 1
    assert red_w["pixels_in_windows"] == sum(
        b["pixels_in_window"] for lk in windowed["lakes"] for b in lk["bands"] if b["key"] == "red"
    )
    by_lake = all_runs[("lake-by-lake", "raster-mask")]
    red_l = next(b for b in by_lake["bands"] if b["key"] == "red")
    assert red_l["opens"] == 4 and red_l["opens_observed"] == 4
    # The naive clip rasterizes in memory. Those opens are not raster file opens.
    naive_l = next(b for b in naive_ref["bands"] if b["key"] == "red")
    assert naive_l["opens"] == 3 and naive_l["opens_observed"] == 3
    lines = Path(naive_ref_log := tile_spec_log(naive_ref)).read_text().splitlines()
    assert naive_ref_log and tile_extraction.observed_opens(lines) == 15
    assert tile_extraction.observed_opens(lines, red_l["href"]) == 3
    assert any("MEM:" in line for line in lines if "GDALOpen(" in line)
    assert tile_extraction.read_seconds(whole) > 0
    assert tile_extraction.extract_seconds(whole) >= 0
    # The lazy stack counts logical loads and computes, observes opens, and counts chunks
    # relative to its graph. The fixture tile spans two chunks each way at 10 m.
    lazy_whole = all_runs[("whole-tile", "lazy-stack")]
    red_lw = next(b for b in lazy_whole["bands"] if b["key"] == "red")
    assert red_lw["opens"] is None and red_lw["loads"] == 1 and red_lw["computes"] == 1
    assert red_lw["graph"] == "shared" and red_lw["chunks_in_file"] == 4
    assert red_lw["opens_observed"] >= 1 and "compute_seconds" in red_lw
    lazy_tile = all_runs[("tile-by-tile", "lazy-stack")]
    red_lt = next(b for b in lazy_tile["bands"] if b["key"] == "red")
    assert red_lt["loads"] == 1 and red_lt["computes"] == 4 and red_lt["chunks_in_file"] == 4
    assert band_of(lazy_tile, "lake-c", "red")["chunks_touched"] == 4
    assert band_of(lazy_tile, "lake-a", "red")["chunks_touched"] == 1
    assert red_lt["chunks_touched_distinct"] == 4 and red_lt["chunks_touched_sum"] >= 7
    lazy_lake = all_runs[("lake-by-lake", "lazy-stack")]
    red_ll = next(b for b in lazy_lake["bands"] if b["key"] == "red")
    assert red_ll["graph"] == "per-lake" and red_ll["loads"] == 4 and red_ll["computes"] == 4
    assert red_ll["chunks_touched_distinct"] is None and red_ll["chunks_in_file"] is None
    assert band_of(lazy_lake, "lake-c", "red")["chunks_touched"] == 4
    assert lazy_lake["totals"]["opens_observed"] >= 4
    # Values are the fixture pixels at the mask's classified positions.
    spec, _ = prepared["lake-a"]
    mask = masks.load_mask(Path(spec["mask_paths"]["10"]))
    selected = mask.selected()
    rows, cols = np.nonzero(selected)
    expected = scene["data"]["red"][rows + mask.window.row_off, cols + mask.window.col_off]
    assert ref[("lake-a", "red")]["digest_all"] == stage2.digest_values(expected)
    # The near-land-only lake extracted near-land pixels and nothing else.
    counts = band_of(reference, "lake-near", "red")["counts"]
    assert counts["interior"] == 0 and counts["shoreline"] == 0 and counts["near_land"] > 0


def test_lake_by_lake_releases_each_lake_before_the_next(scene, prepared, tmp_path, monkeypatch):
    original = tile_extraction.selections_for
    refs, alive_before = [], []

    def recording(*args, **kwargs):
        alive_before.append(sum(1 for r in refs if r() is not None))
        setup, chosen = original(*args, **kwargs)
        refs.extend(weakref.ref(s) for s in chosen.values())
        return setup, chosen

    monkeypatch.setattr(tile_extraction, "selections_for", recording)
    for method in ("raster-mask", "lazy-stack"):
        refs.clear()
        alive_before.clear()
        tile_extraction.extract_worker(tile_spec(scene, tmp_path, prepared, "lake-by-lake", method))
        assert alive_before == [0] * len(prepared), (method, alive_before)


def stage_2_like_result(scene, prepared, tmp_path):
    """A stage 2 result for the same fixture, from stage 2's own worker, all four methods."""
    lakes = [lake(scene, "lake-a"), lake(scene, "lake-b")]
    item = scene["item"]
    runs = []
    for feature_ in lakes:
        lake_id = feature_["properties"]["water_body_id"]
        spec, _ = prepared[lake_id]
        for method in stage2.METHODS:
            runs.append(
                stage2.extract_worker(
                    {
                        "water_body_id": lake_id,
                        "region": "fixture",
                        "size_label": stage2.size_label(feature_),
                        "method": method,
                        "repetition": 1,
                        "tile": "17SKU",
                        "item_id": item["id"],
                        "item_path": str(scene["dir"] / "item.json"),
                        "grid": spec["grid"],
                        "geometry": feature_["geometry"],
                        "assets": assets_for(scene),
                        "mask_paths": spec["mask_paths"],
                        "index_paths": spec["index_paths"],
                    }
                )
            )
    preparation = {lake_id: prepared[lake_id][1] for lake_id in ("lake-a", "lake-b")}
    plan = {"methods": stage2.METHODS, "repeat": 1}
    result = {
        "measured_at": "2026-09-15T13:21:37+00:00",
        "stage": "2, one lake at a time",
        "bands": list(BANDS),
        "plan": plan,
        "scenes": {"fixture": {"tile": "17SKU", "item": stage2.trim_item(item)}},
        "runs": runs,
        "summary": stage2.summarize(runs, preparation, lakes, plan),
    }
    path = tmp_path / "lake-extraction.json"
    path.write_text(json.dumps(result))
    return path


def test_summary_compares_families_with_stage_2_and_checks_completeness(
    scene, prepared, all_runs, tmp_path
):
    baseline = tile_extraction.load_baseline(stage_2_like_result(scene, prepared, tmp_path))
    assert baseline["items"] == {"fixture": scene["item"]["id"]} and baseline["bands"] == list(
        BANDS
    )
    assert ("lake-a", "naive-clip") in baseline["rows"]
    item_id = scene["item"]["id"]
    # Stage 2's naive and mask families differ on lake-b and never mix.
    assert (
        baseline["digests"][("lake-b", item_id, "red", "naive")]
        != (baseline["digests"][("lake-b", item_id, "red", "mask")])
    )
    assert len(baseline["digests"][("lake-b", item_id, "red", "mask")]) == 1
    tiles = tiles_for(scene)
    preparation = {f"17SKU/{lake_id}": result for lake_id, (_, result) in prepared.items()}
    plan = {"patterns": tile_extraction.PATTERNS, "methods": tile_extraction.METHODS, "repeat": 1}
    selection = {"fixture": {"unplaced": ["lake-far"]}}
    summary = tile_extraction.summarize(
        list(all_runs.values()), preparation, tiles, scene["lakes"], plan, baseline, selection
    )
    assert summary["runs"] == {
        "planned": 12,
        "ok": 12,
        "with_lake_errors": 0,
        "failed": 0,
        "stopped_for_memory": 0,
        "with_memory_pressure": 0,
    }
    assert summary["lakes"] == 5 and summary["unplaced_lakes"] == ["lake-far"]
    assert summary["distinct_tiles"] == 1 and summary["distinct_tile_dates"] == 1
    assert summary["expected_lake_bands"] == 25 and summary["lake_bands_without_records"] == 0
    tile_row = summary["tiles"][0]
    assert tile_row["lakes"] == 5 and tile_row["lakes_entirely_inside"] == 3
    assert tile_row["lakes_partly_inside"] == 0 and tile_row["lakes_near_land_only"] == 2
    assert tile_row["lakes_with_pixels"] == 4
    assert tile_row["members_without_a_pixel"] == ["lake-outer"]
    assert tile_row["members_failed_preparation"] == [] and tile_row["members_not_prepared"] == []
    rows = {(r["pattern"], r["method"]): r for r in summary["by_tile_pattern_method"]}
    assert len(rows) == 12
    row = rows[("tile-by-tile", "raster-mask")]
    assert row["lakes"] == 5 and row["runs"] == 1 and row["failed"] == 0
    assert row["runs_with_errors"] == 0 and row["timings_from_runs"] == 1
    assert row["runs_with_memory_pressure"] == 0
    assert (
        row["lakes_with_pixels"] == 4
        and row["blocks_touched_distinct"] <= row["blocks_touched_sum"]
    )
    assert row["opens_observed"] == 5
    assert row["baseline_stage_2"]["comparable"] is True
    assert row["baseline_stage_2"]["lakes_with_baseline"] == ["lake-a", "lake-b"]
    assert row["baseline_stage_2"]["lakes_without_baseline"] == [
        "lake-c",
        "lake-near",
        "lake-outer",
    ]
    assert row["baseline_stage_2"]["requests"] >= 0
    assert rows[("whole-tile", "naive-clip")]["baseline_stage_2"]["lakes_with_baseline"] == [
        "lake-a",
        "lake-b",
    ]
    assert rows[("whole-tile", "raster-mask")]["pixels_in_windows"] == (
        240 * 240 * 2 + 120 * 120 * 2 + 40 * 40
    )
    lake_rows = summary["by_tile_lake_pattern_method"]
    assert len(lake_rows) == 5 * 12
    near = next(
        r for r in lake_rows if r["water_body_id"] == "lake-near" and r["pattern"] == "whole-tile"
    )
    assert near["requests_median"] == 0 and near["pixels_extracted"] > 0 and near["runs_clean"] == 1
    assert summary["equality_incomplete"] == 0 and len(summary["equality"]) == 25
    assert summary["equality_stage_2_compared"] == 2 * 5
    for row in summary["equality"]:
        assert row["complete"] and row["records"] == 12
        assert row["mask_methods_identical"] and row["mask_pixel_sets_identical"]
        assert row["naive_identical_across_patterns"] is True
        assert row["naive_pixel_sets_identical_across_patterns"] is True
        assert (
            row["naive_matches_interior_and_shoreline"] != row["naive_set_differs_in_preparation"]
        )
        if row["water_body_id"] in ("lake-a", "lake-b"):
            assert row["matches_stage_2"] is True and row["naive_matches_stage_2"] is True
            assert row["stage_2_mask_reference_consistent"] is True
        else:
            assert row["matches_stage_2"] is None and row["naive_matches_stage_2"] is None
            assert row["stage_2_mask_reference_consistent"] is None
    lake_b = [r for r in summary["equality"] if r["water_body_id"] == "lake-b"]
    assert any(r["naive_set_differs_in_preparation"] for r in lake_b)
    # Another band set makes the timing sums incomparable. The lakes are still named.
    lakes_by_id = {x["properties"]["water_body_id"]: x for x in scene["lakes"]}
    other = tile_extraction.baseline_for(
        baseline, item_id, ["lake-a"], "raster-mask", lakes_by_id, ["red", "nir"]
    )
    assert other["comparable"] is False and other["lakes_with_baseline"] == ["lake-a"]
    assert "requests" not in other
    # Without a repetition, the comparison is incomplete and says which runs are missing.
    partial = tile_extraction.summarize(
        [all_runs[("whole-tile", "raster-mask")]], preparation, tiles, scene["lakes"], plan, None
    )
    row = partial["equality"][0]
    assert row["complete"] is False and len(row["missing"]) == 11 and row["records"] == 1
    assert row["matches_stage_2"] is None and partial["equality_stage_2_compared"] == 0


def test_completeness_catches_missing_lakes_bands_and_later_errors(scene, prepared, all_runs):
    tiles = tiles_for(scene)
    preparation = {f"17SKU/{lake_id}": result for lake_id, (_, result) in prepared.items()}
    plan = {"patterns": tile_extraction.PATTERNS, "methods": tile_extraction.METHODS, "repeat": 1}
    # A member whose preparation failed is excluded from every run. It stays expected.
    without_b = []
    for run in all_runs.values():
        clone = copy.deepcopy(run)
        clone["lakes"] = [lk for lk in clone["lakes"] if lk["water_body_id"] != "lake-b"]
        clone["totals"]["lakes"] = 4
        without_b.append(clone)
    failed_prep = {**preparation, "17SKU/lake-b": {"water_body_id": "lake-b", "error": "boom"}}
    summary = tile_extraction.summarize(without_b, failed_prep, tiles, scene["lakes"], plan)
    assert summary["runs"]["ok"] == 12 and summary["lake_bands_without_records"] == 5
    assert summary["equality_incomplete"] == 5 and summary["expected_lake_bands"] == 25
    missing = [r for r in summary["equality"] if r["records"] == 0]
    assert {r["water_body_id"] for r in missing} == {"lake-b"}
    assert all(len(r["missing"]) == 12 and r["mask_methods_identical"] is None for r in missing)
    assert summary["tiles"][0]["members_failed_preparation"] == ["lake-b"]
    absent = {k: v for k, v in preparation.items() if not k.endswith("lake-c")}
    summary = tile_extraction.summarize(without_b, absent, tiles, scene["lakes"], plan)
    assert summary["tiles"][0]["members_not_prepared"] == ["lake-c"]
    # A band the scene calls for that no run recorded.
    green = {**assets_for(scene)[0], "key": "green", "href": "missing.tif"}
    tiles_green = tiles_for(scene, [*assets_for(scene), green])
    summary = tile_extraction.summarize(
        list(all_runs.values()), preparation, tiles_green, scene["lakes"], plan
    )
    assert summary["expected_lake_bands"] == 30 and summary["lake_bands_without_records"] == 5
    assert {r["band"] for r in summary["equality"] if r["records"] == 0} == {"green"}
    assert summary["lake_bands_without_asset"] == 0
    # A requested band the scene could not resolve stays expected and is counted apart.
    tiles_short = tiles_for(scene)
    tiles_short["17SKU"]["assets"]["missing"] = ["green"]
    summary = tile_extraction.summarize(
        list(all_runs.values()),
        preparation,
        tiles_short,
        scene["lakes"],
        plan,
        bands=[*BANDS, "green"],
    )
    assert summary["expected_lake_bands"] == 30 and summary["lake_bands_without_records"] == 5
    assert summary["lake_bands_without_asset"] == 5 and summary["equality_incomplete"] == 5
    assert summary["tiles"][0]["assets_missing"] == ["green"]
    assert summary["tiles"][0]["assets_skipped"] == []
    unresolved = [r for r in summary["equality"] if not r["asset_resolved"]]
    assert {(r["band"], r["resolution"], r["records"]) for r in unresolved} == {("green", None, 0)}
    assert len(unresolved) == 5 and all(len(r["missing"]) == 12 for r in unresolved)
    assert all(r["asset_resolved"] for r in summary["equality"] if r["band"] != "green")
    # An error in a later repetition is counted and kept out of the timing medians.
    first = all_runs[("tile-by-tile", "raster-mask")]
    second = copy.deepcopy(first)
    second["repetition"] = 2
    second["wall_seconds"] = first["wall_seconds"] * 50
    second["lakes"][0]["bands"][0] = {"key": "red", "error": "read failed"}
    second["totals"]["lake_band_errors"] = 1
    third = copy.deepcopy(first)
    third["repetition"] = 3
    third["wall_seconds"] = first["wall_seconds"] * 20
    third["host_memory"] = {"pressure": True, "swap_out_delta": 4096}
    plan3 = {**plan, "repeat": 3}
    summary = tile_extraction.summarize(
        [first, second, third], preparation, tiles, scene["lakes"], plan3
    )
    assert summary["runs"]["ok"] == 2 and summary["runs"]["with_lake_errors"] == 1
    assert summary["runs"]["with_memory_pressure"] == 1
    row = summary["by_tile_pattern_method"][0]
    assert (
        row["runs"] == 3 and row["runs_with_errors"] == 1 and row["runs_with_memory_pressure"] == 1
    )
    assert row["timings_from_runs"] == 1
    assert row["wall_seconds_median"] == round(first["wall_seconds"], 3)
    assert row["lake_band_errors"] == 1 and "timings_under_memory_pressure" not in row
    lake_row = next(
        r for r in summary["by_tile_lake_pattern_method"] if r["water_body_id"] == "lake-a"
    )
    # The pressured run is out of the lake's median too, and counted.
    assert lake_row["runs"] == 3 and lake_row["runs_clean"] == 1 and lake_row["band_errors"] == 1
    assert lake_row["runs_under_memory_pressure"] == 1
    assert lake_row["read_seconds_median"] == round(
        sum(b.get(k, 0.0) for b in first["lakes"][0]["bands"] for k in tile_extraction.READ_TIMERS),
        3,
    )
    red_a = next(
        r for r in summary["equality"] if r["water_body_id"] == "lake-a" and r["band"] == "red"
    )
    assert red_a["records"] == 2 and "tile-by-tile/raster-mask:2" in red_a["missing"]
    assert not {"tile-by-tile/raster-mask:1", "tile-by-tile/raster-mask:3"} & set(red_a["missing"])
    # When every run of a combination is under pressure, there is no median, only counts.
    summary = tile_extraction.summarize([third], preparation, tiles, scene["lakes"], plan)
    row = summary["by_tile_pattern_method"][0]
    assert row["timings_from_runs"] == 0 and row["runs_with_memory_pressure"] == 1
    assert "wall_seconds_median" not in row and "requests_median" not in row
    assert summary["runs"]["with_memory_pressure"] == 1 and summary["runs"]["ok"] == 1
    lake_row = summary["by_tile_lake_pattern_method"][0]
    assert lake_row["runs_clean"] == 0 and lake_row["runs_under_memory_pressure"] == 1
    assert "read_seconds_median" not in lake_row


def test_reuse_is_bound_to_lakes_and_inputs():
    inputs = {"grid": {"epsg": 1}, "lakes": [{"water_body_id": "a", "polygon_sha256": "p"}]}
    saved = {
        "tile": "17SKU",
        "item_id": "i",
        "pattern": "whole-tile",
        "method": "raster-mask",
        "repetition": 1,
        "inputs": inputs,
        "bands": [{"key": "red", "href": "h"}],
        "lakes": [{"water_body_id": "a", "bands": [{"key": "red", "digest_all": "d"}]}],
        "gdal_env": tile_extraction.GDAL_ENV,
    }
    keys = ("tile", "item_id", "pattern", "method", "repetition")
    spec = {**saved, "assets": [{"key": "red", "href": "h"}]}
    assert tile_extraction.reuse_mismatch(saved, spec, keys) is None
    assert tile_extraction.reuse_mismatch(saved, {**spec, "pattern": "tile-by-tile"}, keys) == (
        "pattern differs"
    )
    more_lakes = {**spec, "inputs": {**inputs, "lakes": inputs["lakes"] + [{"water_body_id": "b"}]}}
    assert "inputs differ" in tile_extraction.reuse_mismatch(saved, more_lakes, keys)
    broken = {**saved, "lakes": [{"water_body_id": "a", "bands": [{"key": "red", "error": "x"}]}]}
    assert "lake error" in tile_extraction.reuse_mismatch(broken, spec, keys)
    stale = {**saved, "gdal_env": stage2.GDAL_ENV}
    assert "reader configuration" in tile_extraction.reuse_mismatch(stale, spec, keys)
    assert tile_extraction.reusable_result(None, "x", spec, keys) == (None, None)
    assert tile_extraction.run_status({"error": "x"}) == "failed"
    assert tile_extraction.run_status({"error": "x", "memory_stop": True}) == "stopped_for_memory"
    assert (
        tile_extraction.run_status({"totals": {"band_errors": 0, "lake_band_errors": 2}})
        == "lake_errors"
    )


def test_baseline_absent_and_item_mismatch(scene, prepared, tmp_path):
    assert tile_extraction.load_baseline(tmp_path / "missing.json") is None
    assert tile_extraction.load_baseline(None) is None
    baseline = tile_extraction.load_baseline(stage_2_like_result(scene, prepared, tmp_path))
    lakes_by_id = {x["properties"]["water_body_id"]: x for x in scene["lakes"]}
    same = tile_extraction.baseline_for(
        baseline, scene["item"]["id"], ["lake-a", "lake-c"], "raster-mask", lakes_by_id
    )
    assert same["lakes_with_baseline"] == ["lake-a"] and same["lakes_without_baseline"] == [
        "lake-c"
    ]
    assert same["comparable"] is True
    other = tile_extraction.baseline_for(
        baseline, "other-item", ["lake-a"], "raster-mask", lakes_by_id
    )
    assert other["lakes_with_baseline"] == [] and other["requests"] == 0
    assert tile_extraction.baseline_for(None, "i", ["lake-a"], "raster-mask", lakes_by_id) is None


def test_worker_subprocess_is_guarded_by_the_memory_budget(scene, prepared, tmp_path):
    spec = tile_spec(scene, tmp_path, prepared, "whole-tile", "raster-mask")
    stopped = tile_extraction.run_in_subprocess(
        "extract", spec, tmp_path / "stop.json", {"budget_bytes": 1, "poll_seconds": 0.05}
    )
    assert stopped["memory_stop"] is True and stopped["error"].startswith("stopped:")
    assert stopped["pattern"] == "whole-tile" and stopped["host_memory"]["peak_rss_observed"] > 1
    not_started = tile_extraction.run_in_subprocess(
        "extract", spec, tmp_path / "wait.json", {"reserve_bytes": 10**18, "wait_seconds": 0.0}
    )
    assert not_started["memory_stop"] is True and "not started" in not_started["error"]
    result = tile_extraction.run_in_subprocess("extract", spec, tmp_path / "ok.json")
    assert "error" not in result and result["totals"]["lakes_with_pixels"] == 4
    memory = result["host_memory"]
    assert memory["budget_bytes"] == 4 * tile_extraction.GIB
    assert (memory["samples"] == 0) == (memory["peak_rss_observed"] is None)
    assert memory["peak_rss_observed"] is None or memory["peak_rss_observed"] > 0
    assert "pressure" in memory and "swap_out_delta" in memory
    assert memory["pressure_bytes"] == 128 * 1024**2 and memory["total"] > 0
    assert Path(spec["log_path"]).exists()


def test_dry_run_and_worker_entry_points(scene, prepared, tmp_path, capsys):
    manifest = str(scene["dir"] / "manifest.geojson")
    assert tile_extraction.main(["--dry-run", "--manifest", manifest, "--repeat", "2"]) == 0
    out = capsys.readouterr().out
    assert "5 lakes in 1 regions, 3 patterns, 4 methods, 2 repetitions: 24 runs per tile" in out
    assert "repetition 2: tile-by-tile/raster-mask" in out
    assert "lake-c (anchor)" in out
    assert tile_extraction.main(["--dry-run", "--manifest", manifest, "--regions", "none"]) == 1
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(tile_spec(scene, tmp_path, prepared, "whole-tile", "index-lists")))
    assert tile_extraction.main(["--extract-worker", str(path)]) == 0
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["pattern"] == "whole-tile" and printed["totals"]["lakes_with_pixels"] == 4
    prepare_path = tmp_path / "prepare.json"
    prepare_path.write_text(json.dumps(prepared["lake-a"][0]))
    assert tile_extraction.main(["--prepare-worker", str(prepare_path)]) == 0
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["water_body_id"] == "lake-a" and printed["tile"] == "17SKU"


def test_resummarize_rewrites_only_the_summary_and_needs_its_baseline(
    scene, prepared, all_runs, tmp_path
):
    manifest = scene["dir"] / "manifest.geojson"
    baseline_path = stage_2_like_result(scene, prepared, tmp_path)
    runs = [all_runs[("whole-tile", "raster-mask")], all_runs[("whole-tile", "naive-clip")]]
    result = {
        "measured_at": "2026-09-15T13:21:37+00:00",
        "manifest": {
            "path": str(manifest),
            "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        },
        "lakes_requested": list(LAKE_IDS),
        "bands": list(BANDS),
        "plan": {"patterns": ["whole-tile"], "methods": ["raster-mask", "naive-clip"], "repeat": 1},
        "selection": {"fixture": {"unplaced": []}},
        "tiles": tiles_for(scene),
        "preparation": {f"17SKU/{lake_id}": r for lake_id, (_, r) in prepared.items()},
        "baseline": {
            "path": str(baseline_path),
            "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        },
        "runs": runs,
        "summary": {"stale": True},
    }
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    tile_extraction.ROOT = Path("/")
    try:
        assert tile_extraction.resummarize(path) == 0
        written = json.loads(path.read_text())
        assert written["measured_at"] == "2026-09-15T13:21:37+00:00"
        assert written["summary"]["lakes"] == 5 and written["summary"]["runs"]["ok"] == 2
        assert written["summary"]["equality"][0]["complete"] is True
        assert written["summary"]["equality_stage_2_compared"] == 10
        ends = [
            datetime.fromisoformat(r["started_at"]) + timedelta(seconds=r["wall_seconds"])
            for r in runs
        ]
        assert written["pixels_read_between"] == [
            min(r["started_at"] for r in runs),
            max(ends).isoformat(timespec="seconds"),
        ]
        assert "summary_generated_at" in written and written["summary_implementation"]
        assert written["runs"] == runs
        baseline_path.unlink()
        assert tile_extraction.resummarize(path) == 1
    finally:
        tile_extraction.ROOT = ROOT
