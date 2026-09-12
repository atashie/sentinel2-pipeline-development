"""Fixture tests for the gap survey's pure logic. No network."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gap_survey", ROOT / "benchmarks" / "gap_survey.py")
gap_survey = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gap_survey)


def es_feature(item_id, dt, platform="sentinel-2a", baseline="05.10", **extra):
    props = {
        "datetime": dt,
        "platform": platform,
        "grid:code": "MGRS-10SGJ",
        "s2:processing_baseline": baseline,
        "s2:sequence": "0",
        "processing:software": {"sentinel-2-c1-l2a-to-stac": "v2024.02.01"},
        "earthsearch:boa_offset_applied": False,
    }
    props.update(extra)
    return {"id": item_id, "collection": "sentinel-2-c1-l2a", "properties": props}


def cdse_feature(item_id, dt, platform="sentinel-2a", version="05.10"):
    return {
        "id": item_id,
        "properties": {
            "datetime": dt,
            "platform": platform,
            "grid:code": "MGRS-10SGJ",
            "processing:version": version,
        },
    }


def test_month_range_is_inclusive_and_ordered():
    assert gap_survey.month_range("2021-11-15", "2022-02-01") == [
        "2021-11",
        "2021-12",
        "2022-01",
        "2022-02",
    ]
    with pytest.raises(ValueError):
        gap_survey.month_range("2022-01-01", "2021-01-01")


def test_platform_letter_and_tile_code():
    assert gap_survey.platform_letter("sentinel-2b", "x") == "b"
    assert gap_survey.platform_letter(None, "S2C_T10SGJ_20260907T185201_L2A") == "c"
    assert gap_survey.platform_letter("Sentinel-2A", "S2B_x") == "a"
    assert gap_survey.platform_letter(None, "nothing") == "?"
    assert gap_survey.tile_code({"grid:code": "MGRS-10SGJ"}, "x") == "10SGJ"
    cdse_id = "S2A_MSIL2A_20220630T183931_N0510_R070_T11SKD_20240628T155056"
    assert gap_survey.tile_code({}, cdse_id) == "11SKD"
    assert gap_survey.tile_code({}, "S2A_10SGJ_20220630_0_L2A") == "10SGJ"


def test_normalize_keeps_survey_fields_only():
    item = gap_survey.normalize_es(
        es_feature("S2A_T10SGJ_20240629T185101_L2A", "2024-06-29T18:53:40.644000Z")
    )
    assert item["tile"] == "10SGJ"
    assert item["platform"] == "a"
    assert item["baseline"] == "05.10"
    assert json.loads(item["software"]) == {"sentinel-2-c1-l2a-to-stac": "v2024.02.01"}
    assert item["offset_applied"] is False
    ref = gap_survey.normalize_cdse(
        cdse_feature("S2A_MSIL2A_20220630T183931_N0510_R070_T10SGJ_x", "2022-06-30T18:39:31Z")
    )
    assert ref["baseline"] == "05.10"
    assert gap_survey.sensing_key(ref) == "2022-06-30/a"


def test_summarize_counts_acquisitions_not_items():
    months = ["2021-06", "2021-07"]
    items = [
        gap_survey.normalize_es(f)
        for f in [
            es_feature("a0", "2021-06-30T18:53:38Z", "sentinel-2b", "03.01"),
            es_feature(
                "a1", "2021-06-30T18:53:38Z", "sentinel-2b", "05.00", **{"s2:sequence": "1"}
            ),
            es_feature("b0", "2021-06-25T18:53:38Z", "sentinel-2a", "03.01"),
            es_feature("c0", "2021-08-01T18:53:38Z", "sentinel-2a", "05.00"),
        ]
    ]
    summary, keys = gap_survey.summarize(items, months)
    assert summary["items"] == [3, 0]
    assert summary["acquisitions"] == [2, 0]
    assert summary["duplicate_acquisitions"] == [1, 0]
    assert summary["baselines"][0] == {"03.01": 2, "05.00": 1}
    assert summary["sequences_total"] == {"0": 2, "1": 1}
    assert summary["platforms_total"] == {"a": 1, "b": 2}
    assert summary["duplicate_baseline_sets"] == {"03.01+05.00": 1}
    assert summary["offset_flag_by_baseline"] == {"03.01": {"False": 2}, "05.00": {"False": 1}}
    assert summary["items_total"] == 3
    assert summary["acquisitions_total"] == 2
    assert summary["duplicate_acquisitions_total"] == 1
    assert summary["outside_window"] == 1
    assert keys["2021-06"] == {"2021-06-30/b", "2021-06-25/a"}
    assert keys["2021-07"] == set()


def test_compare_classifies_months_and_counts_fallback_cover():
    months = ["2022-05", "2022-06", "2022-07", "2022-08"]
    reference = {
        "2022-05": {"2022-05-01/a", "2022-05-06/b"},
        "2022-06": {"2022-06-01/a", "2022-06-06/b", "2022-06-11/a"},
        "2022-07": {"2022-07-01/a"},
        "2022-08": set(),
    }
    primary = {
        "2022-05": {"2022-05-01/a", "2022-05-06/b"},
        "2022-06": set(),
        "2022-07": {"2022-07-01/a", "2022-07-31/b"},
        "2022-08": {"2022-08-05/a"},
    }
    fallback = {"2022-06": {"2022-06-01/a", "2022-06-06/b"}}
    rows = gap_survey.compare(months, reference, primary, fallback)
    assert rows["status"] == ["complete", "empty", "complete", "primary_only"]
    assert rows["missing"] == [0, 3, 0, 0]
    assert rows["covered_by_fallback"] == [0, 2, 0, 0]
    assert rows["uncovered"] == [0, 1, 0, 0]
    assert rows["primary_not_in_reference"] == [0, 0, 1, 1]
    assert rows["uncovered_keys"] == ["2022-06-11/a"]
    assert rows["months_by_status"] == {"complete": 2, "empty": 1, "primary_only": 1}
    partial = gap_survey.compare(["2022-06"], reference, {"2022-06": {"2022-06-01/a"}}, {})
    assert partial["status"] == ["partial"]
    assert partial["uncovered"] == [2]


def test_asset_summary_reads_quality_assets_and_hosts():
    feature = es_feature("S2A_T10SGJ_20240629T185101_L2A", "2024-06-29T18:53:40Z")
    feature["properties"]["storage:requester_pays"] = False
    feature["assets"] = {
        "scl": {
            "href": "https://e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com/x/SCL.tif",
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "raster:bands": [{"nodata": 0, "data_type": "uint8", "spatial_resolution": 20}],
        },
        "red": {
            "href": "s3://sentinel-s2-l2a/tiles/10/S/GJ/2022/6/30/0/B04.jp2",
            "raster:bands": [{"scale": 0.0001, "offset": -0.1, "data_type": "uint16"}],
        },
        "visual": {"href": "https://example.invalid/TCI.tif"},
    }
    summary = gap_survey.asset_summary(feature)
    assert summary["asset_keys"] == ["red", "scl", "visual"]
    assert summary["quality_assets"]["scl"]["href_host"] == (
        "e84-earth-search-sentinel-data.s3.us-west-2.amazonaws.com"
    )
    assert summary["quality_assets"]["scl"]["resolution_m"] == 20
    assert summary["red"]["href_host"] == "sentinel-s2-l2a"
    assert summary["red"]["offset"] == -0.1
    assert summary["storage"] == {"storage:requester_pays": False}
    assert "cloud" not in summary["quality_assets"]


def test_sites_file_is_well_formed():
    doc = json.loads((ROOT / "benchmarks" / "gap-survey-sites.json").read_text())
    ids = [site["site_id"] for site in doc["sites"]]
    assert len(ids) == len(set(ids))
    for site in doc["sites"]:
        assert site["group"] in {"us", "context"}
        assert -90 <= site["latitude"] <= 90
        assert -180 <= site["longitude"] <= 180
        assert site["why"]
