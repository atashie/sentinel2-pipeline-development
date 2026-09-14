"""Fixture tests for the copy difference script. No network."""

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
SPEC = importlib.util.spec_from_file_location(
    "copy_difference", ROOT / "benchmarks" / "copy_difference.py"
)
copy_difference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(copy_difference)


def test_compare_arrays_reports_a_constant_offset():
    first = np.array([[0, 1500, 2000], [0, 3000, 4000]], dtype=np.uint16)
    second = first.copy()
    second[first != 0] -= 1000
    second[1, 2] = 3007
    result = copy_difference.compare_arrays(first, second, 0, 0)
    assert result["same_shape"] and not result["identical"]
    assert result["nodata_agrees"]
    assert result["valid_in_both"] == 4
    assert result["equal_where_both_valid"] == 0
    assert result["differing_where_both_valid"] == 4
    assert result["most_common_differences"][0] == {"second_minus_first": -1000, "pixels": 3}
    assert result["most_common_differences"][1] == {"second_minus_first": -993, "pixels": 1}
    assert result["difference_min"] == -1000 and result["difference_max"] == -993
    assert result["max_first"] == 4000 and result["max_second"] == 3007
    assert result["offset_clamp_rule"]["violations"] == 1
    assert result["offset_clamp_rule"]["first_at_or_below_offset"] == 0


def test_rule_check_separates_the_two_fixtures_the_summary_cannot():
    first_a = np.array([0, 100, 2000], dtype=np.uint16)
    second_a = np.array([0, 1, 1000], dtype=np.uint16)
    first_b = np.array([0, 101, 2000], dtype=np.uint16)
    second_b = np.array([0, 2, 1000], dtype=np.uint16)
    a = copy_difference.compare_arrays(first_a, second_a, 0, 0)
    b = copy_difference.compare_arrays(first_b, second_b, 0, 0)
    assert a["most_common_differences"] == b["most_common_differences"]
    assert a["difference_min"] == b["difference_min"] and a["nodata_agrees"] == b["nodata_agrees"]
    assert a["offset_clamp_rule"] == {
        "rule": "second == max(first - 1000, 1) on pixels valid in both",
        "violations": 0,
        "first_at_or_below_offset": 1,
    }
    assert b["offset_clamp_rule"]["violations"] == 1


def test_grid_mismatch_and_shared_product_guards():
    grid = {
        "width": 4,
        "height": 4,
        "crs": "EPSG:32617",
        "transform": [10.0, 0.0, 600000.0, 0.0, -10.0, 3800000.0],
    }
    assert copy_difference.grid_mismatch(grid, dict(grid)) is None
    shifted = {**grid, "transform": [10.0, 0.0, 600010.0, 0.0, -10.0, 3800000.0]}
    assert copy_difference.grid_mismatch(grid, shifted).startswith("transform differs")
    other_crs = {**grid, "crs": "EPSG:32616"}
    assert copy_difference.grid_mismatch(grid, other_crs).startswith("crs differs")
    smaller = {**grid, "width": 2}
    assert copy_difference.grid_mismatch(grid, smaller).startswith("width differs")
    assert copy_difference.grid_mismatch(grid, {**grid, "transform": None}) == "transform missing"
    assert copy_difference.shared_product("same ESA product on every copy: X")
    assert not copy_difference.shared_product(
        "no shared ESA product URI. First item per copy taken."
    )


def test_compare_arrays_identical_and_nodata_disagreement():
    first = np.array([[0, 5], [6, 7]], dtype=np.uint16)
    assert copy_difference.compare_arrays(first, first.copy(), 0, 0)["identical"]
    second = first.copy()
    second[0, 1] = 0
    result = copy_difference.compare_arrays(first, second, 0, 0)
    assert not result["nodata_agrees"]
    assert result["valid_only_in_first"] == 1 and result["valid_only_in_second"] == 0
    assert result["valid_in_both"] == 2 and result["equal_where_both_valid"] == 2
    shapes = copy_difference.compare_arrays(first, first[:1], 0, 0)
    assert shapes == {"same_shape": False, "shapes": [[2, 2], [1, 2]]}
    no_nodata = copy_difference.compare_arrays(first, first, None, None)
    assert no_nodata["valid_in_both"] == 4
