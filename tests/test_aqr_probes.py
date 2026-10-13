"""Fixture tests for probes T1 to T3 on the USGS aquatic reflectance bucket. No network."""

import importlib.util
import json
from pathlib import Path

import pytest

from s2proto import aqr, harness

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "benchmarks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aqr_headers = load("aqr_headers")
aqr_coverage = load("aqr_coverage")

PRODUCT = "S2B_MSIAQR_20251015T162149_N0511_R040_T17SKU_20251015T195355"
LISTING = f"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
<Name>usgs-wma-sentinel-2-aqr-acolite-dsf</Name><Prefix>version_01/</Prefix>
<KeyCount>2</KeyCount><MaxKeys>1000</MaxKeys><IsTruncated>true</IsTruncated>
<NextContinuationToken>abc</NextContinuationToken>
<Contents><Key>version_01/T17SKU/{PRODUCT}_B04.tif</Key><LastModified>2025-12-24T16:03:13.000Z</LastModified>
<ETag>&quot;e1&quot;</ETag><Size>44043505</Size><StorageClass>STANDARD</StorageClass></Contents>
<CommonPrefixes><Prefix>version_01/T17SKU/</Prefix></CommonPrefixes>
</ListBucketResult>"""


def objects(product, layers=aqr.OBSERVED_LAYERS, modified="2025-10-15T23:00:00.000Z"):
    out = []
    for layer in layers:
        ext = "txt" if layer == "settings" else "tif"
        tile = product.split("_")[5][1:]
        out.append(
            {
                "key": f"version_01/T{tile}/{product}_{layer}.{ext}",
                "size": 10,
                "etag": "x",
                "last_modified": modified,
            }
        )
    return out


def es_feature(product_uri, cloud=5.0, nodata=10.0, collection="sentinel-2-c1-l2a"):
    fields = aqr.parse_product(product_uri.removesuffix(".SAFE"))
    sensing = fields["sensing"]
    return {
        "id": f"{fields['platform']}_T{fields['tile']}_{sensing}_{collection}",
        "properties": {
            "datetime": aqr.compact_time(sensing),
            "platform": f"sentinel-2{fields['platform'][-1].lower()}",
            "grid:code": f"MGRS-{fields['tile']}",
            "s2:processing_baseline": fields["baseline"],
            "s2:product_uri": product_uri,
            "eo:cloud_cover": cloud,
            "s2:nodata_pixel_percentage": nodata,
        },
    }


def test_listing_parses_keys_prefixes_and_continuation():
    listing = aqr.parse_listing(LISTING)
    assert listing["truncated"] is True and listing["next_token"] == "abc"
    assert listing["prefixes"] == ["version_01/T17SKU/"]
    assert listing["keys"][0]["size"] == 44043505 and listing["keys"][0]["etag"] == "e1"


def test_key_names_parse_into_scene_fields():
    parsed = aqr.parse_key(f"version_01/T17SKU/{PRODUCT}_l2_flags.tif")
    assert parsed["layer"] == "l2_flags" and parsed["baseline"] == "05.11"
    assert parsed["sensing_time"] == "2025-10-15T16:21:49Z" and parsed["orbit"] == 40
    assert parsed["product"] == PRODUCT
    assert aqr.parse_key("version_01/T17SKU/readme.txt") is None


def test_scenes_group_by_product_and_report_unparsed_keys():
    listed = objects(PRODUCT) + [
        {"key": "version_01/odd.txt", "size": 1, "etag": "", "last_modified": None}
    ]
    scenes, unparsed = aqr.group_scenes(listed)
    assert list(scenes) == [PRODUCT]
    assert set(scenes[PRODUCT]["layers"]) == set(aqr.OBSERVED_LAYERS)
    assert unparsed == ["version_01/odd.txt"]


def test_settings_skip_comments_and_keep_values():
    text = "## ACOLITE settings\n## Written at 2025-12-24\ndsf_aot_estimate=tiled\n\nlimit=None\n"
    assert aqr.parse_settings(text) == {"dsf_aot_estimate": "tiled", "limit": "None"}


def test_join_prefers_collection_one_and_marks_baseline_agreement():
    scenes, _ = aqr.group_scenes(objects(PRODUCT))
    scene = scenes[PRODUCT]
    exact = "S2B_MSIL2A_20251015T162149_N0511_R040_T17SKU_20251015T202039.SAFE"
    other = "S2B_MSIL2A_20251015T162149_N0500_R040_T17SKU_20240101T000000.SAFE"
    items = {
        "c1": [aqr_coverage.gs.normalize_es(es_feature(other))],
        "older": [aqr_coverage.gs.normalize_es(es_feature(exact))],
    }
    joined = aqr.join_scene(scene, items, ["c1", "older"])
    assert joined["status"] == "other_baseline" and joined["joined"]["collection"] == "c1"
    items["c1"].append(aqr_coverage.gs.normalize_es(es_feature(exact)))
    assert aqr.join_scene(scene, items, ["c1", "older"])["status"] == "exact"
    assert aqr.join_scene(scene, {}, ["c1"])["status"] == "none"


def test_scene_specs_and_month_selection():
    assert aqr_headers.parse_scene_spec("T17SKU:2022-07")["first_in_month"] is True
    assert aqr_headers.parse_scene_spec("10SGJ:2025-10-20")["date"] == "20251020"
    with pytest.raises(ValueError):
        aqr_headers.parse_scene_spec("17SKU:2022")
    early = PRODUCT.replace("20251015T162149", "20220703T161839")
    late = PRODUCT.replace("20251015T162149", "20220708T161839")
    scenes, _ = aqr.group_scenes(objects(early) + objects(late))
    spec = aqr_headers.parse_scene_spec("17SKU:2022-07")
    assert [s["product"] for s in aqr_headers.select(spec, scenes)] == [early]


def test_grid_comparison_detects_alignment_and_offsets():
    header = {
        "transform": [20.0, 0.0, 199980.0, 0.0, -20.0, 3800040.0],
        "height": 5490,
        "width": 5490,
        "epsg": 32617,
        "crs": "EPSG:32617",
    }
    item = {
        "id": "x",
        "properties": {"proj:code": "EPSG:32617"},
        "assets": {
            "rededge1": {
                "proj:transform": [20, 0, 199980, 0, -20, 3800040],
                "proj:shape": [5490, 5490],
            }
        },
    }
    assert aqr_headers.grid_comparison(header, item)["aligned"] is True
    item["assets"]["rededge1"]["proj:transform"] = [20, 0, 199990, 0, -20, 3800040]
    shifted = aqr_headers.grid_comparison(header, item)
    assert shifted["aligned"] is False and shifted["origin_offset_pixels"][0] == -0.5


class NoNetwork:
    def __init__(self, *args, **kwargs):
        raise AssertionError("a dry run must not create a client")


def test_dry_runs_contact_nothing(monkeypatch, capsys):
    monkeypatch.setattr(harness, "Client", NoNetwork)
    monkeypatch.setattr(aqr_coverage.gs, "Client", NoNetwork)
    assert aqr_headers.main(["--dry-run"]) == 0
    assert aqr_coverage.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "unsigned" in out and "No pixel is read" in out


def test_coverage_analysis_counts_acquisitions_joins_and_latency():
    present = PRODUCT
    duplicate = PRODUCT.replace("20251015T195355", "20251016T000000")
    month = ["2025-10"]
    listed = objects(present, modified="2025-10-15T22:21:49.000Z") + objects(duplicate)
    l1c = [
        es_feature(present.replace("MSIAQR", "MSIL1C") + ".SAFE", cloud=20.0),
        es_feature("S2C_MSIL1C_20251020T162149_N0511_R040_T17SKU_20251020T190000.SAFE", cloud=90.0),
    ]
    c1 = [es_feature("S2B_MSIL2A_20251015T162149_N0511_R040_T17SKU_20251015T202039.SAFE")]
    es = {aqr_coverage.L1C: l1c, aqr_coverage.C1: c1, aqr_coverage.OLDER: []}
    record = aqr_coverage.analyze_tile("17SKU", listed, es, month, "2025-10-31")
    assert record["scenes"] == 2 and record["acquisitions"] == 1
    assert record["duplicate_kinds"] == {"same_sensing": 1}
    assert record["monthly"]["aqr"] == [1] and record["monthly"]["earth_search_any"] == [2]
    assert record["missing_vs_l1c_by_year"] == {"2025": 1}
    assert record["join_by_year"]["2025"] == {"exact sentinel-2-c1-l2a": 2}
    assert record["l1c_by_year"]["2025"] == {"same_pass_other_product": 1, "same_product": 1}
    assert record["cloud_cover"]["bins"]["missing"]["75-100"] == 1
    assert record["latency_by_sensing_year"]["2025"]["min_days"] == 0.25


RESULTS = ROOT / "benchmarks" / "results"


@pytest.mark.parametrize("name", ["aqr-headers.json", "aqr-coverage.json"])
def test_results_name_bucket_region_payer_and_read_no_pixel(name):
    path = RESULTS / name
    if not path.exists():
        pytest.skip(f"{name} has not been produced")
    result = json.loads(path.read_text())
    assert result["measured_at"] and result["code_version"] and result["limitations"]
    endpoints = result["endpoints"]
    assert endpoints["bucket"] == aqr.BUCKET and endpoints["region"] == aqr.REGION
    assert "unsigned" in endpoints["credentials"] and endpoints["payer"].startswith("Bucket owner")
    if name == "aqr-coverage.json":
        assert result["requests"]["pixels_read"] == 0
        assert result["requests"]["object_bodies_read"] == 0
    else:
        statuses = {entry["status"] for entry in result["request_log"]}
        assert statuses == {200}
        assert all(e["method"] in {"GET", "HEAD", "POST"} for e in result["request_log"])
