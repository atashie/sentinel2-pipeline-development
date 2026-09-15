"""Fixture tests for the renderer's stage 2 rows. No network, no result file needed."""

import importlib.util
from pathlib import Path

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


def test_megabytes_label_switches_at_ten_megabytes():
    assert render_options.megabytes_label(3_735_552) == "3.7 MB"
    assert render_options.megabytes_label(41_500_000) == "42 MB"
    assert render_options.machine_label(
        {"cpu_count": 8, "machine": "arm64", "memory_total_bytes": 16e9}
    ) == ("8-core arm64 laptop, 16 GB memory")
