"""Sleep events qualify timing without being attributed as a proven failure cause."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import audit_workload_execution as execution  # noqa: E402
from audit_workload_execution import sleep_intervals  # noqa: E402


def test_sleep_intervals_end_at_maintenance_or_full_wake():
    text = """2026-09-19 13:00:00 -0400 Wake Wake from Deep Idle
2026-09-19 14:00:00 -0400 Sleep Entering Sleep state due to 'Idle Sleep'
2026-09-19 14:10:00 -0400 DarkWake DarkWake from Deep Idle
2026-09-19 14:11:00 -0400 Sleep Entering Sleep state due to 'Maintenance Sleep'
2026-09-19 14:12:00 -0400 Wake Wake from Deep Idle
2026-09-19 14:20:00 -0400 Sleep Entering Sleep state due to 'Idle Sleep'
"""
    intervals = sleep_intervals(text)
    assert [end - start for start, end in intervals] == [600, 60]
    assert intervals[1][0] - intervals[0][1] == 60


def test_rerun_audit_binds_retained_inputs_and_guard_coverage(tmp_path, monkeypatch):
    runner = execution.runner
    monkeypatch.setattr(runner, "source_digests", lambda: {})
    monkeypatch.setattr(runner, "active_workers", lambda _: [])
    monkeypatch.setattr(runner, "verify_frozen", lambda _: None)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(execution, "ROOT", tmp_path)
    result_path = tmp_path / "result.json"
    monkeypatch.setattr(runner, "RESULT", result_path)
    retained = [["dispersed", "A-raster"], ["dispersed", "A-lazy"]]
    original_rows, cohorts = [], {}
    start, end = "2026-09-21T15:00:01+00:00", "2026-09-21T15:00:10+00:00"
    for cohort in ("dispersed", "florida"):
        rows = []
        for name in runner.readers.CONFIGURATIONS:
            inherited = [cohort, name] in retained
            started = "2026-09-19T15:00:00+00:00" if inherited else start
            finished = "2026-09-19T15:01:00+00:00" if inherited else end
            prefix = tmp_path / cohort / f"extract-{name}"
            runner.write_json(prefix.with_suffix(".launch.json"), {"state": "spawned"})
            supervision = prefix.with_suffix(".supervision.json")
            runner.write_json(supervision, {"status": "complete"})
            timestamp = datetime.fromisoformat(finished).timestamp()
            os.utime(supervision, (timestamp, timestamp))
            runner.write_json(prefix.with_suffix(".cleanup.json"), {"remaining_files": []})
            rows.append(
                {
                    "configuration": name,
                    "started_at": started,
                    "status": "complete",
                    "matches_all_complete_outputs": True,
                    "validation": {"ordered_signature": cohort, "complete": True},
                    "supervision": {"peak_aggregate_rss_bytes": 1, "status": "complete"},
                }
            )
            if inherited:
                original_rows.append(
                    {
                        "cohort": cohort,
                        "configuration": name,
                        "sleep_intervals_overlapping": 0,
                        "sleep_seconds_overlapping": 0,
                    }
                )
        cohorts[cohort] = {"comparisons": rows}
        for name, source in (("original-frozen-plan.json", "old"), ("frozen-plan.json", "new")):
            runner.write_json(
                tmp_path / cohort / name,
                {"source_digests": source, "sha256": source, "workload": cohort},
            )
    runner.write_json(tmp_path / "original-audit.json", {"rows": original_rows})
    runner.write_json(
        tmp_path / "original-result.json",
        {
            "cohorts": {
                "dispersed": {"comparisons": cohorts["dispersed"]["comparisons"][:2]},
                "florida": {"comparisons": [cohorts["florida"]["comparisons"][4]]},
            }
        },
    )
    selections = tmp_path / "selections.sqlite"
    selections.write_bytes(b"unchanged frozen geometry")
    identity = {
        "owner": runner.OWNER,
        "source_digests": {},
        "rerun": {
            "original_result_sha256": runner.file_digest(tmp_path / "original-result.json"),
            "original_audit_sha256": runner.file_digest(tmp_path / "original-audit.json"),
            "input_hashes": {"selections.sqlite": runner.file_digest(selections)},
            "retained_artifact_hashes": {},
            "retained_configurations": retained,
        },
    }
    runner.write_json(tmp_path / "run.json", identity)
    runner.write_json(
        result_path,
        {"cohorts": cohorts, "provider": {}, "cleanup": {"remaining_files": []}},
    )
    guard_path = tmp_path / "diagnostics/keep-awake.json"
    guard = {
        "started_at": "2026-09-21T15:00:00+00:00",
        "finished_at": "2026-09-21T15:00:11+00:00",
        "released": True,
        "errors": [],
        "checks": 2,
    }
    runner.write_json(guard_path, guard)
    power = tmp_path / "diagnostics/power-events.log"
    power.write_text("")
    result = execution.audit(tmp_path, power)
    assert result["complete_workers"] == 14
    assert result["new_extraction_launches"] == 12
    assert result["retained_original_attempts"] == 2
    assert result["prior_complete_outputs_compared"] == 3
    assert result["prior_complete_outputs_unchanged"] == 3
    assert sum(row["attempt_origin"] == "retained original" for row in result["rows"]) == 2
    guard["started_at"] = "2026-09-21T15:00:05+00:00"
    runner.write_json(guard_path, guard)
    with pytest.raises(AssertionError):
        execution.audit(tmp_path, power)
    guard["started_at"] = "2026-09-21T15:00:00+00:00"
    runner.write_json(guard_path, guard)
    for name in ("assertions-start.txt", "assertions-latest.txt", "power-source-start.txt"):
        (guard_path.parent / name).write_text("fixture evidence\n")
    archived = execution.archive_session(tmp_path, "Preserve a completed guard before resuming")
    assert execution.archive_session(tmp_path, "Idempotent repeat") == archived
    runner.write_json(
        guard_path,
        {
            **guard,
            "started_at": "2026-09-21T15:00:12+00:00",
            "finished_at": "2026-09-21T15:00:15+00:00",
        },
    )
    resumed = execution.audit(tmp_path, power)
    assert len(resumed["keep_awake_sessions"]) == 2
    assert resumed["complete_workers"] == 14
    plan_path = tmp_path / "florida/frozen-plan.json"
    plan = json.loads(plan_path.read_text())
    runner.write_json(plan_path, {**plan, "workload": "different"})
    with pytest.raises(AssertionError, match="frozen workload changed"):
        execution.audit(tmp_path, power)
    runner.write_json(plan_path, plan)
    selections.write_bytes(b"unexpectedly changed geometry")
    with pytest.raises(AssertionError, match="selections.sqlite"):
        execution.audit(tmp_path, power)
    assert json.loads((tmp_path / "run.json").read_text()) == identity
