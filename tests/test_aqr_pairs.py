"""Pairing and paired-value helpers for probes T5 and T6. Synthetic inputs, no network."""

from __future__ import annotations

import numpy as np
import pytest

from s2proto import aqr_pairing, masks, pairs

TAHOE = "S2B_MSIAQR_20250801T184919_N0511_R113_T10SGJ_20250801T223016"


def l1c_item(name, strip):
    return {
        "id": name,
        "properties": {
            "s2:product_uri": f"{name}.SAFE",
            "s2:datastrip_id": f"S2B_OPER_MSI_L1C_DS_2BPS_{name[-15:]}_S{strip}_N05.11",
        },
    }


def c1_item(item_id, strip, created="2025-08-01T23:41:44Z", tile="MGRS-10SGJ"):
    return {
        "id": item_id,
        "properties": {
            "grid:code": tile,
            "platform": "sentinel-2b",
            "created": created,
            "s2:datastrip_id": f"S2B_OPER_MSI_L2A_DS_2BPS_20250801T223959_S{strip}_N05.11",
            "proj:code": "EPSG:32610",
        },
        "assets": {
            "red": {
                "proj:transform": [10, 0, 699960.0, 0, -10, 4400040.0],
                "proj:shape": [10980, 10980],
            }
        },
    }


def scene(product=TAHOE, layers=("B04", "B08", "B11", "B01", "l2_flags")):
    return {
        "product": product,
        "tile": "10SGJ",
        "platform": "S2B",
        "generation_time": "2025-08-01T22:30:16Z",
        "layers": {
            layer: {"key": f"version_01/T10SGJ/{product}_{layer}.tif", "size": 1}
            for layer in layers
        },
    }


# The Tahoe split datastrip of finding 30, as Earth Search declared it on 2026-10-14.
L1C_ITEMS = [
    l1c_item("S2B_MSIL1C_20250801T184919_N0511_R113_T10SGJ_20250801T223016", "20250801T190325"),
    l1c_item("S2B_MSIL1C_20250801T184919_N0511_R113_T10SGJ_20250801T222448", "20250801T185203"),
]
C1_ITEMS = [
    c1_item("S2B_T10SGJ_20250801T190325_L2A", "20250801T190325"),
    c1_item("S2B_T10SGJ_20250801T185203_L2A", "20250801T185203", "2025-08-01T23:42:22Z"),
]


def test_names_and_datastrips():
    assert aqr_pairing.l1c_name(TAHOE).startswith("S2B_MSIL1C_20250801T184919")
    with pytest.raises(ValueError):
        aqr_pairing.l1c_name("S2B_MSIL2A_20250801T184919_N0511_R113_T10SGJ_20250801T223016")
    assert (
        aqr_pairing.datastrip_sensing(
            "S2B_OPER_MSI_L2A_DS_2BPS_20250801T223959_S20250801T190325_N05.11"
        )
        == "20250801T190325"
    )
    assert aqr_pairing.datastrip_sensing(None) is None
    assert aqr_pairing.normalize_tile("MGRS-5VMG") == "05VMG"
    assert aqr_pairing.normalize_tile("MGRS-10SGJ") == "10SGJ"


def test_pair_picks_the_same_datastrip_not_the_latest_created():
    record = aqr_pairing.pair_product(scene(), L1C_ITEMS, C1_ITEMS)
    assert record["status"] == "datastrip"
    assert record["c1_item"] == "S2B_T10SGJ_20250801T190325_L2A"
    assert record["datastrip_sensing"] == "20250801T190325"


def test_pair_statuses():
    assert aqr_pairing.pair_product(scene(), [], C1_ITEMS)["status"] == "no_l1c_item"
    assert aqr_pairing.pair_product(scene(), L1C_ITEMS, C1_ITEMS[1:])["status"] == "no_c1_item"
    twice = [*C1_ITEMS, c1_item("again", "20250801T190325", "2025-08-02T00:00:00Z")]
    record = aqr_pairing.pair_product(scene(), L1C_ITEMS, twice)
    assert record["status"] == "datastrip_multiple"
    assert record["c1_item"] == "again"
    other_tile = [c1_item("x", "20250801T190325", tile="MGRS-10SGH")]
    assert aqr_pairing.pair_product(scene(), L1C_ITEMS, other_tile)["status"] == "no_c1_item"


def test_products_by_item_skips_incomplete_and_keeps_latest_generation():
    full = scene()
    partial = scene(layers=("B04",))
    partial["product"] = TAHOE.replace("223016", "223017")
    chosen, records = aqr_pairing.products_by_item(
        [full, partial], L1C_ITEMS, C1_ITEMS, aqr_pairing.T6_LAYERS.values()
    )
    assert list(chosen) == ["S2B_T10SGJ_20250801T190325_L2A"]
    assert {r["status"] for r in records} == {"datastrip", "incomplete_layers"}


def test_stand_in_item_declares_the_20m_grid_and_patched_grid_matches():
    item = aqr_pairing.stand_in_item(C1_ITEMS[0], scene())
    assert item["id"] == TAHOE
    assert item["properties"]["aqr:paired_item"] == C1_ITEMS[0]["id"]
    red = item["assets"]["red"]
    assert red["proj:transform"][:6] == [20, 0.0, 699960.0, 0.0, -20, 4400040.0]
    assert red["proj:shape"] == [5490, 5490]
    assert item["assets"]["scl"]["raster:bands"][0]["data_type"] == "int32"
    assert red["href"].endswith(f"{TAHOE}_B04.tif")
    grid = aqr_pairing.grid_20m(item)
    assert grid == masks.TileGrid.from_item(C1_ITEMS[0])
    assert aqr_pairing.grid_20m(C1_ITEMS[0]) == grid


def test_resampling_helpers():
    ten = np.array([[1, 3, 0, 4], [5, 7, 4, 4]], dtype=np.uint16)
    mean, valid = pairs.block_mean_10m(ten)
    assert mean.tolist() == [[4.0, 3.0]]
    assert valid.tolist() == [[True, False]]
    assert pairs.window_60m(4, 2, 5, 2) == (1, 0, 2, 2)
    sixty = np.array([[10, 20], [30, 0]], dtype=np.uint16)
    values, ok = pairs.parent_60m(sixty, 4, 2, 5, 2)
    assert values[:, 0].tolist() == [10, 10, 30, 30, 30]
    assert values[:, 1].tolist() == [20, 20, 0, 0, 0]
    assert ok[:, 1].tolist() == [True, True, False, False, False]


def test_moments_and_summary():
    m = pairs.Moments(values=True)
    a = np.array([100.0, 200.0, 300.0, 400.0])
    s = np.array([100.0, 100.0, 290.0, 500.0])
    m.add(a, s)
    out = pairs.summarize(m)
    assert out["n"] == 4
    assert out["difference_units"]["mean"] == pytest.approx(2.5)
    assert out["difference_units"]["p50"] == 0
    assert out["share_disagree"] == 0.5
    assert out["verdict"] == "differs"
    assert out["median_units"] == {"product": 200, "c1": 100}
    other = pairs.Moments()
    other.add(np.array([1.0]), np.array([1.0]))
    m.merge(other)
    assert m.n == 5
    assert pairs.summarize(pairs.Moments()) == {"n": 0}
    assert pairs.hist_quantile(np.array([0, 2, 1]), -1, 0.5) == 0
    assert pairs.spread([3.0, 1.0, 2.0])["median"] == 2.0


def test_tolerances_name_every_rule():
    assert [key.split("_", 1)[0] for key in pairs.TOLERANCES] == [f"P{i}" for i in range(1, 10)]
