"""Check cost dimensions, saturation, workload identity, and artifact provenance offline."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "estimate_aws_costs", ROOT / "tools/estimate_aws_costs.py"
)
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)


@pytest.fixture(scope="module")
def settings():
    return json.loads(model.INPUT.read_text())


def test_binary_storage_tiers():
    rates = [0.023, 0.022, 0.021]
    assert model.storage_price(1024, rates) == pytest.approx(23.552)
    assert model.storage_price(51_201, rates) == pytest.approx(51_200 * 0.023 + 0.022)
    assert model.storage_price(512_001, rates) == pytest.approx(
        51_200 * 0.023 + 460_800 * 0.022 + 0.021
    )


def test_geographic_occupancy_saturates_and_preserves_sparse_reads():
    assert model.occupancy(0, 1000, 0.25, 0.9) == 0
    assert model.occupancy(1e9, 1000, 0.25, 0.9) == pytest.approx(1000)
    assert 0.99 < model.occupancy(1, 1000, 0.25, 0.9) < 1
    assert model.occupancy(1000, 1000, 0.25, 0.9) < 1000


def test_population_area_closes_independently(settings):
    for count in (3_000_000, 5_000_000, 8_000_000):
        for area in (100_000, 130_000, 170_000):
            bins = model.population(settings, count, area)
            assert sum(b["count"] for b in bins) == count
            assert sum(b["count"] * b["mean_km2"] for b in bins) == pytest.approx(area)


def test_samples_use_count_uniform_expectation_and_independent_stress_cases(settings):
    calibrated = model.calibration()
    sample = model.estimate(settings, "base", True, True, calibrated)
    national = model.estimate(settings, "base", False, True, calibrated)
    fraction = 10_000 / 5_000_000
    assert sample["water_km2"] == 260
    assert sample["historical_dynamic_TiB"] == pytest.approx(
        national["historical_dynamic_TiB"] * fraction
    )
    assert sample["active_tiles"] > national["active_tiles"] * 0.5
    low = model.estimate(settings, "low", True, True, calibrated)
    high = model.estimate(settings, "high", True, True, calibrated)
    assert low["water_km2"] == 125
    assert high["water_km2"] == pytest.approx(170_000 / 3_000_000 * 10_000)


def test_buffer_changes_storage_without_requiring_proportional_source_savings(settings):
    calibrated = model.calibration()
    land = model.estimate(settings, "base", False, True, calibrated)
    water = model.estimate(settings, "base", False, False, calibrated)
    assert land["historical_dynamic_TiB"] > 2 * water["historical_dynamic_TiB"]
    source_ratio = (
        land["recipes"]["B1"]["historical_requested_TB_decimal"]
        / water["recipes"]["B1"]["historical_requested_TB_decimal"]
    )
    storage_ratio = land["historical_dynamic_TiB"] / water["historical_dynamic_TiB"]
    assert 1 < source_ratio < storage_ratio


def test_worker_packing_changes_ec2_billing_without_changing_cpu_work(settings):
    calibrated = model.calibration()
    baseline = model.estimate(settings, "base", True, False, calibrated)["recipes"]["B1"]
    changed = copy.deepcopy(settings)
    changed["ec2_workers_per_instance"] = 1
    single = model.estimate(changed, "base", True, False, calibrated)["recipes"]["B1"]
    assert single["historical_ec2_compute_usd"] == pytest.approx(
        2 * baseline["historical_ec2_compute_usd"]
    )
    assert single["historical_extraction_cpu_hours"] == baseline["historical_extraction_cpu_hours"]
    assert single["historical_lambda_compute_usd"] == baseline["historical_lambda_compute_usd"]


def test_output_and_source_accounting_and_reproducibility(settings):
    generated = model.build()
    assert generated == json.loads(model.OUTPUT.read_text())
    assert model.render_report(generated) == model.REPORT.read_text()
    for row in generated["estimates"]:
        assert row["same_region_transfer_usd"] == 0
        for recipe in row["recipes"].values():
            assert recipe["source_request_charge_to_project_usd"] == 0
            expected = (
                recipe["monthly_ec2_compute_ebs_put_usd"]
                + row["s3_monthly_at_cutoff_usd"]
                + row["fixed_operations_monthly_allowance_usd"]
            )
            assert recipe["monthly_ec2_budget_with_storage_and_allowance_usd"] == expected


def test_a1_metadata_misses_affect_only_a1(settings):
    calibrated = model.calibration()
    original = model.estimate(settings, "base", True, False, calibrated)
    changed = copy.deepcopy(settings)
    changed["cases"]["base"]["a1_metadata_cache_miss_fraction"] = 1
    cold = model.estimate(changed, "base", True, False, calibrated)
    assert (
        cold["recipes"]["A1"]["historical_source_requests"]
        > (original["recipes"]["A1"]["historical_source_requests"])
    )
    assert cold["recipes"]["B1"] == original["recipes"]["B1"]


def test_lambda_duration_changes_with_allocated_cpu_and_thread_limits(settings):
    calibrated = model.calibration()
    assert model.cpu_wall_seconds(100, 1769 / 1024, 0, 1) == pytest.approx(100)
    assert model.cpu_wall_seconds(100, 1769 / 2048, 0, 1) == pytest.approx(200)
    assert model.cpu_wall_seconds(100, 2 * 1769 / 1024, 0.5, 2) == pytest.approx(75)
    # Single-threaded work cannot consume the added cores above one allocated vCPU.
    assert model.cpu_wall_seconds(100, 3, 0, 1) == model.cpu_wall_seconds(100, 6, 0, 1)
    changed = copy.deepcopy(settings)
    changed["lambda_memory_gib"] = 1
    small = model.estimate(changed, "base", True, False, calibrated)["recipes"]["B3"]
    changed["lambda_memory_gib"] = 2
    large = model.estimate(changed, "base", True, False, calibrated)["recipes"]["B3"]
    assert large["historical_lambda_billed_hours"] < small["historical_lambda_billed_hours"]
    assert large["historical_extraction_cpu_hours"] == small["historical_extraction_cpu_hours"]


def test_cohort_bytes_are_held_out_not_fitted_to_the_target():
    blocks = json.loads(model.COHORTS.read_text())
    observations = json.loads(model.EVIDENCE.read_text())["cohorts"]
    for name, cohort in blocks["cohorts"].items():
        assert (
            sum(b["unique_blocks"] for b in cohort["by_band"].values())
            == (cohort["total"]["unique_blocks"])
        )
        for recipe in ("B-raster", "B-lazy"):
            evidence = next(
                r for r in observations[name]["comparisons"] if r["configuration"] == recipe
            )
            assert (
                cohort["observations"][recipe]["requested_bytes"]
                == (evidence["io"]["bytes_requested"])
            )
            other = blocks["cohorts"]["dispersed" if name == "florida" else "florida"]
            coefficient = (
                other["observations"][recipe]["requested_bytes"]
                / (other["total"]["unique_decoded_bytes"])
            )
            predicted = coefficient * cohort["total"]["unique_decoded_bytes"]
            actual = evidence["io"]["bytes_requested"]
            # Regression for these two existing conditional holdouts, not an AWS acceptance band.
            assert abs(predicted / actual - 1) < 0.06


def test_original_model_dense_bias_is_preserved_and_spatial_fit_is_labeled():
    blocks = json.loads(model.COHORTS.read_text())
    florida = blocks["cohorts"]["florida"]
    assert florida["unique_decoded_fraction_of_full"] == pytest.approx(0.2055022139)
    original = florida["old_model_conditional_backtest"]["predictions"]["B-raster"]
    assert original["predicted_over_observed"] == pytest.approx(1.5088172429)
    fitted = model.calibration()["byte_calibration"]["spatial_fit"]
    checks = {r["cohort"]: r for r in fitted["checks"]}
    assert checks["florida"]["role"] == "fit"
    assert checks["florida"]["predicted_unique_red_blocks"] == pytest.approx(99)
    assert checks["dispersed"]["role"] == "sparse_holdout"
    assert checks["dispersed"]["predicted_unique_red_blocks"] == pytest.approx(158.0376671)


def test_a1_central_ratio_is_an_envelope_not_unbounded_extrapolation(settings):
    calibrated = model.calibration()
    anchors = calibrated["byte_calibration"]["cohorts"]
    expected_max = max(r["a1_b1_byte_ratio"] for r in anchors)
    assert model.observed_a1_ratio(10000, calibrated) == pytest.approx(expected_max)
    row = model.estimate(settings, "base", False, True, calibrated)
    assert row["recipes"]["A1"]["historical_requested_TB_decimal"] / row["recipes"]["B1"][
        "historical_requested_TB_decimal"
    ] == pytest.approx(expected_max)


def test_preparation_packing_changes_instance_hours_and_enforces_memory(settings):
    calibrated = model.calibration()
    baseline = model.estimate(settings, "base", False, True, calibrated)
    single_settings = copy.deepcopy(settings)
    single_settings["preparation_workers_per_instance"] = 1
    single = model.estimate(single_settings, "base", False, True, calibrated)
    assert single["preparation_single_instance_hours"] == pytest.approx(
        2 * baseline["preparation_single_instance_hours"]
    )
    assert single["preparation_cpu_hours"] == baseline["preparation_cpu_hours"]
    single_settings["preparation_workers_per_instance"] = 4
    with pytest.raises(AssertionError):
        model.estimate(single_settings, "base", False, True, calibrated)


def test_storage_classes_include_retrieval_access_clock_and_transfer(settings):
    row = model.estimate(settings, "base", False, True, model.calibration())
    options = model.storage_and_serving(settings, row)
    assert options["ia_no_reads_monthly_usd"] < options["standard_no_reads_monthly_usd"]
    assert options["ia_two_full_scans_monthly_usd"] > options["standard_no_reads_monthly_usd"]
    assert options["it_mature_no_reads_monthly_usd"] < options["ia_no_reads_monthly_usd"]
    assert options["it_new_backfill_first_30_days_monthly_usd"] >= row["s3_monthly_at_cutoff_usd"]
    assert options["it_monthly_full_scan_monthly_usd"] >= row["s3_monthly_at_cutoff_usd"]
    scan = options["transfer"][0]
    assert scan["internet_gross_usd"] == pytest.approx(row["historical_dynamic_bytes"] / 1e9 * 0.09)
    assert scan["internet_gross_usd"] - scan[
        "internet_if_100_GB_allowance_unused_usd"
    ] == pytest.approx(9)


def test_compaction_changes_object_layout_without_padding_stored_bytes(settings):
    calibrated = model.calibration()
    packed = model.estimate(settings, "base", True, True, calibrated)
    varied = copy.deepcopy(settings)
    varied["object_layout"] = "tile_month"
    tiled = model.estimate(varied, "base", True, True, calibrated)
    assert packed["historical_dynamic_bytes"] == tiled["historical_dynamic_bytes"]
    assert packed["archive_objects"] < tiled["archive_objects"] / 100
    assert 16 <= packed["average_archive_object_MiB"] <= 128


def test_sensitivity_cost_drivers_are_independent_and_discounts_do_not_discount_s3(settings):
    data = model.build()
    rows = data["sensitivities"]["latency_concurrency"]
    equal = next(
        r for r in rows if r["latency_ms"] == 10 and r["B1_concurrency"] == r["B3_concurrency"] == 1
    )
    asymmetric = next(
        r
        for r in rows
        if r["latency_ms"] == 10 and r["B1_concurrency"] == 1 and r["B3_concurrency"] == 2
    )
    assert equal["B1"] == asymmetric["B1"]
    assert equal["B3"] > asymmetric["B3"]
    base = next(r for r in data["estimates"] if r["workload"] == "all_land" and r["case"] == "base")
    recipe = base["recipes"]["B1"]
    spot = next(
        r
        for r in data["sensitivities"]["purchase_options"]
        if r["recipe"] == "B1" and r["option"] == "Spot 70% discount"
    )
    assert spot["backfill_usd"] == pytest.approx(
        recipe["historical_ec2_compute_usd"] * 0.3 * 1.1
        + recipe["historical_ec2_ebs_usd"] * 1.1
        + base["preparation_ec2_usd"]
        + base["backfill_put_usd"]
    )


def test_survey_rates_exclude_erie_and_preserve_item_count_qualification():
    evidence = model.survey_rates()
    assert len(evidence["tile_ids"]) == 23
    assert len(evidence["site_ids"]) == 15
    assert "erie-west" not in evidence["site_ids"]
    assert evidence["recent_annual_tile_rate"] == pytest.approx(4006 / 23)
    assert evidence["historical_complete_month_epochs"] == pytest.approx(19955 / 23)
    assert "raw items" in evidence["qualification"]
    assert evidence["recent_peak_month_count_over_mean"] == pytest.approx(358 / (4006 / 12))


def test_point_and_tile_rates_have_different_dense_and_sparse_effects(settings):
    calibrated = model.calibration()
    for sample in (False, True):
        full = model.estimate(
            settings, "base", sample, True, calibrated, {"tile": 174, "point": 174}
        )
        half = model.estimate(
            settings, "base", sample, True, calibrated, {"tile": 174, "point": 87}
        )
        assert (
            full["historical_source_products_including_revisions"]
            == half["historical_source_products_including_revisions"]
        )
        assert half["historical_dynamic_bytes"] == pytest.approx(
            full["historical_dynamic_bytes"] / 2
        )
        ratio = (
            half["recipes"]["B1"]["historical_requested_TB_decimal"]
            / full["recipes"]["B1"]["historical_requested_TB_decimal"]
        )
        assert 0.5 < ratio < 1
        if not sample:
            dense_ratio = ratio
        else:
            assert ratio < dense_ratio


def test_daily_core_reproduces_history_when_rates_match(settings):
    calibrated = model.calibration()
    for sample, land in ((False, True), (True, False)):
        row = model.estimate(settings, "base", sample, land, calibrated)
        daily = model.daily_estimate(settings, row, calibrated, row["annual_rates"])
        days = row["history_months"] * 365.25 / 12
        for code, recipe in row["recipes"].items():
            assert daily["recipes"][code]["extraction_ec2_usd_per_day"] * days == pytest.approx(
                recipe["historical_ec2_compute_usd"] + recipe["historical_ec2_ebs_usd"]
            )
            assert daily["recipes"][code][
                "extraction_lambda_useful_seconds_per_day"
            ] * days == pytest.approx(recipe["historical_lambda_useful_seconds"])
        assert daily["s3_monthly_added_after_one_year_usd"] == pytest.approx(
            row["s3_monthly_added_each_year_usd"]
        )


def test_storage_accrual_uses_uniform_arrivals_and_respects_tiers(settings):
    varied = copy.deepcopy(settings)
    varied["prices"]["s3_tiers"] = [1, 1, 1]
    row = {
        "historical_dynamic_bytes": 100 * model.GIB,
        "static_geometry_bytes": 2 * model.GIB,
        "archive_objects": 100,
        "active_tiles": 1,
        "s3_monthly_at_cutoff_usd": 102,
    }
    result = model.forecast_storage(varied, row, model.GIB, 12)
    assert result["standard_end_month_usd"] == 114
    # Twelve months with uniform arrivals have 72 GiB-months of additional retention.
    assert result["standard_updates_only_cumulative_usd"] == 72
    assert result["standard_cumulative_usd"] == 102 * 12 + 72
    assert result["it_no_reads_cumulative_usd"] < result["standard_cumulative_usd"]
    flat = model.forecast_storage(varied, row, 0, 12)
    assert flat["standard_end_month_usd"] == 102
    assert flat["standard_updates_only_cumulative_usd"] == 0
    assert flat["it_no_reads_end_month_usd"] == pytest.approx(2 + 100 * 0.004 + 100 / 1000 * 0.0025)


def test_daily_budget_adds_overheads_and_keeps_reprocessing_revisions_once(settings):
    calibrated = model.calibration()
    row = model.estimate(settings, "base", True, True, calibrated)
    daily = model.daily_estimate(settings, row, calibrated)
    assert daily["daily_geometry_read_GiB"] > 0
    assert daily["monthly_s3_put_get_usd"] > 0
    assert daily["operations"]["monthly_total_usd"] == sum(
        daily["operations"]["monthly_components_usd"].values()
    )
    b1 = daily["recipes"]["B1"]
    assert b1["ec2_ingest_usd_per_day"] > b1["extraction_ec2_usd_per_day"]
    reserves = b1["reprocessing"]["annual_reserves"]
    assert reserves[0]["ec2_annual_usd"] == 0
    assert reserves[2]["ec2_annual_usd"] == pytest.approx(4 * reserves[1]["ec2_annual_usd"])
    assert reserves[2]["new_retained_GiB"] == pytest.approx(
        row["historical_dynamic_TiB"] * 1024 * 0.2 / settings["cases"]["base"]["revisions"]
    )
    forecasts = daily["storage_forecasts_by_annual_reserve"]
    assert forecasts["0.2"]["12"]["retained_GiB"] - forecasts["0"]["12"][
        "retained_GiB"
    ] == pytest.approx(reserves[2]["new_retained_GiB"])
    assert (
        b1["horizons_by_annual_reserve"]["0.2"]["60_ec2_standard"][
            "cumulative_backfill_and_updates_usd"
        ]
        > b1["horizons_by_annual_reserve"]["0"]["60_ec2_standard"][
            "cumulative_backfill_and_updates_usd"
        ]
    )


def test_daily_fleet_can_clear_average_work_and_compaction_is_partitioned(settings):
    calibrated = model.calibration()
    row = model.estimate(settings, "high", False, True, calibrated)
    daily = model.daily_estimate(settings, row, calibrated)
    for recipe in daily["recipes"].values():
        assert (
            recipe["ec2_instance_hours_per_average_day"] <= 24 * recipe["ec2_minimum_modeled_fleet"]
        )
        assert (
            recipe["lambda_compaction_useful_seconds_per_month"]
            / recipe["lambda_compaction_invocations_per_month"]
            <= settings["lambda_useful_seconds_per_invocation"]
        )
    assert (
        daily["recipes"]["A1"]["ec2_minimum_modeled_fleet"]
        > settings["daily_updates"]["ec2_instances_per_run"]
    )
    assert daily["recipes"]["B1"]["lambda_compaction_invocations_per_month"] > 1
