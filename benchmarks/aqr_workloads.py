"""Probe T6: the access tests replayed on the USGS ACOLITE aquatic reflectance product.

Runs only when the user invokes it. Unsigned requests, no credentials. Stages 2 to 4 and readers
B1 and B3 of the larger workloads run their own unchanged code. Only the source changes.

Each Collection 1 candidate the earlier selection rules see is replaced by the primary product
of the same datastrip, src/s2proto/aqr_pairing.py, or dropped when the bucket lacks that product.
The rules then choose as before among what remains. The product's B04, B08, B11, B01, and
l2_flags stand in for red, nir, swir16, coastal, and the scene classification, all at 20 m.
Decision 0009 keeps the two options standalone. The pairing only keeps the cohorts the same.

    uv run python benchmarks/aqr_workloads.py                     # print the plan, contact nothing
    uv run python benchmarks/aqr_workloads.py --run RUN_DIR      # every part, resumable by part
    uv run python benchmarks/aqr_workloads.py --run RUN_DIR --parts stage2
    uv run python benchmarks/aqr_workloads.py --collate RUN_DIR  # write the result, no network

Probe T6 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md. Probe T7, the
overlap comparison, is not part of this script.
"""

from __future__ import annotations

import argparse
import ast
import calendar
import copy
import fcntl
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks"), str(ROOT / "tools")]

import aqr_validity as t4  # noqa: E402

from s2proto import aqr, aqr_pairing, harness, masks  # noqa: E402
from s2proto.workload_resources import (  # noqa: E402
    LIMITS,
    clean_workspace,
    create_workspace,
    supervise,
    write_json,
)

# The earlier scripts load on demand, so that each worker process imports what its own
# script imported before. load() binds these names.
stage2 = stage3 = stage4 = lazy = None
ORIGINAL: dict = {}

PARTS = ("stage2", "stage3", "stage4", "workloads")
LAYERS = tuple(aqr_pairing.T6_LAYERS.values())
RESULT = ROOT / "benchmarks/results/aqr-workloads.json"
REFERENCES = {
    "stage2": ROOT / "benchmarks/results/lake-extraction.json",
    "stage3": ROOT / "benchmarks/results/tile-extraction.json",
    "stage4": ROOT / "benchmarks/results/cross-tile-extraction.json",
    "workloads": ROOT / "benchmarks/results/lazy-reader-workloads.json",
}
STAGE4_CATALOG = ROOT / "data/cross-tile-extraction/full-plan.catalog.json"
"""The saved Collection 1 catalog stage 4 froze, matching catalog_sha256 in its result."""
STAGE4_REGIONS = ["lanier", "okeechobee"]
WORKLOAD_REFERENCE = ROOT / "data/lazy-reader-workloads/2026-09-21-sleep-rerun"
"""The run directory of the published larger-workload result. Its catalog and manifest."""
CONFIGURATIONS = {"dispersed": ["B-raster", "B-lazy"], "florida": ["B-lazy", "B-raster"]}
"""B1 and B3, in the order each cohort ran them in the reference plan."""
OWN_SOURCES = [
    "benchmarks/aqr_workloads.py",
    "benchmarks/aqr_validity.py",
    "src/s2proto/aqr_pairing.py",
    "src/s2proto/aqr.py",
]
LIMITATIONS = [
    "The cohorts are the earlier lakes, restricted to acquisitions the primary product holds. "
    "Where a lake's earlier acquisition is missing, the unchanged rules choose another one. "
    "Tile-dates therefore differ in part from the Level-2A reference. Each part reports how many "
    "match.",
    "Selection ranks candidates by the paired Collection 1 item's metadata: footprint, cloud "
    "cover, datastrip, and creation time. The primary product has no catalog that states them.",
    "Five layers per product, the earlier band set's counterparts. The primary product holds 13 "
    "raster layers. A store of every layer reads more files per product.",
    "Laptop over the internet, outside us-west-2, assumption A25. Times are not AWS estimates.",
    "Requests and bytes come from GDAL's debug log of requested ranges, not metered transfer.",
    "One run per part on one day. Provider, operating-system, and network caches are not "
    "controlled. Timing repetitions are those of each earlier script.",
    "Intermediate stage files under data/ come from the unchanged scripts and keep their "
    "Collection 1 wording in places. This result's endpoints block is authoritative.",
]


# ---------------------------------------------------------------- source substitution

HEADER_CHECKS: list[dict] = []


def load(*, workloads: bool = False) -> None:
    """Import the earlier scripts and keep their original functions."""
    global stage2, stage3, stage4, lazy
    stage4 = importlib.import_module("cross_tile_extraction")
    stage3, stage2 = stage4.stage3, stage4.stage2
    if workloads:
        lazy = importlib.import_module("lazy_reader_workloads")
    if not ORIGINAL:
        ORIGINAL.update(
            search_region=stage2.search_region,
            resolve_assets=stage2.resolve_assets,
            native_assets=stage4.native_assets,
            stage3_run=stage3.run_in_subprocess,
        )


def check_headers(item: dict, assets: list[dict], grid: masks.TileGrid) -> None:
    """Every chosen product layer must match its declared grid, data type, and no-data."""
    import rasterio

    env = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif"}
    with rasterio.Env(**env):
        for asset in assets:
            with rasterio.open(asset["href"]) as src:
                problems = []
                if src.crs.to_epsg() != grid.epsg:
                    problems.append("crs")
                if src.transform != grid.transform(asset["resolution"]):
                    problems.append("transform")
                if list(src.shape) != list(grid.shape(asset["resolution"])):
                    problems.append("shape")
                if src.dtypes[0] != asset["dtype"] or src.nodata != asset["nodata"]:
                    problems.append("dtype or nodata")
                if src.count != 1:
                    problems.append("band count")
                HEADER_CHECKS.append(
                    {"item": item["id"], "key": asset["key"], "problems": problems}
                )
                if problems:
                    raise ValueError(f"{item['id']} {asset['key']}: header differs: {problems}")


def resolve_assets(item, keys, grid):
    resolved = ORIGINAL["resolve_assets"](item, keys, grid)
    if item.get("collection") == aqr_pairing.COLLECTION:
        check_headers(item, resolved["assets"], grid)
    return resolved


def native_assets(item, bands):
    """Stage 4 admits only Collection 1 items. A stand-in replaces one on purpose."""
    if item.get("collection") == aqr_pairing.COLLECTION:
        grid, assets = ORIGINAL["native_assets"]({**item, "collection": stage2.COLLECTION}, bands)
        check_headers(item, assets, grid)
        return grid, assets
    return ORIGINAL["native_assets"](item, bands)


def stage2_run(task: str, spec: dict, spec_path: Path) -> dict:
    """Stage 2's subprocess runner with this script as the worker entry. Otherwise the same."""
    spec_path.write_text(json.dumps(spec))
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), f"--{task}-worker", str(spec_path)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **stage2.GDAL_ENV, "AQR_T6_MODULE": "lake_extraction"},
    )
    if completed.returncode != 0:
        keys = ("water_body_id", "region", "size_label", "method", "repetition")
        return {**{k: spec[k] for k in keys if k in spec}, "error": completed.stderr[-3000:]}
    return json.loads(completed.stdout.strip().splitlines()[-1])


def stage3_run(task, spec, spec_path, memory=None, *, script=None):
    """Stage 3's runner with this script as the worker entry, for the module that asked."""
    module = "tile_extraction" if script is None else Path(script).stem
    previous = os.environ.get("AQR_T6_MODULE")
    os.environ["AQR_T6_MODULE"] = module
    try:
        return ORIGINAL["stage3_run"](task, spec, spec_path, memory, script=SCRIPT)
    finally:
        if previous is None:
            os.environ.pop("AQR_T6_MODULE", None)
        else:
            os.environ["AQR_T6_MODULE"] = previous


def install_grid() -> None:
    """The primary product has no 10 m layer. Read the tile grid from a 20 m layer too."""
    masks.TileGrid.from_item = staticmethod(aqr_pairing.grid_20m)


def install(pairer: Pairer | None = None) -> None:
    """Substitute the source in the earlier scripts. Their methods stay as written."""
    load()
    install_grid()
    stage2.BUCKET = aqr.BUCKET
    stage2.resolve_assets = resolve_assets
    stage4.native_assets = native_assets
    stage2.run_in_subprocess = stage2_run
    stage3.run_in_subprocess = stage3_run
    if pairer is not None:

        def search_region(client, bbox, window):
            return pairer.stand_ins(ORIGINAL["search_region"](client, bbox, window))

        stage2.search_region = search_region


# ---------------------------------------------------------------- pairing


def month_range(month: str) -> tuple[str, str]:
    year, number = map(int, month.split("-"))
    return f"{month}-01", f"{month}-{calendar.monthrange(year, number)[1]:02d}"


def search_month(client, collection: str, tile: str, month: str) -> list[dict]:
    start, end = month_range(month)
    body = {
        "collections": [collection],
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "limit": 100,
    }
    items, seen = [], set()
    while True:
        key = json.dumps(body, sort_keys=True)
        if key in seen:
            raise ValueError("catalog pagination repeated")
        seen.add(key)
        page = client.post_json(f"{t4.ES_ROOT}/search", body, f"{collection} {tile} {month}")
        items.extend(page.get("features", []))
        link = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not link:
            return items
        if not link.get("body"):
            raise ValueError("unsupported catalog pagination")
        body = {**body, **link["body"]} if link.get("merge") else link["body"]


class Pairer:
    """Stand-ins for Collection 1 items whose datastrip the primary product holds."""

    def __init__(self, directory: Path, pause: float = 0.1):
        self.directory = Path(directory)
        self.client = harness.Client(pause=pause)
        self.listings: dict[tuple, dict] = {}
        self.l1c: dict[tuple, list] = {}
        self.records: dict[str, dict] = {}
        self.items: dict[str, dict | None] = {}

    def products(self, tile: str, month: str) -> list[dict]:
        out = []
        for platform in aqr.PLATFORMS:
            key = (tile, platform, month)
            if key not in self.listings:
                prefix = f"{aqr.VERSION_PREFIX}T{tile}/{platform}_MSIAQR_{month.replace('-', '')}"
                objects = t4.list_all(self.client, prefix, f"products {tile} {platform} {month}")
                write_json(self.directory / "listings" / f"{tile}-{platform}-{month}.json", objects)
                self.listings[key] = aqr.group_scenes(objects)[0]
            out.extend(self.listings[key].values())
        return out

    def l1c_items(self, tile: str, month: str) -> list[dict]:
        if (tile, month) not in self.l1c:
            items = search_month(self.client, "sentinel-2-l1c", tile, month)
            write_json(self.directory / "l1c" / f"{tile}-{month}.json", items)
            self.l1c[(tile, month)] = items
        return self.l1c[(tile, month)]

    def stand_ins(self, items: list[dict]) -> list[dict]:
        groups: dict[tuple, list] = {}
        for item in items:
            props = item["properties"]
            tile = aqr_pairing.normalize_tile(props.get("grid:code"))
            groups.setdefault((tile, props["datetime"][:7]), []).append(item)
        for (tile, month), group in sorted(groups.items()):
            if all(item["id"] in self.items for item in group):
                continue
            chosen, records = aqr_pairing.products_by_item(
                self.products(tile, month), self.l1c_items(tile, month), group, LAYERS
            )
            for record in records:
                self.records[record["product"]] = record
            for item in group:
                pick = chosen.get(item["id"])
                self.items[item["id"]] = (
                    aqr_pairing.stand_in_item(item, pick["scene"]) if pick else None
                )
        return [self.items[i["id"]] for i in items if self.items.get(i["id"])]

    def summary(self) -> dict:
        return {
            "c1_items_seen": len(self.items),
            "c1_items_with_product": sum(1 for v in self.items.values() if v),
            "product_status": aqr.counter_dict(r["status"] for r in self.records.values()),
            "listings": len(self.listings),
            "l1c_searches": len(self.l1c),
            "requests": aqr.counter_dict(f"{e['host']} {e['method']}" for e in self.client.log),
        }

    def save(self) -> None:
        write_json(
            self.directory / "pairing.json",
            {
                "summary": self.summary(),
                "records": sorted(self.records.values(), key=lambda r: r["product"]),
                "items": {k: (v["id"] if v else None) for k, v in sorted(self.items.items())},
                "request_log": self.client.log,
            },
        )


# ---------------------------------------------------------------- stages 2 to 4


def run_stage(run_dir: Path, part: str) -> None:
    directory = run_dir / part
    output = run_dir / f"{part}.json"
    if output.exists():
        print(f"{part}: {output} exists, skipped", flush=True)
        return
    directory.mkdir(parents=True, exist_ok=True)
    HEADER_CHECKS.clear()
    pairer = Pairer(directory / "pairing")
    install(pairer)
    try:
        if part == "stage2":
            os.environ["AQR_T6_MODULE"] = "lake_extraction"
            code = stage2.main(["--output", str(output), "--raw-dir", str(directory)])
        elif part == "stage3":
            os.environ["AQR_T6_MODULE"] = "tile_extraction"
            baseline = run_dir / "stage2.json"
            code = stage3.main(
                ["--output", str(output), "--raw-dir", str(directory), "--baseline", str(baseline)]
            )
        else:
            os.environ["AQR_T6_MODULE"] = "cross_tile_extraction"
            catalogs = json.loads(STAGE4_CATALOG.read_text())
            stand_ins = {region: pairer.stand_ins(items) for region, items in catalogs.items()}
            catalog_path = directory / "stand-in-catalog.json"
            write_json(catalog_path, stand_ins)
            plan = directory / "plan.json"
            if not plan.exists():
                code = stage4.main(
                    [
                        "--catalog",
                        str(catalog_path),
                        "--plan",
                        str(plan),
                        "--raw-dir",
                        str(directory),
                        "--regions",
                        *STAGE4_REGIONS,
                    ]
                )
                if code:
                    raise RuntimeError(f"stage 4 plan not ready, exit {code}")
            code = stage4.main(
                ["--run-plan", str(plan), "--raw-dir", str(directory), "--output", str(output)]
            )
    finally:
        pairer.save()
        write_json(directory / "header-checks.json", HEADER_CHECKS)
    print(f"{part}: exit {code}", flush=True)


# ---------------------------------------------------------------- larger workloads


def own_digests() -> dict:
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in OWN_SOURCES}


def restricted_snapshot(snapshot: dict, keep: set[str]) -> dict:
    out = copy.deepcopy(snapshot)
    out["items"] = {k: v for k, v in snapshot["items"].items() if k in keep}
    for region in out["regions"].values():
        region["items"] = [i for i in region["items"] if i in keep]
    for group in out["groups"]:
        group["items"] = [i for i in group["items"] if i in keep]
    out["restricted_to_primary_product"] = True
    return out


def pair_cohort(directory: Path, cohort: str) -> dict:
    reference = WORKLOAD_REFERENCE / cohort
    pairer = Pairer(directory / "pairing")
    snapshot = json.loads((reference / "catalog.json").read_text())
    items = [json.loads(Path(p).read_text()) for p in snapshot["items"].values()]
    stand_ins = {item["properties"]["aqr:paired_item"]: item for item in pairer.stand_ins(items)}
    pairer.save()
    write_json(directory / "stand-ins.json", stand_ins)
    write_json(directory / "catalog.json", restricted_snapshot(snapshot, set(stand_ins)))
    shutil.copyfile(reference / "manifest.json", directory / "manifest.json")
    return {"c1_items": len(items), "with_product": len(stand_ins), **pairer.summary()}


def stand_in_plan(plan: dict, stand_ins: dict, cohort: str, dropped: list) -> dict:
    plan = copy.deepcopy(plan)
    for scene in plan["scenes"]:
        c1_id = scene["item"]["id"]
        item = stand_ins[c1_id]
        if aqr_pairing.grid_20m(item) != masks.TileGrid(**scene["grid"]):
            raise ValueError(f"stand-in grid differs for {c1_id}")
        scene["paired_item"] = c1_id
        scene["item"] = item
        scene["assets"] = [
            {
                "key": key,
                "href": item["assets"][key]["href"],
                "resolution": aqr_pairing.RESOLUTION,
                "nodata": aqr_pairing.NODATA,
                "dtype": item["assets"][key]["raster:bands"][0]["data_type"],
                "file_size": item["assets"][key]["file:size"],
            }
            for key in lazy.BANDS
        ]
    plan["order"] = CONFIGURATIONS[cohort]
    plan["aqr"] = {
        "layers": aqr_pairing.T6_LAYERS,
        "source_digests": own_digests(),
        "dropped_lakes": dropped,
        "reference": str(WORKLOAD_REFERENCE / cohort),
    }
    return plan


def freeze_phase(spec: dict) -> dict:
    """The unchanged freeze on the restricted catalog, then the stand-in assets.

    Lakes left with no candidate product, or with no complete one, are dropped and recorded.
    """
    directory = Path(spec["directory"])
    snapshot = json.loads((directory / "catalog.json").read_text())
    manifest = json.loads((directory / "manifest.json").read_text())
    dropped: list[str] = []

    def drop(lakes: set[str], reason: str) -> None:
        dropped.extend(sorted(lakes))
        manifest["lakes"] = [lake for lake in manifest["lakes"] if lake["id"] not in lakes]
        manifest["aqr_dropped_lakes"] = sorted(dropped)
        for group in snapshot["groups"]:
            group["lakes"] = [lake for lake in group["lakes"] if lake not in lakes]
        for region in snapshot["regions"].values():
            region["lakes"] = [lake for lake in region["lakes"] if lake not in lakes]
        snapshot["groups"] = [g for g in snapshot["groups"] if g["lakes"]]
        write_json(directory / "manifest.json", manifest)
        write_json(directory / "catalog.json", snapshot)
        print(f"dropped lakes, {reason}: {sorted(lakes)}", flush=True)

    # A group whose candidates all lack a product leaves its lakes with no candidate at all.
    empty = {lake for g in snapshot["groups"] if not g["items"] for lake in g["lakes"]}
    if empty:
        drop(empty, "no candidate product")
    for _ in range(5):
        try:
            summary = lazy.freeze(manifest, snapshot, directory)
            break
        except ValueError as exc:
            text = str(exc)
            if "no complete acquisition for lakes:" not in text:
                raise
            drop(set(ast.literal_eval(text.split("lakes:", 1)[1].strip())), "no complete product")
    else:
        raise RuntimeError("freeze kept dropping lakes")
    c1_plan = json.loads((directory / "selected-plan.json").read_text())
    write_json(directory / "selected-plan-c1.json", c1_plan)
    stand_ins = json.loads((directory / "stand-ins.json").read_text())
    plan = stand_in_plan(c1_plan, stand_ins, manifest["cohort"], dropped)
    write_json(directory / "selected-plan.json", plan)
    return {**summary, "dropped_lakes": dropped}


def worker(spec: dict) -> None:
    load(workloads=True)
    install_grid()
    if spec["phase"] == "extract":
        plan = json.loads((Path(spec["directory"]) / "frozen-plan.json").read_text())
        if plan["aqr"]["source_digests"] != own_digests():
            raise ValueError("probe T6 source changed after the freeze")
    if spec["phase"] != "freeze":
        lazy.worker(spec)
        return
    started = time.perf_counter()
    cpu = harness.cpu_seconds()
    result = {"phase": "freeze", "started_at": harness.utc_now()}
    try:
        result.update(freeze_phase(spec))
        result["artifacts"] = lazy.artifact_digests(spec["directory"], "freeze")
        result["status"] = "complete"
    except BaseException as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result["elapsed_seconds"] = time.perf_counter() - started
        result["cpu"] = harness.cpu_delta(cpu, harness.cpu_seconds())
        result["peak_worker_rss_bytes"] = harness.peak_rss_bytes()
        write_json(spec["result"], result)


def run_phase(base: Path, cohort: str, phase: str, temporary: Path, **extra) -> dict:
    directory = base / cohort
    name = phase + ("-" + extra["configuration"] if "configuration" in extra else "")
    spec_path = directory / f"{name}.json"
    if phase == "extract" and lazy.extraction_attempted(spec_path):
        status = spec_path.with_suffix(".supervision.json")
        return json.loads(status.read_text()) if status.exists() else {"status": "interrupted"}
    if phase in ("freeze", "prepare") and lazy.phase_complete(spec_path):
        return {"status": "complete", "reused": True}
    lazy.archive_phase(spec_path)
    phase_temporary = temporary / f"{cohort}-{name}"
    phase_temporary.mkdir()
    spec = {
        "phase": phase,
        "cohort": cohort,
        "directory": str(directory),
        "temporary": str(phase_temporary),
        "selections": str(directory / "selections.sqlite"),
        "result": str(directory / f"{name}.result.json"),
        **extra,
    }
    write_json(spec_path, spec)
    write_json(spec_path.with_suffix(".supervision.json"), {"status": "not_started"})
    print(f"starting {cohort}: {name}", flush=True)
    try:
        status = supervise(SCRIPT, spec_path)
    finally:
        shutil.rmtree(phase_temporary, ignore_errors=True)
    write_json(spec_path.with_suffix(".supervision.json"), status)
    print(f"finished {cohort}: {name}: {status['status']}", flush=True)
    return status


def run_workloads(run_dir: Path) -> None:
    load(workloads=True)
    install_grid()
    base = run_dir / "workloads"
    base.mkdir(parents=True, exist_ok=True)
    with (base / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        clean_workspace(base)
        temporary = create_workspace(base)
        try:
            for cohort in CONFIGURATIONS:
                directory = base / cohort
                directory.mkdir(exist_ok=True)
                if not (directory / "stand-ins.json").exists():
                    write_json(directory / "pairing-summary.json", pair_cohort(directory, cohort))
                for phase in ("freeze", "prepare"):
                    status = run_phase(base, cohort, phase, temporary)
                    if status["status"] != "complete":
                        raise RuntimeError(f"{cohort} {phase}: {status}")
            for cohort, order in CONFIGURATIONS.items():
                for configuration in order:
                    status = run_phase(
                        base, cohort, "extract", temporary, configuration=configuration
                    )
                    if status["status"] == "not_started":
                        raise RuntimeError(f"{cohort} {configuration} not started: {status}")
                run_phase(base, cohort, "validate", temporary)
        finally:
            write_json(base / "cleanup.json", clean_workspace(base))


def part_items(run_dir: Path, part: str) -> list[dict]:
    """The stand-in items one completed stage read, from its saved files."""
    if part == "stage4":
        return [
            s["item"] for s in json.loads((run_dir / "stage4.json").read_text())["plan"]["scenes"]
        ]
    return [json.loads(p.read_text()) for p in sorted((run_dir / part).glob("*/items/*.json"))]


def verify_headers(run_dir: Path) -> int:
    """Check every layer each completed stage read against its declared grid. Headers only.

    The workload prepare phase checks its own headers, workload_readers.read_headers.
    """
    load()
    install_grid()
    for part in ("stage2", "stage3", "stage4"):
        if not (run_dir / f"{part}.json").exists():
            continue
        HEADER_CHECKS.clear()
        for item in part_items(run_dir, part):
            grid = aqr_pairing.grid_20m(item)
            assets = ORIGINAL["resolve_assets"](item, list(aqr_pairing.T6_LAYERS), grid)["assets"]
            check_headers(item, assets, grid)
        write_json(
            run_dir / part / "header-checks-after.json",
            {"checked_at": harness.utc_now(), "checks": HEADER_CHECKS},
        )
        print(f"{part}: {len(HEADER_CHECKS)} layers checked, no problem", flush=True)
    return 0


def accept_source_change(run_dir: Path, reason: str) -> None:
    """Record a source change in the run state. Refused once any workload phase started."""
    identity = run_dir / "run.json"
    state = json.loads(identity.read_text())
    if not reason.strip():
        raise ValueError("a source change needs a reason")
    started = [p for p in (run_dir / "workloads").glob("*/*.launch.json")]
    if started:
        raise ValueError(f"workload phases already launched: {started}")
    current = own_digests()
    if current == state["source_digests"]:
        return
    state.setdefault("source_history", []).append(
        {
            "recorded_at": harness.utc_now(),
            "reason": reason,
            "previous_digests": state["source_digests"],
            "current_digests": current,
            "parts_complete_before": sorted(
                p for p in ("stage2", "stage3", "stage4") if (run_dir / f"{p}.json").exists()
            ),
        }
    )
    state["source_digests"] = current
    write_json(identity, state)
    print(f"recorded a source change: {reason}", flush=True)


# ---------------------------------------------------------------- result


def rel(path: Path) -> str:
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def compact_run(run: dict, keys: tuple[str, ...]) -> dict:
    out = {k: run.get(k) for k in keys if k in run}
    for k in ("wall_seconds", "elapsed_seconds", "cpu", "peak_rss_bytes", "totals"):
        if k in run:
            out[k] = run[k]
    if "error" in run:
        out["error"] = run["error"][-300:]
    return out


def reference_ids(part: str) -> set[str]:
    data = json.loads(REFERENCES[part].read_text())
    if part == "stage2":
        return {s["item"]["id"] for s in data["scenes"].values() if s.get("item")}
    if part == "stage3":
        return {s["item"]["id"] for s in data["tiles"].values() if s.get("item")}
    if part == "stage4":
        return {s["item"]["id"] for s in data["plan"]["scenes"]}
    ids = set()
    for cohort in CONFIGURATIONS:
        plan = json.loads((WORKLOAD_REFERENCE / cohort / "frozen-plan.json").read_text())
        ids |= {s["item"]["id"] for s in plan["scenes"]}
    return ids


def same_acquisitions(paired: list[str], part: str) -> dict:
    reference = reference_ids(part)
    return {
        "products": len(paired),
        "same_item_as_reference": sum(1 for p in paired if p in reference),
        "reference_items": len(reference),
    }


def collate_stage(run_dir: Path, part: str) -> dict:
    data = json.loads((run_dir / f"{part}.json").read_text())
    pairing = json.loads((run_dir / part / "pairing" / "pairing.json").read_text())
    own = {item["id"] for item in part_items(run_dir, part)}
    checks = [
        c
        for c in json.loads((run_dir / part / "header-checks.json").read_text())
        if c["item"] in own
    ]
    after_path = run_dir / part / "header-checks-after.json"
    after = json.loads(after_path.read_text()) if after_path.exists() else None
    out = {
        "intermediate": rel(run_dir / f"{part}.json"),
        "intermediate_sha256": hashlib.sha256((run_dir / f"{part}.json").read_bytes()).hexdigest(),
        "reference": rel(REFERENCES[part]),
        "measured_at": data.get("measured_at"),
        "pairing": pairing["summary"],
        "header_checks_during_run": {
            "layers": len(checks),
            "problems": sum(bool(c["problems"]) for c in checks),
        },
        "header_checks_after_run": None
        if after is None
        else {
            "checked_at": after["checked_at"],
            "layers": len(after["checks"]),
            "problems": sum(bool(c["problems"]) for c in after["checks"]),
        },
        "summary": data.get("summary"),
    }
    if part == "stage2":
        scenes = {r: s for r, s in data["scenes"].items()}
        out["scenes"] = {
            r: {k: s.get(k) for k in ("tile", "note")} | {"item": s.get("item")}
            for r, s in scenes.items()
        }
        keys = ("water_body_id", "region", "size_label", "method", "repetition", "tile", "item_id")
    elif part == "stage3":
        out["selection"] = data.get("selection")
        out["tiles"] = {
            t: {k: s.get(k) for k in ("tile", "regions", "note")} | {"item": s.get("item")}
            for t, s in data["tiles"].items()
        }
        keys = ("tile", "region", "pattern", "method", "repetition", "item_id")
    else:
        out["scenes"] = [
            {
                "region": s["region"],
                "tile": s["tile"],
                "item": s["item"]["id"],
                "paired_item": s["item"]["properties"].get("aqr:paired_item"),
                "members": s["members"],
            }
            for s in data["plan"]["scenes"]
        ]
        paired = [s["item"]["properties"].get("aqr:paired_item") for s in data["plan"]["scenes"]]
        keys = ("unit", "region", "path", "method", "repetition")
    if part != "stage4":
        # Stage 2 and 3 results keep trimmed items. Their saved items keep the pairing.
        paired = [
            json.loads(path.read_text())["properties"]["aqr:paired_item"]
            for path in sorted((run_dir / part).glob("*/items/*.json"))
        ]
    out["same_acquisitions"] = same_acquisitions(paired, part)
    out["runs"] = [compact_run(r, keys) for r in data.get("runs", [])]
    return out


def collate_workloads(run_dir: Path) -> dict:
    base = run_dir / "workloads"
    out = {}
    for cohort in CONFIGURATIONS:
        directory = base / cohort
        if not (directory / "comparisons.json").exists():
            phases = {
                name: json.loads(path.read_text())
                for name in ("freeze", "prepare")
                if (path := directory / f"{name}.supervision.json").exists()
            }
            summary = directory / "pairing-summary.json"
            out[cohort] = {
                "status": "not run",
                "pairing": json.loads(summary.read_text()) if summary.exists() else None,
                "phases": phases,
            }
            continue
        plan = json.loads((directory / "frozen-plan.json").read_text())
        manifest = json.loads((directory / "manifest.json").read_text())
        comparisons = json.loads((directory / "comparisons.json").read_text())
        paired = [s["paired_item"] for s in plan["scenes"]]
        out[cohort] = {
            "status": "complete",
            "pairing": json.loads((directory / "pairing-summary.json").read_text()),
            "plan_sha256": plan["sha256"],
            "lakes": len(manifest["lakes"]),
            "dropped_lakes": plan["aqr"]["dropped_lakes"],
            "products": len(plan["scenes"]),
            "tiles": len({s["tile"] for s in plan["scenes"]}),
            "tile_dates": len(
                {(s["tile"], s["item"]["properties"]["datetime"][:10]) for s in plan["scenes"]}
            ),
            "acquisitions": len({s["group"] for s in plan["scenes"]}),
            "lake_product_memberships": sum(len(s["members"]) for s in plan["scenes"]),
            "same_acquisitions": same_acquisitions(paired, "workloads"),
            "preparation": plan["preparation"],
            "unconverged_geometry": plan.get("unconverged_geometry", []),
            "limits": plan["limits"],
            "comparisons": [r for r in comparisons if r.get("status") != "not_attempted"],
        }
    return out


def collate(run_dir: Path, output: Path = RESULT) -> int:
    import rasterio

    run_dir = run_dir.resolve()
    result = {
        "schema_version": 1,
        "measured_at": min(
            json.loads((run_dir / "run.json").read_text())["parts"].values(), default=None
        ),
        "collated_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": {**own_digests(), **lazy.source_digests()},
        "script": "benchmarks/aqr_workloads.py",
        "probe": "T6, docs/reviews/2026-10-13-acolite-first-replan.md",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2, assumption A25. "
            "Transfer times include that path."
        ),
        "endpoints": {
            "bucket": aqr.BUCKET,
            "region": aqr.REGION,
            "endpoint": aqr.ENDPOINT,
            "earth_search": t4.ES_ROOT,
            "earth_search_use": (
                "Selection metadata only: Collection 1 candidates and Level-1C datastrips. "
                "No Collection 1 pixel is read."
            ),
            "credentials": "none, unsigned requests",
            "payer": (
                "Bucket owner. Every request was unsigned, so no requester was charged. "
                "A requester-pays bucket refuses unsigned requests."
            ),
        },
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "layers": aqr_pairing.T6_LAYERS,
        "pairing_rule": aqr_pairing.pair_product.__doc__.strip(),
        "run_directory": rel(run_dir),
        "run_source_digests": json.loads((run_dir / "run.json").read_text())["source_digests"],
        "source_history": json.loads((run_dir / "run.json").read_text()).get("source_history", []),
        "limitations": LIMITATIONS,
    }
    for part in PARTS:
        if part == "workloads":
            if (run_dir / "workloads").exists():
                result["workloads"] = collate_workloads(run_dir)
        elif (run_dir / f"{part}.json").exists():
            result[part] = collate_stage(run_dir, part)
    write_json(output, result)
    print(f"wrote {output}", flush=True)
    return 0


# ---------------------------------------------------------------- entry


def print_plan() -> None:
    lines = [
        f"Bucket {aqr.BUCKET}, region {aqr.REGION}, unsigned requests, no credentials.",
        f"Earth Search {t4.ES_ROOT}, Collection 1 and Level-1C metadata only, unsigned.",
        "Layers: " + ", ".join(f"{k} = {v}" for k, v in aqr_pairing.T6_LAYERS.items()) + ".",
        "Pairing: " + " ".join(aqr_pairing.pair_product.__doc__.split()),
        "stage2: benchmarks/lake_extraction.py unchanged, pilot manifest, its default window,",
        "        methods, and three repetitions, on stand-ins for the Collection 1 candidates.",
        "stage3: benchmarks/tile_extraction.py unchanged, baseline this run's stage 2.",
        f"stage4: benchmarks/cross_tile_extraction.py unchanged, regions {STAGE4_REGIONS},",
        f"        stand-ins for the saved catalog {STAGE4_CATALOG.relative_to(ROOT)}.",
        f"workloads: the frozen cohorts of {WORKLOAD_REFERENCE.relative_to(ROOT)},",
        "        catalog restricted to paired items, unchanged freeze and prepare,",
        "        then "
        + ", ".join(f"{c}: {' then '.join(o)}" for c, o in CONFIGURATIONS.items())
        + ".",
        f"        Limits unchanged: {json.dumps(LIMITS)}.",
        "Writes intermediate files under the run directory and, on --collate,",
        f"{RESULT.relative_to(ROOT)}.",
        "Tolerances are each earlier script's own, unchanged. Rules added here: the pairing, the",
        "layer map, and a header check of every chosen layer against its declared grid.",
    ]
    print("\n".join(lines))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", type=Path, metavar="RUN_DIR")
    mode.add_argument("--collate", type=Path, metavar="RUN_DIR")
    mode.add_argument("--verify-headers", type=Path, metavar="RUN_DIR")
    mode.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    for task in ("prepare", "extract", "select"):
        mode.add_argument(f"--{task}-worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--parts", nargs="+", choices=PARTS, default=list(PARTS))
    parser.add_argument("--output", type=Path, default=RESULT, help="result path for --collate")
    parser.add_argument("--accept-source-change", metavar="REASON", help="with --run")
    args = parser.parse_args(argv)

    for task in ("prepare", "extract", "select"):
        path = getattr(args, f"{task}_worker")
        if path:
            name = os.environ["AQR_T6_MODULE"]
            module = importlib.import_module(name)
            # Stage 4 workers select and read stand-ins, so they need its guard substitution.
            install() if name == "cross_tile_extraction" else install_grid()
            return module.main([f"--{task}-worker", str(path)]) or 0
    if args.worker:
        worker(json.loads(args.worker.read_text()))
        return 0
    if args.verify_headers:
        return verify_headers(args.verify_headers.resolve())
    if args.collate:
        load(workloads=True)
        return collate(args.collate, args.output)
    print_plan()
    if not args.run:
        return 0
    run_dir = args.run.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    identity = run_dir / "run.json"
    state = (
        json.loads(identity.read_text())
        if identity.exists()
        else {"created_at": harness.utc_now(), "source_digests": own_digests(), "parts": {}}
    )
    if args.accept_source_change is not None and identity.exists():
        accept_source_change(run_dir, args.accept_source_change)
        state = json.loads(identity.read_text())
    if state["source_digests"] != own_digests():
        raise ValueError("probe T6 source changed since this run directory was created")
    for part in args.parts:
        state["parts"].setdefault(part, harness.utc_now())
        write_json(identity, state)
        if part == "workloads":
            run_workloads(run_dir)
        else:
            run_stage(run_dir, part)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
