"""Pixel validity of the USGS aquatic reflectance product per band and pixel class.

Pure counting for probe T4 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.
The rules and tolerances below were fixed before any pixel was read. Nothing here contacts a
provider. benchmarks/aqr_validity.py reads the windows when the user invokes it.
"""

from __future__ import annotations

import numpy as np

from s2proto.masks import CLASS_CODES

NODATA = -32768
"""The no-data value every product GeoTIFF declares, measurement finding 26."""
FLAG_FACTOR = 10_000
"""In one crop every flags value was the ACOLITE flag integer times 10,000, finding 29."""
UNIT = 10_000
"""USGS documents a reflectance factor of 10,000. A stored value above it is above one."""
SCL_NODATA = 0
SCL_WATER = 6
SCL_SHADOW = (3,)
SCL_CLOUD = (8, 9, 10)
SCL_CLASSES = 12
BANDS = ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12")
MASKED_SHARE = 0.01
"""A pixel class counts as masked by the processor above this share, decision rule R3."""
GRID_TOLERANCE_PIXELS = 1e-6

TOLERANCES = {
    "R1_grid": (
        "The product window and the joined Level-2A scene classification window must share the "
        "CRS, a 20 m pixel, and a zero-pixel origin offset, from the file headers, within "
        f"{GRID_TOLERANCE_PIXELS} pixel. A scene that fails keeps its band counts and is left out "
        "of every comparison with the scene classification."
    ),
    "R2_flags": (
        f"A flags value decodes when it is an exact multiple of {FLAG_FACTOR}. Zero tolerance. "
        "Other values are counted as not_multiple and never rounded."
    ),
    "R3_masking": (
        f"A band pixel is no_data when it holds {NODATA}. It is also processor_masked when the "
        f"joined scene classification holds data there, any class but {SCL_NODATA}. Without a "
        "usable join, processor_masked is null. A pixel class counts as masked by the processor "
        "when, pooled over scenes and lakes, the processor_masked share of its joined pixels "
        f"exceeds {MASKED_SHARE:.0%} in any band. Every processor_masked pixel is reported "
        "whatever the share."
    ),
    "R4_values": (
        f"A stored value is negative when it lies between {NODATA} and 0, exclusive, and above "
        f"one when it exceeds {UNIT}. Counted per band and class. No tolerance."
    ),
    "R5_water": (
        "Water by NDWI means a delivered NDWI value above 0. Water by ACOLITE means the flag at "
        "exponent flag_exponent_swir is clear. Water by Level-2A means scene classification "
        f"class {SCL_WATER}. Agreement is counted where all three layers hold data. Descriptive, "
        "no tolerance."
    ),
    "R6_cloud": (
        f"Level-2A cloud means scene classification classes {list(SCL_CLOUD)}, and shadow class "
        f"{list(SCL_SHADOW)}. Such a pixel is unflagged when its decoded ACOLITE flag integer is "
        "0. Descriptive, no tolerance. The scene classification is a land product with its own "
        "errors, claims Q1, Q4, and Q8."
    ),
    "R7_ndwi_recompute": (
        "Diagnostic only. A stored NDWI value agrees with a band pair when it lies within half a "
        f"unit of {UNIT} times (G - N) / (G + N), for some G and N within half a unit of the "
        "stored B03 and the stored B08 or B8A. Pixels whose G + N interval reaches zero are not "
        "comparable."
    ),
}


def flag_exponents(settings: dict[str, str]) -> dict[str, int]:
    """Flag names and bit exponents from the settings keys flag_exponent_<name>."""
    out = {}
    for key, value in settings.items():
        if key.startswith("flag_exponent_"):
            try:
                out[key.removeprefix("flag_exponent_")] = int(value)
            except ValueError:
                continue
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


def decode_flags(flags: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decoded flag integers, the no-data mask, and the mask of values that do not decode."""
    values = flags.astype(np.int64)
    missing = values == NODATA
    not_multiple = ~missing & (values % FLAG_FACTOR != 0)
    decoded = np.where(missing | not_multiple, 0, values // FLAG_FACTOR)
    return decoded, missing, not_multiple


def _count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def ndwi_agrees(green: np.ndarray, nir: np.ndarray, ndwi: np.ndarray) -> tuple[int, int]:
    """Comparable pixels and agreeing pixels under rule R7. Inputs are valid stored integers."""
    g = green.astype(np.float64)
    n = nir.astype(np.float64)
    comparable = (g + n - 1.0) > 0
    if not comparable.any():
        return 0, 0
    g, n, d = g[comparable], n[comparable], ndwi[comparable].astype(np.float64)
    steps = [(dg, dn) for dg in (-0.5, 0.5) for dn in (-0.5, 0.5)]
    corners = [((g + dg) - (n + dn)) / ((g + dg) + (n + dn)) for dg, dn in steps]
    low = np.minimum.reduce(corners) * UNIT - 0.5
    high = np.maximum.reduce(corners) * UNIT + 0.5
    return int(comparable.sum()), _count((d >= low) & (d <= high))


def agreement(usable: np.ndarray, test: np.ndarray, reference: np.ndarray) -> dict[str, int]:
    """Two-by-two counts of a product water test against the Level-2A water class."""
    return {
        "both": _count(usable & test & reference),
        "product_only": _count(usable & test & ~reference),
        "scl_only": _count(usable & ~test & reference),
        "neither": _count(usable & ~test & ~reference),
    }


def class_counts(
    pixel_class: np.ndarray,
    bands: dict[str, np.ndarray],
    ndwi: np.ndarray,
    flags: np.ndarray,
    exponents: dict[str, int],
    scl: np.ndarray | None,
) -> dict[str, dict]:
    """Validity counts per pixel class for one lake window of one scene.

    Every array shares the window of pixel_class. scl is None when the scene has no usable
    join to a Level-2A scene classification under rule R1.
    """
    decoded, flags_missing, not_multiple = decode_flags(flags)
    known_bits = sum(1 << bit for bit in exponents.values())
    swir_bit = 1 << exponents["swir"] if "swir" in exponents else None
    out = {}
    for name, code in CLASS_CODES.items():
        sel = pixel_class == code
        pixels = _count(sel)
        if pixels == 0:
            out[name] = {"pixels": 0}
            continue
        joined = None if scl is None else sel & (scl != SCL_NODATA)
        record = {"pixels": pixels, "joined_pixels": None if joined is None else _count(joined)}

        band_counts = {}
        for band, values in bands.items():
            missing = values == NODATA
            band_counts[band] = {
                "no_data": _count(sel & missing),
                "processor_masked": None if joined is None else _count(joined & missing),
                "negative": _count(sel & ~missing & (values < 0)),
                "above_one": _count(sel & (values > UNIT)),
            }
        record["bands"] = band_counts

        ndwi_missing = ndwi == NODATA
        record["ndwi"] = {
            "no_data": _count(sel & ndwi_missing),
            "positive": _count(sel & (ndwi > 0)),
            "zero": _count(sel & (ndwi == 0)),
            "negative": _count(sel & ~ndwi_missing & (ndwi < 0)),
            "outside_unit": _count(sel & ~ndwi_missing & (np.abs(ndwi.astype(np.int32)) > UNIT)),
        }

        valid_flags = sel & ~flags_missing & ~not_multiple
        record["flags"] = {
            "no_data": _count(sel & flags_missing),
            "not_multiple": _count(sel & not_multiple),
            "none": _count(valid_flags & (decoded == 0)),
            "bits": {
                flag: _count(valid_flags & ((decoded >> bit) & 1 == 1))
                for flag, bit in exponents.items()
            },
            "unknown_bits": _count(valid_flags & ((decoded & ~known_bits) != 0)),
        }

        green, ndwi_ok = bands.get("B03"), sel & ~ndwi_missing
        recompute = {}
        if green is not None:
            for band in ("B08", "B8A"):
                nir = bands.get(band)
                if nir is None:
                    continue
                ok = ndwi_ok & (green != NODATA) & (nir != NODATA)
                comparable, agree = ndwi_agrees(green[ok], nir[ok], ndwi[ok])
                recompute[band] = {"comparable": comparable, "agree": agree}
        record["ndwi_recompute"] = recompute

        if joined is None:
            record["scl"] = None
            record["water"] = None
            record["cloud"] = None
        else:
            hist = np.bincount(scl[sel].astype(np.int64), minlength=SCL_CLASSES)
            record["scl"] = {str(i): int(v) for i, v in enumerate(hist) if v}
            scl_water = scl == SCL_WATER
            usable = joined & ~ndwi_missing & ~flags_missing & ~not_multiple
            ndwi_water = ndwi > 0

            water = {
                "usable": _count(usable),
                "ndwi_vs_scl": agreement(usable, ndwi_water, scl_water),
            }
            if swir_bit is not None:
                acolite_water = (decoded & swir_bit) == 0
                water["acolite_vs_scl"] = agreement(usable, acolite_water, scl_water)
            record["water"] = water

            cloud = joined & np.isin(scl, SCL_CLOUD) & ~flags_missing & ~not_multiple
            shadow = joined & np.isin(scl, SCL_SHADOW) & ~flags_missing & ~not_multiple
            record["cloud"] = {
                "scl_cloud": _count(cloud),
                "scl_cloud_unflagged": _count(cloud & (decoded == 0)),
                "scl_cloud_by_flag": {
                    flag: _count(cloud & ((decoded >> bit) & 1 == 1))
                    for flag, bit in exponents.items()
                },
                "scl_shadow": _count(shadow),
                "scl_shadow_unflagged": _count(shadow & (decoded == 0)),
            }
        out[name] = record
    return out


def _add(total: dict, part: dict) -> None:
    """Add nested integer counts of part into total. None stays None only if never counted."""
    for key, value in part.items():
        if isinstance(value, dict):
            if total.get(key) is None:
                total[key] = {}
            _add(total[key], value)
        elif value is None:
            total.setdefault(key, None)
        else:
            total[key] = (total.get(key) or 0) + value


def pool(records: list[dict], key=lambda record: "all") -> dict[str, dict]:
    """Sum the per-class counts of scene-lake records, grouped by key, then by pixel class."""
    groups: dict[str, dict] = {}
    for record in records:
        group = groups.setdefault(str(key(record)), {})
        for name, counts in record["classes"].items():
            _add(group.setdefault(name, {}), counts)
    return groups


def share(part: int | None, whole: int | None) -> float | None:
    if part is None or not whole:
        return None
    return round(part / whole, 6)


def class_verdicts(pooled: dict[str, dict]) -> dict[str, dict]:
    """Rule R3 applied to pooled counts: the largest processor_masked share per class."""
    out = {}
    for name in CLASS_CODES:
        counts = pooled.get(name, {})
        joined = counts.get("joined_pixels")
        shares = {
            band: share(values.get("processor_masked"), joined)
            for band, values in counts.get("bands", {}).items()
        }
        known = {band: value for band, value in shares.items() if value is not None}
        largest = max(known.values()) if known else None
        out[name] = {
            "joined_pixels": joined,
            "processor_masked_share_by_band": shares,
            "largest_share": largest,
            "masked_by_processor": None if largest is None else largest > MASKED_SHARE,
        }
    return out
