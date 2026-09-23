"""Offline audit of saved source reads. No provider access or benchmark execution."""

import argparse
import collections
import hashlib
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/cost-analysis/cohort-blocks.json"


def build():
    """Read frozen local inputs and derive geometry and held-out byte comparisons."""
    root = ROOT
    evidence_path = root / "benchmarks/results/lazy-reader-workloads.json"
    evidence = json.loads(evidence_path.read_text())
    run = root / "data/lazy-reader-workloads/2026-09-21-sleep-rerun"

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def occupancy(draws, cells):
        return sum(
            cells * f * -math.expm1(-draws * m / (cells * f))
            for (f, m) in ((0.25, 0.9), (0.75, 0.1))
        )

    cohorts = {}
    for name in ("florida", "dispersed"):
        folder = run / name
        plan_path = folder / "frozen-plan.json"
        plan = json.loads(plan_path.read_text())
        database = folder / "expected.sqlite"
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        by_band = collections.defaultdict(
            lambda: dict(
                logical_blocks=0,
                unique_blocks=0,
                full_blocks=0,
                logical_decoded_bytes=0,
                unique_decoded_bytes=0,
                full_decoded_bytes=0,
            )
        )
        for scene in plan["scenes"]:
            for asset in scene["assets"]:
                band = asset["key"]
                row = by_band[band]
                size = {"uint8": 1, "uint16": 2}[asset["dtype"]]
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
        conn.close()
        total = {
            key: sum(row[key] for row in by_band.values()) for key in next(iter(by_band.values()))
        }
        observations = {
            row["configuration"]: {
                "requested_bytes": row["io"]["bytes_requested"],
                "http_requests": row["io"]["requests"],
                "read_units": row["read_units"],
            }
            for row in evidence["cohorts"][name]["comparisons"]
            if row["configuration"] in ("A-raster", "B-raster", "B-lazy", "C-raster", "C-lazy")
        }
        coefficients = {}
        for recipe in observations:
            denominator = (
                total["logical_decoded_bytes"]
                if recipe == "A-raster"
                else total["full_decoded_bytes"]
                if recipe.startswith("C-")
                else total["unique_decoded_bytes"]
            )
            coefficients[recipe] = observations[recipe]["requested_bytes"] / denominator
        ratio = observations["B-raster"]["requested_bytes"] / total["unique_decoded_bytes"]
        miss = (
            observations["A-raster"]["requested_bytes"] / ratio - total["unique_decoded_bytes"]
        ) / (total["logical_decoded_bytes"] - total["unique_decoded_bytes"])
        coefficients["A1_repeat_miss_fraction_relative_to_B1"] = miss
        cohorts[name] = {
            "plan_path": str(plan_path.relative_to(root)),
            "plan_sha256": digest(plan_path),
            "plan_internal_sha256": plan["sha256"],
            "expected_database_path": str(database.relative_to(root)),
            "expected_database_sha256": digest(database),
            "lake_count": evidence["cohorts"][name]["preflight"]["lakes"],
            "products": len(plan["scenes"]),
            "lake_product_memberships": sum(len(scene["members"]) for scene in plan["scenes"]),
            "by_band": dict(by_band),
            "total": total,
            "unique_decoded_fraction_of_full": total["unique_decoded_bytes"]
            / total["full_decoded_bytes"],
            "observations": observations,
            "requested_to_decoded_ratios": coefficients,
        }
    payload5 = 1000000.0 * (4 / 100 + 3 / 400 + 2 / 3600)
    payload17 = 1000000.0 * (12 / 100 + 15 / 400 + 4 / 3600)
    full_payload_ratio = payload17 / payload5
    old_compressed_ratio = 9000000.0 / (10.24**2 * payload17)
    for row in cohorts.values():
        red = row["by_band"]["red"]
        totals = row["total"]
        occupied = occupancy(red["logical_blocks"], row["products"] * 121 * 0.7)
        old_predictions = {}
        for recipe in ("A-raster", "B-raster", "B-lazy"):
            modeled = (
                max(red["logical_blocks"] * 0.5, occupied)
                if recipe == "A-raster"
                else occupied * (1.05 if recipe == "B-raster" else 1)
            )
            estimate = modeled * 9000000.0 / full_payload_ratio
            old_predictions[recipe] = {
                "requested_bytes": estimate,
                "predicted_over_observed": estimate
                / row["observations"][recipe]["requested_bytes"],
            }
        actual_unique_predictions = {
            recipe: {
                "requested_bytes": totals["unique_decoded_bytes"]
                * old_compressed_ratio
                * (1.05 if recipe == "B-raster" else 1),
                "predicted_over_observed": totals["unique_decoded_bytes"]
                * old_compressed_ratio
                * (1.05 if recipe == "B-raster" else 1)
                / row["observations"][recipe]["requested_bytes"],
            }
            for recipe in ("B-raster", "B-lazy")
        }
        row["old_model_conditional_backtest"] = {
            "actual_red_logical_block_driver": red["logical_blocks"],
            "actual_red_unique_blocks": red["unique_blocks"],
            "assumed_available_red_block_pool": row["products"] * 121 * 0.7,
            "predicted_unsaturated_red_block_occupancy": occupied,
            "predictions": old_predictions,
            "qualified_scope": (
                "Actual geometry replaces national population geometry. Original national "
                "two-stratum occupancy and byte assumptions are retained. Five-asset "
                "normalization uses native payload ratio, not 17/5."
            ),
        }
        row["old_byte_coefficient_with_actual_unique_geometry"] = actual_unique_predictions
    holdouts = []
    for training, target in [("florida", "dispersed"), ("dispersed", "florida")]:
        tr = cohorts[training]
        te = cohorts[target]
        tot = te["total"]
        for recipe in ("B-raster", "B-lazy", "C-raster", "C-lazy"):
            decoded = (
                tot["full_decoded_bytes"]
                if recipe.startswith("C-")
                else tot["unique_decoded_bytes"]
            )
            prediction = tr["requested_to_decoded_ratios"][recipe] * decoded
            holdouts.append(
                {
                    "training": training,
                    "held_out": target,
                    "recipe": recipe,
                    "predicted_requested_bytes": prediction,
                    "observed_requested_bytes": te["observations"][recipe]["requested_bytes"],
                    "predicted_over_observed": prediction
                    / te["observations"][recipe]["requested_bytes"],
                }
            )
        prediction = tr["requested_to_decoded_ratios"]["B-raster"] * (
            tot["unique_decoded_bytes"]
            + tr["requested_to_decoded_ratios"]["A1_repeat_miss_fraction_relative_to_B1"]
            * (tot["logical_decoded_bytes"] - tot["unique_decoded_bytes"])
        )
        holdouts.append(
            {
                "training": training,
                "held_out": target,
                "recipe": "A-raster repeat-miss model",
                "predicted_requested_bytes": prediction,
                "observed_requested_bytes": te["observations"]["A-raster"]["requested_bytes"],
                "predicted_over_observed": prediction
                / te["observations"]["A-raster"]["requested_bytes"],
            }
        )
    result = {
        "status": "offline derived check, not a new measurement",
        "checked_on": "2026-09-23",
        "checker": "Independent Codex checking agent /root/claim_checker",
        "evidence_path": str(evidence_path.relative_to(root)),
        "evidence_sha256": digest(evidence_path),
        "decoded_bytes_definition": (
            "Native dtype bytes for each actual source block window, clipped at image "
            "edges. Logical sums repeat each lake-band-block contribution. Unique "
            "sums deduplicate item, band, block row, block column. Full bytes sum "
            "native asset shapes."
        ),
        "cohorts": cohorts,
        "native_payload_bytes_per_km2": {
            "five_measured_assets": payload5,
            "seventeen_modeled_assets": payload17,
            "seventeen_to_five_ratio": full_payload_ratio,
        },
        "old_9MB_block_set_implied_requested_to_decoded_ratio": old_compressed_ratio,
        "cross_cohort_holdouts": holdouts,
        "limitations": [
            (
                "The two cohorts differ in geography and size, not only lake density. "
                "Cross-cohort checks are directional validation from two observations, "
                "not a broad statistical validation."
            ),
            (
                "Requested bytes include range overhead and cache behavior. "
                "Requested-to-decoded ratios are not pure file compression ratios."
            ),
            (
                "Seventeen-asset native payload weights extrapolate unmeasured bands and "
                "quality assets. They do not measure their compression."
            ),
            (
                "The old-model backtest supplies actual red-grid logical blocks but "
                "retains the original assumed national spatial concentration. It isolates "
                "occupancy and bytes from population geometry."
            ),
            (
                "A1 repeat-miss inference is poorly conditioned in the dispersed cohort "
                "because logical and unique block volumes differ by less than one "
                "percent."
            ),
            (
                "Frozen plans and SQLite inputs remain local under data. Aggregate counts "
                "and hashes make the derivation reviewable without distributing polygons."
            ),
        ],
        "generator_path": str(Path(__file__).relative_to(ROOT)),
        "generator_sha256": digest(Path(__file__)),
        "reproduction_command": "uv run python tools/backtest_source_bytes.py",
        "old_model_geometry_qualification": (
            "The original national two-stratum occupancy remains an unsourced "
            "extrapolation. Conditional cohort backtesting predicts Florida unique "
            "footprints about 1.87 times observed, and dispersed footprints about "
            "0.98 times observed. Updating only byte coefficients does not fix that "
            "geography bias."
        ),
    }
    return result


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
            raise SystemExit("Cohort byte checks differ. Run tools/backtest_source_bytes.py.")
        print("Cohort byte checks match saved local evidence and generator.")
    else:
        OUTPUT.write_text(rendered)
        print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
