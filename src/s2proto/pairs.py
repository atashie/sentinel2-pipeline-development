"""Paired values of the two standalone options on the same pixels, probe T5.

Pure arithmetic for probe T5 of the replan record, docs/reviews/2026-10-13-acolite-first-replan.md.
The rules and tolerances below were fixed before any pixel was read. Nothing here contacts a
provider. benchmarks/aqr_pairs.py reads the windows when the user invokes it.

Decision 0009 makes ACOLITE only and Sen2Cor only two standalone options. This comparison joins
nothing in a store. It describes where the two corrections give different values for the same
pixel. It ranks neither, assumption A52.
"""

from __future__ import annotations

import numpy as np

from s2proto import validity
from s2proto.masks import CLASS_CODES

UNIT = 10_000
"""Both products store reflectance times 10,000. USGS documents the factor, finding 26."""
NODATA = validity.NODATA
C1_NODATA = 0
SCL_WATER = validity.SCL_WATER
DISAGREE_UNITS = 50
"""A pixel disagrees when the two values differ by more than 0.005 reflectance."""
AGREE_SHARE = 0.90
MIN_RECORD_PIXELS = 100
DIFF_LIMIT = 5_000
VALUE_LOW, VALUE_HIGH = -5_000, 15_000
QUALITIES = ("all", "both_clear_water")
CLASSES = tuple(CLASS_CODES)

TOLERANCES = {
    "P1_pairing": (
        "Each primary product pairs with the Collection 1 item of the same datastrip. The "
        "product name with MSIL1C in place of MSIAQR names its Level-1C input. Earth Search's "
        "Level-1C item of that name declares a datastrip. The pair is the Collection 1 item of "
        "the same tile and platform whose datastrip has the same sensing start. A product "
        "without such an item is reported and left out. The older collection is not used."
    ),
    "P2_grid": (
        "Every Collection 1 asset read must share the product's CRS and tile origin, from the "
        "file headers, within 1e-06 pixel at its own resolution. A scene that fails is left out "
        "of every comparison."
    ),
    "P3_resampling": (
        "The primary product has one 20 m grid. A 20 m Collection 1 band is compared pixel for "
        "pixel. A 10 m band is the mean of the four 10 m pixels inside the 20 m pixel, used only "
        "when all four hold data. B01 at 60 m takes the 60 m pixel that contains the 20 m pixel."
    ),
    "P4_units": (
        f"Product values are divided by {UNIT}. Collection 1 values are the stored integer times "
        "the scale plus the offset its asset declares. Differences are product minus Collection "
        "1, in reflectance, and are reported in integer units of 1e-04."
    ),
    "P5_comparable": (
        f"A pixel is comparable in a band when the product value is not {NODATA} and the "
        f"Collection 1 value, or each 10 m value it averages, is not {C1_NODATA}."
    ),
    "P6_strata": (
        "Results are reported per band and pixel class, interior, shoreline, and near-land, "
        "masks version 2 at 20 m. Two quality subsets: all comparable pixels, and "
        "both_clear_water, where the decoded ACOLITE flag integer is 0 and the scene "
        f"classification is class {SCL_WATER}. Each option's own flags define its own clear water."
    ),
    "P7_disagreement": (
        f"A pixel disagrees when the absolute difference exceeds {DISAGREE_UNITS} units, 0.005 "
        f"reflectance. A band and class agrees when at least {AGREE_SHARE:.0%} of its comparable "
        "pixels do not disagree. Otherwise it differs. Pooled over scenes and lakes, per quality "
        "subset. This describes difference, not error. Neither product is a reference."
    ),
    "P8_spread": (
        "Descriptive. Per scene-lake record with at least "
        f"{MIN_RECORD_PIXELS} comparable pixels, the median difference. Its spread across "
        "records is reported so that large lakes do not hide scene-to-scene variation."
    ),
    "P9_offset_diagnostic": (
        "Diagnostic only, not a rule. Per scene, the declared Collection 1 offset, and the 1st "
        "and 50th percentiles of the stored B11 and B12 integers over interior pixels the scene "
        "classification calls water. It shows whether the declared offset matches the data. "
        "It never changes P4."
    ),
}


def class_masks(pixel_class: np.ndarray) -> dict[str, np.ndarray]:
    return {name: pixel_class == code for name, code in CLASS_CODES.items()}


def block_mean_10m(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mean of each 2 by 2 block of a 10 m window, and where all four pixels hold data."""
    h, w = values.shape[0] // 2, values.shape[1] // 2
    blocks = values[: h * 2, : w * 2].reshape(h, 2, w, 2).astype(np.float64)
    valid = (blocks != C1_NODATA).all(axis=(1, 3))
    return blocks.mean(axis=(1, 3)), valid


def parent_60m(values: np.ndarray, row_off: int, col_off: int, height: int, width: int):
    """The 60 m pixel containing each 20 m pixel of a window, from a 60 m window.

    The 60 m window starts at row_off // 3 and col_off // 3 of the 60 m grid.
    """
    rows = (np.arange(row_off, row_off + height) // 3) - row_off // 3
    cols = (np.arange(col_off, col_off + width) // 3) - col_off // 3
    picked = values[np.ix_(rows, cols)]
    return picked.astype(np.float64), picked != C1_NODATA


def window_60m(row_off: int, col_off: int, height: int, width: int) -> tuple[int, int, int, int]:
    r0, c0 = row_off // 3, col_off // 3
    r1, c1 = (row_off + height - 1) // 3 + 1, (col_off + width - 1) // 3 + 1
    return r0, c0, r1 - r0, c1 - c0


class Moments:
    """Running sums for one stratum, and an integer histogram of the differences."""

    __slots__ = (
        "n",
        "sa",
        "ss",
        "saa",
        "sss",
        "sas",
        "sd",
        "sdd",
        "sabs",
        "disagree",
        "a_neg",
        "s_neg",
        "hist_d",
        "hist_a",
        "hist_s",
        "clipped",
    )

    def __init__(self, values: bool = False):
        self.n = 0
        self.sa = self.ss = self.saa = self.sss = self.sas = 0.0
        self.sd = self.sdd = self.sabs = 0.0
        self.disagree = self.a_neg = self.s_neg = 0
        self.hist_d = np.zeros(2 * DIFF_LIMIT + 1, dtype=np.int64)
        self.hist_a = np.zeros(VALUE_HIGH - VALUE_LOW + 1, dtype=np.int64) if values else None
        self.hist_s = np.zeros(VALUE_HIGH - VALUE_LOW + 1, dtype=np.int64) if values else None
        self.clipped = 0

    def add(self, a: np.ndarray, s: np.ndarray) -> None:
        """a and s in integer units of 1e-04 reflectance, float64, comparable pixels only."""
        if a.size == 0:
            return
        d = a - s
        self.n += int(a.size)
        self.sa += float(a.sum())
        self.ss += float(s.sum())
        self.saa += float((a * a).sum())
        self.sss += float((s * s).sum())
        self.sas += float((a * s).sum())
        self.sd += float(d.sum())
        self.sdd += float((d * d).sum())
        self.sabs += float(np.abs(d).sum())
        self.disagree += int((np.abs(d) > DISAGREE_UNITS).sum())
        self.a_neg += int((a < 0).sum())
        self.s_neg += int((s < 0).sum())
        rounded = np.rint(d).astype(np.int64)
        self.clipped += int((np.abs(rounded) > DIFF_LIMIT).sum())
        self.hist_d += np.bincount(
            np.clip(rounded, -DIFF_LIMIT, DIFF_LIMIT) + DIFF_LIMIT, minlength=self.hist_d.size
        )
        if self.hist_a is not None:
            for values, hist in ((a, self.hist_a), (s, self.hist_s)):
                index = np.clip(np.rint(values).astype(np.int64), VALUE_LOW, VALUE_HIGH)
                hist += np.bincount(index - VALUE_LOW, minlength=hist.size)

    def merge(self, other: Moments) -> None:
        for name in (
            "n",
            "sa",
            "ss",
            "saa",
            "sss",
            "sas",
            "sd",
            "sdd",
            "sabs",
            "disagree",
            "a_neg",
            "s_neg",
            "clipped",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        self.hist_d += other.hist_d
        if self.hist_a is not None and other.hist_a is not None:
            self.hist_a += other.hist_a
            self.hist_s += other.hist_s


def hist_quantile(hist: np.ndarray, low: int, fraction: float) -> int | None:
    """Nearest-rank quantile of an integer histogram whose first bin is `low`."""
    total = int(hist.sum())
    if not total:
        return None
    rank = max(1, int(np.ceil(fraction * total)))
    return int(np.searchsorted(np.cumsum(hist), rank) + low)


def summarize(m: Moments) -> dict:
    if not m.n:
        return {"n": 0}
    n = m.n
    var_a = m.saa / n - (m.sa / n) ** 2
    var_s = m.sss / n - (m.ss / n) ** 2
    cov = m.sas / n - (m.sa / n) * (m.ss / n)
    r = cov / np.sqrt(var_a * var_s) if var_a > 0 and var_s > 0 else None
    agree_share = 1 - m.disagree / n
    out = {
        "n": n,
        "difference_units": {
            "mean": round(m.sd / n, 2),
            "rms": round(float(np.sqrt(m.sdd / n)), 2),
            "mean_absolute": round(m.sabs / n, 2),
            **{
                f"p{int(q * 100):02d}": hist_quantile(m.hist_d, -DIFF_LIMIT, q)
                for q in (0.05, 0.25, 0.5, 0.75, 0.95)
            },
            "clipped_at_limit": m.clipped,
        },
        "mean_units": {"product": round(m.sa / n, 2), "c1": round(m.ss / n, 2)},
        "pearson_r": round(float(r), 4) if r is not None else None,
        "share_disagree": round(m.disagree / n, 4),
        "share_negative": {"product": round(m.a_neg / n, 4), "c1": round(m.s_neg / n, 4)},
        "verdict": "agree" if agree_share >= AGREE_SHARE else "differs",
    }
    if m.hist_a is not None:
        out["median_units"] = {
            "product": hist_quantile(m.hist_a, VALUE_LOW, 0.5),
            "c1": hist_quantile(m.hist_s, VALUE_LOW, 0.5),
        }
    return out


def record_summary(a: np.ndarray, s: np.ndarray) -> dict:
    """Per scene-lake stratum: count, median and mean difference in units."""
    if a.size == 0:
        return {"n": 0}
    d = a - s
    return {
        "n": int(a.size),
        "median": round(float(np.median(d)), 2),
        "mean": round(float(d.mean()), 2),
        "share_disagree": round(float((np.abs(d) > DISAGREE_UNITS).mean()), 4),
    }


def spread(values: list[float]) -> dict | None:
    if not values:
        return None
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return {
        "records": int(ordered.size),
        "min": round(float(ordered[0]), 2),
        "p25": round(float(np.percentile(ordered, 25)), 2),
        "median": round(float(np.median(ordered)), 2),
        "p75": round(float(np.percentile(ordered, 75)), 2),
        "max": round(float(ordered[-1]), 2),
    }
