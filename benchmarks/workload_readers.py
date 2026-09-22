"""Bounded block selections and seven native-grid reader/workflow combinations."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sqlite3
import sys
import time
import zlib
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import tile_extraction as old  # noqa: E402
from rasterio.windows import Window  # noqa: E402

from s2proto import masks  # noqa: E402
from s2proto.workload_resources import LIMITS, MIB, admit  # noqa: E402

CONFIGURATIONS = [
    "A-raster",
    "A-lazy",
    "B-raster",
    "B-lazy",
    "B-lazy-control",
    "C-raster",
    "C-lazy",
]
GDAL_ENV = {
    **old.stage2.GDAL_ENV,
    "GDAL_CACHEMAX": LIMITS["gdal_cache_bytes"],
    "GDAL_HTTP_MAX_RETRY": 2,
    "GDAL_HTTP_RETRY_DELAY": 1,
    "GDAL_HTTP_CONNECTTIMEOUT": 30,
    "GDAL_HTTP_TIMEOUT": 120,
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def connect(path):
    db = sqlite3.connect(path)
    db.execute("PRAGMA cache_size=-8192")
    db.execute("PRAGMA temp_store=FILE")
    return db


@contextmanager
def gdal_log(path):
    """Stream Python GDAL messages to disk, avoiding the older in-memory log lists."""
    logger = logging.getLogger("rasterio")
    handler = logging.FileHandler(path, mode="w")
    handler.setLevel(logging.DEBUG)
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        with rasterio.Env(**GDAL_ENV):
            yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
        handler.close()


def block_window(row, col, shape, block_shape):
    height, width = shape
    bh, bw = block_shape
    return Window(col * bw, row * bh, min(bw, width - col * bw), min(bh, height - row * bh))


def selection_block(polygon, grid, resolution, window):
    """Classify a core block with a two-pixel halo, retaining the real lake boundary."""
    height, width = grid.shape(resolution)
    r0, c0 = max(0, int(window.row_off) - 2), max(0, int(window.col_off) - 2)
    r1 = min(height, int(window.row_off + window.height) + 2)
    c1 = min(width, int(window.col_off + window.width) + 2)
    pixels = (r1 - r0) * (c1 - c0)
    admit(pixels * 256 + 64 * MIB, active_arrays_bytes=pixels * 64)
    local_grid = masks.TileGrid(
        grid.epsg,
        grid.x0 + c0 * resolution,
        grid.y0 - r0 * resolution,
        (c1 - c0) * resolution // 10,
        (r1 - r0) * resolution // 10,
    )
    prepared = masks.compute_mask(polygon, local_grid, resolution)
    rows, cols = np.nonzero(prepared.pixel_class)
    rows = rows + prepared.window.row_off + r0 - int(window.row_off)
    cols = cols + prepared.window.col_off + c0 - int(window.col_off)
    valid = (rows >= 0) & (rows < window.height) & (cols >= 0) & (cols < window.width)
    classes = prepared.pixel_class[prepared.pixel_class > 0][valid]
    positions = (rows[valid] * int(window.width) + cols[valid]).astype("<u4")
    if positions.size and not np.all(positions[1:] > positions[:-1]):
        raise ValueError("duplicate or unordered selected pixels")
    return positions, classes


def pack_selection(positions, classes):
    return zlib.compress(positions.tobytes() + classes.tobytes(), level=1)


def unpack_selection(blob, count):
    raw = zlib.decompress(blob)
    if len(raw) != count * 5:
        raise ValueError("selection size mismatch")
    return np.frombuffer(raw, "<u4", count), np.frombuffer(raw, "u1", count, count * 4)


def read_headers(plan, directory):
    """Inspect source headers, checking actual CRS, grids, data types and block layout."""
    with gdal_log(Path(directory) / "headers.gdal.log"):
        for scene in plan["scenes"]:
            grid = masks.TileGrid(**scene["grid"])
            for asset in scene["assets"]:
                admit(64 * MIB)
                with rasterio.open(asset["href"]) as source:
                    resolution = asset["resolution"]
                    if (
                        source.crs.to_epsg() != grid.epsg
                        or source.transform != grid.transform(resolution)
                        or source.shape != grid.shape(resolution)
                    ):
                        raise ValueError("source header differs from declared native grid")
                    if source.count != 1 or source.nodata != asset["nodata"]:
                        raise ValueError("unexpected band count or nodata")
                    if source.dtypes[0] != asset["dtype"]:
                        raise ValueError("source data type differs from catalog")
                    block = list(source.block_shapes[0])
                    if block[0] != block[1]:
                        raise ValueError("native loader requires square internal blocks")
                    asset["block_shape"] = block
                    asset["shape"] = list(source.shape)
                    asset["selection_grid"] = digest([scene["grid"], resolution, block])[:24]
    return plan


def prepare_selections(plan, manifest, selection_path, expected_path):
    selected = connect(selection_path)
    expected = connect(expected_path)
    selected.executescript("""
        CREATE TABLE selections (
          grid TEXT,lake TEXT,br INT,bc INT,n INT,psha TEXT,classes TEXT,blob BLOB,
          PRIMARY KEY(grid,lake,br,bc));
        CREATE INDEX block_consumers ON selections(grid,br,bc,lake);
        CREATE TABLE prepared (grid TEXT,lake TEXT,PRIMARY KEY(grid,lake));
    """)
    expected.executescript("""
        CREATE TABLE expected (
          item TEXT,band TEXT,lake TEXT,br INT,bc INT,n INT,psha TEXT,classes TEXT,
          PRIMARY KEY(item,band,lake,br,bc));
        CREATE TABLE contributions (item TEXT,band TEXT,lake TEXT,n INT,
          PRIMARY KEY(item,band,lake));
    """)
    by_id = {lake["id"]: lake for lake in manifest["lakes"]}
    for scene in plan["scenes"]:
        grid = masks.TileGrid(**scene["grid"])
        for asset in scene["assets"]:
            gid, resolution = asset["selection_grid"], asset["resolution"]
            for lid in scene["members"]:
                if not selected.execute(
                    "SELECT 1 FROM prepared WHERE grid=? AND lake=?", (gid, lid)
                ).fetchone():
                    path = Path(by_id[lid]["path"])
                    admit(path.stat().st_size * 40 + 64 * MIB)
                    raw = path.read_bytes()
                    if hashlib.sha256(raw).hexdigest() != by_id[lid]["file_sha256"]:
                        raise ValueError("frozen lake geometry changed before preparation")
                    lake = json.loads(raw)
                    del raw
                    polygon = masks.project(lake["geometry"], grid.epsg)
                    candidate = masks.window_for(
                        polygon.bounds, grid, resolution, masks.NEAR_LAND_M + resolution
                    )
                    bh, bw = asset["block_shape"]
                    if not candidate.empty:
                        for br in range(
                            candidate.row_off // bh,
                            math.ceil((candidate.row_off + candidate.height) / bh),
                        ):
                            for bc in range(
                                candidate.col_off // bw,
                                math.ceil((candidate.col_off + candidate.width) / bw),
                            ):
                                window = block_window(br, bc, asset["shape"], asset["block_shape"])
                                # Skip distant blocks without allocating any dense mask.
                                bounds = rasterio.windows.bounds(window, grid.transform(resolution))
                                from shapely.geometry import box

                                if polygon.distance(box(*bounds)) > masks.NEAR_LAND_M + resolution:
                                    continue
                                positions, classes = selection_block(
                                    polygon, grid, resolution, window
                                )
                                if not positions.size:
                                    continue
                                count = len(positions)
                                psha = hashlib.sha256(
                                    positions.tobytes() + classes.tobytes()
                                ).hexdigest()
                                counts = json.dumps([int((classes == i).sum()) for i in (1, 2, 3)])
                                selected.execute(
                                    "INSERT INTO selections VALUES (?,?,?,?,?,?,?,?)",
                                    (
                                        gid,
                                        lid,
                                        br,
                                        bc,
                                        count,
                                        psha,
                                        counts,
                                        pack_selection(positions, classes),
                                    ),
                                )
                    selected.execute("INSERT INTO prepared VALUES (?,?)", (gid, lid))
                    selected.commit()
                    del polygon, lake
                count = 0
                for row in selected.execute(
                    "SELECT br,bc,n,psha,classes FROM selections WHERE grid=? AND lake=?",
                    (gid, lid),
                ):
                    expected.execute(
                        "INSERT INTO expected VALUES (?,?,?,?,?,?,?,?)",
                        (scene["item"]["id"], asset["key"], lid, *row),
                    )
                    count += row[2]
                expected.execute(
                    "INSERT INTO contributions VALUES (?,?,?,?)",
                    (scene["item"]["id"], asset["key"], lid, count),
                )
            expected.commit()
        print(f"prepared {scene['item']['id']} ({len(scene['members'])} lakes)", flush=True)
    summary = {
        "expected_block_contributions": expected.execute(
            "SELECT COUNT(*) FROM expected"
        ).fetchone()[0],
        "expected_lake_band_contributions": expected.execute(
            "SELECT COUNT(*) FROM contributions"
        ).fetchone()[0],
        "selected_pixel_entries": expected.execute("SELECT SUM(n) FROM expected").fetchone()[0],
        "block_coverage": [],
        "logical_output_bytes": 0,
        "logical_output_model": "uint32 native row, uint32 column, uint8 class, raw band value",
    }
    for scene in plan["scenes"]:
        for asset in scene["assets"]:
            distinct = expected.execute(
                "SELECT COUNT(*) FROM (SELECT DISTINCT br,bc FROM expected "
                "WHERE item=? AND band=?)",
                (scene["item"]["id"], asset["key"]),
            ).fetchone()[0]
            total = math.prod(
                math.ceil(n / b) for n, b in zip(asset["shape"], asset["block_shape"], strict=True)
            )
            summary["block_coverage"].append(
                {
                    "item": scene["item"]["id"],
                    "band": asset["key"],
                    "resolution": asset["resolution"],
                    "distinct_blocks": distinct,
                    "total_blocks": total,
                    "fraction": distinct / total,
                }
            )
            pixels = expected.execute(
                "SELECT COALESCE(SUM(n),0) FROM expected WHERE item=? AND band=?",
                (scene["item"]["id"], asset["key"]),
            ).fetchone()[0]
            summary["logical_output_bytes"] += pixels * (9 + np.dtype(asset["dtype"]).itemsize)
    selected.close()
    expected.close()
    return summary


def native_array(scene, asset, chunk):
    import pystac
    from odc.geo.geobox import GeoBox

    grid = masks.TileGrid(**scene["grid"])
    resolution = asset["resolution"]
    geobox = GeoBox(grid.shape(resolution), grid.transform(resolution), f"EPSG:{grid.epsg}")
    # The complete item and absolute asset URLs are already frozen. Catalog links
    # otherwise let PySTAC serialization resolve a live root or collection.
    item = pystac.Item.from_dict({**scene["item"], "links": []})
    dataset = old.load_native_item([item], [asset["key"]], geobox, grid, chunk)
    if dataset.odc.geobox != geobox:
        raise ValueError("lazy loader changed the native grid")
    graph = dataset[asset["key"]].isel(time=0).data
    expected_chunks = tuple(
        (chunk,) * (size // chunk) + ((size % chunk,) if size % chunk else ())
        for size in grid.shape(resolution)
    )
    if graph.chunks != expected_chunks:
        raise ValueError(f"lazy chunk grid differs: {graph.chunks} != {expected_chunks}")
    return graph


def subarray(array, window):
    r, c, h, w = map(int, (window.row_off, window.col_off, window.height, window.width))
    return array[r : r + h, c : c + w]


def allocation_for(shape, dtype, *, whole=False):
    """Whole lazy compute can simultaneously hold chunks, assembled output, and scratch."""
    size = math.prod(shape) * np.dtype(dtype).itemsize
    scratch = size * (3 if whole else 6) + 64 * MIB
    admit(scratch, active_arrays_bytes=size + (16 * MIB if whole else size))
    return size


class Extractor:
    def __init__(self, plan, selections, output, configuration):
        self.plan = plan
        self.selected = connect(selections)
        self.selected.execute("CREATE TEMP TABLE wanted_lakes (lake TEXT PRIMARY KEY)")
        self.output = connect(output)
        self.output.execute("PRAGMA synchronous=NORMAL")
        self.output.executescript("""
            CREATE TABLE actual (
              item TEXT,band TEXT,lake TEXT,br INT,bc INT,n INT,psha TEXT,classes TEXT,
              vsha TEXT,zeros INT,PRIMARY KEY(item,band,lake,br,bc));
            CREATE TABLE completed (item TEXT,band TEXT,lake TEXT,
              PRIMARY KEY(item,band,lake));
        """)
        self.configuration = configuration
        self.timings = dict.fromkeys(
            [
                "build_seconds",
                "read_seconds",
                "extract_seconds",
                "validation_seconds",
                "selection_seconds",
                "checkpoint_seconds",
            ],
            0.0,
        )
        self.read_units = 0
        self.computes = 0
        self.pending_records = 0
        self.checkpoints = 0

    def checkpoint(self, *, force=False):
        # Use the same record-count schedule for every workflow. No per-lake fsync bias.
        if self.pending_records >= 256 or (force and self.pending_records):
            started = time.perf_counter()
            self.output.commit()
            self.timings["checkpoint_seconds"] += time.perf_counter() - started
            self.pending_records = 0
            self.checkpoints += 1

    def rows(self, asset, *, lake=None, block=None):
        query = "SELECT lake,br,bc,n,psha,classes,blob FROM selections WHERE grid=?"
        params = [asset["selection_grid"]]
        if lake is not None:
            query += " AND lake=?"
            params.append(lake)
        if block is not None:
            query += " AND br=? AND bc=?"
            params.extend(block)
        return self.selected.execute(query + " ORDER BY lake,br,bc", params)

    def consume(self, scene, asset, record, array):
        lid, br, bc, count, psha, counts, blob = record
        started = time.perf_counter()
        positions, classes = unpack_selection(blob, count)
        self.timings["selection_seconds"] += time.perf_counter() - started
        started = time.perf_counter()
        values = array.reshape(-1)[positions]
        if np.issubdtype(values.dtype, np.floating):
            values = np.where(np.isnan(values), asset["nodata"], values)
        raw = values.astype(np.dtype(asset["dtype"]).newbyteorder("<"))
        if not np.array_equal(raw, values):
            raise ValueError("lazy output cannot be represented as stored raw integers")
        zeros = int((raw == asset["nodata"]).sum())
        self.timings["extract_seconds"] += time.perf_counter() - started
        started = time.perf_counter()
        actual_psha = hashlib.sha256(positions.tobytes() + classes.tobytes()).hexdigest()
        if actual_psha != psha or (count > 1 and not np.all(positions[1:] > positions[:-1])):
            raise ValueError("selection identity changed or duplicated pixels")
        vsha = hashlib.sha256(raw.tobytes()).hexdigest()
        self.output.execute(
            "INSERT INTO actual VALUES (?,?,?,?,?,?,?,?,?,?)",
            (scene["item"]["id"], asset["key"], lid, br, bc, count, psha, counts, vsha, zeros),
        )
        self.timings["validation_seconds"] += time.perf_counter() - started
        self.pending_records += 1
        self.checkpoint()

    def finish(self, scene, asset, members):
        for lid in members:
            self.output.execute(
                "INSERT INTO completed VALUES (?,?,?)", (scene["item"]["id"], asset["key"], lid)
            )
            self.pending_records += 1
            self.checkpoint()

    def raster_asset(self, scene, asset, members, whole=False):
        started = time.perf_counter()
        with rasterio.open(asset["href"]) as source:
            self.timings["build_seconds"] += time.perf_counter() - started
            if whole:
                allocation_for(asset["shape"], asset["dtype"], whole=True)
                started = time.perf_counter()
                entire = source.read(1)
                self.timings["read_seconds"] += time.perf_counter() - started
                self.read_units += 1
            for lid in members:
                for record in self.rows(asset, lake=lid):
                    window = block_window(
                        record[1], record[2], asset["shape"], asset["block_shape"]
                    )
                    if whole:
                        part = subarray(entire, window)
                    else:
                        allocation_for((window.height, window.width), asset["dtype"])
                        started = time.perf_counter()
                        part = source.read(1, window=window)
                        self.timings["read_seconds"] += time.perf_counter() - started
                        self.read_units += 1
                    self.consume(scene, asset, record, part)
                    del part
                self.finish(scene, asset, [lid])
            if whole:
                del entire

    def lazy_asset(self, scene, asset, members, *, whole=False, control=False):
        import dask

        started = time.perf_counter()
        chunk = 2048 if control else asset["block_shape"][0]
        graph = native_array(scene, asset, chunk)
        self.timings["build_seconds"] += time.perf_counter() - started
        with dask.config.set(scheduler="threads", num_workers=LIMITS["threads"]):
            if whole:
                allocation_for(asset["shape"], graph.dtype, whole=True)
                started = time.perf_counter()
                entire = graph.compute()
                self.computes += 1
                self.read_units += math.prod(map(len, graph.chunks))
                self.timings["read_seconds"] += time.perf_counter() - started
                for lid in members:
                    for record in self.rows(asset, lake=lid):
                        window = block_window(
                            record[1], record[2], asset["shape"], asset["block_shape"]
                        )
                        self.consume(scene, asset, record, subarray(entire, window))
                    self.finish(scene, asset, [lid])
                del entire
            elif control:
                self.lazy_control(scene, asset, members, graph)
            else:
                # Memberships select source blocks before graph scheduling. At most two
                # decoded blocks are held, and all consumers finish before the next batch.
                self.selected.execute("DELETE FROM wanted_lakes")
                self.selected.executemany(
                    "INSERT INTO wanted_lakes VALUES (?)", ((lid,) for lid in members)
                )
                blocks = self.selected.execute(
                    "SELECT DISTINCT br,bc FROM selections JOIN wanted_lakes USING(lake) "
                    "WHERE grid=? ORDER BY br,bc",
                    (asset["selection_grid"],),
                )
                member_set = set(members)
                while batch := blocks.fetchmany(LIMITS["threads"]):
                    arrays = [graph.blocks[br, bc] for br, bc in batch]
                    planned = sum(math.prod(a.shape) * a.dtype.itemsize for a in arrays)
                    admit(planned * 6 + 64 * MIB, active_arrays_bytes=planned * 2)
                    started = time.perf_counter()
                    decoded = dask.compute(*arrays)
                    self.timings["read_seconds"] += time.perf_counter() - started
                    self.computes += 1
                    self.read_units += len(batch)
                    for block, array in zip(batch, decoded, strict=True):
                        for record in self.rows(asset, block=block):
                            if record[0] in member_set:
                                self.consume(scene, asset, record, array)
                    del decoded, arrays, array
                self.finish(scene, asset, members)

    def lazy_control(self, scene, asset, members, graph):
        """Old shared graph, large chunks, and one compute for each lake window."""
        for lid in members:
            bounds = self.selected.execute(
                "SELECT MIN(br),MIN(bc),MAX(br),MAX(bc) FROM selections WHERE grid=? AND lake=?",
                (asset["selection_grid"], lid),
            ).fetchone()
            if bounds[0] is None:
                self.finish(scene, asset, [lid])
                continue
            bh, bw = asset["block_shape"]
            r0, c0 = bounds[0] * bh, bounds[1] * bw
            r1, c1 = (
                min((bounds[2] + 1) * bh, graph.shape[0]),
                min((bounds[3] + 1) * bw, graph.shape[1]),
            )
            # The control still computes separately for each lake. Window edges follow
            # the selected pixels, matching the historical per-lake graph slicing.
            minr, minc, maxr, maxc = r1, c1, r0, c0
            for record in self.rows(asset, lake=lid):
                window = block_window(record[1], record[2], asset["shape"], asset["block_shape"])
                positions, _ = unpack_selection(record[-1], record[3])
                rr, cc = np.divmod(positions, int(window.width))
                minr, minc = (
                    min(minr, int(rr.min()) + int(window.row_off)),
                    min(minc, int(cc.min()) + int(window.col_off)),
                )
                maxr, maxc = (
                    max(maxr, int(rr.max()) + int(window.row_off) + 1),
                    max(maxc, int(cc.max()) + int(window.col_off) + 1),
                )
            padded_shape = (
                min(graph.shape[0], math.ceil(maxr / 2048) * 2048) - (minr // 2048) * 2048,
                min(graph.shape[1], math.ceil(maxc / 2048) * 2048) - (minc // 2048) * 2048,
            )
            allocation_for(padded_shape, graph.dtype)
            started = time.perf_counter()
            array = graph[minr:maxr, minc:maxc].compute()
            self.timings["read_seconds"] += time.perf_counter() - started
            self.computes += 1
            self.read_units += math.ceil((maxr - (minr // 2048) * 2048) / 2048) * math.ceil(
                (maxc - (minc // 2048) * 2048) / 2048
            )
            for record in self.rows(asset, lake=lid):
                window = block_window(record[1], record[2], asset["shape"], asset["block_shape"])
                # Only selected positions are needed. Use a small block container to
                # preserve the same canonical block signature at clipped window edges.
                part = np.empty((int(window.height), int(window.width)), dtype=array.dtype)
                positions, _ = unpack_selection(record[-1], record[3])
                rr, cc = np.divmod(positions, int(window.width))
                part.flat[positions] = array[
                    rr + int(window.row_off) - minr, cc + int(window.col_off) - minc
                ]
                self.consume(scene, asset, record, part)
                del part
            del array
            self.finish(scene, asset, [lid])

    def run(self):
        workflow, reader = self.configuration.split("-", 1)
        if workflow == "A":
            for lid in sorted({lid for scene in self.plan["scenes"] for lid in scene["members"]}):
                for scene in self.plan["scenes"]:
                    if lid not in scene["members"]:
                        continue
                    for asset in scene["assets"]:
                        if reader == "raster":
                            self.raster_asset(scene, asset, [lid])
                        else:
                            self.lazy_asset(scene, asset, [lid])
                print(f"completed lake {lid}", flush=True)
        else:
            for scene in self.plan["scenes"]:
                for asset in scene["assets"]:
                    if reader == "raster":
                        self.raster_asset(scene, asset, scene["members"], whole=workflow == "C")
                    else:
                        self.lazy_asset(
                            scene,
                            asset,
                            scene["members"],
                            whole=workflow == "C",
                            control=reader == "lazy-control",
                        )
                print(f"completed product {scene['item']['id']}", flush=True)
        self.checkpoint(force=True)
        self.selected.close()
        self.output.close()
        return {
            "timings": self.timings,
            "read_units": self.read_units,
            "computes": self.computes,
            "read_and_extract_seconds": self.timings["read_seconds"]
            + self.timings["extract_seconds"],
            "output_database": {
                "synchronous": "NORMAL",
                "checkpoint_records": 256,
                "checkpoints": self.checkpoints,
            },
        }


def validate(expected_path, actual_path, reference_path=None):
    db = connect(actual_path)
    db.execute("ATTACH DATABASE ? AS expected_db", (str(expected_path),))
    keys = "item,band,lake,br,bc,n,psha,classes"
    missing = db.execute(
        f"SELECT COUNT(*) FROM (SELECT {keys} FROM expected_db.expected "
        f"EXCEPT SELECT {keys} FROM actual)"
    ).fetchone()[0]
    extra = db.execute(
        f"SELECT COUNT(*) FROM (SELECT {keys} FROM actual "
        f"EXCEPT SELECT {keys} FROM expected_db.expected)"
    ).fetchone()[0]
    contributions_missing = db.execute(
        "SELECT COUNT(*) FROM (SELECT item,band,lake FROM expected_db.contributions "
        "EXCEPT SELECT * FROM completed)"
    ).fetchone()[0]
    contributions_extra = db.execute(
        "SELECT COUNT(*) FROM (SELECT * FROM completed EXCEPT "
        "SELECT item,band,lake FROM expected_db.contributions)"
    ).fetchone()[0]
    differences = None
    if reference_path:
        db.execute("ATTACH DATABASE ? AS reference_db", (str(reference_path),))
        differences = db.execute(
            "SELECT COUNT(*) FROM (SELECT * FROM actual EXCEPT SELECT * FROM reference_db.actual)"
        ).fetchone()[0]
        differences += db.execute(
            "SELECT COUNT(*) FROM (SELECT * FROM reference_db.actual EXCEPT SELECT * FROM actual)"
        ).fetchone()[0]
    signature = hashlib.sha256()
    for record in db.execute("SELECT * FROM actual ORDER BY item,band,lake,br,bc"):
        signature.update(json.dumps(record).encode() + b"\n")
    for record in db.execute("SELECT * FROM completed ORDER BY item,band,lake"):
        signature.update(json.dumps(record).encode() + b"\n")
    count, pixels = db.execute("SELECT COUNT(*),COALESCE(SUM(n),0) FROM actual").fetchone()
    db.close()
    return {
        "complete": not (missing or extra or contributions_missing or contributions_extra),
        "missing_blocks": missing,
        "unexpected_blocks": extra,
        "missing_contributions": contributions_missing,
        "unexpected_contributions": contributions_extra,
        "value_differences": differences,
        "ordered_signature": signature.hexdigest(),
        "completed_blocks": count,
        "selected_pixel_entries": pixels,
    }
