"""Pixel differences between the two GeoTIFF copies of one acquisition.

Runs only when the user invokes it. It reads the same assets of the same ESA product from
the Collection 1 copy and the older copy, then compares the stored integers pixel by pixel.
It answers whether the copies hold the same numbers, and by how much they differ where they
do not. It reads nothing else and writes nothing back.

    uv run python benchmarks/copy_difference.py --keys coastal nir09 scl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "benchmarks"))

import raw_access  # noqa: E402

from s2proto import harness  # noqa: E402


def grid_mismatch(first: dict, second: dict) -> str | None:
    """Why two dataset descriptions are not the same grid, or None when they are."""
    for key in ("width", "height", "crs"):
        if first.get(key) != second.get(key):
            return f"{key} differs: {first.get(key)} against {second.get(key)}"
    a, b = first.get("transform"), second.get("transform")
    if a is None or b is None or len(a) != len(b):
        return "transform missing"
    if any(abs(x - y) > 1e-6 for x, y in zip(a, b, strict=True)):
        return f"transform differs: {a} against {b}"
    return None


def shared_product(pairing: str) -> bool:
    """Whether pair_items found the same ESA product on every copy."""
    return pairing.startswith("same ESA product")


def rule_check(first, second, both_valid, offset: int = 1000, floor: int = 1) -> dict:
    """Count valid pixels that break second == max(first - offset, floor)."""
    import numpy as np

    expected = np.maximum(first.astype(np.int64) - offset, floor)
    breaks = (second.astype(np.int64) != expected) & both_valid
    return {
        "rule": f"second == max(first - {offset}, {floor}) on pixels valid in both",
        "violations": int(breaks.sum()),
        "first_at_or_below_offset": int(((first.astype(np.int64) <= offset) & both_valid).sum()),
    }


def compare_arrays(first, second, nodata_first, nodata_second) -> dict:
    """Integer differences between two arrays of the same shape."""
    import numpy as np

    if first.shape != second.shape:
        return {"same_shape": False, "shapes": [list(first.shape), list(second.shape)]}
    valid_first = first != nodata_first if nodata_first is not None else np.ones_like(first, bool)
    valid_second = (
        second != nodata_second if nodata_second is not None else np.ones_like(second, bool)
    )
    both_valid = valid_first & valid_second
    diff = second.astype(np.int64) - first.astype(np.int64)
    valid_diff = diff[both_valid]
    counts = Counter(valid_diff.tolist()) if valid_diff.size else Counter()
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    return {
        "same_shape": True,
        "pixels": int(first.size),
        "identical": bool(np.array_equal(first, second)),
        "nodata_agrees": bool(np.array_equal(valid_first, valid_second)),
        "valid_in_both": int(both_valid.sum()),
        "valid_only_in_first": int((valid_first & ~valid_second).sum()),
        "valid_only_in_second": int((~valid_first & valid_second).sum()),
        "equal_where_both_valid": int((valid_diff == 0).sum()),
        "differing_where_both_valid": int((valid_diff != 0).sum()),
        "difference_min": int(valid_diff.min()) if valid_diff.size else None,
        "difference_max": int(valid_diff.max()) if valid_diff.size else None,
        "most_common_differences": [{"second_minus_first": d, "pixels": n} for d, n in top],
        "min_first": int(first.min()),
        "max_first": int(first.max()),
        "min_second": int(second.min()),
        "max_second": int(second.max()),
        "offset_clamp_rule": rule_check(first, second, both_valid),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--tile", default=raw_access.DEFAULT_TILE)
    parser.add_argument("--date", default=raw_access.DEFAULT_DATE)
    parser.add_argument("--keys", nargs="+", default=["coastal", "nir09", "scl"])
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks" / "results" / "copy-difference.json"
    )
    parser.add_argument(
        "--allow-different-products",
        action="store_true",
        help="Compare even when the copies hold different ESA products",
    )
    args = parser.parse_args(argv)

    import rasterio

    measured_at = harness.utc_now()
    client = harness.Client(pause=0.2)
    copies = ["c1", "older"]
    items_by_copy = {
        copy: raw_access.search_items(
            client, raw_access.COPIES[copy]["collection"], args.tile, args.date
        )
        for copy in copies
    }
    chosen, pairing = raw_access.pair_items(items_by_copy)
    print(f"copy difference {measured_at}: {pairing}", flush=True)
    if not shared_product(pairing) and not args.allow_different_products:
        raise SystemExit("the copies hold different ESA products. Nothing compared.")
    assets = {copy: raw_access.resolve_assets(chosen[copy], args.keys) for copy in copies}
    by_key = {}
    with rasterio.Env(**raw_access.GDAL_ENV), harness.GdalLogCapture() as capture:
        for key in args.keys:
            hrefs = {
                copy: next((a for a in assets[copy]["assets"] if a["key"] == key), None)
                for copy in copies
            }
            if any(h is None for h in hrefs.values()):
                by_key[key] = {"missing_on": [c for c, h in hrefs.items() if h is None]}
                print(f"{key}: missing on {by_key[key]['missing_on']}", flush=True)
                continue
            arrays, infos, logs = {}, {}, {}
            for copy in copies:
                infos[copy], arrays[copy] = raw_access.read_with_gdal(hrefs[copy]["href"])
                logs[copy] = harness.parse_gdal_log(capture.take())
            mismatch = grid_mismatch(infos["c1"], infos["older"])
            if mismatch:
                comparison = {"same_shape": False, "grid_mismatch": mismatch}
                same_size = all(infos["c1"][k] == infos["older"][k] for k in ("width", "height"))
                if not same_size:
                    comparison["shapes"] = [[infos[c]["height"], infos[c]["width"]] for c in copies]
            else:
                comparison = compare_arrays(
                    arrays["c1"], arrays["older"], infos["c1"]["nodata"], infos["older"]["nodata"]
                )
            by_key[key] = {
                "hrefs": {c: hrefs[c]["href"] for c in copies},
                "catalog_scale_offset": {
                    c: {"scale": hrefs[c]["scale"], "offset": hrefs[c]["offset"]} for c in copies
                },
                "gsd": {c: hrefs[c]["gsd"] for c in copies},
                "reads": {c: {**infos[c], **logs[c]} for c in copies},
                "comparison": comparison,
            }
            print(
                f"{key}: identical={comparison.get('identical')} "
                f"differing={comparison.get('differing_where_both_valid')} "
                f"top={comparison.get('most_common_differences', [])[:3]}",
                flush=True,
            )
    output = {
        "schema_version": 1,
        "measured_at": measured_at,
        "code_version": harness.code_version(),
        "script": "benchmarks/copy_difference.py",
        "machine": harness.machine_info(),
        "endpoints": {
            copy: {
                "collection": raw_access.COPIES[copy]["collection"],
                "bucket": raw_access.COPIES[copy]["bucket"],
                "region": "us-west-2",
                "payer": "provider. Public bucket, unsigned requests, RequesterPays false.",
            }
            for copy in copies
        },
        "catalog": {"root": raw_access.ES_ROOT, "tile": args.tile, "date": args.date},
        "pairing": pairing,
        "items": {copy: raw_access.trim_item(chosen[copy]) for copy in copies},
        "by_key": by_key,
        "catalog_request_log": client.log,
        "limitations": [
            "One acquisition of one tile. The listed assets only.",
            "Differences are between stored integers. The catalog's scale and offset are "
            "recorded beside them, not applied.",
            "A dominant difference equal to the declared offset in stored units is consistent "
            "with one copy having the offset applied. The provider's own statement of what it "
            "applied is the per-item flag, recorded from the catalog.",
            "The offset and clamp rule is checked pixel by pixel with a fixed offset of 1000 "
            "and floor of 1. Violations are counted, not explained.",
            "Same product and same grid are required before pixels are subtracted. A grid "
            "mismatch is recorded and not compared.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=1) + "\n")
    print(f"wrote {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
