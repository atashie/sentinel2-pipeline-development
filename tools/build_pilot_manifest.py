"""Build the public pilot water-body manifest from the USGS National Hydrography Dataset.

Two modes. With `--fetch`, the script contacts The National Map hydro service once per region
box and once per anchor lake, and saves every response under data/pilot-manifest/<time>/.
Without `--fetch`, it rebuilds the manifest from the newest saved run and contacts nothing.

    uv run python tools/build_pilot_manifest.py --fetch
    uv run python tools/build_pilot_manifest.py

Selection, per region and size class: among the lakes and ponds in the region box with an
allowed feature code, take the one whose width is nearest the class width. Width is the square
root of the polygon area. Anchor lakes come from a point query at the gap survey site.
Polygons only. No imagery, no catalog, no credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
LAYER = 12
SOURCE = "USGS National Hydrography Dataset, Waterbody - Large Scale layer"
PROVIDER = "U.S. Geological Survey, The National Map"
TERMS_URL = (
    "https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map"
)
TERMS_CHECKED = "2026-09-11"
TERMS_TEXT = (
    "Map services and data downloaded from The National Map are free and in the public domain."
)
ACKNOWLEDGMENT = (
    "Map services and data available from U.S. Geological Survey, National Geospatial Program."
)
USER_AGENT = "sentinel2-pipeline-development pilot manifest (polygons only, no imagery)"
# NHD feature codes kept: lake or pond (feature type 390) with a perennial or unspecified
# hydrographic category, and reservoir (436) codes for water storage or an unspecified type.
# Intermittent ponds, aquaculture, treatment, disposal, evaporation, cooling, and swimming
# pools are left out.
FCODES = [39000, 39004, 39009, 39010, 39011, 39012, 43600, 43613, 43615, 43617, 43618, 43619, 43621]
CANDIDATE_LIMIT_KM2 = 5.0
PAGE = 1000
COORD_DECIMALS = 6
EARTH_RADIUS_M = 6371008.8
OUT_FIELDS = (
    "PERMANENT_IDENTIFIER,GNIS_ID,GNIS_NAME,FTYPE,FCODE,AREASQKM,REACHCODE,FDATE,RESOLUTION"
)


# ---------------------------------------------------------------- pure helpers


def class_bounds(classes: list[int]) -> list[float]:
    """Upper width bound of every class but the last: the geometric midpoint to the next."""
    return [math.sqrt(a * b) for a, b in zip(classes, classes[1:], strict=False)]


def size_class(width_m: float, classes: list[int]) -> int:
    """The size class a width falls in. The last class is open-ended."""
    for cls, bound in zip(classes, class_bounds(classes), strict=False):
        if width_m < bound:
            return cls
    return classes[-1]


def ring_area_m2(ring: list) -> float:
    """Unsigned ring area by the shoelace formula on a local equirectangular plane."""
    if len(ring) < 4:
        return 0.0
    lat0 = math.radians(sum(point[1] for point in ring) / len(ring))
    kx = EARTH_RADIUS_M * math.cos(lat0) * math.pi / 180
    ky = EARTH_RADIUS_M * math.pi / 180
    lon0 = ring[0][0]
    total = 0.0
    for a, b in zip(ring, ring[1:], strict=False):
        ax, ay = (a[0] - lon0) * kx, a[1] * ky
        bx, by = (b[0] - lon0) * kx, b[1] * ky
        total += ax * by - bx * ay
    return abs(total) / 2


def polygon_area_m2(geometry: dict) -> float:
    """Area of a Polygon or MultiPolygon in square meters, holes removed."""
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"not a polygon: {geometry['type']}")
    total = 0.0
    for rings in polygons:
        outer = ring_area_m2(rings[0])
        holes = sum(ring_area_m2(ring) for ring in rings[1:])
        total += max(outer - holes, 0.0)
    return total


def _points(node):
    if isinstance(node[0], int | float):
        yield node
    else:
        for child in node:
            yield from _points(child)


def geometry_bbox(geometry: dict) -> list[float]:
    """West, south, east, north."""
    points = list(_points(geometry["coordinates"]))
    return [
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    ]


def vertex_count(geometry: dict) -> int:
    return sum(1 for _ in _points(geometry["coordinates"]))


def round_coordinates(node, decimals: int = COORD_DECIMALS):
    """Round every coordinate and drop any third dimension."""
    if isinstance(node[0], int | float):
        return [round(node[0], decimals), round(node[1], decimals)]
    return [round_coordinates(child, decimals) for child in node]


def candidate(feature: dict) -> dict | None:
    """Normalize one service feature. None when its code or geometry disqualifies it."""
    props = feature.get("properties") or {}
    geometry = feature.get("geometry")
    if props.get("FCODE") not in FCODES or not geometry:
        return None
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    if props.get("PERMANENT_IDENTIFIER") in (None, ""):
        return None
    rounded = {"type": geometry["type"], "coordinates": round_coordinates(geometry["coordinates"])}
    area = polygon_area_m2(rounded)
    if area < 1.0:
        return None
    return {
        "source_id": str(props["PERMANENT_IDENTIFIER"]),
        "props": props,
        "geometry": rounded,
        "area_m2": area,
        "width_m": math.sqrt(area),
    }


def select_by_class(candidates: list[dict], classes: list[int]) -> dict[int, dict]:
    """The candidate nearest each class width. Ties go to the smaller source id."""
    best: dict[int, tuple] = {}
    for cand in candidates:
        cls = size_class(cand["width_m"], classes)
        key = (abs(math.log(cand["width_m"] / cls)), cand["source_id"])
        if cls not in best or key < best[cls][0]:
            best[cls] = (key, cand)
    return {cls: best[cls][1] for cls in sorted(best)}


def water_body_id(source_id: str) -> str:
    return "nhd-" + source_id.strip("{}").lower()


def feature_date(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, UTC).date().isoformat()


def manifest_feature(
    cand: dict, region: dict, tier: str, classes: list[int], accessed: str, why: str
) -> dict:
    props = cand["props"]
    width = cand["width_m"]
    name = props.get("GNIS_NAME") or f"Unnamed water body, {region['name']}"
    return {
        "type": "Feature",
        "id": water_body_id(cand["source_id"]),
        "bbox": geometry_bbox(cand["geometry"]),
        "geometry": cand["geometry"],
        "properties": {
            "water_body_id": water_body_id(cand["source_id"]),
            "name": name,
            "source": SOURCE,
            "source_id": cand["source_id"],
            "source_accessed": accessed[:10],
            "polygon_version": 1,
            "region": region["region_id"],
            "survey_site_id": region["survey_site_id"],
            "setting": region["setting"],
            "tier": tier,
            "size_class_m": size_class(width, classes),
            "width_m": round(width, 1),
            "area_m2": round(cand["area_m2"], 1),
            "fcode": props.get("FCODE"),
            "gnis_id": props.get("GNIS_ID"),
            "reachcode": props.get("REACHCODE"),
            "nhd_feature_date": feature_date(props.get("FDATE")),
            "vertex_count": vertex_count(cand["geometry"]),
            "why": why,
        },
    }


def build_manifest(config: dict, raw: dict) -> dict:
    """Derive the manifest from the region config and one saved fetch run."""
    classes = config["size_classes_m"]
    accessed = raw["fetch"]["accessed_at"]
    features = []
    by_region: dict[str, dict] = {}
    for region in config["regions"]:
        rid = region["region_id"]
        saved = raw["regions"][rid]
        pages = saved["candidates"]["pages"]
        candidates = [c for page in pages for f in page.get("features", []) if (c := candidate(f))]
        picks = select_by_class(candidates, classes)
        region_features = []
        if region["include_anchor"]:
            anchors = [c for f in saved["anchor"].get("features", []) if (c := candidate(f))]
            if len(anchors) != 1:
                raise ValueError(f"{rid}: expected one anchor water body, found {len(anchors)}")
            region_features.append(
                manifest_feature(anchors[0], region, "large", classes, accessed, region["why"])
            )
        for cls, cand in picks.items():
            why = (
                f"Size class {cls} m for region {rid}. "
                f"Nearest width to {cls} m among {len(candidates)} candidates."
            )
            region_features.append(manifest_feature(cand, region, "pilot", classes, accessed, why))
        features.extend(region_features)
        by_region[rid] = {
            "candidates": len(candidates),
            "features": len(region_features),
            "size_classes_m": sorted(picks),
            "anchor": bool(region["include_anchor"]),
        }
    ids = [f["id"] for f in features]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate water body ids")
    by_class: dict[str, int] = {}
    by_setting: dict[str, int] = {}
    for f in features:
        p = f["properties"]
        by_class[str(p["size_class_m"])] = by_class.get(str(p["size_class_m"]), 0) + 1
        by_setting[p["setting"]] = by_setting.get(p["setting"], 0) + 1
    service = raw["service"]
    layer = raw["layer"]
    fetch = raw["fetch"]
    return {
        "type": "FeatureCollection",
        "manifest_version": 1,
        "note": (
            "Public pilot water bodies for prototypes, derived by tools/build_pilot_manifest.py "
            "from examples/pilot-regions.json. Customer water bodies never enter this "
            "repository (assumption A8). Tile membership is not recorded here. The gap survey "
            "discovers it from the catalog."
        ),
        "dataset": {
            "name": SOURCE,
            "provider": PROVIDER,
            "service": SERVICE,
            "layer": LAYER,
            "layer_name": layer.get("name"),
            "service_copyright": service.get("copyrightText"),
            "layer_copyright": layer.get("copyrightText"),
            "terms": {"url": TERMS_URL, "checked": TERMS_CHECKED, "text": TERMS_TEXT},
            "acknowledgment": ACKNOWLEDGMENT,
        },
        "retrieval": {
            "accessed_at": accessed,
            "script": "tools/build_pilot_manifest.py",
            "code_version": fetch["code_version"],
            "config_sha256": fetch["config_sha256"],
            "requests_total": len(fetch["requests"]),
            "bytes_total": sum(r["bytes"] for r in fetch["requests"]),
            "raw_files": fetch["files"],
            "requests": fetch["requests"],
        },
        "selection": {
            "size_classes_m": classes,
            "class_upper_bounds_m": [round(b, 1) for b in class_bounds(classes)],
            "fcodes_kept": FCODES,
            "candidate_area_limit_km2": CANDIDATE_LIMIT_KM2,
            "coordinate_decimals": COORD_DECIMALS,
            "rule": (
                "Per region and size class, the candidate whose width is nearest the class "
                "width, by absolute log ratio. Ties go to the smaller source id. Width is the "
                "square root of the area."
            ),
            "area_method": (
                "Shoelace formula on a local equirectangular plane per ring, sphere radius "
                f"{EARTH_RADIUS_M} m, holes subtracted, computed after coordinate rounding."
            ),
        },
        "summary": {
            "features": len(features),
            "by_region": by_region,
            "by_size_class_m": by_class,
            "by_setting": by_setting,
            "by_tier": {
                "large": sum(1 for f in features if f["properties"]["tier"] == "large"),
                "pilot": sum(1 for f in features if f["properties"]["tier"] == "pilot"),
            },
            "vertices": sum(f["properties"]["vertex_count"] for f in features),
        },
        "features": features,
    }


def dump_manifest(manifest: dict, path: Path) -> None:
    """Pretty metadata, then one compact feature per line, as one valid JSON document."""
    head = {key: value for key, value in manifest.items() if key != "features"}
    text = json.dumps(head, indent=1)
    assert text.endswith("\n}")
    lines = [json.dumps(f, separators=(",", ":")) for f in manifest["features"]]
    body = ",\n  ".join(lines)
    path.write_text(text[:-2] + ',\n "features": [\n  ' + body + "\n ]\n}\n")


# ---------------------------------------------------------------- fetching


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_version() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        return head + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


class Client:
    """GET JSON with a pause between requests, retries on transient errors, and a log."""

    def __init__(self, pause: float = 0.3, retries: int = 4, timeout: float = 120.0):
        self.pause = pause
        self.retries = retries
        self.timeout = timeout
        self.log: list[dict] = []

    def get_json(self, url: str, note: str) -> dict:
        host = urllib.parse.urlparse(url).netloc
        headers = {"accept": "application/json", "user-agent": USER_AGENT}
        delay = 2.0
        for attempt in range(1, self.retries + 1):
            request = urllib.request.Request(url, headers=headers)
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
            self.log.append(
                {
                    "host": host,
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
                document = json.loads(raw)
                if isinstance(document, dict) and "error" in document:
                    raise RuntimeError(f"service error for {note}: {document['error']}")
                return document
            retryable = status is None or status in (408, 429, 500, 502, 503, 504)
            if retryable and attempt < self.retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"{status} from {url}: {raw[:300]!r}") from error
        raise RuntimeError("unreachable")


def query_url(params: dict) -> str:
    return f"{SERVICE}/{LAYER}/query?" + urllib.parse.urlencode(params)


def box_params(box: dict, offset: int) -> dict:
    h = box["half_width_deg"]
    west, east = box["longitude"] - h, box["longitude"] + h
    south, north = box["latitude"] - h, box["latitude"] + h
    codes = ",".join(str(c) for c in FCODES)
    return {
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "where": f"FTYPE IN (390,436) AND AREASQKM < {CANDIDATE_LIMIT_KM2} AND FCODE IN ({codes})",
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "outSR": 4326,
        "orderByFields": "OBJECTID ASC",
        "resultOffset": offset,
        "resultRecordCount": PAGE,
        "f": "geojson",
    }


def point_params(site: dict) -> dict:
    return {
        "geometry": f"{site['longitude']},{site['latitude']}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "where": "FTYPE IN (390,436)",
        "outFields": OUT_FIELDS,
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "geojson",
    }


def fetch_run(config: dict, sites: dict, run_dir: Path, config_path: Path, pause: float) -> None:
    """Contact the service and save every response under run_dir."""
    run_dir.mkdir(parents=True, exist_ok=True)
    client = Client(pause=pause)
    accessed = datetime.now(UTC).isoformat(timespec="seconds")

    def save(document: dict, name: str) -> None:
        (run_dir / name).write_text(json.dumps(document) + "\n")

    save(client.get_json(f"{SERVICE}?f=json", "service"), "service.json")
    save(client.get_json(f"{SERVICE}/{LAYER}?f=json", "layer"), "layer.json")
    for region in config["regions"]:
        rid = region["region_id"]
        pages, offset = [], 0
        while True:
            page = client.get_json(query_url(box_params(region["box"], offset)), f"{rid} box")
            pages.append(page)
            count = len(page.get("features", []))
            print(f"{rid}: {count} features at offset {offset}", flush=True)
            if count < PAGE:
                break
            offset += count
        save({"pages": pages}, f"{rid}-candidates.json")
        if region["include_anchor"]:
            site = sites[region["survey_site_id"]]
            page = client.get_json(query_url(point_params(site)), f"{rid} anchor")
            print(f"{rid}: anchor features {len(page.get('features', []))}", flush=True)
            save(page, f"{rid}-anchor.json")
    files = {p.name: sha256_file(p) for p in sorted(run_dir.iterdir()) if p.name != "fetch.json"}
    fetch = {
        "accessed_at": accessed,
        "script": "tools/build_pilot_manifest.py",
        "code_version": code_version(),
        "config_sha256": sha256_file(config_path),
        "files": files,
        "requests": client.log,
    }
    (run_dir / "fetch.json").write_text(json.dumps(fetch, indent=1) + "\n")
    print(f"saved {len(client.log)} responses under {run_dir}", flush=True)


def load_run(config: dict, run_dir: Path, config_path: Path) -> dict:
    """Load a saved run only when its configuration and saved files still match."""
    fetch = json.loads((run_dir / "fetch.json").read_text())
    if sha256_file(config_path) != fetch["config_sha256"]:
        raise ValueError("configuration differs from the saved fetch run")

    def read(name: str) -> dict:
        path = run_dir / name
        if name not in fetch["files"] or sha256_file(path) != fetch["files"][name]:
            raise ValueError(f"saved response differs from its recorded digest: {name}")
        return json.loads(path.read_text())

    regions = {}
    for region in config["regions"]:
        rid = region["region_id"]
        regions[rid] = {
            "candidates": read(f"{rid}-candidates.json"),
            "anchor": read(f"{rid}-anchor.json") if region["include_anchor"] else None,
        }
    return {
        "service": read("service.json"),
        "layer": read("layer.json"),
        "fetch": fetch,
        "regions": regions,
    }


def newest_run(parent: Path) -> Path:
    runs = sorted(p for p in parent.iterdir() if (p / "fetch.json").exists())
    if not runs:
        raise SystemExit(f"no saved run under {parent}. Run with --fetch first.")
    return runs[-1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, default=ROOT / "examples" / "pilot-regions.json")
    parser.add_argument("--sites", type=Path, default=ROOT / "benchmarks" / "gap-survey-sites.json")
    parser.add_argument("--fetch", action="store_true", help="Contact the USGS service")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "pilot-manifest")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "examples" / "water-bodies-public-pilot.geojson"
    )
    parser.add_argument("--pause", type=float, default=0.3, help="Seconds between requests")
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text())
    sites = {s["site_id"]: s for s in json.loads(args.sites.read_text())["sites"]}
    if args.fetch:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_dir = args.raw_dir / stamp
        fetch_run(config, sites, run_dir, args.config, args.pause)
    else:
        explicit = (args.raw_dir / "fetch.json").exists()
        run_dir = args.raw_dir if explicit else newest_run(args.raw_dir)
    manifest = build_manifest(config, load_run(config, run_dir, args.config))
    dump_manifest(manifest, args.output)
    summary = manifest["summary"]
    print(
        f"wrote {args.output}: {summary['features']} features, {summary['vertices']} vertices, "
        f"from {run_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
