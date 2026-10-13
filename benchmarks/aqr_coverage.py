"""Probes T2 and T3: coverage of the USGS aquatic reflectance product, and its join to Level-2A.

Runs only when the user invokes it. Metadata only, unsigned, no credentials. For each gap survey
tile in the lower 48 states it lists every aquatic reflectance object in the public USGS bucket
and every Earth Search item in the Level-1C, Collection 1 Level-2A, and older Level-2A
collections over the window. It reads no object body and no pixel. Tiles outside the lower 48
get one bucket listing each, to record whether the bucket holds them.

T2 counts distinct acquisitions per month against Earth Search, the baseline mix, duplicates,
and the time from sensing to the bucket's object timestamps. T3 joins every aquatic reflectance
scene to Earth Search Level-2A items by tile, platform, and sensing start, Collection 1 first.
Probes T2 and T3 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.

    uv run python benchmarks/aqr_coverage.py --dry-run
    uv run python benchmarks/aqr_coverage.py
    uv run python benchmarks/aqr_coverage.py --from-raw data/aqr-coverage/STAMP
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))
import gap_survey as gs  # noqa: E402

from s2proto import aqr, harness  # noqa: E402

GAP_SURVEY = ROOT / "benchmarks" / "results" / "gap-survey.json"
L1C = "sentinel-2-l1c"
C1 = "sentinel-2-c1-l2a"
OLDER = "sentinel-2-l2a"
ES_COLLECTIONS = [L1C, C1, OLDER]
JOIN_ORDER = [C1, OLDER]
# Survey tiles outside the lower 48: one Alaska tile and the three context sites' tiles.
OUTSIDE = {"05VLG", "31TGM", "32TLS", "36MVE", "60HUC", "60HVC"}
DEFAULT_START = "2015-06-01"
RECENT_DAYS = 120
# Earth Search Level-1C cloud cover bins, percent, lower bound inclusive.
CLOUD_BINS = [(0, 10), (10, 25), (25, 50), (50, 75), (75, 101)]


def survey_tiles(gap_survey: dict) -> tuple[list[str], list[str]]:
    """The gap survey's tiles, split into lower 48 and outside."""
    tiles = sorted(gap_survey["tiles"])
    return [t for t in tiles if t not in OUTSIDE], [t for t in tiles if t in OUTSIDE]


def plan(inside: list[str], outside: list[str], start: str, end: str) -> list[str]:
    return [
        f"Window {start} to {end}. Bucket {aqr.BUCKET}, region {aqr.REGION}, unsigned.",
        f"1. Lower 48, {len(inside)} tiles: {', '.join(inside)}.",
        f"   Per tile: list every object under {aqr.VERSION_PREFIX}T<tile>/, every page.",
        f"   Per tile: Earth Search listings in {', '.join(ES_COLLECTIONS)}, catalog fields.",
        f"2. Outside the lower 48, {len(outside)} tiles: {', '.join(outside)}.",
        "   Per tile: one bucket listing of up to 1,000 keys. No Earth Search request.",
        "No object body is read. No pixel is read. Raw listings go under data/aqr-coverage/.",
        "Writes benchmarks/results/aqr-coverage.json.",
    ]


def list_prefix(client, prefix: str, note: str, max_pages: int | None = None) -> list[dict]:
    keys: list[dict] = []
    token = None
    page = 0
    while True:
        page += 1
        text, _ = client.get_text(aqr.list_url(prefix, None, token), f"{note} page {page}")
        listing = aqr.parse_listing(text)
        keys.extend(listing["keys"])
        if not listing["truncated"] or (max_pages and page >= max_pages):
            return keys
        token = listing["next_token"]


def collect(args, inside, outside, raw_dir: Path) -> dict:
    s3 = harness.Client(pause=0.05)
    es = gs.Client(pause=0.2)
    for tile in inside:
        objects = list_prefix(s3, f"{aqr.VERSION_PREFIX}T{tile}/", f"aqr {tile}")
        (raw_dir / f"aqr-{tile}.json").write_text(json.dumps(objects, separators=(",", ":")))
        print(f"{tile}: {len(objects)} aquatic reflectance objects", flush=True)
        for collection in ES_COLLECTIONS:
            features = gs.es_list(es, collection, tile, args.start, args.end)
            path = raw_dir / f"es-{tile}-{collection}.json"
            path.write_text(json.dumps(features, separators=(",", ":")))
            print(f"  {collection}: {len(features)} items", flush=True)
    for tile in outside:
        objects = list_prefix(s3, f"{aqr.VERSION_PREFIX}T{tile}/", f"presence {tile}", max_pages=1)
        (raw_dir / f"presence-{tile}.json").write_text(json.dumps(objects, separators=(",", ":")))
        print(f"{tile}: {len(objects)} keys in the first page", flush=True)
    return {"s3": s3.log, "earth_search": es.log}


def latency_stats(hours: list[float]) -> dict:
    days = [h / 24 for h in hours]
    return {
        "scenes": len(days),
        "median_days": round(aqr.percentile(days, 0.5), 2) if days else None,
        "p90_days": round(aqr.percentile(days, 0.9), 2) if days else None,
        "min_days": round(min(days), 2) if days else None,
        "max_days": round(max(days), 2) if days else None,
    }


def cloud_bin(cover: float) -> str:
    for low, high in CLOUD_BINS:
        if low <= cover < high:
            return f"{low}-{min(high, 100)}"
    raise ValueError(f"cloud cover out of range: {cover}")


def cloud_comparison(l1c_items: list[dict], tile: str, aqr_keys: set[str]) -> dict:
    """Level-1C cloud cover of Earth Search acquisitions with and without a product scene.

    An acquisition with several Level-1C items keeps the lowest cloud cover.
    """
    cover: dict[str, float] = {}
    for item in l1c_items:
        if item["tile"] != tile or not item["datetime"] or item["cloud_cover"] is None:
            continue
        key = gs.sensing_key(item)
        cover[key] = min(float(item["cloud_cover"]), cover.get(key, 101.0))
    present = sorted(v for k, v in cover.items() if k in aqr_keys)
    missing = sorted(v for k, v in cover.items() if k not in aqr_keys)
    bins = {"present": Counter(), "missing": Counter()}
    for key, value in cover.items():
        bins["present" if key in aqr_keys else "missing"][cloud_bin(value)] += 1
    labels = [f"{low}-{min(high, 100)}" for low, high in CLOUD_BINS]
    return {
        "bins": {side: {label: bins[side].get(label, 0) for label in labels} for side in bins},
        "present_max": present[-1] if present else None,
        "present_median": aqr.percentile(present, 0.5),
        "missing_min": missing[0] if missing else None,
        "missing_median": aqr.percentile(missing, 0.5),
        "acquisitions_with_cover": len(cover),
    }


def nodata_comparison(l2a_items: list[dict], tile: str, aqr_keys: set[str]) -> dict:
    """Level-2A no-data share of Earth Search acquisitions with and without a product scene.

    Level-1C items carry no no-data share, so this uses both Level-2A collections. An
    acquisition with several items keeps the lowest share.
    """
    share: dict[str, float] = {}
    for item in l2a_items:
        if item["tile"] != tile or not item["datetime"] or item["nodata_pct"] is None:
            continue
        key = gs.sensing_key(item)
        share[key] = min(float(item["nodata_pct"]), share.get(key, 101.0))
    present = [v for k, v in share.items() if k in aqr_keys]
    missing = [v for k, v in share.items() if k not in aqr_keys]
    return {
        "present_median": aqr.percentile(present, 0.5),
        "missing_median": aqr.percentile(missing, 0.5),
        "present_over_50": sum(1 for v in present if v > 50),
        "missing_over_50": sum(1 for v in missing if v > 50),
        "acquisitions_with_share": len(share),
    }


def analyze_tile(tile: str, objects: list[dict], es: dict[str, list[dict]], months, end: str):
    scenes, unparsed = aqr.group_scenes(objects)
    observed = set(aqr.OBSERVED_LAYERS)
    layer_sets = Counter(" ".join(sorted(s["layers"])) for s in scenes.values())
    incomplete = sorted(p for p, s in scenes.items() if not observed <= set(s["layers"]))
    by_key: dict[str, list[dict]] = defaultdict(list)
    for scene in scenes.values():
        by_key[aqr.acquisition_key(scene["platform"], scene["sensing"])].append(scene)
    aqr_months = aqr.keys_by_month_of([(s["platform"], s["sensing"]) for s in scenes.values()])

    items = {c: [gs.normalize_es(f) for f in es.get(c, [])] for c in ES_COLLECTIONS}
    es_months: dict[str, dict[str, set[str]]] = {}
    for collection, rows in items.items():
        grouped: dict[str, set[str]] = defaultdict(set)
        for item in rows:
            if item["tile"] == tile and item["datetime"]:
                grouped[item["datetime"][:7]].add(gs.sensing_key(item))
        es_months[collection] = grouped
    any_months = {
        m: set().union(*(es_months[c].get(m, set()) for c in ES_COLLECTIONS)) for m in months
    }

    def yearly(fn) -> dict[str, int]:
        out: Counter = Counter()
        for month in months:
            out[month[:4]] += fn(month)
        return dict(sorted(out.items()))

    missing_vs_l1c = yearly(lambda m: len(es_months[L1C].get(m, set()) - aqr_months.get(m, set())))
    missing_vs_any = yearly(lambda m: len(any_months[m] - aqr_months.get(m, set())))
    not_on_es = yearly(lambda m: len(aqr_months.get(m, set()) - any_months[m]))

    end_day = date.fromisoformat(end)
    recent_from = (end_day - timedelta(days=RECENT_DAYS)).isoformat()
    hours_by_year: dict[str, list[float]] = defaultdict(list)
    recent_hours: list[float] = []
    published_months: Counter = Counter()
    for scene in scenes.values():
        published = aqr.published_at(scene)
        if not published:
            continue
        hours = aqr.hours_between(scene["sensing_time"], published)
        hours_by_year[scene["sensing_time"][:4]].append(hours)
        published_months[published[:7]] += 1
        if scene["sensing_time"][:10] >= recent_from:
            recent_hours.append(hours)

    joins = [aqr.join_scene(s, items, JOIN_ORDER) for s in scenes.values()]
    join_by_year: dict[str, Counter] = defaultdict(Counter)
    join_by_baseline: dict[str, Counter] = defaultdict(Counter)
    for scene, joined in zip(scenes.values(), joins, strict=True):
        status = joined["status"]
        collection = joined["joined"]["collection"] if joined["joined"] else "none"
        join_by_year[scene["sensing_time"][:4]][f"{status} {collection}"] += 1
        join_by_baseline[scene["baseline"]][f"{status} {collection}"] += 1

    l1c_names = {i["product_uri"].removesuffix(".SAFE") for i in items[L1C] if i["product_uri"]}
    l1c_status: dict[str, Counter] = defaultdict(Counter)
    for scene in scenes.values():
        name = scene["product"].replace("_MSIAQR_", "_MSIL1C_")
        if name in l1c_names:
            status = "same_product"
        else:
            hit = aqr.join_scene(scene, items, [L1C])
            status = "same_pass_other_product" if hit["matches"][L1C] else "no_pass"
        l1c_status[scene["sensing_time"][:4]][status] += 1

    sensing = sorted(s["sensing_time"] for s in scenes.values())
    duplicate_kinds = Counter(
        "same_sensing" if len({s["sensing"] for s in v}) == 1 else "different_sensing"
        for v in by_key.values()
        if len(v) > 1
    )
    return {
        "tile": tile,
        "objects": len(objects),
        "unparsed_keys": unparsed[:20],
        "unparsed_count": len(unparsed),
        "scenes": len(scenes),
        "first_sensing": sensing[0] if sensing else None,
        "last_sensing": sensing[-1] if sensing else None,
        "layer_sets": dict(layer_sets),
        "scenes_without_observed_layers": incomplete[:20],
        "scenes_without_observed_layers_count": len(incomplete),
        "acquisitions": len(by_key),
        "duplicate_acquisitions": sum(1 for v in by_key.values() if len(v) > 1),
        "duplicate_kinds": dict(sorted(duplicate_kinds.items())),
        "duplicate_baseline_sets": aqr.counter_dict(
            "+".join(sorted(s["baseline"] for s in v)) for v in by_key.values() if len(v) > 1
        ),
        "baselines_by_year": {
            year: aqr.counter_dict(
                s["baseline"] for s in scenes.values() if s["sensing"][:4] == year
            )
            for year in sorted({s["sensing"][:4] for s in scenes.values()})
        },
        "platforms": aqr.counter_dict(s["platform"] for s in scenes.values()),
        "monthly": {
            "aqr": aqr.monthly_acquisitions(aqr_months, months),
            L1C: aqr.monthly_acquisitions(es_months[L1C], months),
            C1: aqr.monthly_acquisitions(es_months[C1], months),
            OLDER: aqr.monthly_acquisitions(es_months[OLDER], months),
            "earth_search_any": [len(any_months[m]) for m in months],
            "aqr_in_earth_search": [len(aqr_months.get(m, set()) & any_months[m]) for m in months],
        },
        "es_items": {c: len(items[c]) for c in ES_COLLECTIONS},
        "es_items_without_product_uri": {
            c: sum(1 for i in items[c] if not i["product_uri"]) for c in ES_COLLECTIONS
        },
        "missing_vs_l1c_by_year": missing_vs_l1c,
        "missing_vs_earth_search_by_year": missing_vs_any,
        "aqr_not_on_earth_search_by_year": not_on_es,
        "latency_by_sensing_year": {y: latency_stats(h) for y, h in sorted(hours_by_year.items())},
        "latency_recent": latency_stats(recent_hours) | {"sensed_from": recent_from},
        "published_by_month": dict(sorted(published_months.items())),
        "join_by_year": {y: dict(sorted(c.items())) for y, c in sorted(join_by_year.items())},
        "join_by_baseline": {
            b: dict(sorted(c.items())) for b, c in sorted(join_by_baseline.items())
        },
        "join_unmatched": sorted(j["product"] for j in joins if j["status"] == "none")[:30],
        "l1c_by_year": {y: dict(sorted(c.items())) for y, c in sorted(l1c_status.items())},
        "cloud_cover": cloud_comparison(items[L1C], tile, set(by_key)),
        "nodata_share": nodata_comparison(items[C1] + items[OLDER], tile, set(by_key)),
        "_latency_hours": recent_hours,
    }


def pooled(records: list[dict], months: list[str], hours: list[float]) -> dict:
    def total(key):
        return sum(r[key] for r in records)

    def merge(key) -> dict:
        out: dict = defaultdict(Counter)
        for r in records:
            for outer, inner in r[key].items():
                if isinstance(inner, dict):
                    out[outer].update(inner)
                else:
                    out[outer][""] += inner
        return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}

    def merge_flat(key) -> dict:
        out: Counter = Counter()
        for r in records:
            out.update(r[key])
        return dict(sorted(out.items()))

    coverage = []
    for i, month in enumerate(months):
        coverage.append(
            {
                "month": month,
                "reference": sum(r["monthly"]["earth_search_any"][i] for r in records),
                "aqr": sum(r["monthly"]["aqr_in_earth_search"][i] for r in records),
                "aqr_total": sum(r["monthly"]["aqr"][i] for r in records),
                "l1c": sum(r["monthly"][L1C][i] for r in records),
                "collection1": sum(r["monthly"][C1][i] for r in records),
            }
        )
    join_totals: Counter = Counter()
    for r in records:
        for counts in r["join_by_year"].values():
            join_totals.update(counts)
    cloud_bins = {"present": Counter(), "missing": Counter()}
    for r in records:
        for side in cloud_bins:
            cloud_bins[side].update(r["cloud_cover"]["bins"][side])
    present_max = [r["cloud_cover"]["present_max"] for r in records]
    missing_min = [r["cloud_cover"]["missing_min"] for r in records]
    l1c_totals: Counter = Counter()
    for r in records:
        for counts in r["l1c_by_year"].values():
            l1c_totals.update(counts)
    return {
        "tiles": len(records),
        "tiles_with_scenes": sum(1 for r in records if r["scenes"]),
        "objects": total("objects"),
        "scenes": total("scenes"),
        "acquisitions": total("acquisitions"),
        "duplicate_acquisitions": total("duplicate_acquisitions"),
        "duplicate_kinds": merge_flat("duplicate_kinds"),
        "scenes_without_observed_layers": total("scenes_without_observed_layers_count"),
        "unparsed_keys": total("unparsed_count"),
        "first_sensing": min(
            (r["first_sensing"] for r in records if r["first_sensing"]), default=None
        ),
        "last_sensing": max(
            (r["last_sensing"] for r in records if r["last_sensing"]), default=None
        ),
        "baselines_by_year": merge("baselines_by_year"),
        "missing_vs_l1c_by_year": merge_flat("missing_vs_l1c_by_year"),
        "missing_vs_earth_search_by_year": merge_flat("missing_vs_earth_search_by_year"),
        "aqr_not_on_earth_search_by_year": merge_flat("aqr_not_on_earth_search_by_year"),
        "earth_search_acquisitions_by_year": {
            year: sum(row["reference"] for row in coverage if row["month"][:4] == year)
            for year in sorted({row["month"][:4] for row in coverage})
        },
        "aqr_acquisitions_by_year": {
            year: sum(row["aqr_total"] for row in coverage if row["month"][:4] == year)
            for year in sorted({row["month"][:4] for row in coverage})
        },
        "join_totals": dict(sorted(join_totals.items())),
        "join_by_year": merge("join_by_year"),
        "join_by_baseline": merge("join_by_baseline"),
        "l1c_totals": dict(sorted(l1c_totals.items())),
        "l1c_by_year": merge("l1c_by_year"),
        "latency_recent": latency_stats(hours),
        "cloud_cover_bins": {side: dict(c) for side, c in cloud_bins.items()},
        "cloud_cover_present_max": max((v for v in present_max if v is not None), default=None),
        "cloud_cover_missing_min": min((v for v in missing_min if v is not None), default=None),
        "published_by_month": merge_flat("published_by_month"),
        "coverage_by_month": coverage,
    }


def analyze(raw_dir: Path, meta: dict) -> dict:
    months = gs.month_range(meta["start"], meta["end"])
    records = []
    hours: list[float] = []
    for tile in meta["inside"]:
        objects = json.loads((raw_dir / f"aqr-{tile}.json").read_text())
        es = {c: json.loads((raw_dir / f"es-{tile}-{c}.json").read_text()) for c in ES_COLLECTIONS}
        record = analyze_tile(tile, objects, es, months, meta["end"])
        hours.extend(record.pop("_latency_hours"))
        records.append(record)
    presence = {}
    for tile in meta["outside"]:
        objects = json.loads((raw_dir / f"presence-{tile}.json").read_text())
        scenes, _ = aqr.group_scenes(objects)
        presence[tile] = {
            "keys_first_page": len(objects),
            "scenes_first_page": len(scenes),
            "first_sensing": min((s["sensing_time"] for s in scenes.values()), default=None),
        }
    raw_files = {
        path.name: gs.sha256_file(path)
        for path in sorted(raw_dir.glob("*.json"))
        if path.name != "meta.json"
    }
    return {
        "months": months,
        "tiles": records,
        "presence": presence,
        "raw_files": raw_files,
        "summary": pooled(records, months, hours),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=datetime.now(UTC).date().isoformat())
    parser.add_argument("--tiles", nargs="*", help="Lower-48 tiles to survey instead of all")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks/results/aqr-coverage.json"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the plan, contact nothing")
    parser.add_argument("--from-raw", type=Path, help="rebuild the result from saved listings")
    args = parser.parse_args(argv)

    if args.from_raw:
        raw_dir = args.from_raw.resolve()
        meta = json.loads((raw_dir / "meta.json").read_text())
    else:
        inside, outside = survey_tiles(json.loads(GAP_SURVEY.read_text()))
        if args.tiles:
            inside, outside = [t for t in inside if t in args.tiles], []
        for line in plan(inside, outside, args.start, args.end):
            print(line)
        if args.dry_run:
            return 0
        measured_at = harness.utc_now()
        raw_dir = ROOT / "data" / "aqr-coverage" / measured_at.replace(":", "")
        raw_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "measured_at": measured_at,
            "start": args.start,
            "end": args.end,
            "inside": inside,
            "outside": outside,
            "code_version": harness.code_version(),
        }
        meta["request_log"] = collect(args, inside, outside, raw_dir)
        (raw_dir / "meta.json").write_text(json.dumps(meta))

    analysis = analyze(raw_dir, meta)
    logs = meta["request_log"]
    result = {
        "schema_version": 1,
        "measured_at": meta["measured_at"],
        "code_version": meta["code_version"],
        "analysis_code_version": harness.code_version(),
        "script": "benchmarks/aqr_coverage.py",
        "probe": "T2 and T3, docs/reviews/2026-10-13-acolite-first-replan.md",
        "window": {"start": meta["start"], "end": meta["end"]},
        "tiles_source": "benchmarks/results/gap-survey.json",
        "tiles_inside": meta["inside"],
        "tiles_outside": meta["outside"],
        "endpoints": {
            "bucket": aqr.BUCKET,
            "region": aqr.REGION,
            "credentials": "none, unsigned requests",
            "payer": "Bucket owner. Every request was unsigned, so no requester was charged.",
            "earth_search": gs.ES_ROOT,
            "earth_search_payer": "provider. Public API, no credentials",
        },
        "requests": {
            "s3_list": len(logs["s3"]),
            "s3_bytes_received": sum(e["bytes"] for e in logs["s3"]),
            "earth_search": len(logs["earth_search"]),
            "earth_search_bytes_received": sum(e["bytes"] for e in logs["earth_search"]),
            "object_bodies_read": 0,
            "pixels_read": 0,
        },
        "definitions": {
            "acquisition": "A distinct sensing date and platform letter on one tile, as in the "
            "gap survey. An aquatic reflectance acquisition takes both from the object name.",
            "earth_search_any": "Acquisitions in any of the three Earth Search collections.",
            "latency": "Hours from the sensing start in the object name to the earliest "
            "last-modified time of the scene's objects. It describes the bucket copy.",
            "join": "Tile, platform, and sensing start from the product names. Exact when the "
            "processing baseline also agrees. Collection 1 first, then the older collection.",
            "cloud_cover": "Earth Search Level-1C eo:cloud_cover per acquisition, the lowest "
            "of its items, split by whether the acquisition has a product scene.",
            "l1c": "same_product: Earth Search's Level-1C collection lists the Level-1C product "
            "named in the aquatic reflectance object name. same_pass_other_product: it lists the "
            "pass with another baseline or generation time. no_pass: neither.",
        },
        **analysis,
        "raw_dir": str(raw_dir.relative_to(ROOT)),
        "request_log": logs,
        "limitations": [
            "Listings and catalog metadata only. No object body and no pixel was read, so "
            "listed scenes are not shown to open or to hold valid water pixels.",
            "Earth Search is the reference. Its own completeness against ESA is measured "
            "separately in the gap survey, and only from 2021.",
            "Acquisition keys pair date and platform. Two passes of one unit on one tile and "
            "date would collapse into one key.",
            "Object last-modified times describe when the bucket copy was written. They can "
            "postdate processing, and a rewritten object resets its time.",
            f"Recent latency covers scenes sensed in the last {RECENT_DAYS} days of the window. "
            "Scenes not yet published are absent, so the statistic is biased low.",
            "Tiles outside the lower 48 get one listing page each. A presence count, not a survey.",
            "Counts describe the bucket and the catalog at measured_at.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=1) + "\n")
    s = analysis["summary"]
    print(
        f"wrote {args.output}: {s['scenes']} scenes on {s['tiles_with_scenes']} tiles, "
        f"join {s['join_totals']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
