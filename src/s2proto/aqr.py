"""The USGS ACOLITE aquatic reflectance bucket: object names, listings, settings, and joins.

Pure helpers for probes T1 to T3 of the replan record,
docs/reviews/2026-10-13-acolite-first-replan.md.
Nothing here contacts a provider. The scripts under benchmarks/ do, when the user invokes them.
"""

from __future__ import annotations

import math
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import UTC, datetime

BUCKET = "usgs-wma-sentinel-2-aqr-acolite-dsf"
REGION = "us-west-2"
ENDPOINT = f"https://{BUCKET}.s3.{REGION}.amazonaws.com"
VERSION_PREFIX = "version_01/"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
PLATFORMS = ("S2A", "S2B", "S2C", "S2D")
# The layer set one scene held in the reconnaissance listing of 2026-10-13. Probes report
# every layer set they find, so a scene with other layers shows up rather than being dropped.
OBSERVED_LAYERS = (
    "B01",
    "B02",
    "B03",
    "B04",
    "B05",
    "B06",
    "B07",
    "B08",
    "B8A",
    "B11",
    "B12",
    "NDWI",
    "l2_flags",
    "settings",
)
KEY_PATTERN = re.compile(
    r"^(?P<version>version_\d+)/T(?P<prefix_tile>\d{2}[C-X][A-Z]{2})/"
    r"(?P<platform>S2[A-D])_MSIAQR_(?P<sensing>\d{8}T\d{6})_N(?P<baseline>\d{4})_"
    r"R(?P<orbit>\d{3})_T(?P<tile>\d{2}[C-X][A-Z]{2})_(?P<generation>\d{8}T\d{6})_"
    r"(?P<layer>[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*)\.(?P<ext>tif|txt)$"
)
PRODUCT_PATTERN = re.compile(
    r"^(?P<platform>S2[A-D])_MSI(?P<level>L1C|L2A|AQR)_(?P<sensing>\d{8}T\d{6})_"
    r"N(?P<baseline>\d{4})_R(?P<orbit>\d{3})_T(?P<tile>\d{2}[C-X][A-Z]{2})_"
    r"(?P<generation>\d{8}T\d{6})(?:\.SAFE)?$"
)


def list_url(prefix: str, delimiter: str | None = None, token: str | None = None) -> str:
    """ListObjectsV2 URL for an unsigned request."""
    query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
    if delimiter:
        query["delimiter"] = delimiter
    if token:
        query["continuation-token"] = token
    return f"{ENDPOINT}/?{urllib.parse.urlencode(query)}"


def object_url(key: str) -> str:
    return f"{ENDPOINT}/{urllib.parse.quote(key)}"


def parse_listing(xml_text: str) -> dict:
    """Keys, common prefixes, and the continuation state of one ListObjectsV2 page."""
    root = ET.fromstring(xml_text)

    def text(node, tag):
        found = node.find(f"s3:{tag}", S3_NS)
        return found.text if found is not None else None

    keys = [
        {
            "key": text(item, "Key"),
            "size": int(text(item, "Size") or 0),
            "etag": (text(item, "ETag") or "").strip('"'),
            "last_modified": text(item, "LastModified"),
            "storage_class": text(item, "StorageClass"),
        }
        for item in root.findall("s3:Contents", S3_NS)
    ]
    prefixes = [text(item, "Prefix") for item in root.findall("s3:CommonPrefixes", S3_NS)]
    return {
        "keys": keys,
        "prefixes": prefixes,
        "truncated": text(root, "IsTruncated") == "true",
        "next_token": text(root, "NextContinuationToken"),
    }


def compact_time(value: str) -> str:
    """20251015T162149 as 2025-10-15T16:21:49Z."""
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat()[:19] + "Z"


def baseline_label(digits: str) -> str:
    """0511 as 05.11."""
    return f"{digits[:2]}.{digits[2:]}"


def parse_key(key: str) -> dict | None:
    """Fields of one aquatic reflectance object name, or None for any other name."""
    found = KEY_PATTERN.match(key)
    if not found:
        return None
    parts = found.groupdict()
    product = (
        f"{parts['platform']}_MSIAQR_{parts['sensing']}_N{parts['baseline']}_R{parts['orbit']}_"
        f"T{parts['tile']}_{parts['generation']}"
    )
    return {
        "version": parts["version"],
        "prefix_tile": parts["prefix_tile"],
        "tile": parts["tile"],
        "platform": parts["platform"],
        "sensing": parts["sensing"],
        "sensing_time": compact_time(parts["sensing"]),
        "baseline": baseline_label(parts["baseline"]),
        "orbit": int(parts["orbit"]),
        "generation_time": compact_time(parts["generation"]),
        "layer": parts["layer"],
        "extension": parts["ext"],
        "product": product,
    }


def parse_product(name: str) -> dict | None:
    """Fields of a Level-1C, Level-2A, or aquatic reflectance product name."""
    found = PRODUCT_PATTERN.match(name or "")
    if not found:
        return None
    parts = found.groupdict()
    return {
        "platform": parts["platform"],
        "level": parts["level"],
        "sensing": parts["sensing"],
        "baseline": baseline_label(parts["baseline"]),
        "orbit": int(parts["orbit"]),
        "tile": parts["tile"],
        "generation_time": compact_time(parts["generation"]),
    }


def group_scenes(objects: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Group listed objects by product. Returns the scenes and the keys that did not parse."""
    scenes: dict[str, dict] = {}
    unparsed: list[str] = []
    for obj in objects:
        parsed = parse_key(obj["key"])
        if parsed is None:
            unparsed.append(obj["key"])
            continue
        scene = scenes.setdefault(
            parsed["product"],
            {
                key: parsed[key]
                for key in (
                    "product",
                    "version",
                    "prefix_tile",
                    "tile",
                    "platform",
                    "sensing",
                    "sensing_time",
                    "baseline",
                    "orbit",
                    "generation_time",
                )
            }
            | {"layers": {}},
        )
        scene["layers"][parsed["layer"]] = {
            "key": obj["key"],
            "size": obj["size"],
            "etag": obj["etag"],
            "last_modified": obj["last_modified"],
        }
    return scenes, unparsed


def parse_settings(text: str) -> dict[str, str]:
    """Key and value pairs of an ACOLITE settings file. Comments and blank lines are skipped."""
    settings: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")) or "=" not in line:
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def acquisition_key(platform: str, sensing: str) -> str:
    """Distinct-acquisition key of the gap survey: sensing date and platform letter."""
    return f"{sensing[:4]}-{sensing[4:6]}-{sensing[6:8]}/{platform[-1].lower()}"


def hours_between(start: str, end: str) -> float:
    """Hours from one ISO time to another. Both carry a zone."""
    first = datetime.fromisoformat(start.replace("Z", "+00:00"))
    last = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return round((last - first).total_seconds() / 3600, 2)


def published_at(scene: dict) -> str | None:
    """Earliest last-modified time across a scene's objects."""
    times = [layer["last_modified"] for layer in scene["layers"].values() if layer["last_modified"]]
    return min(times) if times else None


def es_product(item: dict) -> dict | None:
    """Product fields of a normalized Earth Search item, from its product name."""
    name = item.get("product_uri") or ""
    return parse_product(name.removesuffix(".SAFE"))


def join_scene(scene: dict, items_by_collection: dict[str, list[dict]], order: list[str]) -> dict:
    """Match one aquatic reflectance scene to Earth Search items of the same tile and pass.

    The candidate key is tile, platform, and sensing start from the product names. A match is
    exact when the processing baseline also agrees. Collections are tried in `order`, and the
    first collection with any match on the candidate key supplies the join.
    """
    record = {"product": scene["product"], "matches": {}, "joined": None, "status": "none"}
    for collection in order:
        hits = []
        for item in items_by_collection.get(collection, []):
            product = es_product(item)
            if product is None:
                continue
            if (product["tile"], product["platform"], product["sensing"]) == (
                scene["tile"],
                scene["platform"],
                scene["sensing"],
            ):
                hits.append(
                    {
                        "id": item["id"],
                        "baseline": product["baseline"],
                        "same_baseline": product["baseline"] == scene["baseline"],
                    }
                )
        record["matches"][collection] = hits
        if hits and record["joined"] is None:
            exact = [hit for hit in hits if hit["same_baseline"]]
            chosen = exact or hits
            record["joined"] = {"collection": collection, "ids": [hit["id"] for hit in chosen]}
            if exact:
                record["status"] = "exact" if len(exact) == 1 else "exact_multiple"
            else:
                record["status"] = "other_baseline" if len(hits) == 1 else "other_multiple"
    return record


def monthly_acquisitions(keys_by_month: dict[str, set[str]], months: list[str]) -> list[int]:
    return [len(keys_by_month.get(month, set())) for month in months]


def keys_by_month_of(entries: list[tuple[str, str]]) -> dict[str, set[str]]:
    """(platform, sensing) pairs grouped as distinct acquisition keys per YYYY-MM month."""
    out: dict[str, set[str]] = defaultdict(set)
    for platform, sensing in entries:
        out[f"{sensing[:4]}-{sensing[4:6]}"].add(acquisition_key(platform, sensing))
    return out


def counter_dict(values) -> dict[str, int]:
    return {str(k): v for k, v in sorted(Counter(values).items(), key=lambda kv: str(kv[0]))}


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile, None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), math.ceil(fraction * len(ordered))))
    return ordered[rank - 1]
