"""Measurement harness for prototype runs. Standard library plus psutil.

Every prototype measurement reports wall time, CPU time, peak memory, bytes and requests,
pixels read, and output bytes, with the machine and the code version. Scripts under
benchmarks/ use it. Nothing here contacts a provider on its own.
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import re
import resource
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "sentinel2-pipeline-development prototype (owner-invoked)"
GDAL_DOWNLOAD = re.compile(r"VSICURL: Downloading (\S+?) \(")
GDAL_FILESIZE = re.compile(r"VSICURL: GetFileSize\(")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def code_version() -> str:
    """Short git hash of HEAD, with -dirty when the working tree has changes."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=ROOT,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT
        )
        return head + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256_bytes(data: bytes | memoryview) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_maxrss(value: int, system: str) -> int:
    """ru_maxrss in bytes. Darwin reports bytes, Linux reports kilobytes."""
    return value if system == "Darwin" else value * 1024


def peak_rss_bytes() -> int:
    """Peak resident set size of this process since it started."""
    return normalize_maxrss(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, platform.system())


def cpu_seconds() -> dict[str, float]:
    times = os.times()
    return {"user": times.user, "system": times.system}


def cpu_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {key: round(after[key] - before[key], 3) for key in ("user", "system")}


def net_counters() -> dict[str, int] | None:
    """Machine-wide network counters, all processes. None when psutil cannot read them."""
    try:
        import psutil

        counters = psutil.net_io_counters()
        return {"bytes_recv": counters.bytes_recv, "bytes_sent": counters.bytes_sent}
    except Exception:
        return None


def net_delta(before: dict | None, after: dict | None) -> dict[str, int] | None:
    if before is None or after is None:
        return None
    return {key: after[key] - before[key] for key in ("bytes_recv", "bytes_sent")}


def machine_info() -> dict:
    """The machine a measurement ran on, and the library versions that read the data."""
    info: dict = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "memory_total_bytes": None,
        "libraries": {},
    }
    try:
        import psutil

        info["memory_total_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass
    for name in ("rasterio", "numpy"):
        try:
            info["libraries"][name] = __import__(name).__version__
        except Exception:
            info["libraries"][name] = None
    try:
        import rasterio

        info["libraries"]["gdal"] = rasterio.__gdal_version__
    except Exception:
        info["libraries"]["gdal"] = None
    return info


class Timer:
    """Wall-clock seconds for a with-block."""

    def __enter__(self):
        self.start = time.perf_counter()
        self.seconds = 0.0
        return self

    def __exit__(self, *exc):
        self.seconds = round(time.perf_counter() - self.start, 4)
        return False


def parse_gdal_log(lines) -> dict[str, int]:
    """Requests and bytes from GDAL's VSICURL debug messages.

    GDAL logs the byte ranges it asks for, so the total is bytes requested, which can differ
    from bytes delivered. Size probes are counted separately.
    """
    requests = total = size_requests = 0
    for line in lines:
        found = GDAL_DOWNLOAD.search(line)
        if found:
            requests += 1
            for part in found.group(1).split(","):
                start, _, end = part.partition("-")
                if start.isdigit() and end.isdigit():
                    total += int(end) - int(start) + 1
        elif GDAL_FILESIZE.search(line):
            size_requests += 1
    return {"requests": requests, "bytes": total, "size_requests": size_requests}


class _ListHandler(logging.Handler):
    def __init__(self, sink: list[str]):
        super().__init__(logging.DEBUG)
        self.sink = sink

    def emit(self, record):
        self.sink.append(record.getMessage())


class GdalLogCapture:
    """Collect the GDAL debug messages rasterio forwards to its logger.

    Use inside rasterio.Env(CPL_DEBUG=True). take() returns and clears the lines so far.
    """

    def __init__(self):
        self.lines: list[str] = []
        self.all_lines: list[str] = []
        self._logger = logging.getLogger("rasterio")
        self._handler = _ListHandler(self.lines)
        self._level = self._logger.level

    def __enter__(self):
        self._level = self._logger.level
        self._logger.setLevel(logging.DEBUG)
        self._logger.addHandler(self._handler)
        return self

    def __exit__(self, *exc):
        self._logger.removeHandler(self._handler)
        self._logger.setLevel(self._level)
        return False

    def take(self) -> list[str]:
        lines = list(self.lines)
        self.all_lines.extend(lines)
        self.lines.clear()
        return lines


class Client:
    """HTTP client that logs every request with host, status, bytes, and seconds."""

    def __init__(self, pause: float = 0.2, retries: int = 4, timeout: float = 300.0):
        self.pause = pause
        self.retries = retries
        self.timeout = timeout
        self.log: list[dict] = []

    def _request(self, url: str, body: bytes | None, note: str, accept: str) -> tuple:
        host = urllib.parse.urlparse(url).netloc
        headers = {"accept": accept, "user-agent": USER_AGENT}
        if body is not None:
            headers["content-type"] = "application/json"
        delay = 2.0
        for attempt in range(1, self.retries + 1):
            request = urllib.request.Request(url, data=body, headers=headers)
            started = time.perf_counter()
            status, raw, error, response_headers = None, b"", None, {}
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    status = response.status
                    response_headers = {k.lower(): v for k, v in response.headers.items()}
            except urllib.error.HTTPError as caught:
                status, raw, error = caught.code, caught.read(), caught
            except (urllib.error.URLError, TimeoutError) as caught:
                error = caught
            seconds = round(time.perf_counter() - started, 3)
            self.log.append(
                {
                    "host": host,
                    "method": "POST" if body is not None else "GET",
                    "path": url[len(f"https://{host}") :],
                    "note": note,
                    "status": status,
                    "bytes": len(raw),
                    "seconds": seconds,
                    "attempt": attempt,
                }
            )
            if error is None:
                if self.pause:
                    time.sleep(self.pause)
                return raw, status, response_headers, seconds
            retryable = status is None or status in (408, 429, 500, 502, 503, 504)
            if retryable and attempt < self.retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"{status} from {url}: {raw[:300]!r}") from error
        raise RuntimeError("unreachable")

    def get_json(self, url: str, note: str = "") -> dict:
        import json

        raw, _, _, _ = self._request(url, None, note, "application/json")
        return json.loads(raw)

    def post_json(self, url: str, body: dict, note: str = "") -> dict:
        import json

        raw, _, _, _ = self._request(url, json.dumps(body).encode(), note, "application/json")
        return json.loads(raw)

    def get_bytes(self, url: str, note: str = "") -> tuple[bytes, dict]:
        """One GET of a whole object. Returns the bytes and what the response said."""
        raw, status, headers, seconds = self._request(url, None, note, "*/*")
        meta = {
            "status": status,
            "bytes": len(raw),
            "seconds": seconds,
            "content_length": headers.get("content-length"),
            "etag": headers.get("etag"),
            "request_charged": headers.get("x-amz-request-charged"),
        }
        return raw, meta
