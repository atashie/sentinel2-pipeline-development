"""Audit a completed workload run and saved macOS sleep events, without network access."""

from __future__ import annotations

import argparse
import fcntl
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "src")]

import lazy_reader_workloads as runner  # noqa: E402


def archive_session(run, reason):
    """Preserve a finished guard session before an explicit extraction resume."""
    run = Path(run).resolve()
    if not reason.strip():
        raise ValueError("record why this guarded session is being archived")
    with (run / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identity = json.loads((run / "run.json").read_text())
        assert identity["owner"] == runner.OWNER
        assert identity["source_digests"] == runner.source_digests()
        assert not runner.active_workers(run)
        diagnostics = run / "diagnostics"
        guard = json.loads((diagnostics / "keep-awake.json").read_text())
        assert guard["released"]
        history = diagnostics / "keep-awake-history"
        history.mkdir(exist_ok=True)
        for folder in sorted(history.iterdir()):
            manifest = json.loads((folder / "manifest.json").read_text())
            for name, digest in manifest["sha256"].items():
                assert runner.file_digest(folder / name) == digest
            if manifest["sha256"]["keep-awake.json"] == runner.file_digest(
                diagnostics / "keep-awake.json"
            ):
                return folder
        target = history / f"{len(list(history.iterdir())) + 1:04d}"
        target.mkdir()
        for name in (
            "keep-awake.json",
            "assertions-start.txt",
            "assertions-latest.txt",
            "power-source-start.txt",
            "power-events.log",
        ):
            shutil.copy2(diagnostics / name, target / name)
        shutil.copy2(run / "result.json", target / "result.json")
        shutil.copy2(__file__, target / "audit_workload_execution.py")
        runner.write_json(
            target / "manifest.json",
            {
                "recorded_at": runner.harness.utc_now(),
                "reason": reason,
                "sha256": {path.name: runner.file_digest(path) for path in target.iterdir()},
            },
        )
        return target


def sleep_intervals(text):
    intervals, started = [], None
    for line in text.splitlines():
        match = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4})\s+(\w+)", line)
        if not match:
            continue
        timestamp = datetime.strptime(match[1], "%Y-%m-%d %H:%M:%S %z").timestamp()
        if match[2] == "Sleep" and "Entering Sleep" in line:
            if started is None:
                started = timestamp
        elif match[2] in ("Wake", "DarkWake") and started is not None:
            intervals.append((started, timestamp))
            started = None
    return intervals


def audit(run, power_log):
    run = Path(run).resolve()
    result_path = run / "result.json"
    result = json.loads(result_path.read_text())
    assert runner.file_digest(result_path) == runner.file_digest(runner.RESULT)
    identity = json.loads((run / "run.json").read_text())
    assert identity["source_digests"] == runner.source_digests()
    lineage = identity.get("rerun")
    retained = {tuple(key) for key in (lineage or {}).get("retained_configurations", [])}
    original_rows, original_signatures = {}, {}
    guard, guard_sessions, archived_intervals = None, [], []
    if lineage:
        assert runner.file_digest(run / "original-result.json") == lineage["original_result_sha256"]
        assert runner.file_digest(run / "original-audit.json") == lineage["original_audit_sha256"]
        original = json.loads((run / "original-audit.json").read_text())
        original_rows = {(row["cohort"], row["configuration"]): row for row in original["rows"]}
        previous_result = json.loads((run / "original-result.json").read_text())
        original_signatures = {
            (cohort, row["configuration"]): row["validation"]["ordered_signature"]
            for cohort, data in previous_result["cohorts"].items()
            for row in data["comparisons"]
            if row["status"] == "complete"
        }
        for relative, digest in {
            **lineage["input_hashes"],
            **lineage["retained_artifact_hashes"],
        }.items():
            assert runner.file_digest(run / relative) == digest, relative
        for relative, digest in identity["source_digests"].items():
            assert runner.file_digest(run / "source-at-extraction" / relative) == digest
        guard = json.loads((run / "diagnostics/keep-awake.json").read_text())
        for folder in sorted((run / "diagnostics/keep-awake-history").glob("*")):
            manifest = json.loads((folder / "manifest.json").read_text())
            for name, digest in manifest["sha256"].items():
                assert runner.file_digest(folder / name) == digest
            guard_sessions.append(json.loads((folder / "keep-awake.json").read_text()))
            archived_intervals.extend(sleep_intervals((folder / "power-events.log").read_text()))
        guard_sessions.append(guard)
        assert all(g["released"] and not g["errors"] and g["checks"] > 0 for g in guard_sessions)
    assert not runner.active_workers(run)
    assert not (run / "temporary-images").exists()
    assert result["cleanup"]["remaining_files"] == []
    launches = list(run.glob("*/extract-*.launch.json"))
    assert len(launches) == 14
    assert all(json.loads(path.read_text())["state"] == "spawned" for path in launches)
    intervals = sorted(set([*archived_intervals, *sleep_intervals(Path(power_log).read_text())]))
    rows = []
    for cohort, data in result["cohorts"].items():
        runner.verify_frozen(run / cohort)
        if lineage:
            plans = [
                json.loads((run / cohort / name).read_text())
                for name in ("original-frozen-plan.json", "frozen-plan.json")
            ]
            fields = [
                {
                    key: value
                    for key, value in plan.items()
                    if key not in ("source_digests", "sha256")
                }
                for plan in plans
            ]
            assert fields[0] == fields[1], f"frozen workload changed: {cohort}"
        assert len(data["comparisons"]) == 7
        for row in data["comparisons"]:
            name = row["configuration"]
            directory = run / cohort
            supervision = directory / f"extract-{name}.supervision.json"
            start = datetime.fromisoformat(row["started_at"]).timestamp()
            end = supervision.stat().st_mtime
            overlap = [max(0.0, min(end, b) - max(start, a)) for a, b in intervals]
            inherited = (cohort, name) in retained
            sleep_count = sum(value > 0 for value in overlap)
            sleep_seconds = sum(overlap)
            if inherited:
                prior = original_rows[cohort, name]
                sleep_count = prior["sleep_intervals_overlapping"]
                sleep_seconds = prior["sleep_seconds_overlapping"]
            elif guard:
                assert any(
                    datetime.fromisoformat(session["started_at"]).timestamp() <= start
                    and end <= datetime.fromisoformat(session["finished_at"]).timestamp() + 1
                    for session in guard_sessions
                ), f"attempt lies outside recorded sleep guards: {cohort}/{name}"
            cleanup = json.loads((directory / f"extract-{name}.cleanup.json").read_text())
            assert cleanup["remaining_files"] == []
            original_signature = original_signatures.get((cohort, name))
            matches_previous = (
                row["validation"]["ordered_signature"] == original_signature
                if row["status"] == "complete" and original_signature is not None
                else None
            )
            rows.append(
                {
                    "cohort": cohort,
                    "configuration": name,
                    "attempt_origin": "retained original" if inherited else "current run",
                    "status": row["status"],
                    "outputs_agree": row.get("matches_all_complete_outputs", False),
                    "matches_prior_complete_output": matches_previous,
                    "started_at": row["started_at"],
                    "observed_finished_at": datetime.fromtimestamp(end, UTC).isoformat(),
                    "observed_wall_seconds": end - start,
                    "recorded_worker_elapsed_seconds": row.get("elapsed_seconds"),
                    "sleep_intervals_overlapping": sleep_count,
                    "sleep_seconds_overlapping": sleep_seconds,
                    "cpu_seconds": sum(row.get("cpu", {}).values()),
                    "peak_aggregate_rss_bytes": row["supervision"]["peak_aggregate_rss_bytes"],
                    "error": row.get("error"),
                }
            )
    return {
        "measured_at": runner.harness.utc_now(),
        "code_version": runner.harness.code_version(),
        "provider": result["provider"],
        "audit_network_access": False,
        "result_path": str(runner.RESULT.relative_to(ROOT)),
        "result_sha256": runner.file_digest(result_path),
        "script_sha256": runner.file_digest(Path(__file__)),
        "power_log_sha256": runner.file_digest(Path(power_log)),
        "power_log": str(Path(power_log).resolve()),
        "source_history_entries": len(identity.get("source_history", [])),
        "extraction_launches": len(launches),
        "new_extraction_launches": len(launches) - len(retained),
        "retained_original_attempts": len(retained),
        "prior_complete_outputs_compared": sum(
            row["matches_prior_complete_output"] is not None for row in rows
        ),
        "prior_complete_outputs_unchanged": sum(
            row["matches_prior_complete_output"] is True for row in rows
        ),
        "keep_awake": guard,
        "keep_awake_sessions": guard_sessions,
        "complete_workers": sum(row["status"] == "complete" for row in rows),
        "incomplete_workers": sum(row["status"] != "complete" for row in rows),
        "memory_stops": sum(
            row["supervision"]["status"] == "memory_stopped"
            for data in result["cohorts"].values()
            for row in data["comparisons"]
        ),
        "source_integrity_verified": True,
        "frozen_inputs_verified": True,
        "owned_image_workspace_removed": True,
        "no_active_workers": True,
        "rows": rows,
        "limitations": [
            "Power events are an after-the-run host audit, not part of the original timers.",
            "Observed finish times come from supervision file modification times.",
            "Recorded elapsed timers differ from wall time across laptop sleep.",
            "Sleep overlap confounds performance interpretation, "
            "without proving each failure's cause.",
            "Retained originals use their saved source version and sleep audit. "
            "Replacement lazy graphs omit catalog links and use frozen metadata.",
            "GDAL request counts exclude any Python metadata requests in the original attempts.",
            "Partial attempts cannot establish completed-workload speed or peak memory.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--power-log", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--archive-session", action="store_true")
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.archive_session:
        if not args.reason or args.power_log or args.output:
            parser.error("--archive-session requires --reason and no audit output options")
        print(archive_session(args.run_directory, args.reason))
        return
    if not args.power_log or not args.output:
        parser.error("auditing requires --power-log and --output")
    result = audit(args.run_directory, args.power_log)
    runner.write_json(args.output, result)
    print(
        f"Audited {result['extraction_launches']} launches: "
        f"{result['complete_workers']} complete, {result['incomplete_workers']} incomplete"
    )
    for row in result["rows"]:
        print(
            row["cohort"],
            row["configuration"],
            row["status"],
            "sleep intervals:",
            row["sleep_intervals_overlapping"],
        )


if __name__ == "__main__":
    main()
