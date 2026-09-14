"""Stage 1, raw access: read whole tiles from both GeoTIFF copies and time it.

Runs only when the user invokes it. It contacts the Earth Search STAC API to find one
acquisition on both Level-2A collections, then reads every band of that acquisition from the
two public buckets. Each read is a whole tile. Nothing is written back to a provider.

    uv run python benchmarks/raw_access.py --dry-run                # plan only, no network
    uv run python benchmarks/raw_access.py --groups 60m --repeat 1  # smoke run, two small bands
    uv run python benchmarks/raw_access.py                          # every group, three times

Every combination of copy, band group, read mode, and repetition runs in a fresh worker
process, so GDAL's caches are cold for each run. Two read modes: `vsicurl`, where GDAL reads
the object in ranges, and `whole-object`, one HTTP GET followed by a decode from memory.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from s2proto import harness  # noqa: E402

ES_ROOT = "https://earth-search.aws.element84.com/v1"
COPIES = {
    "c1": {
        "label": "Collection 1 copy",
        "collection": "sentinel-2-c1-l2a",
        "bucket": "e84-earth-search-sentinel-data",
    },
    "older": {"label": "older copy", "collection": "sentinel-2-l2a", "bucket": "sentinel-cogs"},
}
BAND_GROUPS = {
    "10m": ["blue", "green", "red", "nir"],
    "20m": ["rededge1", "rededge2", "rededge3", "nir08", "swir16", "swir22"],
    "60m": ["coastal", "nir09"],
    "quality": ["scl", "aot", "wvp", "cloud", "snow"],
}
GROUPS = ["10m", "20m", "60m", "quality", "all"]
MODES = ["vsicurl", "whole-object"]
DEFAULT_TILE = "17SKU"
DEFAULT_DATE = "2025-10-15"
GDAL_ENV = {
    "CPL_DEBUG": "ON",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
}


# ---------------------------------------------------------------- pure helpers


def group_assets(group: str) -> list[str]:
    """Asset keys of a band group. `all` is every group in order."""
    if group == "all":
        return [key for name in ("10m", "20m", "60m", "quality") for key in BAND_GROUPS[name]]
    if group not in BAND_GROUPS:
        raise ValueError(f"unknown group {group}")
    return list(BAND_GROUPS[group])


def resolve_assets(item: dict, keys: list[str]) -> dict:
    """Hrefs and declared properties of the requested GeoTIFF assets.

    Keys the item lacks are listed under `missing`. Assets that are not GeoTIFFs served over
    HTTPS, such as JPEG 2000 links into another bucket, are listed under `skipped` and not read.
    """
    assets, missing, skipped = [], [], []
    for key in keys:
        asset = item.get("assets", {}).get(key)
        if not asset or "href" not in asset:
            missing.append(key)
            continue
        reason = unreadable_reason(asset)
        if reason:
            skipped.append({"key": key, "href": asset["href"], "reason": reason})
            continue
        bands = asset.get("raster:bands") or [{}]
        assets.append(
            {
                "key": key,
                "href": asset["href"],
                "gsd": asset.get("gsd") or bands[0].get("spatial_resolution"),
                "file_size": asset.get("file:size"),
                "media_type": asset.get("type"),
                "scale": bands[0].get("scale"),
                "offset": bands[0].get("offset"),
                "nodata": bands[0].get("nodata"),
            }
        )
    return {"assets": assets, "missing": missing, "skipped": skipped}


def unreadable_reason(asset: dict) -> str | None:
    """Why an asset is outside stage 1: not HTTPS, or not a GeoTIFF."""
    href = asset["href"]
    media = (asset.get("type") or "").lower()
    if not href.startswith("https://") and "://" in href:
        return f"href scheme {href.split('://', 1)[0]} is outside this HTTPS GeoTIFF benchmark"
    if media and "tiff" not in media:
        return f"media type {asset.get('type')} is not GeoTIFF, outside this benchmark"
    if not media and not href.lower().endswith((".tif", ".tiff")):
        return "no media type and the href is not a .tif"
    return None


def trim_item(item: dict) -> dict:
    props = item.get("properties", {})
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "datetime": props.get("datetime"),
        "platform": props.get("platform"),
        "product_uri": props.get("s2:product_uri"),
        "processing_baseline": props.get("s2:processing_baseline"),
        "sequence": props.get("s2:sequence"),
        "created": props.get("created"),
        "software": props.get("processing:software"),
        "boa_offset_applied": props.get("earthsearch:boa_offset_applied"),
        "requester_pays": props.get("storage:requester_pays"),
        "asset_keys": sorted(item.get("assets", {})),
    }


def pair_items(items_by_copy: dict[str, list[dict]]) -> tuple[dict[str, dict], str]:
    """One item per copy, preferring items that share an ESA product URI."""
    copies = list(items_by_copy)
    for copy in copies:
        if not items_by_copy[copy]:
            raise ValueError(f"no item returned for {copy}")
    uris = [
        {i.get("properties", {}).get("s2:product_uri") for i in items_by_copy[c]} for c in copies
    ]
    shared = set.intersection(*uris) - {None}
    if shared:
        uri = sorted(shared)[0]
        chosen = {
            c: next(i for i in items_by_copy[c] if i["properties"].get("s2:product_uri") == uri)
            for c in copies
        }
        return chosen, f"same ESA product on every copy: {uri}"
    chosen = {c: items_by_copy[c][0] for c in copies}
    return chosen, "no shared ESA product URI. First item per copy taken. Not the same product."


def plan_runs(copies: list[str], groups: list[str], modes: list[str], repeat: int) -> list[dict]:
    runs = []
    for group in groups:
        for copy in copies:
            for mode in modes:
                for repetition in range(1, repeat + 1):
                    runs.append(
                        {"copy": copy, "group": group, "mode": mode, "repetition": repetition}
                    )
    return runs


def read_seconds(run: dict) -> float:
    """Sum of the per-file open, read, fetch, and decode timers. Excludes digest and statistics."""
    keys = ("open_seconds", "read_seconds", "fetch_seconds", "decode_seconds")
    return round(sum(band.get(key, 0.0) for band in run["bands"] for key in keys), 3)


def summarize(results: list[dict]) -> dict:
    """Medians per copy, group, and mode, and whether both copies decoded to the same bytes."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for result in results:
        groups[(result["copy"], result["group"], result["mode"])].append(result)
    rows = []
    for (copy, group, mode), runs in sorted(groups.items()):
        ok = [r for r in runs if "error" not in r]
        row = {
            "copy": copy,
            "group": group,
            "mode": mode,
            "runs": len(runs),
            "failed": len(runs) - len(ok),
        }
        if ok:
            walls = [r["wall_seconds"] for r in ok]
            row.update(
                {
                    "wall_seconds_median": round(statistics.median(walls), 3),
                    "wall_seconds_min": round(min(walls), 3),
                    "wall_seconds_max": round(max(walls), 3),
                    "read_seconds_median": round(statistics.median(read_seconds(r) for r in ok), 3),
                    "bytes_requested_median": int(
                        statistics.median(r["totals"]["bytes_requested"] for r in ok)
                    ),
                    "requests_median": int(statistics.median(r["totals"]["requests"] for r in ok)),
                    "pixels": ok[0]["totals"]["pixels"],
                    "bytes_in_memory": ok[0]["totals"]["bytes_in_memory"],
                    "peak_rss_bytes_max": max(r["peak_rss_bytes"] for r in ok),
                    "cpu_seconds_median": round(
                        statistics.median(r["cpu"]["user"] + r["cpu"]["system"] for r in ok), 3
                    ),
                }
            )
        rows.append(row)
    digests: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for result in results:
        for band in result.get("bands", []):
            digests[band["key"]][result["copy"]].add(band["digest"])
    match = {}
    for key, by_copy in sorted(digests.items()):
        if len(by_copy) < 2:
            match[key] = None
        else:
            match[key] = len(set.union(*by_copy.values())) == 1
    return {"by_copy_group_mode": rows, "digest_match_by_band": match}


# ---------------------------------------------------------------- worker


def dataset_info(dataset) -> dict:
    return {
        "dtype": str(dataset.dtypes[0]),
        "width": dataset.width,
        "height": dataset.height,
        "nodata": dataset.nodata,
        "block_shape": list(dataset.block_shapes[0]),
        "compression": dataset.compression.value.lower() if dataset.compression else None,
        "overview_count": len(dataset.overviews(1)),
        "crs": str(dataset.crs) if dataset.crs else None,
        "transform": list(dataset.transform)[:6],
    }


def array_stats(array, nodata) -> dict:
    import numpy as np

    contiguous = np.ascontiguousarray(array)
    stats = {
        "pixels": int(array.size),
        "bytes_in_memory": int(array.nbytes),
        "digest": harness.sha256_bytes(memoryview(contiguous).cast("B")),
        "min": int(array.min()),
        "max": int(array.max()),
    }
    stats["nodata_count"] = int((array == nodata).sum()) if nodata is not None else None
    return stats


def read_with_gdal(href: str) -> tuple[dict, object]:
    import rasterio

    with harness.Timer() as open_timer:
        dataset = rasterio.open(href)
    with dataset:
        info = dataset_info(dataset)
        with harness.Timer() as read_timer:
            array = dataset.read(1)
    info.update({"open_seconds": open_timer.seconds, "read_seconds": read_timer.seconds})
    return info, array


def fetch_object(href: str, client: harness.Client) -> tuple[bytes, dict]:
    """The whole object. Local paths and file URLs read from disk, for fixture runs."""
    if href.startswith("file://"):
        href = href[len("file://") :]
    if "://" not in href:
        with harness.Timer() as timer:
            data = Path(href).read_bytes()
        return data, {"status": None, "bytes": len(data), "seconds": timer.seconds}
    return client.get_bytes(href, "whole object")


def read_from_bytes(data: bytes) -> tuple[dict, object]:
    from rasterio.io import MemoryFile

    with harness.Timer() as timer, MemoryFile(data) as memfile, memfile.open() as dataset:
        info = dataset_info(dataset)
        array = dataset.read(1)
    info["decode_seconds"] = timer.seconds
    return info, array


def run_worker(spec: dict) -> dict:
    """Read every asset of one run, holding the arrays until the run ends."""
    import rasterio

    started = harness.utc_now()
    net_before = harness.net_counters()
    cpu_before = harness.cpu_seconds()
    client = harness.Client(pause=0.0)
    bands, held = [], []
    with harness.Timer() as wall, rasterio.Env(**GDAL_ENV), harness.GdalLogCapture() as capture:
        for asset in spec["assets"]:
            record = {"key": asset["key"], "href": asset["href"], "gsd": asset.get("gsd")}
            if spec["mode"] == "vsicurl":
                info, array = read_with_gdal(asset["href"])
                gdal = harness.parse_gdal_log(capture.take())
                record.update(info)
                record.update(
                    {
                        "requests": gdal["requests"] + gdal["size_requests"],
                        "bytes_requested": gdal["bytes"],
                        "size_requests": gdal["size_requests"],
                    }
                )
            elif spec["mode"] == "whole-object":
                attempts_before = len(client.log)
                data, meta = fetch_object(asset["href"], client)
                info, array = read_from_bytes(data)
                del data
                capture.take()
                record.update(info)
                record.update(
                    {
                        "requests": len(client.log) - attempts_before,
                        "bytes_requested": meta["bytes"],
                        "fetch_seconds": meta["seconds"],
                        "http_status": meta["status"],
                        "content_length": meta.get("content_length"),
                        "request_charged": meta.get("request_charged"),
                    }
                )
            else:
                raise ValueError(f"unknown mode {spec['mode']}")
            record.update(array_stats(array, info.get("nodata")))
            held.append(array)
            bands.append(record)
    if spec.get("log_path"):
        Path(spec["log_path"]).write_text("\n".join(capture.all_lines) + "\n")
    held.clear()
    return {
        "copy": spec["copy"],
        "group": spec["group"],
        "mode": spec["mode"],
        "repetition": spec["repetition"],
        "started_at": started,
        "wall_seconds": wall.seconds,
        "cpu": harness.cpu_delta(cpu_before, harness.cpu_seconds()),
        "peak_rss_bytes": harness.peak_rss_bytes(),
        "net": harness.net_delta(net_before, harness.net_counters()),
        "bands": bands,
        "totals": {
            "bands": len(bands),
            "bytes_requested": sum(b["bytes_requested"] for b in bands),
            "requests": sum(b["requests"] for b in bands),
            "pixels": sum(b["pixels"] for b in bands),
            "bytes_in_memory": sum(b["bytes_in_memory"] for b in bands),
        },
        "gdal_env": GDAL_ENV,
        "http_log": client.log,
    }


# ---------------------------------------------------------------- parent


def search_items(client: harness.Client, collection: str, tile: str, date: str) -> list[dict]:
    body = {
        "collections": [collection],
        "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z",
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "limit": 10,
    }
    result = client.post_json(f"{ES_ROOT}/search", body, f"search {collection} {tile} {date}")
    return result.get("features", [])


def run_in_subprocess(spec: dict, spec_path: Path) -> dict:
    spec_path.write_text(json.dumps(spec))
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", str(spec_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            **{k: spec[k] for k in ("copy", "group", "mode", "repetition")},
            "error": completed.stderr[-3000:],
        }
    return json.loads(completed.stdout.strip().splitlines()[-1])


def reuse_mismatch(saved: dict, spec: dict) -> str | None:
    """Why a saved result cannot stand in for the requested run, or None when it can."""
    for key in ("copy", "group", "mode", "repetition"):
        if saved.get(key) != spec.get(key):
            return f"{key} differs"
    saved_assets = [(band.get("key"), band.get("href")) for band in saved.get("bands", [])]
    wanted = [(asset["key"], asset["href"]) for asset in spec["assets"]]
    if saved_assets != wanted:
        return "assets differ: another product, date, or band set"
    if saved.get("gdal_env") != GDAL_ENV:
        return "reader configuration differs"
    return None


def reusable_result(
    reuse_dir: Path | None, name: str, spec: dict
) -> tuple[dict | None, str | None]:
    """A saved, successful result for exactly this run, or None with the reason."""
    if reuse_dir is None:
        return None, None
    path = reuse_dir / f"{name}.result.json"
    if not path.exists():
        return None, None
    saved = json.loads(path.read_text())
    if "error" in saved:
        return None, "saved run failed"
    reason = reuse_mismatch(saved, spec)
    if reason:
        return None, reason
    saved["reused_from"] = str(path)
    return saved, None


def print_plan(runs: list[dict], groups: list[str]) -> None:
    print(f"{len(runs)} runs planned. Asset hrefs resolve from the catalog at run time.")
    for group in groups:
        print(f"  {group}: {', '.join(group_assets(group))}")
    for run in runs:
        print(f"  {run['copy']:6} {run['group']:8} {run['mode']:13} repetition {run['repetition']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tile", default=DEFAULT_TILE)
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--copies", nargs="+", default=list(COPIES), choices=list(COPIES))
    parser.add_argument("--groups", nargs="+", default=GROUPS, choices=GROUPS)
    parser.add_argument("--modes", nargs="+", default=MODES, choices=MODES)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks" / "results" / "raw-access.json"
    )
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw-access")
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds between catalog requests")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and contact nothing")
    parser.add_argument(
        "--reuse",
        type=Path,
        help="Raw directory of an interrupted run. Its saved successful runs are not repeated",
    )
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.worker:
        print(json.dumps(run_worker(json.loads(args.worker.read_text()))))
        return 0

    runs = plan_runs(args.copies, args.groups, args.modes, args.repeat)
    if args.dry_run:
        print_plan(runs, args.groups)
        return 0

    measured_at = harness.utc_now()
    raw_dir = args.raw_dir / measured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = harness.Client(pause=args.pause)
    items_by_copy = {
        copy: search_items(client, COPIES[copy]["collection"], args.tile, args.date)
        for copy in args.copies
    }
    chosen, pairing = pair_items(items_by_copy)
    print(f"raw access {measured_at}: {pairing}", flush=True)
    assets = {
        copy: {group: resolve_assets(chosen[copy], group_assets(group)) for group in args.groups}
        for copy in args.copies
    }
    for copy in args.copies:
        for group in args.groups:
            resolved = assets[copy][group]
            if resolved["missing"]:
                print(f"  {copy} {group}: missing {resolved['missing']}", flush=True)
            for skip in resolved["skipped"]:
                print(f"  {copy} {group}: skipping {skip['key']}, {skip['reason']}", flush=True)

    results = []
    for index, run in enumerate(runs, 1):
        name = f"{index:03d}-{run['copy']}-{run['group']}-{run['mode']}-{run['repetition']}"
        spec = {
            **run,
            "assets": assets[run["copy"]][run["group"]]["assets"],
            "log_path": str(raw_dir / f"{name}.gdal.log"),
        }
        result, reason = reusable_result(args.reuse, name, spec)
        if reason:
            print(f"  {name}: not reusing the saved result, {reason}", flush=True)
        if result is None:
            result = run_in_subprocess(spec, raw_dir / f"{name}.spec.json")
        (raw_dir / f"{name}.result.json").write_text(json.dumps(result, indent=1) + "\n")
        results.append(result)
        if "error" in result:
            print(f"{index}/{len(runs)} {name}: FAILED {result['error'][-200:]}", flush=True)
            continue
        totals = result["totals"]
        reused = " (reused)" if "reused_from" in result else ""
        print(
            f"{index}/{len(runs)} {name}{reused}: {result['wall_seconds']:.1f} s, "
            f"{totals['bytes_requested'] / 1e6:.1f} MB requested, {totals['requests']} requests, "
            f"peak {result['peak_rss_bytes'] / 1e9:.2f} GB",
            flush=True,
        )

    output = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": harness.code_version(),
        "script": "benchmarks/raw_access.py",
        "stage": "1, raw access to whole tiles",
        "machine": harness.machine_info(),
        "network": (
            "The owner's laptop over the internet, outside us-west-2. Transfer times include "
            "that path. Assumption A25. Repeat from us-west-2 when AWS access exists."
        ),
        "endpoints": {
            copy: {
                "label": COPIES[copy]["label"],
                "collection": COPIES[copy]["collection"],
                "bucket": COPIES[copy]["bucket"],
                "region": "us-west-2",
                "payer": (
                    "provider. Public bucket read with unsigned requests. The registry lists "
                    "RequesterPays false, finding F-22."
                ),
            }
            for copy in args.copies
        },
        "catalog": {"root": ES_ROOT, "tile": args.tile, "date": args.date, "pairing": pairing},
        "items": {copy: trim_item(chosen[copy]) for copy in args.copies},
        "assets": assets,
        "plan": {
            "copies": args.copies,
            "groups": args.groups,
            "modes": args.modes,
            "repeat": args.repeat,
            "runs": len(runs),
        },
        "runs": results,
        "reused_runs": sum(1 for r in results if "reused_from" in r),
        "reused_from": str(args.reuse) if args.reuse else None,
        "summary": summarize(results),
        "catalog_request_log": client.log,
        "raw_dir": str(raw_dir),
        "limitations": [
            "Runs on the owner's laptop over the internet, outside us-west-2. Every transfer "
            "time includes that path. Assumption A25.",
            "In vsicurl mode, requests and bytes come from GDAL's debug log of requested "
            "ranges, which is what the reader asked for, not what the network delivered. "
            "Network counters are machine-wide and include other traffic.",
            "Wall seconds per run include the digest and statistics of every array. The "
            "per-file open, read, fetch, and decode seconds exclude them. Whole-object "
            "requests count HTTP attempts, including retries.",
            "Every run is a fresh process, so GDAL caches start cold. Provider-side and "
            "operating-system caches are not controlled.",
            "One acquisition of one tile. Whole-tile reads only. No polygon, no extraction.",
            "Only GeoTIFF assets served over HTTPS are read. Assets the catalog links elsewhere, "
            "such as JPEG 2000 files in another bucket, are listed as skipped and not read.",
            "Digest equality between copies compares decoded integers. It says nothing about "
            "the offset state, scaling, or georeferencing.",
            "Peak memory is the worker's maximum resident set while it holds every array of "
            "the group.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=1) + "\n")
    failed = sum(1 for r in results if "error" in r)
    print(f"wrote {args.output}: {len(results)} runs, {failed} failed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
