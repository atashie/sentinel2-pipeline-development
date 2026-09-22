"""Prepare an explicit replacement run, or extract it under a verified macOS sleep guard."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "src")]

import lazy_reader_workloads as runner  # noqa: E402


def replacement_rows(audit):
    rows = {(row["cohort"], row["configuration"]): row for row in audit["rows"]}
    expected = {
        (cohort, name)
        for cohort in ("dispersed", "florida")
        for name in runner.readers.CONFIGURATIONS
    }
    if set(rows) != expected or len(audit["rows"]) != len(expected):
        raise ValueError("sleep audit must cover all fourteen distinct comparisons")
    selected, retained = [], []
    for key, row in rows.items():
        if row["sleep_intervals_overlapping"]:
            selected.append(list(key))
        elif row["status"] == "complete" and row["outputs_agree"]:
            retained.append(list(key))
        else:
            raise ValueError("unaffected incomplete attempt needs separate review")
    if not selected:
        raise ValueError("no sleep-affected attempts to replace")
    return selected, retained


def prepare(original, destination, audit_path, reason):
    """Reuse byte-identical selections. Never reset or overwrite original attempts."""
    original, destination = Path(original).resolve(), Path(destination).resolve()
    if not reason.strip():
        raise ValueError("record the owner's rerun authorization")
    if destination.exists() or original == destination or original in destination.parents:
        raise ValueError("replacement requires a new sibling run directory")
    with (original / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if runner.active_workers(original):
            raise ValueError("original run still has active or unresolved workers")
        identity = json.loads((original / "run.json").read_text())
        audit = json.loads(Path(audit_path).read_text())
        if audit["result_sha256"] != runner.file_digest(original / "result.json"):
            raise ValueError("sleep audit belongs to a different result")
        if identity["owner"] != runner.OWNER or identity["limits"] != runner.LIMITS:
            raise ValueError("original ownership or resource limits differ")
        selected, retained = replacement_rows(audit)
        for relative, digest in identity["source_digests"].items():
            if runner.file_digest(original / "source-at-extraction" / relative) != digest:
                raise ValueError(f"original source snapshot differs: {relative}")
        for cohort in ("dispersed", "florida"):
            runner.verify_frozen(original / cohort, expected_sources=identity["source_digests"])
            for phase in ("boundaries", "catalog", "freeze", "prepare"):
                if not runner.phase_complete(original / cohort / f"{phase}.json"):
                    raise ValueError(f"original preparation incomplete: {cohort}/{phase}")
        destination.mkdir(parents=True)
        pending = destination / "source-change.pending.json"
        lineage = {
            "authorized_at": runner.harness.utc_now(),
            "authorization": reason,
            "original_run": str(original),
            "original_result_sha256": audit["result_sha256"],
            "original_audit_sha256": runner.file_digest(audit_path),
            "original_source_digests": identity["source_digests"],
            "replacement_configurations": selected,
            "retained_configurations": retained,
            "input_hashes": {},
            "retained_artifact_hashes": {},
            "metadata_policy": "Build lazy graphs from frozen items without catalog links.",
        }
        runner.write_json(pending, lineage)
        shutil.copy2(audit_path, destination / "original-audit.json")
        shutil.copy2(original / "result.json", destination / "original-result.json")
        preflight = json.loads((original / "preflight.json").read_text())
        for cohort in ("dispersed", "florida"):
            source, target = original / cohort, destination / cohort
            target.mkdir()
            for name in ("manifest.json", "catalog.json", "selections.sqlite", "expected.sqlite"):
                shutil.copy2(source / name, target / name)
                lineage["input_hashes"][f"{cohort}/{name}"] = runner.file_digest(target / name)
            plan = json.loads((source / "frozen-plan.json").read_text())
            lineage["input_hashes"][f"{cohort}/original-frozen-plan.json"] = runner.file_digest(
                source / "frozen-plan.json"
            )
            shutil.copy2(source / "frozen-plan.json", target / "original-frozen-plan.json")
            plan["source_digests"] = runner.source_digests()
            plan["sha256"] = runner.readers.digest({k: v for k, v in plan.items() if k != "sha256"})
            runner.write_json(target / "frozen-plan.json", plan)
            local = json.loads((source / "preflight.json").read_text())
            local["plan_sha256"] = plan["sha256"]
            runner.write_json(target / "preflight.json", local)
            preflight["cohorts"][cohort]["preflight"] = local
            for saved_cohort, name in retained:
                if saved_cohort != cohort:
                    continue
                files = list(source.glob(f"extract-{name}.*"))
                files += [source / f"{name}.sqlite", source / f"{name}.gdal.log"]
                for path in files:
                    shutil.copy2(path, target / path.name)
                    lineage["retained_artifact_hashes"][f"{cohort}/{path.name}"] = (
                        runner.file_digest(path)
                    )
            runner.verify_frozen(target)
        runner.write_json(destination / "preflight.json", preflight)
        runner.write_json(
            destination / "run.json",
            {
                "owner": runner.OWNER,
                "created_at": runner.harness.utc_now(),
                "limits": runner.LIMITS,
                "source_digests": runner.source_digests(),
                "rerun": lineage,
            },
        )
        for relative in runner.source_digests():
            target = destination / "source-at-extraction" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        for path, name in (
            (original / "result.json", "lazy-reader-workloads-before-sleep-rerun.json"),
            (Path(audit_path), "lazy-reader-workloads-audit-before-sleep-rerun.json"),
        ):
            archive = runner.RESULT.parent / name
            archive.parent.mkdir(parents=True, exist_ok=True)
            if archive.exists() and runner.file_digest(archive) != runner.file_digest(path):
                raise ValueError("refusing to overwrite different historical evidence")
            shutil.copy2(path, archive)
        pending.unlink()
    print(f"Prepared {len(selected)} replacements, retaining {len(retained)} unaffected results.")


def assertions(pid):
    text = subprocess.check_output(["/usr/bin/pmset", "-g", "assertions"], text=True, timeout=10)
    owned = "\n".join(line for line in text.splitlines() if f"pid {pid}(" in line)
    if not all(name in owned for name in ("PreventUserIdleSystemSleep", "PreventSystemSleep")):
        raise RuntimeError("caffeinate sleep assertions are missing")
    return text


def save_power_events(path):
    with (
        subprocess.Popen(
            ["/usr/bin/pmset", "-g", "log"], stdout=subprocess.PIPE, text=True
        ) as process,
        Path(path).open("w") as output,
    ):
        for line in process.stdout:
            if any(token in line for token in ("Entering Sleep", "Wake from", "DarkWake")):
                output.write(line)
        if process.wait() != 0:
            raise RuntimeError("could not capture macOS power events")


@contextmanager
def awake(run):
    """Acquire real assertions before extraction, monitor them, and release on exit."""
    if sys.platform != "darwin":
        raise RuntimeError("this recovery guard requires macOS")
    run = Path(run)
    diagnostics = run / "diagnostics"
    diagnostics.mkdir(exist_ok=True)
    battery = subprocess.check_output(["/usr/bin/pmset", "-g", "batt"], text=True, timeout=10)
    if "AC Power" not in battery:
        raise RuntimeError("connect AC power before starting the replacement run")
    stopped, errors = threading.Event(), []
    guard = subprocess.Popen(["/usr/bin/caffeinate", "-dis", "-w", str(os.getpid())])
    record = {"started_at": runner.harness.utc_now(), "pid": guard.pid, "checks": 0}
    status_path = diagnostics / "keep-awake.json"

    def check():
        if guard.poll() is not None:
            raise RuntimeError("keep-awake process exited during extraction")
        text = assertions(guard.pid)
        (diagnostics / "assertions-latest.txt").write_text(text)
        record.update(checks=record["checks"] + 1, checked_at=runner.harness.utc_now())
        runner.write_json(status_path, record)

    def monitor():
        while not stopped.wait(30):
            try:
                check()
            except Exception as exc:
                errors.append(str(exc))
                # The supervisor catches the interrupt and cleans its worker process group.
                import _thread

                _thread.interrupt_main()
                return

    thread = None
    try:
        for attempt in range(20):
            try:
                check()
                break
            except RuntimeError:
                if attempt == 19:
                    raise
                time.sleep(0.1)
        (diagnostics / "assertions-start.txt").write_text(assertions(guard.pid))
        (diagnostics / "power-source-start.txt").write_text(battery)
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        print(f"Verified macOS sleep assertions for caffeinate PID {guard.pid}.", flush=True)
        yield
        check()
        if errors:
            raise RuntimeError(errors[0])
    finally:
        stopped.set()
        if thread:
            thread.join(timeout=12)
        guard.terminate()
        guard.wait(timeout=10)
        record.update(finished_at=runner.harness.utc_now(), released=True, errors=errors)
        runner.write_json(status_path, record)
        save_power_events(diagnostics / "power-events.log")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-from", type=Path)
    mode.add_argument("--extract", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--reason")
    args = parser.parse_args()
    if args.prepare_from:
        if not all((args.destination, args.audit, args.reason)):
            parser.error("preparation requires --destination, --audit, and --reason")
        prepare(args.prepare_from, args.destination, args.audit, args.reason)
    else:
        with awake(args.extract):
            result = runner.extract(args.extract)
        if result["status"] != "complete":
            raise SystemExit("replacement comparison remains incomplete; inspect saved failures")


if __name__ == "__main__":
    main()
