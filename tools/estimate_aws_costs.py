"""Offline planning arithmetic, not an AWS benchmark or a hydrography census."""

import argparse
import copy
import hashlib
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/cost-analysis/inputs.json"
OUTPUT = ROOT / "docs/cost-analysis/estimates.json"
REPORT = ROOT / "docs/aws-cost-analysis.md"
EVIDENCE = ROOT / "benchmarks/results/lazy-reader-workloads.json"
COHORTS = ROOT / "docs/cost-analysis/cohort-blocks.json"
SURVEY = ROOT / "benchmarks/results/gap-survey.json"
GIB = 2**30
TIB = 2**40


def storage_price(gib, rates):
    """Marginal S3 tiers use binary storage units, not decimal transfer GB."""
    return (
        min(gib, 50 * 1024) * rates[0]
        + min(max(gib - 50 * 1024, 0), 450 * 1024) * rates[1]
        + max(gib - 500 * 1024, 0) * rates[2]
    )


def occupancy(draws, cells, concentrated_fraction, concentrated_mass):
    """Poisson occupancy approximation with two geographic density strata."""
    result = 0.0
    for fraction, mass in (
        (concentrated_fraction, concentrated_mass),
        (1 - concentrated_fraction, 1 - concentrated_mass),
    ):
        capacity = cells * fraction
        result += capacity * -math.expm1(-draws * mass / capacity)
    return result


def population(settings, count, area):
    bins = [dict(item) for item in settings["area_bins"]]
    bins[0]["count"] = count - sum(item["count"] for item in bins[1:])
    known_area = sum(item["count"] * item["mean_km2"] for item in bins[:-1])
    bins[-1]["mean_km2"] = (area - known_area) / bins[-1]["count"]
    assert bins[0]["count"] > 0 and bins[-1]["mean_km2"] > 0.5
    return bins


def cpu_wall_seconds(cpu_seconds, memory_gib, parallel_fraction, max_threads):
    """An explicit Amdahl scenario, not an empirical Lambda speedup curve."""
    vcpu = min(6, memory_gib * 1024 / 1769)
    serial = (1 - parallel_fraction) / min(vcpu, 1)
    parallel = parallel_fraction / min(vcpu, max_threads)
    return cpu_seconds * (serial + parallel)


def object_count(history_bytes, months, active_tiles, settings):
    """Compare tile-month partitions with cross-tile compaction per grid-month."""
    groups = 3 * math.ceil(months)
    target = settings["target_object_bytes"]
    if settings["object_layout"] == "tile_month":
        return math.ceil(max(groups * active_tiles, history_bytes / target))
    # Equal-size grid-month groups are an approximation. Edge objects can be smaller.
    return groups * max(1, math.ceil(history_bytes / groups / target))


def observed_a1_ratio(redundancy, calibrated):
    """Interpolate in repeated block work, clamping to the observed ratio envelope."""
    anchors = sorted(
        (r["logical_to_unique_decoded_ratio"], r["a1_b1_byte_ratio"])
        for r in calibrated["byte_calibration"]["cohorts"]
    )
    (lo_redundancy, lo_ratio), (hi_redundancy, hi_ratio) = anchors
    weight = (redundancy - lo_redundancy) / (hi_redundancy - lo_redundancy)
    return lo_ratio + min(1, max(0, weight)) * (hi_ratio - lo_ratio)


def fit_concentration(draws, cells, fraction, target):
    """Fit one clustering parameter. This is calibration, not a validation observation."""
    lo, hi = fraction, 1.0
    assert occupancy(draws, cells, fraction, hi) <= target
    assert occupancy(draws, cells, fraction, lo) >= target
    for _ in range(60):
        middle = (lo + hi) / 2
        if occupancy(draws, cells, fraction, middle) > target:
            lo = middle
        else:
            hi = middle
    return (lo + hi) / 2


def calibration():
    evidence = json.loads(EVIDENCE.read_text())
    blocks = json.loads(COHORTS.read_text())
    settings = json.loads(INPUT.read_text())
    assert blocks["evidence_sha256"] == hashlib.sha256(EVIDENCE.read_bytes()).hexdigest()
    result = {}
    for code, original in {"A1": "A-raster", "B1": "B-raster", "B3": "B-lazy"}.items():
        rows = []
        for name, cohort in evidence["cohorts"].items():
            row = next(r for r in cohort["comparisons"] if r["configuration"] == original)
            cpu = sum(row["cpu"].values())
            rows.append(
                {
                    "cohort": name,
                    "cpu_seconds": cpu,
                    "requested_bytes": row["io"]["bytes_requested"],
                    "total_extraction_seconds": row["extraction_seconds"],
                    "cpu_seconds_per_requested_MB": cpu / (row["io"]["bytes_requested"] / 1e6),
                }
            )
        result[code] = {
            "observations": rows,
            "cpu_seconds_per_requested_MB": sum(row["cpu_seconds_per_requested_MB"] for row in rows)
            / len(rows),
        }
        if code != "A1":
            result[code]["requested_per_decoded_byte"] = sum(
                c["requested_to_decoded_ratios"][original] for c in blocks["cohorts"].values()
            ) / len(blocks["cohorts"])
    result["byte_calibration"] = {
        "cohorts": [
            {
                "cohort": name,
                "memberships_per_product": c["lake_product_memberships"] / c["products"],
                "logical_to_unique_decoded_ratio": c["total"]["logical_decoded_bytes"]
                / c["total"]["unique_decoded_bytes"],
                "a1_b1_byte_ratio": c["observations"]["A-raster"]["requested_bytes"]
                / c["observations"]["B-raster"]["requested_bytes"],
                "decoded_fraction_of_full": c["unique_decoded_fraction_of_full"],
            }
            for name, c in blocks["cohorts"].items()
        ],
        "old_model_backtests": {
            name: c["old_model_conditional_backtest"] for name, c in blocks["cohorts"].items()
        },
        "cross_cohort_holdouts": blocks["cross_cohort_holdouts"],
        "qualification": "Holdouts condition on actual blocks. National occupancy is unvalidated.",
    }
    florida = blocks["cohorts"]["florida"]
    pool_per_product = (
        settings["blocks_per_tile_proxy"] * settings["cases"]["base"]["accessible_block_fraction"]
    )
    fraction = settings["cases"]["base"]["concentrated_fraction"]
    mass = fit_concentration(
        florida["by_band"]["red"]["logical_blocks"],
        florida["products"] * pool_per_product,
        fraction,
        florida["by_band"]["red"]["unique_blocks"],
    )
    result["byte_calibration"]["spatial_fit"] = {
        "training": "florida",
        "fitted_concentrated_mass": mass,
        "fixed_concentrated_fraction": fraction,
        "fixed_pool_per_product": pool_per_product,
        "checks": [
            {
                "cohort": name,
                "role": "fit" if name == "florida" else "sparse_holdout",
                "actual_unique_red_blocks": c["by_band"]["red"]["unique_blocks"],
                "predicted_unique_red_blocks": occupancy(
                    c["by_band"]["red"]["logical_blocks"],
                    c["products"] * pool_per_product,
                    fraction,
                    mass,
                ),
            }
            for name, c in blocks["cohorts"].items()
        ],
    }
    return result


@lru_cache(maxsize=1)
def survey_rates():
    """Aggregate frozen metadata only, excluding Alaska, Erie, and non-US sites."""
    survey = json.loads(SURVEY.read_text())
    sites = [
        site
        for site in survey["sites"]
        if site["group"] == "us" and site["site_id"] not in ("iliamna", "erie-west")
    ]
    tiles = sorted({tile for site in sites for tile in site["tiles"]})
    months = survey["window"]["months"]
    counts = {
        month: sum(survey["tiles"][tile]["reference"]["acquisitions"][i] for tile in tiles)
        for i, month in enumerate(months)
        if month < "2026-09"
    }
    recent = {m: n for m, n in counts.items() if m >= "2025-09"}
    annual = {
        str(year): sum(n for m, n in counts.items() if m.startswith(str(year))) / len(tiles)
        for year in range(2021, 2026)
    }
    return {
        "tile_ids": tiles,
        "site_ids": [site["site_id"] for site in sites],
        "annual_tile_acquisitions": annual,
        "early_annual_tile_rate": sum(annual[str(y)] for y in range(2021, 2025)) / 4,
        "recent_annual_tile_rate": sum(recent.values()) / len(tiles),
        "recent_monthly_counts": recent,
        "recent_peak_month_count_over_mean": max(recent.values()) / (sum(recent.values()) / 12),
        "historical_complete_month_epochs": sum(counts.values()) / len(tiles),
        "historical_complete_month_end": "2026-09-01",
        "replacement_2022_epochs": sum(n for m, n in counts.items() if "2022-01" <= m <= "2022-11")
        / len(tiles),
        "site_max_footprint_items": {
            site["site_id"]: max(site["tiles"].values()) for site in sites
        },
        "qualification": (
            "Purpose-selected metadata counts, not national rates or valid pixel "
            "observations. Site counts are raw items, not acquisition unions."
        ),
    }


def acquisition_rates(settings, case):
    evidence = survey_rates()
    days = (
        date.fromisoformat(settings["end_exclusive"]) - date.fromisoformat(settings["start"])
    ).days
    tail = (
        date.fromisoformat(settings["end_exclusive"])
        - date.fromisoformat(evidence["historical_complete_month_end"])
    ).days
    tile_epochs = (
        evidence["historical_complete_month_epochs"]
        + tail * evidence["recent_annual_tile_rate"] / 365.25
    )
    fraction = settings["daily_updates"]["cases"][case]["point_to_tile_fraction"]
    return {"tile": tile_epochs / days * 365.25, "point": tile_epochs / days * 365.25 * fraction}


def estimate(settings, case, sample, land, calibration_rows, rate_override=None):
    s = settings
    p = s["prices"]
    c = dict(s["cases"][case])
    rates = rate_override or (
        acquisition_rates(s, case)
        if s["acquisition_model"] == "survey_split"
        else {"point": c["acquisitions_per_year"], "tile": c["acquisitions_per_year"]}
    )
    c["acquisitions_per_year"] = rates["point"]
    # Sample stress cases invert population size to vary area per sampled body correctly.
    if sample and case != "base":
        opposite = "high" if case == "low" else "low"
        c["population"] = s["cases"][opposite]["population"]
    bins = population(s, c["population"], c["water_area_km2"])
    n = s["sample_size"] if sample else c["population"]
    fraction = n / c["population"]
    water = c["water_area_km2"] * fraction
    perimeter = (
        sum(b["count"] * 2 * math.sqrt(math.pi * b["mean_km2"]) * b["sqrt_moment"] for b in bins)
        * c["shore_complexity"]
        * fraction
    )
    radius = s["land_radius_km"] if land else 0
    buffer = c["buffer_retention"] * (radius * perimeter + math.pi * radius**2 * n)
    pixels = {}
    for resolution in (10, 20, 60):
        r = resolution / 1000
        water_shore = water / r**2 + 2 * perimeter / (math.pi * r) + n
        pixels[str(resolution)] = max(water_shore, (water + buffer) / r**2)
    years = (date.fromisoformat(s["end_exclusive"]) - date.fromisoformat(s["start"])).days / 365.25
    acquisitions = years * c["acquisitions_per_year"]
    retained_epochs = acquisitions * c["pixel_overlap"] * c["revisions"]
    memberships = n * c["lake_tile_membership"]
    raw_values = sum(pixels[r] * size for r, size in s["value_bytes_per_grid_pixel"].items())
    raw_flags = sum(pixels.values()) * s["flag_bytes_per_grid_pixel"]
    raw_metadata = memberships * s["observation_metadata_bytes"]
    # Overlap is applied to grid pixels. Body metadata already uses lake-tile membership.
    dynamic_epoch = (
        ((raw_values + raw_flags) * c["pixel_overlap"] + raw_metadata)
        * c["layout_multiplier"]
        / c["output_compression"]
    )
    history_bytes = dynamic_epoch * acquisitions * c["revisions"]
    static_bytes = (
        sum(pixels.values()) * s["static_bytes_per_grid_pixel"] * c["pixel_overlap"]
        + n * s["static_body_metadata_bytes"]
    ) / c["output_compression"]
    daily_bytes = history_bytes / (years * 365.25)

    # Whole block intersections are modeled separately from retained pixel area.
    block_km = s["source_block_km_proxy"]
    read_area = water + buffer
    read_perimeter = perimeter + 2 * math.pi * radius * n
    logical_blocks = (n + read_area / block_km**2 + 2 * read_perimeter / (math.pi * block_km)) * c[
        "lake_tile_membership"
    ]
    block_pool = c["tiles"] * s["blocks_per_tile_proxy"] * c["accessible_block_fraction"]
    block_mass = (
        calibration_rows["byte_calibration"]["spatial_fit"]["fitted_concentrated_mass"]
        if case == "base"
        else c["concentrated_mass"]
    )
    # Partial orbit coverage reduces intersections per product before block occupancy.
    logical_blocks *= rates["point"] / rates["tile"]
    distinct_blocks = occupancy(logical_blocks, block_pool, c["concentrated_fraction"], block_mass)
    active_tiles = occupancy(
        memberships, c["tiles"], c["concentrated_fraction"], c["concentrated_mass"]
    )
    tile_dates = active_tiles * years * rates["tile"]
    source_epochs = years * rates["tile"] * c["revisions"]
    months = years * 12
    # Three native-grid partitions per occupied tile-month. Larger partitions split.
    objects = object_count(history_bytes, months, active_tiles, s)
    daily_puts = max(
        3 * active_tiles * rates["tile"] * c["revisions"] / 365.25,
        daily_bytes / s["target_object_bytes"],
    )
    # Backfill batches write final objects plus retry/compaction allowance.
    initial_put_cost = (
        (objects * s["write_amplification"] + n / s["bodies_per_mask_object"])
        * p["s3_put_per_1000"]
        / 1000
    )
    monthly_put_cost = (daily_puts * 365.25 / 12 + objects / months) * p["s3_put_per_1000"] / 1000
    prep_cpu = (
        n * c["preparation_seconds_per_body"]
        + sum(pixels.values()) * c["preparation_seconds_per_grid_pixel"]
    )
    prep_workers = s["preparation_workers_per_instance"]
    assert prep_workers <= s["ec2_instance_vcpu"]
    assert (
        prep_workers * s["preparation_worker_memory_gib"] + s["instance_reserved_memory_gib"]
        <= s["ec2_instance_memory_gib"]
    )
    prep_hours = prep_cpu / 3600 / s["preparation_cpu_utilization"] / prep_workers
    prep_cost = prep_hours * (
        p["ec2_instance_hour"] + s["ec2_ebs_gib"] * p["ebs_gib_month"] / s["billing_month_hours"]
    )
    result = {
        "workload": ("sample" if sample else "all") + ("_land" if land else "_water_shore"),
        "case": case,
        "annual_rates": rates,
        "bodies": n,
        "population_basis": c["population"],
        "water_km2": water,
        "perimeter_km": perimeter,
        "additional_buffer_km2": buffer,
        "selected_pixels_per_epoch_before_overlap": pixels,
        "retained_pixel_epochs": retained_epochs,
        "active_tiles": active_tiles,
        "historical_distinct_tile_dates": tile_dates,
        "historical_source_products_including_revisions": tile_dates * c["revisions"],
        "logical_block_sets_per_epoch": logical_blocks,
        "distinct_block_sets_per_epoch": distinct_blocks,
        "source_block_concentrated_mass": block_mass,
        "historical_dynamic_TiB": history_bytes / TIB,
        "static_geometry_GiB": static_bytes / GIB,
        "daily_proration_status": (
            "Historical comparator only. Forward operations and storage "
            "accrual live in daily_updates."
        ),
        "daily_new_GiB": daily_bytes / GIB,
        "s3_monthly_at_cutoff_usd": storage_price(
            (history_bytes + static_bytes) / GIB, p["s3_tiers"]
        ),
        "s3_monthly_added_each_year_usd": storage_price(
            (history_bytes + static_bytes + daily_bytes * 365.25) / GIB, p["s3_tiers"]
        )
        - storage_price((history_bytes + static_bytes) / GIB, p["s3_tiers"]),
        "backfill_put_usd": initial_put_cost,
        "monthly_ingest_put_usd": monthly_put_cost,
        "archive_objects": math.ceil(objects),
        "average_archive_object_MiB": history_bytes / objects / 2**20,
        "historical_dynamic_bytes": history_bytes,
        "static_geometry_bytes": static_bytes,
        "history_months": months,
        "one_full_archive_scan_get_usd": objects * p["s3_get_per_1000"] / 1000,
        "same_region_transfer_usd": 0,
        "fixed_operations_monthly_allowance_usd": c["fixed_operations_monthly_allowance_usd"],
        "preparation_cpu_hours": prep_cpu / 3600,
        "preparation_single_instance_hours": prep_hours,
        "preparation_ec2_usd": prep_cost,
        "recipes": {},
    }
    if sample:
        mean = c["water_area_km2"] / c["population"]
        second = (
            sum(b["count"] * b["mean_km2"] ** 2 * (1 + b["area_cv"] ** 2) for b in bins)
            / c["population"]
        )
        result["sample_water_area_standard_deviation_km2"] = math.sqrt(
            n * (second - mean**2) * (c["population"] - n) / (c["population"] - 1)
        )
        tail = bins[-1]
        result["sample_area_SD_by_uncalibrated_large_lake_CV"] = {}
        for cv in (3, 10, 20):
            varied_second = second + (
                tail["count"]
                * tail["mean_km2"] ** 2
                * (cv**2 - tail["area_cv"] ** 2)
                / c["population"]
            )
            result["sample_area_SD_by_uncalibrated_large_lake_CV"][str(cv)] = math.sqrt(
                n * (varied_second - mean**2) * (c["population"] - n) / (c["population"] - 1)
            )
    for recipe in ("A1", "B1", "B3"):
        # Native payload replaces a free-standing compressed MB-per-block assumption.
        decoded_bytes_per_block = sum(
            block_km**2 * 1e6 / int(r) ** 2 * size
            for r, size in s["value_bytes_per_grid_pixel"].items()
        )
        coefficient = calibration_rows["B1" if recipe == "A1" else recipe][
            "requested_per_decoded_byte"
        ]
        if recipe == "A1" and s["a1_byte_mode"] == "legacy_extrapolation":
            blocks = max(logical_blocks * c["a1_read_fraction"], distinct_blocks)
        elif recipe == "A1":
            blocks = distinct_blocks * observed_a1_ratio(
                logical_blocks / distinct_blocks, calibration_rows
            )
        else:
            blocks = distinct_blocks
        source_mb = (
            blocks
            * decoded_bytes_per_block
            / 1e6
            * coefficient
            * c["source_compression_multiplier"]
            * source_epochs
        )
        source_requests = max(
            source_mb / c["mean_request_MB"],
            blocks * source_epochs * s["source_files"] * c["requests_per_band_block"],
        )
        metadata_opens = active_tiles
        if recipe == "A1":
            metadata_opens += (
                memberships * rates["point"] / rates["tile"] * c["a1_metadata_cache_miss_fraction"]
            )
        source_requests += metadata_opens * source_epochs * s["source_files"] * 2
        cpu_seconds = (
            source_mb
            * calibration_rows[recipe]["cpu_seconds_per_requested_MB"]
            * c["cpu_transfer_multiplier"]
        )
        output_seconds = (history_bytes * c["output_compression"] / 1e6) / c["output_MB_per_second"]
        overlap = s["request_concurrency"][recipe]
        # Add CPU, transfer service, latency, and output work conservatively.
        latency_seconds = source_requests * c["request_latency_seconds"] / overlap
        ec2_seconds = (
            (
                cpu_seconds
                + source_mb / c["ec2_worker_MB_per_second"]
                + latency_seconds
                + output_seconds
            )
            * c["operations_multiplier"]
            * c["retry_multiplier"]
        )
        lambda_cpu_seconds = cpu_wall_seconds(
            cpu_seconds,
            s["lambda_memory_gib"],
            s["lambda_cpu_parallel_fraction"][recipe],
            s["lambda_max_cpu_threads"][recipe],
        )
        lambda_output_seconds = cpu_wall_seconds(output_seconds, s["lambda_memory_gib"], 0, 1)
        lambda_seconds = (
            (
                lambda_cpu_seconds
                + source_mb / c["lambda_worker_MB_per_second"]
                + latency_seconds
                + lambda_output_seconds
            )
            * c["operations_multiplier"]
            * c["retry_multiplier"]
        )
        invocations = math.ceil(lambda_seconds / s["lambda_useful_seconds_per_invocation"])
        lambda_useful_seconds = lambda_seconds
        lambda_seconds += invocations * s["lambda_start_checkpoint_seconds"]
        ec2_hours = ec2_seconds / 3600 / s["ec2_workers_per_instance"]
        ec2_cost = ec2_hours * p["ec2_instance_hour"]
        ebs_cost = ec2_hours * s["ec2_ebs_gib"] * p["ebs_gib_month"] / s["billing_month_hours"]
        lambda_cost = lambda_seconds * s["lambda_memory_gib"] * p["lambda_gib_second"]
        lambda_cost += invocations * p["lambda_per_million_requests"] / 1e6
        lambda_cost += (
            lambda_seconds * max(s["lambda_scratch_gib"] - 0.5, 0) * p["lambda_scratch_gib_second"]
        )
        daily_ec2_hours = ec2_hours / (years * 365.25)
        result["recipes"][recipe] = {
            "historical_requested_TB_decimal": source_mb / 1e6,
            "historical_source_requests": source_requests,
            "source_request_charge_to_project_usd": 0,
            "historical_extraction_cpu_hours": cpu_seconds / 3600,
            "ec2_uninflated_components_worker_hours": {
                "cpu": cpu_seconds / 3600,
                "transfer": source_mb / c["ec2_worker_MB_per_second"] / 3600,
                "request_latency": latency_seconds / 3600,
                "output": output_seconds / 3600,
            },
            "lambda_cpu_wall_hours": lambda_cpu_seconds / 3600,
            "historical_ec2_instance_hours": ec2_hours,
            "historical_ec2_compute_usd": ec2_cost,
            "historical_ec2_ebs_usd": ebs_cost,
            "historical_ec2_total_including_prep_put_usd": ec2_cost
            + ebs_cost
            + prep_cost
            + initial_put_cost,
            "backfill_hours_32_ec2_instances": ec2_hours / 32 + prep_hours / 32,
            "ec2_instances_for_7_day_backfill": math.ceil((ec2_hours + prep_hours) / (7 * 24)),
            "daily_ec2_instance_hours": daily_ec2_hours,
            "daily_minutes_one_ec2_instance": daily_ec2_hours * 60,
            "daily_ec2_instances_for_1_hour": max(1, math.ceil(daily_ec2_hours)),
            "monthly_ec2_compute_ebs_put_usd": (ec2_cost + ebs_cost) / months + monthly_put_cost,
            "historical_lambda_billed_hours": lambda_seconds / 3600,
            "historical_lambda_useful_seconds": lambda_useful_seconds,
            "historical_lambda_invocations": invocations,
            "historical_lambda_compute_usd": lambda_cost,
            "historical_lambda_total_including_ec2_prep_put_usd": lambda_cost
            + prep_cost
            + initial_put_cost,
            "backfill_hours_64_lambda_slots_plus_32_ec2_prep": lambda_seconds / 3600 / 64
            + prep_hours / 32,
            "daily_lambda_slots_for_1_hour": max(
                1, math.ceil(lambda_seconds / 3600 / (years * 365.25))
            ),
            "monthly_lambda_compute_put_usd": lambda_cost / months + monthly_put_cost,
        }
        row = result["recipes"][recipe]
        for platform in ("ec2", "lambda"):
            variable_key = (
                "monthly_ec2_compute_ebs_put_usd"
                if platform == "ec2"
                else "monthly_lambda_compute_put_usd"
            )
            row[f"monthly_{platform}_budget_with_storage_and_allowance_usd"] = (
                row[variable_key]
                + result["s3_monthly_at_cutoff_usd"]
                + c["fixed_operations_monthly_allowance_usd"]
            )
    return result


def storage_and_serving(settings, row):
    p = settings["storage_sensitivity"]
    history = row["historical_dynamic_bytes"]
    static_gib = row["static_geometry_GiB"]
    total_gib = history / GIB + static_gib
    objects = row["archive_objects"]
    daily = (
        row["daily_new_GiB"]
        * survey_rates()["recent_annual_tile_rate"]
        / row["annual_rates"]["tile"]
    )
    recent = min(history / GIB, 30 * daily)
    warm = min(max(history / GIB - recent, 0), 60 * daily)
    cold = max(history / GIB - recent - warm, 0)
    eligible = history / objects >= p["minimum_tiering_object_bytes"]
    monitor = objects * p["it_monitor_per_1000_month"] / 1000 if eligible else 0
    standard = row["s3_monthly_at_cutoff_usd"]
    hot_cost = storage_price(recent + static_gib, settings["prices"]["s3_tiers"])
    ia_objects = objects * (warm + cold) / (history / GIB)
    ia_gib = max(warm + cold, ia_objects * p["minimum_tiering_object_bytes"] / GIB)
    ia_storage = hot_cost + ia_gib * p["ia_storage_per_gib_month"]
    ia_retrieval_per_scan = (
        (warm + cold) * GIB / settings["transfer_billing_bytes_per_GB"] * p["ia_retrieval_per_GB"]
    )
    ia_scan_get = (
        ia_objects * p["ia_get_per_1000"]
        + (objects - ia_objects) * settings["prices"]["s3_get_per_1000"]
    ) / 1000
    it_cold = (
        hot_cost
        + warm * p["it_infrequent_per_gib_month"]
        + cold * p["it_archive_instant_per_gib_month"]
        + monitor
        if eligible
        else standard
    )
    return {
        "workload": row["workload"],
        "standard_no_reads_monthly_usd": standard,
        "ia_no_reads_monthly_usd": ia_storage,
        "ia_one_full_scan_monthly_usd": ia_storage + ia_retrieval_per_scan + ia_scan_get,
        "ia_two_full_scans_monthly_usd": ia_storage + 2 * ia_retrieval_per_scan + 2 * ia_scan_get,
        "ia_one_time_transition_usd": ia_objects * p["transition_per_1000"] / 1000,
        "ia_full_scan_break_even_per_month": (standard - ia_storage)
        / (ia_retrieval_per_scan + ia_scan_get - row["one_full_archive_scan_get_usd"]),
        "it_new_backfill_first_30_days_monthly_usd": standard + monitor,
        "it_mature_no_reads_monthly_usd": it_cold,
        "it_monthly_full_scan_monthly_usd": standard
        + monitor
        + row["one_full_archive_scan_get_usd"],
        "it_monitor_monthly_usd": monitor,
        "history_plus_geometry_GiB": total_gib,
        "object_layout": settings["object_layout"],
        "ia_get_status": p["ia_get_price_status"],
        "transfer": [
            {
                "volume": name,
                "decimal_GB": volume / settings["transfer_billing_bytes_per_GB"],
                "internet_gross_usd": volume
                / settings["transfer_billing_bytes_per_GB"]
                * settings["internet_egress_per_GB"],
                "internet_if_100_GB_allowance_unused_usd": max(
                    volume / settings["transfer_billing_bytes_per_GB"] - 100, 0
                )
                * settings["internet_egress_per_GB"],
                "oregon_to_virginia_usd": volume
                / settings["transfer_billing_bytes_per_GB"]
                * settings["oregon_to_virginia_per_GB"],
            }
            for name, volume in (
                ("one full history scan", history),
                ("30 days of new output", daily * GIB * 30),
            )
        ],
    }


def sensitivities(settings, calibrated, estimates):
    base = [r for r in estimates if r["case"] == "base"]
    national = base[0]
    result = {"storage_and_serving": [storage_and_serving(settings, row) for row in base]}
    result["latency_concurrency"] = []
    for latency in (0.003, 0.01, 0.03):
        for b1, b3 in ((1, 1), (1, 2), (2, 2), (4, 4)):
            varied = copy.deepcopy(settings)
            varied["cases"]["base"]["request_latency_seconds"] = latency
            varied["request_concurrency"].update(B1=b1, B3=b3)
            row = estimate(varied, "base", False, True, calibrated)
            result["latency_concurrency"].append(
                {
                    "latency_ms": latency * 1000,
                    "B1_concurrency": b1,
                    "B3_concurrency": b3,
                    **{
                        code: row["recipes"][code]["historical_ec2_total_including_prep_put_usd"]
                        for code in ("B1", "B3")
                    },
                }
            )
    result["preparation_packing"] = []
    for workers in (1, 2, 4):
        varied = copy.deepcopy(settings)
        varied["preparation_workers_per_instance"] = workers
        varied["preparation_worker_memory_gib"] = min(3, 6 / workers)
        row = estimate(varied, "base", False, True, calibrated)
        result["preparation_packing"].append(
            {
                "workers": workers,
                "worker_memory_gib": varied["preparation_worker_memory_gib"],
                "preparation_instance_hours": row["preparation_single_instance_hours"],
                "preparation_usd": row["preparation_ec2_usd"],
                "B1_backfill_usd": row["recipes"]["B1"][
                    "historical_ec2_total_including_prep_put_usd"
                ],
            }
        )
    result["lambda_memory"] = []
    for memory in (1, 2, 3, 6):
        varied = copy.deepcopy(settings)
        varied["lambda_memory_gib"] = memory
        row = estimate(varied, "base", False, True, calibrated)
        for code, recipe in row["recipes"].items():
            result["lambda_memory"].append(
                {
                    "memory_gib": memory,
                    "recipe": code,
                    "allocated_vcpu": min(6, memory * 1024 / 1769),
                    "billed_hours": recipe["historical_lambda_billed_hours"],
                    "backfill_usd": recipe["historical_lambda_total_including_ec2_prep_put_usd"],
                }
            )
    result["purchase_options"] = []
    for code, recipe in national["recipes"].items():
        for name, discount, extra_work in (
            ("On-Demand", 0, 1),
            ("Spot 60% discount", 0.60, 1.1),
            ("Spot 70% discount", 0.70, 1.1),
            ("Existing Savings Plan 30% discount", 0.30, 1),
        ):
            total = (
                recipe["historical_ec2_compute_usd"] * (1 - discount) * extra_work
                + recipe["historical_ec2_ebs_usd"] * extra_work
                + national["preparation_ec2_usd"]
                + national["backfill_put_usd"]
            )
            result["purchase_options"].append(
                {
                    "recipe": code,
                    "option": name,
                    "backfill_usd": total,
                    "extraction_elapsed_multiplier": extra_work,
                }
            )
    result["occupancy"] = []
    for coverage in (0.2, 0.45, 0.7, 0.95):
        varied = copy.deepcopy(settings)
        varied["cases"]["base"]["accessible_block_fraction"] = coverage
        row = estimate(varied, "base", False, True, calibrated)
        result["occupancy"].append(
            {
                "available_block_fraction": coverage,
                "B1_source_TB": row["recipes"]["B1"]["historical_requested_TB_decimal"],
                "B1_backfill_usd": row["recipes"]["B1"][
                    "historical_ec2_total_including_prep_put_usd"
                ],
            }
        )
    result["a1_extrapolation"] = []
    result["object_layouts"] = []
    for sample in (False, True):
        for land in (True, False):
            varied = copy.deepcopy(settings)
            varied["a1_byte_mode"] = "legacy_extrapolation"
            legacy = estimate(varied, "base", sample, land, calibrated)
            base_row = next(e for e in base if e["workload"] == legacy["workload"])
            result["a1_extrapolation"].append(
                {
                    "workload": legacy["workload"],
                    "observed_ratio_envelope_usd": base_row["recipes"]["A1"][
                        "historical_ec2_total_including_prep_put_usd"
                    ],
                    "extrapolated_repeat_reads_usd": legacy["recipes"]["A1"][
                        "historical_ec2_total_including_prep_put_usd"
                    ],
                    "extrapolated_A1_B1_source_ratio": legacy["recipes"]["A1"][
                        "historical_requested_TB_decimal"
                    ]
                    / legacy["recipes"]["B1"]["historical_requested_TB_decimal"],
                }
            )
            varied["object_layout"] = "tile_month"
            tiled = estimate(varied, "base", sample, land, calibrated)
            result["object_layouts"].append(
                {
                    "workload": tiled["workload"],
                    "packed_objects": base_row["archive_objects"],
                    "tile_month_objects": tiled["archive_objects"],
                    "packed_average_MiB": base_row["average_archive_object_MiB"],
                    "tile_month_average_MiB": tiled["average_archive_object_MiB"],
                    "packed_full_scan_get_usd": base_row["one_full_archive_scan_get_usd"],
                    "tile_month_full_scan_get_usd": tiled["one_full_archive_scan_get_usd"],
                }
            )
    return result


def lambda_charge(settings, seconds, invocations):
    p = settings["prices"]
    return (
        seconds * settings["lambda_memory_gib"] * p["lambda_gib_second"]
        + seconds * max(settings["lambda_scratch_gib"] - 0.5, 0) * p["lambda_scratch_gib_second"]
        + invocations * p["lambda_per_million_requests"] / 1e6
    )


def daily_operations(settings, row, products_per_day):
    """Illustrative service bill, gross of shared free allowances, not an architecture."""
    d = settings["daily_updates"]
    c = d["cases"][row["case"]]
    p = d["prices"]
    month_days = 365.25 / 12
    products = products_per_day * month_days
    gb = d["service_GB_bytes"]
    log_gb = products * c["log_bytes_per_product"] / gb
    ledger_gb = (
        row["historical_source_products_including_revisions"] * c["ledger_bytes_per_product"] / gb
    )
    controller = d["batch_runs_per_day"] * month_days * c["controller_seconds_per_run"]
    # Shared controller example uses 1 GiB, independent of extraction memory.
    control_settings = dict(settings, lambda_memory_gib=1, lambda_scratch_gib=0.5)
    components = {
        "scheduler": d["batch_runs_per_day"] * month_days * p["scheduler_per_million"] / 1e6,
        "queue": products * c["queue_requests_per_product"] * p["queue_per_million"] / 1e6,
        "ledger_requests": products
        * (
            c["ledger_writes_per_product"] * p["ledger_write_per_million"]
            + c["ledger_reads_per_product"] * p["ledger_read_per_million"]
        )
        / 1e6,
        "ledger_storage_at_cutoff": ledger_gb * p["ledger_GB_month"],
        "logs_ingest": log_gb * p["log_ingest_per_GB"],
        "logs_retained": log_gb
        * c["log_retention_days"]
        / month_days
        * c["log_archive_compression"]
        * p["log_storage_per_GB_month"],
        "alarms": c["alarm_metrics"] * p["alarm_metric_month"],
        "metrics": c["custom_metrics"] * p["custom_metric_month"],
        "registry": c["registry_GB"] * p["registry_GB_month"],
        "catalog_and_reconciliation_compute": lambda_charge(
            control_settings, controller, d["batch_runs_per_day"] * month_days
        ),
        "residual_allowance": c["residual_monthly_usd"],
    }
    return {
        "monthly_components_usd": components,
        "monthly_total_usd": sum(components.values()),
        "monthly_ledger_growth_GB": products * c["ledger_bytes_per_product"] / gb,
        "qualification": (
            "Payloads fit one billing unit. Queue actions include empty polling "
            "allowance. Ledger storage retains one KiB per processed product, not one row per lake."
        ),
    }


def forecast_storage(settings, row, monthly_new_bytes, months):
    """End-month run rates and midpoint accrued costs, including fresh-backfill IT aging."""
    p = settings["prices"]
    q = settings["storage_sensitivity"]
    history = row["historical_dynamic_bytes"]
    static = row["static_geometry_bytes"]
    days = 365.25 / 12
    cohorts = [(history, 0, row["archive_objects"])]
    new_objects = (
        object_count(monthly_new_bytes, 1, row["active_tiles"], settings)
        if monthly_new_bytes
        else 0
    )

    def it_cost(time, current_bytes=0):
        frequent = static + current_bytes
        warm = cold = monitoring = 0
        for volume, born, objects in cohorts:
            age = (time - born) * days
            eligible = volume / objects >= q["minimum_tiering_object_bytes"]
            if eligible:
                monitoring += objects * q["it_monitor_per_1000_month"] / 1000
            if not eligible or age < q["it_infrequent_days"]:
                frequent += volume
            elif age < q["it_archive_instant_days"]:
                warm += volume
            else:
                cold += volume
        return (
            storage_price(frequent / GIB, p["s3_tiers"])
            + warm / GIB * q["it_infrequent_per_gib_month"]
            + cold / GIB * q["it_archive_instant_per_gib_month"]
            + monitoring
        )

    standard_sum = it_sum = extra_standard_sum = 0
    cutoff = row["s3_monthly_at_cutoff_usd"]
    for month in range(1, months + 1):
        # Uniform arrivals within a month. Daily objects stay Standard until compaction.
        standard_mid = storage_price(
            (history + static + (month - 0.5) * monthly_new_bytes) / GIB, p["s3_tiers"]
        )
        standard_sum += standard_mid
        extra_standard_sum += standard_mid - cutoff
        # Daily quadrature handles IT's 30/90-day boundaries after each compaction.
        it_sum += (
            sum(
                it_cost(month - 1 + (i + 0.5) / 32, monthly_new_bytes * (i + 0.5) / 32)
                for i in range(32)
            )
            / 32
        )
        if monthly_new_bytes:
            cohorts.append((monthly_new_bytes, month, new_objects))
    return {
        "standard_end_month_usd": storage_price(
            (history + static + months * monthly_new_bytes) / GIB, p["s3_tiers"]
        ),
        "standard_cumulative_usd": standard_sum,
        "standard_updates_only_cumulative_usd": extra_standard_sum,
        "it_no_reads_end_month_usd": it_cost(months),
        "it_no_reads_cumulative_usd": it_sum,
        "retained_GiB": (history + static + months * monthly_new_bytes) / GIB,
    }


def daily_estimate(settings, row, calibrated, rate_override=None):
    """Forward work has its own frequency, batch overheads, compaction, and retention."""
    s, p = settings, settings["prices"]
    d = s["daily_updates"]
    c, u = s["cases"][row["case"]], d["cases"][row["case"]]
    tile_rate = survey_rates()["recent_annual_tile_rate"]
    rates = rate_override or {"tile": tile_rate, "point": tile_rate * u["point_to_tile_fraction"]}
    forward = estimate(
        s,
        row["case"],
        row["workload"].startswith("sample"),
        row["workload"].endswith("_land"),
        calibrated,
        rates,
    )
    days = row["history_months"] * 365.25 / 12
    month_days = 365.25 / 12
    products = forward["historical_source_products_including_revisions"] / days
    daily_bytes = forward["historical_dynamic_bytes"] / days
    geometry_bytes = row["static_geometry_bytes"] / row["active_tiles"] * products
    geometry_cpu = geometry_bytes / 1e6 * u["geometry_cpu_seconds_per_MB"]
    geometry_gets = products * max(
        1, math.ceil(row["bodies"] / row["active_tiles"] / s["bodies_per_mask_object"])
    )
    daily_objects = max(3 * products, daily_bytes / s["target_object_bytes"])
    compact_objects = object_count(daily_bytes * month_days, 1, row["active_tiles"], s)
    daily_request_cost = (
        (daily_objects + compact_objects / month_days) * p["s3_put_per_1000"]
        + (daily_objects + geometry_gets) * p["s3_get_per_1000"]
    ) / 1000
    compact_seconds = daily_bytes / 1e6 / u["compaction_MB_per_second"]
    ec2_price = (
        p["ec2_instance_hour"] + s["ec2_ebs_gib"] * p["ebs_gib_month"] / s["billing_month_hours"]
    )
    ec2_extra_hours = (
        (geometry_cpu + geometry_bytes / 1e6 / c["ec2_worker_MB_per_second"] + compact_seconds)
        * c["retry_multiplier"]
        / s["ec2_workers_per_instance"]
        / 3600
    )
    lambda_geometry = (
        cpu_wall_seconds(geometry_cpu, s["lambda_memory_gib"], 0, 1)
        + geometry_bytes / 1e6 / c["lambda_worker_MB_per_second"]
    ) * c["retry_multiplier"]
    lambda_compact = (
        cpu_wall_seconds(compact_seconds, s["lambda_memory_gib"], 0, 1) * c["retry_multiplier"]
    )
    compact_invocations = math.ceil(
        lambda_compact * month_days / s["lambda_useful_seconds_per_invocation"]
    )
    operations = daily_operations(s, row, products)
    monthly_bytes = daily_bytes * month_days
    storage = {}
    for reserve in d["annual_reprocessing_fractions"]:
        growth = monthly_bytes + row["historical_dynamic_bytes"] * reserve / 12 / c["revisions"]
        storage[str(reserve)] = {
            str(m): forecast_storage(s, row, growth, m) for m in d["horizons_months"]
        }
    result = {
        "workload": row["workload"],
        "case": row["case"],
        "annual_rates": rates,
        "tile_products_per_day_including_revisions": products,
        "daily_new_GiB": daily_bytes / GIB,
        "daily_geometry_read_GiB": geometry_bytes / GIB,
        "daily_geometry_gets": geometry_gets,
        "daily_temporary_objects": daily_objects,
        "monthly_compacted_objects": compact_objects,
        "monthly_s3_put_get_usd": daily_request_cost * month_days,
        "operations": operations,
        "monthly_storage_run_rate_added_per_day_usd": storage_price(
            (row["historical_dynamic_bytes"] + row["static_geometry_bytes"] + daily_bytes) / GIB,
            p["s3_tiers"],
        )
        - row["s3_monthly_at_cutoff_usd"],
        "s3_monthly_added_after_one_year_usd": storage["0"]["12"]["standard_end_month_usd"]
        - row["s3_monthly_at_cutoff_usd"],
        "storage_forecasts_by_annual_reserve": storage,
        "recipes": {},
    }
    replacement_fraction = survey_rates()["replacement_2022_epochs"] / (
        row["annual_rates"]["tile"] * days / 365.25
    )
    for code, r in forward["recipes"].items():
        baseline = row["recipes"][code]
        core_ec2_hours = r["historical_ec2_instance_hours"] / days
        available_hours = 24 - d["batch_runs_per_day"] * u["ec2_start_seconds"] / 3600
        fleet = max(
            d["ec2_instances_per_run"],
            math.ceil((core_ec2_hours + ec2_extra_hours) / available_hours),
        )
        ec2_start_hours = d["batch_runs_per_day"] * fleet * u["ec2_start_seconds"] / 3600
        useful_lambda = r["historical_lambda_useful_seconds"] / days + lambda_geometry
        # Expected product tasks, split again when mean useful runtime exceeds the batch limit.
        invocations = products * max(
            1, math.ceil(useful_lambda / products / s["lambda_useful_seconds_per_invocation"])
        )
        # Compaction runs separately monthly. Its startup is amortized over the month.
        invocations += compact_invocations / month_days
        lambda_seconds = (
            useful_lambda + lambda_compact + invocations * s["lambda_start_checkpoint_seconds"]
        )
        daily_ec2 = (
            core_ec2_hours + ec2_extra_hours + ec2_start_hours
        ) * ec2_price + daily_request_cost
        daily_lambda = lambda_charge(s, lambda_seconds, invocations) + daily_request_cost
        records = {
            "extraction_ec2_usd_per_day": core_ec2_hours * ec2_price,
            "extraction_lambda_useful_seconds_per_day": r["historical_lambda_useful_seconds"]
            / days,
            "source_TB_per_day": r["historical_requested_TB_decimal"] / days,
            "ec2_extra_work_usd_per_day": ec2_extra_hours * ec2_price,
            "ec2_start_usd_per_day": ec2_start_hours * ec2_price,
            "ec2_minimum_modeled_fleet": fleet,
            "ec2_instance_hours_per_average_day": core_ec2_hours
            + ec2_extra_hours
            + ec2_start_hours,
            "lambda_billed_hours_per_average_day": lambda_seconds / 3600,
            "lambda_invocations_per_average_day": invocations,
            "lambda_compaction_invocations_per_month": compact_invocations,
            "lambda_compaction_useful_seconds_per_month": lambda_compact * month_days,
            "ec2_ingest_usd_per_day": daily_ec2,
            "lambda_ingest_usd_per_day": daily_lambda,
            "ec2_ingest_usd_per_month": daily_ec2 * month_days,
            "lambda_ingest_usd_per_month": daily_lambda * month_days,
            "horizons_by_annual_reserve": {},
        }
        # Campaigns reuse prepared geometry. They retain one new output per replacement.
        historical_products = row["historical_source_products_including_revisions"]
        historical_single_revisions = c["revisions"]
        campaign_lambda_useful = (
            baseline["historical_lambda_useful_seconds"]
            + (lambda_geometry + lambda_compact) / products * historical_products
        )
        campaign_invocations = historical_products * max(
            1,
            math.ceil(
                campaign_lambda_useful
                / historical_products
                / s["lambda_useful_seconds_per_invocation"]
            ),
        )
        campaign_costs = {
            "ec2": (
                baseline["historical_ec2_compute_usd"]
                + baseline["historical_ec2_ebs_usd"]
                + ec2_extra_hours * ec2_price / products * historical_products
                + daily_request_cost / products * historical_products
            )
            / historical_single_revisions,
            "lambda": (
                lambda_charge(
                    s,
                    campaign_lambda_useful
                    + campaign_invocations * s["lambda_start_checkpoint_seconds"],
                    campaign_invocations,
                )
                + daily_request_cost / products * historical_products
            )
            / historical_single_revisions,
        }
        records["reprocessing"] = {
            "annual_reserves": [
                {
                    "fraction_of_cutoff_history": f,
                    "ec2_annual_usd": campaign_costs["ec2"] * f,
                    "lambda_annual_usd": campaign_costs["lambda"] * f,
                    "new_retained_GiB": row["historical_dynamic_bytes"]
                    / GIB
                    * f
                    / historical_single_revisions,
                }
                for f in d["annual_reprocessing_fractions"]
            ],
            "conditional_2022_replacement": {
                "historical_acquisition_fraction": replacement_fraction,
                "ec2_usd": campaign_costs["ec2"] * replacement_fraction,
                "lambda_usd": campaign_costs["lambda"] * replacement_fraction,
                "additional_retained_GiB": row["historical_dynamic_bytes"]
                / GIB
                * replacement_fraction
                / historical_single_revisions,
            },
        }
        for reserve in d["annual_reprocessing_fractions"]:
            horizons = {}
            for m in d["horizons_months"]:
                st = storage[str(reserve)][str(m)]
                ledger_growth = (
                    operations["monthly_ledger_growth_GB"]
                    + historical_products
                    * reserve
                    / historical_single_revisions
                    / 12
                    * u["ledger_bytes_per_product"]
                    / d["service_GB_bytes"]
                )
                for platform, ingest in (("ec2", daily_ec2), ("lambda", daily_lambda)):
                    reserve_operations = daily_operations(
                        s,
                        row,
                        products
                        + historical_products * reserve / historical_single_revisions / 365.25,
                    )["monthly_total_usd"]
                    monthly_variable = (
                        ingest * month_days
                        + reserve_operations
                        + campaign_costs[platform] * reserve / 12
                    )
                    backfill_key = (
                        "historical_ec2_total_including_prep_put_usd"
                        if platform == "ec2"
                        else "historical_lambda_total_including_ec2_prep_put_usd"
                    )
                    for policy in ("standard", "it_no_reads"):
                        horizons[f"{m}_{platform}_{policy}"] = {
                            "end_month_total_usd": monthly_variable
                            + st[f"{policy}_end_month_usd"]
                            + ledger_growth * m * d["prices"]["ledger_GB_month"],
                            "cumulative_backfill_and_updates_usd": baseline[backfill_key]
                            + monthly_variable * m
                            + st[f"{policy}_cumulative_usd"]
                            + ledger_growth * m * m / 2 * d["prices"]["ledger_GB_month"],
                        }
            records["horizons_by_annual_reserve"][str(reserve)] = horizons
        result["recipes"][code] = records
    return result


def build():
    settings = json.loads(INPUT.read_text())
    calibrated = calibration()
    estimates = [
        estimate(settings, case, sample, land, calibrated)
        for sample in (False, True)
        for land in (True, False)
        for case in ("low", "base", "high")
    ]
    daily = [daily_estimate(settings, row, calibrated) for row in estimates]
    rate_sensitivity = []
    for row in estimates:
        if row["case"] != "base":
            continue
        for label, rates in (
            ("Legacy 73", {"tile": 73, "point": 73}),
            (
                "Recent tile, half point",
                {
                    "tile": survey_rates()["recent_annual_tile_rate"],
                    "point": survey_rates()["recent_annual_tile_rate"] / 2,
                },
            ),
            (
                "Recent tile, full point",
                {
                    "tile": survey_rates()["recent_annual_tile_rate"],
                    "point": survey_rates()["recent_annual_tile_rate"],
                },
            ),
        ):
            varied = estimate(
                settings,
                "base",
                row["workload"].startswith("sample"),
                row["workload"].endswith("_land"),
                calibrated,
                rates,
            )
            rate_sensitivity.append(
                {
                    "workload": row["workload"],
                    "scenario": label,
                    "rates": rates,
                    "history_GiB_if_applied_throughout": varied["historical_dynamic_TiB"] * 1024,
                    "daily_output_GiB": varied["daily_new_GiB"],
                    "B1_source_TB_per_day": varied["recipes"]["B1"][
                        "historical_requested_TB_decimal"
                    ]
                    / (varied["history_months"] * 365.25 / 12),
                    "B1_backfill_usd": varied["recipes"]["B1"][
                        "historical_ec2_total_including_prep_put_usd"
                    ],
                }
            )
    return {
        "status": "estimated, not measured",
        "as_of": settings["as_of"],
        "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "evidence_sha256": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cohort_blocks_sha256": hashlib.sha256(COHORTS.read_bytes()).hexdigest(),
        "survey_sha256": hashlib.sha256(SURVEY.read_bytes()).hexdigest(),
        "survey_rate_evidence": survey_rates(),
        "calibration": calibrated,
        "estimates": estimates,
        "daily_updates": daily,
        "rate_sensitivity": rate_sensitivity,
        "sensitivities": sensitivities(settings, calibrated, estimates),
    }


def report_tables(data):
    """Present derived values in the report without maintaining a second set of numbers."""
    names = {
        "all_land": "All, with land",
        "all_water_shore": "All, water + shore",
        "sample_land": "10,000, with land",
        "sample_water_shore": "10,000, water + shore",
    }
    base = [row for row in data["estimates"] if row["case"] == "base"]
    forward_by_workload = {r["workload"]: r for r in data["daily_updates"] if r["case"] == "base"}
    sections = []

    def table(title, headers, rows):
        sections.extend([f"### {title}", "", "| " + " | ".join(headers) + " |"])
        sections.append("| " + " | ".join("---" for _ in headers) + " |")
        sections.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
        sections.append("")

    evidence = data["survey_rate_evidence"]
    table(
        "Saved survey acquisition evidence, 23 selected tiles",
        ["Period", "Mean acquisitions per tile"],
        [[period, f"{rate:.3f}"] for period, rate in evidence["annual_tile_acquisitions"].items()]
        + [["2025-09 through 2026-08", f"{evidence['recent_annual_tile_rate']:.3f}"]],
    )
    peak_month, peak_count = max(
        evidence["recent_monthly_counts"].items(), key=lambda item: item[1]
    )
    sections.extend(
        [
            f"Largest recent monthly count: {peak_count} acquisitions across the selected tiles "
            f"in {peak_month}. This is not a measured daily peak.",
            "",
        ]
    )
    table(
        "Historical-rate revision with other central assumptions fixed",
        [
            "Workload",
            "Legacy history GiB",
            "Revised history GiB",
            "Legacy B1 backfill",
            "Revised B1 backfill",
        ],
        [
            [
                names[e["workload"]],
                f"{old['history_GiB_if_applied_throughout']:,.1f}",
                f"{e['historical_dynamic_TiB'] * 1024:,.1f}",
                f"${old['B1_backfill_usd']:,.2f}",
                f"${e['recipes']['B1']['historical_ec2_total_including_prep_put_usd']:,.2f}",
            ]
            for e in base
            for old in data["rate_sensitivity"]
            if old["workload"] == e["workload"] and old["scenario"] == "Legacy 73"
        ],
    )
    table(
        "Retained storage and central B1 recurring budget",
        ["Workload", "History GiB", "New GiB/day", "S3/month", "B1 EC2 total/month"],
        [
            [
                names[e["workload"]],
                f"{e['historical_dynamic_TiB'] * 1024:,.1f}",
                f"{forward_by_workload[e['workload']]['daily_new_GiB']:,.3f}",
                f"${e['s3_monthly_at_cutoff_usd']:,.2f}",
                "${:,.2f}".format(
                    e["s3_monthly_at_cutoff_usd"]
                    + forward_by_workload[e["workload"]]["recipes"]["B1"][
                        "ec2_ingest_usd_per_month"
                    ]
                    + forward_by_workload[e["workload"]]["operations"]["monthly_total_usd"]
                ),
            ]
            for e in base
        ],
    )
    sections.extend(
        [
            "History excludes reusable geometry. S3 includes it. "
            "Total uses cutoff retention, forward ingestion, itemized operations, "
            "and the residual allowance.",
            "",
        ]
    )
    table(
        "Geography and selected pixels per acquisition epoch",
        ["Workload", "Tiles", "Historical tile-dates", "10 m Mpx", "20 m Mpx", "60 m Mpx"],
        [
            [
                names[e["workload"]],
                f"{e['active_tiles']:,.0f}",
                f"{e['historical_distinct_tile_dates']:,.0f}",
                *[
                    f"{e['selected_pixels_per_epoch_before_overlap'][r] / 1e6:,.3f}"
                    for r in ("10", "20", "60")
                ],
            ]
            for e in base
        ],
    )
    sections.extend(
        [
            "Mpx means million grid cells, before overlap and revision multipliers. "
            "Tile-dates exclude repeated product revisions.",
            "",
        ]
    )
    table(
        "Backfill cost and elapsed time",
        ["Workload", "Recipe", "EC2 cost", "Lambda cost", "32 EC2 hours", "64 Lambda hours"],
        [
            [
                names[e["workload"]],
                code,
                f"${r['historical_ec2_total_including_prep_put_usd']:,.0f}",
                f"${r['historical_lambda_total_including_ec2_prep_put_usd']:,.0f}",
                f"{r['backfill_hours_32_ec2_instances']:,.1f}",
                f"{r['backfill_hours_64_lambda_slots_plus_32_ec2_prep']:,.1f}",
            ]
            for e in base
            for code, r in e["recipes"].items()
        ],
    )
    table(
        "Extraction work and capacity",
        ["Workload", "Recipe", "Source TB", "CPU hours", "EC2 for 7 days"],
        [
            [
                names[e["workload"]],
                code,
                f"{r['historical_requested_TB_decimal']:,.1f}",
                f"{r['historical_extraction_cpu_hours']:,.0f}",
                r["ec2_instances_for_7_day_backfill"],
            ]
            for e in base
            for code, r in e["recipes"].items()
        ],
    )
    daily = [row for row in data["daily_updates"] if row["case"] == "base"]
    table(
        "Forward daily work and storage growth",
        [
            "Workload",
            "Products/day",
            "Output GiB/day",
            "Geometry GiB/day",
            "S3 monthly charge added/day",
            "S3 monthly charge added/year",
        ],
        [
            [
                names[e["workload"]],
                f"{e['tile_products_per_day_including_revisions']:,.1f}",
                f"{e['daily_new_GiB']:,.3f}",
                f"{e['daily_geometry_read_GiB']:,.3f}",
                f"${e['monthly_storage_run_rate_added_per_day_usd']:,.4f}",
                f"${e['s3_monthly_added_after_one_year_usd']:,.2f}",
            ]
            for e in daily
        ],
    )
    table(
        "Daily ingestion, including startup, geometry, requests, and compaction",
        [
            "Workload",
            "Recipe",
            "EC2 hours/day",
            "Lambda slot-hours/day",
            "EC2/day",
            "Lambda/day",
            "EC2/month",
            "Lambda/month",
        ],
        [
            [
                names[e["workload"]],
                code,
                f"{r['ec2_instance_hours_per_average_day']:,.2f}",
                f"{r['lambda_billed_hours_per_average_day']:,.2f}",
                f"${r['ec2_ingest_usd_per_day']:,.3f}",
                f"${r['lambda_ingest_usd_per_day']:,.3f}",
                f"${r['ec2_ingest_usd_per_month']:,.2f}",
                f"${r['lambda_ingest_usd_per_month']:,.2f}",
            ]
            for e in daily
            for code, r in e["recipes"].items()
        ],
    )
    sections.extend(
        [
            "These are average-day work totals, not peak-day capacity or a latency promise. "
            "Retention and shared operations are separate.",
            "",
        ]
    )
    table(
        "Illustrative daily operations, monthly gross costs",
        ["Component", *[names[e["workload"]] for e in daily]],
        [
            [
                key.replace("_", " "),
                *[f"${e['operations']['monthly_components_usd'][key]:,.4f}" for e in daily],
            ]
            for key in daily[0]["operations"]["monthly_components_usd"]
        ],
    )
    table(
        "Storage accrual without reprocessing or reads",
        [
            "Workload",
            "Month",
            "Standard/month",
            "IT/month",
            "Cumulative extra Standard for updates",
            "Cumulative all Standard",
            "Cumulative all IT",
        ],
        [
            [
                names[e["workload"]],
                m,
                f"${r['standard_end_month_usd']:,.2f}",
                f"${r['it_no_reads_end_month_usd']:,.2f}",
                f"${r['standard_updates_only_cumulative_usd']:,.2f}",
                f"${r['standard_cumulative_usd']:,.2f}",
                f"${r['it_no_reads_cumulative_usd']:,.2f}",
            ]
            for e in daily
            for m, r in e["storage_forecasts_by_annual_reserve"]["0"].items()
        ],
    )
    for cumulative in (False, True):
        key = "cumulative_backfill_and_updates_usd" if cumulative else "end_month_total_usd"
        table(
            "Cumulative backfill, updates, operations, and retention"
            if cumulative
            else "Monthly bill at each horizon, including updates, operations, and retention",
            [
                "Workload",
                "Recipe",
                "Month",
                "EC2 Standard",
                "Lambda Standard",
                "EC2 IT",
                "Lambda IT",
            ],
            [
                [
                    names[e["workload"]],
                    code,
                    m,
                    *[
                        f"${r['horizons_by_annual_reserve']['0'][f'{m}_{platform}_{policy}'][key]:,.2f}"
                        for policy in ("standard", "it_no_reads")
                        for platform in ("ec2", "lambda")
                    ],
                ]
                for e in daily
                for code, r in e["recipes"].items()
                for m in (12, 36, 60)
            ],
        )
    sections.extend(
        [
            "IT assumes no archive reads and starts the completed backfill in frequent access. "
            "Cumulative totals exclude storage during backfill and consumer compute.",
            "",
        ]
    )
    table(
        "Annual reprocessing sensitivity, retaining each replacement",
        [
            "Workload",
            "Recipe",
            "5% EC2/year",
            "5% Lambda/year",
            "20% EC2/year",
            "20% Lambda/year",
            "20% new GiB/year",
        ],
        [
            [
                names[e["workload"]],
                code,
                *[
                    f"${r['reprocessing']['annual_reserves'][i][f'{platform}_annual_usd']:,.2f}"
                    for i in (1, 2)
                    for platform in ("ec2", "lambda")
                ],
                f"{r['reprocessing']['annual_reserves'][2]['new_retained_GiB']:,.1f}",
            ]
            for e in daily
            for code, r in e["recipes"].items()
        ],
    )
    table(
        "Conditional replacement of January through November 2022",
        ["Workload", "Recipe", "EC2 event", "Lambda event", "Additional retained GiB"],
        [
            [
                names[e["workload"]],
                code,
                f"${r['reprocessing']['conditional_2022_replacement']['ec2_usd']:,.2f}",
                f"${r['reprocessing']['conditional_2022_replacement']['lambda_usd']:,.2f}",
                f"{r['reprocessing']['conditional_2022_replacement']['additional_retained_GiB']:,.1f}",
            ]
            for e in daily
            for code, r in e["recipes"].items()
        ],
    )
    table(
        "Forward-rate sensitivity with other central assumptions fixed",
        [
            "Workload",
            "Rate scenario",
            "Tile/year",
            "Point/year",
            "Output GiB/day",
            "B1 source TB/day",
        ],
        [
            [
                names[r["workload"]],
                r["scenario"],
                f"{r['rates']['tile']:.1f}",
                f"{r['rates']['point']:.1f}",
                f"{r['daily_output_GiB']:.3f}",
                f"{r['B1_source_TB_per_day']:.3f}",
            ]
            for r in data["rate_sensitivity"]
        ],
    )
    table(
        "Daily ingestion combined stress cases",
        ["Workload", "Recipe", "Low EC2/day", "High EC2/day", "Low Lambda/day", "High Lambda/day"],
        [
            [
                names[e["workload"]],
                code,
                *[
                    "${:,.3f}".format(
                        next(
                            x
                            for x in data["daily_updates"]
                            if x["workload"] == e["workload"] and x["case"] == case
                        )["recipes"][code][f"{platform}_ingest_usd_per_day"]
                    )
                    for platform in ("ec2", "lambda")
                    for case in ("low", "high")
                ],
            ]
            for e in daily
            for code in e["recipes"]
        ],
    )
    table(
        "Combined storage stress cases",
        ["Workload", "Low GiB", "Base GiB", "High GiB", "Low S3/month", "High S3/month"],
        [
            [
                names[key],
                *[f"{row['historical_dynamic_TiB'] * 1024:,.1f}" for row in rows],
                f"${rows[0]['s3_monthly_at_cutoff_usd']:,.2f}",
                f"${rows[2]['s3_monthly_at_cutoff_usd']:,.2f}",
            ]
            for key in names
            for rows in [[e for e in data["estimates"] if e["workload"] == key]]
        ],
    )
    table(
        "Combined backfill stress cases",
        ["Workload", "Recipe", "Low EC2", "Base EC2", "High EC2", "Low–high Lambda"],
        [
            [
                names[key],
                code,
                *[
                    f"${row['recipes'][code]['historical_ec2_total_including_prep_put_usd']:,.0f}"
                    for row in rows
                ],
                "–".join(
                    f"${row['recipes'][code]['historical_lambda_total_including_ec2_prep_put_usd']:,.0f}"
                    for row in (rows[0], rows[2])
                ),
            ]
            for key in names
            for rows in [[e for e in data["estimates"] if e["workload"] == key]]
            for code in ("A1", "B1", "B3")
        ],
    )
    reviewed = data["sensitivities"]
    table(
        "Measured-cohort byte back-tests",
        ["Held-out cohort", "Recipe", "Observed MB", "Predicted MB", "Error"],
        [
            [
                r["held_out"],
                r["recipe"],
                f"{r['observed_requested_bytes'] / 1e6:,.1f}",
                f"{r['predicted_requested_bytes'] / 1e6:,.1f}",
                f"{100 * (r['predicted_over_observed'] - 1):+.1f}%",
            ]
            for r in data["calibration"]["byte_calibration"]["cross_cohort_holdouts"]
            if r["recipe"] in ("B-raster", "B-lazy")
        ],
    )
    sections.extend(
        [
            "Predictions use the other cohort's requested/decoded ratio "
            "and the held-out cohort's actual blocks. "
            "They do not validate national block occupancy.",
            "",
        ]
    )
    table(
        "National buffered latency and effective-concurrency sensitivity",
        ["Latency ms", "B1 concurrency", "B3 concurrency", "B1 EC2 backfill", "B3 EC2 backfill"],
        [
            [
                r["latency_ms"],
                r["B1_concurrency"],
                r["B3_concurrency"],
                f"${r['B1']:,.0f}",
                f"${r['B3']:,.0f}",
            ]
            for r in reviewed["latency_concurrency"]
        ],
    )
    table(
        "National buffered source-block coverage sensitivity",
        ["Available block fraction", "B1 source TB", "B1 EC2 backfill"],
        [
            [
                f"{r['available_block_fraction']:.0%}",
                f"{r['B1_source_TB']:,.1f}",
                f"${r['B1_backfill_usd']:,.0f}",
            ]
            for r in reviewed["occupancy"]
        ],
    )
    table(
        "A1 measured-ratio scenario versus repeat-read extrapolation",
        ["Workload", "Central EC2", "Extrapolated EC2", "Extrapolated A1/B1 source bytes"],
        [
            [
                names[r["workload"]],
                f"${r['observed_ratio_envelope_usd']:,.0f}",
                f"${r['extrapolated_repeat_reads_usd']:,.0f}",
                f"{r['extrapolated_A1_B1_source_ratio']:.1f}×",
            ]
            for r in reviewed["a1_extrapolation"]
        ],
    )
    table(
        "National buffered preparation packing",
        ["Workers/instance", "GiB/worker", "Preparation instance-hours", "Preparation charge"],
        [
            [
                r["workers"],
                r["worker_memory_gib"],
                f"{r['preparation_instance_hours']:,.1f}",
                f"${r['preparation_usd']:,.2f}",
            ]
            for r in reviewed["preparation_packing"]
        ],
    )
    table(
        "Storage-class monthly sensitivities",
        [
            "Workload",
            "Standard",
            "IA, no reads",
            "IA, one scan",
            "IT, mature cold",
            "IT, monthly scan",
        ],
        [
            [
                names[r["workload"]],
                *[
                    f"${r[k]:,.2f}"
                    for k in (
                        "standard_no_reads_monthly_usd",
                        "ia_no_reads_monthly_usd",
                        "ia_one_full_scan_monthly_usd",
                        "it_mature_no_reads_monthly_usd",
                        "it_monthly_full_scan_monthly_usd",
                    )
                ],
            ]
            for r in reviewed["storage_and_serving"]
        ],
    )
    sections.extend(
        [
            "Storage-class rows exclude compute and operations overhead. "
            "Cold cases require objects to age after ingestion without historical reads. "
            "IA retrieval and an unverified request-price allowance are included.",
            "",
        ]
    )
    table(
        "National buffered purchase-option sensitivity",
        ["Recipe", "Purchase assumption", "EC2 backfill"],
        [
            [r["recipe"], r["option"], f"${r['backfill_usd']:,.0f}"]
            for r in reviewed["purchase_options"]
        ],
    )
    table(
        "National buffered Lambda memory and CPU sensitivity",
        ["Recipe", "Allocated GiB", "Allocated vCPU", "Billed worker-hours", "Backfill charge"],
        [
            [
                r["recipe"],
                r["memory_gib"],
                f"{r['allocated_vcpu']:.2f}",
                f"{r['billed_hours']:,.0f}",
                f"${r['backfill_usd']:,.0f}",
            ]
            for r in reviewed["lambda_memory"]
        ],
    )
    table(
        "Serving transfer sensitivity before account allowances",
        ["Workload", "Volume", "Decimal GB", "Internet at $0.09/GB", "Oregon to Virginia"],
        [
            [
                names[r["workload"]],
                t["volume"],
                f"{t['decimal_GB']:,.2f}",
                f"${t['internet_gross_usd']:,.2f}",
                f"${t['oregon_to_virginia_usd']:,.2f}",
            ]
            for r in reviewed["storage_and_serving"]
            for t in r["transfer"]
        ],
    )
    table(
        "Compaction across small tile partitions",
        [
            "Workload",
            "Tile-month objects",
            "Packed objects",
            "Packed mean MiB",
            "Packed scan GET cost",
        ],
        [
            [
                names[r["workload"]],
                f"{r['tile_month_objects']:,}",
                f"{r['packed_objects']:,}",
                f"{r['packed_average_MiB']:.1f}",
                f"${r['packed_full_scan_get_usd']:.5f}",
            ]
            for r in reviewed["object_layouts"]
        ],
    )
    return "\n".join(sections)


def render_report(data):
    start = "<!-- BEGIN GENERATED COST TABLES -->"
    end = "<!-- END GENERATED COST TABLES -->"
    existing = REPORT.read_text()
    before, remainder = existing.split(start)
    _, after = remainder.split(end)
    return before + start + "\n\n" + report_tables(data) + "\n" + end + after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build()
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    report = render_report(data)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            raise SystemExit("Cost estimates differ. Run tools/estimate_aws_costs.py.")
        if REPORT.read_text() != report:
            raise SystemExit("Cost report tables differ. Run tools/estimate_aws_costs.py.")
        print("Cost estimates match offline inputs, source evidence, and model.")
    else:
        OUTPUT.write_text(rendered)
        REPORT.write_text(report)
        print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
