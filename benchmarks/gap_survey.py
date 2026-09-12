"""Data gap survey over the Earth Search Sentinel-2 collections. Catalog metadata only.

Runs only when the user invokes it. It contacts the Earth Search STAC API and, as a
reference count, the Copernicus Data Space Ecosystem catalogs. It reads no imagery.
It writes one result JSON to benchmarks/results/ and raw item listings under data/.

    uv run python benchmarks/gap_survey.py
    uv run python benchmarks/gap_survey.py --max-sites 1 --output data/smoke.json

Method, per tile found from the survey sites: one aggregation and one paged listing per
Earth Search collection over the window, one reference listing per year from the
Copernicus STAC, and one reference count per year from the Copernicus OData catalog.
Gaps are counted on distinct sensing dates per platform, never on item counts alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

ES_ROOT = "https://earth-search.aws.element84.com/v1"
ES_COLLECTIONS = [
    "sentinel-2-c1-l2a",
    "sentinel-2-pre-c1-l2a",
    "sentinel-2-l2a",
    "sentinel-2-l1c",
]
PRIMARY = "sentinel-2-c1-l2a"
FALLBACK = "sentinel-2-l2a"
CDSE_STAC = "https://stac.dataspace.copernicus.eu/v1"
CDSE_COLLECTION = "sentinel-2-l2a"
CDSE_ODATA = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
PAGE_LIMIT = 1000
QUALITY_ASSETS = ["scl", "cloud", "snow", "aot", "wvp", "scl-jp2", "aot-jp2", "wvp-jp2"]
ITEM_FIELDS = [
    "id",
    "properties.datetime",
    "properties.platform",
    "properties.grid:code",
    "properties.s2:processing_baseline",
    "properties.s2:sequence",
    "properties.processing:software",
    "properties.earthsearch:boa_offset_applied",
    "properties.eo:cloud_cover",
    "properties.s2:nodata_pixel_percentage",
    "properties.s2:product_uri",
    "properties.s2:generation_time",
    "properties.created",
    "properties.updated",
]
EXCLUDE = ["geometry", "bbox", "links", "assets"]
USER_AGENT = "sentinel2-pipeline-development gap survey (catalog metadata only)"


# ---------------------------------------------------------------- pure helpers


def month_range(start: str, end: str) -> list[str]:
    """Inclusive list of YYYY-MM months between two ISO dates."""
    first = date.fromisoformat(start)
    last = date.fromisoformat(end)
    if last < first:
        raise ValueError("end precedes start")
    months = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return months


def platform_letter(platform: str | None, item_id: str) -> str:
    """Return a, b, or c for the Sentinel-2 unit, from the platform field or the id."""
    for text in (platform or "", item_id):
        found = re.search(r"sentinel-?2([abc])", text, re.IGNORECASE) or re.match(
            r"S2([ABC])", text
        )
        if found:
            return found.group(1).lower()
    return "?"


def sensing_key(item: dict) -> str:
    """Distinct-acquisition key: sensing date plus platform letter."""
    return f"{item['datetime'][:10]}/{item['platform']}"


def tile_code(props: dict, item_id: str) -> str | None:
    """MGRS tile such as 10SGJ, from grid:code or from the item id."""
    code = props.get("grid:code")
    if isinstance(code, str) and code.startswith("MGRS-"):
        return code[5:]
    found = re.search(r"_T?(\d{1,2}[C-X][A-Z]{2})_", item_id)
    return found.group(1) if found else None


def normalize_es(feature: dict) -> dict:
    """Reduce an Earth Search item to the fields the survey keeps."""
    props = feature.get("properties", {})
    software = props.get("processing:software")
    return {
        "id": feature["id"],
        "datetime": props.get("datetime", ""),
        "platform": platform_letter(props.get("platform"), feature["id"]),
        "tile": tile_code(props, feature["id"]),
        "baseline": props.get("s2:processing_baseline"),
        "sequence": props.get("s2:sequence"),
        "software": json.dumps(software, sort_keys=True) if software else None,
        "offset_applied": props.get("earthsearch:boa_offset_applied"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "nodata_pct": props.get("s2:nodata_pixel_percentage"),
        "product_uri": props.get("s2:product_uri"),
        "generation_time": props.get("s2:generation_time"),
        "created": props.get("created"),
        "updated": props.get("updated"),
    }


def normalize_cdse(feature: dict) -> dict:
    """Reduce a Copernicus STAC item to the fields the survey keeps."""
    props = feature.get("properties", {})
    return {
        "id": feature["id"],
        "datetime": props.get("datetime", ""),
        "platform": platform_letter(props.get("platform"), feature["id"]),
        "tile": tile_code(props, feature["id"]),
        "baseline": props.get("processing:version"),
        "sequence": None,
        "software": None,
        "offset_applied": None,
        "cloud_cover": props.get("eo:cloud_cover"),
        "nodata_pct": None,
        "product_uri": None,
        "generation_time": props.get("processing:datetime"),
        "created": props.get("created"),
        "updated": props.get("updated"),
    }


def _counter_dict(values) -> dict:
    return {str(k): v for k, v in sorted(Counter(values).items(), key=lambda kv: str(kv[0]))}


def summarize(items: list[dict], months: list[str]) -> dict:
    """Per-month arrays aligned to `months`, plus per-month sensing keys for comparison."""
    by_month: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        month = item["datetime"][:7]
        if month in months:
            by_month[month].append(item)
    keys = {m: {sensing_key(i) for i in by_month[m]} for m in months}
    in_window = [i for m in months for i in by_month[m]]
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in in_window:
        groups[sensing_key(item)].append(item)
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    flags_by_baseline: dict[str, Counter] = defaultdict(Counter)
    for item in in_window:
        flags_by_baseline[str(item["baseline"])][str(item["offset_applied"])] += 1
    out = {
        "items": [len(by_month[m]) for m in months],
        "acquisitions": [len(keys[m]) for m in months],
        "duplicate_acquisitions": [sum(1 for k in keys[m] if k in duplicates) for m in months],
        "baselines": [_counter_dict(i["baseline"] for i in by_month[m]) for m in months],
        "baselines_total": _counter_dict(i["baseline"] for i in in_window),
        "platforms_total": _counter_dict(i["platform"] for i in in_window),
        "sequences_total": _counter_dict(i["sequence"] for i in in_window),
        "software": _counter_dict(i["software"] for i in in_window),
        "offset_flag_by_baseline": {
            b: dict(sorted(c.items())) for b, c in sorted(flags_by_baseline.items())
        },
        "duplicate_baseline_sets": _counter_dict(
            "+".join(sorted(str(i["baseline"]) for i in v)) for v in duplicates.values()
        ),
        "items_total": len(in_window),
        "acquisitions_total": len(groups),
        "duplicate_acquisitions_total": len(duplicates),
        "outside_window": len(items) - len(in_window),
    }
    return out, keys


def compare(months, reference_keys, primary_keys, fallback_keys) -> dict:
    """Per-month gap accounting of the primary collection against the reference archive.

    Every quantity counts distinct sensing keys (date and platform), not items.
    """
    rows = {
        "reference": [],
        "primary": [],
        "missing": [],
        "covered_by_fallback": [],
        "uncovered": [],
        "primary_not_in_reference": [],
        "status": [],
    }
    for m in months:
        ref, pri, fb = (
            reference_keys.get(m, set()),
            primary_keys.get(m, set()),
            fallback_keys.get(m, set()),
        )
        missing = ref - pri
        covered = missing & fb
        uncovered = missing - fb
        if not ref:
            status = "no_reference" if not pri else "primary_only"
        elif not missing:
            status = "complete"
        elif not pri:
            status = "empty"
        else:
            status = "partial"
        rows["reference"].append(len(ref))
        rows["primary"].append(len(pri))
        rows["missing"].append(len(missing))
        rows["covered_by_fallback"].append(len(covered))
        rows["uncovered"].append(len(uncovered))
        rows["primary_not_in_reference"].append(len(pri - ref))
        rows["status"].append(status)
    rows["months_by_status"] = _counter_dict(rows["status"])
    rows["missing_total"] = sum(rows["missing"])
    rows["covered_by_fallback_total"] = sum(rows["covered_by_fallback"])
    rows["uncovered_total"] = sum(rows["uncovered"])
    rows["uncovered_keys"] = sorted(
        k
        for m in months
        for k in (
            reference_keys.get(m, set()) - primary_keys.get(m, set()) - fallback_keys.get(m, set())
        )
    )
    return rows


def asset_summary(feature: dict) -> dict:
    """Asset keys and the quality-asset details of one full item."""
    assets = feature.get("assets", {})
    props = feature.get("properties", {})

    def describe(asset):
        band = (asset.get("raster:bands") or [{}])[0]
        href = asset.get("href", "")
        host = urllib.parse.urlparse(href).netloc or href
        return {
            "href_host": host,
            "type": asset.get("type"),
            "resolution_m": band.get("spatial_resolution"),
            "data_type": band.get("data_type"),
            "scale": band.get("scale"),
            "offset": band.get("offset"),
            "nodata": band.get("nodata"),
        }

    return {
        "item_id": feature["id"],
        "collection": feature.get("collection"),
        "baseline": props.get("s2:processing_baseline"),
        "software": props.get("processing:software"),
        "boa_offset_applied": props.get("earthsearch:boa_offset_applied"),
        "storage": {k: v for k, v in props.items() if k.startswith("storage:")},
        "asset_keys": sorted(assets),
        "quality_assets": {k: describe(assets[k]) for k in QUALITY_ASSETS if k in assets},
        "red": describe(assets["red"]) if "red" in assets else None,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_version() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        return sha + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# ---------------------------------------------------------------- HTTP client


class Client:
    """Small HTTP client that counts requests and bytes per host and retries politely."""

    def __init__(self, pause: float = 0.2, retries: int = 5, timeout: float = 120.0):
        self.pause = pause
        self.retries = retries
        self.timeout = timeout
        self.requests: Counter = Counter()
        self.bytes: Counter = Counter()
        self.log: list[dict] = []

    def get_json(self, url: str, body: dict | None = None, note: str = "") -> dict:
        host = urllib.parse.urlparse(url).netloc
        data = json.dumps(body).encode() if body is not None else None
        headers = {"accept": "application/json", "user-agent": USER_AGENT}
        if data is not None:
            headers["content-type"] = "application/json"
        delay = 1.0
        for attempt in range(1, self.retries + 1):
            request = urllib.request.Request(url, data=data, headers=headers)
            started = time.perf_counter()
            status, raw, error = None, b"", None
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    status = response.status
            except urllib.error.HTTPError as caught:
                status, raw, error = caught.code, caught.read(), caught
            except (urllib.error.URLError, TimeoutError) as caught:
                error = caught
            self.requests[host] += 1
            self.bytes[host] += len(raw)
            self.log.append(
                {
                    "host": host,
                    "method": "POST" if data is not None else "GET",
                    "path": url[len(f"https://{host}") :],
                    "note": note,
                    "status": status,
                    "bytes": len(raw),
                    "seconds": round(time.perf_counter() - started, 3),
                    "attempt": attempt,
                }
            )
            if error is None:
                time.sleep(self.pause)
                return json.loads(raw)
            retryable = status is None or status in (408, 425, 429, 500, 502, 503, 504)
            if retryable and attempt < self.retries:
                time.sleep(delay)
                delay *= 2
                continue
            if status is None:
                raise RuntimeError(f"no response from {url}: {error}") from error
            raise RuntimeError(f"{status} from {url}: {raw[:300]!r}") from error
        raise RuntimeError("unreachable")


def paged_search(client: Client, root: str, body: dict, note: str) -> list[dict]:
    """POST /search and follow `next` links until exhausted. Returns raw features."""
    features: list[dict] = []
    url = f"{root}/search"
    payload = dict(body)
    for page in range(1, 200):
        result = client.get_json(url, payload, f"{note} page {page}")
        features.extend(result.get("features", []))
        links = result.get("links", [])
        next_link = next((link for link in links if link.get("rel") == "next"), None)
        if not next_link:
            return features
        if next_link.get("method", "GET").upper() == "POST" or "body" in next_link:
            url = next_link.get("href", url)
            payload = dict(body)
            if next_link.get("merge", True) is False:
                payload = {}
            payload.update(next_link.get("body", {}))
        else:
            url = next_link["href"]
            payload = None  # type: ignore[assignment]
    raise RuntimeError(f"pagination did not end: {note}")


# ---------------------------------------------------------------- survey steps


def window_datetime(start: str, end: str) -> str:
    return f"{start}T00:00:00Z/{end}T23:59:59Z"


def discover_tiles(client: Client, site: dict, start: str, end: str) -> dict:
    """Tiles whose Collection 1 item footprints cover the site point in the last year."""
    body = {
        "collections": [PRIMARY],
        "intersects": {"type": "Point", "coordinates": [site["longitude"], site["latitude"]]},
        "datetime": window_datetime(start, end),
        "limit": PAGE_LIMIT,
        "fields": {"include": ["id", "properties.grid:code"], "exclude": EXCLUDE},
    }
    features = paged_search(client, ES_ROOT, body, f"discover {site['site_id']}")
    counts = Counter(tile_code(f.get("properties", {}), f["id"]) for f in features)
    return {str(k): v for k, v in sorted(counts.items()) if k}


def es_aggregate(client: Client, collection: str, tile: str | None, start: str, end: str) -> dict:
    params = {
        "collections": collection,
        "aggregations": "total_count,datetime_frequency",
        "datetime_frequency_interval": "month",
        "datetime": window_datetime(start, end),
    }
    if tile:
        params["query"] = json.dumps({"grid:code": {"eq": f"MGRS-{tile}"}})
    url = f"{ES_ROOT}/aggregate?{urllib.parse.urlencode(params)}"
    result = client.get_json(url, None, f"aggregate {collection} {tile or 'global'}")
    out = {"total_count": None, "monthly": {}}
    for agg in result.get("aggregations", []):
        if agg["name"] == "total_count":
            out["total_count"] = agg.get("value")
        elif agg["name"] == "datetime_frequency":
            out["overflow"] = agg.get("overflow")
            out["monthly"] = {b["key"][:7]: b["frequency"] for b in agg.get("buckets", [])}
    return out


def es_collection_extent(client: Client, collection: str) -> dict:
    params = {"collections": collection, "aggregations": "total_count,datetime_min,datetime_max"}
    url = f"{ES_ROOT}/aggregate?{urllib.parse.urlencode(params)}"
    result = client.get_json(url, None, f"extent {collection}")
    return {a["name"]: a.get("value") for a in result.get("aggregations", [])}


def es_list(client: Client, collection: str, tile: str, start: str, end: str) -> list[dict]:
    body = {
        "collections": [collection],
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "datetime": window_datetime(start, end),
        "limit": PAGE_LIMIT,
        "fields": {"include": ITEM_FIELDS, "exclude": EXCLUDE},
    }
    return paged_search(client, ES_ROOT, body, f"list {collection} {tile}")


def es_fetch_item(client: Client, collection: str, item_id: str) -> dict | None:
    body = {"collections": [collection], "ids": [item_id], "limit": 1}
    features = paged_search(client, ES_ROOT, body, f"item {item_id}")
    return features[0] if features else None


def cdse_list(client: Client, tile: str, year: int, start: str, end: str) -> list[dict]:
    year_start = max(start, f"{year}-01-01")
    year_end = min(end, f"{year}-12-31")
    body = {
        "collections": [CDSE_COLLECTION],
        "query": {"grid:code": {"eq": f"MGRS-{tile}"}},
        "datetime": window_datetime(year_start, year_end),
        "limit": PAGE_LIMIT,
        "fields": {
            "include": [
                "id",
                "properties.datetime",
                "properties.platform",
                "properties.grid:code",
                "properties.processing:version",
                "properties.processing:datetime",
                "properties.eo:cloud_cover",
                "properties.created",
                "properties.updated",
            ],
            "exclude": EXCLUDE,
        },
    }
    return paged_search(client, CDSE_STAC, body, f"cdse {tile} {year}")


def odata_count(client: Client, tile: str, year: int, start: str, end: str) -> int | None:
    year_start = max(start, f"{year}-01-01")
    year_end = min(end, f"{year}-12-31")
    query = (
        "Collection/Name eq 'SENTINEL-2' and contains(Name,'MSIL2A') and "
        f"contains(Name,'_T{tile}_') and ContentDate/Start ge {year_start}T00:00:00.000Z "
        f"and ContentDate/Start le {year_end}T23:59:59.999Z"
    )
    url = f"{CDSE_ODATA}?{urllib.parse.urlencode({'$filter': query, '$count': 'true', '$top': 1})}"
    result = client.get_json(url, None, f"odata {tile} {year}")
    return result.get("@odata.count")


def survey_tile(client, tile, start, end, months, reference: bool, raw_dir: Path) -> dict:
    record: dict = {"earth_search": {}, "reference": None, "gaps": None, "raw_files": {}}
    keys_by_collection = {}
    for collection in ES_COLLECTIONS:
        agg = es_aggregate(client, collection, tile, start, end)
        features = es_list(client, collection, tile, start, end)
        raw_path = raw_dir / f"{tile}-{collection}.json"
        raw_path.write_text(json.dumps(features, separators=(",", ":")))
        record["raw_files"][collection] = {"path": str(raw_path), "sha256": sha256_file(raw_path)}
        items = [normalize_es(f) for f in features]
        wrong_tile = sum(1 for i in items if i["tile"] != tile)
        summary, keys = summarize(items, months)
        keys_by_collection[collection] = keys
        listed_in_window = sum(summary["items"])
        agg_total = sum(agg["monthly"].get(m, 0) for m in months)
        summary["aggregation_monthly"] = [agg["monthly"].get(m, 0) for m in months]
        summary["aggregation_total"] = agg["total_count"]
        summary["aggregation_matches_listing"] = agg_total == listed_in_window
        summary["items_wrong_tile"] = wrong_tile
        record["earth_search"][collection] = summary
        print(
            f"  {tile} {collection}: {listed_in_window} items, "
            f"{summary['acquisitions_total']} acquisitions, aggregation "
            f"{'agrees' if summary['aggregation_matches_listing'] else 'DISAGREES'}",
            flush=True,
        )
    if reference:
        years = sorted({int(m[:4]) for m in months})
        cdse_features: list[dict] = []
        odata_counts = {}
        for year in years:
            cdse_features.extend(cdse_list(client, tile, year, start, end))
            odata_counts[str(year)] = odata_count(client, tile, year, start, end)
        raw_path = raw_dir / f"{tile}-cdse-stac.json"
        raw_path.write_text(json.dumps(cdse_features, separators=(",", ":")))
        record["raw_files"]["cdse-stac"] = {"path": str(raw_path), "sha256": sha256_file(raw_path)}
        ref_items = [normalize_cdse(f) for f in cdse_features]
        ref_summary, ref_keys = summarize(ref_items, months)
        stac_by_year = Counter(i["datetime"][:4] for i in ref_items if i["datetime"][:7] in months)
        ref_summary["odata_counts_by_year"] = odata_counts
        ref_summary["stac_counts_by_year"] = {y: stac_by_year.get(y, 0) for y in odata_counts}
        ref_summary["odata_matches_stac"] = all(
            odata_counts[y] == stac_by_year.get(y, 0) for y in odata_counts
        )
        record["reference"] = ref_summary
        record["gaps"] = compare(
            months, ref_keys, keys_by_collection[PRIMARY], keys_by_collection[FALLBACK]
        )
        record["fallback_gaps"] = compare(months, ref_keys, keys_by_collection[FALLBACK], {})
        print(
            f"  {tile} reference: {ref_summary['acquisitions_total']} acquisitions, "
            f"primary missing {record['gaps']['missing_total']}, "
            f"uncovered {record['gaps']['uncovered_total']}, status "
            f"{record['gaps']['months_by_status']}",
            flush=True,
        )
    return record


def sample_assets(client: Client, tiles: dict, raw_dir: Path) -> list[dict]:
    """One full item per (collection, software, baseline) seen across all tiles."""
    chosen: dict[tuple, str] = {}
    for record in tiles.values():
        for collection, entry in record["raw_files"].items():
            if collection not in ES_COLLECTIONS:
                continue
            for feature in json.loads(Path(entry["path"]).read_text()):
                item = normalize_es(feature)
                key = (collection, item["software"], item["baseline"])
                chosen.setdefault(key, item["id"])
    samples = []
    for (collection, _software, _baseline), item_id in sorted(chosen.items(), key=str):
        feature = es_fetch_item(client, collection, item_id)
        if feature:
            samples.append(asset_summary(feature))
    return samples


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sites", type=Path, default=Path("benchmarks/gap-survey-sites.json"))
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default=datetime.now(UTC).date().isoformat())
    parser.add_argument(
        "--tiles", nargs="*", help="Survey these MGRS tiles instead of discovering them"
    )
    parser.add_argument(
        "--max-sites", type=int, help="Survey only the first N sites, for a smoke run"
    )
    parser.add_argument("--no-reference", action="store_true", help="Skip the Copernicus reference")
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/gap-survey.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/gap-survey"))
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds between requests")
    args = parser.parse_args(argv)

    measured_at = datetime.now(UTC).isoformat(timespec="seconds")
    months = month_range(args.start, args.end)
    discovery_start = (
        date.fromisoformat(args.end).replace(year=date.fromisoformat(args.end).year - 1)
    ).isoformat()
    raw_dir = args.raw_dir / measured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = Client(pause=args.pause)
    sites_doc = json.loads(args.sites.read_text())
    sites = sites_doc["sites"][: args.max_sites] if args.max_sites else sites_doc["sites"]

    print(f"gap survey {measured_at}: {len(months)} months, {len(sites)} sites", flush=True)
    collections = {}
    for collection in ES_COLLECTIONS:
        collections[collection] = es_collection_extent(client, collection)
        agg = es_aggregate(client, collection, None, args.start, args.end)
        collections[collection]["window_total"] = agg["total_count"]
        collections[collection]["window_monthly"] = [agg["monthly"].get(m, 0) for m in months]
        print(f"{collection}: {collections[collection]}", flush=True)

    site_records = []
    tile_sites: dict[str, list[str]] = defaultdict(list)
    if args.tiles:
        for tile in args.tiles:
            tile_sites[tile].append("(argument)")
    else:
        for site in sites:
            found = discover_tiles(client, site, discovery_start, args.end)
            site_records.append({**site, "tiles": found})
            for tile in found:
                tile_sites[tile].append(site["site_id"])
            print(f"{site['site_id']}: tiles {found}", flush=True)

    tiles = {}
    for tile in sorted(tile_sites):
        print(f"tile {tile} ({', '.join(tile_sites[tile])})", flush=True)
        tiles[tile] = survey_tile(
            client, tile, args.start, args.end, months, not args.no_reference, raw_dir
        )
        tiles[tile]["sites"] = tile_sites[tile]
        tiles[tile]["utm_zone"] = int(re.match(r"\d+", tile).group())

    samples = sample_assets(client, tiles, raw_dir)

    summary = summarize_survey(tiles, months, collections)
    result = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": code_version(),
        "script": "benchmarks/gap_survey.py",
        "sites_file": str(args.sites),
        "sites_sha256": sha256_file(args.sites),
        "window": {"start": args.start, "end": args.end, "months": months},
        "tile_discovery_window": {"start": discovery_start, "end": args.end, "collection": PRIMARY},
        "endpoints": {
            "earth_search": {
                "root": ES_ROOT,
                "operator": "Element 84",
                "region": "us-west-2",
                "payer": "provider. Public API, no credentials, no requester-pays bucket touched",
                "role": "the access route, decision 0003",
            },
            "cdse_stac": {
                "root": CDSE_STAC,
                "operator": "Copernicus Data Space Ecosystem",
                "region": "not AWS",
                "payer": "provider. Public catalog, no credentials",
                "role": "reference count of what ESA currently lists. Not a route",
            },
            "cdse_odata": {
                "root": CDSE_ODATA,
                "operator": "Copernicus Data Space Ecosystem",
                "region": "not AWS",
                "payer": "provider. Public catalog, no credentials",
                "role": "second reference count per tile and year. Not a route",
            },
        },
        "requests": {
            "by_host": dict(client.requests),
            "bytes_received_by_host": dict(client.bytes),
            "imagery_bytes": 0,
            "total": sum(client.requests.values()),
        },
        "collections": collections,
        "sites": site_records,
        "tiles": tiles,
        "asset_samples": samples,
        "summary": summary,
        "raw_listing_dir": str(raw_dir),
        "request_log": client.log,
        "limitations": [
            "Catalog metadata only. No imagery byte was read, so nothing here shows whether "
            "a listed asset opens or holds valid pixels.",
            "Sensing keys pair the date with the platform letter. Two acquisitions of one tile "
            "by one unit on one date would collapse into one key.",
            "Tiles come from Collection 1 footprints covering the site point in the last year. "
            "A tile whose items never cover the point is not surveyed.",
            "The Copernicus catalogs are a reference for what ESA lists today, not a route. "
            "Their completeness is not independently established.",
            "Counts describe the catalogs at measured_at. Ingestion continues and can change "
            "every number.",
            "Site points stand in for the pilot manifest, which does not exist yet. Rerun on "
            "the manifest's tiles when it exists.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n")
    print(f"wrote {args.output}: {result['requests']['total']} requests", flush=True)
    return 0


def summarize_survey(tiles: dict, months: list[str], collections: dict) -> dict:
    """Cross-tile summary: which months are empty or partial everywhere, and fallback baselines."""
    status_by_month = defaultdict(Counter)
    fallback_baselines_by_year = defaultdict(Counter)
    primary_baselines_by_year = defaultdict(Counter)
    offset_by_collection_baseline = defaultdict(Counter)
    uncovered = Counter()
    missing = Counter()
    for record in tiles.values():
        es = record["earth_search"]
        for idx, month in enumerate(months):
            year = month[:4]
            for baseline, n in es[FALLBACK]["baselines"][idx].items():
                fallback_baselines_by_year[year][baseline] += n
            for baseline, n in es[PRIMARY]["baselines"][idx].items():
                primary_baselines_by_year[year][baseline] += n
            if record["gaps"]:
                status_by_month[month][record["gaps"]["status"][idx]] += 1
                missing[month] += record["gaps"]["missing"][idx]
                uncovered[month] += record["gaps"]["uncovered"][idx]
    collection_totals = defaultdict(Counter)
    duplicate_sets = defaultdict(Counter)
    for record in tiles.values():
        for collection, entry in record["earth_search"].items():
            for baseline, flags in entry["offset_flag_by_baseline"].items():
                offset_by_collection_baseline[f"{collection} {baseline}"].update(flags)
            for key in ("items_total", "acquisitions_total", "duplicate_acquisitions_total"):
                collection_totals[collection][key] += entry[key]
            collection_totals[collection]["aggregation_matches_listing"] += int(
                entry["aggregation_matches_listing"]
            )
            duplicate_sets[collection].update(entry["duplicate_baseline_sets"])
        if record["reference"]:
            ref = record["reference"]
            for key in ("items_total", "acquisitions_total", "duplicate_acquisitions_total"):
                collection_totals["reference cdse stac"][key] += ref[key]
            collection_totals["reference cdse stac"]["odata_matches_stac"] += int(
                ref["odata_matches_stac"]
            )
    months_empty_everywhere = [
        m for m in months if status_by_month.get(m) and set(status_by_month[m]) <= {"empty"}
    ]
    months_incomplete_anywhere = [
        m for m in months if any(s in ("empty", "partial") for s in status_by_month.get(m, {}))
    ]
    return {
        "tiles": len(tiles),
        "tiles_with_reference": sum(1 for r in tiles.values() if r["gaps"]),
        "primary_status_by_month": {m: dict(status_by_month[m]) for m in months},
        "months_empty_in_every_tile": months_empty_everywhere,
        "months_incomplete_in_any_tile": months_incomplete_anywhere,
        "missing_acquisitions_by_month": {m: missing[m] for m in months if missing[m]},
        "uncovered_acquisitions_by_month": {m: uncovered[m] for m in months if uncovered[m]},
        "missing_acquisitions_total": sum(missing.values()),
        "uncovered_acquisitions_total": sum(uncovered.values()),
        "primary_baselines_by_year": {
            y: dict(c) for y, c in sorted(primary_baselines_by_year.items())
        },
        "fallback_baselines_by_year": {
            y: dict(c) for y, c in sorted(fallback_baselines_by_year.items())
        },
        "offset_flag_by_collection_and_baseline": {
            k: dict(v) for k, v in sorted(offset_by_collection_baseline.items())
        },
        "collection_totals": {k: dict(v) for k, v in collection_totals.items()},
        "duplicate_baseline_sets_by_collection": {
            k: dict(v.most_common()) for k, v in duplicate_sets.items()
        },
        "global_window_monthly": {c: collections[c]["window_monthly"] for c in ES_COLLECTIONS},
    }


if __name__ == "__main__":
    sys.exit(main())
