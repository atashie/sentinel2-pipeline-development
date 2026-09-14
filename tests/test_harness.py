"""Tests for the measurement harness. No network."""

import logging

from s2proto import harness


def test_parse_gdal_log_counts_ranges_and_size_probes():
    lines = [
        "GDAL: GDALOpen(https://x/B04.tif, this=0x1) succeeds as GTiff.",
        "VSICURL: GetFileSize(https://x/B04.tif)=123456789  response_code=200",
        "VSICURL: Downloading 0-16383 (https://x/B04.tif)...",
        "VSICURL: Downloading 16384-32767,65536-98303 (https://x/B04.tif)...",
        "VSICURL: Downloading 1000-1999 (https://x/B04.tif)...",
    ]
    assert harness.parse_gdal_log(lines) == {"requests": 3, "bytes": 66536, "size_requests": 1}
    assert harness.parse_gdal_log([]) == {"requests": 0, "bytes": 0, "size_requests": 0}


def test_normalize_maxrss_by_platform():
    assert harness.normalize_maxrss(1000, "Darwin") == 1000
    assert harness.normalize_maxrss(1000, "Linux") == 1_024_000
    assert harness.peak_rss_bytes() > 1_000_000


def test_timer_cpu_and_net_helpers():
    with harness.Timer() as timer:
        sum(range(10000))
    assert timer.seconds >= 0
    before = harness.cpu_seconds()
    after = {"user": before["user"] + 1.5, "system": before["system"]}
    assert harness.cpu_delta(before, after) == {"user": 1.5, "system": 0.0}
    assert harness.net_delta(None, {"bytes_recv": 1, "bytes_sent": 1}) is None
    assert harness.net_delta(
        {"bytes_recv": 1, "bytes_sent": 2}, {"bytes_recv": 5, "bytes_sent": 2}
    ) == {
        "bytes_recv": 4,
        "bytes_sent": 0,
    }


def test_machine_info_names_the_libraries():
    info = harness.machine_info()
    assert info["system"] and info["python"] and info["cpu_count"]
    assert (
        info["libraries"]["rasterio"] and info["libraries"]["gdal"] and info["libraries"]["numpy"]
    )


def test_gdal_log_capture_collects_rasterio_logger_lines():
    with harness.GdalLogCapture() as capture:
        logging.getLogger("rasterio._env").debug("VSICURL: Downloading 0-9 (https://x)...")
        first = capture.take()
        logging.getLogger("rasterio").debug("second")
    assert first == ["VSICURL: Downloading 0-9 (https://x)..."]
    assert capture.all_lines == first
    assert capture.take() == ["second"]


def test_code_version_and_digest():
    assert harness.code_version() != ""
    assert harness.sha256_bytes(b"abc").startswith("ba7816bf")
