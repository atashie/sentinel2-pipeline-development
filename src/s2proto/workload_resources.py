"""Bounded allocations, process supervision, and owned temporary image directories."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil

GIB = 1024**3
MIB = 1024**2
LIMITS = {
    "planned_worker_bytes": 2 * GIB,
    "aggregate_rss_bytes": 4 * GIB,
    "reserve_bytes": 3 * GIB,
    "gdal_cache_bytes": 256 * MIB,
    "active_arrays_bytes": 512 * MIB,
    "threads": 2,
    "poll_seconds": 0.1,
}
OWNER = "sentinel2-lazy-workloads-v1"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def admit(scratch_bytes, *, active_arrays_bytes=0, limits=LIMITS):
    """Check conservative scratch estimates before allocating, in addition to RSS polling."""
    rss = psutil.Process().memory_info().rss
    available = psutil.virtual_memory().available
    if active_arrays_bytes > limits["active_arrays_bytes"]:
        raise MemoryError("active arrays exceed the declared 512 MiB limit")
    if rss + scratch_bytes > limits["planned_worker_bytes"]:
        raise MemoryError(f"planned worker footprint exceeds limit: {rss} + {scratch_bytes}")
    if available < scratch_bytes + limits["reserve_bytes"]:
        raise MemoryError("allocation would consume the system memory reserve")


def create_workspace(run_directory):
    run_directory = Path(run_directory).resolve()
    path = run_directory / "temporary-images"
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.mkdir()
    write_json(path / "owner.json", {"owner": OWNER, "run": str(run_directory)})
    return path


def clean_workspace(run_directory):
    """Delete only our marked directory. Never follow a root or descendant symlink."""
    run_directory = Path(run_directory).resolve()
    path = run_directory / "temporary-images"
    if not path.exists() and not path.is_symlink():
        return {"removed": False, "remaining_files": []}
    if path.is_symlink() or path.resolve().parent != run_directory:
        raise ValueError("temporary workspace escapes the run directory")
    marker = path / "owner.json"
    if marker.is_symlink():
        raise ValueError("symlink ownership marker")
    owner = json.loads(marker.read_text())
    if owner != {"owner": OWNER, "run": str(run_directory)}:
        raise ValueError("workspace is not owned by this benchmark")
    files, byte_count = 0, 0
    for directory, _, names in os.walk(path, followlinks=False):
        for name in names:
            entry = Path(directory) / name
            files += 1
            byte_count += entry.lstat().st_size
    # rmtree unlinks descendant symlinks, without traversing their targets.
    shutil.rmtree(path)
    return {
        "removed": True,
        "files_removed": files,
        "bytes_removed": byte_count,
        "remaining_files": [],
        "workspace_exists": path.exists(),
    }


def recover_workspaces(parent):
    """Recover only marked temporary directories from completed or dead supervisors."""
    recovered = []
    for run in sorted(Path(parent).glob("*/supervisor.json")):
        if run.is_symlink() or run.parent.is_symlink():
            continue
        record = json.loads(run.read_text())
        if record.get("owner") != OWNER:
            continue
        try:
            process = psutil.Process(record["pid"])
            live = abs(process.create_time() - record["create_time"]) < 0.01
        except psutil.NoSuchProcess:
            live = False
        if not live and not active_workers(run.parent):
            audit = clean_workspace(run.parent)
            write_json(run.parent / "recovery-cleanup.json", audit)
            recovered.append(str(run.parent))
    return recovered


def active_workers(run_directory):
    """Do not clean or resume underneath a surviving worker after supervisor failure."""
    active = []
    for marker in Path(run_directory).glob("*/*.launch.json"):
        record = json.loads(marker.read_text())
        if record["state"] == "launching":
            # Parent death between Popen and recording its PID is ambiguous.
            active.append(str(marker))
        elif record["state"] == "spawned":
            try:
                process = psutil.Process(record["pid"])
                if (
                    abs(process.create_time() - record["create_time"]) < 0.01
                    and process.status() != psutil.STATUS_ZOMBIE
                ):
                    active.append(str(marker))
            except psutil.NoSuchProcess:
                pass
    return active


def memory_reason(aggregate, available, limits=LIMITS):
    if aggregate > limits["aggregate_rss_bytes"]:
        return "aggregate RSS exceeded the benchmark limit"
    if available < limits["reserve_bytes"]:
        return "system available memory fell below the reserve"
    return None


def stop_process(process):
    """The worker starts a separate session, so its process group includes descendants."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    # A descendant can survive its parent. Kill the group even after the parent exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def supervise(script, spec_path, *, limits=LIMITS):
    """Run one bounded phase, preserving partial files and a separate supervision record."""
    spec_path = Path(spec_path)
    started = time.perf_counter()
    status = {
        "status": "not_started",
        "spawned": False,
        "peak_aggregate_rss_bytes": 0,
        "peak_worker_rss_bytes": 0,
        "limits": limits,
    }
    required = limits["planned_worker_bytes"] + limits["reserve_bytes"]
    if psutil.virtual_memory().available < required:
        return {
            **status,
            "reason": "insufficient available memory to start",
            "elapsed_seconds": 0.0,
        }
    spec = json.loads(spec_path.read_text())
    spec["spawn_started"] = time.perf_counter()
    write_json(spec_path, spec)
    temporary = spec["temporary"]
    environment = {
        **os.environ,
        "TMPDIR": temporary,
        "CPL_TMPDIR": temporary,
        "DASK_TEMPORARY_DIRECTORY": temporary,
        "GDAL_CACHEMAX": "256",
        "GDAL_HTTP_MAX_RETRY": "2",
        "GDAL_HTTP_RETRY_DELAY": "1",
        "GDAL_HTTP_CONNECTTIMEOUT": "30",
        "GDAL_HTTP_TIMEOUT": "120",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }
    process = None
    parent = psutil.Process()
    with spec_path.with_suffix(".stdout.log").open("w") as output:
        try:
            marker = spec_path.with_suffix(".launch.json")
            write_json(marker, {"state": "launching"})
            process = subprocess.Popen(
                [sys.executable, str(script), "--worker", str(spec_path)],
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            status["spawned"] = True
            child = psutil.Process(process.pid)
            write_json(
                marker, {"state": "spawned", "pid": child.pid, "create_time": child.create_time()}
            )
            status["status"] = "running"
            while process.poll() is None:
                aggregate = parent.memory_info().rss
                worker = 0
                try:
                    descendants = [child, *child.children(recursive=True)]
                    for entry in descendants:
                        try:
                            worker += entry.memory_info().rss
                        except psutil.NoSuchProcess:
                            pass
                except psutil.NoSuchProcess:
                    pass
                aggregate += worker
                status["peak_worker_rss_bytes"] = max(status["peak_worker_rss_bytes"], worker)
                status["peak_aggregate_rss_bytes"] = max(
                    status["peak_aggregate_rss_bytes"], aggregate
                )
                reason = memory_reason(aggregate, psutil.virtual_memory().available, limits)
                if reason:
                    status.update(status="memory_stopped", reason=reason)
                    stop_process(process)
                    break
                time.sleep(limits["poll_seconds"])
            if status["status"] == "running":
                status["status"] = "complete" if process.returncode == 0 else "failed"
            status["returncode"] = process.returncode
        except BaseException:
            if process is not None:
                stop_process(process)
            elif "marker" in locals():
                write_json(marker, {"state": "not_spawned"})
            status["status"] = "interrupted"
            raise
        finally:
            status["elapsed_seconds"] = time.perf_counter() - started
            write_json(spec_path.with_suffix(".supervision.json"), status)
    return status
