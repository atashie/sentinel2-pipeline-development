"""Stage 4 fixtures. Only synthetic local pixels, no provider access."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pyproj
import pytest
import rasterio
from affine import Affine
from shapely.geometry import box, mapping
from test_lake_extraction import BANDS, EPSG, GRID, X0, Y0, feature, make_item

from s2proto import masks

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cross_tile_extraction", ROOT / "benchmarks/cross_tile_extraction.py"
)
cross = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cross
SPEC.loader.exec_module(cross)


def item_for(directory, grid, tile, group="datatake-one", seed=1):
    directory.mkdir(parents=True, exist_ok=True)
    item = make_item(directory, tile=tile)
    footprint = cross.transform(grid.extent(), grid.epsg, 4326, 100)
    item["geometry"] = mapping(footprint)
    item["bbox"] = list(footprint.bounds)
    item["id"] = f"{group}-{tile}"
    item["properties"].update(
        {
            "s2:datatake_id": group,
            "s2:datastrip_id": f"strip-{tile}",
            "platform": "sentinel-2b",
            "proj:epsg": grid.epsg,
        }
    )
    for key, resolution in BANDS.items():
        asset = item["assets"][key]
        asset["proj:shape"] = list(grid.shape(resolution))
        asset["proj:transform"] = list(grid.transform(resolution))[:6]
        height, width = grid.shape(resolution)
        dtype = "uint8" if key == "scl" else "uint16"
        data = (
            np.arange(height * width).reshape(height, width) % (10 if key == "scl" else 10000)
            + seed
        ).astype(dtype)
        data[20:40, 20:40] = 0
        with rasterio.open(
            asset["href"],
            "w",
            driver="GTiff",
            width=width,
            height=height,
            count=1,
            dtype=dtype,
            crs=grid.epsg,
            transform=grid.transform(resolution),
            nodata=0,
            tiled=True,
            blockxsize=16,
            blockysize=16,
        ) as dataset:
            dataset.write(data, 1)
        asset["file:size"] = Path(asset["href"]).stat().st_size
    return item


def versioned(lake):
    lake["properties"]["polygon_version"] = 1
    return lake


@pytest.fixture(scope="module")
def scene(tmp_path_factory):
    directory = tmp_path_factory.mktemp("cross-tiles")
    west = item_for(directory / "west", GRID, "17SKU")
    east_grid = masks.TileGrid(EPSG, X0 + 1200, Y0, 240, 240)
    east = item_for(directory / "east", east_grid, "17SKV", seed=2)
    lakes = [
        versioned(
            feature("crossing", box(X0 + 700, Y0 - 1400, X0 + 2800, Y0 - 1100), 1000, "large")
        ),
        versioned(feature("overlap", box(X0 + 1600, Y0 - 800, X0 + 1630, Y0 - 770), 30)),
        versioned(feature("empty-west", box(X0 + 2498, Y0 - 600, X0 + 2518, Y0 - 580), 30)),
    ]
    plan = cross.freeze_plan(lakes, {"fixture": [west, east]}, repeat=1)
    return {"directory": directory, "items": [west, east], "lakes": lakes, "plan": plan}


def test_selection_union_overlap_and_native_identity(scene):
    plan = scene["plan"]
    assert plan["ready"]
    cross.verify_plan(plan)
    assert len(plan["expected"]) == 3 * 2 * 5
    assert len(plan["order"]) == 2 * (3 + 2)
    selected = plan["selection"]["fixture"]
    anchor = selected["coverage"]["crossing"]
    assert anchor["support_uncovered_fraction"] < cross.TOLERANCE
    assert anchor["support_overlap_m2"] > 0
    assert all(0 < m["polygon_share"] < 1 for m in anchor["members"])
    assert selected["roles"]["crossing"]["primary"] is None
    assert selected["roles"]["empty-west"]["primary"] == "17SKV"
    assert selected["roles"]["overlap"]["primary"] is None
    near = next(m for m in selected["coverage"]["empty-west"]["members"] if m["tile"] == "17SKU")
    assert near["polygon_share"] == 0 and near["buffered_share"] > 0
    assert anchor["geometry_check"]["relative_change_bound"] <= cross.TOLERANCE / 8
    assert plan["transfer_estimate"]["bytes"] > 0


def test_cannot_pair_acquisitions_or_silently_fill_missing_tiles(scene):
    items = copy.deepcopy(scene["items"])
    items[1]["properties"]["s2:datatake_id"] = "another-date"
    selected = cross.select_region(items, scene["lakes"])
    assert selected["selected_group"] is None
    assert all(not g["eligible"] and len(g["missing_tiles"]) == 1 for g in selected["groups"])
    items[1]["properties"].pop("s2:datatake_id")
    selected = cross.select_region(items, scene["lakes"])
    assert selected["ungrouped"] == [items[1]["id"]]
    assert selected["selected_group"] is None


def test_missing_redundant_tile_is_reported_and_triple_overlap_counted_once(scene):
    pond = scene["lakes"][1]
    items = copy.deepcopy(scene["items"])
    items[1]["properties"]["s2:datatake_id"] = "other"
    selected = cross.select_region(items, [pond])
    assert selected["selected_group"]
    assert all(g["eligible"] and len(g["missing_tiles"]) == 1 for g in selected["groups"])
    third = copy.deepcopy(scene["items"][0])
    third["id"] = "third"
    third["properties"]["grid:code"] = "MGRS-17SKW"
    selected = cross.select_region([*scene["items"], third], [pond])
    c = selected["coverage"]["overlap"]
    assert c["support_overlap_m2"] == pytest.approx(c["support_area_m2"])
    assert c["footprint_overlap_m2"] == pytest.approx(c["support_area_m2"])


def test_group_ranking_revision_asset_failure_and_platform(scene, monkeypatch):
    older = copy.deepcopy(scene["items"])
    newer = copy.deepcopy(scene["items"])
    for item in newer:
        item["id"] += "-new"
        item["properties"].update({"s2:datatake_id": "new", "datetime": "2025-10-20T16:00:00Z"})
    assert cross.select_region(older + newer, scene["lakes"])["selected_group"] == "new"
    # Sub-tolerance numerical residuals cannot override cloud and date tie-breakers.
    coverage = cross.coverage

    def tiny_residual(context, items):
        row = coverage(context, items)
        if any(item["id"].endswith("-new") for item in items.values()):
            row["footprint_uncovered_fraction"] = cross.TOLERANCE / 2
        return row

    with monkeypatch.context() as patch:
        patch.setattr(cross, "coverage", tiny_residual)
        selected = cross.select_region(older + newer, scene["lakes"])
        assert selected["selected_group"] == "new"
        assert selected["coverage"]["crossing"]["footprint_uncovered_fraction"] > 0
    for item in newer:
        item["properties"]["eo:cloud_cover"] = 50
    assert cross.select_region(older + newer, scene["lakes"])["selected_group"] == "datatake-one"
    # An individual footprint shortfall no longer outranks complete union coverage.
    older[0]["geometry"] = mapping(
        cross.transform(box(X0, Y0 - 2400, X0 + 1500, Y0), EPSG, 4326, 100)
    )
    assert cross.select_region(older + newer, scene["lakes"])["selected_group"] == "datatake-one"
    # An actual union gap still precedes clouds and sensing time as a coarse heuristic.
    older[0]["geometry"] = mapping(
        cross.transform(box(X0, Y0 - 2400, X0 + 800, Y0), EPSG, 4326, 100)
    )
    assert cross.select_region(older + newer, scene["lakes"])["selected_group"] == "new"
    revision = copy.deepcopy(newer[0])
    revision["id"] = "latest-revision"
    revision["properties"]["created"] = "2026-01-01T00:00:00Z"
    chosen = cross.select_region(newer + [revision], scene["lakes"])
    assert "latest-revision" in chosen["selected_items"]
    revision["assets"].pop("scl")
    chosen = cross.select_region(newer + [revision], scene["lakes"])
    assert newer[0]["id"] in chosen["selected_items"]
    assert "latest-revision" not in chosen["selected_items"]
    assert any("unusable assets" in r["reason"] for r in chosen["groups"][0]["discarded"])
    newer[1]["properties"]["platform"] = "sentinel-2c"
    assert cross.select_region(newer, scene["lakes"])["selected_group"] is None


def test_missing_geometry_excludes_group_and_rotated_asset_is_rejected(scene):
    items = copy.deepcopy(scene["items"])
    items[1]["geometry"] = None
    selection = cross.select_region(items, scene["lakes"])
    assert selection["selected_group"] is None and selection["rejected"]
    items = copy.deepcopy(scene["items"])
    items[1]["assets"]["red"]["proj:transform"][1] = 1
    with pytest.raises(ValueError, match="different native grid"):
        cross.native_assets(items[1], cross.BANDS)


def test_frozen_plan_tamper_rotation_and_transfer_unknown(scene):
    plan = cross.freeze_plan(scene["lakes"], {"fixture": scene["items"]}, repeat=3)
    first = [next(u for u in plan["order"] if u["repetition"] == r) for r in (1, 2, 3)]
    assert [(u["path"], u["method"]) for u in first] == [
        ("lake-first", "raster-mask"),
        ("tile-first", "lazy-stack"),
        ("lake-first", "raster-mask"),
    ]
    plan["scenes"][0]["grid"]["x0"] += 1
    with pytest.raises(ValueError, match="digest"):
        cross.verify_plan(plan)
    assert (
        cross.freeze_plan(scene["lakes"], {"fixture": scene["items"]}, transfer_reference=None)[
            "transfer_estimate"
        ]["bytes"]
        is None
    )


def test_native_lazy_guard_refuses_merge_shift_resample_before_load(scene, monkeypatch):
    import odc.stac
    import pystac
    from odc.geo.geobox import GeoBox

    calls = []
    monkeypatch.setattr(odc.stac, "load", lambda items, **kwargs: calls.append((items, kwargs)))
    item = pystac.Item.from_dict(scene["items"][0])
    geobox = GeoBox(GRID.shape(10), GRID.transform(10), f"EPSG:{EPSG}")
    cross.stage3.load_native_item([item], ["red"], geobox, GRID, 128)
    assert len(calls) == 1 and len(calls[0][0]) == 1
    bad_boxes = [
        GeoBox((100, 100), Affine(10, 0, X0 + 1, 0, -10, Y0), f"EPSG:{EPSG}"),
        GeoBox((100, 100), Affine(30, 0, X0, 0, -30, Y0), f"EPSG:{EPSG}"),
        GeoBox((100, 100), GRID.transform(10), "EPSG:32616"),
    ]
    for candidate in bad_boxes:
        with pytest.raises(ValueError):
            cross.stage3.load_native_item([item], ["red"], candidate, GRID, 128)
    with pytest.raises(ValueError, match="exactly one"):
        cross.stage3.load_native_item([item, item], ["red"], geobox, GRID, 128)
    assert len(calls) == 1


def prepare_locally(plan, directory):
    """Use real preparation, avoiding many interpreter startups in most tests."""
    prepared = {}
    for scene in plan["scenes"]:
        sid = f"{scene['region']}-{scene['tile']}"
        cross.write_json(directory / "items" / f"{cross.scene_id(scene)}.json", scene["item"])
        prepared[sid] = []
        for lid in scene["members"]:
            lake = next(lake for lake in plan["lakes"] if cross.lake_id(lake) == lid)
            spec = {
                "tile": scene["tile"],
                "water_body_id": lid,
                "geometry": lake["geometry"],
                "polygon_sha256": cross.stage2.polygon_digest(lake),
                "grid": scene["grid"],
                "resolutions": [10, 20, 60],
                "mask_parameters": cross.stage2.MASK_PARAMETERS,
                "implementation": cross.IMPLEMENTATION,
                **{
                    f"{kind}_paths": {
                        str(r): str(directory / kind / f"{sid}-{lid}-{r}.npz") for r in (10, 20, 60)
                    }
                    for kind in ("mask", "index")
                },
            }
            result = cross.stage3.prepare_worker(spec)
            name = f"prepare-{scene['tile']}-{lid}"
            cross.write_json(directory / f"{name}.spec.json", spec)
            cross.write_json(directory / f"{name}.result.json", result)
            prepared[sid].append(
                {
                    "water_body_id": lid,
                    "size_label": "fixture",
                    "geometry": lake["geometry"],
                    "mask_paths": spec["mask_paths"],
                    "index_paths": spec["index_paths"],
                    "mask_sha256": {r: v["mask_sha256"] for r, v in result["resolutions"].items()},
                }
            )
    return prepared


@pytest.fixture(scope="module")
def measured(scene, tmp_path_factory):
    directory = tmp_path_factory.mktemp("cross-workers")
    plan = scene["plan"]
    prepared = prepare_locally(plan, directory)
    runs = []
    for number, unit in enumerate(plan["order"]):
        spec = cross.worker_spec(plan, unit, prepared, directory, number)
        runs.append(cross.extract_worker(spec))
    return {"plan": plan, "runs": runs, "directory": directory, "prepared": prepared}


def test_both_paths_and_readers_preserve_all_contributions_including_empty(measured):
    summary = cross.summarize(measured["plan"], measured["runs"])
    assert summary["complete"] and summary["equal"]
    assert all(e["matches"] for e in summary["equality"])
    assert all(m["clean_repetitions"] == 1 for m in summary["medians"])
    records = [r for run in measured["runs"] for r in run["contributions"]]
    empty = [r for r in records if r["key"][0] == "empty-west" and r["key"][3] == "17SKU"]
    assert len(empty) == 4 * 5 and all(r["status"] == "empty" for r in empty)
    assert any(r["nodata_extracted"] > 0 for r in records)
    keys = [r["key"] for r in measured["runs"][0]["contributions"]]
    assert keys == sorted(keys)
    assert all(run["gdal_cache_bytes"] == 512 * 1024**2 for run in measured["runs"])


def test_missing_failed_pressure_and_digest_mismatch_cannot_pass(measured):
    runs = copy.deepcopy(measured["runs"])
    runs.pop(0)
    summary = cross.summarize(measured["plan"], runs)
    assert not summary["complete"] and not summary["equal"]
    assert summary["medians"][0]["wall_seconds"] is None
    runs = copy.deepcopy(measured["runs"])
    runs[0]["host_memory"] = {"pressure": True}
    summary = cross.summarize(measured["plan"], runs)
    assert summary["complete"] and summary["equal"]
    assert summary["medians"][0]["clean_repetitions"] == 0
    runs = copy.deepcopy(measured["runs"])
    runs[0]["contributions"][0]["status"] = "failed"
    assert not cross.summarize(measured["plan"], runs)["complete"]
    runs = copy.deepcopy(measured["runs"])
    runs[-1]["contributions"][0]["digest_pixels"] = "wrong pixel order"
    assert not cross.summarize(measured["plan"], runs)["equal"]


def test_canonical_order_rejects_retries_and_conflicts(measured):
    records = measured["runs"][0]["contributions"]
    assert cross.canonical(list(reversed(records))) == records
    with pytest.raises(ValueError, match="repeated"):
        cross.canonical(records + [records[0]])
    changed = {**records[0], "digest_all": "wrong"}
    with pytest.raises(ValueError, match="conflicting"):
        cross.canonical(records + [changed])
    with pytest.raises(ValueError, match="duplicate worker"):
        cross.summarize(measured["plan"], measured["runs"] + [measured["runs"][0]])


def test_reuse_requires_geometry_and_hashes_but_not_acquisition(measured, tmp_path):
    scene = measured["plan"]["scenes"][0]
    lid = scene["members"][0]
    name = f"prepare-{scene['tile']}-{lid}"
    original = json.loads((measured["directory"] / f"{name}.spec.json").read_text())
    spec = copy.deepcopy(original)
    for kind in ("mask", "index"):
        spec[f"{kind}_paths"] = {
            r: str(tmp_path / kind / Path(p).name) for r, p in original[f"{kind}_paths"].items()
        }
    spec["implementation"]["script"] = 999
    result, _ = cross.reuse_preparation(measured["directory"], name, spec)
    assert result is not None
    spec["polygon_sha256"] = "changed"
    assert cross.reuse_preparation(measured["directory"], name, spec)[0] is None
    spec["polygon_sha256"] = original["polygon_sha256"]
    # Corrupt an isolated saved copy, preserving the shared fixture.
    saved = json.loads((measured["directory"] / f"{name}.result.json").read_text())
    cross.write_json(tmp_path / f"{name}.spec.json", spec)
    cross.write_json(tmp_path / f"{name}.result.json", saved)
    Path(spec["mask_paths"]["10"]).write_bytes(b"corrupt")
    assert "hash differs" in cross.reuse_preparation(tmp_path, name, original)[1]


def test_cross_crs_graphs_remain_separate_and_geometry_refines(scene, tmp_path, monkeypatch):
    import odc.stac

    transformer = pyproj.Transformer.from_crs(EPSG, 32616, always_xy=True)
    x, y = transformer.transform(X0 + 1700, Y0 - 800)
    grid = masks.TileGrid(32616, round((x - 1200) / 60) * 60, round((y + 1200) / 60) * 60, 240, 240)
    other = item_for(tmp_path / "zone16", grid, "16SGD", seed=3)
    lake = scene["lakes"][1]
    plan = cross.freeze_plan([lake], {"fixture": [scene["items"][0], other]}, repeat=1)
    assert plan["ready"] and len(plan["scenes"]) == 2
    native_load = odc.stac.load
    calls = []

    def inspect(items, **kwargs):
        calls.append((len(items), kwargs["geobox"].crs.epsg))
        return native_load(items, **kwargs)

    monkeypatch.setattr(odc.stac, "load", inspect)
    prepared = prepare_locally(plan, tmp_path)
    runs = [
        cross.extract_worker(cross.worker_spec(plan, unit, prepared, tmp_path, n))
        for n, unit in enumerate(plan["order"])
    ]
    assert cross.summarize(plan, runs)["equal"]
    assert set(calls) == {(1, EPSG), (1, 32616)}
    assert all(
        c["geometry_check"]["relative_change_bound"] <= cross.TOLERANCE / 8
        for c in plan["selection"]["fixture"]["coverage"].values()
    )
    # A long inter-zone edge changes when densified. The final refinement converges.
    long = masks.TileGrid(32616, 700000, 3800000)
    coarse = cross.transform(long.extent(), 32616, EPSG, 200000)
    fine = cross.transform(long.extent(), 32616, EPSG, 500)
    assert coarse.symmetric_difference(fine).area / fine.area > cross.TOLERANCE


def test_guarded_subprocess_and_offline_cli(measured, tmp_path, monkeypatch, capsys):
    # This exercises the actual new worker entry point and the shared memory sampler.
    plan = measured["plan"]
    spec = cross.worker_spec(plan, plan["order"][0], measured["prepared"], tmp_path, 0)
    for tile in spec["tiles"]:
        tile["item_path"] = str(measured["directory"] / "items" / Path(tile["item_path"]).name)
    result = cross.stage3.run_in_subprocess(
        "extract", spec, tmp_path / "worker.json", {"reserve_bytes": 0}, script=Path(cross.__file__)
    )
    assert result["contributions"] and "error" not in result
    assert result["host_memory"]["samples"] > 0
    assert result["host_memory"]["pressure_bytes"] == 128 * 1024**2
    stopped = cross.stage3.run_in_subprocess(
        "extract",
        spec,
        tmp_path / "stopped.json",
        {"reserve_bytes": 0, "budget_bytes": 1, "poll_seconds": 0.01},
        script=Path(cross.__file__),
    )
    assert stopped["memory_stop"] and "contributions" not in stopped
    monkeypatch.setattr(cross.harness, "Client", lambda **kwargs: pytest.fail("unexpected network"))
    assert cross.main(["--dry-run"]) == 0
    assert '"lakes": 11' in capsys.readouterr().out


def test_catalog_pagination_does_not_truncate_or_hide_repeated_pages(tmp_path):
    class Client:
        def __init__(self):
            self.calls = 0

        def post_json(self, url, body, label):
            self.calls += 1
            return {
                "features": [{"id": self.calls}],
                "links": [{"rel": "next", "merge": True, "body": {"token": self.calls}}]
                if self.calls < 22
                else [],
            }

    client = Client()
    assert len(cross.search_catalog(client, [0, 0, 1, 1], tmp_path)) == 22
    assert len(list(tmp_path.glob("page-*.json"))) == 22

    class Loop:
        def post_json(self, url, body, label):
            return {"features": [], "links": [{"rel": "next", "body": body}]}

    with pytest.raises(ValueError, match="repeated"):
        cross.search_catalog(Loop(), [0, 0, 1, 1], tmp_path / "loop")


def test_full_local_runner_saves_frozen_evidence_and_reuses_masks(scene, measured, tmp_path):
    lake = scene["lakes"][1]
    catalog = tmp_path / "catalog.json"
    manifest = tmp_path / "manifest.geojson"
    plan_path = tmp_path / "plan.json"
    output = tmp_path / "result.json"
    cross.write_json(catalog, {"fixture": scene["items"]})
    cross.write_json(manifest, {"type": "FeatureCollection", "features": [lake]})
    assert (
        cross.main(
            [
                "--catalog",
                str(catalog),
                "--manifest",
                str(manifest),
                "--regions",
                "fixture",
                "--repeat",
                "1",
                "--plan",
                str(plan_path),
                "--raw-dir",
                str(tmp_path / "metadata"),
            ]
        )
        == 0
    )
    assert (
        cross.main(
            [
                "--run-plan",
                str(plan_path),
                "--raw-dir",
                str(tmp_path / "raw"),
                "--output",
                str(output),
                "--reuse-masks",
                str(measured["directory"]),
            ]
        )
        == 0
    )
    result = json.loads(output.read_text())
    assert result["summary"]["complete"] and result["summary"]["equal"]
    assert len(result["runs"]) == 2 * (1 + 2)
    assert all(p["reused"] for p in result["preparation"].values())
    assert all(r["host_memory"]["samples"] for r in result["runs"])
    assert len(list(Path(result["raw_dir"]).glob("run-*.spec.json"))) == 6
    assert cross.main(["--resummarize", str(output)]) == 0
    assert json.loads(output.read_text())["summary"]["equal"]
    with pytest.raises(ValueError, match="already exists"):
        cross.main(["--run-plan", str(plan_path), "--output", str(output)])


def test_failed_asset_and_log_diagnostics_are_explicit(measured, tmp_path):
    plan = measured["plan"]
    spec = cross.worker_spec(plan, plan["order"][0], measured["prepared"], tmp_path, 0)
    # A frozen input lost after selection must fail without shrinking the expected key set.
    for tile in spec["tiles"]:
        tile["item_path"] = str(tmp_path / "missing-item.json")
    run = cross.extract_worker(spec)
    assert len(run["contributions"]) == len(spec["expected"])
    assert all(
        r["status"] == "failed" and "FileNotFoundError" in r["error"] for r in run["contributions"]
    )
    path = tmp_path / "fixture.gdal.log"
    path.write_text(
        "VSICURL: Downloading 0-100 (https://example.test/a.tif)...\n" * 2 + "Operation timed out\n"
    )
    diagnostic = cross.log_diagnostics(path)
    assert diagnostic["repeated_ranges"][0]["count"] == 2
    assert diagnostic["timeouts_or_retries"][0]["line"] == 3


def test_complex_pilot_polygon_geometry_without_imagery(tmp_path):
    lake = cross.stage2.load_lakes(cross.stage2.MANIFEST, lake_ids=["nhd-34974901"])[0]
    polygon = masks.project(lake["geometry"], 32616)
    center = polygon.representative_point()
    grid = masks.TileGrid(
        32616, round((center.x - 55000) / 60) * 60, round((center.y + 55000) / 60) * 60
    )
    # Metadata only. This wide tile tests the real shoreline in another UTM zone.
    item = make_item(tmp_path, tile="16SGD")
    item["geometry"] = mapping(cross.transform(grid.extent(), grid.epsg, 4326, 500))
    context = cross.geometry_context(lake, {"16SGD": grid}, [item])
    covered = cross.coverage(context, {"16SGD": item})
    assert covered["reference_epsg"] == 32617
    assert covered["support_uncovered_fraction"] < cross.TOLERANCE
    assert covered["geometry_check"]["roundtrip_relative_error"] < cross.TOLERANCE
    assert covered["support_area_m2"] > covered["polygon_area_m2"]


def test_alternative_catalog_revisions_do_not_accumulate_geometry_error(tmp_path):
    lake = cross.stage2.load_lakes(cross.stage2.MANIFEST, lake_ids=["nhd-120024129"])[0]
    polygon = masks.project(lake["geometry"], EPSG)
    center = polygon.representative_point()
    grid = masks.TileGrid(
        EPSG, round((center.x - 55000) / 60) * 60, round((center.y + 55000) / 60) * 60
    )
    item = make_item(tmp_path, tile="17RNK")
    item["properties"].update({"s2:datatake_id": "one-group", "s2:datastrip_id": "one-strip"})
    item["geometry"] = mapping(cross.transform(grid.extent(), grid.epsg, 4326, 500))
    single = cross.geometry_context(lake, {"17RNK": grid}, [item])
    alternatives = [{**item, "id": f"revision-{n}"} for n in range(100)]
    many = cross.geometry_context(lake, {"17RNK": grid}, alternatives)
    assert single["audit"] == many["audit"]
    assert single["audit"]["relative_change_bound"] > 0
    # Item identities differ, while all geometric results agree.
    a = cross.coverage(single, {item["id"]: item})
    b = cross.coverage(many, {alternatives[-1]["id"]: alternatives[-1]})
    a.pop("products")
    b.pop("products")
    assert a == b


def test_split_datastrips_survive_selection_preparation_and_both_paths(tmp_path, monkeypatch):
    first = item_for(tmp_path / "first", GRID, "17SKU", seed=1)
    second = item_for(tmp_path / "second", GRID, "17SKU", seed=20)
    first["id"] += ".part1"
    second["id"] += ".part2"
    second["properties"]["s2:datastrip_id"] = "second-strip"
    second["properties"]["created"] = "2026-01-01T00:00:00Z"
    for item, lo, hi in [(first, 0, 1600), (second, 800, 2400)]:
        footprint = box(X0 + lo, Y0 - 2400, X0 + hi, Y0)
        item["geometry"] = mapping(cross.transform(footprint, EPSG, 4326, 100))
        for asset in item["assets"].values():
            if not asset.get("href", "").endswith(".tif"):
                continue
            with rasterio.open(asset["href"], "r+") as dataset:
                data = dataset.read(1)
                resolution = round(dataset.res[0])
                data[:, : lo // resolution] = 0
                data[:, hi // resolution :] = 0
                dataset.write(data, 1)
    lake = versioned(feature("split", box(X0 + 300, Y0 - 1400, X0 + 2100, Y0 - 1100), 1000))
    plan = cross.freeze_plan([lake], {"fixture": [first, second]}, repeat=1)
    assert plan["ready"] and len(plan["scenes"]) == 2
    assert len(plan["expected"]) == 10 and len(plan["order"]) == 6
    spatial = plan["selection"]["fixture"]["coverage"]["split"]
    assert spatial["footprint_uncovered_fraction"] < cross.TOLERANCE
    assert spatial["support_overlap_m2"] == 0  # one tile, two product footprints
    assert spatial["footprint_overlap_m2"] > 0
    assert all(0 < p["support_in_footprint"] < 1 for p in spatial["products"])
    assert not plan["selection"]["fixture"]["groups"][0]["discarded"]
    calls = []

    def prepare(mode, spec, *_args):
        assert mode == "prepare"
        calls.append(spec)
        return cross.stage3.prepare_worker(spec)

    monkeypatch.setattr(cross.stage3, "run_in_subprocess", prepare)
    preparation, prepared = cross.prepare(plan, tmp_path, None)
    assert len(preparation) == len(calls) == 1  # same polygon and grid reuse one mask
    for scene in plan["scenes"]:
        cross.write_json(tmp_path / "items" / f"{cross.scene_id(scene)}.json", scene["item"])
    runs, paths = [], []
    for n, unit in enumerate(plan["order"]):
        spec = cross.worker_spec(plan, unit, prepared, tmp_path, n)
        paths.extend(t["log_path"] for t in spec["tiles"])
        runs.append(cross.extract_worker(spec))
    assert len(paths) == len(set(paths))
    summary = cross.summarize(plan, runs)
    assert summary["complete"] and summary["equal"]
    first_run = runs[0]["contributions"]
    assert {c["key"][4] for c in first_run} == {first["id"], second["id"]}
    assert len({c["digest_all"] for c in first_run if c["key"][5] == "red"}) == 2


def test_unknown_datastrip_never_deduplicates_and_footprint_never_removes_member(scene):
    items = [copy.deepcopy(scene["items"][0]) for _ in range(2)]
    for i, item in enumerate(items):
        item["id"] = f"unknown-{i}"
        item["properties"].pop("s2:datastrip_id")
    # A coarse footprint can omit valid lake pixels. Keep the native tile candidate.
    items[1]["geometry"] = mapping(
        cross.transform(box(X0, Y0 - 2400, X0 + 100, Y0), EPSG, 4326, 100)
    )
    lake = scene["lakes"][1]
    plan = cross.freeze_plan([lake], {"fixture": items}, repeat=1)
    assert len(plan["scenes"]) == 2 and len(plan["expected"]) == 10
    products = plan["selection"]["fixture"]["coverage"]["overlap"]["products"]
    assert [p["support_in_footprint"] for p in products] == pytest.approx([1, 0])


def test_transfer_estimate_uses_workload_totals_and_matching_settings(scene, tmp_path):
    plan = scene["plan"]
    reference = tmp_path / "reference.json"
    workloads = [
        {"path": path, "method": method, "clean": True, "totals": {"bytes_requested": value}}
        for path in plan["paths"]
        for method in plan["methods"]
        for value in (100, 200, 900)
    ]
    saved = {"plan": plan, "summary": {"memberships": 3, "workloads": workloads}}
    cross.write_json(reference, saved)
    estimate = cross.transfer_estimate(plan, reference)
    assert estimate["bytes"] == 4 * 200 * 2  # six memberships vs three in the reference
    assert estimate["observed_rate_range_bytes"] == [4 * 100 * 2, 4 * 900 * 2]
    assert estimate["reference_sha256"] == cross.file_digest(reference)
    saved["plan"] = {**plan, "chunk": plan["chunk"] // 2}
    cross.write_json(reference, saved)
    assert cross.transfer_estimate(plan, reference)["bytes"] is None
    cross.write_json(reference, {"plan": plan, "runs": []})
    assert cross.transfer_estimate(plan, reference)["bytes"] is None
