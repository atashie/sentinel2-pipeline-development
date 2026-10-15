"""Fixture tests for prototype presentation data. No network or result file needed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_options", ROOT / "tools" / "render_options.py"
)
render_options = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_options)


def test_machine_label_names_cores_and_memory():
    assert render_options.machine_label(
        {"cpu_count": 8, "machine": "arm64", "memory_total_bytes": 16e9}
    ) == ("8-core arm64 laptop, 14.9 GiB memory")


def cross_tile_fixture():
    medians = [
        {"path": path, "method": method, "requests": 100 * f, "bytes_requested": 25e6 * f}
        | {"wall_seconds": 20 * f}
        for method in ("raster-mask", "lazy-stack")
        for path, f in (("lake-first", 2), ("tile-first", 1.2))
    ]
    summary = {"complete": True, "equal": True, "medians": medians}
    summary |= {"expected_contributions_per_workload": 125, "lakes": 11, "tiles": 8}
    summary |= {"acquisitions": 2, "memberships": 25}
    return {"measured_at": "2026-09-16T01:02:03+00:00", "summary": summary}


def test_cross_tile_headline_states_tile_first_savings_against_lake_first():
    markers = render_options.cross_tile_markers(cross_tile_fixture())
    assert markers["CROSS_SAVED_REQUESTS"] == markers["CROSS_SAVED_BYTES"] == "40"
    assert (markers["CROSS_DATE"], markers["CROSS_EXPECTED"]) == ("2026-09-16", "125")
    assert markers["CROSS_MEMBERSHIPS"] == "25"


@pytest.mark.parametrize("complete,equal", [(False, True), (True, False)])
def test_cross_tile_headline_refuses_incomplete_or_unequal_results(complete, equal):
    with pytest.raises(ValueError, match="requires complete, equal"):
        render_options.cross_tile_markers({"summary": {"complete": complete, "equal": equal}})


def workload_run(configuration, seconds, cpu, requests, megabytes, peak_gib, day):
    return {
        "configuration": configuration,
        "started_at": f"{day}T12:00:00+00:00",
        "status": "complete",
        "matches_all_complete_outputs": True,
        "extraction_seconds": seconds,
        "cpu": {"user": cpu - 1, "system": 1.0},
        "io": {"requests": requests, "bytes_requested": megabytes * 1e6},
        "supervision": {"peak_aggregate_rss_bytes": peak_gib * 1024**3},
    }


def workload_fixtures():
    """ACOLITE and Level-2A runs of B1 and B3 that satisfy every takeaway claim."""

    def runs(scale, day, byte_factor, request_factor):
        return [
            workload_run(
                "B-raster",
                100 * scale,
                8 * scale,
                round(500 * request_factor * scale),
                300 * byte_factor * scale,
                0.2,
                day,
            ),
            workload_run(
                "B-lazy",
                80 * scale,
                20 * scale,
                round(540 * request_factor * scale),
                280 * byte_factor * scale,
                0.3,
                day,
            ),
        ]

    product = {
        "measured_at": "2026-10-14T12:00:00+00:00",
        "workloads": {
            "dispersed": {
                "lakes": 93,
                "products": 112,
                "tiles": 111,
                "dropped_lakes": ["dropped"] * 7,
                "same_acquisitions": {"same_item_as_reference": 98},
                "comparisons": runs(4, "2026-10-14", 0.4, 1.1),
            },
            "florida": {
                "lakes": 1000,
                "products": 4,
                "tiles": 4,
                "dropped_lakes": [],
                "same_acquisitions": {"same_item_as_reference": 4},
                "comparisons": runs(1, "2026-10-14", 0.4, 1.1),
            },
        },
    }
    reference = {
        "cohorts": {
            "dispersed": {
                "preflight": {"lakes": 100, "products": 121},
                "comparisons": runs(4, "2026-09-21", 1.0, 1.0),
            },
            "florida": {
                "preflight": {"lakes": 1000, "products": 4},
                "comparisons": runs(1, "2026-09-21", 1.0, 1.0),
            },
        }
    }
    return product, reference


def clean_audit():
    """A sleep audit row, free of sleep, for each Level-2A run the page shows."""
    return {
        "rows": [
            {"cohort": cohort, "configuration": key, "sleep_intervals_overlapping": 0}
            for cohort in ("dispersed", "florida")
            for key in ("B-raster", "B-lazy")
        ]
    }


def test_main_comparison_groups_each_reader_on_both_options_by_cohort():
    product, reference = workload_fixtures()
    markers = render_options.option_workload_markers(product, reference, clean_audit())
    rendered = markers["OPTION_WORKLOAD_ROWS"]
    assert rendered.count('class="result-group"') == 2 and rendered.count("<tr>") == 8
    assert rendered.index("Dispersed lakes") < rendered.index("Lakes concentrated in Florida")
    assert (
        "<td>ACOLITE only</td><td>93 · 112</td><td>400.0 s</td><td>32.0 s</td><td>2,200</td>"
        "<td>480.0 MB</td><td>0.20 GiB</td><td>2026-10-14</td>"
    ) in rendered
    assert "<td>Sen2Cor only</td><td>100 · 121</td>" in rendered
    assert 'href="#reader-3">B3' in rendered
    assert markers["T6_BYTE_SHARE"] == "40" and markers["T6_MORE_REQUESTS"] == "10"
    assert (markers["T6_DISP_B1_CPU"], markers["T6_DISP_B3_CPU"]) == ("32.0", "80.0")
    assert markers["T6_B3_FASTER_DISP"] == markers["T6_B3_FASTER_FL"] == "20"
    assert (markers["T6_RAM_LOW"], markers["T6_RAM_HIGH"]) == ("0.20", "0.30")
    assert (markers["T6_DISP_LAKES"], markers["T6_DISP_DROPPED"]) == ("93", "7")
    assert (markers["T6_DISP_SAME"], markers["T6_FL_SAME"]) == ("98", "4")


@pytest.mark.parametrize(
    "change,message",
    [
        ({"status": "incomplete"}, "complete, agreeing run"),
        ({"matches_all_complete_outputs": False}, "complete, agreeing run"),
    ],
)
def test_main_comparison_refuses_incomplete_or_unequal_runs(change, message):
    product, reference = workload_fixtures()
    reference["cohorts"]["florida"]["comparisons"][1].update(change)
    with pytest.raises(ValueError, match=message):
        render_options.option_workloads(product, reference, clean_audit())


def test_main_comparison_refuses_duplicate_or_sleeping_runs():
    product, reference = workload_fixtures()
    runs = product["workloads"]["dispersed"]["comparisons"]
    runs.append(dict(runs[0]))
    with pytest.raises(ValueError, match="Expected one B-raster run"):
        render_options.option_workloads(product, reference, clean_audit())
    product, reference = workload_fixtures()
    audit = clean_audit()
    audit["rows"][1]["sleep_intervals_overlapping"] = 2
    with pytest.raises(ValueError, match="dispersed B-lazy overlapped laptop sleep"):
        render_options.option_workloads(product, reference, audit)


def test_main_comparison_refuses_level_2a_runs_without_a_sleep_audit():
    product, reference = workload_fixtures()
    with pytest.raises(ValueError, match="need the sleep audit"):
        render_options.option_workloads(product, reference, None)
    audit = clean_audit()
    del audit["rows"][3]
    with pytest.raises(ValueError, match="florida B-lazy needs one sleep audit row"):
        render_options.option_workloads(product, reference, audit)


def test_takeaway_numbers_refuse_runs_that_contradict_them():
    product, reference = workload_fixtures()
    product["workloads"]["florida"]["comparisons"][1]["cpu"]["user"] = 1.0
    with pytest.raises(ValueError, match="no longer split"):
        render_options.option_workload_markers(product, reference, clean_audit())
    product, reference = workload_fixtures()
    reference["cohorts"]["florida"]["comparisons"][0]["extraction_seconds"] = 9_999
    with pytest.raises(ValueError, match="no longer split|Florida no longer"):
        render_options.option_workload_markers(product, reference, clean_audit())
    product, reference = workload_fixtures()
    for requests, run in enumerate(product["workloads"]["florida"]["comparisons"], start=1):
        run["io"]["requests"] = requests
    with pytest.raises(ValueError, match="more requests in Florida"):
        render_options.option_workload_markers(product, reference, clean_audit())
    product, reference = workload_fixtures()
    for run in product["workloads"]["florida"]["comparisons"]:
        run["io"]["bytes_requested"] *= 3
    with pytest.raises(ValueError, match="fewer bytes in Florida"):
        render_options.option_workload_markers(product, reference, clean_audit())


def test_percent_range_and_workload_dates():
    assert render_options.percent_range([0.396, 0.404]) == "40"
    assert render_options.percent_range([0.082, 0.093]) == "8 to 9"
    result = {"cohorts": {"a": {"comparisons": [{"started_at": "2026-09-21T01:00:00+00:00"}]}}}
    assert render_options.workload_dates(result) == "2026-09-21"
    result["cohorts"]["b"] = {"comparisons": [{"started_at": "2026-09-19T23:00:00+00:00"}]}
    assert render_options.workload_dates(result) == "2026-09-19 to 2026-09-21"


BANDS = ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12")


def pixel_fixtures():
    """Probe T4, T5, and T7 summaries holding only the fields the pixel checks state."""
    classes = (
        ("interior", 0.578, 0.35),
        ("shoreline", 0.202, 0.772),
        ("near_land", 0.0652, 0.9152),
    )
    cloud = {"scl_cloud_unflagged_of_cloud": 0.073, "scl_shadow_unflagged_of_shadow": 0.7355}
    validity = {
        "summary": {
            "scenes_read": 59,
            "distinct_tiles": 5,
            "lakes": 26,
            "verdicts": {name: {"masked_by_processor": False} for name, _, _ in classes},
            "no_data_diagnostic": {
                "mismatches": [
                    {
                        "product": "p",
                        "water_body_id": "w",
                        "class": "near_land",
                        "band": band,
                        "no_data": 0,
                        "out_of_scene_flag": 2,
                    }
                    for band in BANDS
                    if band != "B04"
                ],
                "scenes_with_no_data": {
                    "p": {"bands": {band: 2 if band == "B04" else 0 for band in BANDS}}
                },
            },
            "shares": {
                name: {"flags": {"none": none, "bits": {"swir": swir}}, "cloud": cloud}
                for name, none, swir in classes
            },
        }
    }
    pairs = {
        "summary": {
            "verdicts": {"all": {"interior": {"agree": []}}},
            "pooled": {
                "both_clear_water": {
                    "interior": {"B01": {"share_disagree": 0.8065}, "B12": {"share_disagree": 0.25}}
                }
            },
        }
    }
    agree, differs = {"verdict": "agree"}, {"verdict": "differs"}
    overlap = {
        "summary": {
            "pairs_compared": 8,
            "pooled": {
                "acolite": {"all": {"interior": {"B01": agree}, "shoreline": {"B01": agree}}},
                "sen2cor": {"all": {"shoreline": {"B01": differs}, "near_land": {"B01": differs}}},
            },
        },
        "diagnostics": {
            "relative_offsets": {
                "pair": {
                    "acolite": {"interior": {"B01": -0.6951, "B02": 0.3, "B03": None}},
                    "sen2cor": {"interior": {"B01": 0.3611, "B02": -0.1}},
                }
            }
        },
    }
    return validity, pairs, overlap


def test_pixel_checks_state_the_probe_summaries():
    markers = render_options.pixel_check_markers(*pixel_fixtures())
    assert (markers["T4_SCENES"], markers["T4_TILES"], markers["T4_LAKES"]) == ("59", "5", "26")
    assert [markers[f"T4_NONWATER_{k}"] for k in ("INTERIOR", "SHORE", "NEAR")] == [
        "35",
        "77",
        "92",
    ]
    assert [markers[f"T4_NOFLAG_{k}"] for k in ("INTERIOR", "SHORE", "NEAR")] == ["58", "20", "7"]
    assert (markers["T4_CLOUD_UNFLAGGED"], markers["T4_SHADOW_UNFLAGGED"]) == ("7", "74")
    assert (markers["T5_LOW"], markers["T5_HIGH"]) == ("25", "81")
    assert (markers["T7_ACOLITE_MAX"], markers["T7_SEN2COR_MAX"]) == ("70", "36")
    assert markers["T7_PAIRS"] == "8"


def test_pixel_checks_refuse_summaries_that_contradict_the_page():
    validity, pairs, overlap = pixel_fixtures()
    validity["summary"]["verdicts"]["shoreline"]["masked_by_processor"] = True
    with pytest.raises(ValueError, match="processor masks"):
        render_options.pixel_check_markers(validity, pairs, overlap)
    validity, pairs, overlap = pixel_fixtures()
    pairs["summary"]["verdicts"]["all"]["interior"]["agree"] = ["B12"]
    with pytest.raises(ValueError, match="options agree"):
        render_options.pixel_check_markers(validity, pairs, overlap)
    validity, pairs, overlap = pixel_fixtures()
    overlap["summary"]["pooled"]["acolite"]["all"]["interior"]["B01"] = {"verdict": "differs"}
    with pytest.raises(ValueError, match="pooled exceptions changed"):
        render_options.pixel_check_markers(validity, pairs, overlap)
    validity, pairs, overlap = pixel_fixtures()
    overlap["diagnostics"]["relative_offsets"]["pair"]["sen2cor"]["interior"]["B02"] = 0.5
    with pytest.raises(ValueError, match="moved from B01 to B02"):
        render_options.pixel_check_markers(validity, pairs, overlap)


def test_pixel_checks_refuse_a_changed_no_data_exception():
    validity, pairs, overlap = pixel_fixtures()
    diagnostic = validity["summary"]["no_data_diagnostic"]
    diagnostic["mismatches"][0]["no_data"] = 3
    with pytest.raises(ValueError, match="no longer follow the out-of-scene flag"):
        render_options.pixel_check_markers(validity, pairs, overlap)
    validity, pairs, overlap = pixel_fixtures()
    diagnostic = validity["summary"]["no_data_diagnostic"]
    diagnostic["mismatches"][0]["water_body_id"] = "other"
    with pytest.raises(ValueError, match="no longer follow the out-of-scene flag"):
        render_options.pixel_check_markers(validity, pairs, overlap)
    validity, pairs, overlap = pixel_fixtures()
    diagnostic = validity["summary"]["no_data_diagnostic"]
    diagnostic["scenes_with_no_data"]["p"]["bands"]["B05"] = 1
    with pytest.raises(ValueError, match="no-data exception changed"):
        render_options.pixel_check_markers(validity, pairs, overlap)


def cost_fixture(option="sen2cor"):
    """Estimates for four workloads and three cases, scaled so each figure is traceable."""
    acolite = option == "acolite"
    sizes = {
        "all_land": 100.0,
        "all_water_shore": 40.0,
        "sample_land": 1.0,
        "sample_water_shore": 0.5,
    }
    codes = (("B1", 1.0), ("B3", 1.2)) if acolite else (("A1", 9.0), ("B1", 1.0), ("B3", 1.2))
    share = 0.25 if acolite else 1.0
    estimates, daily = [], []
    for workload, size in sizes.items():
        for case, stress in (("low", 0.2), ("base", 1.0), ("high", 10.0)):
            scale = size * stress * share
            recipes = {
                code: {
                    "historical_ec2_total_including_prep_put_usd": scale * 12 * factor,
                    "historical_lambda_total_including_ec2_prep_put_usd": scale * 25 * factor,
                    "historical_requested_TB_decimal": scale * 6 * factor,
                    "ec2_ingest_usd_per_month": scale * 0.2 * factor,
                    "lambda_ingest_usd_per_month": scale * 0.5 * factor,
                }
                for code, factor in codes
            }
            sample = workload.startswith("sample")
            estimates.append(
                {
                    "workload": workload,
                    "case": case,
                    "bodies": 10_000 if sample else 5_000_000,
                    "historical_dynamic_TiB": scale / 10,
                    "static_geometry_GiB": scale / 2,
                    "s3_monthly_at_cutoff_usd": scale * 8,
                    "recipes": recipes,
                }
            )
            operations = (12.77 if sample else 12.88) if acolite else (13.21 if sample else 13.41)
            daily.append(
                {
                    "workload": workload,
                    "case": case,
                    "s3_monthly_added_after_one_year_usd": scale * 1.5,
                    "operations": {
                        "monthly_total_usd": operations,
                        "monthly_components_usd": {"residual_allowance": 10.0},
                    },
                    "recipes": recipes,
                }
            )
    rates = {"recent_annual_tile_rate": 98.21 if acolite else 174.17}
    if acolite:
        rates["historical_share_of_earth_search_any"] = 0.5515
    return {
        "option": f"{option}_only",
        "status": "estimated, not measured",
        "as_of": "2026-09-22",
        "calibration": {
            "byte_calibration": {"cohorts": [{"a1_b1_byte_ratio": 9.0}, {"a1_b1_byte_ratio": 1.0}]}
        },
        "survey_rate_evidence": rates,
        "estimates": estimates,
        "daily_updates": daily,
    }


def cost_options():
    return {"acolite": cost_fixture("acolite"), "sen2cor": cost_fixture("sen2cor")}


COST_INPUTS = {
    "start": "2021-01-01",
    "end_exclusive": "2026-09-23",
    "sample_size": 10_000,
    "land_radius_km": 0.1,
    "ec2_instance_vcpu": 4,
    "ec2_instance_memory_gib": 8,
    "lambda_memory_gib": 3,
}


def test_usd_keeps_whole_dollars_for_backfill_and_cents_for_monthly_charges():
    assert render_options.usd(1262.04) == "$1,262"
    assert render_options.usd(22.115077, cents=True) == "$22.12"
    assert render_options.usd(10.0, cents=True) == "$10.00"


def test_cost_table_shows_each_reader_on_both_options_under_each_workload():
    rendered = render_options.cost_table_rows(cost_options(), "100")
    assert rendered.count('class="result-group"') == 4
    for label in (
        "All contiguous US water bodies (5,000,000) · water + shoreline + 100 m nearby land",
        "All contiguous US water bodies (5,000,000) · water + shoreline only",
        "10,000-lake sample · water + shoreline + 100 m nearby land",
        "10,000-lake sample · water + shoreline only",
    ):
        assert label in rendered, label
    assert rendered.count("<tr>") == 16
    assert 'href="#reader-1">B1' in rendered and 'href="#reader-3">B3' in rendered
    assert ">A1" not in rendered
    # All water bodies with nearby land: each option's storage, then B1 on each option.
    assert "Sen2Cor only: storage at completion 10,290 GiB of records and geometry" in rendered
    assert "ACOLITE only: storage at completion 2,572 GiB of records and geometry" in rendered
    assert "S3 Standard $800.00 per month, rising by $150.00 over the first year" in rendered
    assert (
        "<td>Sen2Cor only</td><td>600 TB</td><td>$1,200</td><td>$2,500</td><td>$20.00</td>"
        "<td>$50.00</td>"
    ) in rendered
    assert "<td>ACOLITE only</td><td>150 TB</td><td>$300</td><td>$625</td>" in rendered
    assert rendered.index("<td>ACOLITE only</td><td>150 TB") < rendered.index(
        "<td>Sen2Cor only</td><td>600 TB"
    )


def test_cost_table_refuses_options_with_different_body_counts():
    options = cost_options()
    for row in options["acolite"]["estimates"]:
        row["bodies"] = 4_000_000
    with pytest.raises(ValueError, match="different body counts"):
        render_options.cost_table_rows(options, "100")


def test_cost_markers_define_the_experiments_from_both_options_and_the_inputs():
    markers = render_options.cost_markers(cost_options(), COST_INPUTS)
    assert markers["COST_CUTOFF"] == "2026-09-22"
    assert markers["COST_BODIES"] == "5,000,000"
    assert markers["COST_SAMPLE"] == "10,000"
    assert markers["COST_LAND_M"] == "100"
    assert (markers["COST_EC2_VCPU"], markers["COST_EC2_GIB"]) == ("4", "8")
    assert markers["COST_LAMBDA_GIB"] == "3"
    assert markers["COST_OPS"] == "$12.77 to $13.41"
    assert markers["COST_RESIDUAL"] == "$10.00"
    assert markers["COST_A1_CAP"] == "9.0"
    assert (markers["COST_RATE_ACO"], markers["COST_RATE_S2C"]) == ("98.2", "174.2")
    assert markers["COST_ACQ_SHARE"] == "55"
    assert (markers["COST_TAKEAWAY_ACO_B1"], markers["COST_TAKEAWAY_S2C_B1"]) == ("$300", "$1,200")
    assert (markers["COST_TAKEAWAY_ACO_S3"], markers["COST_TAKEAWAY_S2C_S3"]) == (
        "$200.00",
        "$800.00",
    )


def test_cost_markers_refuse_national_a1_away_from_the_measured_cap():
    options = cost_options()
    options["sen2cor"]["calibration"]["byte_calibration"]["cohorts"][0]["a1_b1_byte_ratio"] = 5.0
    with pytest.raises(ValueError, match="largest measured A1/B1 ratio"):
        render_options.cost_markers(options, COST_INPUTS)


def test_cost_markers_refuse_unexpected_status_or_duplicate_rows():
    options = cost_options()
    options["acolite"]["status"] = "measured"
    with pytest.raises(ValueError, match="status"):
        render_options.cost_markers(options, COST_INPUTS)
    data = cost_fixture()
    data["estimates"].append(data["estimates"][1])
    with pytest.raises(ValueError, match="Expected one estimates row"):
        render_options.cost_rows(data, "all_land")


def cost_files(tmp_path, monkeypatch, acolite, sen2cor):
    model, inputs = tmp_path / "model.py", tmp_path / "inputs.json"
    evidence, coverage = tmp_path / "evidence.json", tmp_path / "coverage.json"
    model.write_text("model")
    inputs.write_text("{}")
    evidence.write_text("evidence")
    coverage.write_text("coverage")
    monkeypatch.setattr(
        render_options,
        "COST_DEPENDENCIES",
        {
            "acolite": {"evidence_sha256": evidence, "coverage_sha256": coverage},
            "sen2cor": {"evidence_sha256": evidence},
        },
    )
    for name, attribute, data in (
        ("aco.json", "COST_ESTIMATES_ACOLITE", acolite),
        ("s2c.json", "COST_ESTIMATES", sen2cor),
    ):
        (tmp_path / name).write_text(json.dumps(data))
        monkeypatch.setattr(render_options, attribute, tmp_path / name)
    monkeypatch.setattr(render_options, "COST_MODEL", model)
    monkeypatch.setattr(render_options, "COST_INPUTS", inputs)
    digest = render_options.hashlib.sha256
    return {
        "input_sha256": digest(b"{}").hexdigest(),
        "model_sha256": digest(b"model").hexdigest(),
        "evidence_sha256": digest(b"evidence").hexdigest(),
        "coverage_sha256": digest(b"coverage").hexdigest(),
    }


def test_cost_estimates_refuse_a_file_older_than_its_model(tmp_path, monkeypatch):
    digests = cost_files(tmp_path, monkeypatch, {}, {})
    stale = digests | {"model_sha256": "old", "option": "sen2cor_only"}
    cost_files(tmp_path, monkeypatch, digests | {"option": "acolite_only"}, stale)
    with pytest.raises(ValueError, match="predate model.py"):
        render_options.cost_estimates()


def test_cost_estimates_refuse_a_file_older_than_its_measurements(tmp_path, monkeypatch):
    digests = cost_files(tmp_path, monkeypatch, {}, {})
    sen2cor = digests | {"option": "sen2cor_only"}
    stale = digests | {"evidence_sha256": "old", "option": "acolite_only"}
    cost_files(tmp_path, monkeypatch, stale, sen2cor)
    with pytest.raises(ValueError, match="predate evidence.json"):
        render_options.cost_estimates()
    stale = digests | {"coverage_sha256": "old", "option": "acolite_only"}
    cost_files(tmp_path, monkeypatch, stale, sen2cor)
    with pytest.raises(ValueError, match="predate coverage.json"):
        render_options.cost_estimates()


def test_cost_estimates_refuse_a_file_holding_the_other_option(tmp_path, monkeypatch):
    digests = cost_files(tmp_path, monkeypatch, {}, {})
    cost_files(
        tmp_path, monkeypatch, digests | {"option": "sen2cor_only"}, digests | {"option": "x"}
    )
    with pytest.raises(ValueError, match="aco.json holds option sen2cor_only"):
        render_options.cost_estimates()
    cost_files(
        tmp_path, monkeypatch, digests | {"option": "acolite_only"}, digests | {"option": "x"}
    )
    with pytest.raises(ValueError, match="s2c.json holds option x"):
        render_options.cost_estimates()
    cost_files(
        tmp_path,
        monkeypatch,
        digests | {"option": "acolite_only"},
        digests | {"option": "sen2cor_only"},
    )
    assert set(render_options.cost_estimates()) == {"acolite", "sen2cor"}
