"""Fixture tests for the pixel-class module. Synthetic grids and polygons, no network."""

import numpy as np
import pyproj
import pytest
import shapely
from shapely.geometry import MultiPolygon, Polygon, box, mapping

from s2proto import masks

EPSG = 32617
X0, Y0 = 600000.0, 3800000.0
GRID = masks.TileGrid(EPSG, X0, Y0, 240, 240)


def lonlat(geometry):
    """A projected shapely geometry as a GeoJSON dict in EPSG:4326."""
    transformer = pyproj.Transformer.from_crs(EPSG, 4326, always_xy=True)

    def to_lonlat(coords):
        lon, lat = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([lon, lat])

    return mapping(shapely.transform(geometry, to_lonlat))


def square(x, y, side):
    return box(x, y, x + side, y + side)


def brute_force_classes(polygon, resolution, near_land_m=100.0):
    """Every pixel of the tile classified by direct geometry, for small fixtures."""
    height, width = GRID.shape(resolution)
    classes = np.zeros((height, width), dtype=np.uint8)
    for row in range(height):
        for col in range(width):
            left = X0 + col * resolution
            top = Y0 - row * resolution
            pixel = box(left, top - resolution, left + resolution, top)
            area = pixel.intersection(polygon).area / (resolution * resolution)
            centre = shapely.Point(left + resolution / 2, top - resolution / 2)
            if area >= 1 - 1e-9:
                classes[row, col] = 1
            elif area > 1e-9:
                classes[row, col] = 2
            elif polygon.boundary.distance(centre) <= near_land_m:
                classes[row, col] = 3
    return classes


def test_grid_shapes_transforms_and_item_parsing():
    assert GRID.shape(10) == (240, 240)
    assert GRID.shape(20) == (120, 120)
    assert GRID.shape(60) == (40, 40)
    with pytest.raises(ValueError):
        GRID.shape(7)
    assert list(GRID.transform(20))[:6] == [20, 0, X0, 0, -20, Y0]
    assert GRID.bounds() == (X0, Y0 - 2400, X0 + 2400, Y0)
    item = {
        "properties": {"proj:epsg": EPSG},
        "assets": {"red": {"proj:shape": [240, 240], "proj:transform": [10, 0, X0, 0, -10, Y0]}},
    }
    assert masks.TileGrid.from_item(item) == GRID
    item["properties"] = {"proj:code": "EPSG:32617"}
    assert masks.TileGrid.from_item(item) == GRID
    with pytest.raises(ValueError):
        masks.TileGrid.from_item({"properties": {}, "assets": item["assets"]})
    with pytest.raises(ValueError):
        masks.TileGrid.from_item({"properties": {"proj:epsg": EPSG}, "assets": {}})


def test_asset_mismatch_names_the_reason():
    good = {"proj:shape": [120, 120], "proj:transform": [20, 0, X0, 0, -20, Y0]}
    assert masks.asset_mismatch(GRID, good) is None
    assert masks.asset_resolution(good) == 20
    shifted = {"proj:shape": [240, 240], "proj:transform": [10, 0, X0 + 5, 0, -10, Y0]}
    assert "tile origin" in masks.asset_mismatch(GRID, shifted)
    odd = {"proj:shape": [80, 80], "proj:transform": [30, 0, X0, 0, -30, Y0]}
    assert "not 10, 20, or 60" in masks.asset_mismatch(GRID, odd)
    short = {"proj:shape": [100, 120], "proj:transform": [20, 0, X0, 0, -20, Y0]}
    assert "shape" in masks.asset_mismatch(GRID, short)
    assert "declares no" in masks.asset_mismatch(GRID, {})


def test_project_round_trips_and_fraction_inside():
    original = square(X0 + 1000, Y0 - 1500, 500)
    projected = masks.project(lonlat(original), EPSG)
    assert projected.bounds == pytest.approx(original.bounds, abs=1e-5)
    assert masks.fraction_inside(projected, GRID.extent()) == pytest.approx(1.0)
    half_out = square(X0 - 250, Y0 - 1500, 500)
    assert masks.fraction_inside(half_out, GRID.extent()) == pytest.approx(0.5)
    assert masks.fraction_inside(Polygon(), GRID.extent()) == 0.0


def test_window_for_clips_to_the_tile():
    window = masks.window_for((X0 + 95, Y0 - 205, X0 + 155, Y0 - 145), GRID, 10, 0.0)
    assert (window.row_off, window.col_off, window.height, window.width) == (14, 9, 7, 7)
    assert list(window.transform(GRID, 10))[:6] == [10, 0, X0 + 90, 0, -10, Y0 - 140]
    clipped = masks.window_for((X0 - 500, Y0 - 100, X0 + 50, Y0 + 500), GRID, 60, 0.0)
    assert (clipped.row_off, clipped.col_off, clipped.height, clipped.width) == (0, 0, 2, 1)
    assert masks.window_for((X0 + 5000, Y0 - 100, X0 + 5100, Y0), GRID, 10, 0.0).empty


def test_aligned_square_has_only_interior_pixels_and_exact_coverage():
    polygon = square(X0 + 500, Y0 - 1000, 50)
    mask = masks.compute_mask(polygon, GRID, 10)
    assert mask.counts["interior"] == 25
    assert mask.counts["shoreline"] == 0
    assert mask.counts["coverage_area_m2"] == pytest.approx(2500.0, abs=1e-6)
    assert (mask.window.height, mask.window.width) == (2 * 10 + 5, 2 * 10 + 5)
    inside = mask.pixel_class == 1
    assert inside.sum() == 25
    assert np.all(mask.coverage[inside] == 1.0)
    assert np.all(mask.edge_distance[inside] <= -5.0)
    expected = brute_force_classes(polygon, 10)
    rows = slice(mask.window.row_off, mask.window.row_off + mask.window.height)
    cols = slice(mask.window.col_off, mask.window.col_off + mask.window.width)
    assert np.array_equal(mask.pixel_class, expected[rows, cols])
    assert mask.counts["near_land"] == int((expected == 3).sum())
    assert mask.parameters["near_land_m"] == 100.0
    assert set(mask.timings) >= {"coverage_seconds", "near_land_seconds", "total_seconds"}


@pytest.mark.parametrize("resolution", [10, 20, 60])
def test_offset_square_matches_brute_force_classes(resolution):
    polygon = square(X0 + 503, Y0 - 1004, 47)
    mask = masks.compute_mask(polygon, GRID, resolution)
    expected = brute_force_classes(polygon, resolution)
    rows = slice(mask.window.row_off, mask.window.row_off + mask.window.height)
    cols = slice(mask.window.col_off, mask.window.col_off + mask.window.width)
    assert np.array_equal(mask.pixel_class, expected[rows, cols])
    assert mask.counts["coverage_area_m2"] == pytest.approx(47.0 * 47.0, rel=1e-9)
    wet = (mask.pixel_class == 1) | (mask.pixel_class == 2)
    assert mask.counts["naive"] == int(mask.naive.sum())
    assert mask.counts["naive_only"] == int((mask.naive & ~wet).sum())
    assert mask.counts["classes_only"] == int((wet & ~mask.naive).sum())
    near = mask.pixel_class == 3
    assert np.all(mask.edge_distance[near] > 0) and np.all(mask.edge_distance[near] <= 100.0)
    assert np.all(np.isnan(mask.edge_distance[mask.pixel_class == 0]))


def test_tiny_pond_has_no_interior_pixel_at_any_resolution():
    polygon = square(X0 + 1002, Y0 - 1006, 6)
    for resolution in (10, 20, 60):
        mask = masks.compute_mask(polygon, GRID, resolution)
        assert mask.counts["interior"] == 0
        assert mask.counts["shoreline"] == 1
        assert mask.counts["near_land"] > 0
        assert mask.counts["coverage_area_m2"] == pytest.approx(36.0, abs=1e-9)
        shoreline = mask.pixel_class == 2
        assert mask.coverage[shoreline] == pytest.approx(36.0 / resolution**2)


def test_polygon_outside_or_partly_outside_the_tile():
    outside = square(X0 + 5000, Y0 - 1000, 50)
    mask = masks.compute_mask(outside, GRID, 10)
    assert mask.window.empty and mask.counts["interior"] == 0 and mask.pixel_class.size == 0
    assert masks.naive_mask(outside, GRID, 10)[0].empty
    straddling = square(X0 - 20, Y0 - 1000, 60)
    mask = masks.compute_mask(straddling, GRID, 10)
    assert mask.counts["interior"] == 4 * 6
    assert mask.counts["coverage_area_m2"] == pytest.approx(40.0 * 60.0, abs=1e-6)
    assert mask.window.col_off == 0


def test_multipolygon_with_a_hole():
    outer = square(X0 + 300, Y0 - 900, 200)
    hole = square(X0 + 380, Y0 - 820, 40)
    part = Polygon(outer.exterior.coords, [hole.exterior.coords])
    other = square(X0 + 1200, Y0 - 900, 30)
    polygon = MultiPolygon([part, other])
    mask = masks.compute_mask(polygon, GRID, 10)
    assert mask.counts["coverage_area_m2"] == pytest.approx(polygon.area, rel=1e-12)
    assert mask.counts["interior"] == 400 - 16 + 9
    expected = brute_force_classes(polygon, 10)
    rows = slice(mask.window.row_off, mask.window.row_off + mask.window.height)
    cols = slice(mask.window.col_off, mask.window.col_off + mask.window.width)
    assert np.array_equal(mask.pixel_class, expected[rows, cols])


def test_edge_distance_cap_leaves_far_interior_without_a_distance():
    polygon = square(X0 + 60, Y0 - 2340, 2280)
    mask = masks.compute_mask(polygon, GRID, 60, edge_distance_cap_m=300.0)
    interior = mask.pixel_class == 1
    distances = mask.edge_distance[interior]
    assert np.isnan(distances).sum() > 0
    finite = distances[~np.isnan(distances)]
    assert finite.max() < 0 and finite.min() >= -300.0
    assert mask.parameters["edge_distance_cap_m"] == 300.0


def test_index_lists_windows_and_round_trips(tmp_path):
    polygon = square(X0 + 503, Y0 - 1004, 47)
    mask = masks.compute_mask(polygon, GRID, 10)
    lists = mask.index_lists()
    assert len(lists["rows"]) == int(mask.selected().sum())
    order = np.lexsort((lists["cols"], lists["rows"]))
    assert np.array_equal(order, np.arange(len(order)))
    assert masks.lists_window(lists) == mask.window
    assert masks.lists_window({"rows": np.array([]), "cols": np.array([])}).empty
    masks.save_mask(mask, tmp_path / "m.npz")
    loaded = masks.load_mask(tmp_path / "m.npz")
    assert loaded.window == mask.window and loaded.counts == mask.counts
    assert np.array_equal(loaded.pixel_class, mask.pixel_class)
    assert np.array_equal(loaded.coverage, mask.coverage)
    assert np.array_equal(loaded.naive, mask.naive)
    written = masks.save_index_lists(mask, tmp_path / "i.npz")
    assert written["pixels"] == len(lists["rows"]) and written["bytes"] > 0
    lists_back, meta = masks.load_index_lists(tmp_path / "i.npz")
    assert np.array_equal(lists_back["rows"], lists["rows"])
    assert np.array_equal(lists_back["pixel_class"], lists["pixel_class"])
    assert meta["window"] == mask.window.as_dict()


def test_naive_mask_uses_the_polygon_bounds_without_margin():
    polygon = square(X0 + 503, Y0 - 1004, 47)
    window, selected = masks.naive_mask(polygon, GRID, 10)
    assert (window.row_off, window.col_off, window.height, window.width) == (95, 50, 6, 5)
    assert selected.shape == (6, 5) and selected.all()
    mask = masks.compute_mask(polygon, GRID, 10)
    wet = (mask.pixel_class == 1) | (mask.pixel_class == 2)
    r0 = window.row_off - mask.window.row_off
    c0 = window.col_off - mask.window.col_off
    assert np.array_equal(wet[r0 : r0 + 6, c0 : c0 + 5], selected)
    assert wet.sum() == 30


def test_tile_edge_is_not_a_shoreline():
    """A lake crossing the tile edge keeps its real boundary for every distance."""
    polygon = box(X0 - 400, Y0 - 1500, X0 + 1000, Y0 - 500)
    mask = masks.compute_mask(polygon, GRID, 10)
    assert mask.window.col_off == 0
    assert mask.counts["interior"] == 100 * 100
    assert mask.counts["shoreline"] == 0
    assert mask.counts["near_land"] > 0
    # The pixel in column 0, halfway down: 5 m from the tile edge, 405 m from the west shore.
    middle = 100 - mask.window.row_off
    assert mask.pixel_class[middle, 0] == 1
    assert mask.edge_distance[middle, 0] == pytest.approx(-405.0)
    # No near-land pixel sits along the cut. Near-land pixels lie north, south, and east only.
    near = mask.pixel_class == 3
    assert not near[:, 0].any() or near[:, 0].sum() == near[:, 1].sum()
    assert mask.parameters["mask_version"] == masks.MASK_VERSION


def test_lake_outside_the_tile_still_has_near_land_pixels_inside_it():
    polygon = square(X0 - 90, Y0 - 1000, 50)
    mask = masks.compute_mask(polygon, GRID, 10)
    assert mask.counts["interior"] == 0 and mask.counts["shoreline"] == 0
    assert mask.counts["near_land"] > 0
    assert np.all(mask.edge_distance[mask.pixel_class == 3] > 0)


def test_naive_only_pixels_split_into_slivers_and_empty_contacts():
    polygon = square(X0 + 1002, Y0 - 1006, 6)
    mask = masks.compute_mask(polygon, GRID, 10)
    counts = mask.counts
    assert counts["naive_only"] == counts["naive_only_sliver"] + counts["naive_only_empty"]
    assert counts["naive_only_empty"] == 1 and counts["naive_only_sliver"] == 0
    assert set(masks.empty_counts()) == set(counts)
