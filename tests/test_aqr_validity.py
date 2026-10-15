"""Fixture tests for probe T4, pixel validity of the aquatic reflectance product. No network."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from affine import Affine

from s2proto import aqr, harness, masks, validity

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("aqr_validity", ROOT / "benchmarks/aqr_validity.py")
aqr_validity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aqr_validity)

EXPONENTS = {"swir": 0, "cirrus": 1, "toa": 2, "negative": 3, "outofscene": 4, "mixed": 5}
N = validity.NODATA


def test_flag_exponents_come_from_settings_keys():
    settings = {"flag_exponent_toa": "2", "flag_exponent_swir": "0", "l2w_mask": "True"}
    settings["flag_exponent_bad"] = "x"
    assert validity.flag_exponents(settings) == {"swir": 0, "toa": 2}


def test_flags_decode_only_exact_multiples():
    flags = np.array([0, 10000, 40000, 90000, N, 12345], dtype=np.int32)
    decoded, missing, not_multiple = validity.decode_flags(flags)
    assert decoded.tolist() == [0, 1, 4, 9, 0, 0]
    assert missing.tolist() == [False, False, False, False, True, False]
    assert not_multiple.tolist() == [False, False, False, False, False, True]


def test_ndwi_agreement_uses_the_rounding_interval():
    green = np.array([500, 500, 0, 1])
    nir = np.array([100, 100, 0, 0])
    ndwi = np.array([6667, 6000, 0, 10000])
    comparable, agree = validity.ndwi_agrees(green, nir, ndwi)
    # The third pixel's G + N interval reaches zero, the fourth's reaches exactly zero.
    assert comparable == 2
    assert agree == 1


def window():
    """A 2 by 3 window: interior, shoreline, and near-land columns."""
    pixel_class = np.array([[1, 2, 3], [1, 2, 3]], dtype=np.uint8)
    b03 = np.array([[500, N, 300], [-5, 200, 10001]], dtype=np.int16)
    bands = {band: np.full((2, 3), 100, dtype=np.int16) for band in validity.BANDS}
    bands["B03"] = b03
    ndwi = np.array([[6667, N, -100], [500, 0, -2000]], dtype=np.int16)
    flags = np.array([[0, 10000, 10000], [80000, 12345, 50000]], dtype=np.int32)
    scl = np.array([[6, 4, 0], [9, 6, 8]], dtype=np.uint8)
    return pixel_class, bands, ndwi, flags, scl


def test_class_counts_separate_processor_masking_from_no_data():
    pixel_class, bands, ndwi, flags, scl = window()
    counts = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, scl)
    shoreline = counts["shoreline"]
    assert shoreline["pixels"] == 2
    assert shoreline["joined_pixels"] == 2
    assert shoreline["bands"]["B03"] == {
        "no_data": 1,
        "processor_masked": 1,
        "negative": 0,
        "above_one": 0,
    }
    assert counts["interior"]["bands"]["B03"]["negative"] == 1
    near = counts["near_land"]
    assert near["joined_pixels"] == 1
    assert near["bands"]["B03"]["above_one"] == 1
    assert near["bands"]["B03"]["processor_masked"] == 0
    assert shoreline["flags"]["not_multiple"] == 1
    assert shoreline["flags"]["bits"]["swir"] == 1
    assert counts["interior"]["flags"]["none"] == 1
    assert counts["interior"]["flags"]["bits"]["negative"] == 1
    assert near["flags"]["bits"]["swir"] == 2
    assert near["flags"]["bits"]["toa"] == 1


def test_class_counts_compare_water_and_cloud_with_the_scene_classification():
    pixel_class, bands, ndwi, flags, scl = window()
    counts = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, scl)
    interior = counts["interior"]
    assert interior["scl"] == {"6": 1, "9": 1}
    assert interior["water"]["usable"] == 2
    assert interior["water"]["ndwi_vs_scl"] == {
        "both": 1,
        "product_only": 1,
        "scl_only": 0,
        "neither": 0,
    }
    assert interior["water"]["acolite_vs_scl"]["both"] == 1
    assert interior["cloud"]["scl_cloud"] == 1
    assert interior["cloud"]["scl_cloud_unflagged"] == 0
    assert interior["cloud"]["scl_cloud_by_flag"]["negative"] == 1
    near = counts["near_land"]
    # The no-data scene classification pixel and the flagged cloud pixel.
    assert near["cloud"]["scl_cloud"] == 1
    assert near["cloud"]["scl_cloud_by_flag"]["swir"] == 1
    # The second interior pixel is comparable, with B03 -5 and B08 100, and disagrees.
    assert interior["ndwi_recompute"]["B08"] == {"comparable": 2, "agree": 1}


def test_class_counts_without_a_join_leave_comparisons_null():
    pixel_class, bands, ndwi, flags, _ = window()
    counts = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, None)
    assert counts["shoreline"]["bands"]["B03"]["processor_masked"] is None
    assert counts["shoreline"]["water"] is None
    assert counts["shoreline"]["cloud"] is None


def record(tile, joined, scl, tier="pilot"):
    pixel_class, bands, ndwi, flags, _ = window()
    classes = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, scl)
    return {
        "tile": tile,
        "product": f"P-{tile}",
        "water_body_id": f"nhd-{tile}",
        "tier": tier,
        "size_class_m": 10,
        "joined": joined,
        "classes": classes,
    }


def test_pooling_mixes_joined_and_unjoined_records_and_applies_rule_r3():
    scl = window()[4]
    records = [record("A", True, scl), record("B", False, None), record("A", True, scl)]
    pooled = validity.pool(records)["all"]
    assert pooled["shoreline"]["pixels"] == 6
    assert pooled["shoreline"]["joined_pixels"] == 4
    assert pooled["shoreline"]["bands"]["B03"]["no_data"] == 3
    assert pooled["shoreline"]["bands"]["B03"]["processor_masked"] == 2
    verdicts = validity.class_verdicts(pooled)
    assert verdicts["shoreline"]["largest_share"] == 0.5
    assert verdicts["shoreline"]["masked_by_processor"] is True
    assert verdicts["interior"]["masked_by_processor"] is False
    by_tile = validity.pool(records, key=lambda r: r["tile"])
    assert set(by_tile) == {"A", "B"}
    assert validity.class_verdicts(by_tile["B"])["shoreline"]["masked_by_processor"] is None


def scene(product, layers=aqr.OBSERVED_LAYERS):
    fields = aqr.parse_key(f"version_01/T17SKU/{product}_B04.tif")
    return {k: fields[k] for k in ("product", "tile", "platform", "sensing", "baseline")} | {
        "generation_time": fields["generation_time"],
        "sensing_time": fields["sensing_time"],
        "layers": {layer: {"key": f"{product}_{layer}"} for layer in layers},
    }


def test_monthly_selection_takes_the_earliest_complete_scene():
    early_partial = scene(
        "S2A_MSIAQR_20251002T162149_N0511_R040_T17SKU_20251002T195355", ("B06", "settings")
    )
    first_old = scene("S2B_MSIAQR_20251005T162149_N0511_R040_T17SKU_20251005T195355")
    first_new = scene("S2B_MSIAQR_20251005T162149_N0511_R040_T17SKU_20251207T000000")
    later = scene("S2C_MSIAQR_20251015T162149_N0511_R040_T17SKU_20251015T195355")
    scenes = {s["product"]: s for s in (early_partial, first_old, first_new, later)}
    chosen = aqr_validity.select_monthly(scenes, ["2025-10", "2025-11"])
    assert chosen[0]["chosen"]["product"] == first_new["product"]
    assert chosen[0]["same_sensing"] == [first_old["product"]]
    assert chosen[0]["incomplete"] == [early_partial["product"]]
    assert chosen[0]["listed"] == 4
    assert chosen[1]["chosen"] is None


def test_choose_item_prefers_the_latest_created_joined_item():
    join = {"joined": {"collection": "c1", "ids": ["a", "b"]}}
    items = {"c1": [{"id": "a", "created": "2025-01-01"}, {"id": "b", "created": "2025-02-01"}]}
    items["c1"].append({"id": "c", "created": "2026-01-01"})
    assert aqr_validity.choose_item(join, items)["id"] == "b"
    assert aqr_validity.choose_item({"joined": None}, items) is None


def test_grid_check_applies_rule_r1():
    expected = Affine(20, 0, 199980, 0, -20, 3900000)
    header = {"epsg": 32617, "transform": [20, 0, 199980, 0, -20, 3900000], "shape": [5490, 5490]}
    assert aqr_validity.grid_check(header, expected)["aligned"] is True
    shifted = header | {"transform": [20, 0, 199990, 0, -20, 3900000]}
    check = aqr_validity.grid_check(shifted, expected)
    assert check["aligned"] is False
    assert check["origin_offset_pixels"] == [0.5, 0.0]
    small = header | {"shape": [1830, 1830]}
    assert aqr_validity.grid_check(small, expected)["aligned"] is False


def test_tiles_are_the_stage_2_tiles():
    stage_2 = json.loads(aqr_validity.STAGE_2_RESULT.read_text())
    for region, tile in aqr_validity.TILES.items():
        assert stage_2["scenes"][region]["tile"] == tile
    assert "iliamna" not in aqr_validity.TILES


def test_dry_run_prints_the_tolerances_and_contacts_nothing(monkeypatch, capsys):
    def refuse(*args, **kwargs):
        raise AssertionError("the dry run contacted a provider")

    monkeypatch.setattr(harness.Client, "_request", refuse)
    assert aqr_validity.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    for key in validity.TOLERANCES:
        assert key in out
    assert aqr.BUCKET in out
    assert "17RNK" in out


def test_summary_counts_tiles_scenes_and_masked_cases():
    scl = window()[4]
    records = [record("17SKU", True, scl), record("10SGJ", False, None, tier="large")]
    gdal = {"product": {"requests": 3, "bytes": 30}, "scl": {"requests": 1, "bytes": 5}}
    scenes = [
        {
            "tile": "17SKU",
            "month": "2025-10",
            "product": "P-17SKU",
            "sensing_time": "2025-10-15T16:21:49Z",
            "join": {"status": "exact"},
            "scl_item": {"collection": "sentinel-2-c1-l2a"},
            "scl_grid": {"aligned": True},
            "settings": {"sha256": "x", "flag_exponents": EXPONENTS},
            "gdal": gdal,
            "seconds": 1.0,
            "lakes_read": 1,
        },
        {
            "tile": "10SGJ",
            "month": "2025-10",
            "product": "P-10SGJ",
            "sensing_time": "2025-10-20T18:53:29Z",
            "join": {"status": "none"},
            "scl_item": None,
            "settings": {"sha256": "x", "flag_exponents": EXPONENTS},
            "gdal": gdal,
            "seconds": 1.0,
            "lakes_read": 1,
        },
        {"tile": "10SGJ", "month": "2025-11", "product": None, "listed_in_month": 0},
    ]
    tile_meta = {"17SKU": {"lakes": {"x": {"water_body_id": "x", "window": {"height": 0}}}}}
    summary = aqr_validity.summarize(scenes, records, tile_meta)
    assert summary["distinct_tiles"] == 2
    assert summary["distinct_tile_dates"] == 2
    assert summary["scenes_read"] == 2
    assert summary["scenes_scl_aligned"] == 1
    assert summary["months_without_scene"] == {"10SGJ": ["2025-11"], "17SKU": []}
    assert summary["lakes_outside_tile"] == ["x"]
    assert summary["processor_masked_cases"] == [
        {
            "product": "P-17SKU",
            "water_body_id": "nhd-17SKU",
            "class": "shoreline",
            "band": "B03",
            "processor_masked": 1,
        }
    ]
    assert summary["gdal_product_bytes_requested"] == 60
    assert set(summary["shares_by_size"]) == {"10 m", "anchor"}
    assert summary["shares"]["shoreline"]["bands"]["B03"]["processor_masked"] == 0.5


@pytest.mark.parametrize("resolution", [20])
def test_tile_masks_use_the_product_grid(resolution):
    grid = masks.TileGrid(32617, 199980.0, 3900000.0)
    built = aqr_validity.tile_masks("lanier", "17SKU", grid)
    assert len(built) == len(aqr_validity.pilot_lakes("lanier"))
    for lake in built.values():
        assert lake["mask"].resolution == resolution


def test_no_data_diagnostic_compares_band_no_data_with_the_out_of_scene_flag():
    pixel_class, bands, ndwi, flags, scl = window()
    # One shoreline pixel holds no data in every band and carries the out-of-scene flag.
    for values in bands.values():
        values[0, 1] = N
    flags[0, 1] = 160000
    classes = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, scl)
    records = [{"product": "P", "water_body_id": "w", "classes": classes}]
    diagnostic = aqr_validity.no_data_diagnostic(records)
    assert diagnostic["comparisons"] == 3 * len(validity.BANDS)
    assert diagnostic["mismatches"] == []
    assert diagnostic["scenes_with_no_data"]["P"]["bands"]["B03"] == 1
    assert diagnostic["scenes_with_no_data"]["P"]["out_of_scene_flag"] == 1
    flags[0, 1] = 10000
    classes = validity.class_counts(pixel_class, bands, ndwi, flags, EXPONENTS, scl)
    records = [{"product": "P", "water_body_id": "w", "classes": classes}]
    mismatches = aqr_validity.no_data_diagnostic(records)["mismatches"]
    assert {(m["class"], m["no_data"], m["out_of_scene_flag"]) for m in mismatches} == {
        ("shoreline", 1, 0)
    }
    assert len(mismatches) == len(validity.BANDS)
