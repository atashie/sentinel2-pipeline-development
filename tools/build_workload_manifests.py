"""Select two public lake cohorts with bounded, saved NHD metadata requests.

The benchmark invokes this module only in an explicitly requested, supervised phase.
No imagery is read. Existing pilot manifests remain unchanged.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

import build_pilot_manifest as pilot  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from s2proto import harness  # noqa: E402
from s2proto.workload_resources import MIB, admit, write_json  # noqa: E402

SEED = "lake-workloads-2026-09-18"
AREA_BANDS = {
    "small": "AREASQKM > 0 AND AREASQKM < 0.1",
    "medium": "AREASQKM >= 0.1 AND AREASQKM < 1",
    "large": "AREASQKM >= 1",
}
FLORIDA_BOXES = [
    [-82.05, 28.2, -81.25, 29.15],
    [-82.2, 28.0, -81.05, 29.3],
    [-82.4, 27.8, -80.85, 29.5],
]
SOURCE_FIELDS = pilot.OUT_FIELDS
IDENTIFIER_BATCH = 10_000
MAX_SUBDIVISIONS = 10


def stable_key(value):
    return hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()


def area_band(area_m2):
    return "small" if area_m2 < 100_000 else "medium" if area_m2 < 1_000_000 else "large"


class MetadataClient:
    """Bounded responses and recorded request-level retries. Reuse saved metadata only."""

    def __init__(self, directory, pause=0.2):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pause = pause
        self.last_request_finished = 0.0

    def request(self, url, body=None):
        encoded = json.dumps(body, sort_keys=True).encode() if body is not None else None
        key = hashlib.sha256(url.encode() + (encoded or b"")).hexdigest()
        path = self.directory / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())["response"]
        for attempt in range(1, 4):
            admit(160 * MIB)
            time.sleep(max(0.0, self.pause - (time.perf_counter() - self.last_request_finished)))
            started = time.perf_counter()
            record = {"url": url, "body": body, "attempt": attempt, "started_at": harness.utc_now()}
            request = urllib.request.Request(
                url,
                data=encoded,
                headers={
                    "User-Agent": "sentinel2-workload-assessment",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            error = None
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    raw = response.read(16 * MIB + 1)
                    if len(raw) > 16 * MIB:
                        raise ValueError("metadata response exceeds 16 MiB bound")
                    record.update(status=response.status, bytes_delivered=len(raw))
                value = json.loads(raw)
                if "error" in value:
                    raise ValueError(f"provider error: {value['error']}")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                error = exc
                record["error"] = str(exc)
            finally:
                self.last_request_finished = time.perf_counter()
                record["seconds"] = time.perf_counter() - started
                with (self.directory / "requests.jsonl").open("a") as stream:
                    stream.write(json.dumps(record) + "\n")
            if error is None:
                write_json(path, {"request": record, "response": value})
                return value
            if attempt == 3:
                raise error
            time.sleep(attempt)
        raise RuntimeError("unreachable")


def query_url(parameters):
    return f"{pilot.SERVICE}/{pilot.LAYER}/query?{urllib.parse.urlencode(parameters)}"


def candidate_ids(client, bbox, band, *, limit=None, audit=None):
    """Count and subdivide requests. Deduplicate and rank IDs on disk, not in a giant list."""
    audit = audit if audit is not None else {}
    audit.update(bbox=bbox, band=band, queries=[], shortages=[])
    index = client.directory / f"ids-{stable_key(json.dumps([bbox, band]))}.sqlite"
    database = sqlite3.connect(index)
    database.execute("PRAGMA cache_size=-4096")
    database.execute("CREATE TABLE IF NOT EXISTS ids (id INTEGER PRIMARY KEY,rank TEXT)")
    database.execute("DELETE FROM ids")
    params = {
        "f": "json",
        "where": f"FCODE IN ({','.join(map(str, pilot.FCODES))}) AND " + AREA_BANDS[band],
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
    }

    def collect(bounds, depth):
        query = {**params, "geometry": ",".join(map(str, bounds))}
        record = {"bbox": bounds, "depth": depth}
        audit["queries"].append(record)
        try:
            count = client.request(query_url({**query, "returnCountOnly": "true"}))["count"]
            record["count"] = count
            if not isinstance(count, int) or count < 0:
                raise ValueError("invalid identifier count")
            if count == 0:
                return
            if count <= IDENTIFIER_BATCH:
                response = client.request(query_url({**query, "returnIdsOnly": "true"}))
                ids = response.get("objectIds") or []
                if not response.get("exceededTransferLimit") and len(ids) <= IDENTIFIER_BATCH:
                    if len(set(ids)) != count:
                        raise ValueError("count and distinct identifiers disagree")
                    database.executemany(
                        "INSERT OR IGNORE INTO ids VALUES (?,?)",
                        ((value, stable_key(value)) for value in ids),
                    )
                    record["returned_ids"] = len(ids)
                    return
            if depth >= MAX_SUBDIVISIONS:
                raise ValueError("identifier subdivision limit reached")
            x0, y0, x1, y1 = bounds
            if (x1 - x0) * math.cos(math.radians((y0 + y1) / 2)) >= y1 - y0:
                midpoint = (x0 + x1) / 2
                parts = [[x0, y0, midpoint, y1], [midpoint, y0, x1, y1]]
            else:
                midpoint = (y0 + y1) / 2
                parts = [[x0, y0, x1, midpoint], [x0, midpoint, x1, y1]]
            record["subdivided"] = True
            for part in parts:
                collect(part, depth + 1)
        except (OSError, TimeoutError, ValueError, KeyError) as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            audit["shortages"].append(record.copy())

    try:
        collect(bbox, 0)
        database.commit()
        audit["available_ids"] = database.execute("SELECT COUNT(*) FROM ids").fetchone()[0]
        audit["complete"] = not audit["shortages"]
    finally:
        database.close()
    write_json(index.with_suffix(".audit.json"), audit)

    def ordered_ids():
        connection = sqlite3.connect(index)
        connection.execute("PRAGMA cache_size=-4096")
        connection.execute("PRAGMA temp_store=FILE")
        try:
            query = "SELECT id FROM ids ORDER BY rank,id"
            if limit is not None:
                query += " LIMIT ?"
            for row in connection.execute(query, (limit,) if limit is not None else ()):
                yield row[0]
        finally:
            connection.close()

    return ordered_ids()


def fetch_candidates(client, object_ids, *, audit=None):
    for batch in itertools.batched(object_ids, 20):
        params = {
            "f": "geojson",
            "objectIds": ",".join(map(str, batch)),
            "outFields": SOURCE_FIELDS,
            "outSR": 4326,
            "returnGeometry": "true",
        }
        try:
            page = client.request(query_url(params))
            if page.get("exceededTransferLimit"):
                raise ValueError("NHD geometry response was truncated")
        except (OSError, TimeoutError, ValueError) as exc:
            if audit is None:
                raise
            audit.setdefault("geometry_shortages", []).append(
                {"object_ids": list(batch), "error": str(exc)}
            )
            continue
        for feature in page.get("features", []):
            candidate = pilot.candidate(feature)
            if candidate is None:
                continue
            geometry = shape(candidate["geometry"])
            if not geometry.is_valid or geometry.is_empty:
                continue
            point = geometry.representative_point()
            candidate["center"] = [point.x, point.y]
            candidate["area_band"] = area_band(candidate["area_m2"])
            yield candidate


def inside(point, bbox):
    return bbox[0] <= point[0] < bbox[2] and bbox[1] <= point[1] < bbox[3]


def quotas(available, count):
    """Balance area bands where available, then distribute shortages deterministically."""
    if sum(available.values()) < count:
        raise ValueError("insufficient distinct eligible lakes")
    result = {key: 0 for key in available}
    while sum(result.values()) < count:
        for key in available:
            if result[key] < available[key] and sum(result.values()) < count:
                result[key] += 1
    return result


def save_candidate(database, candidate, stratum):
    database.execute(
        "INSERT OR IGNORE INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            candidate["source_id"],
            stratum,
            candidate["area_band"],
            *candidate["center"],
            stable_key(candidate["source_id"]),
            json.dumps(candidate),
        ),
    )


def select_spread(database, count):
    """Round-robin occupied strata and area bands, maximizing local separation."""
    strata = [r[0] for r in database.execute("SELECT DISTINCT stratum FROM candidates ORDER BY 1")]
    selected, centers = [], {s: [] for s in strata}
    used = set()
    while len(selected) < count:
        progress = False
        for stratum in strata:
            if len(selected) == count:
                break
            options = database.execute(
                "SELECT id,band,x,y,rank FROM candidates WHERE stratum=? ORDER BY rank", (stratum,)
            ).fetchall()
            options = [r for r in options if r[0] not in used]
            if not options:
                continue
            band = list(AREA_BANDS)[len(centers[stratum]) % 3]
            options = [r for r in options if r[1] == band] or options

            def score(row, stratum=stratum):
                distances = [
                    ((row[2] - x) * math.cos(math.radians(row[3]))) ** 2 + (row[3] - y) ** 2
                    for x, y in centers[stratum]
                ]
                return (-min(distances, default=0), row[4])

            chosen = min(options, key=score)
            selected.append((chosen[0], stratum))
            centers[stratum].append((chosen[2], chosen[3]))
            used.add(chosen[0])
            progress = True
        if not progress:
            raise ValueError("insufficient dispersed candidates")
    return selected


def write_manifest(database, selection, directory, cohort, details):
    directory = Path(directory)
    (directory / "lakes").mkdir(parents=True, exist_ok=True)
    index = []
    for source_id, stratum in selection:
        candidate = json.loads(
            database.execute("SELECT feature FROM candidates WHERE id=?", (source_id,)).fetchone()[
                0
            ]
        )
        # Separate dispersed lakes are local acquisition groups. Florida shares one group.
        region = "florida" if cohort == "florida" else pilot.water_body_id(source_id)
        feature = pilot.manifest_feature(
            candidate,
            {
                "region_id": region,
                "name": stratum,
                "survey_site_id": None,
                "setting": "public workload comparison",
            },
            "workload",
            [10, 30, 100, 300, 1000, 3000],
            harness.utc_now(),
            "Deterministic geographic and area selection. " + details["selection_rule"],
        )
        feature["properties"].update(area_band=candidate["area_band"], stratum=stratum)
        lid = feature["properties"]["water_body_id"]
        path = directory / "lakes" / f"{lid}.geojson"
        write_json(path, feature)
        index.append(
            {
                "id": lid,
                "path": str(path),
                "region": region,
                "area_m2": candidate["area_m2"],
                "area_band": candidate["area_band"],
                "center": candidate["center"],
                "bbox": feature["bbox"],
                "vertices": feature["properties"]["vertex_count"],
                "polygon_sha256": hashlib.sha256(
                    json.dumps(feature["geometry"], sort_keys=True).encode()
                ).hexdigest(),
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "created_at": harness.utc_now(),
        "cohort": cohort,
        "lakes": index,
        "seed": SEED,
        "source": pilot.SERVICE,
        "source_layer": pilot.LAYER,
        "source_region": "United States",
        "payer": "public metadata, no requester-pays",
        "source_codes": pilot.FCODES,
        "area_bands_m2": [100_000, 1_000_000],
        "boundary_limitations": "Mapped public geometry, not verified current shoreline or water.",
        **details,
    }
    write_json(directory / "manifest.json", manifest)
    return manifest


def build(cohort, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    client = MetadataClient(directory / "boundary-responses")
    database = sqlite3.connect(directory / "candidates.sqlite")
    database.execute("PRAGMA cache_size=-8192")
    database.execute(
        "CREATE TABLE IF NOT EXISTS candidates "
        "(id TEXT PRIMARY KEY,stratum TEXT,band TEXT,x REAL,y REAL,rank TEXT,"
        "feature TEXT)"
    )
    if cohort == "dispersed":
        boxes = []
        for column in range(8):
            for row in range(4):
                boxes.append(
                    [
                        -124.8 + column * 7.25,
                        24.5 + row * 6.225,
                        -124.8 + (column + 1) * 7.25,
                        24.5 + (row + 1) * 6.225,
                    ]
                )
        supply = []
        for number, bbox in enumerate(boxes):
            stratum = f"us-{number:02d}"
            for band in AREA_BANDS:
                audit = {"stratum": stratum}
                ids = candidate_ids(client, bbox, band, limit=48, audit=audit)
                supply.append(audit)
                # Fixed, hashed candidate sample, without an upper lake-area cap.
                for candidate in fetch_candidates(client, ids, audit=audit):
                    if inside(candidate["center"], bbox):
                        save_candidate(database, candidate, stratum)
            database.commit()
            print(f"boundary stratum {number + 1}/{len(boxes)}", flush=True)
        selection = select_spread(database, 100)
        details = {
            "boxes": boxes,
            "candidate_supply": supply,
            "selection_rule": "Round-robin occupied geographic strata and area bands. "
            "Prefer farthest candidates within each stratum, with fixed hash ties. "
            "Candidate sample: first 48 hashed source object IDs per stratum and band.",
        }
    elif cohort == "florida":
        query_audits = []
        for bbox in FLORIDA_BOXES:
            for band in AREA_BANDS:
                audit = {}
                ids = candidate_ids(client, bbox, band, audit=audit)
                query_audits.append(audit)
                for candidate in fetch_candidates(client, ids, audit=audit):
                    if inside(candidate["center"], bbox):
                        save_candidate(database, candidate, "central-florida")
                database.commit()
            available = dict(database.execute("SELECT band,COUNT(*) FROM candidates GROUP BY band"))
            if sum(available.values()) >= 1000:
                break
        requested = quotas({b: available.get(b, 0) for b in AREA_BANDS}, 1000)
        selection = []
        for band, count in requested.items():
            rows = database.execute(
                "SELECT id,x,y,rank FROM candidates WHERE band=?", (band,)
            ).fetchall()
            rows.sort(key=lambda r: (((r[1] + 81.65) * 0.88) ** 2 + (r[2] - 28.675) ** 2, r[3]))
            selection.extend((r[0], "central-florida") for r in rows[:count])
        details = {
            "bbox": bbox,
            "candidate_supply": available,
            "query_audits": query_audits,
            "selected_by_band": requested,
            "selection_rule": "Balance available area bands, filling shortages in order. "
            "Within each band prefer proximity to (-81.65, 28.675), with fixed hash ties.",
        }
    else:
        raise ValueError(cohort)
    manifest = write_manifest(database, selection, directory, cohort, details)
    database.close()
    return {"manifest": str(directory / "manifest.json"), "lake_count": len(manifest["lakes"])}
