"""Pixel classes for one water body on one tile grid. Geometry only, no network.

Every water body is stored as three pixel classes per resolution, assumption A20: interior
pixels lie entirely inside the polygon, shoreline pixels intersect it partially, and near-land
pixels do not intersect it but have their centre within the near-land distance of the polygon
edge, assumption A21. Practice P1 computes them once per tile and resolution and reuses them for
every date. This module is that computation, plus the naive per-scene mask it is compared with.

Coverage fractions are exact polygon areas, not sampled. Pixels the polygon boundary can touch
are found by rasterizing the boundary and growing the result by one pixel. Their intersection
area with the polygon is computed with the polygon clipped to blocks, so a detailed shoreline
is not intersected with every pixel. Every other pixel is entirely inside or entirely outside,
decided by its centre. Edge distances are exact distances from pixel centres to the boundary
segments, negative inside the polygon as the draft contract states.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyproj
import shapely
from affine import Affine
from rasterio import features
from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry

CLASS_CODES = {"interior": 1, "shoreline": 2, "near_land": 3}
CLASS_NAMES = {code: name for name, code in CLASS_CODES.items()}
RESOLUTIONS = (10, 20, 60)
NEAR_LAND_M = 100.0
FRACTION_TOLERANCE = 1e-6
"""Coverage within this fraction of a whole pixel counts as 1, and within it of zero as 0."""
DEFAULT_TILE_PIXELS = 10980
"""Sentinel-2 tiles are 109.8 km squares, 10,980 pixels at 10 m, claim G3."""
EDGE_DISTANCE_CAP_M = 1000.0
"""Edge distance is exact up to this distance. Farther pixels are stored as not a number."""
BLOCK_M = 2000.0
"""Coverage is computed with the polygon clipped to blocks this wide, in metres."""
MASK_VERSION = 2
"""Bumped when the classification or distance algorithm changes. Saved with every mask."""


@dataclass(frozen=True)
class TileGrid:
    """One tile's pixel grid. The coarser grids nest inside the 10 m grid, claim G3."""

    epsg: int
    x0: float
    y0: float
    width_10m: int = DEFAULT_TILE_PIXELS
    height_10m: int = DEFAULT_TILE_PIXELS

    def shape(self, resolution: int) -> tuple[int, int]:
        if (self.height_10m * 10) % resolution or (self.width_10m * 10) % resolution:
            raise ValueError(f"{resolution} m does not nest in this grid")
        return self.height_10m * 10 // resolution, self.width_10m * 10 // resolution

    def transform(self, resolution: int) -> Affine:
        return Affine(resolution, 0.0, self.x0, 0.0, -resolution, self.y0)

    def bounds(self) -> tuple[float, float, float, float]:
        return (
            self.x0,
            self.y0 - self.height_10m * 10,
            self.x0 + self.width_10m * 10,
            self.y0,
        )

    def extent(self) -> BaseGeometry:
        return box(*self.bounds())

    @classmethod
    def from_item(cls, item: dict, asset_key: str = "red") -> TileGrid:
        """The grid a catalog item declares, from its item CRS and one 10 m asset."""
        props = item.get("properties", {})
        epsg = props.get("proj:epsg")
        if epsg is None:
            code = props.get("proj:code") or ""
            if not code.upper().startswith("EPSG:"):
                raise ValueError("item declares no proj:epsg and no EPSG proj:code")
            epsg = int(code.split(":", 1)[1])
        asset = item.get("assets", {}).get(asset_key)
        if not asset or "proj:transform" not in asset or "proj:shape" not in asset:
            raise ValueError(f"asset {asset_key} lacks proj:transform or proj:shape")
        a, _, x0, _, e, y0 = asset["proj:transform"][:6]
        if a != 10 or e != -10:
            raise ValueError(f"asset {asset_key} is not a north-up 10 m grid: {a}, {e}")
        height, width = asset["proj:shape"]
        return cls(int(epsg), float(x0), float(y0), int(width), int(height))


def asset_mismatch(grid: TileGrid, asset: dict) -> str | None:
    """Why an asset's declared grid does not nest in the tile grid, or None when it does."""
    transform = asset.get("proj:transform")
    shape_ = asset.get("proj:shape")
    if not transform or not shape_:
        return "asset declares no proj:transform or proj:shape"
    a, _, x0, _, e, y0 = transform[:6]
    if a <= 0 or e != -a or (x0, y0) != (grid.x0, grid.y0):
        return f"asset grid {transform[:6]} is not north-up on the tile origin"
    resolution = int(a)
    if resolution != a or resolution not in RESOLUTIONS:
        return f"asset resolution {a} m is not 10, 20, or 60 m"
    if tuple(shape_) != grid.shape(resolution):
        return f"asset shape {shape_} is not {grid.shape(resolution)} at {resolution} m"
    return None


def asset_resolution(asset: dict) -> int:
    return int(asset["proj:transform"][0])


def project(geometry: dict | BaseGeometry, epsg: int) -> BaseGeometry:
    """A GeoJSON geometry in EPSG:4326 as a shapely geometry in the tile CRS, in metres."""
    transformer = pyproj.Transformer.from_crs(4326, epsg, always_xy=True)
    geom = shape(geometry) if isinstance(geometry, dict) else geometry

    def to_crs(coords):
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geom, to_crs)


def fraction_inside(polygon: BaseGeometry, region: BaseGeometry) -> float:
    """Share of the polygon's area that lies inside the region, 0 to 1."""
    if polygon.is_empty or polygon.area == 0:
        return 0.0
    return float(polygon.intersection(region).area / polygon.area)


@dataclass(frozen=True)
class Window:
    """Pixel window in tile coordinates at one resolution."""

    row_off: int
    col_off: int
    height: int
    width: int

    @property
    def empty(self) -> bool:
        return self.height <= 0 or self.width <= 0

    def transform(self, grid: TileGrid, resolution: int) -> Affine:
        return grid.transform(resolution) @ Affine.translation(self.col_off, self.row_off)

    def as_dict(self) -> dict:
        return {
            "row_off": self.row_off,
            "col_off": self.col_off,
            "height": self.height,
            "width": self.width,
        }


def window_for(
    bounds: tuple[float, float, float, float], grid: TileGrid, resolution: int, margin_m: float
) -> Window:
    """The pixel window covering the bounds plus a margin, clipped to the tile."""
    minx, miny, maxx, maxy = bounds
    height, width = grid.shape(resolution)
    col0 = int(np.floor((minx - margin_m - grid.x0) / resolution))
    col1 = int(np.ceil((maxx + margin_m - grid.x0) / resolution))
    row0 = int(np.floor((grid.y0 - maxy - margin_m) / resolution))
    row1 = int(np.ceil((grid.y0 - miny + margin_m) / resolution))
    col0, row0 = max(col0, 0), max(row0, 0)
    col1, row1 = min(col1, width), min(row1, height)
    return Window(row0, col0, max(row1 - row0, 0), max(col1 - col0, 0))


def _rasterize(geometry: BaseGeometry, window: Window, transform: Affine, all_touched: bool):
    if geometry.is_empty:
        return np.zeros((window.height, window.width), dtype=bool)
    burned = features.rasterize(
        [(mapping(geometry), 1)],
        out_shape=(window.height, window.width),
        transform=transform,
        all_touched=all_touched,
        dtype="uint8",
    )
    return burned.astype(bool)


def _grow(mask: np.ndarray) -> np.ndarray:
    """The mask plus its eight-connected neighbours."""
    grown = mask.copy()
    grown[1:, :] |= mask[:-1, :]
    grown[:-1, :] |= mask[1:, :]
    grown[:, 1:] |= mask[:, :-1]
    grown[:, :-1] |= mask[:, 1:]
    grown[1:, 1:] |= mask[:-1, :-1]
    grown[:-1, :-1] |= mask[1:, 1:]
    grown[1:, :-1] |= mask[:-1, 1:]
    grown[:-1, 1:] |= mask[1:, :-1]
    return grown


def boundary_segments(polygon: BaseGeometry) -> np.ndarray:
    """Every boundary edge as a two-point line, for a spatial index."""
    parts = []
    rings = [ring for part in shapely.get_parts(polygon) for ring in shapely.get_rings(part)]
    for ring in rings:
        coords = shapely.get_coordinates(ring)
        if len(coords) >= 2:
            parts.append(np.stack([coords[:-1], coords[1:]], axis=1))
    if not parts:
        return np.empty(0, dtype=object)
    return shapely.linestrings(np.concatenate(parts))


def exact_coverage(
    polygon: BaseGeometry,
    window: Window,
    transform: Affine,
    resolution: int,
    candidates: np.ndarray,
    block_m: float = BLOCK_M,
) -> np.ndarray:
    """Area fraction of every candidate pixel inside the polygon. Others are 0."""
    coverage = np.zeros((window.height, window.width), dtype=np.float64)
    pixel_area = float(resolution) * resolution
    block = max(int(block_m // resolution), 1)
    for r0 in range(0, window.height, block):
        for c0 in range(0, window.width, block):
            part = candidates[r0 : r0 + block, c0 : c0 + block]
            if not part.any():
                continue
            rows, cols = np.nonzero(part)
            rows, cols = rows + r0, cols + c0
            xmin, ymax = transform.c + c0 * resolution, transform.f - r0 * resolution
            xmax = xmin + part.shape[1] * resolution
            ymin = ymax - part.shape[0] * resolution
            piece = shapely.clip_by_rect(polygon, xmin, ymin, xmax, ymax)
            if piece.is_empty:
                continue
            left = transform.c + cols * resolution
            top = transform.f - rows * resolution
            boxes = shapely.box(left, top - resolution, left + resolution, top)
            areas = shapely.area(shapely.intersection(boxes, piece))
            coverage[rows, cols] = areas / pixel_area
    return coverage


def signed_distances(
    tree: shapely.STRtree,
    xs: np.ndarray,
    ys: np.ndarray,
    inside: np.ndarray,
    cap_m: float | None = None,
    chunk: int = 500_000,
) -> np.ndarray:
    """Distance from each point to the nearest boundary segment, negative where inside.

    With a cap, points farther than the cap are not a number, and the search stops early.
    """
    out = np.full(len(xs), np.nan, dtype=np.float64)
    for start in range(0, len(xs), chunk):
        stop = start + chunk
        points = shapely.points(xs[start:stop], ys[start:stop])
        found, distance = tree.query_nearest(
            points, max_distance=cap_m, return_distance=True, all_matches=False
        )
        out[start + found[0]] = distance
    out[inside] *= -1
    return out


@dataclass
class Mask:
    """Pixel classes of one water body at one resolution, in tile pixel coordinates."""

    resolution: int
    window: Window
    pixel_class: np.ndarray
    coverage: np.ndarray
    edge_distance: np.ndarray
    naive: np.ndarray
    counts: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)

    def selected(self) -> np.ndarray:
        return self.pixel_class > 0

    def index_lists(self) -> dict[str, np.ndarray]:
        """The same classes as row and column lists in tile coordinates, row-major order."""
        rows, cols = np.nonzero(self.pixel_class)
        return {
            "rows": (rows + self.window.row_off).astype(np.int32),
            "cols": (cols + self.window.col_off).astype(np.int32),
            "pixel_class": self.pixel_class[rows, cols],
            "coverage": self.coverage[rows, cols],
            "edge_distance": self.edge_distance[rows, cols],
        }

    def meta(self) -> dict:
        return {
            "resolution": self.resolution,
            "window": self.window.as_dict(),
            "counts": self.counts,
            "timings": self.timings,
            "parameters": self.parameters,
        }


def _trim(mask: np.ndarray, keep: np.ndarray, window: Window) -> tuple[Window, slice, slice]:
    """The window and slices that bound the pixels to keep. Empty when nothing is kept."""
    rows, cols = np.nonzero(keep)
    if len(rows) == 0:
        return Window(window.row_off, window.col_off, 0, 0), slice(0, 0), slice(0, 0)
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    return (
        Window(window.row_off + r0, window.col_off + c0, r1 - r0, c1 - c0),
        slice(r0, r1),
        slice(c0, c1),
    )


def compute_mask(
    polygon: BaseGeometry,
    grid: TileGrid,
    resolution: int,
    near_land_m: float = NEAR_LAND_M,
    tolerance: float = FRACTION_TOLERANCE,
    edge_distance_cap_m: float = EDGE_DISTANCE_CAP_M,
    block_m: float = BLOCK_M,
) -> Mask:
    """Classes, coverage, edge distance, and the naive mask for one polygon on one grid.

    The polygon is in the tile CRS. Only pixels inside the tile are classified, but every
    distance is measured to the polygon's real boundary, which can lie outside the tile. A
    tile edge is never a shoreline. The result window is the bounding box of the classified
    pixels, so it is empty when no pixel qualifies.
    """
    timings: dict[str, float] = {}
    clock = time.perf_counter()
    if resolution not in RESOLUTIONS:
        raise ValueError(f"resolution {resolution} is not one of {RESOLUTIONS}")
    margin = near_land_m + resolution
    window = window_for(
        polygon.bounds if not polygon.is_empty else (0, 0, 0, 0), grid, resolution, margin
    )
    parameters = {
        "near_land_m": near_land_m,
        "tolerance": tolerance,
        "edge_distance_cap_m": edge_distance_cap_m,
        "block_m": block_m,
        "mask_version": MASK_VERSION,
    }
    if polygon.is_empty or window.empty:
        empty = np.zeros((0, 0))
        return Mask(
            resolution,
            Window(window.row_off, window.col_off, 0, 0),
            empty.astype(np.uint8),
            empty.astype(np.float32),
            empty.astype(np.float32),
            empty.astype(bool),
            counts=empty_counts(),
            timings={"total_seconds": round(time.perf_counter() - clock, 4)},
            parameters=parameters,
        )
    transform = window.transform(grid, resolution)

    touched = _rasterize(polygon.boundary, window, transform, all_touched=True)
    candidates = _grow(touched)
    centre_in = _rasterize(polygon, window, transform, all_touched=False)
    naive = _rasterize(polygon, window, transform, all_touched=True)
    timings["rasterize_seconds"] = round(time.perf_counter() - clock, 4)

    clock = time.perf_counter()
    coverage = exact_coverage(polygon, window, transform, resolution, candidates, block_m)
    coverage[~candidates & centre_in] = 1.0
    timings["coverage_seconds"] = round(time.perf_counter() - clock, 4)

    clock = time.perf_counter()
    pixel_class = np.zeros(coverage.shape, dtype=np.uint8)
    pixel_class[coverage >= 1 - tolerance] = CLASS_CODES["interior"]
    pixel_class[(coverage > tolerance) & (coverage < 1 - tolerance)] = CLASS_CODES["shoreline"]
    dry = pixel_class == 0
    near_candidates = _rasterize(polygon.buffer(near_land_m), window, transform, True) & dry
    segments = boundary_segments(polygon)
    if len(segments) == 0:
        raise ValueError("the polygon has no boundary segments")
    tree = shapely.STRtree(segments)
    rows, cols = np.nonzero(near_candidates)
    xs = transform.c + (cols + 0.5) * resolution
    ys = transform.f - (rows + 0.5) * resolution
    near_distance = signed_distances(tree, xs, ys, np.zeros(len(xs), dtype=bool))
    near = near_distance <= near_land_m
    pixel_class[rows[near], cols[near]] = CLASS_CODES["near_land"]
    timings["near_land_seconds"] = round(time.perf_counter() - clock, 4)

    clock = time.perf_counter()
    edge_distance = np.full(coverage.shape, np.nan, dtype=np.float64)
    edge_distance[rows[near], cols[near]] = near_distance[near]
    wet_rows, wet_cols = np.nonzero((pixel_class > 0) & (pixel_class != CLASS_CODES["near_land"]))
    xs = transform.c + (wet_cols + 0.5) * resolution
    ys = transform.f - (wet_rows + 0.5) * resolution
    edge_distance[wet_rows, wet_cols] = signed_distances(
        tree, xs, ys, centre_in[wet_rows, wet_cols], cap_m=edge_distance_cap_m
    )
    timings["edge_distance_seconds"] = round(time.perf_counter() - clock, 4)

    trimmed, rs, cs = _trim(pixel_class, pixel_class > 0, window)
    counts = {name: int((pixel_class == code).sum()) for name, code in CLASS_CODES.items()}
    wet = (pixel_class == CLASS_CODES["interior"]) | (pixel_class == CLASS_CODES["shoreline"])
    naive_only = naive & ~wet
    counts["naive"] = int(naive.sum())
    counts["naive_only"] = int(naive_only.sum())
    counts["naive_only_sliver"] = int((naive_only & (coverage > 0)).sum())
    counts["naive_only_empty"] = int((naive_only & (coverage == 0)).sum())
    counts["classes_only"] = int((wet & ~naive).sum())
    counts["coverage_area_m2"] = float(coverage.sum() * resolution * resolution)
    timings["total_seconds"] = round(sum(timings.values()), 4)
    return Mask(
        resolution,
        trimmed,
        pixel_class[rs, cs],
        coverage[rs, cs].astype(np.float32),
        edge_distance[rs, cs].astype(np.float32),
        naive[rs, cs],
        counts=counts,
        timings=timings,
        parameters=parameters,
    )


def empty_counts() -> dict:
    """The count keys of a mask with no pixel, all zero."""
    names = ("naive", "naive_only", "naive_only_sliver", "naive_only_empty", "classes_only")
    return (
        {name: 0 for name in CLASS_CODES} | {name: 0 for name in names} | {"coverage_area_m2": 0.0}
    )


def naive_window(polygon: BaseGeometry, grid: TileGrid, resolution: int) -> Window:
    """The naive method's read window: the projected polygon's bounds, clipped to the tile."""
    if polygon.is_empty:
        return Window(0, 0, 0, 0)
    return window_for(polygon.bounds, grid, resolution, 0.0)


def naive_mask(polygon: BaseGeometry, grid: TileGrid, resolution: int) -> tuple[Window, np.ndarray]:
    """What clipping per scene selects: every pixel the polygon touches, no classes."""
    window = naive_window(polygon, grid, resolution)
    if window.empty:
        return window, np.zeros((0, 0), dtype=bool)
    return window, _rasterize(polygon, window, window.transform(grid, resolution), True)


def save_mask(mask: Mask, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        pixel_class=mask.pixel_class,
        coverage=mask.coverage,
        edge_distance=mask.edge_distance,
        naive=mask.naive,
        meta=np.array(json.dumps(mask.meta())),
    )


def load_mask(path: Path) -> Mask:
    with np.load(path) as saved:
        meta = json.loads(str(saved["meta"]))
        return Mask(
            meta["resolution"],
            Window(**meta["window"]),
            saved["pixel_class"],
            saved["coverage"],
            saved["edge_distance"],
            saved["naive"],
            counts=meta["counts"],
            timings=meta["timings"],
            parameters=meta["parameters"],
        )


def save_index_lists(mask: Mask, path: Path) -> dict:
    """The index-list form of a mask, with its bounding window. Returns what was written."""
    lists = mask.index_lists()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **lists, meta=np.array(json.dumps(mask.meta())))
    return {"pixels": int(len(lists["rows"])), "bytes": path.stat().st_size}


def load_index_lists(path: Path) -> tuple[dict[str, np.ndarray], dict]:
    with np.load(path) as saved:
        meta = json.loads(str(saved["meta"]))
        lists = {key: saved[key] for key in saved.files if key != "meta"}
    return lists, meta


def lists_window(lists: dict[str, np.ndarray]) -> Window:
    """The tight window that holds every listed pixel."""
    if len(lists["rows"]) == 0:
        return Window(0, 0, 0, 0)
    r0, r1 = int(lists["rows"].min()), int(lists["rows"].max()) + 1
    c0, c1 = int(lists["cols"].min()), int(lists["cols"].max()) + 1
    return Window(r0, c0, r1 - r0, c1 - c0)
