"""Fixture tests for the fallback survey's pure logic. No network."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fallback_survey", ROOT / "benchmarks" / "fallback_survey.py"
)
fallback_survey = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fallback_survey)

COG = "image/tiff; application=geotiff; profile=cloud-optimized"
HOST = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/10/S/GJ/2022/6/x"


def older_item(item_id="S2A_10SGJ_20220630_0_L2A", bands=None, scl=True, jp2=True, cloud=False):
    bands = fallback_survey.REFLECTANCE_BANDS if bands is None else bands
    assets = {}
    for band in bands:
        assets[band] = {
            "type": COG,
            "href": f"{HOST}/{band}.tif",
            "raster:bands": [{"scale": 0.0001, "offset": -0.1}],
        }
        if jp2:
            assets[f"{band}-jp2"] = {
                "type": "image/jp2",
                "href": f"s3://sentinel-s2-l2a/tiles/{band}.jp2",
            }
    if scl:
        assets["scl"] = {"type": COG, "href": f"{HOST}/SCL.tif"}
    assets["aot"] = {"type": COG, "href": f"{HOST}/AOT.tif"}
    assets["wvp"] = {"type": COG, "href": f"{HOST}/WVP.tif"}
    if cloud:
        assets["cloud"] = {"type": "image/jp2", "href": "s3://sentinel-s2-l2a/tiles/CLD.jp2"}
    return {
        "id": item_id,
        "properties": {
            "datetime": "2022-06-30T18:53:38Z",
            "platform": "sentinel-2a",
            "s2:processing_baseline": "04.00",
            "s2:sequence": "0",
            "earthsearch:boa_offset_applied": True,
            "processing:software": {"sentinel2-to-stac": "0.1.0"},
        },
        "assets": assets,
    }


def test_spans_groups_contiguous_months():
    assert fallback_survey.spans(
        ["2022-01", "2022-02", "2022-04", "2022-05", "2022-06", "2023-01"]
    ) == [
        ("2022-01", "2022-02"),
        ("2022-04", "2022-06"),
        ("2023-01", "2023-01"),
    ]
    assert fallback_survey.spans(["2021-12", "2022-01"]) == [("2021-12", "2022-01")]
    assert fallback_survey.span_dates("2022-11", "2022-12") == ("2022-11-01", "2022-12-31")
    assert fallback_survey.span_dates("2024-02", "2024-02") == ("2024-02-01", "2024-02-29")


def test_classify_assets_counts_geotiffs_in_the_public_bucket():
    item = fallback_survey.classify_assets(older_item())
    assert item["bands_cog"] == 12
    assert item["bands_cog_complete"] is True
    assert item["quality"] == {
        "scl": "cog",
        "aot": "cog",
        "wvp": "cog",
        "cloud": None,
        "snow": None,
    }
    assert len(item["jp2_assets"]) == 12
    assert item["hosts"]["sentinel-cogs.s3.us-west-2.amazonaws.com"] == 15
    assert item["red_offset"] == -0.1
    assert item["offset_applied"] is True
    assert set(item["urls"]) == {"scl", "red"}
    partial = fallback_survey.classify_assets(older_item(bands=["red", "green"], scl=False))
    assert partial["bands_cog"] == 2
    assert partial["bands_cog_complete"] is False
    assert partial["quality"]["scl"] is None
    with_cloud = fallback_survey.classify_assets(older_item(cloud=True))
    assert with_cloud["quality"]["cloud"] == "jp2"


def test_coverage_class_and_best_item():
    full = fallback_survey.classify_assets(older_item("full"))
    partial = fallback_survey.classify_assets(older_item("part", bands=["red"], scl=False))
    jp2 = fallback_survey.classify_assets(older_item("jp2", bands=[], scl=False))
    jp2["cog_assets"] = []
    jp2["jp2_assets"] = ["red-jp2"]
    assert fallback_survey.coverage_class([]) == "none"
    assert fallback_survey.coverage_class([partial]) == "partial_cog"
    assert fallback_survey.coverage_class([partial, full]) == "complete_cog"
    assert fallback_survey.coverage_class([jp2]) == "jp2_only"
    assert fallback_survey.best_item([partial, full])["id"] == "full"
    assert fallback_survey.best_item([]) is None
