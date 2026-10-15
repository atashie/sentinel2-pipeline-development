"""Probe T7 rules: one option's values for the same pixels in two overlapping tiles.

Pure functions. The rules are fixed before any pixel is read and printed by the probe's dry run.
Probe T7 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.
"""

from __future__ import annotations

from itertools import combinations

from s2proto import pairs

RESOLUTION = 20
GRID_TOLERANCE_PIXELS = 1e-6
TILE_PIXELS_20M = 5490
WIDEN_POINTS = 0.05
"""ACOLITE widens or narrows tile disagreement beyond this share difference against Sen2Cor."""
OPTIONS = ("acolite", "sen2cor")
SUBSETS = ("all", "own_clear_water", "shared", "shared_clear_water")

TOLERANCES = {
    "O1_pairs": (
        "Probe T6's stage 4 plan fixes the regions, acquisitions, products, and member lakes. "
        "Two tiles of one region form a pair when they share a UTM zone and a member lake. "
        "Pairs across zones are listed and not compared. Each tile's Sen2Cor source is the "
        "Collection 1 item its product was paired with, from the saved Level-2A stage 4 catalog."
    ),
    "O2_grid": (
        "Both tiles declare the same CRS. Their 20 m origins differ by a whole number of pixels "
        f"within {GRID_TOLERANCE_PIXELS:g} pixel. Every layer read sits on its own tile's grid "
        f"within {GRID_TOLERANCE_PIXELS:g} pixel at its resolution. A pair that fails leaves "
        "every comparison. When the offset is not a whole number of 60 m pixels, B01 leaves the "
        "Sen2Cor comparison, because its 60 m parents would cover different ground."
    ),
    "O3_pixels": (
        "Pixel classes come from each lake's exact polygon on the shared 20 m grid, masks "
        "version 2, interior, shoreline, and near-land. Overlap pixels lie inside both tiles."
    ),
    "O4_units": (
        "Values are integers of 1e-04 reflectance. Product values are used as stored. "
        "Collection 1 values are the stored integer times the declared scale plus the declared "
        "offset, with rule P3's resampling for 10 m and 60 m bands. Both Collection 1 items of a "
        "pair must declare one scale and offset per band. Differences are tile A minus tile B, "
        "tiles in name order."
    ),
    "O5_comparable": (
        "Within one option, a pixel is comparable in a band when both tiles hold data, rule "
        "P5's no-data values. The shared set holds the pixels comparable in both options."
    ),
    "O6_strata": (
        "Per option, band, and pixel class. Four subsets: all comparable pixels, own clear water "
        "where the option's own flags call the pixel clear water in both tiles, the shared set, "
        "and shared clear water, clear by both options' flags in both tiles. ACOLITE clear water "
        f"is a decoded flag integer of 0. Sen2Cor clear water is scene class {pairs.SCL_WATER}."
    ),
    "O7_tile_agreement": (
        f"A pixel disagrees when its two tiles differ by more than {pairs.DISAGREE_UNITS} units, "
        f"0.005 reflectance. An option's tiles agree in a band, class, and subset when at least "
        f"{pairs.AGREE_SHARE:.0%} of its pixels do not disagree. A stratum with fewer than "
        f"{pairs.MIN_RECORD_PIXELS} pixels gets no verdict. Pooled over pairs and lakes."
    ),
    "O8_widening": (
        "On the shared and shared clear-water sets, ACOLITE widens tile disagreement in a band "
        f"and class when its share beyond 0.005 exceeds Sen2Cor's by more than "
        f"{WIDEN_POINTS * 100:.0f} percentage points. It narrows it when Sen2Cor's share "
        "exceeds ACOLITE's by more than that. Otherwise the two are similar. This compares "
        "consistency across tiles. It says nothing about accuracy, assumption A52."
    ),
    "O9_flag_diagnostic": (
        "Diagnostic only, never a rule. Per option and class, the share of overlap pixels whose "
        "quality code differs between the two tiles: the decoded ACOLITE flag integer, and the "
        "scene classification class."
    ),
}


def zone_pairs(scenes: list[dict]) -> tuple[list[dict], list[dict]]:
    """Same-zone tile pairs that share a member lake, and the cross-zone pairs left out."""
    same, cross = [], []
    by_region: dict[str, list[dict]] = {}
    for scene in scenes:
        by_region.setdefault(scene["region"], []).append(scene)
    for region, group in sorted(by_region.items()):
        for a, b in combinations(sorted(group, key=lambda s: s["tile"]), 2):
            shared = sorted(set(a["members"]) & set(b["members"]))
            if not shared:
                continue
            pair = {"region": region, "tile_a": a["tile"], "tile_b": b["tile"], "lakes": shared}
            (same if a["epsg"] == b["epsg"] else cross).append(pair)
    return same, cross


def origin_offset(grid_a, grid_b, resolution: int = RESOLUTION) -> tuple[float, float]:
    """Rows and columns from tile A's pixel to the same ground pixel in tile B."""
    return (grid_b.y0 - grid_a.y0) / resolution, (grid_a.x0 - grid_b.x0) / resolution


def whole_offset(offset: tuple[float, float]) -> tuple[int, int] | None:
    rounded = tuple(round(v) for v in offset)
    if all(abs(v - r) <= GRID_TOLERANCE_PIXELS for v, r in zip(offset, rounded, strict=True)):
        return int(rounded[0]), int(rounded[1])
    return None


def overlap_windows(
    window: tuple[int, int, int, int], offset: tuple[int, int], size: int = TILE_PIXELS_20M
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    """Clip a tile A window (row, col, height, width) to pixels inside both tiles.

    Returns the clipped window in tile A coordinates and the same pixels in tile B coordinates.
    """
    row, col, height, width = window
    dr, dc = offset
    r0 = max(row, -dr, 0)
    c0 = max(col, -dc, 0)
    r1 = min(row + height, size - dr, size)
    c1 = min(col + width, size - dc, size)
    if r1 <= r0 or c1 <= c0:
        return None
    a = (r0, c0, r1 - r0, c1 - c0)
    return a, (r0 + dr, c0 + dc, r1 - r0, c1 - c0)


def verdict(n: int, disagree: int) -> str:
    if n < pairs.MIN_RECORD_PIXELS:
        return "too_few"
    return "agree" if 1 - disagree / n >= pairs.AGREE_SHARE else "differs"


def widening(acolite_share: float | None, sen2cor_share: float | None) -> str | None:
    if acolite_share is None or sen2cor_share is None:
        return None
    if acolite_share - sen2cor_share > WIDEN_POINTS:
        return "widens"
    if sen2cor_share - acolite_share > WIDEN_POINTS:
        return "narrows"
    return "similar"
