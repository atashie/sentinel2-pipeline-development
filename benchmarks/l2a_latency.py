"""Sen2Cor latency: time from sensing to each clock of the Earth Search Level-2A copies.

Runs only when the user invokes it. Metadata only, unsigned, no credentials. For each lower-48
tile of probe T2 it lists the Earth Search items of both Level-2A collections, the Copernicus
OData Level-2A products, and every object of both public GeoTIFF buckets for the window's
months. It reads no object body and no pixel.

The window and tiles come from benchmarks/results/aqr-coverage.json, so the bucket clock
matches finding 27's ACOLITE latency. Each Earth Search item is timed against its product's
sensing start: ESA generation, Copernicus origin and publication, the Earth Search catalog
record, and the first and last object in its bucket folder.

    uv run python benchmarks/l2a_latency.py --dry-run
    uv run python benchmarks/l2a_latency.py
    uv run python benchmarks/l2a_latency.py --from-raw data/l2a-latency/STAMP
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))
import gap_survey as gs  # noqa: E402

from s2proto import aqr, harness  # noqa: E402

AQR_COVERAGE = ROOT / "benchmarks" / "results" / "aqr-coverage.json"
C1 = "sentinel-2-c1-l2a"
OLDER = "sentinel-2-l2a"
COLLECTIONS = [C1, OLDER]
REGION = "us-west-2"
BUCKETS = {
    C1: {"bucket": "e84-earth-search-sentinel-data", "prefix": "sentinel-2-c1-l2a"},
    OLDER: {"bucket": "sentinel-cogs", "prefix": "sentinel-s2-l2a-cogs"},
}
CLOCKS = [
    "esa_generation",
    "esa_origin",
    "cdse_publication",
    "catalog_created",
    "bucket_first",
    "bucket_last",
]
WITHIN_HOURS = (6, 12, 24, 72)
SLOWEST = 15
ODATA_SELECT = "Name,OriginDate,PublicationDate,ModificationDate,ContentDate,Online"
TILE_PATTERN = re.compile(r"^(?P<zone>\d{1,2})(?P<band>[C-X])(?P<square>[A-Z]{2})$")


def window_from_coverage(coverage: dict) -> dict:
    """Tiles, sensing window, and observation cutoff of finding 27's recent latency."""
    starts = {t["latency_recent"]["sensed_from"] for t in coverage["tiles"]}
    if len(starts) != 1:
        raise ValueError(f"tiles disagree on the recent window: {sorted(starts)}")
    return {
        "tiles": list(coverage["tiles_inside"]),
        "start": starts.pop(),
        "end": coverage["window"]["end"],
        "cutoff": coverage["measured_at"],
    }


def tile_prefix(tile: str) -> str:
    """10SEJ as 10/S/EJ, the bucket folder of one tile."""
    found = TILE_PATTERN.match(tile)
    if not found:
        raise ValueError(f"not an MGRS tile: {tile}")
    return f"{int(found['zone'])}/{found['band']}/{found['square']}"


def month_prefixes(collection: str, tile: str, start: str, end: str) -> list[str]:
    """Bucket prefixes of one tile for each month of the window. Months are not zero-padded."""
    base = f"{BUCKETS[collection]['prefix']}/{tile_prefix(tile)}"
    return [f"{base}/{m[:4]}/{int(m[5:])}/" for m in gs.month_range(start, end)]


def list_url(bucket: str, prefix: str, token: str | None = None) -> str:
    """ListObjectsV2 URL for an unsigned request."""
    query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if token:
        query["continuation-token"] = token
    return f"https://{bucket}.s3.{REGION}.amazonaws.com/?{urllib.parse.urlencode(query)}"


def odata_url(tile: str, start: str, end: str) -> str:
    query = (
        "Collection/Name eq 'SENTINEL-2' and contains(Name,'MSIL2A') and "
        f"contains(Name,'_T{tile}_') and ContentDate/Start ge {start}T00:00:00.000Z "
        f"and ContentDate/Start le {end}T23:59:59.999Z"
    )
    params = {
        "$filter": query,
        "$select": ODATA_SELECT,
        "$orderby": "ContentDate/Start asc",
        "$top": 1000,
    }
    return f"{gs.CDSE_ODATA}?{urllib.parse.urlencode(params)}"


def plan(meta: dict, output: Path) -> list[str]:
    tiles = meta["tiles"]
    months = gs.month_range(meta["start"], meta["end"])
    return [
        f"Sensing window {meta['start']} to {meta['end']}, from {AQR_COVERAGE.name}.",
        f"Matched cutoff {meta['cutoff']}, when finding 27's listing ran.",
        f"{len(tiles)} lower-48 tiles: {', '.join(tiles)}.",
        f"1. Earth Search, per tile: paged item listings in {', '.join(COLLECTIONS)}.",
        "2. Copernicus OData, per tile: Level-2A product names, origin and publication times.",
        f"3. Buckets in {REGION}, unsigned, per tile and month ({len(months)} months):",
        *(f"   {BUCKETS[c]['bucket']}/{BUCKETS[c]['prefix']}/<zone>/<band>/<sq>/" for c in BUCKETS),
        "No object body is read. No pixel is read. Raw listings go under data/l2a-latency/.",
        f"Writes {output}.",
    ]


# ---------------------------------------------------------------- collection


def list_all(client, bucket: str, prefix: str, note: str) -> list[dict]:
    keys: list[dict] = []
    token = None
    page = 0
    while True:
        page += 1
        text, _ = client.get_text(list_url(bucket, prefix, token), f"{note} page {page}")
        listing = aqr.parse_listing(text)
        keys.extend(listing["keys"])
        if not listing["truncated"]:
            return keys
        token = listing["next_token"]


def odata_list(client, tile: str, start: str, end: str) -> list[dict]:
    products: list[dict] = []
    url = odata_url(tile, start, end)
    page = 0
    while url:
        page += 1
        result = client.get_json(url, None, f"odata {tile} page {page}")
        products.extend(result.get("value", []))
        url = result.get("@odata.nextLink")
    return products


def collect(meta: dict, raw_dir: Path) -> dict:
    es = gs.Client(pause=0.2)
    s3 = harness.Client(pause=0.05)
    for tile in meta["tiles"]:
        for collection in COLLECTIONS:
            features = gs.es_list(es, collection, tile, meta["start"], meta["end"])
            (raw_dir / f"es-{tile}-{collection}.json").write_text(
                json.dumps(features, separators=(",", ":"))
            )
            keys: list[dict] = []
            for prefix in month_prefixes(collection, tile, meta["start"], meta["end"]):
                keys.extend(list_all(s3, BUCKETS[collection]["bucket"], prefix, f"s3 {prefix}"))
            (raw_dir / f"s3-{tile}-{collection}.json").write_text(
                json.dumps(keys, separators=(",", ":"))
            )
            print(f"{tile} {collection}: {len(features)} items, {len(keys)} objects", flush=True)
        products = odata_list(es, tile, meta["start"], meta["end"])
        (raw_dir / f"cdse-{tile}.json").write_text(json.dumps(products, separators=(",", ":")))
        print(f"{tile} cdse: {len(products)} products", flush=True)
    return {"earth_search_and_cdse": es.log, "s3": s3.log}


# ---------------------------------------------------------------- analysis


def folders(keys: list[dict]) -> dict[str, dict]:
    """Earliest and latest last-modified time per item folder of one bucket listing."""
    out: dict[str, dict] = {}
    for entry in keys:
        parts = entry["key"].split("/")
        if len(parts) < 2 or not entry["last_modified"]:
            continue
        folder = out.setdefault(parts[-2], {"first": None, "last": None, "objects": 0})
        stamp = entry["last_modified"]
        folder["objects"] += 1
        folder["first"] = min(folder["first"] or stamp, stamp)
        folder["last"] = max(folder["last"] or stamp, stamp)
    return out


def product_fields(name: str | None) -> dict | None:
    fields = aqr.parse_product((name or "").removesuffix(".SAFE"))
    if fields is None:
        return None
    return fields | {"sensing_time": aqr.compact_time(fields["sensing"])}


def pass_key(fields: dict) -> tuple[str, str, str]:
    return fields["tile"], fields["platform"], fields["sensing"]


def hours_or_none(start: str | None, end: str | None) -> float | None:
    return aqr.hours_between(start, end) if start and end else None


def item_record(item: dict, folder: dict | None, cdse: dict | None) -> dict:
    """One Earth Search item's clocks, in hours after its product's sensing start."""
    fields = product_fields(item["product_uri"])
    sensing = fields["sensing_time"] if fields else item["datetime"] or None
    times = {
        "esa_generation": item["generation_time"],
        "esa_origin": cdse.get("OriginDate") if cdse else None,
        "cdse_publication": cdse.get("PublicationDate") if cdse else None,
        "catalog_created": item["created"],
        "bucket_first": folder["first"] if folder else None,
        "bucket_last": folder["last"] if folder else None,
    }
    hours = {clock: hours_or_none(sensing, times[clock]) for clock in CLOCKS}
    return {
        "id": item["id"],
        "product": (item["product_uri"] or "").removesuffix(".SAFE") or None,
        "sensing_time": sensing,
        "sensing_source": "product_name" if fields else "item_datetime",
        "sequence": item["sequence"],
        "baseline": item["baseline"],
        "objects": folder["objects"] if folder else 0,
        "times": times,
        "hours": hours,
        "after_cdse_publication_hours": hours_or_none(
            times["cdse_publication"], times["bucket_first"]
        ),
    }


def in_window(sensing: str | None, start: str, end: str) -> bool:
    return bool(sensing) and start <= sensing[:10] <= end


def product_name(entry: dict) -> str:
    return entry["product"]


def cdse_status(products: list[dict], records: list[dict], measured_at: str) -> dict:
    """Whether each Copernicus product of the window has an Earth Search item at run time."""
    names = {r["product"] for r in records if r["product"]}
    passes = {pass_key(f) for r in records if (f := product_fields(r["product"]))}
    counts: Counter = Counter()
    absent = []
    for product in products:
        name = product["Name"].removesuffix(".SAFE")
        fields = product_fields(name)
        if name in names:
            counts["same_product"] += 1
        elif fields and pass_key(fields) in passes:
            counts["pass_other_product"] += 1
        else:
            counts["absent"] += 1
            sensing = fields["sensing_time"] if fields else product["ContentDate"]["Start"]
            absent.append(
                {
                    "product": name,
                    "publication": product.get("PublicationDate"),
                    "age_days_at_run": round(aqr.hours_between(sensing, measured_at) / 24, 2),
                }
            )
    return {"counts": dict(sorted(counts.items())), "absent": sorted(absent, key=product_name)}


def analyze_tile(tile: str, raw: dict, meta: dict) -> dict:
    cdse = [
        p
        for p in raw["cdse"]
        if (f := product_fields(p["Name"]))
        and f["tile"] == tile
        and in_window(f["sensing_time"], meta["start"], meta["end"])
    ]
    by_name = {p["Name"].removesuffix(".SAFE"): p for p in cdse}
    out: dict = {"tile": tile, "cdse_products": len(cdse), "collections": {}}
    for collection in COLLECTIONS:
        found = folders(raw["s3"][collection])
        records = []
        outside = 0
        for feature in raw["es"][collection]:
            item = gs.normalize_es(feature)
            if item["tile"] != tile:
                continue
            record = item_record(
                item,
                found.get(item["id"]),
                by_name.get((item["product_uri"] or "").removesuffix(".SAFE")),
            )
            if not in_window(record["sensing_time"], meta["start"], meta["end"]):
                outside += 1
                continue
            records.append(record)
        out["collections"][collection] = {
            "records": records,
            "items_outside_window": outside,
            "folders_without_item": len(set(found) - {r["id"] for r in records}),
            "cdse_status": cdse_status(cdse, records, meta["measured_at"]),
        }
    return out


def stats(hours: list[float], days: bool = True) -> dict:
    """Nearest-rank percentiles, as finding 27 used, in days or in signed hours."""
    if not hours:
        return {"n": 0}
    values = [h / 24 for h in hours] if days else list(hours)
    unit = "days" if days else "hours"
    out = {"n": len(values)}
    for label, fraction in (("p10", 0.1), ("median", 0.5), ("p90", 0.9), ("p99", 0.99)):
        out[f"{label}_{unit}"] = round(aqr.percentile(values, fraction), 2)
    out[f"min_{unit}"] = round(min(values), 2)
    out[f"max_{unit}"] = round(max(values), 2)
    return out


def within(hours: list[float], denominator: int) -> dict:
    """Share of `denominator` products whose hours are at or under each threshold."""
    if not denominator:
        return {}
    return {f"{h}h": round(sum(1 for v in hours if v <= h) / denominator, 4) for h in WITHIN_HOURS}


def summarize(records: list[dict], status: Counter, cdse_total: int, cutoff: str) -> dict:
    by_clock = {c: [r["hours"][c] for r in records if r["hours"][c] is not None] for c in CLOCKS}
    matched_first = [
        r["hours"]["bucket_first"]
        for r in records
        if r["times"]["bucket_first"] and aqr.hours_between(r["times"]["bucket_first"], cutoff) >= 0
    ]
    # One value per Copernicus product, the earliest of any items that carry its name.
    first_by_product: dict[str, float] = {}
    for r in records:
        hours = r["hours"]["bucket_first"]
        if r["times"]["cdse_publication"] and hours is not None:
            first_by_product[r["product"]] = min(hours, first_by_product.get(r["product"], hours))
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in records:
        if r["hours"]["bucket_first"] is not None:
            by_month[r["sensing_time"][:7]].append(r["hours"]["bucket_first"])
    slowest = sorted(
        (r for r in records if r["hours"]["bucket_first"] is not None),
        key=lambda r: -r["hours"]["bucket_first"],
    )[:SLOWEST]
    return {
        "items": len(records),
        "items_without_product_name": sum(1 for r in records if not r["product"]),
        "items_matched_to_cdse": sum(1 for r in records if r["times"]["cdse_publication"]),
        "items_without_bucket_objects": sum(1 for r in records if not r["objects"]),
        "objects_per_item": aqr.counter_dict(r["objects"] for r in records),
        "sequences": aqr.counter_dict(r["sequence"] for r in records),
        "baselines": aqr.counter_dict(r["baseline"] for r in records),
        "latency": {c: stats(v) for c, v in by_clock.items()},
        "bucket_first_after_cdse_publication": stats(
            [
                r["after_cdse_publication_hours"]
                for r in records
                if r["after_cdse_publication_hours"] is not None
            ],
            days=False,
        ),
        "bucket_first_matched_cutoff": stats(matched_first) | {"cutoff": cutoff},
        "bucket_first_by_sensing_month": {m: stats(v) for m, v in sorted(by_month.items())},
        "cdse_products": cdse_total,
        "cdse_status": dict(sorted(status.items())),
        "share_of_cdse_products_in_bucket_within": within(
            list(first_by_product.values()), cdse_total
        ),
        "slowest_bucket_first": [
            {
                "id": r["id"],
                "product": r["product"],
                "bucket_first_days": round(r["hours"]["bucket_first"] / 24, 2),
                "catalog_created_days": (
                    round(r["hours"]["catalog_created"] / 24, 2)
                    if r["hours"]["catalog_created"] is not None
                    else None
                ),
                "cdse_publication_days": (
                    round(r["hours"]["cdse_publication"] / 24, 2)
                    if r["hours"]["cdse_publication"] is not None
                    else None
                ),
            }
            for r in slowest
        ],
    }


def analyze(raw_dir: Path, meta: dict) -> dict:
    tiles = []
    for tile in meta["tiles"]:
        raw = {
            "cdse": json.loads((raw_dir / f"cdse-{tile}.json").read_text()),
            "es": {
                c: json.loads((raw_dir / f"es-{tile}-{c}.json").read_text()) for c in COLLECTIONS
            },
            "s3": {
                c: json.loads((raw_dir / f"s3-{tile}-{c}.json").read_text()) for c in COLLECTIONS
            },
        }
        tiles.append(analyze_tile(tile, raw, meta))
    summary = {}
    for collection in COLLECTIONS:
        records = [r for t in tiles for r in t["collections"][collection]["records"]]
        status: Counter = Counter()
        absent = []
        for t in tiles:
            entry = t["collections"][collection]["cdse_status"]
            status.update(entry["counts"])
            absent.extend(entry["absent"])
        summary[collection] = summarize(
            records, status, sum(t["cdse_products"] for t in tiles), meta["cutoff"]
        ) | {
            "items_outside_window": sum(
                t["collections"][collection]["items_outside_window"] for t in tiles
            ),
            "folders_without_item": sum(
                t["collections"][collection]["folders_without_item"] for t in tiles
            ),
            "cdse_absent": sorted(absent, key=product_name),
        }
    per_tile = []
    for t in tiles:
        row = {"tile": t["tile"], "cdse_products": t["cdse_products"]}
        for collection in COLLECTIONS:
            records = t["collections"][collection]["records"]
            first = [
                r["hours"]["bucket_first"]
                for r in records
                if r["hours"]["bucket_first"] is not None
            ]
            row[collection] = stats(first) | {
                "cdse_status": t["collections"][collection]["cdse_status"]["counts"]
            }
        per_tile.append(row)
    raw_files = {
        path.name: gs.sha256_file(path)
        for path in sorted(raw_dir.glob("*.json"))
        if path.name != "meta.json"
    }
    items = {
        c: [
            {
                k: r[k]
                for k in ("id", "product", "sensing_time", "sensing_source", "objects", "times")
            }
            for t in tiles
            for r in t["collections"][c]["records"]
        ]
        for c in COLLECTIONS
    }
    return {"summary": summary, "tiles": per_tile, "items": items, "raw_files": raw_files}


def acolite_reference(coverage: dict) -> dict:
    """Finding 27's ACOLITE latency, copied from its result file for side-by-side reading."""
    return {
        "source": "benchmarks/results/aqr-coverage.json",
        "measured_at": coverage["measured_at"],
        "sensed_from": coverage["tiles"][0]["latency_recent"]["sensed_from"],
        "latency_recent": coverage["summary"]["latency_recent"],
        "clock": "earliest object last-modified time in the USGS bucket, after sensing start",
    }


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tiles", nargs="*", help="Tiles to survey instead of all")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks/results/l2a-latency.json")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    parser.add_argument("--from-raw", type=Path, help="rebuild the result from saved listings")
    args = parser.parse_args(argv)

    coverage = json.loads(AQR_COVERAGE.read_text())
    if args.from_raw:
        raw_dir = args.from_raw.resolve()
        meta = json.loads((raw_dir / "meta.json").read_text())
    else:
        meta = window_from_coverage(coverage)
        if args.tiles:
            meta["tiles"] = [t for t in meta["tiles"] if t in args.tiles]
        for line in plan(meta, args.output):
            print(line)
        if args.dry_run:
            return 0
        meta["measured_at"] = harness.utc_now()
        meta["code_version"] = harness.code_version()
        meta["script_sha256"] = sha256_text(Path(__file__))
        raw_dir = ROOT / "data" / "l2a-latency" / meta["measured_at"].replace(":", "")
        raw_dir.mkdir(parents=True, exist_ok=True)
        meta["request_log"] = collect(meta, raw_dir)
        (raw_dir / "meta.json").write_text(json.dumps(meta))

    analysis = analyze(raw_dir, meta)
    logs = meta["request_log"]
    api = logs["earth_search_and_cdse"]
    result = {
        "schema_version": 1,
        "measured_at": meta["measured_at"],
        "code_version": meta["code_version"],
        "script_sha256": meta["script_sha256"],
        "analysis_code_version": harness.code_version(),
        "script": "benchmarks/l2a_latency.py",
        "window": {"start": meta["start"], "end": meta["end"], "cutoff": meta["cutoff"]},
        "tiles_source": "benchmarks/results/aqr-coverage.json",
        "tiles": meta["tiles"],
        "endpoints": {
            "earth_search": gs.ES_ROOT,
            "cdse_odata": gs.CDSE_ODATA,
            "buckets": {c: BUCKETS[c]["bucket"] for c in COLLECTIONS},
            "region": REGION,
            "credentials": "none, unsigned requests and public APIs",
            "payer": "Bucket owner. Neither bucket is requester pays, and every request was "
            "unsigned. The catalog APIs are public and free.",
        },
        "requests": {
            "earth_search": sum(1 for e in api if e["host"].startswith("earth-search")),
            "cdse_odata": sum(1 for e in api if e["host"].startswith("catalogue")),
            "api_bytes_received": sum(e["bytes"] for e in api),
            "s3_list": len(logs["s3"]),
            "s3_bytes_received": sum(e["bytes"] for e in logs["s3"]),
            "object_bodies_read": 0,
            "pixels_read": 0,
        },
        "definitions": {
            "sensing": "Sensing start in the item's ESA product name, s2:product_uri. Finding 27 "
            "takes the same start from the ACOLITE object name.",
            "esa_generation": "s2:generation_time, the ESA product generation time.",
            "esa_origin": "Copernicus OData OriginDate of the same product name.",
            "cdse_publication": "Copernicus OData PublicationDate of the same product name.",
            "catalog_created": "The Earth Search item's created time.",
            "bucket_first": "Earliest last-modified time of the objects in the item's bucket "
            "folder. The clock of finding 27.",
            "bucket_last": "Latest last-modified time in the same folder.",
            "bucket_first_matched_cutoff": "bucket_first over items whose first object is at or "
            "before finding 27's listing time, so both options face the same censoring.",
            "share_of_cdse_products_in_bucket_within": "Of the Copernicus products sensed in the "
            "window on these tiles, the share whose Earth Search item, matched by product name, "
            "had a first bucket object within each threshold of sensing. Unmatched products "
            "count as not arrived.",
            "cdse_status": "same_product: an Earth Search item has the product name. "
            "pass_other_product: an item has the tile, platform, and sensing start under another "
            "name. absent: neither.",
            "percentiles": "Nearest rank, as in finding 27.",
        },
        "acolite_reference": acolite_reference(coverage),
        **analysis,
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "request_log": logs,
        "limitations": [
            "Listings and catalog metadata only. No object body and no pixel was read.",
            "Object last-modified times show when each object was last written. A rewritten "
            "object resets its time, so a reprocessed item can look late.",
            "Items not yet on Earth Search at measured_at carry no latency. "
            "share_of_cdse_products_in_bucket_within counts them as not arrived.",
            "Copernicus is the reference set of products. Products missing there are not seen.",
            "One window of four months on 24 lower-48 tiles. Seasonal and outage behavior "
            "outside it is not shown, issue I-24.",
            "The ACOLITE reference is copied from finding 27's result. Neither option's scenes "
            "were paired pass by pass.",
            "Counts describe the catalogs and buckets at measured_at.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    for collection in COLLECTIONS:
        s = analysis["summary"][collection]
        print(
            f"{collection}: {s['items']} items, bucket_first {s['latency']['bucket_first']}, "
            f"cdse {s['cdse_status']}"
        )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
