"""Replacement authorization, preserved evidence, and verified sleep assertions."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import rerun_sleep_workloads as recovery  # noqa: E402

runner = recovery.runner


def audit_rows():
    return [
        {
            "cohort": cohort,
            "configuration": name,
            "sleep_intervals_overlapping": int(
                not (cohort == "dispersed" and name.startswith("A-"))
            ),
            "status": "complete",
            "outputs_agree": True,
        }
        for cohort in ("dispersed", "florida")
        for name in runner.readers.CONFIGURATIONS
    ]


def test_only_sleep_affected_attempts_are_replaced():
    rows = audit_rows()
    selected, retained = recovery.replacement_rows({"rows": rows})
    assert len(selected) == 12
    assert retained == [["dispersed", "A-raster"], ["dispersed", "A-lazy"]]
    with pytest.raises(ValueError, match="fourteen distinct"):
        recovery.replacement_rows({"rows": rows + [rows[0]]})
    rows[0]["status"] = "incomplete"
    with pytest.raises(ValueError, match="separate review"):
        recovery.replacement_rows({"rows": rows})


def test_sleep_guard_requires_its_own_assertions(monkeypatch):
    text = (
        "pid 100(caffeinate): PreventSystemSleep\npid 100(caffeinate): PreventUserIdleSystemSleep"
    )
    monkeypatch.setattr(recovery.subprocess, "check_output", lambda *a, **k: text)
    assert recovery.assertions(100) == text
    with pytest.raises(RuntimeError, match="missing"):
        recovery.assertions(101)


def test_replacement_preserves_inputs_attempts_and_source_lineage(tmp_path, monkeypatch):
    source, destination = tmp_path / "old", tmp_path / "new"
    monkeypatch.setattr(runner, "RESULT", tmp_path / "results/lazy-reader-workloads.json")
    relative = "benchmarks/workload_readers.py"
    snapshot = source / "source-at-extraction" / relative
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text("original source\n")
    old_sources = {relative: runner.file_digest(snapshot)}
    new_sources = {relative: runner.file_digest(recovery.ROOT / relative)}
    monkeypatch.setattr(runner, "source_digests", lambda: new_sources)
    runner.write_json(
        source / "run.json",
        {"owner": runner.OWNER, "limits": runner.LIMITS, "source_digests": old_sources},
    )
    runner.write_json(source / "result.json", {"status": "incomplete"})
    audit = {"rows": audit_rows(), "result_sha256": runner.file_digest(source / "result.json")}
    runner.write_json(source / "audit.json", audit)
    preflight = {"status": "preflight_complete", "cohorts": {}}
    for cohort in ("dispersed", "florida"):
        directory = source / cohort
        directory.mkdir()
        runner.write_json(directory / "manifest.json", {"lakes": []})
        runner.write_json(directory / "catalog.json", {"items": {}})
        for name in ("selections.sqlite", "expected.sqlite"):
            (directory / name).write_bytes(b"frozen selection fixture")
        plan = {
            "source_digests": old_sources,
            "scenes": [{"identity": "frozen item"}],
            "order": runner.readers.CONFIGURATIONS,
            "selection_sha256": runner.file_digest(directory / "selections.sqlite"),
            "expected_sha256": runner.file_digest(directory / "expected.sqlite"),
        }
        plan["sha256"] = runner.readers.digest(plan)
        runner.write_json(directory / "frozen-plan.json", plan)
        runner.write_json(directory / "selected-plan.json", plan)
        local = {"plan_sha256": plan["sha256"]}
        runner.write_json(directory / "preflight.json", local)
        preflight["cohorts"][cohort] = {"preflight": local}
        for phase in ("boundaries", "catalog", "freeze", "prepare"):
            runner.write_json(directory / f"{phase}.supervision.json", {"status": "complete"})
            runner.write_json(
                directory / f"{phase}.result.json",
                {"status": "complete", "artifacts": runner.artifact_digests(directory, phase)},
            )
    for name in ("A-raster", "A-lazy"):
        directory = source / "dispersed"
        runner.write_json(directory / f"extract-{name}.json", {"phase": "extract"})
        runner.write_json(directory / f"extract-{name}.supervision.json", {"status": "complete"})
        (directory / f"{name}.sqlite").write_bytes(b"original completed signatures")
        (directory / f"{name}.gdal.log").write_text("original logs\n")
    runner.write_json(source / "preflight.json", preflight)
    before = {
        str(p.relative_to(source)): runner.file_digest(p) for p in source.rglob("*") if p.is_file()
    }
    recovery.prepare(source, destination, source / "audit.json", "Owner requested sleep reruns")
    assert all(runner.file_digest(source / p) == digest for p, digest in before.items())
    identity = json.loads((destination / "run.json").read_text())
    assert identity["rerun"]["original_source_digests"] == old_sources
    assert len(identity["rerun"]["replacement_configurations"]) == 12
    for cohort in ("dispersed", "florida"):
        original_plan = json.loads((source / cohort / "frozen-plan.json").read_text())
        new_plan = runner.verify_frozen(destination / cohort)
        expected = copy.deepcopy(original_plan)
        expected["source_digests"] = new_sources
        expected.pop("sha256")
        assert {k: v for k, v in new_plan.items() if k != "sha256"} == expected
        for name in runner.readers.CONFIGURATIONS:
            assert runner.extraction_attempted(destination / cohort / f"extract-{name}.json") == (
                cohort == "dispersed" and name.startswith("A-")
            )
    with pytest.raises(ValueError, match="new sibling"):
        recovery.prepare(source, destination, source / "audit.json", "authorized")
