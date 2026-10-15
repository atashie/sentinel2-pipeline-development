"""Offline audit of probe T6's saved source reads. No provider access or benchmark execution."""

import argparse
import collections
import hashlib
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "benchmarks/results/aqr-workloads.json"
HEADERS = ROOT / "benchmarks/results/aqr-headers.json"
REFERENCE = ROOT / "docs/cost-analysis/cohort-blocks.json"
OUTPUT = ROOT / "docs/cost-analysis/aqr-cohort-blocks.json"
SIZES = {"int16": 2, "int32": 4}
RECIPES = ("B-raster", "B-lazy")
COUNTS = (
    "logical_blocks",
    "unique_blocks",
    "full_blocks",
    "logical_decoded_bytes",
    "unique_decoded_bytes",
    "full_decoded_bytes",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def whole_file_compression(measured):
    """Object size over native bytes per T1 scene, for the measured layers and for all layers."""
    headers = json.loads(HEADERS.read_text())
    rows = []
    for scene in headers["scenes"]:
        layers = {name: layer for name, layer in scene["layers"].items() if layer.get("header")}
        native = {
            name: layer["header"]["width"]
            * layer["header"]["height"]
            * SIZES[layer["header"]["dtypes"][0]]
            for name, layer in layers.items()
        }
        size = {name: layer["size"] for name, layer in layers.items()}
        five = sum(size[n] for n in measured) / sum(native[n] for n in measured)
        every = sum(size.values()) / sum(native.values())
        rows.append(
            {
                "product": scene["product"],
                "object_bytes_all_layers": sum(size.values()),
                "measured_layers": five,
                "delivered_layers": every,
                "delivered_over_measured": every / five,
                "flags_layer": size["l2_flags"] / native["l2_flags"],
            }
        )
    return {
        "scenes": rows,
        "delivered_over_measured_mean": sum(r["delivered_over_measured"] for r in rows) / len(rows),
        "definition": (
            "Whole-object bytes over native bytes, from T1's listed object sizes. The ratio "
            "of all delivered layers to the five measured layers scales T6's windowed "
            "requested-to-decoded ratio to the full payload."
        ),
    }


def delivered_payload():
    """Native bytes per square kilometer of every GeoTIFF layer T1 found in one scene."""
    headers = json.loads(HEADERS.read_text())
    payloads = set()
    for scene in headers["scenes"]:
        layers = {
            name: layer["header"]["dtypes"][0]
            for name, layer in scene["layers"].items()
            if layer.get("header")
        }
        resolutions = {
            tuple(layer["header"]["resolution"])
            for layer in scene["layers"].values()
            if layer.get("header")
        }
        assert resolutions == {(20.0, 20.0)}
        payloads.add(tuple(sorted(layers.items())))
    assert len(payloads) == 1, "T1 scenes disagree on their layers"
    layers = dict(next(iter(payloads)))
    return {
        "layers": layers,
        "bytes_per_20m_pixel": sum(SIZES[dtype] for dtype in layers.values()),
        "bytes_per_km2": 1e6 / 400 * sum(SIZES[dtype] for dtype in layers.values()),
    }


def cohort_blocks(plan, database):
    """Sum native block bytes per layer from a frozen plan and its expected blocks."""
    by_band = collections.defaultdict(lambda: dict.fromkeys(COUNTS, 0))
    conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        for scene in plan["scenes"]:
            for asset in scene["assets"]:
                band = asset["key"]
                row = by_band[band]
                size = SIZES[asset["dtype"]]
                (height, width) = asset["shape"]
                (bh, bw) = asset["block_shape"]
                row["full_decoded_bytes"] += height * width * size
                row["full_blocks"] += math.ceil(height / bh) * math.ceil(width / bw)
                blocks = conn.execute(
                    "SELECT br,bc,COUNT(*) FROM expected WHERE item=? AND band=? GROUP BY br,bc",
                    (scene["item"]["id"], band),
                ).fetchall()
                for br, bc, count in blocks:
                    decoded = min(bh, height - br * bh) * min(bw, width - bc * bw) * size
                    row["logical_blocks"] += count
                    row["unique_blocks"] += 1
                    row["logical_decoded_bytes"] += count * decoded
                    row["unique_decoded_bytes"] += decoded
    finally:
        conn.close()
    return dict(by_band)


def build():
    """Derive block counts, byte ratios, and holdouts from T6's frozen local inputs."""
    evidence = json.loads(EVIDENCE.read_text())
    reference = json.loads(REFERENCE.read_text())
    run = ROOT / evidence["run_directory"]
    cohorts = {}
    for name in ("florida", "dispersed"):
        recorded = evidence["workloads"][name]
        folder = run / "workloads" / name
        plan_path = folder / "frozen-plan.json"
        plan = json.loads(plan_path.read_text())
        assert plan["sha256"] == recorded["plan_sha256"], f"{name} plan differs from T6"
        database = folder / "expected.sqlite"
        by_band = cohort_blocks(plan, database)
        total = {key: sum(row[key] for row in by_band.values()) for key in COUNTS}
        observations = {
            row["configuration"]: {
                "requested_bytes": row["io"]["bytes_requested"],
                "http_requests": row["io"]["requests"],
                "read_units": row["read_units"],
            }
            for row in recorded["comparisons"]
            if row["configuration"] in RECIPES
        }
        assert set(observations) == set(RECIPES)
        cohorts[name] = {
            "plan_path": str(plan_path.relative_to(ROOT)),
            "plan_sha256": digest(plan_path),
            "plan_internal_sha256": plan["sha256"],
            "expected_database_path": str(database.relative_to(ROOT)),
            "expected_database_sha256": digest(database),
            "lake_count": recorded["lakes"],
            "products": len(plan["scenes"]),
            "lake_product_memberships": sum(len(scene["members"]) for scene in plan["scenes"]),
            "by_band": by_band,
            "total": total,
            "unique_decoded_fraction_of_full": total["unique_decoded_bytes"]
            / total["full_decoded_bytes"],
            "observations": observations,
            "requested_to_decoded_ratios": {
                recipe: observations[recipe]["requested_bytes"] / total["unique_decoded_bytes"]
                for recipe in RECIPES
            },
            "reference_unique_red_blocks": reference["cohorts"][name]["by_band"]["red"][
                "unique_blocks"
            ],
            "reference_products": reference["cohorts"][name]["products"],
        }
    holdouts = []
    for training, target in (("florida", "dispersed"), ("dispersed", "florida")):
        for recipe in RECIPES:
            prediction = (
                cohorts[training]["requested_to_decoded_ratios"][recipe]
                * cohorts[target]["total"]["unique_decoded_bytes"]
            )
            observed = cohorts[target]["observations"][recipe]["requested_bytes"]
            holdouts.append(
                {
                    "training": training,
                    "held_out": target,
                    "recipe": recipe,
                    "predicted_requested_bytes": prediction,
                    "observed_requested_bytes": observed,
                    "predicted_over_observed": prediction / observed,
                }
            )
    measured = {"red": "B04", "nir": "B08", "swir16": "B11", "coastal": "B01", "scl": "l2_flags"}
    assert evidence["layers"] == measured
    delivered = delivered_payload()
    five = 1e6 / 400 * sum(SIZES[delivered["layers"][layer]] for layer in measured.values())
    return {
        "status": "offline derived check, not a new measurement",
        "generated_on": "2026-10-14",
        "evidence_path": str(EVIDENCE.relative_to(ROOT)),
        "evidence_sha256": digest(EVIDENCE),
        "headers_path": str(HEADERS.relative_to(ROOT)),
        "headers_sha256": digest(HEADERS),
        "reference_path": str(REFERENCE.relative_to(ROOT)),
        "reference_sha256": digest(REFERENCE),
        "decoded_bytes_definition": (
            "Native dtype bytes for each actual source block window, clipped at image "
            "edges. Logical sums repeat each lake-layer-block contribution. Unique sums "
            "deduplicate item, layer, block row, block column. Full bytes sum native "
            "layer shapes. The method matches tools/backtest_source_bytes.py."
        ),
        "measured_layers": measured,
        "cohorts": cohorts,
        "native_payload_bytes_per_km2": {
            "five_measured_layers": five,
            "delivered_layers": delivered["bytes_per_km2"],
            "delivered_to_five_ratio": delivered["bytes_per_km2"] / five,
            "delivered_layer_dtypes": delivered["layers"],
            "delivered_bytes_per_20m_pixel": delivered["bytes_per_20m_pixel"],
            "reference_seventeen_modeled_assets": reference["native_payload_bytes_per_km2"][
                "seventeen_modeled_assets"
            ],
        },
        "whole_file_compression": whole_file_compression(list(measured.values())),
        "cross_cohort_holdouts": holdouts,
        "limitations": [
            (
                "T6 replayed readers B1 and B3 only. Reader A1 has no measurement on the "
                "product, so no A1 ratio exists."
            ),
            (
                "Two cohorts give directional checks from two observations, not a broad "
                "statistical validation."
            ),
            (
                "The dispersed cohort kept 93 of 100 lakes and 112 products. 98 of the "
                "112 are the reference's acquisitions."
            ),
            (
                "Requested bytes include range overhead and cache behavior. "
                "Requested-to-decoded ratios are not pure file compression ratios."
            ),
            (
                "T6 read five of the thirteen delivered GeoTIFF layers. The int32 flags "
                "layer holds a third of their native bytes and compresses to about 3 "
                "percent. T1's whole-object sizes scale the ratio to all thirteen layers, "
                "on three scenes."
            ),
            (
                "Frozen plans and SQLite inputs remain local under data. Aggregate counts "
                "and hashes make the derivation reviewable without distributing polygons."
            ),
        ],
        "generator_path": str(Path(__file__).relative_to(ROOT)),
        "generator_sha256": digest(Path(__file__)),
        "reproduction_command": "uv run python tools/backtest_aqr_source_bytes.py",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        data = build()
    except FileNotFoundError as error:
        raise SystemExit(
            "Saved local frozen inputs are required. No data will be fetched."
        ) from error
    rendered = json.dumps(data, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit("Product byte checks differ. Run tools/backtest_aqr_source_bytes.py.")
        print("Product byte checks match saved local evidence and generator.")
    else:
        OUTPUT.write_text(rendered)
        print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
