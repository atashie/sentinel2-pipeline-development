"""Fallback survey: asset-level check of the older Earth Search collection at Collection 1 gaps.

Runs only when the user invokes it. Reads the tiles and their incomplete months from
benchmarks/results/gap-survey.json. For each tile and each contiguous span of incomplete months
it lists Collection 1 items, the older collection's items with their assets, and the Copernicus
reference. It classifies every older-collection item by which assets are cloud-optimized
GeoTIFFs in the public sentinel-cogs bucket, matches acquisitions, and sends HEAD requests for
a sample of those objects. Headers only. No pixel is read.

    uv run python benchmarks/fallback_survey.py
    uv run python benchmarks/fallback_survey.py --tiles 10SGJ --output data/smoke.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gap_survey as gs  # noqa: E402

REFLECTANCE_BANDS = [
    "coastal",
    "blue",
    "green",
    "red",
    "rededge1",
    "rededge2",
    "rededge3",
    "nir",
    "nir08",
    "nir09",
    "swir16",
    "swir22",
]
QUALITY_KEYS = ["scl", "aot", "wvp", "cloud", "snow"]
COG_HOST = "sentinel-cogs.s3.us-west-2.amazonaws.com"
HEAD_KEYS = ["scl", "red"]
INCOMPLETE = {"empty", "partial"}


# ---------------------------------------------------------------- pure helpers


def spans(months: list[str]) -> list[tuple[str, str]]:
    """Group sorted YYYY-MM months into contiguous (first, last) spans."""
    out: list[tuple[str, str]] = []
    for month in sorted(months):
        if out and gs.month_range(out[-1][1] + "-01", month + "-01") == [out[-1][1], month]:
            out[-1] = (out[-1][0], month)
        else:
            out.append((month, month))
    return out


def span_dates(first: str, last: str) -> tuple[str, str]:
    """First day of the first month and last day of the last month."""
    year, month = int(last[:4]), int(last[5:7])
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    last_day = date(next_year, next_month, 1) - timedelta(days=1)
    return f"{first}-01", last_day.isoformat()


def is_cog(asset: dict) -> bool:
    kind = asset.get("type") or ""
    href = asset.get("href") or ""
    return "cloud-optimized" in kind and urllib.parse.urlparse(href).netloc == COG_HOST


def classify_assets(feature: dict) -> dict:
    """Which assets of one older-collection item are GeoTIFFs in the public bucket."""
    assets = feature.get("assets", {})
    props = feature.get("properties", {})
    cog = sorted(k for k, a in assets.items() if is_cog(a))
    jp2 = sorted(k for k, a in assets.items() if (a.get("type") or "") == "image/jp2")
    hosts = Counter(urllib.parse.urlparse(a.get("href") or "").netloc for a in assets.values())
    bands_cog = [b for b in REFLECTANCE_BANDS if b in cog]
    quality = {}
    for key in QUALITY_KEYS:
        asset = assets.get(key)
        if asset is None:
            quality[key] = None
        else:
            quality[key] = (
                "cog"
                if is_cog(asset)
                else ("jp2" if "jp2" in (asset.get("type") or "") else "other")
            )
    red = (assets.get("red", {}).get("raster:bands") or [{}])[0]
    return {
        "id": feature["id"],
        "datetime": props.get("datetime", ""),
        "platform": gs.platform_letter(props.get("platform"), feature["id"]),
        "baseline": props.get("s2:processing_baseline"),
        "sequence": props.get("s2:sequence"),
        "software": json.dumps(props.get("processing:software"), sort_keys=True)
        if props.get("processing:software")
        else None,
        "offset_applied": props.get("earthsearch:boa_offset_applied"),
        "created": props.get("created"),
        "cog_assets": cog,
        "jp2_assets": jp2,
        "hosts": dict(hosts),
        "bands_cog": len(bands_cog),
        "bands_cog_complete": len(bands_cog) == len(REFLECTANCE_BANDS),
        "quality": quality,
        "red_scale": red.get("scale"),
        "red_offset": red.get("offset"),
        "urls": {k: assets[k].get("href") for k in HEAD_KEYS if k in assets},
    }


def coverage_class(items: list[dict]) -> str:
    """Best fallback class among the older-collection items of one acquisition."""
    if not items:
        return "none"
    if any(i["bands_cog_complete"] and i["quality"]["scl"] == "cog" for i in items):
        return "complete_cog"
    if any(i["cog_assets"] for i in items):
        return "partial_cog"
    if any(i["jp2_assets"] for i in items):
        return "jp2_only"
    return "no_data_assets"


def best_item(items: list[dict]) -> dict | None:
    """The item a fill would use, a survey heuristic and not a product selection rule.

    Order: a complete GeoTIFF set with the scene classification first, then the larger count
    of GeoTIFF assets, then the higher baseline string. The asset count is a deliberate
    second preference. The fill policy decides product selection.
    """
    ranked = sorted(
        items,
        key=lambda i: (
            i["bands_cog_complete"] and i["quality"]["scl"] == "cog",
            len(i["cog_assets"]),
            str(i["baseline"]),
        ),
        reverse=True,
    )
    return ranked[0] if ranked else None


# ---------------------------------------------------------------- HTTP


def head(client: gs.Client, url: str, note: str) -> dict:
    """HEAD one object without credentials. Headers only. Counted like any other request."""
    host = urllib.parse.urlparse(url).netloc
    delay = 1.0
    for attempt in range(1, client.retries + 1):
        request = urllib.request.Request(url, method="HEAD", headers={"user-agent": gs.USER_AGENT})
        started = time.perf_counter()
        status, headers, failed = None, {}, False
        try:
            with urllib.request.urlopen(request, timeout=client.timeout) as response:
                status, headers = response.status, dict(response.headers)
        except urllib.error.HTTPError as error:
            status, headers = error.code, dict(error.headers)
            failed = status in (408, 425, 429, 500, 502, 503, 504)
        except (urllib.error.URLError, TimeoutError) as error:
            headers, failed = {"error": str(error)}, True
        client.requests[host] += 1
        client.log.append(
            {
                "host": host,
                "method": "HEAD",
                "path": url[len(f"https://{host}") :],
                "note": note,
                "status": status,
                "bytes": 0,
                "seconds": round(time.perf_counter() - started, 3),
                "attempt": attempt,
            }
        )
        if failed and attempt < client.retries:
            time.sleep(delay)
            delay *= 2
            continue
        time.sleep(client.pause)
        lower = {k.lower(): v for k, v in headers.items()}
        return {
            "url": url,
            "status": status,
            "content_length": int(lower["content-length"]) if "content-length" in lower else None,
            "etag": lower.get("etag"),
            "last_modified": lower.get("last-modified"),
            "storage_class": lower.get("x-amz-storage-class"),
            "content_type": lower.get("content-type"),
            "request_charged": lower.get("x-amz-request-charged"),
            "error": lower.get("error"),
        }
    raise RuntimeError("unreachable")


def list_older_with_assets(client, tile, start, end):
    body = {
        "collections": [gs.FALLBACK],
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "datetime": gs.window_datetime(start, end),
        "limit": gs.PAGE_LIMIT,
        "fields": {
            "include": [*gs.ITEM_FIELDS, "assets"],
            "exclude": ["geometry", "bbox", "links"],
        },
    }
    return gs.paged_search(client, gs.ES_ROOT, body, f"older+assets {tile}")


# ---------------------------------------------------------------- survey


def survey_tile(client, tile, months, raw_dir: Path, head_per_month: int) -> dict:
    record: dict = {"incomplete_months": months, "spans": [], "monthly": {}, "head_sample": []}
    c1_items, older_features, ref_items = [], [], []
    for first, last in spans(months):
        start, end = span_dates(first, last)
        record["spans"].append([first, last])
        c1_items += [gs.normalize_es(f) for f in gs.es_list(client, gs.PRIMARY, tile, start, end)]
        older_features += list_older_with_assets(client, tile, start, end)
        for year in sorted({int(m[:4]) for m in gs.month_range(start, end)}):
            ref_items += [
                gs.normalize_cdse(f) for f in gs.cdse_list(client, tile, year, start, end)
            ]
    raw_path = raw_dir / f"{tile}-older-with-assets.json"
    raw_path.write_text(json.dumps(older_features, separators=(",", ":")))
    record["raw_file"] = {"path": str(raw_path), "sha256": gs.sha256_file(raw_path)}
    older = [classify_assets(f) for f in older_features]
    by_key: dict[str, list[dict]] = defaultdict(list)
    for item in older:
        by_key[gs.sensing_key(item)].append(item)
    c1_keys = {gs.sensing_key(i) for i in c1_items}
    ref_keys = {gs.sensing_key(i) for i in ref_items}
    totals = Counter()
    for month in months:
        ref_m = {k for k in ref_keys if k.startswith(month)}
        c1_m = {k for k in c1_keys if k.startswith(month)}
        missing = sorted(ref_m - c1_m)
        classes = Counter()
        used: list[dict] = []
        for key in missing:
            cls = coverage_class(by_key.get(key, []))
            classes[cls] += 1
            item = best_item(by_key.get(key, []))
            if item:
                used.append(item)
        row = {
            "reference": len(ref_m),
            "primary": len(c1_m),
            "missing": len(missing),
            "complete_cog": classes["complete_cog"],
            "partial_cog": classes["partial_cog"],
            "jp2_only": classes["jp2_only"],
            "no_data_assets": classes["no_data_assets"],
            "uncovered": classes["none"],
            "older_items": sum(1 for i in older if i["datetime"][:7] == month),
            "older_not_in_reference": len({k for k in by_key if k.startswith(month)} - ref_m),
            "fallback_baselines": gs._counter_dict(i["baseline"] for i in used),
            "fallback_offset_flags": gs._counter_dict(i["offset_applied"] for i in used),
            "fallback_software": gs._counter_dict(i["software"] for i in used),
            "fallback_full_cog": sum(
                1
                for i in used
                if i["bands_cog_complete"]
                and all(i["quality"][k] == "cog" for k in ("scl", "aot", "wvp"))
            ),
            "fallback_cloud_snow": gs._counter_dict(
                f"{i['quality']['cloud']}/{i['quality']['snow']}" for i in used
            ),
            "fallback_red_offset": gs._counter_dict(i["red_offset"] for i in used),
        }
        record["monthly"][month] = row
        for key in (
            "reference",
            "primary",
            "missing",
            "complete_cog",
            "partial_cog",
            "jp2_only",
            "uncovered",
        ):
            totals[key] += row[key]
        sample = [i for i in used if i["bands_cog_complete"] and i["quality"]["scl"] == "cog"][
            :head_per_month
        ]
        for item in sample:
            for key in HEAD_KEYS:
                url = item["urls"].get(key)
                if url and url.startswith("https://"):
                    result = head(client, url, f"head {tile} {month} {key}")
                    result.update(
                        {
                            "item_id": item["id"],
                            "asset": key,
                            "month": month,
                            "baseline": item["baseline"],
                            "offset_applied": item["offset_applied"],
                        }
                    )
                    record["head_sample"].append(result)
    record["totals"] = dict(totals)
    record["head_status"] = gs._counter_dict(h["status"] for h in record["head_sample"])
    print(
        f"  {tile}: {len(months)} months, missing {totals['missing']}, complete GeoTIFF fallback "
        f"{totals['complete_cog']}, uncovered {totals['uncovered']}, HEAD {record['head_status']}",
        flush=True,
    )
    return record


def summarize(tiles: dict) -> dict:
    totals = Counter()
    by_month = defaultdict(Counter)
    baselines = Counter()
    flags = Counter()
    software = Counter()
    cloud_snow = Counter()
    head_status = Counter()
    sizes = defaultdict(list)
    for record in tiles.values():
        for key, value in record["totals"].items():
            totals[key] += value
        for month, row in record["monthly"].items():
            for key in (
                "reference",
                "primary",
                "missing",
                "complete_cog",
                "partial_cog",
                "jp2_only",
                "uncovered",
            ):
                by_month[month][key] += row[key]
            baselines.update(row["fallback_baselines"])
            flags.update(row["fallback_offset_flags"])
            software.update(row["fallback_software"])
            cloud_snow.update(row["fallback_cloud_snow"])
        for h in record["head_sample"]:
            head_status[str(h["status"])] += 1
            if h["content_length"]:
                sizes[h["asset"]].append(h["content_length"])
    return {
        "tiles": len(tiles),
        "totals": dict(totals),
        "by_month": {m: dict(c) for m, c in sorted(by_month.items())},
        "fallback_baselines": dict(sorted(baselines.items())),
        "fallback_offset_flags": dict(sorted(flags.items())),
        "fallback_software": dict(sorted(software.items())),
        "fallback_cloud_snow": dict(sorted(cloud_snow.items())),
        "head_requests": sum(head_status.values()),
        "head_status": dict(sorted(head_status.items())),
        "head_content_length_bytes": {
            k: {"min": min(v), "max": max(v), "count": len(v)} for k, v in sorted(sizes.items())
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--gap-survey", type=Path, default=Path("benchmarks/results/gap-survey.json")
    )
    parser.add_argument("--tiles", nargs="*", help="Survey only these tiles from the gap survey")
    parser.add_argument(
        "--head-per-month", type=int, default=1, help="Items to HEAD per tile and month"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("benchmarks/results/fallback-survey.json")
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("data/fallback-survey"))
    parser.add_argument("--pause", type=float, default=0.2)
    args = parser.parse_args(argv)

    measured_at = datetime.now(UTC).isoformat(timespec="seconds")
    survey = json.loads(args.gap_survey.read_text())
    months = survey["window"]["months"]
    raw_dir = args.raw_dir / measured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = gs.Client(pause=args.pause)
    selected = {t: r for t, r in survey["tiles"].items() if not args.tiles or t in args.tiles}
    print(
        f"fallback survey {measured_at}: {len(selected)} tiles from {args.gap_survey}", flush=True
    )
    tiles = {}
    for tile, record in selected.items():
        incomplete = [
            m for m, s in zip(months, record["gaps"]["status"], strict=True) if s in INCOMPLETE
        ]
        if not incomplete:
            print(f"  {tile}: no incomplete month", flush=True)
            continue
        tiles[tile] = survey_tile(client, tile, incomplete, raw_dir, args.head_per_month)
        tiles[tile]["sites"] = record["sites"]
    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": gs.code_version(),
        "script": "benchmarks/fallback_survey.py",
        "input": {
            "path": str(args.gap_survey),
            "sha256": gs.sha256_file(args.gap_survey),
            "measured_at": survey["measured_at"],
        },
        "definitions": {
            "incomplete_month": "A month whose gap survey status is empty or partial for the tile.",
            "complete_cog": "An acquisition Collection 1 lacks, where an older-collection item has "
            "all twelve reflectance bands and the scene classification as cloud-optimized GeoTIFFs "
            "in the sentinel-cogs bucket.",
            "partial_cog": "Some GeoTIFF assets in that bucket, but not the full set.",
            "jp2_only": "Only JPEG 2000 assets, which point into the Sinergise bucket.",
            "uncovered": "No older-collection item for the acquisition.",
            "fallback_full_cog": "Best item also has aerosol and water vapour as GeoTIFFs.",
            "reflectance_bands": REFLECTANCE_BANDS,
            "head_sample": "Per tile and month, the first complete_cog item's scene classification "
            "and red band objects, HEAD without credentials.",
        },
        "endpoints": {
            "earth_search": survey["endpoints"]["earth_search"],
            "cdse_stac": survey["endpoints"]["cdse_stac"],
            "sentinel_cogs_bucket": {
                "host": COG_HOST,
                "region": "us-west-2",
                "payer": "Unsigned HEAD requests answered. No x-amz-request-charged header seen "
                "means the requester was not charged. Bytes transferred: headers only",
                "role": "the older collection's GeoTIFF store, the fallback of decision 0003",
            },
        },
        "requests": {
            "by_host": dict(client.requests),
            "bytes_received_by_host": dict(client.bytes),
            "imagery_bytes": 0,
            "total": sum(client.requests.values()),
        },
        "tiles": tiles,
        "summary": summarize(tiles),
        "raw_listing_dir": str(raw_dir),
        "request_log": client.log,
        "limitations": [
            "Headers only. A 200 to HEAD shows the object exists and its size. It shows nothing "
            "about the pixels or the offset state.",
            "One item per tile and month was HEAD-checked, two objects each. Other objects of the "
            "same item and other items are assumed to match their catalog entries.",
            "Asset classes come from catalog media types and hosts. A catalog entry can be stale.",
            "Only months the gap survey marked empty or partial are surveyed. Months marked "
            "complete are not rechecked here.",
            "Sensing keys pair date and platform, as in the gap survey.",
            "Counts describe the catalogs and bucket at measured_at.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {args.output}: {result['requests']['total']} requests", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
