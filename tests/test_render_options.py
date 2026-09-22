"""Fixture tests for prototype presentation data. No network or result file needed."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "render_options", ROOT / "tools" / "render_options.py"
)
render_options = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_options)


def class_row(size, method, seconds, failed=False):
    row = {
        "size_label": size,
        "method": method,
        "lakes": 2,
        "runs": 6,
        "failed": 6 if failed else 0,
    }
    if not failed:
        row.update(
            {
                "read_seconds_median": seconds,
                "requests_median": 15,
                "bytes_requested_median": 3_735_552,
                "pixels_extracted_median": 912,
                "blocks_touched_median": 5,
                "blocks_touched_max": 5 if size == "10 m" else 20,
                "peak_rss_bytes_max": 166_395_904,
            }
        )
    return row


def fixture_result():
    methods = ["naive-clip", "raster-mask", "index-lists", "lazy-stack"]
    rows = [class_row("10 m", m, 2.1 + i) for i, m in enumerate(methods)]
    rows += [
        class_row("anchor", m, 12.0 + i, failed=(m == "lazy-stack")) for i, m in enumerate(methods)
    ]
    rows.append(class_row("30 m", "naive-clip", 1.0))
    return {
        "measured_at": "2026-09-15T01:02:03+00:00",
        "machine": {"cpu_count": 8, "machine": "arm64", "memory_total_bytes": 16e9},
        "runs": [{}] * 24,
        "summary": {
            "lakes": 3,
            "distinct_tiles": 2,
            "by_size_class_method": rows,
            "preparation_by_size_class": [
                {
                    "size_label": "10 m",
                    "lakes": 2,
                    "prepare_seconds_median": 0.05,
                    "classes": {
                        "10": {
                            "interior": 0,
                            "shoreline": 4,
                            "near_land": 354,
                            "all_classes_median": 361,
                        },
                        "20": {"interior": 0, "shoreline": 1, "near_land": 92},
                        "60": {"interior": 0, "shoreline": 1, "near_land": 9},
                    },
                },
                {
                    "size_label": "anchor",
                    "lakes": 1,
                    "prepare_seconds_median": 19.4,
                    "classes": {
                        "10": {
                            "interior": 1_479_563,
                            "shoreline": 143_274,
                            "near_land": 844_386,
                            "all_classes_median": 1_672_524,
                        }
                    },
                },
            ],
        },
    }


def test_larger_workloads_show_whole_lazy_and_hide_partial_timing():
    result = {
        "cohorts": {
            "dispersed": {
                "comparisons": [
                    {
                        "configuration": "B-lazy",
                        "status": "incomplete",
                        "extraction_seconds": 99999.9,
                        "cpu": {"user": 88888.8, "system": 0},
                    },
                    {
                        "configuration": "C-lazy",
                        "status": "complete",
                        "matches_all_complete_outputs": True,
                        "extraction_seconds": 12.3,
                        "cpu": {"user": 2.0, "system": 0.5},
                        "io": {"requests": 100, "bytes_requested": 2_000_000},
                    },
                ]
            }
        }
    }
    rendered = render_options.workload_comparison(result)
    assert "99999.9" not in rendered
    assert "12.3 s" in rendered
    assert "Worker CPU" in rendered and "2.5 s" in rendered
    assert "88,888.8" not in rendered
    assert "C3 · Read the whole image" in rendered
    assert "Source-block lazy reads" in rendered
    assert "B2 · Share image windows" in rendered
    assert "Control for this comparison" in rendered
    assert "1,000 lakes concentrated in Florida" in rendered
    assert rendered.count("<tr>") == 16
    assert "Incomplete attempts retain their partial measurements" in rendered
    assert "preserved original result" not in rendered
    assert "Not measured" in render_options.workload_comparison(None)
    audit = {
        "rows": [
            {
                "cohort": "dispersed",
                "configuration": "C-lazy",
                "sleep_intervals_overlapping": 1,
            }
        ]
    }
    interrupted = render_options.workload_comparison(result, audit)
    assert "Sleep interrupted this experiment" in interrupted
    assert "12.3 s" not in interrupted
    assert "sleep interrupted" in interrupted
    result["cohorts"]["dispersed"]["comparisons"][1]["matches_all_complete_outputs"] = False
    unverified = render_options.workload_comparison(result, audit)
    assert "Complete · agreement unverified · sleep interrupted" in unverified
    assert "2.5 s" in unverified and "2.0 MB" in unverified
    assert "12.3 s" not in unverified
    result["rerun"] = {
        "replacement_configurations": [["dispersed", "B-lazy"]],
        "retained_configurations": [["dispersed", "C-lazy"]],
    }
    replacement = render_options.workload_comparison(result, {"rows": []})
    assert "1 replacements use the same frozen inputs" in replacement
    assert "1 unaffected results retain their original dates and source versions" in replacement
    assert "retained original" in replacement
    assert "12.3 s" in replacement
    assert "lazy-reader-workloads-before-sleep-rerun.json" in replacement
    result["cohorts"]["dispersed"]["comparisons"] = result["cohorts"]["dispersed"]["comparisons"][
        1:
    ]
    completed = render_options.workload_comparison(result, {"rows": []})
    assert "Incomplete attempts retain their partial measurements" not in completed
    assert "Their RAM peaks cover only" not in completed
    assert "preserved original result" in completed
    assert "12.3 s" in completed


def test_reader_codes_keep_historical_and_workload_recipes_distinct():
    # The historical lazy-stack means reader 2. The later lazy keys mean reader 3,
    # except for the explicit control. Unique values catch labels attached to wrong rows.
    expected = [
        ("A-raster", "A1", "Direct raster reads"),
        ("A-lazy", "A3", "Source-block lazy reads"),
        ("B-raster", "B1", "Direct raster reads"),
        ("B-lazy-control", "B2", "Large-chunk lazy reads"),
        ("B-lazy", "B3", "Source-block lazy reads"),
        ("C-raster", "C1", "Direct raster reads"),
        ("C-lazy", "C3", "Source-block lazy reads"),
    ]
    comparisons = [
        {
            "configuration": key,
            "status": "complete",
            "matches_all_complete_outputs": True,
            "extraction_seconds": 101 + index,
        }
        for index, (key, _, _) in enumerate(expected)
    ]
    rendered = render_options.workload_comparison(
        {"cohorts": {"dispersed": {"comparisons": comparisons[::-1]}}}
    )
    for index, (_, code, reader) in enumerate(expected):
        row = next(part for part in rendered.split("<tr>") if f">{101 + index}.0 s<" in part)
        row = row.split("</tr>")[0]
        assert f">{code} · " in row and f"<td>{reader}</td>" in row
        assert ("Control for this comparison" in row) == (code == "B2")
    historical = render_options.cross_tile_rows(cross_tile_fixture())
    assert "A2 · Each lake separately" in historical
    assert "B2 · Share image windows" in historical
    assert "Source-block lazy reads" not in historical
    lake = render_options.lake_method_rows(fixture_result())
    for label in ("A1 · Boundary clip", "A1 · Prepared mask", "A1 · Stored positions"):
        assert lake.count(label) == 2
    assert lake.count("A2 · Prepared mask") == 2
    assert lake.count("Nearby land omitted") == 2


def test_lake_extraction_rows_report_each_class_once():
    html = render_options.lake_extraction_rows(fixture_result())
    rows = [line for line in html.splitlines() if line.startswith("<tr>")]
    assert len(rows) == 2
    assert rows[0].startswith('<tr><th scope="row">10 m class</th><td>2</td><td>361</td>')
    assert "<td>5 blocks · 3.7 MB · 15 requests</td>" in rows[0]
    assert rows[0].count("<td>2.1 s</td>") == 1 and "<td>5.1 s</td>" in rows[0]
    assert rows[0].endswith("<td>0.2 GB</td></tr>")
    assert rows[1].startswith('<tr><th scope="row">Anchor lakes</th>')
    assert rows[1].count("<td>failed</td>") == 1 and "<td>1,672,524</td>" in rows[1]
    assert "<td>5 to 20 blocks · 3.7 MB · 15 requests</td>" in rows[1]


def test_pixel_class_rows_show_interior_shoreline_near_land():
    html = render_options.pixel_class_rows(fixture_result())
    rows = [line for line in html.splitlines() if line.startswith("<tr>")]
    assert len(rows) == 2
    assert "<td>0 · 4 · 354</td><td>0 · 1 · 92</td><td>0 · 1 · 9</td><td>0.1 s</td>" in rows[0]
    assert "<td>1,479,563 · 143,274 · 844,386</td><td>not read</td><td>not read</td>" in rows[1]
    assert rows[1].endswith("<td>19 s</td></tr>")


def tile_row(tile, pattern, method, requests=None, mb=None, seconds=None, baseline=None, **counts):
    row = {"tile": tile, "region": "lanier", "pattern": pattern, "method": method, **counts}
    if seconds is not None:
        row["requests_median"] = requests
        row["bytes_requested_median"] = int(mb * 1e6)
        row["read_seconds_median"] = seconds
    if baseline is not None:
        row["baseline_stage_2"] = baseline
    return row


def test_tile_extraction_rows_keep_workloads_baselines_and_exclusions_separate():
    full = {
        "comparable": True,
        "lakes_with_baseline": ["a", "b", "c"],
        "lakes_without_baseline": [],
        "requests": 79,
        "bytes_requested": 26_700_000,
        "read_seconds": 11.4,
    }
    none = {"comparable": True, "lakes_with_baseline": [], "lakes_without_baseline": ["d"]}
    result = {
        "summary": {
            "tiles": [
                {"tile": "16TGK", "region": "grand-st-marys", "lakes": 3, "lakes_partly_inside": 0},
                {"tile": "17SKT", "region": "lanier", "lakes": 1, "lakes_partly_inside": 1},
                {"tile": "05VLG", "region": "iliamna", "lakes": 3, "lakes_partly_inside": 0},
            ],
            "by_tile_pattern_method": [
                # One of three runs was under memory pressure. The medians come from two.
                tile_row(
                    "16TGK",
                    "tile-by-tile",
                    "raster-mask",
                    27,
                    23.0,
                    4.5,
                    full,
                    runs=3,
                    timings_from_runs=2,
                    runs_with_memory_pressure=1,
                ),
                tile_row("16TGK", "whole-tile", "raster-mask", 54, 394.2, 41.6, runs=3),
                tile_row("16TGK", "tile-by-tile", "lazy-stack", 71, 92.9, 14.2),
                tile_row("17SKT", "tile-by-tile", "raster-mask", 30, 28.5, 6.7, none),
                tile_row("17SKT", "whole-tile", "raster-mask", 54, 409.9, 39.1),
                # No clean run: the cell says why, and the tile stays in the table.
                tile_row(
                    "17SKT",
                    "tile-by-tile",
                    "lazy-stack",
                    runs=3,
                    timings_from_runs=0,
                    runs_with_memory_pressure=2,
                    runs_with_errors=1,
                ),
                tile_row(
                    "05VLG", "tile-by-tile", "raster-mask", runs=3, timings_from_runs=0, failed=3
                ),
            ],
        }
    }
    rendered = render_options.tile_extraction_rows(result)
    rows = [line for line in rendered.splitlines() if line.startswith("<tr>")]
    assert len(rows) == 15
    assert "Grand Lake St. Marys · 16TGK · 3 lakes" in rendered
    assert "<td>11.40 s</td><td>79</td><td>26.70 MB</td>" in rows[0]
    assert "Sum of lake medians" in rows[0] and "Not summarized" in rows[0]
    assert "A1 · Each lake separately" in rows[0] and "Separate process per lake" in rows[0]
    assert "A1 · Each lake separately" in rows[1] and "reopen files" in rows[1]
    assert 'colspan="5">Not measured' in rows[1]
    assert "<td>4.50 s</td><td>27</td><td>23.00 MB</td>" in rows[2]
    assert "B1 · Share image windows" in rows[2]
    assert "2 of 3 runs" in rows[2]
    assert "<td>41.60 s</td><td>54</td><td>394.20 MB</td>" in rows[3]
    assert "C1 · Read the whole image" in rows[3]
    assert "<td>14.20 s</td><td>71</td><td>92.90 MB</td>" in rows[4]
    assert "B2 · Share image windows" in rows[4]
    assert "Lanier · 17SKT · 1 lakes, 1 partly inside" in rendered
    assert "No matching individual-lake comparison" in rows[5]
    assert "No clean run: 2 under memory pressure, 1 with errors" in rows[9]
    assert "No clean run: 3 failed" in rows[12]
    assert 'colspan="5">Not measured' in rows[13]
    assert 'colspan="5">Not measured' in rows[14]

    # A subset baseline must not look like the whole tile's cost.
    full["lakes_with_baseline"] = ["a", "b"]
    partial = render_options.tile_extraction_rows(result, tile_ids={"16TGK"})
    assert "only 2 of 3 lakes" in partial
    assert "17SKT" not in partial and "05VLG" not in partial
    full["comparable"] = False
    unmatched = render_options.tile_extraction_rows(result, tile_ids={"16TGK"})
    assert "No matching individual-lake comparison" in unmatched
    assert "26.70 MB" not in unmatched


def test_lake_method_rows_keep_each_methods_costs_and_missing_results():
    result = fixture_result()
    clip = result["summary"]["by_size_class_method"][0]
    clip.update(requests_median=7, bytes_requested_median=1_500_000, peak_rss_bytes_max=333_000_000)
    rendered = render_options.lake_method_rows(result)
    rows = [line for line in rendered.splitlines() if line.startswith("<tr>")]
    assert len(rows) == 8
    assert "Nearby land omitted" in rows[0]
    assert "<td>2.10 s</td><td>7</td><td>1.50 MB</td><td>333 MB</td>" in rows[0]
    assert "All three classes" in rows[1]
    assert "<td>3.10 s</td><td>15</td><td>3.74 MB</td><td>166 MB</td>" in rows[1]
    assert "No successful read" in rows[-1]
    result["summary"]["by_size_class_method"] = []
    assert render_options.lake_method_rows(result).count("Not measured") == 8


def test_megabytes_label_switches_at_ten_megabytes():
    assert render_options.megabytes_label(3_735_552) == "3.7 MB"
    assert render_options.megabytes_label(41_500_000) == "42 MB"
    assert render_options.machine_label(
        {"cpu_count": 8, "machine": "arm64", "memory_total_bytes": 16e9}
    ) == ("8-core arm64 laptop, 14.9 GiB memory")


def cross_tile_fixture():
    medians, workloads = [], []
    for method in ("raster-mask", "lazy-stack"):
        for path, factor in (("lake-first", 2), ("tile-first", 1)):
            medians.append(
                {
                    "path": path,
                    "method": method,
                    "clean_repetitions": 2,
                    "excluded_repetitions": 1,
                    "wall_seconds": 20 * factor,
                    "requests": 100 * factor,
                    "bytes_requested": 12_500_000 * factor,
                }
            )
            for clean, seconds in ((True, 18 * factor), (True, 22 * factor), (False, 999)):
                workloads.append(
                    {
                        "path": path,
                        "method": method,
                        "clean": clean,
                        "end_to_end_seconds": seconds,
                    }
                )
    return {"summary": {"medians": medians, "workloads": workloads}}


def test_cross_tile_rows_use_workload_medians_and_only_clean_ranges():
    result = cross_tile_fixture()
    result["summary"]["medians"].reverse()
    rendered = render_options.cross_tile_rows(result)
    assert rendered.count("<tr>") == 4
    assert "40.00 s" in rendered and "36.00–44.00 s" in rendered
    assert "20.00 s" in rendered and "18.00–22.00 s" in rendered
    assert "25.00 MB" in rendered and "12.50 MB" in rendered
    assert rendered.count("2 included, 1 excluded") == 4
    assert "999" not in rendered


def test_cross_tile_rows_report_missing_clean_combinations():
    result = cross_tile_fixture()
    result["summary"]["medians"].pop()
    for row in result["summary"]["workloads"]:
        if row["method"] == "raster-mask" and row["path"] == "lake-first":
            row["clean"] = False
    rendered = render_options.cross_tile_rows(result)
    assert rendered.count("No clean complete repetition") == 2
    assert rendered.count("<tr>") == 4


@pytest.mark.parametrize("complete,equal", [(False, True), (True, False)])
def test_cross_tile_headline_refuses_incomplete_or_unequal_results(complete, equal):
    with pytest.raises(ValueError, match="requires complete, equal"):
        render_options.cross_tile_markers({"summary": {"complete": complete, "equal": equal}})
