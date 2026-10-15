"""Probe T6 driver helpers. Synthetic inputs, no network."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools")]

import aqr_workloads as t6  # noqa: E402
from test_aqr_pairs import C1_ITEMS, TAHOE, scene  # noqa: E402

from s2proto import aqr_pairing, masks  # noqa: E402


def test_month_range():
    assert t6.month_range("2025-06") == ("2025-06-01", "2025-06-30")
    assert t6.month_range("2024-02") == ("2024-02-01", "2024-02-29")


def test_restricted_snapshot_keeps_only_paired_items():
    snapshot = {
        "items": {"a": "pa", "b": "pb"},
        "regions": {"r": {"lakes": ["l1"], "items": ["a", "b"]}},
        "groups": [{"lakes": ["l1"], "items": ["a", "b"], "tiles": ["10SGJ"]}],
    }
    out = t6.restricted_snapshot(snapshot, {"b"})
    assert out["items"] == {"b": "pb"}
    assert out["regions"]["r"]["items"] == ["b"]
    assert out["groups"][0]["items"] == ["b"]
    assert snapshot["groups"][0]["items"] == ["a", "b"]


def test_stand_in_plan_swaps_assets_and_keeps_grid(monkeypatch):
    t6.load(workloads=True)
    c1 = C1_ITEMS[0]
    grid = masks.TileGrid.from_item(c1)
    plan = {
        "scenes": [
            {
                "item": c1,
                "tile": "10SGJ",
                "group": "g",
                "grid": {
                    "epsg": grid.epsg,
                    "x0": grid.x0,
                    "y0": grid.y0,
                    "width_10m": 10980,
                    "height_10m": 10980,
                },
                "assets": [],
                "members": ["l1"],
            }
        ],
        "order": [],
    }
    stand = {c1["id"]: aqr_pairing.stand_in_item(c1, scene())}
    out = t6.stand_in_plan(plan, stand, "florida", ["dropped"])
    first = out["scenes"][0]
    assert first["paired_item"] == c1["id"]
    assert first["item"]["id"] == TAHOE
    assert [a["key"] for a in first["assets"]] == ["red", "nir", "swir16", "coastal", "scl"]
    assert {a["resolution"] for a in first["assets"]} == {20}
    assert first["assets"][-1]["dtype"] == "int32"
    assert out["order"] == ["B-lazy", "B-raster"]
    assert out["aqr"]["dropped_lakes"] == ["dropped"]
    bad = {c1["id"]: {**stand[c1["id"]], "assets": {}}}
    with pytest.raises(ValueError):
        t6.stand_in_plan(plan, bad, "florida", [])


def test_plan_prints_without_network(capsys):
    assert t6.main([]) == 0
    text = capsys.readouterr().out
    assert "red = B04" in text and "scl = l2_flags" in text
    assert "B-raster then B-lazy" in text
