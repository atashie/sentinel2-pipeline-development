"""Probe T7 rules and helpers. Synthetic inputs, no network."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks")]

from s2proto import masks, overlap, pairs  # noqa: E402


def scene(region, tile, epsg, members):
    return {"region": region, "tile": tile, "epsg": epsg, "members": members}


def test_zone_pairs_split_same_and_cross_zone_and_need_a_shared_lake():
    scenes = [
        scene("lanier", "16SGD", 32616, ["a", "b"]),
        scene("lanier", "16SGC", 32616, ["a"]),
        scene("lanier", "17SKT", 32617, ["a", "c"]),
        scene("okee", "17RNK", 32617, ["x"]),
        scene("okee", "17RNL", 32617, ["y"]),
    ]
    same, cross = overlap.zone_pairs(scenes)
    assert same == [{"region": "lanier", "tile_a": "16SGC", "tile_b": "16SGD", "lakes": ["a"]}]
    assert {(p["tile_a"], p["tile_b"]) for p in cross} == {("16SGC", "17SKT"), ("16SGD", "17SKT")}


def test_origin_offset_maps_one_ground_pixel_between_tiles():
    a = masks.TileGrid(32617, 399960.0, 3000000.0)
    b = masks.TileGrid(32617, 499980.0, 3000000.0)
    dr, dc = overlap.origin_offset(a, b)
    assert (dr, dc) == (0.0, -5001.0)
    assert overlap.whole_offset((dr, dc)) == (0, -5001)
    assert overlap.whole_offset((0.5, 0.0)) is None
    # A pixel at column 5100 of tile A sits at column 99 of tile B.
    assert 5100 + dc == 99


def test_overlap_windows_clip_to_both_tiles():
    clipped = overlap.overlap_windows((100, 5000, 50, 400), (0, -5001), size=5490)
    assert clipped == ((100, 5001, 50, 399), (100, 0, 50, 399))
    assert overlap.overlap_windows((0, 0, 10, 10), (0, -5001), size=5490) is None
    a, b = overlap.overlap_windows((5480, 0, 20, 30), (-5001, 0), size=5490)
    assert a == (5480, 0, 10, 30) and b == (479, 0, 10, 30)


def test_verdict_and_widening_follow_the_declared_thresholds():
    assert overlap.verdict(99, 0) == "too_few"
    assert overlap.verdict(1000, 100) == "agree"
    assert overlap.verdict(1000, 101) == "differs"
    assert overlap.widening(0.30, 0.20) == "widens"
    assert overlap.widening(0.20, 0.30) == "narrows"
    assert overlap.widening(0.25, 0.20) == "similar"
    assert overlap.widening(None, 0.2) is None


def test_sixty_metre_parents_coincide_for_same_zone_origins():
    # Same-zone MGRS origins differ by 99,960 or 100,020 m, whole 60 m pixels.
    for metres in (99960, 100020, 199980):
        assert (metres / 20) % 3 == 0


def test_collection1_quarter_units_keep_exact_differences_at_the_threshold():
    scale, offset = 0.0001, -0.1
    factor, shift = round(scale * pairs.UNIT, 9), round(offset * pairs.UNIT, 6)
    a = np.array([1050.0, 1234.25]) * factor + shift
    b = np.array([1000.0, 1184.25]) * factor + shift
    assert np.array_equal(a - b, np.array([50.0, 50.0]))
    m = pairs.Moments()
    m.add(a, b)
    assert m.disagree == 0


def test_rules_cover_o1_to_o9():
    assert list(overlap.TOLERANCES) == [
        "O1_pairs",
        "O2_grid",
        "O3_pixels",
        "O4_units",
        "O5_comparable",
        "O6_strata",
        "O7_tile_agreement",
        "O8_widening",
        "O9_flag_diagnostic",
    ]
