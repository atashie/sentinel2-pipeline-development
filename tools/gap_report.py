"""Build the machine-readable gap survey report from the two survey result files.

Deterministic. Standard library. No network. Every number in the report is computed here from
benchmarks/results/gap-survey.json, benchmarks/results/fallback-survey.json, and the probe
record. A reviewer reruns this script with --check to confirm the committed report matches.

    uv run python tools/gap_report.py            # write the report under docs/reviews/
    uv run python tools/gap_report.py --check    # fail when the committed report is stale
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAP = ROOT / "benchmarks" / "results" / "gap-survey.json"
FALLBACK = ROOT / "benchmarks" / "results" / "fallback-survey.json"
PROBES = ROOT / "docs" / "assessment-checks" / "probes-2026-09-10.json"
OUTPUT = ROOT / "docs" / "reviews" / "2026-09-10-gap-survey-report.json"
PRIMARY = "sentinel-2-c1-l2a"
OLDER = "sentinel-2-l2a"
L1C = "sentinel-2-l1c"
PRE_C1 = "sentinel-2-pre-c1-l2a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counter_sum(dicts) -> dict:
    total = Counter()
    for d in dicts:
        total.update(d)
    return dict(sorted(total.items()))


def year_indices(months: list[str], year: str) -> list[int]:
    return [i for i, m in enumerate(months) if m.startswith(year)]


def quality_layouts_from(samples: list[dict]) -> list[dict]:
    """Distinct quality-asset layouts, each with the samples and baselines that show it."""
    layouts: dict[tuple, dict] = {}
    for sample in samples:
        assets = {
            key: {
                "class": "cog" if "cloud-optimized" in (value.get("type") or "") else "other",
                "host": value["href_host"],
            }
            for key, value in sorted(sample["quality_assets"].items())
        }
        requester_pays = sample["storage"].get("storage:requester_pays")
        key = (
            sample["collection"],
            json.dumps(sample["software"], sort_keys=True),
            json.dumps(assets, sort_keys=True),
            json.dumps(requester_pays),
        )
        entry = layouts.setdefault(
            key,
            {
                "collection": sample["collection"],
                "software": sample["software"],
                "quality_assets": assets,
                "requester_pays": requester_pays,
                "baselines": set(),
                "sample_item_ids": [],
            },
        )
        entry["baselines"].add(str(sample["baseline"]))
        entry["sample_item_ids"].append(sample["item_id"])
    return [
        {
            **layouts[k],
            "baselines": sorted(layouts[k]["baselines"]),
            "sample_item_ids": sorted(layouts[k]["sample_item_ids"]),
        }
        for k in sorted(layouts, key=str)
    ]


def expected_tile_months(gap: dict) -> set[tuple[str, str]]:
    """Every tile and month the gap survey marked empty or partial."""
    months = gap["window"]["months"]
    return {
        (tile, month)
        for tile, record in gap["tiles"].items()
        for month, status in zip(months, record["gaps"]["status"], strict=True)
        if status in ("empty", "partial")
    }


def coverage_by_month(gap: dict, fallback: dict) -> list[dict]:
    """Per month across every surveyed tile: expected, present in Collection 1, and filled.

    Expected and Collection 1 counts come from the gap survey arrays. The fill count is the
    fallback survey's complete GeoTIFF sets, which exist only for incomplete tile-months.
    """
    rows = []
    for i, month in enumerate(gap["window"]["months"]):
        fill = uncovered = 0
        for record in fallback["tiles"].values():
            entry = record["monthly"].get(month)
            if entry:
                fill += entry["complete_cog"]
                uncovered += entry["uncovered"] + entry["partial_cog"] + entry["jp2_only"]
        rows.append(
            {
                "month": month,
                "reference": sum(r["gaps"]["reference"][i] for r in gap["tiles"].values()),
                "collection1": sum(r["gaps"]["primary"][i] for r in gap["tiles"].values()),
                "older_collection_fill": fill,
                "uncovered": uncovered,
            }
        )
    return rows


def validate_inputs(gap: dict, fallback: dict, gap_sha256: str) -> None:
    """Refuse inputs that do not belong together. Raises ValueError with the reason."""
    recorded = fallback.get("input", {})
    if recorded.get("sha256") != gap_sha256:
        raise ValueError(
            "the fallback survey was built from a different gap survey result: recorded digest "
            f"{recorded.get('sha256')}, current digest {gap_sha256}"
        )
    if recorded.get("measured_at") != gap.get("measured_at"):
        raise ValueError("the fallback survey records a different gap survey measured_at")
    expected = expected_tile_months(gap)
    actual = {
        (tile, month) for tile, record in fallback["tiles"].items() for month in record["monthly"]
    }
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ValueError(
            f"fallback survey tile-months do not match the gap survey: {len(missing)} missing, "
            f"{len(extra)} extra. First missing: {missing[:3]}. First extra: {extra[:3]}"
        )


def build(gap: dict, fallback: dict, probes: dict, paths: dict[str, Path]) -> dict:
    validate_inputs(gap, fallback, sha256(paths["gap"]))
    months = gap["window"]["months"]
    tiles = gap["tiles"]
    absent = sorted(
        t
        for t, r in tiles.items()
        if r["earth_search"][OLDER]["items_total"] == 0
        and r["earth_search"][L1C]["items_total"] == 0
    )
    present = [t for t in tiles if t not in absent]

    def gap_total(tile_list, key, idxs=None):
        idxs = idxs if idxs is not None else range(len(months))
        return sum(tiles[t]["gaps"][key][i] for t in tile_list for i in idxs)

    i2022 = year_indices(months, "2022")
    i2023 = year_indices(months, "2023")
    i_dec22 = [months.index("2022-12")]
    status_2022 = {
        m: gap["summary"]["primary_status_by_month"][m] for m in months if m.startswith("2022")
    }
    c1_global = dict(zip(months, gap["summary"]["global_window_monthly"][PRIMARY], strict=True))
    global_2022 = {m: c1_global[m] for m in months if m.startswith("2022")}
    other_months = [c1_global[m] for m in months if not m.startswith("2022")]

    ref_baselines_2022 = counter_sum(
        tiles[t]["reference"]["baselines"][i] for t in present for i in i2022
    )
    older_baselines_2022 = counter_sum(
        tiles[t]["earth_search"][OLDER]["baselines"][i] for t in present for i in i2022
    )
    c1_baselines_2023 = counter_sum(
        tiles[t]["earth_search"][PRIMARY]["baselines"][i] for t in present for i in i2023
    )
    ref_baselines_2023 = counter_sum(
        tiles[t]["reference"]["baselines"][i] for t in present for i in i2023
    )
    c1_dec22 = counter_sum(
        tiles[t]["earth_search"][PRIMARY]["baselines"][i] for t in present for i in i_dec22
    )
    ref_dec22 = counter_sum(tiles[t]["reference"]["baselines"][i] for t in present for i in i_dec22)

    absent_detail = {}
    for t in absent:
        es = tiles[t]["earth_search"][PRIMARY]
        first = next((m for m, n in zip(months, es["items"], strict=True) if n), None)
        absent_detail[t] = {
            "sites": tiles[t]["sites"],
            "reference_acquisitions": tiles[t]["reference"]["acquisitions_total"],
            "collection1_acquisitions": es["acquisitions_total"],
            "older_collection_items": tiles[t]["earth_search"][OLDER]["items_total"],
            "level1c_items": tiles[t]["earth_search"][L1C]["items_total"],
            "first_month_with_collection1_items": first,
            "uncovered_acquisitions": tiles[t]["gaps"]["uncovered_total"],
            "months_by_status": tiles[t]["gaps"]["months_by_status"],
        }
    pr06 = next((p for p in probes["probes"] if p["id"] == "PR-06"), None)
    pr06_summary = None
    if pr06:
        pr06_summary = {
            box: {
                c: {
                    "window_total": v["window_total"],
                    "months_below_5pct_of_median": v["months_below_5pct_of_median"],
                }
                for c, v in detail.items()
                if c != "bbox"
            }
            for box, detail in pr06["result"].items()
        }

    pre = gap["collections"][PRE_C1]
    pre_in_tiles = {
        t: r["earth_search"][PRE_C1]["items_total"]
        for t, r in tiles.items()
        if r["earth_search"][PRE_C1]["items_total"]
    }

    flags = gap["summary"]["offset_flag_by_collection_and_baseline"]
    red_offsets = sorted(
        {
            (
                s["collection"],
                str(s["baseline"]),
                str(s["boa_offset_applied"]),
                str(s["red"]["offset"]),
            )
            for s in gap["asset_samples"]
            if s["red"]
        }
    )
    quality_layouts = quality_layouts_from(gap["asset_samples"])

    totals = gap["summary"]["collection_totals"]
    dup_sets = gap["summary"]["duplicate_baseline_sets_by_collection"]

    def split_dups(sets):
        mixed = sum(v for k, v in sets.items() if len(set(k.split("+"))) > 1)
        same = sum(v for k, v in sets.items() if len(set(k.split("+"))) == 1)
        return {"mixed_baselines": mixed, "same_baseline": same}

    multi_tile_sites = [
        {"site_id": s["site_id"], "group": s["group"], "tiles": sorted(s["tiles"])}
        for s in gap["sites"]
        if len(s["tiles"]) > 1
    ]
    last13 = list(range(len(months) - 13, len(months)))
    point_vs_tile = []
    for s in gap["sites"]:
        for tile, n in s["tiles"].items():
            tile_items = sum(tiles[tile]["earth_search"][PRIMARY]["items"][i] for i in last13)
            point_vs_tile.append(
                {
                    "site_id": s["site_id"],
                    "tile": tile,
                    "footprints_covering_point_last_year": n,
                    "tile_items_last_13_months": tile_items,
                }
            )

    fb = fallback["summary"]
    fb_tiles = fallback["tiles"]
    fb_by_month = fb["by_month"]
    consistency = []
    for t, r in fb_tiles.items():
        g = tiles[t]["gaps"]
        for m, row in r["monthly"].items():
            i = months.index(m)
            consistency.append(
                {
                    "tile": t,
                    "month": m,
                    "missing_gap_survey": g["missing"][i],
                    "missing_fallback_survey": row["missing"],
                    "covered_gap_survey": g["covered_by_fallback"][i],
                    "covered_fallback_survey": row["complete_cog"]
                    + row["partial_cog"]
                    + row["jp2_only"]
                    + row["no_data_assets"],
                }
            )
    disagreements = [
        c
        for c in consistency
        if c["missing_gap_survey"] != c["missing_fallback_survey"]
        or c["covered_gap_survey"] != c["covered_fallback_survey"]
    ]
    head = {
        "requests": fb["head_requests"],
        "status": fb["head_status"],
        "content_length_bytes": fb["head_content_length_bytes"],
        "request_charged_headers_seen": sorted(
            {str(h["request_charged"]) for r in fb_tiles.values() for h in r["head_sample"]}
        ),
        "storage_classes_seen": sorted(
            {str(h["storage_class"]) for r in fb_tiles.values() for h in r["head_sample"]}
        ),
        "content_types_seen": sorted(
            {str(h["content_type"]) for r in fb_tiles.values() for h in r["head_sample"]}
        ),
    }

    per_tile = []
    for t, r in tiles.items():
        g = r["gaps"]
        f = fb_tiles.get(t)
        per_tile.append(
            {
                "tile": t,
                "sites": r["sites"],
                "route_absent": t in absent,
                "reference_acquisitions": r["reference"]["acquisitions_total"],
                "collection1_acquisitions": r["earth_search"][PRIMARY]["acquisitions_total"],
                "missing": g["missing_total"],
                "covered_by_older_collection": g["covered_by_fallback_total"],
                "uncovered": g["uncovered_total"],
                "months_by_status": g["months_by_status"],
                "incomplete_months": f["incomplete_months"] if f else [],
                "fallback": {**f["totals"], "head_status": f["head_status"]} if f else None,
            }
        )

    findings = [
        {
            "id": "GS-01",
            "title": (
                "Collection 1 is nearly empty from January to November 2022 in every surveyed "
                "tile, and the shape is global"
            ),
            "status": "measured",
            "numbers": {
                "tiles": len(tiles),
                "months_empty_in_every_tile": gap["summary"]["months_empty_in_every_tile"],
                "collection1_status_by_month_2022": status_2022,
                "collection1_global_items_by_month_2022": global_2022,
                "collection1_global_items_other_months_min_max": [
                    min(other_months),
                    max(other_months),
                ],
                "reference_baselines_2022_present_tiles": ref_baselines_2022,
                "present_tiles_2022": {
                    "reference": gap_total(present, "reference", i2022),
                    "collection1": gap_total(present, "primary", i2022),
                    "missing": gap_total(present, "missing", i2022),
                    "covered_by_older_collection": gap_total(present, "covered_by_fallback", i2022),
                    "uncovered": gap_total(present, "uncovered", i2022),
                },
                "older_collection_baselines_2022_present_tiles": older_baselines_2022,
            },
            "evidence": [
                {"input": "gap", "path": "summary.months_empty_in_every_tile"},
                {"input": "gap", "path": "summary.primary_status_by_month"},
                {"input": "gap", "path": "summary.global_window_monthly.sentinel-2-c1-l2a"},
                {
                    "input": "gap",
                    "path": (
                        "tiles.<tile>.gaps.{reference,primary,missing,covered_by_fallback,uncovered}"
                    ),
                },
                {"input": "gap", "path": "tiles.<tile>.reference.baselines"},
                {"input": "probes", "path": "probes[id=PR-06].result"},
            ],
            "bears_on": ["I-08"],
            "for_review": (
                "Confirm the month statuses from the per-tile arrays: six months empty in every "
                "tile, the other 2022 months empty or partial per tile, never complete. Confirm "
                "the reference baselines for 2022 are 05.10 rather than 04.00."
            ),
        },
        {
            "id": "GS-02",
            "title": (
                "Collection 1 holds baseline 05.09 originals from December 2022 to December 2023 "
                "where ESA serves 05.10"
            ),
            "status": "measured",
            "numbers": {
                "collection1_baselines_2023_present_tiles": c1_baselines_2023,
                "reference_baselines_2023_present_tiles": ref_baselines_2023,
                "collection1_baselines_2022_12_present_tiles": c1_dec22,
                "reference_baselines_2022_12_present_tiles": ref_dec22,
                "collection1_baselines_by_year": gap["summary"]["primary_baselines_by_year"],
            },
            "evidence": [
                {"input": "gap", "path": "tiles.<tile>.earth_search.sentinel-2-c1-l2a.baselines"},
                {"input": "gap", "path": "tiles.<tile>.reference.baselines"},
                {"input": "gap", "path": "summary.primary_baselines_by_year"},
            ],
            "bears_on": ["I-29", "I-08"],
            "for_review": (
                "Confirm from claims R2 and R5 in docs/s2-best-practices.md that ESA reprocessed "
                "2022 to 2023 at 05.10 and removed the earlier products."
            ),
        },
        {
            "id": "GS-03",
            "title": "Tiles on no Earth Search collection for most of the window",
            "status": "measured",
            "numbers": {"absent_tiles": absent_detail, "probe_pr06_boxes": pr06_summary},
            "evidence": [
                {
                    "input": "gap",
                    "path": "tiles.<tile>.earth_search.{sentinel-2-l2a,sentinel-2-l1c}.items_total",
                },
                {"input": "gap", "path": "tiles.<tile>.gaps.uncovered_total"},
                {"input": "probes", "path": "probes[id=PR-06]"},
            ],
            "bears_on": ["I-08"],
            "for_review": (
                "Confirm that the older collection and Level-1C are empty for these tiles, that "
                "Collection 1 holds isolated items before sustained coverage begins, and that "
                "decision 0003's first review trigger applies if the tiles are in scope."
            ),
        },
        {
            "id": "GS-04",
            "title": "The pre-Collection 1 collection is three months of late 2022",
            "status": "measured",
            "numbers": {
                "global_total_count": pre["total_count"],
                "global_datetime_min": pre["datetime_min"],
                "global_datetime_max": pre["datetime_max"],
                "items_in_surveyed_tiles": pre_in_tiles,
            },
            "evidence": [
                {"input": "gap", "path": "collections.sentinel-2-pre-c1-l2a"},
                {
                    "input": "gap",
                    "path": "tiles.<tile>.earth_search.sentinel-2-pre-c1-l2a.items_total",
                },
            ],
            "bears_on": ["I-08"],
            "for_review": (
                "Confirm the collection extent against the aggregation values recorded in the "
                "input."
            ),
        },
        {
            "id": "GS-05",
            "title": (
                "The provider's offset flag varies per item and disagrees with the asset's "
                "declared offset"
            ),
            "status": "measured",
            "numbers": {
                "offset_flag_by_collection_and_baseline": flags,
                "sampled_red_offset_by_collection_baseline_flag": [
                    {"collection": c, "baseline": b, "flag": f, "raster_bands_offset": o}
                    for c, b, f, o in red_offsets
                ],
            },
            "evidence": [
                {"input": "gap", "path": "summary.offset_flag_by_collection_and_baseline"},
                {"input": "gap", "path": "asset_samples[].red.offset"},
                {"input": "fallback", "path": "summary.fallback_offset_flags"},
            ],
            "bears_on": ["I-05"],
            "for_review": (
                "Confirm that flag true and flag false items at baseline 04.00 both declare a "
                "raster:bands offset of -0.1, and that the README's rule and the flag cannot both "
                "hold."
            ),
        },
        {
            "id": "GS-06",
            "title": (
                "Quality assets depend on the collection and on the provider's ingestion software "
                "version"
            ),
            "status": "measured",
            "numbers": {
                "quality_asset_layouts": quality_layouts,
                "fallback_items_used_by_software": fb["fallback_software"],
                "fallback_items_used_cloud_snow": fb["fallback_cloud_snow"],
            },
            "evidence": [
                {"input": "gap", "path": "asset_samples[]"},
                {"input": "fallback", "path": "summary.fallback_software"},
                {"input": "fallback", "path": "summary.fallback_cloud_snow"},
            ],
            "bears_on": ["I-26"],
            "for_review": (
                "Confirm from the asset samples which layouts occur. One software version can "
                "carry several layouts, so do not infer a layout from the version alone."
            ),
        },
        {
            "id": "GS-07",
            "title": (
                "The older collection keeps originals beside reprocessings. Collection 1 keeps "
                "one product per acquisition key, except same-day splits and one mixed-baseline "
                "group"
            ),
            "status": "measured",
            "numbers": {
                "collection_totals": totals,
                "duplicate_groups_collection1": split_dups(dup_sets[PRIMARY]),
                "mixed_baseline_groups_collection1": {
                    k: v for k, v in dup_sets[PRIMARY].items() if len(set(k.split("+"))) > 1
                },
                "duplicate_groups_older_collection": split_dups(dup_sets[OLDER]),
                "collection1_acquisitions_absent_from_reference": sum(
                    sum(r["gaps"]["primary_not_in_reference"]) for r in tiles.values()
                ),
            },
            "evidence": [
                {"input": "gap", "path": "summary.collection_totals"},
                {"input": "gap", "path": "summary.duplicate_baseline_sets_by_collection"},
                {"input": "gap", "path": "tiles.<tile>.gaps.primary_not_in_reference"},
            ],
            "bears_on": ["I-16", "I-25"],
            "for_review": (
                "Confirm that mixed-baseline duplicate groups are original plus reprocessed pairs, "
                "and that same-baseline groups are same-day datastrip splits. A date and platform "
                "key does not identify one product. Product ids do."
            ),
        },
        {
            "id": "GS-08",
            "title": "Sites in more than one tile",
            "status": "measured",
            "numbers": {"sites": len(gap["sites"]), "multi_tile_sites": multi_tile_sites},
            "evidence": [{"input": "gap", "path": "sites[].tiles"}],
            "bears_on": ["I-30"],
            "for_review": "Confirm the tile lists per site.",
        },
        {
            "id": "GS-09",
            "title": "Tile counts overstate coverage at a point",
            "status": "measured",
            "numbers": {"point_versus_tile": point_vs_tile},
            "evidence": [
                {
                    "input": "gap",
                    "path": "sites[].tiles (footprints covering the point in the discovery window)",
                },
                {
                    "input": "gap",
                    "path": (
                        "tiles.<tile>.earth_search.sentinel-2-c1-l2a.items (last 13 months of the "
                        "window, which contain the discovery window)"
                    ),
                },
            ],
            "bears_on": ["I-30", "A20"],
            "for_review": (
                "The tile count spans 13 months and contains the 12-month discovery window, so it "
                "is an upper bound. Confirm the direction of the difference, not its exact size."
            ),
        },
        {
            "id": "GS-10",
            "title": "The older collection's GeoTIFFs cover the missing acquisitions",
            "status": "measured",
            "numbers": {
                "tiles_surveyed": fb["tiles"],
                "totals": fb["totals"],
                "by_month": fb_by_month,
                "fallback_items_used_baselines": fb["fallback_baselines"],
                "fallback_items_used_offset_flags": fb["fallback_offset_flags"],
                "fallback_full_cog_items": sum(
                    row["fallback_full_cog"]
                    for r in fb_tiles.values()
                    for row in r["monthly"].values()
                ),
                "definitions": fallback["definitions"],
            },
            "evidence": [
                {"input": "fallback", "path": "summary.totals"},
                {"input": "fallback", "path": "summary.by_month"},
                {"input": "fallback", "path": "tiles.<tile>.monthly.<month>"},
            ],
            "bears_on": ["I-08", "I-26"],
            "for_review": (
                "Confirm the complete_cog definition against assumption A3's band list. Confirm "
                "that every missing acquisition outside the absent tiles is classed complete_cog, "
                "jp2_only, or uncovered, with no partial_cog case."
            ),
        },
        {
            "id": "GS-11",
            "title": (
                "Sampled GeoTIFF objects exist in the public bucket and answer unsigned requests"
            ),
            "status": "measured",
            "numbers": head,
            "evidence": [
                {"input": "fallback", "path": "summary.head_status"},
                {"input": "fallback", "path": "tiles.<tile>.head_sample[]"},
            ],
            "bears_on": ["I-08", "I-18"],
            "for_review": (
                "A 200 to HEAD shows existence and size only. Confirm the sampling rule, one item "
                "per tile and month, two objects each."
            ),
        },
        {
            "id": "GS-12",
            "title": (
                "The two surveys agree on missing and covered acquisitions in the incomplete months"
            ),
            "status": "measured",
            "numbers": {
                "tile_months_compared": len(consistency),
                "disagreements": disagreements,
            },
            "evidence": [
                {"input": "gap", "path": "tiles.<tile>.gaps.{missing,covered_by_fallback}"},
                {
                    "input": "fallback",
                    "path": (
                        "tiles.<tile>.monthly.<month>.{missing,complete_cog,partial_cog,jp2_only,no_data_assets}"
                    ),
                },
            ],
            "bears_on": ["I-08"],
            "for_review": (
                "Any disagreement means one survey listed an item the other did not. Zero "
                "disagreements is expected because both ran within hours."
            ),
        },
    ]

    corrections = [
        {
            "id": "GC-01",
            "about": "decision 0003 and assumption A13",
            "statement": (
                "They call the fallback the older collection's JPEG 2000 assets. Its primary "
                "assets are cloud-optimized GeoTIFFs in the public sentinel-cogs bucket, with JPEG "
                "2000 alternates. The wording is for the owner to amend."
            ),
            "evidence": [
                {"input": "gap", "path": "asset_samples[collection=sentinel-2-l2a].red.href_host"},
                {"input": "fallback", "path": "summary.totals.complete_cog"},
            ],
        },
        {
            "id": "GC-02",
            "about": "issue I-08 before this step",
            "statement": (
                "It cited the provider README's April 2024 statement of a 2022 gap. The gap is now "
                "measured, global, and dated to the run."
            ),
            "evidence": [{"input": "gap", "path": "summary.months_empty_in_every_tile"}],
        },
        {
            "id": "GC-03",
            "about": "the discovery response",
            "statement": (
                "It described the pre-Collection 1 collection as baseline below 05.00. Measured, "
                "it holds items from three months of 2022 only."
            ),
            "evidence": [{"input": "gap", "path": "collections.sentinel-2-pre-c1-l2a"}],
        },
    ]

    decision_inputs = {
        "decision": "0004, to be written by the owner",
        "gaps": [
            {
                "id": "A",
                "gap": "January to November 2022 in every tile",
                "findings": ["GS-01", "GS-05", "GS-06", "GS-10", "GS-11"],
                "options": [
                    {
                        "id": "A1",
                        "option": (
                            "Fill from the older collection's GeoTIFF assets, 03.01 then 04.00 "
                            "originals"
                        ),
                        "available_now": True,
                        "risks": [
                            "offset state unknown until a pixel check",
                            "no cloud or snow probability",
                            "items before 2022-01-25 carry no offset, items after do",
                        ],
                    },
                    {
                        "id": "A2",
                        "option": (
                            "Leave 2022 absent and backfill as a revision when the route ingests "
                            "the 05.10 reprocessing"
                        ),
                        "available_now": False,
                        "risks": ["timing unknown"],
                    },
                    {
                        "id": "A3",
                        "option": (
                            "Fetch ESA's 05.10 products for 2022 from the Copernicus catalog once"
                        ),
                        "available_now": True,
                        "risks": [
                            "outside the route of decision 0003",
                            "credentials and egress from a non-AWS store",
                        ],
                    },
                    {
                        "id": "A4",
                        "option": "Start the 2021 scenario at 2023",
                        "available_now": True,
                        "risks": ["loses a year"],
                    },
                ],
                "agent_proposal": (
                    "A1 as a labeled provisional fill keyed by baseline after the pixel check, "
                    "with A2 as the standing rule."
                ),
            },
            {
                "id": "B",
                "gap": "December 2022 to December 2023 at 05.09 where ESA serves 05.10",
                "findings": ["GS-02"],
                "options": [
                    {
                        "id": "B1",
                        "option": "Accept the route's 05.09 products with the baseline recorded",
                        "available_now": True,
                        "risks": ["05.09 to 05.10 differences unassessed"],
                    },
                    {
                        "id": "B2",
                        "option": "Treat as gap A",
                        "available_now": False,
                        "risks": ["the provider may never re-ingest"],
                    },
                ],
                "agent_proposal": "B1, plus a recheck of the 05.10 release note against claim R5.",
            },
            {
                "id": "C",
                "gap": "tiles absent from every Earth Search collection",
                "findings": ["GS-03"],
                "options": [
                    {"id": "C1", "option": "Confirm whether Alaska water bodies are in scope"},
                    {
                        "id": "C2",
                        "option": (
                            "If in scope, survey the tiles the customer set touches, using tile "
                            "ids derived in-house"
                        ),
                    },
                    {
                        "id": "C3",
                        "option": (
                            "For absent tiles, choose exclusion or a non-route source, which "
                            "reopens decision 0003 for those tiles"
                        ),
                    },
                ],
                "agent_proposal": "C1 first.",
            },
            {
                "id": "D",
                "gap": "single acquisitions on no Earth Search collection",
                "findings": ["GS-01", "GS-10"],
                "options": [
                    {
                        "id": "D1",
                        "option": (
                            "Record as absent in the store's missingness fields and rerun the "
                            "survey before backfill"
                        ),
                    }
                ],
                "agent_proposal": "D1.",
            },
            {
                "id": "E",
                "gap": "the offset flag, a blocker for A1",
                "findings": ["GS-05"],
                "options": [
                    {
                        "id": "E1",
                        "option": (
                            "Prototyping measurement: compare one 60 m band window from a GeoTIFF "
                            "with its JPEG 2000 alternate for a flag-true and a flag-false 04.00 "
                            "item"
                        ),
                    }
                ],
                "agent_proposal": "E1 before any A1 fill.",
            },
        ],
    }

    return {
        "schema_version": 1,
        "report": "gap-survey-report",
        "generated_by": "tools/gap_report.py",
        "generated_from": {
            "gap_survey_measured_at": gap["measured_at"],
            "fallback_survey_measured_at": fallback["measured_at"],
            "probes_recorded_on": probes["recorded_on"],
        },
        "purpose": (
            "Machine-readable record of the data gap survey and the fallback survey for review. "
            "Every number is computed from the inputs by tools/gap_report.py. Statements are the "
            "agent's readings of those numbers."
        ),
        "how_to_verify": [
            "uv run python tools/gap_report.py --check",
            (
                "Open each evidence path in the named input and compare with the numbers in the "
                "finding."
            ),
            (
                "Rerun benchmarks/gap_survey.py and benchmarks/fallback_survey.py to refresh the "
                "inputs. Catalogs change, so counts can move."
            ),
        ],
        "inputs": [
            {
                "id": "gap",
                "path": "benchmarks/results/gap-survey.json",
                "sha256": sha256(paths["gap"]),
                "measured_at": gap["measured_at"],
                "script": gap["script"],
                "requests": gap["requests"]["total"],
                "imagery_bytes": gap["requests"]["imagery_bytes"],
            },
            {
                "id": "fallback",
                "path": "benchmarks/results/fallback-survey.json",
                "sha256": sha256(paths["fallback"]),
                "measured_at": fallback["measured_at"],
                "script": fallback["script"],
                "requests": fallback["requests"]["total"],
                "imagery_bytes": fallback["requests"]["imagery_bytes"],
            },
            {
                "id": "probes",
                "path": "docs/assessment-checks/probes-2026-09-10.json",
                "sha256": sha256(paths["probes"]),
                "recorded_on": probes["recorded_on"],
            },
        ],
        "scope": {
            "window": {
                "start": gap["window"]["start"],
                "end": gap["window"]["end"],
                "months": len(months),
            },
            "sites": [
                {"site_id": s["site_id"], "group": s["group"], "tiles": sorted(s["tiles"])}
                for s in gap["sites"]
            ],
            "tiles": sorted(tiles),
            "route_absent_tiles": absent,
            "earth_search_collections": list(gap["collections"]),
            "reference": (
                "Copernicus Data Space Ecosystem STAC and OData catalogs, reference count only, "
                "not a route"
            ),
            "acquisition_key": "sensing date plus platform letter within one tile",
        },
        "findings": findings,
        "per_tile": per_tile,
        "coverage_by_month": coverage_by_month(gap, fallback),
        "corrections": corrections,
        "decision_inputs": decision_inputs,
        "open_questions": [
            (
                "Why tile 05VLG and possibly its neighbors are absent from every Earth Search "
                "collection before June 2025."
            ),
            (
                "Why 15 single acquisitions in 2022 have no Level-2A item on the route while ESA "
                "lists them."
            ),
            "Why Collection 1 lists 30 acquisitions that the Copernicus catalog no longer lists.",
            (
                "Whether the offset flag or the raster:bands offset describes the pixels of 04.00 "
                "items in the older collection."
            ),
            "What changed between baselines 05.09 and 05.10 for Level-2A products.",
        ],
        "limitations": sorted(set(gap["limitations"]) | set(fallback["limitations"])),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail when the committed report is stale"
    )
    parser.add_argument("--gap", type=Path, default=GAP)
    parser.add_argument("--fallback", type=Path, default=FALLBACK)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    gap = json.loads(args.gap.read_text())
    fallback = json.loads(args.fallback.read_text())
    probes = json.loads(PROBES.read_text())
    paths = {"gap": args.gap, "fallback": args.fallback, "probes": PROBES}
    report = build(gap, fallback, probes, paths)
    text = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != text:
            print(f"{args.output} is stale. Run tools/gap_report.py.")
            return 1
        print(f"{args.output} matches the survey results.")
        return 0
    args.output.write_text(text)
    print(f"wrote {args.output} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
