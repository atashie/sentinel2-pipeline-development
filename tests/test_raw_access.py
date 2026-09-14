"""Fixture tests for the stage 1 raw access script. No network."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("raw_access", ROOT / "benchmarks" / "raw_access.py")
raw_access = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(raw_access)


def write_geotiff(path: Path, seed: int, size: int = 64) -> np.ndarray:
    rng = np.random.default_rng(seed)
    data = rng.integers(1, 10000, size=(size, size), dtype=np.uint16)
    data[:4, :4] = 0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=1,
        dtype="uint16",
        crs="EPSG:32617",
        transform=from_origin(600000, 3800000, 10, 10),
        nodata=0,
        tiled=True,
        blockxsize=32,
        blockysize=32,
        compress="deflate",
    ) as dataset:
        dataset.write(data, 1)
    return data


def item(collection, keys, uri="S2B_MSIL2A_x.SAFE", with_size=True):
    assets = {}
    for key in keys:
        assets[key] = {
            "href": f"https://bucket/{collection}/{key}.tif",
            "gsd": 10,
            "type": "image/tiff",
            "raster:bands": [
                {"nodata": 0, "scale": 0.0001, "offset": -0.1, "spatial_resolution": 10}
            ],
        }
        if with_size:
            assets[key]["file:size"] = 123
    return {
        "id": f"{collection}-item",
        "collection": collection,
        "properties": {"s2:product_uri": uri, "datetime": "2025-10-15T16:22:49Z"},
        "assets": assets,
    }


def test_group_assets_and_plan():
    assert raw_access.group_assets("60m") == ["coastal", "nir09"]
    assert len(raw_access.group_assets("all")) == 17
    with pytest.raises(ValueError):
        raw_access.group_assets("30m")
    runs = raw_access.plan_runs(["c1", "older"], raw_access.GROUPS, raw_access.MODES, 3)
    assert len(runs) == 60
    assert runs[0] == {"copy": "c1", "group": "10m", "mode": "vsicurl", "repetition": 1}
    assert runs[-1] == {"copy": "older", "group": "all", "mode": "whole-object", "repetition": 3}


def test_resolve_assets_records_missing_keys():
    resolved = raw_access.resolve_assets(item("c", ["coastal"]), ["coastal", "nir09"])
    assert resolved["missing"] == ["nir09"]
    asset = resolved["assets"][0]
    assert asset["href"].endswith("coastal.tif")
    assert asset["gsd"] == 10 and asset["scale"] == 0.0001 and asset["file_size"] == 123
    assert raw_access.resolve_assets({"assets": {}}, ["red"]) == {
        "assets": [],
        "missing": ["red"],
        "skipped": [],
    }


def test_resolve_assets_skips_jpeg2000_links_into_other_buckets():
    fixture = item("sentinel-2-l2a", ["scl"])
    fixture["assets"]["cloud"] = {
        "href": "s3://sentinel-s2-l2a/tiles/17/S/KU/2025/10/15/0/qi/CLD_20m.jp2",
        "type": "image/jp2",
    }
    fixture["assets"]["snow"] = {"href": "https://bucket/x/SNW_20m.jp2", "type": "image/jp2"}
    fixture["assets"]["odd"] = {"href": "https://bucket/x/thing.bin"}
    resolved = raw_access.resolve_assets(fixture, ["scl", "cloud", "snow", "odd", "aot"])
    assert [a["key"] for a in resolved["assets"]] == ["scl"]
    assert resolved["missing"] == ["aot"]
    assert [s["key"] for s in resolved["skipped"]] == ["cloud", "snow", "odd"]
    assert (
        resolved["skipped"][0]["reason"] == "href scheme s3 is outside this HTTPS GeoTIFF benchmark"
    )
    assert "not GeoTIFF" in resolved["skipped"][1]["reason"]
    assert "not a .tif" in resolved["skipped"][2]["reason"]


def test_pair_items_prefers_the_shared_product():
    c1 = [item("sentinel-2-c1-l2a", ["red"], uri="A"), item("sentinel-2-c1-l2a", ["red"], uri="B")]
    older = [item("sentinel-2-l2a", ["red"], uri="B")]
    chosen, note = raw_access.pair_items({"c1": c1, "older": older})
    assert chosen["c1"]["properties"]["s2:product_uri"] == "B"
    assert "same ESA product" in note
    chosen, note = raw_access.pair_items({"c1": [c1[0]], "older": older})
    assert chosen["c1"]["properties"]["s2:product_uri"] == "A"
    assert note.startswith("no shared")
    with pytest.raises(ValueError):
        raw_access.pair_items({"c1": [], "older": older})
    trimmed = raw_access.trim_item(c1[0])
    assert trimmed["product_uri"] == "A" and trimmed["asset_keys"] == ["red"]


@pytest.mark.parametrize("mode", ["vsicurl", "whole-object"])
def test_worker_reads_local_geotiffs(tmp_path, mode):
    first = write_geotiff(tmp_path / "coastal.tif", 1)
    second = write_geotiff(tmp_path / "nir09.tif", 2)
    prefix = "file://" if mode == "whole-object" else ""
    spec = {
        "copy": "c1",
        "group": "60m",
        "mode": mode,
        "repetition": 1,
        "assets": [
            {"key": "coastal", "href": prefix + str(tmp_path / "coastal.tif"), "gsd": 60},
            {"key": "nir09", "href": prefix + str(tmp_path / "nir09.tif"), "gsd": 60},
        ],
        "log_path": str(tmp_path / "run.gdal.log"),
    }
    result = raw_access.run_worker(spec)
    assert result["mode"] == mode and result["totals"]["bands"] == 2
    assert result["totals"]["pixels"] == 2 * 64 * 64
    assert result["totals"]["bytes_in_memory"] == 2 * 64 * 64 * 2
    assert result["wall_seconds"] >= 0 and result["peak_rss_bytes"] > 0
    assert set(result["cpu"]) == {"user", "system"}
    band = result["bands"][0]
    assert band["digest"] == hashlib.sha256(first.tobytes()).hexdigest()
    assert result["bands"][1]["digest"] == hashlib.sha256(second.tobytes()).hexdigest()
    assert band["nodata_count"] == 16 and band["nodata"] == 0
    assert band["block_shape"] == [32, 32] and band["compression"] == "deflate"
    assert band["width"] == 64 and band["dtype"] == "uint16"
    if mode == "vsicurl":
        assert "read_seconds" in band and band["requests"] == 0
    else:
        assert band["http_status"] is None and band["requests"] == 0
        assert band["bytes_requested"] == (tmp_path / "coastal.tif").stat().st_size
        assert "decode_seconds" in band
    assert (tmp_path / "run.gdal.log").exists()


def test_worker_entry_point_prints_json(tmp_path, capsys):
    write_geotiff(tmp_path / "a.tif", 3)
    spec = {
        "copy": "older",
        "group": "60m",
        "mode": "vsicurl",
        "repetition": 2,
        "assets": [{"key": "coastal", "href": str(tmp_path / "a.tif"), "gsd": 60}],
    }
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    assert raw_access.main(["--worker", str(tmp_path / "spec.json")]) == 0
    result = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert result["copy"] == "older" and result["repetition"] == 2
    assert result["bands"][0]["pixels"] == 4096


def test_summarize_reports_medians_and_digest_matches():
    def run(copy, mode, wall, digest, repetition=1, error=False):
        if error:
            return {
                "copy": copy,
                "group": "60m",
                "mode": mode,
                "repetition": repetition,
                "error": "x",
            }
        return {
            "copy": copy,
            "group": "60m",
            "mode": mode,
            "repetition": repetition,
            "wall_seconds": wall,
            "cpu": {"user": 1.0, "system": 0.5},
            "peak_rss_bytes": 100 + wall,
            "bands": [{"key": "coastal", "digest": digest, "open_seconds": 0.0}],
            "totals": {"bytes_requested": 10, "requests": 2, "pixels": 5, "bytes_in_memory": 10},
        }

    results = [
        run("c1", "vsicurl", 3.0, "d1"),
        run("c1", "vsicurl", 1.0, "d1", 2),
        run("c1", "vsicurl", 2.0, "d1", 3),
        run("older", "vsicurl", 5.0, "d2"),
        run("older", "whole-object", 0, "", error=True),
    ]
    summary = raw_access.summarize(results)
    rows = {(r["copy"], r["mode"]): r for r in summary["by_copy_group_mode"]}
    assert rows[("c1", "vsicurl")]["wall_seconds_median"] == 2.0
    assert rows[("c1", "vsicurl")]["read_seconds_median"] == 0.0
    assert rows[("c1", "vsicurl")]["wall_seconds_min"] == 1.0
    assert rows[("c1", "vsicurl")]["peak_rss_bytes_max"] == 103.0
    assert rows[("c1", "vsicurl")]["cpu_seconds_median"] == 1.5
    assert rows[("older", "whole-object")] == {
        "copy": "older",
        "group": "60m",
        "mode": "whole-object",
        "runs": 1,
        "failed": 1,
    }
    assert summary["digest_match_by_band"] == {"coastal": False}
    only_one = raw_access.summarize([run("c1", "vsicurl", 1.0, "d1")])
    assert only_one["digest_match_by_band"] == {"coastal": None}


def test_dry_run_plans_without_network(capsys, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network client created during a dry run")

    monkeypatch.setattr(raw_access.harness, "Client", refuse)
    assert raw_access.main(["--dry-run", "--repeat", "2", "--groups", "60m", "quality"]) == 0
    out = capsys.readouterr().out
    assert "16 runs planned" in out
    assert "quality: scl, aot, wvp, cloud, snow" in out


def test_reusable_result_requires_the_same_run(tmp_path):
    spec = {
        "copy": "c1",
        "group": "60m",
        "mode": "vsicurl",
        "repetition": 1,
        "assets": [
            {"key": "coastal", "href": "https://b/x/B01.tif"},
            {"key": "nir09", "href": "https://b/x/B09.tif"},
        ],
    }
    saved = {
        "copy": "c1",
        "group": "60m",
        "mode": "vsicurl",
        "repetition": 1,
        "wall_seconds": 1.0,
        "gdal_env": raw_access.GDAL_ENV,
        "bands": [
            {"key": "coastal", "href": "https://b/x/B01.tif"},
            {"key": "nir09", "href": "https://b/x/B09.tif"},
        ],
    }
    name = "001-c1-60m-vsicurl-1"
    assert raw_access.reusable_result(None, name, spec) == (None, None)
    assert raw_access.reusable_result(tmp_path, name, spec) == (None, None)
    (tmp_path / f"{name}.result.json").write_text(json.dumps(saved))
    result, reason = raw_access.reusable_result(tmp_path, name, spec)
    assert reason is None and result["wall_seconds"] == 1.0
    assert result["reused_from"].endswith(f"{name}.result.json")
    other_date = {
        **spec,
        "assets": [{"key": "coastal", "href": "https://b/y/B01.tif"}, spec["assets"][1]],
    }
    assert raw_access.reusable_result(tmp_path, name, other_date) == (
        None,
        "assets differ: another product, date, or band set",
    )
    fewer = {**spec, "assets": spec["assets"][:1]}
    assert raw_access.reusable_result(tmp_path, name, fewer)[1].startswith("assets differ")
    (tmp_path / f"{name}.result.json").write_text(json.dumps({**saved, "gdal_env": {}}))
    assert raw_access.reusable_result(tmp_path, name, spec) == (
        None,
        "reader configuration differs",
    )
    (tmp_path / f"{name}.result.json").write_text(json.dumps({**saved, "repetition": 2}))
    assert raw_access.reusable_result(tmp_path, name, spec) == (None, "repetition differs")
    (tmp_path / f"{name}.result.json").write_text(json.dumps({"copy": "c1", "error": "boom"}))
    assert raw_access.reusable_result(tmp_path, name, spec) == (None, "saved run failed")
