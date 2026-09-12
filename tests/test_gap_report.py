"""The committed gap survey report must match what tools/gap_report.py computes. No network."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "reviews" / "2026-09-10-gap-survey-report.json"


def test_report_matches_survey_results():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gap_report.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_report_findings_cite_inputs_and_issues():
    report = json.loads(REPORT.read_text())
    inputs = {entry["id"] for entry in report["inputs"]}
    for entry in report["inputs"]:
        assert (ROOT / entry["path"]).exists(), entry["path"]
        assert len(entry["sha256"]) == 64
    ids = [finding["id"] for finding in report["findings"]]
    assert len(ids) == len(set(ids))
    for finding in report["findings"]:
        assert finding["status"] == "measured"
        assert finding["numbers"], finding["id"]
        assert finding["evidence"], finding["id"]
        for evidence in finding["evidence"]:
            assert evidence["input"] in inputs, finding["id"]
        assert finding["bears_on"], finding["id"]
    for gap in report["decision_inputs"]["gaps"]:
        for ref in gap["findings"]:
            assert ref in ids, gap["id"]


def _module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gap_report", ROOT / "tools" / "gap_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample(item_id, software, scl_type, scl_host, baseline="04.00"):
    return {
        "item_id": item_id,
        "collection": "sentinel-2-l2a",
        "software": {"sentinel2-to-stac": software},
        "baseline": baseline,
        "storage": {},
        "quality_assets": {"scl": {"type": scl_type, "href_host": scl_host}},
    }


def test_quality_layouts_keep_distinct_layouts_per_software_version():
    gap_report = _module()
    cog = "image/tiff; application=geotiff; profile=cloud-optimized"
    samples = [
        _sample("a", "2026.08.16", cog, "sentinel-cogs.s3.us-west-2.amazonaws.com", "04.00"),
        _sample("b", "2026.08.16", "image/jp2", "sentinel-s2-l2a", "03.01"),
        _sample("c", "2026.08.16", cog, "sentinel-cogs.s3.us-west-2.amazonaws.com", "05.12"),
    ]
    layouts = gap_report.quality_layouts_from(samples)
    assert len(layouts) == 2
    by_ids = {tuple(layout["sample_item_ids"]): layout for layout in layouts}
    assert by_ids[("a", "c")]["baselines"] == ["04.00", "05.12"]
    assert by_ids[("a", "c")]["quality_assets"]["scl"]["class"] == "cog"
    assert by_ids[("b",)]["quality_assets"]["scl"]["class"] == "other"
    assert gap_report.quality_layouts_from(list(reversed(samples))) == layouts


def test_validate_inputs_rejects_foreign_or_incomplete_fallback():
    import copy

    import pytest

    gap_report = _module()
    gap = json.loads((ROOT / "benchmarks" / "results" / "gap-survey.json").read_text())
    fallback = json.loads((ROOT / "benchmarks" / "results" / "fallback-survey.json").read_text())
    digest = gap_report.sha256(ROOT / "benchmarks" / "results" / "gap-survey.json")
    gap_report.validate_inputs(gap, fallback, digest)
    with pytest.raises(ValueError, match="different gap survey"):
        gap_report.validate_inputs(gap, fallback, "0" * 64)
    trimmed = copy.deepcopy(fallback)
    trimmed["tiles"].pop(next(iter(trimmed["tiles"])))
    with pytest.raises(ValueError, match="missing"):
        gap_report.validate_inputs(gap, trimmed, digest)
    extra = copy.deepcopy(fallback)
    tile = next(iter(extra["tiles"]))
    extra["tiles"][tile]["monthly"]["2019-01"] = extra["tiles"][tile]["monthly"][
        next(iter(extra["tiles"][tile]["monthly"]))
    ]
    with pytest.raises(ValueError, match="extra"):
        gap_report.validate_inputs(gap, extra, digest)
