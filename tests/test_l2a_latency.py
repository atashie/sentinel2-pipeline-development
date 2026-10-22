"""Fixture tests for the Sen2Cor Level-2A latency survey. No network."""

import importlib.util
import json
from pathlib import Path

import pytest

from s2proto import harness

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "benchmarks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lat = load("l2a_latency")

TILE = "10SEJ"
NAME = "S2C_MSIL2A_20260903T185911_N0512_R013_T10SEJ_20260903T232308"
LATE = "S2B_MSIL2A_20260905T184919_N0512_R113_T10SEJ_20260905T224919"
MISSING = "S2A_MSIL2A_20260908T185921_N0512_R013_T10SEJ_20260908T230000"
META = {
    "tiles": [TILE],
    "start": "2026-06-15",
    "end": "2026-10-13",
    "cutoff": "2026-10-13T18:22:53+00:00",
    "measured_at": "2026-10-21T00:00:00+00:00",
}


def feature(item_id, product, created):
    return {
        "id": item_id,
        "properties": {
            "datetime": "2026-09-03T19:08:26.000000Z",
            "platform": "sentinel-2c",
            "grid:code": f"MGRS-{TILE}",
            "s2:processing_baseline": "05.12",
            "s2:sequence": "0",
            "s2:product_uri": f"{product}.SAFE",
            "s2:generation_time": "2026-09-03T23:23:08.000000Z",
            "created": created,
            "updated": created,
        },
    }


def objects(prefix, item_id, stamps):
    return [
        {"key": f"{prefix}/{item_id}/B{i:02d}.tif", "size": 1, "etag": "", "last_modified": s}
        for i, s in enumerate(stamps)
    ]


def cdse(name, published):
    sensing = name.split("_")[2]
    start = f"{sensing[:4]}-{sensing[4:6]}-{sensing[6:8]}T{sensing[9:11]}:{sensing[11:13]}:00Z"
    return {
        "Name": f"{name}.SAFE",
        "OriginDate": published,
        "PublicationDate": published,
        "ContentDate": {"Start": start},
    }


def raw_tile():
    c1 = "sentinel-2-c1-l2a/10/S/EJ/2026/9"
    return {
        "cdse": [
            cdse(NAME, "2026-09-04T00:08:56.002418Z"),
            cdse(LATE, "2026-09-05T23:40:45.785291Z"),
            cdse(MISSING, "2026-09-09T00:00:00.000000Z"),
        ],
        "es": {
            lat.C1: [
                feature("S2C_T10SEJ_20260903T190826_L2A", NAME, "2026-09-04T03:00:00Z"),
                feature("S2B_T10SEJ_20260905T184919_L2A", LATE, "2026-10-15T00:00:00Z"),
            ],
            lat.OLDER: [],
        },
        "s3": {
            lat.C1: objects(
                c1,
                "S2C_T10SEJ_20260903T190826_L2A",
                ["2026-09-04T03:11:11.000Z", "2026-09-04T02:59:11.000Z"],
            )
            + objects(c1, "S2B_T10SEJ_20260905T184919_L2A", ["2026-10-14T18:49:19.000Z"])
            + objects(c1, "S2A_T10SEJ_20260801T000000_L2A", ["2026-08-01T05:00:00.000Z"]),
            lat.OLDER: [],
        },
    }


def test_tile_and_month_prefixes_match_the_bucket_layout():
    assert lat.tile_prefix("10SEJ") == "10/S/EJ"
    assert lat.tile_prefix("05VMG") == "5/V/MG"
    with pytest.raises(ValueError):
        lat.tile_prefix("MGRS-10SEJ")
    prefixes = lat.month_prefixes(lat.C1, TILE, "2026-09-20", "2026-10-02")
    assert prefixes == ["sentinel-2-c1-l2a/10/S/EJ/2026/9/", "sentinel-2-c1-l2a/10/S/EJ/2026/10/"]
    assert lat.month_prefixes(lat.OLDER, TILE, "2026-01-01", "2026-01-31") == [
        "sentinel-s2-l2a-cogs/10/S/EJ/2026/1/"
    ]
    assert "e84-earth-search-sentinel-data.s3.us-west-2" in lat.list_url(
        "e84-earth-search-sentinel-data", "x/"
    )


def test_window_comes_from_finding_27_and_rejects_disagreeing_tiles():
    coverage = {
        "tiles_inside": ["10SEJ", "10SGJ"],
        "window": {"end": "2026-10-13"},
        "measured_at": "2026-10-13T18:22:53+00:00",
        "tiles": [{"latency_recent": {"sensed_from": "2026-06-15"}}] * 2,
    }
    window = lat.window_from_coverage(coverage)
    assert window == {
        "tiles": ["10SEJ", "10SGJ"],
        "start": "2026-06-15",
        "end": "2026-10-13",
        "cutoff": "2026-10-13T18:22:53+00:00",
    }
    coverage["tiles"] = [
        {"latency_recent": {"sensed_from": "2026-06-15"}},
        {"latency_recent": {"sensed_from": "2026-06-16"}},
    ]
    with pytest.raises(ValueError):
        lat.window_from_coverage(coverage)


def test_folders_keep_first_and_last_object_time():
    found = lat.folders(raw_tile()["s3"][lat.C1])
    first = found["S2C_T10SEJ_20260903T190826_L2A"]
    assert first == {
        "first": "2026-09-04T02:59:11.000Z",
        "last": "2026-09-04T03:11:11.000Z",
        "objects": 2,
    }


def test_tile_analysis_times_every_clock_from_the_product_sensing_start():
    record = lat.analyze_tile(TILE, raw_tile(), META)
    c1 = record["collections"][lat.C1]
    first = c1["records"][0]
    assert first["sensing_time"] == "2026-09-03T18:59:11Z"
    assert first["sensing_source"] == "product_name"
    assert first["hours"]["bucket_first"] == 8.0
    assert first["hours"]["bucket_last"] == 8.2
    assert first["hours"]["esa_generation"] == 4.4
    assert first["hours"]["cdse_publication"] == 5.16
    assert first["after_cdse_publication_hours"] == 2.84
    assert c1["folders_without_item"] == 1
    assert c1["cdse_status"]["counts"] == {"absent": 1, "same_product": 2}
    assert c1["cdse_status"]["absent"][0]["product"] == MISSING
    older = record["collections"][lat.OLDER]
    assert older["cdse_status"]["counts"] == {"absent": 3}


def test_pass_with_another_product_name_is_not_counted_absent():
    raw = raw_tile()
    other = NAME.replace("20260903T232308", "20260904T010101")
    raw["es"][lat.OLDER] = [feature("S2C_10SEJ_20260903_0_L2A", other, "2026-09-04T03:00:00Z")]
    record = lat.analyze_tile(TILE, raw, META)
    counts = record["collections"][lat.OLDER]["cdse_status"]["counts"]
    assert counts == {"absent": 2, "pass_other_product": 1}


def test_summary_censors_at_the_cutoff_and_counts_unarrived_products():
    records = lat.analyze_tile(TILE, raw_tile(), META)["collections"][lat.C1]["records"]
    summary = lat.summarize(records, {"same_product": 2, "absent": 1}, 3, META["cutoff"])
    assert summary["latency"]["bucket_first"]["n"] == 2
    assert summary["bucket_first_matched_cutoff"]["n"] == 1
    assert summary["bucket_first_matched_cutoff"]["max_days"] == 0.33
    shares = summary["share_of_cdse_products_in_bucket_within"]
    assert shares == {"6h": 0.0, "12h": 0.3333, "24h": 0.3333, "72h": 0.3333}
    assert summary["slowest_bucket_first"][0]["bucket_first_days"] == 39.0


def test_stats_use_nearest_rank_and_handle_empty_lists():
    assert lat.stats([]) == {"n": 0}
    out = lat.stats([24, 48, 72, 96])
    assert out["median_days"] == 2.0 and out["p90_days"] == 4.0 and out["min_days"] == 1.0
    signed = lat.stats([-1.5, 2.0], days=False)
    assert signed["min_hours"] == -1.5 and signed["median_hours"] == -1.5


def test_rebuild_from_raw_is_deterministic(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    tile = raw_tile()
    (raw_dir / f"cdse-{TILE}.json").write_text(json.dumps(tile["cdse"]))
    for collection in lat.COLLECTIONS:
        (raw_dir / f"es-{TILE}-{collection}.json").write_text(json.dumps(tile["es"][collection]))
        (raw_dir / f"s3-{TILE}-{collection}.json").write_text(json.dumps(tile["s3"][collection]))
    meta = META | {
        "code_version": "test",
        "script_sha256": "test",
        "request_log": {"earth_search_and_cdse": [], "s3": []},
    }
    (raw_dir / "meta.json").write_text(json.dumps(meta))
    monkeypatch.setattr(lat, "ROOT", tmp_path)
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert lat.main(["--from-raw", str(raw_dir), "--output", str(first)]) == 0
    assert lat.main(["--from-raw", str(raw_dir), "--output", str(second)]) == 0
    a, b = json.loads(first.read_text()), json.loads(second.read_text())
    a.pop("analysis_code_version")
    b.pop("analysis_code_version")
    assert a == b
    assert a["requests"]["pixels_read"] == 0 and a["requests"]["object_bodies_read"] == 0
    assert a["summary"][lat.C1]["cdse_status"] == {"absent": 1, "same_product": 2}


class NoNetwork:
    def __init__(self, *args, **kwargs):
        raise AssertionError("a dry run must not create a client")


def test_dry_run_contacts_nothing(monkeypatch, capsys):
    monkeypatch.setattr(harness, "Client", NoNetwork)
    monkeypatch.setattr(lat.gs, "Client", NoNetwork)
    assert lat.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "unsigned" in out and "No pixel is read" in out


RESULT = ROOT / "benchmarks" / "results" / "l2a-latency.json"


def test_result_names_endpoints_payer_and_reads_no_pixel():
    if not RESULT.exists():
        pytest.skip("l2a-latency.json has not been produced")
    result = json.loads(RESULT.read_text())
    assert result["measured_at"] and result["code_version"] and result["limitations"]
    assert result["endpoints"]["region"] == "us-west-2"
    assert result["endpoints"]["payer"].startswith("Bucket owner")
    assert result["requests"]["pixels_read"] == 0
    assert result["requests"]["object_bodies_read"] == 0
    # A retried request logs its failed attempts. The run only finishes if each one succeeded.
    statuses = {e["status"] for log in result["request_log"].values() for e in log}
    assert 200 in statuses and statuses <= {200, 408, 429, 500, 502, 503, 504, None}
