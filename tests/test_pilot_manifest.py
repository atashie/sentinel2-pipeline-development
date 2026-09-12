"""Fixture tests for the pilot manifest builder and checks of the committed manifest. No network."""

import importlib.util
import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_pilot_manifest", ROOT / "tools" / "build_pilot_manifest.py"
)
bpm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bpm)

CLASSES = [10, 30, 100, 300, 1000]
MANIFEST = ROOT / "examples" / "water-bodies-public-pilot.geojson"
CONFIG = ROOT / "examples" / "pilot-regions.json"
README = ROOT / "examples" / "README.md"


def square(lon, lat, side_m):
    """Closed ring of a square with the given side, centred on lon and lat."""
    dlat = side_m / 2 / (bpm.EARTH_RADIUS_M * math.pi / 180)
    dlon = dlat / math.cos(math.radians(lat))
    return [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]


def service_feature(pid, rings, fcode=39004, name=None, multi=False):
    geometry = (
        {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
        if multi
        else {"type": "Polygon", "coordinates": rings}
    )
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "PERMANENT_IDENTIFIER": pid,
            "GNIS_ID": None,
            "GNIS_NAME": name,
            "FTYPE": 390,
            "FCODE": fcode,
            "AREASQKM": 0.001,
            "REACHCODE": "16050101000339",
            "FDATE": 1678233600000,
            "RESOLUTION": 2,
        },
    }


def test_class_bounds_are_geometric_midpoints():
    assert bpm.class_bounds(CLASSES) == pytest.approx([17.32, 54.77, 173.2, 547.7], rel=1e-3)
    assert bpm.size_class(17.0, CLASSES) == 10
    assert bpm.size_class(17.4, CLASSES) == 30
    assert bpm.size_class(547.0, CLASSES) == 300
    assert bpm.size_class(50000.0, CLASSES) == 1000


def test_area_of_squares_holes_and_multipolygons():
    ring = square(-84.0, 34.0, 100)
    assert bpm.ring_area_m2(ring) == pytest.approx(10000, rel=0.002)
    with_hole = {"type": "Polygon", "coordinates": [ring, square(-84.0, 34.0, 20)]}
    assert bpm.polygon_area_m2(with_hole) == pytest.approx(9600, rel=0.002)
    multi = {"type": "MultiPolygon", "coordinates": [[ring], [square(-84.01, 34.0, 50)]]}
    assert bpm.polygon_area_m2(multi) == pytest.approx(12500, rel=0.002)
    assert bpm.ring_area_m2(ring[:3]) == 0.0
    with pytest.raises(ValueError):
        bpm.polygon_area_m2({"type": "Point", "coordinates": [0, 0]})


def test_bbox_vertex_count_and_rounding():
    geometry = {"type": "Polygon", "coordinates": [square(-84.0, 34.0, 100)]}
    west, south, east, north = bpm.geometry_bbox(geometry)
    assert west < -84.0 < east and south < 34.0 < north
    assert bpm.vertex_count(geometry) == 5
    rounded = bpm.round_coordinates([[[-84.12345678, 34.87654321, 5.0]]])
    assert rounded == [[[-84.123457, 34.876543]]]


def test_candidate_filters_codes_and_geometry():
    ring = square(-84.0, 34.0, 30)
    assert bpm.candidate(service_feature("1", [ring], fcode=39001)) is None
    assert bpm.candidate(service_feature("", [ring])) is None
    assert bpm.candidate({"properties": {"FCODE": 39004, "PERMANENT_IDENTIFIER": "2"}}) is None
    point = {"properties": {"FCODE": 39004, "PERMANENT_IDENTIFIER": "3"}}
    point["geometry"] = {"type": "Point", "coordinates": [0, 0]}
    assert bpm.candidate(point) is None
    assert bpm.candidate(service_feature("4", [square(-84.0, 34.0, 0.5)])) is None
    cand = bpm.candidate(service_feature("7", [ring]))
    assert cand["source_id"] == "7"
    assert cand["width_m"] == pytest.approx(30, rel=0.002)
    assert cand["geometry"]["type"] == "Polygon"


def test_selection_is_nearest_width_and_deterministic():
    widths = [
        ("w9", 9),
        ("w12", 12),
        ("w28", 28),
        ("w33", 33),
        ("b", 100),
        ("a", 100),
        ("big", 2000),
    ]
    candidates = [
        bpm.candidate(service_feature(pid, [square(-84.0, 34.0, side)])) for pid, side in widths
    ]
    picks = bpm.select_by_class(candidates, CLASSES)
    assert [p["source_id"] for p in picks.values()] == ["w9", "w28", "a", "big"]
    assert sorted(picks) == [10, 30, 100, 1000]


def fixture_config():
    return {
        "size_classes_m": CLASSES,
        "regions": [
            {
                "region_id": "alpha",
                "name": "Alpha basin",
                "survey_site_id": "alpha-site",
                "include_anchor": True,
                "box": {"latitude": 34.0, "longitude": -84.0, "half_width_deg": 0.1},
                "setting": "mountain",
                "setting_basis": "test",
                "why": "Anchor reason.",
            },
            {
                "region_id": "beta",
                "name": "Beta plain",
                "survey_site_id": "beta-site",
                "include_anchor": False,
                "box": {"latitude": 30.0, "longitude": -90.0, "half_width_deg": 0.1},
                "setting": "flat",
                "setting_basis": "test",
                "why": "No anchor.",
            },
        ],
    }


def fixture_raw(anchors=1):
    alpha = [
        service_feature(f"a{i}", [square(-84.0, 34.0, side)]) for i, side in enumerate([12, 95])
    ]
    beta = [service_feature("b0", [square(-90.0, 30.0, 300), square(-90.0, 30.0, 40)])]
    anchor = [
        service_feature(f"L{i}", [square(-84.0, 34.0, 3000), square(-84.05, 34.0, 400)], multi=True)
        for i in range(anchors)
    ]
    return {
        "service": {"copyrightText": "USGS test. Data Refreshed test."},
        "layer": {"name": "Waterbody - Large Scale", "copyrightText": "USGS"},
        "fetch": {
            "accessed_at": "2026-09-12T00:00:00+00:00",
            "code_version": "test",
            "config_sha256": "0" * 64,
            "files": {"service.json": "1" * 64},
            "requests": [{"bytes": 10}, {"bytes": 5}],
        },
        "regions": {
            "alpha": {
                "candidates": {"pages": [{"features": alpha}]},
                "anchor": {"features": anchor},
            },
            "beta": {"candidates": {"pages": [{"features": beta}]}, "anchor": None},
        },
    }


def test_build_manifest_from_fixture(tmp_path):
    manifest = bpm.build_manifest(fixture_config(), fixture_raw())
    assert manifest["type"] == "FeatureCollection"
    ids = [f["id"] for f in manifest["features"]]
    assert ids == ["nhd-l0", "nhd-a0", "nhd-a1", "nhd-b0"]
    anchor = manifest["features"][0]["properties"]
    assert anchor["tier"] == "large"
    assert anchor["size_class_m"] == 1000
    assert anchor["why"] == "Anchor reason."
    assert anchor["source_accessed"] == "2026-09-12"
    assert anchor["nhd_feature_date"] == "2023-03-08"
    assert manifest["features"][0]["geometry"]["type"] == "MultiPolygon"
    pond = manifest["features"][1]["properties"]
    assert pond["tier"] == "pilot"
    assert pond["size_class_m"] == 10
    assert pond["setting"] == "mountain"
    assert pond["survey_site_id"] == "alpha-site"
    assert "among 2 candidates" in pond["why"]
    assert pond["name"] == "Unnamed water body, Alpha basin"
    hole = manifest["features"][3]["properties"]
    assert hole["area_m2"] == pytest.approx(300 * 300 - 40 * 40, rel=0.003)
    summary = manifest["summary"]
    assert summary["features"] == 4
    assert summary["by_tier"] == {"large": 1, "pilot": 3}
    assert summary["by_size_class_m"] == {"1000": 1, "10": 1, "100": 1, "300": 1}
    assert summary["by_region"]["beta"] == {
        "candidates": 1,
        "features": 1,
        "size_classes_m": [300],
        "anchor": False,
    }
    assert manifest["retrieval"]["requests_total"] == 2
    assert manifest["retrieval"]["bytes_total"] == 15
    assert manifest["dataset"]["terms"]["url"] == bpm.TERMS_URL
    path = tmp_path / "manifest.geojson"
    bpm.dump_manifest(manifest, path)
    assert json.loads(path.read_text()) == manifest
    lines = path.read_text().splitlines()
    assert sum(1 for line in lines if line.startswith('  {"type":"Feature"')) == 4


def test_build_manifest_rejects_ambiguous_anchor():
    with pytest.raises(ValueError, match="expected one anchor"):
        bpm.build_manifest(fixture_config(), fixture_raw(anchors=2))
    with pytest.raises(ValueError, match="expected one anchor"):
        bpm.build_manifest(fixture_config(), fixture_raw(anchors=0))


def documented_properties():
    rows = re.findall(r"^\| `(\w+)` \|", README.read_text(), flags=re.MULTILINE)
    return set(rows)


def test_committed_manifest_matches_its_format_and_config():
    manifest = json.loads(MANIFEST.read_text())
    config = json.loads(CONFIG.read_text())
    regions = {r["region_id"]: r for r in config["regions"]}
    classes = config["size_classes_m"]
    accessed = manifest["retrieval"]["accessed_at"][:10]
    documented = documented_properties()
    assert manifest["type"] == "FeatureCollection"
    assert manifest["manifest_version"] == 1
    ids = [f["id"] for f in manifest["features"]]
    assert len(ids) == len(set(ids))
    seen_regions = set()
    for feature in manifest["features"]:
        props = feature["properties"]
        assert set(props) == documented, sorted(set(props) ^ documented)
        assert feature["id"] == props["water_body_id"] == bpm.water_body_id(props["source_id"])
        assert props["source"] == bpm.SOURCE
        assert props["source_accessed"] == accessed
        assert props["polygon_version"] == 1
        assert props["fcode"] in bpm.FCODES
        assert props["tier"] in ("large", "pilot")
        region = regions[props["region"]]
        seen_regions.add(props["region"])
        assert props["setting"] == region["setting"]
        assert props["survey_site_id"] == region["survey_site_id"]
        geometry = feature["geometry"]
        assert geometry["type"] in ("Polygon", "MultiPolygon")
        polygons = (
            [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        )
        for rings in polygons:
            for ring in rings:
                assert ring[0] == ring[-1]
                assert len(ring) >= 4
                for lon, lat in ring:
                    assert -180 <= lon <= 180 and -90 <= lat <= 90
                    assert round(lon, bpm.COORD_DECIMALS) == lon
                    assert round(lat, bpm.COORD_DECIMALS) == lat
        area = bpm.polygon_area_m2(geometry)
        assert props["area_m2"] == pytest.approx(area, abs=0.06)
        assert props["width_m"] == pytest.approx(math.sqrt(area), abs=0.06)
        assert props["size_class_m"] == bpm.size_class(props["width_m"], classes)
        assert props["vertex_count"] == bpm.vertex_count(geometry)
        assert feature["bbox"] == bpm.geometry_bbox(geometry)
    assert seen_regions == set(regions)
    summary = manifest["summary"]
    assert summary["features"] == len(manifest["features"])
    assert summary["vertices"] == sum(f["properties"]["vertex_count"] for f in manifest["features"])
    assert set(summary["by_size_class_m"]) == {str(c) for c in classes}
    assert {"mountain", "flat"} <= set(summary["by_setting"])
    assert summary["by_tier"]["large"] == sum(
        1 for f in manifest["features"] if f["properties"]["tier"] == "large"
    )
    assert manifest["dataset"]["service"] == bpm.SERVICE
    assert manifest["dataset"]["acknowledgment"] == bpm.ACKNOWLEDGMENT
    assert manifest["retrieval"]["requests_total"] == len(manifest["retrieval"]["requests"])
    assert all(r["status"] == 200 for r in manifest["retrieval"]["requests"])
    assert all(r["host"] == "hydro.nationalmap.gov" for r in manifest["retrieval"]["requests"])


def test_pilot_carries_a_body_the_survey_measured_in_two_tiles():
    survey = json.loads((ROOT / "benchmarks" / "results" / "gap-survey.json").read_text())
    tiles_by_site = {site["site_id"]: site["tiles"] for site in survey["sites"]}
    manifest = json.loads(MANIFEST.read_text())
    two_tile = [
        f["properties"]["name"]
        for f in manifest["features"]
        if f["properties"]["tier"] == "large"
        and len(tiles_by_site.get(f["properties"]["survey_site_id"], {})) >= 2
    ]
    assert two_tile, "no large pilot body sits at a survey site with two or more tiles"


def test_ten_metre_class_is_present_for_the_no_interior_pixel_case():
    manifest = json.loads(MANIFEST.read_text())
    tiny = [f for f in manifest["features"] if f["properties"]["size_class_m"] == 10]
    assert tiny
    assert all(f["properties"]["width_m"] < bpm.class_bounds(CLASSES)[0] for f in tiny)
