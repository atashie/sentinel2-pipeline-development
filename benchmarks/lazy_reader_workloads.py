"""Run the approved 100-lake U.S. and 1,000-lake Florida comparisons once.

No arguments prints the plan without network access. --execute selects and prepares
both cohorts, prints the preflight, and stops. --extract runs only unattempted frozen
configurations. Both commands resume the same owned directory. --worker is internal.
"""

from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import re
import shutil
import sqlite3
import statistics
import sys
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks"), str(ROOT / "tools")]

import build_workload_manifests as selector  # noqa: E402
import cross_tile_extraction as previous  # noqa: E402
import psutil  # noqa: E402
import workload_readers as readers  # noqa: E402

from s2proto import harness, masks  # noqa: E402
from s2proto.workload_resources import (  # noqa: E402
    LIMITS,
    MIB,
    OWNER,
    active_workers,
    admit,
    clean_workspace,
    create_workspace,
    recover_workspaces,
    supervise,
    write_json,
)

WINDOW = ["2025-06-01", "2025-06-30"]
BANDS = previous.BANDS
BASE = ROOT / "data/lazy-reader-workloads"
RESULT = ROOT / "benchmarks/results/lazy-reader-workloads.json"
SOURCE_FILES = [
    Path(__file__),
    Path(readers.__file__),
    Path(selector.__file__),
    Path(selector.pilot.__file__),
    ROOT / "src/s2proto/workload_resources.py",
    ROOT / "tools/rerun_sleep_workloads.py",
    *previous.SOURCE_FILES,
]
LIMITATIONS = [
    "One observed attempt per configuration, without timing repetitions or confidence intervals.",
    "Workloads differ in count, geography and lake-size distribution. Density is not isolated.",
    "Laptop measurements do not establish AWS throughput or production storage performance.",
    "Application workers are fresh. Provider, OS and network cache effects are uncontrolled.",
    "GDAL debug ranges measure requested bytes, not separately metered delivered bytes.",
    "Public polygons and catalog footprints do not establish current shorelines or pixel validity.",
    "Raw native-grid contributions remain separate. Science and primary roles remain open.",
    "Memory estimates and RSS polling reduce risk. They are not OS-enforced memory limits.",
    "Raster windows follow required native blocks, using GDAL caching across lakes in workflow B.",
    "The current lazy control retains 2048-pixel chunks and one compute per lake and band.",
    "Unconverged selection geometry uses its smallest-bound refinement, recorded per lake. "
    "Native pixel classes still use the original polygon.",
]


def source_digests():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in dict.fromkeys(SOURCE_FILES)
    }


def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while part := stream.read(MIB):
            result.update(part)
    return result.hexdigest()


def load_lake(entry):
    path = Path(entry["path"])
    admit(path.stat().st_size * 40 + 32 * MIB)
    if file_digest(path) != entry["file_sha256"]:
        raise ValueError("frozen lake geometry changed")
    return json.loads(path.read_text())


def search(client, bbox):
    body = {
        "collections": [previous.stage2.COLLECTION],
        "bbox": bbox,
        "datetime": f"{WINDOW[0]}T00:00:00Z/{WINDOW[1]}T23:59:59Z",
        "limit": 50,
    }
    seen = set()
    while True:
        key = readers.digest(body)
        if key in seen:
            raise ValueError("catalog pagination repeated")
        seen.add(key)
        page = client.request(f"{previous.stage2.ES_ROOT}/search", body)
        yield from page.get("features", [])
        link = next((x for x in page.get("links", []) if x.get("rel") == "next"), None)
        if not link:
            break
        if not link.get("body"):
            raise ValueError("unsupported catalog pagination")
        body = {**body, **link["body"]} if link.get("merge") else link["body"]


def catalog(manifest, directory):
    directory = Path(directory)
    client = selector.MetadataClient(directory / "catalog-responses")
    items_directory = directory / "catalog-items"
    items_directory.mkdir(exist_ok=True)
    by_region = defaultdict(list)
    for entry in manifest["lakes"]:
        by_region[entry["region"]].append(entry)
    regions, item_paths = {}, {}
    for region, entries in by_region.items():
        # Calculate one buffered envelope with only one boundary loaded at a time.
        bounds = [previous.buffered_bbox([load_lake(entry)]) for entry in entries]
        bbox = [
            min(b[0] for b in bounds),
            min(b[1] for b in bounds),
            max(b[2] for b in bounds),
            max(b[3] for b in bounds),
        ]
        ids, tiles = [], set()
        for item in search(client, bbox):
            path = items_directory / f"{readers.digest(item['id'])}.json"
            write_json(path, item)
            item_paths[item["id"]] = str(path)
            ids.append(item["id"])
            tiles.add(previous.item_tile(item))
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate item in catalog pagination")
        regions[region] = {
            "lakes": [e["id"] for e in entries],
            "items": ids,
            "tiles": sorted(t for t in tiles if t),
            "bbox": bbox,
        }
        print(f"catalog {region}: {len(ids)} items", flush=True)
    # Merge dispersed groups that could share a native tile. They then use one acquisition.
    groups = []
    for region in regions.values():
        group = {
            "lakes": set(region["lakes"]),
            "items": set(region["items"]),
            "tiles": set(region["tiles"]),
        }
        matches = [g for g in groups if g["tiles"] & group["tiles"]]
        for other in matches:
            for key in group:
                group[key].update(other[key])
            groups.remove(other)
        groups.append(group)
    snapshot = {
        "created_at": harness.utc_now(),
        "window": WINDOW,
        "regions": regions,
        "items": item_paths,
        "groups": [{k: sorted(v) for k, v in g.items()} for g in groups],
    }
    write_json(directory / "catalog.json", snapshot)
    return {"catalog": str(directory / "catalog.json"), "local_groups": len(groups)}


def assign_acquisitions(eligible_by_lake):
    """Greedily cover remaining lakes, requiring complete support for each assigned lake."""
    remaining = set(eligible_by_lake)
    assignments = []
    while remaining:
        candidates = defaultdict(list)
        for lid in sorted(remaining):
            for gid in eligible_by_lake[lid]:
                candidates[gid].append(lid)
        if not candidates:
            raise ValueError(f"no complete acquisition for lakes: {sorted(remaining)}")

        def rank(gid, candidates=candidates):
            scores = [eligible_by_lake[lid][gid] for lid in candidates[gid]]
            return (
                -len(scores),
                max(s[0] for s in scores),
                max(s[1] if s[1] is not None else float("inf") for s in scores),
                -min(previous.timestamp(s[2]) for s in scores),
                gid,
            )

        winner = min(candidates, key=rank)
        assigned = sorted(candidates[winner])
        assignments.append(
            {
                "datatake": winner,
                "lakes": assigned,
                "selection": "most remaining fully covered lakes, then coverage/cloud/time/id",
            }
        )
        remaining.difference_update(assigned)
    return assignments


def freeze(manifest, snapshot, directory):
    directory = Path(directory)
    diagnostic = directory / "selection-diagnostics"
    diagnostic.mkdir(exist_ok=True)
    lakes = {entry["id"]: entry for entry in manifest["lakes"]}
    scenes = {}
    group_records = []
    unconverged = []
    for number, group in enumerate(snapshot["groups"]):
        paths = [Path(snapshot["items"][iid]) for iid in group["items"]]
        admit(sum(p.stat().st_size for p in paths) * 12 + 128 * MIB)
        items = [json.loads(p.read_text()) for p in paths]
        eligible_by_lake = {}
        for lid in group["lakes"]:
            selection = previous.select_region(items, [load_lake(lakes[lid])])
            selection.pop("selected_items")
            audit = next(g["coverage"][lid]["geometry_check"] for g in selection["groups"])
            if audit.get("converged") is False:
                unconverged.append({"lake": lid, **audit})
                print(
                    f"geometry diagnostic {lid}: unconverged, "
                    f"spacing {audit['spacing_m']} m, bound {audit['relative_change_bound']}",
                    flush=True,
                )
            write_json(diagnostic / f"{lid}.json", selection)
            eligible_by_lake[lid] = {
                g["group"]: g["score"] for g in selection["groups"] if g["eligible"]
            }
            print(f"selected candidates for {lid}", flush=True)
        assignments = assign_acquisitions(eligible_by_lake)
        item_by_id = {item["id"]: item for item in items}
        assigned = {lid: part["datatake"] for part in assignments for lid in part["lakes"]}
        for lid in group["lakes"]:
            winner = assigned[lid]
            selection = json.loads((diagnostic / f"{lid}.json").read_text())
            chosen = next(g for g in selection["groups"] if g["group"] == winner)
            for product in chosen["coverage"][lid]["products"]:
                iid = product["item"]
                if iid not in scenes:
                    item = item_by_id[iid]
                    grid, assets = previous.native_assets(item, BANDS)
                    scenes[iid] = {
                        "item": item,
                        "tile": previous.item_tile(item),
                        "group": winner,
                        "grid": dataclasses.asdict(grid),
                        "assets": assets,
                        "members": [],
                    }
                scenes[iid]["members"].append(lid)
        group_records.append(
            {
                "group": number,
                "lakes": group["lakes"],
                "split_required": len(assignments) > 1,
                "assignments": assignments,
            }
        )
        del items, item_by_id
    order = list(readers.CONFIGURATIONS)
    if manifest["cohort"] == "florida":
        order = ["B-lazy-control", "C-lazy", "A-raster", "B-lazy", "C-raster", "A-lazy", "B-raster"]
    plan = {
        "created_at": harness.utc_now(),
        "cohort": manifest["cohort"],
        "scenes": [scenes[iid] for iid in sorted(scenes)],
        "groups": group_records,
        "source_digests": source_digests(),
        "window": WINDOW,
        "bands": BANDS,
        "order": order,
        "limits": LIMITS,
        "tolerances": {
            "raw_pixels_classes_values": 0,
            "geometry_fraction": masks.FRACTION_TOLERANCE,
            "coverage": previous.TOLERANCE,
        },
        "catalog_sha256": readers.digest(snapshot),
        "manifest_sha256": readers.digest(manifest),
        "limitations": LIMITATIONS,
        "unconverged_geometry": unconverged,
    }
    if set(lakes) != {lid for scene in plan["scenes"] for lid in scene["members"]}:
        raise ValueError("selected imagery does not include every requested lake")
    write_json(directory / "selected-plan.json", plan)
    return {
        "products": len(scenes),
        "local_groups": len(group_records),
        "unconverged_geometry": unconverged,
    }


def io_summary(path, database_path):
    """Stream logs into a disk-backed range counter, including retry diagnostics."""
    db = readers.connect(database_path)
    db.execute("CREATE TABLE ranges (href TEXT,range TEXT,n INT,PRIMARY KEY(href,range))")
    totals = {
        "range_requests": 0,
        "bytes_requested": 0,
        "size_requests": 0,
        "retry_messages": 0,
        "timeout_messages": 0,
    }
    with Path(path).open() as stream:
        for line in stream:
            measured = harness.parse_gdal_log([line])
            totals["range_requests"] += measured["requests"]
            totals["bytes_requested"] += measured["bytes"]
            totals["size_requests"] += measured["size_requests"]
            totals["retry_messages"] += bool(re.search(r"retrying", line, re.I))
            totals["timeout_messages"] += bool(re.search(r"timed? ?out|timeout", line, re.I))
            match = re.search(r"VSICURL: Downloading (\S+) \(([^)]+)\)", line)
            if match:
                byte_range, href = match.groups()
                db.execute(
                    "INSERT INTO ranges VALUES (?,?,1) ON CONFLICT(href,range) DO UPDATE SET n=n+1",
                    (href, byte_range),
                )
    totals["repeated_exact_ranges"] = db.execute(
        "SELECT COALESCE(SUM(n-1),0) FROM ranges"
    ).fetchone()[0]
    db.commit()
    db.close()
    totals["requests"] = totals["range_requests"] + totals["size_requests"]
    totals["delivered_bytes"] = None
    return totals


def worker(spec):
    started = time.perf_counter()
    cpu = harness.cpu_seconds()
    directory = Path(spec["directory"])
    phase = spec["phase"]
    result = {"phase": phase, "started_at": harness.utc_now()}
    if "spawn_started" in spec:
        result["startup_seconds"] = started - spec["spawn_started"]
    try:
        if phase == "boundaries":
            result.update(selector.build(spec["cohort"], directory))
        else:
            manifest = json.loads((directory / "manifest.json").read_text())
            if phase == "catalog":
                result.update(catalog(manifest, directory))
            elif phase == "freeze":
                result.update(
                    freeze(
                        manifest, json.loads((directory / "catalog.json").read_text()), directory
                    )
                )
            elif phase == "prepare":
                plan = json.loads((directory / "selected-plan.json").read_text())
                before = time.perf_counter()
                readers.read_headers(plan, directory)
                result["header_seconds"] = time.perf_counter() - before
                before = time.perf_counter()
                prepared = Path(spec["temporary"]) / "selections.sqlite"
                expected = Path(spec["temporary"]) / "expected.sqlite"
                result["preparation"] = readers.prepare_selections(
                    plan, manifest, prepared, expected
                )
                result["geometry_seconds"] = time.perf_counter() - before
                plan["preparation"] = result["preparation"]
                plan["selection_sha256"] = file_digest(prepared)
                plan["expected_sha256"] = file_digest(expected)
                prepared.replace(spec["selections"])
                expected.replace(directory / "expected.sqlite")
                plan["sha256"] = readers.digest(plan)
                write_json(directory / "frozen-plan.json", plan)
            elif phase == "extract":
                plan = json.loads((directory / "frozen-plan.json").read_text())
                verify_frozen(directory, plan)
                name = spec["configuration"]
                result["configuration"] = name
                path = directory / f"{name}.sqlite"
                before = time.perf_counter()
                with readers.gdal_log(directory / f"{name}.gdal.log"):
                    extractor = readers.Extractor(plan, spec["selections"], path, name)
                    result.update(extractor.run())
                result["extraction_seconds"] = time.perf_counter() - before
            elif phase == "validate":
                result["comparisons"] = finalize_cohort(directory)
            else:
                raise ValueError(phase)
        if phase in ("boundaries", "catalog", "freeze", "prepare"):
            result["artifacts"] = artifact_digests(directory, phase)
        result["status"] = "complete"
    except BaseException as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise
    finally:
        result["elapsed_seconds"] = time.perf_counter() - started
        result["cpu"] = harness.cpu_delta(cpu, harness.cpu_seconds())
        result["peak_worker_rss_bytes"] = harness.peak_rss_bytes()
        write_json(spec["result"], result)


def finalize_cohort(directory):
    directory = Path(directory)
    reference, results = None, []
    for name in readers.CONFIGURATIONS:
        spec_path = directory / f"extract-{name}.json"
        status_path = spec_path.with_suffix(".supervision.json")
        if not status_path.exists():
            results.append({"configuration": name, "status": "not_attempted"})
            continue
        status = json.loads(status_path.read_text())
        result_path = directory / f"extract-{name}.result.json"
        result = json.loads(result_path.read_text()) if result_path.exists() else {}
        row = {**result, "configuration": name, "supervision": status}
        actual = directory / f"{name}.sqlite"
        if actual.exists():
            try:
                validation = readers.validate(directory / "expected.sqlite", actual, reference)
                row["validation"] = validation
                complete = status["status"] == "complete" and validation["complete"]
                row["status"] = "complete" if complete else "incomplete"
                if complete and reference is None:
                    reference = actual
                if validation["value_differences"]:
                    row["status"] = "differs" if complete else "incomplete"
                    row["comparison_note"] = (
                        "Different signatures do not identify which reader is wrong."
                    )
            except sqlite3.DatabaseError as exc:
                row.update(status="incomplete", validation_error=str(exc))
        else:
            row["status"] = "incomplete"
        log_path = directory / f"{name}.gdal.log"
        ranges = directory / f"{name}-ranges.sqlite"
        if log_path.exists():
            if ranges.exists():
                ranges.unlink()
            row["io"] = io_summary(log_path, ranges)
        results.append(row)
    # Mark the complete reference as checked against the other complete signatures too.
    completed = [r for r in results if r["status"] in ("complete", "differs")]
    complete_signatures = {r["validation"]["ordered_signature"] for r in completed}
    complete_count = len(completed)
    for row in results:
        if row["status"] in ("complete", "differs"):
            row["matches_all_complete_outputs"] = (
                complete_count >= 2 and len(complete_signatures) == 1
            )
            if len(complete_signatures) > 1:
                row["status"] = "differs"
                row["comparison_note"] = "No reader is designated correct by this disagreement."
    write_json(directory / "comparisons.json", results)
    return results


def transfer_estimates(
    plan,
    windowed_path=previous.TRANSFER_REFERENCE,
    whole_path=ROOT / "benchmarks/results/tile-extraction.json",
):
    """Historical scenarios for every configuration, explicitly identifying changed settings."""
    historical = json.loads(Path(windowed_path).read_text())
    whole = json.loads(Path(whole_path).read_text())
    memberships = sum(len(scene["members"]) for scene in plan["scenes"])
    products = len(plan["scenes"])
    old_memberships = historical["summary"]["memberships"]
    # Improved B has no measured reference. Raster B supplies a shared-block proxy.
    mapping = {
        "A-raster": ("lake-first", "raster-mask"),
        "A-lazy": ("lake-first", "lazy-stack"),
        "B-raster": ("tile-first", "raster-mask"),
        "B-lazy": ("tile-first", "raster-mask"),
        "B-lazy-control": ("tile-first", "lazy-stack"),
    }
    estimates = []
    for name in readers.CONFIGURATIONS:
        row = {
            "configuration": name,
            "requested_bytes_range": None,
            "historical_median_scaled_bytes": None,
            "kind": "historical proxy, not a bound",
        }
        if name.startswith("C-"):
            method = "raster-mask" if name == "C-raster" else "lazy-stack"
            samples = (
                [
                    r["totals"]["bytes_requested"]
                    for r in whole["runs"]
                    if r["pattern"] == "whole-tile"
                    and r["method"] == method
                    and r["region"] != "iliamna"
                    and readers.old.run_status(r) == "ok"
                    and not readers.old.under_pressure(r)
                ]
                if whole["bands"] == plan["bands"]
                else []
            )
            scale = products
            row.update(
                reference=str(whole_path),
                reference_sha256=file_digest(whole_path),
                formula="observed full-product requested bytes times selected products",
                subset="non-Iliamna full-tile pilot reads, matching band set",
            )
        else:
            path, method = mapping[name]
            samples = (
                [
                    w["totals"]["bytes_requested"] / old_memberships
                    for w in historical["summary"]["workloads"]
                    if w["clean"] and w["path"] == path and w["method"] == method
                ]
                if old_memberships and historical["plan"]["bands"] == plan["bands"]
                else []
            )
            scale = memberships
            row.update(
                reference=str(windowed_path),
                reference_sha256=file_digest(windowed_path),
                reference_path=path,
                reference_reader=method,
                formula="observed workload bytes / memberships * new memberships",
                reference_memberships=old_memberships,
                new_memberships=memberships,
                optimized_reader_proxy=name in ("A-lazy", "B-lazy"),
            )
        if samples:
            row["requested_bytes_range"] = [
                round(min(samples) * scale),
                round(max(samples) * scale),
            ]
            row["historical_median_scaled_bytes"] = round(statistics.median(samples) * scale)
        else:
            row["reason"] = "no clean historical sample with matching bands"
        estimates.append(row)
    return {
        "configurations": estimates,
        "all_configurations_estimated": all(r["requested_bytes_range"] for r in estimates),
        "total_requested_bytes_range": [
            sum(r["requested_bytes_range"][i] for r in estimates) for i in (0, 1)
        ]
        if all(r["requested_bytes_range"] for r in estimates)
        else None,
        "compatible_measurement": False,
        "reference_settings": {
            k: historical["plan"][k] for k in ("chunk", "dask_workers", "gdal_cache_bytes")
        },
        "current_settings": {
            "aligned_chunks": "source block shape",
            "control_chunk": 2048,
            "dask_workers": LIMITS["threads"],
            "gdal_cache_bytes": LIMITS["gdal_cache_bytes"],
        },
        "limitations": [
            "Geometry, density, compression, grids, cache, concurrency and process counts differ.",
            "New block scheduling is unmeasured. Optimized lazy estimates use historical proxies.",
            "Observed historical ranges are not prediction intervals or hard transfer ceilings.",
            "No runtime prediction is inferred from these transfer scenarios.",
        ],
    }


def preflight(directory):
    plan = json.loads((Path(directory) / "frozen-plan.json").read_text())
    manifest = json.loads((Path(directory) / "manifest.json").read_text())
    areas = [lake["area_m2"] for lake in manifest["lakes"]]
    estimates = transfer_estimates(plan)
    whole = [
        row["requested_bytes_range"]
        for row in estimates["configurations"]
        if row["configuration"].startswith("C-")
    ]
    products = len(plan["scenes"])
    largest = max(a["shape"][0] * a["shape"][1] * 4 for s in plan["scenes"] for a in s["assets"])
    report = {
        "recorded_at": harness.utc_now(),
        "plan_sha256": plan["sha256"],
        "lakes": len(areas),
        "unconverged_geometry": plan.get("unconverged_geometry", []),
        "unconverged_geometry_count": len(plan.get("unconverged_geometry", [])),
        "area_m2": {
            "minimum": min(areas),
            "median": statistics.median(areas),
            "maximum": max(areas),
        },
        "area_band_counts": {
            band: sum(lake["area_band"] == band for lake in manifest["lakes"])
            for band in selector.AREA_BANDS
        },
        "products": products,
        "tiles": len({s["tile"] for s in plan["scenes"]}),
        "tile_dates": len(
            {(s["tile"], s["item"]["properties"]["datetime"][:10]) for s in plan["scenes"]}
        ),
        "acquisitions": len({s["group"] for s in plan["scenes"]}),
        "lake_product_memberships": sum(len(s["members"]) for s in plan["scenes"]),
        "whole_image_requested_bytes_estimate_two_passes": [
            sum(r[i] for r in whole) for i in (0, 1)
        ]
        if all(whole)
        else None,
        "estimate_basis": "Historical product and membership proxies. See transfer_estimates.",
        "transfer_estimates": estimates,
        "largest_band_float32_bytes": largest,
        "largest_whole_lazy_scratch_estimate_bytes": largest * 3 + 64 * MIB,
        "order": plan["order"],
        "limits": LIMITS,
        "preparation": plan["preparation"],
    }
    write_json(Path(directory) / "preflight.json", report)
    return report


def verify_frozen(directory, plan=None, *, expected_sources=None):
    directory = Path(directory)
    plan = plan or json.loads((directory / "frozen-plan.json").read_text())
    if readers.digest({k: v for k, v in plan.items() if k != "sha256"}) != plan["sha256"]:
        raise ValueError("frozen plan changed")
    if plan["source_digests"] != (
        source_digests() if expected_sources is None else expected_sources
    ):
        raise ValueError("source code changed after input freeze")
    for name, key in (
        ("selections.sqlite", "selection_sha256"),
        ("expected.sqlite", "expected_sha256"),
    ):
        if file_digest(directory / name) != plan[key]:
            raise ValueError(f"frozen {name} changed")
    return plan


def artifact_digests(directory, phase):
    directory = Path(directory)
    if phase == "boundaries":
        paths = [directory / "manifest.json"]
        paths += [Path(lake["path"]) for lake in json.loads(paths[0].read_text())["lakes"]]
    elif phase == "catalog":
        paths = [directory / "catalog.json"]
        paths += [Path(p) for p in json.loads(paths[0].read_text())["items"].values()]
    elif phase == "freeze":
        paths = [directory / "selected-plan.json"]
    else:
        paths = [
            directory / name
            for name in ("frozen-plan.json", "selections.sqlite", "expected.sqlite")
        ]
    return {str(path.relative_to(directory)): file_digest(path) for path in paths}


def phase_complete(spec_path):
    status_path = spec_path.with_suffix(".supervision.json")
    result_path = spec_path.with_suffix(".result.json")
    if not status_path.exists() or not result_path.exists():
        return False
    status, result = (json.loads(p.read_text()) for p in (status_path, result_path))
    if status["status"] != "complete" or result.get("status") != "complete":
        return False
    for relative, expected in result.get("artifacts", {}).items():
        if file_digest(spec_path.parent / relative) != expected:
            raise ValueError(f"completed phase artifact changed: {relative}")
    if not result.get("artifacts"):
        raise ValueError("completed preparation phase has no frozen artifact hashes")
    return True


def extraction_attempted(spec_path):
    marker = spec_path.with_suffix(".launch.json")
    if marker.exists():
        return json.loads(marker.read_text())["state"] != "not_spawned"
    status = spec_path.with_suffix(".supervision.json")
    if status.exists():
        record = json.loads(status.read_text())
        return record.get("spawned", record["status"] != "not_started")
    # Legacy or interrupted records with no launch evidence must not cause a duplicate read.
    return spec_path.exists()


def archive_phase(spec_path):
    files = list(spec_path.parent.glob(spec_path.stem + ".*"))
    if files:
        history = spec_path.parent / "phase-history" / spec_path.stem
        history.mkdir(parents=True, exist_ok=True)
        target = history / f"{len(list(history.iterdir())) + 1:04d}"
        target.mkdir()
        for path in files:
            path.replace(target / path.name)
        return target
    return None


def supersede_source(run_directory, saved, reason):
    """Record an explicit source revision before extraction, preserving prior evidence."""
    if not reason.strip():
        raise ValueError("source-change reason must not be blank")
    if list(run_directory.rglob("extract-*.launch.json")) or any(
        extraction_attempted(run_directory / cohort / f"extract-{configuration}.json")
        for cohort in ("dispersed", "florida")
        for configuration in readers.CONFIGURATIONS
    ):
        raise ValueError("source change forbidden after an extraction launch or unresolved attempt")
    current = source_digests()
    old = saved["source_digests"]
    if current == old:
        return
    # Verify reusable inputs and every old frozen artifact before moving anything.
    for cohort in ("dispersed", "florida"):
        directory = run_directory / cohort
        for phase in ("boundaries", "catalog", "freeze", "prepare"):
            phase_complete(directory / f"{phase}.json")
        for name in ("selected-plan.json", "frozen-plan.json"):
            path = directory / name
            if path.exists():
                plan = json.loads(path.read_text())
                if plan["source_digests"] != old:
                    raise ValueError(f"recorded source digests differ from run.json: {path}")
                if name == "frozen-plan.json":
                    verify_frozen(directory, plan, expected_sources=old)
    history = saved.get("source_history", [])
    archive = run_directory / "source-history" / f"{len(history) + 1:04d}"
    entry = {
        "recorded_at": harness.utc_now(),
        "reason": reason,
        "previous_digests": old,
        "current_digests": current,
        "changed_files": sorted(
            k for k in old.keys() | current.keys() if old.get(k) != current.get(k)
        ),
        "archive": str(archive.relative_to(run_directory)),
        "reused_phases": ["boundaries", "catalog"],
        "phase_archives": [],
    }
    archive.mkdir(parents=True)
    write_json(archive / "run.json", saved)
    # An interrupted transition cannot silently reuse a mixture of source versions.
    pending = run_directory / "source-change.pending.json"
    write_json(pending, entry)
    for cohort in ("dispersed", "florida"):
        directory = run_directory / cohort
        destination = archive / cohort
        destination.mkdir()
        for phase in ("freeze", "prepare"):
            phase_archive = archive_phase(directory / f"{phase}.json")
            if phase_archive:
                entry["phase_archives"].append(str(phase_archive.relative_to(run_directory)))
        for name in (
            "selected-plan.json",
            "frozen-plan.json",
            "selections.sqlite",
            "expected.sqlite",
            "preflight.json",
            "selection-diagnostics",
            "headers.gdal.log",
        ):
            path = directory / name
            if path.exists():
                path.replace(destination / name)
    preflight_path = run_directory / "preflight.json"
    if preflight_path.exists():
        preflight_path.replace(archive / "preflight.json")
    entry["archived_sha256"] = {
        str(path.relative_to(archive)): file_digest(path)
        for path in sorted(archive.rglob("*"))
        if path.is_file()
    }
    write_json(archive / "transition.json", entry)
    write_json(
        run_directory / "run.json",
        {**saved, "source_digests": current, "source_history": [*history, entry]},
    )
    pending.unlink()
    print(f"Recorded source supersession: {entry['archive']}: {reason}", flush=True)


def run_phase(run_directory, cohort, phase, temporary, **extra):
    directory = Path(run_directory) / cohort
    directory.mkdir(exist_ok=True)
    name = phase + ("-" + extra["configuration"] if "configuration" in extra else "")
    spec_path = directory / f"{name}.json"
    if phase == "extract" and extraction_attempted(spec_path):
        status_path = spec_path.with_suffix(".supervision.json")
        saved = (
            json.loads(status_path.read_text())
            if status_path.exists()
            else {"status": "interrupted"}
        )
        return {**saved, "skipped_attempted": True}
    if phase != "validate" and phase != "extract" and phase_complete(spec_path):
        return {"status": "complete", "reused": True}
    archive_phase(spec_path)
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
    write_json(
        spec_path.with_suffix(".supervision.json"), {"status": "not_started", "spawned": False}
    )
    print(f"starting {cohort}: {name}", flush=True)
    try:
        status = supervise(__file__, spec_path)
    finally:
        started = time.perf_counter()
        if phase_temporary.is_symlink() or phase_temporary.resolve().parent != temporary.resolve():
            raise ValueError("phase workspace escaped its owned parent")
        shutil.rmtree(phase_temporary)
        write_json(
            directory / f"{name}.cleanup.json",
            {
                "workspace": str(phase_temporary),
                "remaining_files": [],
                "seconds": time.perf_counter() - started,
            },
        )
    write_json(spec_path.with_suffix(".supervision.json"), status)
    print(f"finished {cohort}: {name}: {status['status']}", flush=True)
    return status


@contextmanager
def run_session(run_directory, *, create, accept_source_change=None):
    """One supervisor owns the run. Resume metadata without retaining temporary imagery."""
    run_directory = Path(run_directory).resolve()
    if create:
        run_directory.mkdir(parents=True, exist_ok=True)
    with (run_directory / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (run_directory / "source-change.pending.json").exists():
            raise ValueError("incomplete source transition requires inspection")
        if active_workers(run_directory):
            raise RuntimeError("a previous worker is alive or its launch is unresolved")
        identity = run_directory / "run.json"
        if identity.exists():
            saved = json.loads(identity.read_text())
            if saved.get("owner") != OWNER:
                raise ValueError("run ownership differs")
            if accept_source_change is not None:
                if not create:
                    raise ValueError("source change is only allowed during preflight")
                supersede_source(run_directory, saved, accept_source_change)
            elif saved["source_digests"] != source_digests():
                raise ValueError("run ownership or source version differs")
        elif create:
            if accept_source_change is not None:
                raise ValueError("source change requires an existing run identity")
            if any(p.name != "run.lock" for p in run_directory.iterdir()):
                raise ValueError("refusing to adopt an unmarked existing run directory")
            write_json(
                identity,
                {
                    "owner": OWNER,
                    "source_digests": source_digests(),
                    "created_at": harness.utc_now(),
                    "limits": LIMITS,
                },
            )
        else:
            raise ValueError("missing prepared run identity")
        if active_workers(run_directory):
            raise RuntimeError("a previous worker is alive or its launch is unresolved")
        recover_workspaces(run_directory.parent)
        clean_workspace(run_directory)
        process = psutil.Process()
        write_json(
            run_directory / "supervisor.json",
            {
                "owner": OWNER,
                "pid": process.pid,
                "create_time": process.create_time(),
                "started_at": harness.utc_now(),
            },
        )
        temporary = create_workspace(run_directory)
        try:
            yield run_directory, temporary
        finally:
            started = time.perf_counter()
            audit = clean_workspace(run_directory)
            audit["seconds"] = time.perf_counter() - started
            write_json(run_directory / "cleanup.json", audit)


def execute(run_directory, *, accept_source_change=None):
    """Prepare both workloads and stop before any image-pixel read. Resumable."""
    with run_session(run_directory, create=True, accept_source_change=accept_source_change) as (
        run_directory,
        temporary,
    ):
        result = {"created_at": harness.utc_now(), "cohorts": {}, "status": "preflight_incomplete"}
        for cohort in ("dispersed", "florida"):
            for phase in ("boundaries", "catalog", "freeze", "prepare"):
                status = run_phase(run_directory, cohort, phase, temporary)
                if status["status"] != "complete":
                    result.update(stopped_phase=f"{cohort}/{phase}", supervision=status)
                    write_json(run_directory / "preflight.json", result)
                    return result
            result["cohorts"][cohort] = {"preflight": preflight(run_directory / cohort)}
        result["status"] = "preflight_complete"
        write_json(run_directory / "preflight.json", result)
        for cohort, data in result["cohorts"].items():
            estimated = data["preflight"]["transfer_estimates"]["total_requested_bytes_range"]
            print(f"{cohort}: historical transfer scenario {estimated} requested bytes", flush=True)
            for row in data["preflight"]["transfer_estimates"]["configurations"]:
                print(f"  {row['configuration']}: {row['requested_bytes_range']}", flush=True)
        print(
            f"Preflight complete. Pixel extraction command: --extract {run_directory}", flush=True
        )
        return result


def extract(run_directory):
    """Run only unattempted configurations. Never retry a launched extraction worker."""
    run_directory = Path(run_directory).resolve()
    result = {
        "measured_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": source_digests(),
        "run_directory": str(run_directory),
        "machine": harness.machine_info(),
        "limitations": LIMITATIONS,
        "cohorts": {},
        "provider": {
            "endpoint": previous.stage2.ES_ROOT,
            "bucket": "e84-earth-search-sentinel-data",
            "region": "us-west-2",
            "payer": "public assets, not requester-pays",
        },
        "status": "incomplete",
    }
    entered = False
    try:
        with run_session(run_directory, create=False) as (run_directory, temporary):
            entered = True
            identity = json.loads((run_directory / "run.json").read_text())
            if "rerun" in identity:
                result["rerun"] = identity["rerun"]
                result["limitations"] = [
                    "Sleep-affected attempts were replaced with owner-authorized reruns. "
                    "Unaffected attempts retain their original dates and source versions.",
                    *LIMITATIONS[1:],
                ]
            saved = json.loads((run_directory / "preflight.json").read_text())
            if saved["status"] != "preflight_complete":
                raise ValueError("both cohorts require complete preflight before extraction")
            plans = {
                cohort: verify_frozen(run_directory / cohort) for cohort in ("dispersed", "florida")
            }
            if any(
                saved["cohorts"][cohort]["preflight"]["plan_sha256"] != plan["sha256"]
                for cohort, plan in plans.items()
            ):
                raise ValueError("preflight and frozen plans differ")
            result["cohorts"] = saved["cohorts"]
            paused = False
            for cohort, plan in plans.items():
                for configuration in plan["order"]:
                    status = run_phase(
                        run_directory, cohort, "extract", temporary, configuration=configuration
                    )
                    if status["status"] == "not_started":
                        result["paused_before"] = f"{cohort}/{configuration}"
                        paused = True
                        break
                validation = run_phase(run_directory, cohort, "validate", temporary)
                if validation["status"] == "complete":
                    path = run_directory / cohort / "comparisons.json"
                    result["cohorts"][cohort]["comparisons"] = json.loads(path.read_text())
                if paused:
                    break
            if all(
                len(c.get("comparisons", [])) == 7
                and all(
                    r["status"] == "complete" and r.get("matches_all_complete_outputs")
                    for r in c["comparisons"]
                )
                for c in result["cohorts"].values()
            ):
                result["status"] = "complete"
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if entered:
            result["cleanup"] = json.loads((run_directory / "cleanup.json").read_text())
            write_json(run_directory / "result.json", result)
            write_json(RESULT, result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--execute", type=Path, help="Prepare inputs and print preflight, then stop")
    modes.add_argument("--extract", type=Path, help="Extract unattempted frozen configurations")
    modes.add_argument("--worker", type=Path)
    parser.add_argument("--accept-source-change", metavar="REASON")
    args = parser.parse_args(argv)
    if args.accept_source_change is not None and not args.execute:
        parser.error("--accept-source-change requires --execute")
    if args.worker:
        worker(json.loads(args.worker.read_text()))
    elif args.execute:
        execute(args.execute, accept_source_change=args.accept_source_change)
    elif args.extract:
        extract(args.extract)
    else:
        print(
            json.dumps(
                {
                    "workloads": {"dispersed": 100, "florida": 1000},
                    "window": WINDOW,
                    "configurations": readers.CONFIGURATIONS,
                    "attempts": 1,
                    "limits": LIMITS,
                    "network": "--execute: metadata/headers only; --extract: image pixels",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
