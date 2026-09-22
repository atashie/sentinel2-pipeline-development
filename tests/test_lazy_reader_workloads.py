"""Local synthetic coverage for the bounded workload experiment. No provider requests."""

import copy
import dataclasses
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import Polygon, box
from test_lake_extraction import BANDS, GRID, X0, Y0, feature, make_item, write_band

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools")]

import build_workload_manifests as selection  # noqa: E402
import lazy_reader_workloads as runner  # noqa: E402
import workload_readers as readers  # noqa: E402

from s2proto import masks  # noqa: E402
from s2proto import workload_resources as resources  # noqa: E402


@pytest.fixture(autouse=True)
def stable_host_memory(monkeypatch):
    # These small fixture tests exercise reader correctness, independent of other
    # applications. Guard tests below inject low-memory conditions explicitly.
    current = resources.psutil.virtual_memory()
    monkeypatch.setattr(
        resources.psutil, "virtual_memory", lambda: current._replace(available=16 * 1024**3)
    )


@pytest.fixture
def input_workload(tmp_path):
    lakes = [
        feature("one", box(X0 + 110, Y0 - 375, X0 + 360, Y0 - 105), 100),
        feature("two", box(X0 + 115, Y0 - 355, X0 + 300, Y0 - 115), 100),
        feature("empty", box(X0 + 2499, Y0 - 355, X0 + 2510, Y0 - 115), 10),
    ]
    manifest = {"cohort": "fixture", "lakes": []}
    for lake in lakes:
        lid = lake["properties"]["water_body_id"]
        path = tmp_path / f"{lid}.json"
        path.write_text(json.dumps(lake))
        manifest["lakes"].append(
            {
                "id": lid,
                "path": str(path),
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    scenes, arrays = [], {}
    for number in range(2):
        directory = tmp_path / f"product-{number}"
        directory.mkdir()
        for index, (band, resolution) in enumerate(BANDS.items()):
            arrays[number, band] = write_band(
                directory / f"{band}.tif",
                resolution,
                index + 1 + number,
                "uint8" if band == "scl" else "uint16",
            )
        item = make_item(directory)
        item["id"] = f"product-{number}"
        _, assets = runner.previous.native_assets(item, list(BANDS))
        scenes.append(
            {
                "item": item,
                "grid": dataclasses.asdict(GRID),
                "assets": assets,
                "members": [entry["id"] for entry in manifest["lakes"]],
            }
        )
    plan = {"scenes": scenes}
    readers.read_headers(plan, tmp_path)
    selected, expected = tmp_path / "selections.sqlite", tmp_path / "expected.sqlite"
    summary = readers.prepare_selections(plan, manifest, selected, expected)
    return plan, selected, expected, summary, arrays


def test_all_seven_readers_match_complete_native_outputs(input_workload, tmp_path, monkeypatch):
    from pystac.stac_io import DefaultStacIO

    def reject_catalog(*args, **kwargs):
        raise AssertionError("frozen extraction attempted live catalog resolution")

    monkeypatch.setattr(DefaultStacIO, "read_text", reject_catalog)
    plan, selected, expected, summary, arrays = input_workload
    for scene in plan["scenes"]:
        scene["item"]["links"] = [
            {"rel": rel, "href": f"https://catalog.invalid/{rel}", "type": "application/json"}
            for rel in ("root", "parent", "collection", "self")
        ]
    reference = None
    results = {}
    selection_digest = runner.file_digest(selected)
    for name in readers.CONFIGURATIONS:
        output = tmp_path / f"{name}.sqlite"
        with readers.gdal_log(tmp_path / f"{name}.log"):
            results[name] = readers.Extractor(plan, selected, output, name).run()
        report = readers.validate(expected, output, reference)
        assert report["complete"]
        assert report["value_differences"] in (None, 0)
        assert report["selected_pixel_entries"] == summary["selected_pixel_entries"]
        reference = reference or output
    assert runner.file_digest(selected) == selection_digest
    assert len({result["output_database"]["checkpoints"] for result in results.values()}) == 1
    distinct_blocks = sum(row["distinct_blocks"] for row in summary["block_coverage"])
    assert results["B-lazy"]["read_units"] == distinct_blocks
    assert results["A-lazy"]["read_units"] > distinct_blocks
    # Independently check signatures against known fixture pixels, including nodata.
    selections = sqlite3.connect(selected)
    actual = sqlite3.connect(reference)
    for scene in plan["scenes"]:
        number = int(scene["item"]["id"].split("-")[-1])
        for asset in scene["assets"]:
            for lid, br, bc, count, blob in selections.execute(
                "SELECT lake,br,bc,n,blob FROM selections WHERE grid=?",
                (asset["selection_grid"],),
            ):
                window = readers.block_window(br, bc, asset["shape"], asset["block_shape"])
                positions, _ = readers.unpack_selection(blob, count)
                values = readers.subarray(arrays[number, asset["key"]], window).reshape(-1)[
                    positions
                ]
                expected_hash = hashlib.sha256(values.tobytes()).hexdigest()
                measured = actual.execute(
                    "SELECT vsha FROM actual WHERE item=? AND band=? AND lake=? AND br=? AND bc=?",
                    (scene["item"]["id"], asset["key"], lid, br, bc),
                ).fetchone()[0]
                assert measured == expected_hash


@pytest.mark.parametrize("resolution", [10, 20, 60])
def test_block_halo_preserves_existing_classes(resolution):
    exterior = box(X0 - 100, Y0 - 550, X0 + 705, Y0 + 200)
    hole = box(X0 + 120, Y0 - 350, X0 + 285, Y0 - 115)
    polygon = Polygon(exterior.exterior.coords, [hole.exterior.coords])
    canonical = masks.compute_mask(polygon, GRID, resolution)
    height, width = GRID.shape(resolution)
    rebuilt = np.zeros((height, width), dtype=np.uint8)
    for row in range(0, height, 16):
        for col in range(0, width, 16):
            window = readers.block_window(row // 16, col // 16, (height, width), (16, 16))
            positions, classes = readers.selection_block(polygon, GRID, resolution, window)
            rr, cc = np.divmod(positions, int(window.width))
            rebuilt[rr + row, cc + col] = classes
    expected = np.zeros_like(rebuilt)
    w = canonical.window
    expected[w.row_off : w.row_off + w.height, w.col_off : w.col_off + w.width] = (
        canonical.pixel_class
    )
    np.testing.assert_array_equal(rebuilt, expected)


def test_equal_partial_results_are_incomplete(input_workload, tmp_path):
    plan, selected, expected, _, _ = input_workload
    output = tmp_path / "partial.sqlite"
    extractor = readers.Extractor(plan, selected, output, "B-raster")
    extractor.selected.close()
    extractor.output.close()
    report = readers.validate(expected, output, output)
    assert not report["complete"]
    assert report["value_differences"] == 0
    assert report["missing_blocks"] > 0
    assert report["missing_contributions"] == 30


def test_duplicate_signature_is_rejected(input_workload, tmp_path):
    plan, selected, _, _, _ = input_workload
    output = tmp_path / "duplicate.sqlite"
    extractor = readers.Extractor(plan, selected, output, "B-raster")
    scene, asset = plan["scenes"][0], plan["scenes"][0]["assets"][0]
    extractor.raster_asset(scene, asset, ["one"])
    with pytest.raises(sqlite3.IntegrityError):
        extractor.raster_asset(scene, asset, ["one"])


def test_changed_native_grid_is_refused(input_workload):
    plan, _, _, _, _ = input_workload
    scene = copy.deepcopy(plan["scenes"][0])
    scene["grid"]["x0"] += 10
    with pytest.raises(ValueError, match="grid differ"):
        readers.native_array(scene, scene["assets"][0], 16)


def test_allocation_checks_before_any_large_array(monkeypatch):
    monkeypatch.setattr(
        resources.psutil,
        "Process",
        lambda: SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=100)),
    )
    monkeypatch.setattr(resources.psutil, "virtual_memory", lambda: SimpleNamespace(available=500))
    limits = {"planned_worker_bytes": 300, "active_arrays_bytes": 100, "reserve_bytes": 250}
    resources.admit(100, active_arrays_bytes=50, limits=limits)
    with pytest.raises(MemoryError, match="footprint"):
        resources.admit(201, limits=limits)
    with pytest.raises(MemoryError, match="active arrays"):
        resources.admit(1, active_arrays_bytes=101, limits=limits)
    limits["planned_worker_bytes"] = 1000
    with pytest.raises(MemoryError, match="reserve"):
        resources.admit(251, limits=limits)
    assert resources.memory_reason(401, 500, {"aggregate_rss_bytes": 400, "reserve_bytes": 250})
    assert resources.memory_reason(100, 249, {"aggregate_rss_bytes": 400, "reserve_bytes": 250})


def test_cleanup_does_not_follow_symlinks(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.tif").write_bytes(b"unrelated imagery")
    workspace = resources.create_workspace(run)
    (workspace / "discard.tif").write_bytes(b"owned imagery")
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    audit = resources.clean_workspace(run)
    assert audit["remaining_files"] == []
    assert (outside / "keep.tif").exists()
    workspace.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="escapes"):
        resources.clean_workspace(run)


def test_unowned_workspace_is_preserved(tmp_path):
    workspace = tmp_path / "temporary-images"
    workspace.mkdir()
    (workspace / "owner.json").write_text('{"owner":"someone else"}')
    with pytest.raises(ValueError, match="not owned"):
        resources.clean_workspace(tmp_path)
    assert workspace.exists()


def test_area_selection_discloses_shortages_and_is_deterministic():
    assert selection.quotas({"small": 1000, "medium": 200, "large": 10}, 1000) == {
        "small": 790,
        "medium": 200,
        "large": 10,
    }
    with pytest.raises(ValueError, match="insufficient"):
        selection.quotas({"small": 1}, 2)
    assert selection.area_band(10_000_000) == "large"
    assert selection.stable_key("lake") == selection.stable_key("lake")


def test_repeated_ranges_are_not_labeled_delivered_bytes(tmp_path):
    log = tmp_path / "gdal.log"
    log.write_text("VSICURL: Downloading 0-99 (https://example.test/band.tif)\n" * 2)
    counters = runner.io_summary(log, tmp_path / "ranges.sqlite")
    assert counters["bytes_requested"] == 200
    assert counters["repeated_exact_ranges"] == 1
    assert counters["delivered_bytes"] is None


def test_supervisor_stops_a_real_worker_and_descendant(tmp_path):
    import psutil

    script = tmp_path / "worker.py"
    script.write_text(
        "import subprocess,sys,time\n"
        "child=subprocess.Popen([sys.executable,'-c',"
        "'import time; a=bytearray(32*1024**2); time.sleep(20)'])\n"
        "print(child.pid,flush=True)\n"
        "a=bytearray(32*1024**2)\n"
        "time.sleep(20)\n"
    )
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"temporary": str(tmp_path)}))
    limits = {
        **resources.LIMITS,
        "planned_worker_bytes": 64 * 1024**2,
        "reserve_bytes": 0,
        "aggregate_rss_bytes": psutil.Process().memory_info().rss + 45 * 1024**2,
    }
    result = resources.supervise(script, spec, limits=limits)
    assert result["status"] == "memory_stopped"
    assert result["elapsed_seconds"] < 10
    child_id = int(spec.with_suffix(".stdout.log").read_text().strip())
    try:
        child = psutil.Process(child_id)
        assert child.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


def test_raw_value_mismatch_is_not_accepted(input_workload, tmp_path):
    plan, selected, expected, _, _ = input_workload
    first, second = tmp_path / "first.sqlite", tmp_path / "second.sqlite"
    readers.Extractor(plan, selected, first, "B-raster").run()
    import shutil

    shutil.copyfile(first, second)
    db = sqlite3.connect(second)
    db.execute("UPDATE actual SET vsha='wrong' WHERE rowid=1")
    db.commit()
    db.close()
    report = readers.validate(expected, second, first)
    assert report["complete"]
    assert report["value_differences"] == 2


@pytest.mark.parametrize("unconverged", [False, True])
def test_streaming_catalog_selection_retains_datastrips(
    input_workload, tmp_path, monkeypatch, unconverged
):
    select_region = runner.previous.select_region

    def select(*args, **kwargs):
        result = select_region(*args, **kwargs)
        if unconverged:
            for group in result["groups"]:
                for row in group["coverage"].values():
                    row["geometry_check"]["converged"] = False
        return result

    monkeypatch.setattr(runner.previous, "select_region", select)
    plan, _, _, _, _ = input_workload
    entries, item_paths = [], {}
    for lid in ("one", "two"):
        path = tmp_path / f"{lid}.json"
        entries.append({"id": lid, "path": str(path), "file_sha256": runner.file_digest(path)})
    for index, scene in enumerate(plan["scenes"]):
        item = copy.deepcopy(scene["item"])
        item["properties"].update(
            {
                "s2:datatake_id": "same-acquisition",
                "s2:datastrip_id": f"strip-{index}",
                "platform": "sentinel-2b",
            }
        )
        path = tmp_path / f"catalog-item-{index}.json"
        path.write_text(json.dumps(item))
        item_paths[item["id"]] = str(path)
    manifest = {"cohort": "dispersed", "lakes": entries}
    snapshot = {
        "items": item_paths,
        "groups": [{"items": list(item_paths), "lakes": ["one", "two"]}],
    }
    result = runner.freeze(manifest, snapshot, tmp_path)
    frozen = json.loads((tmp_path / "selected-plan.json").read_text())
    assert result["products"] == 2
    assert all(scene["members"] == ["one", "two"] for scene in frozen["scenes"])
    assert {scene["group"] for scene in frozen["scenes"]} == {"same-acquisition"}
    assert frozen["order"] == readers.CONFIGURATIONS
    assert frozen["source_digests"] == runner.source_digests()
    assert len(frozen["unconverged_geometry"]) == (2 if unconverged else 0)
    assert result["unconverged_geometry"] == frozen["unconverged_geometry"]


def test_one_complete_configuration_cannot_establish_reader_agreement(input_workload, tmp_path):
    plan, selected, _, _, _ = input_workload
    readers.Extractor(plan, selected, tmp_path / "A-raster.sqlite", "A-raster").run()
    (tmp_path / "extract-A-raster.supervision.json").write_text('{"status":"complete"}')
    result = runner.finalize_cohort(tmp_path)
    assert result[0]["status"] == "complete"
    assert not result[0]["matches_all_complete_outputs"]


def test_acquisition_split_keeps_each_lake_complete_and_assigned_once():
    score = [0, 10, "2025-06-01T12:00:00Z"]
    eligible = {
        "a": {"west": score},
        "b": {"west": score, "east": score},
        "c": {"east": [0, 20, score[2]]},
    }
    assignments = runner.assign_acquisitions(eligible)
    assert [(a["datatake"], a["lakes"]) for a in assignments] == [
        ("west", ["a", "b"]),
        ("east", ["c"]),
    ]
    with pytest.raises(ValueError, match="no complete acquisition"):
        runner.assign_acquisitions({"no-coverage": {}})


def test_large_identifier_queries_subdivide_and_record_shortages(tmp_path, monkeypatch):
    import urllib.parse

    class Client:
        directory = tmp_path
        fail_right = False

        def request(self, url):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            bbox = list(map(float, query["geometry"][0].split(",")))
            if self.fail_right and bbox[0] >= 2:
                raise OSError("fixture service unavailable")
            ids = [value for value in range(1, 5) if bbox[0] <= value <= bbox[2]]
            if "returnCountOnly" in query:
                return {"count": len(ids)}
            assert len(ids) <= 2
            return {"objectIds": ids}

    monkeypatch.setattr(selection, "IDENTIFIER_BATCH", 2)
    client = Client()
    audit = {}
    actual = list(selection.candidate_ids(client, [0, 0, 4, 1], "small", limit=2, audit=audit))
    assert actual == sorted(range(1, 5), key=selection.stable_key)[:2]
    assert audit["available_ids"] == 4 and audit["complete"]
    assert audit["queries"][0]["subdivided"]
    client.fail_right = True
    assert set(selection.candidate_ids(client, [0, 0, 4, 1], "small", audit=audit)) == {1, 2}
    assert not audit["complete"] and audit["shortages"]


def test_unstarted_extraction_resumes_but_started_extraction_never_repeats(tmp_path, monkeypatch):
    temporary = resources.create_workspace(tmp_path)
    calls = []

    def supervise(script, spec_path):
        calls.append(spec_path)
        if len(calls) == 1:
            return {"status": "not_started", "spawned": False}
        return {"status": "failed", "spawned": True}

    monkeypatch.setattr(runner, "supervise", supervise)
    kwargs = {"configuration": "A-raster"}
    assert (
        runner.run_phase(tmp_path, "dispersed", "extract", temporary, **kwargs)["status"]
        == "not_started"
    )
    assert (
        runner.run_phase(tmp_path, "dispersed", "extract", temporary, **kwargs)["status"]
        == "failed"
    )
    assert runner.run_phase(tmp_path, "dispersed", "extract", temporary, **kwargs)[
        "skipped_attempted"
    ]
    assert len(calls) == 2
    spec = tmp_path / "dispersed/extract-A-raster.json"
    assert json.loads(spec.read_text())["selections"] == str(
        tmp_path / "dispersed/selections.sqlite"
    )
    resources.clean_workspace(tmp_path)


def test_completed_preparation_requires_unchanged_artifacts(tmp_path):
    spec = tmp_path / "prepare.json"
    saved = tmp_path / "selections.sqlite"
    saved.write_bytes(b"geometry only")
    spec.with_suffix(".supervision.json").write_text('{"status":"complete"}')
    spec.with_suffix(".result.json").write_text(
        json.dumps({"status": "complete", "artifacts": {saved.name: runner.file_digest(saved)}})
    )
    assert runner.phase_complete(spec)
    saved.write_bytes(b"changed positions")
    with pytest.raises(ValueError, match="artifact changed"):
        runner.phase_complete(spec)


def test_preflight_command_never_extracts_and_keeps_geometry(tmp_path, monkeypatch):
    run = tmp_path / "run"
    phases = []

    def phase(directory, cohort, phase, temporary, **kwargs):
        assert phase != "extract"
        phases.append((cohort, phase))
        target = directory / cohort
        target.mkdir(exist_ok=True)
        (target / "selections.sqlite").write_bytes(b"geometry only")
        return {"status": "complete"}

    monkeypatch.setattr(runner, "run_phase", phase)
    monkeypatch.setattr(
        runner,
        "preflight",
        lambda directory: {
            "transfer_estimates": {"total_requested_bytes_range": [1, 2], "configurations": []}
        },
    )
    assert runner.execute(run)["status"] == "preflight_complete"
    assert len(phases) == 8
    assert not (run / "temporary-images").exists()
    assert (run / "dispersed/selections.sqlite").exists()


def test_preflight_estimates_all_seven_with_explicit_proxy_limits(input_workload):
    plan, _, _, _, _ = input_workload
    plan["bands"] = runner.BANDS
    estimates = runner.transfer_estimates(plan)
    assert len(estimates["configurations"]) == 7
    assert estimates["all_configurations_estimated"]
    assert estimates["total_requested_bytes_range"][0] > 0
    assert not estimates["compatible_measurement"]
    improved = next(row for row in estimates["configurations"] if row["configuration"] == "B-lazy")
    assert improved["optimized_reader_proxy"]
    assert improved["reference_reader"] == "raster-mask"


def test_chunk_grid_mismatch_is_rejected_before_compute(input_workload, monkeypatch):
    plan, _, _, _, _ = input_workload
    real = readers.old.load_native_item

    def shifted(*args, **kwargs):
        return real(*args, **kwargs).chunk({"x": 17, "y": 17})

    monkeypatch.setattr(readers.old, "load_native_item", shifted)
    scene = plan["scenes"][0]
    with pytest.raises(ValueError, match="chunk grid differs"):
        readers.native_array(scene, scene["assets"][0], 16)


def test_different_complete_outputs_do_not_designate_one_reader_correct(input_workload, tmp_path):
    import shutil

    plan, selected, _, _, _ = input_workload
    first = tmp_path / "A-raster.sqlite"
    second = tmp_path / "A-lazy.sqlite"
    readers.Extractor(plan, selected, first, "A-raster").run()
    shutil.copyfile(first, second)
    db = sqlite3.connect(second)
    db.execute("UPDATE actual SET vsha='different' WHERE rowid=1")
    db.commit()
    db.close()
    for name in ("A-raster", "A-lazy"):
        (tmp_path / f"extract-{name}.supervision.json").write_text('{"status":"complete"}')
    result = runner.finalize_cohort(tmp_path)
    assert [row["status"] for row in result[:2]] == ["differs", "differs"]
    assert not any(row.get("matches_all_complete_outputs") for row in result)


def test_extract_stops_at_startup_refusal_then_resumes_remaining_configs(tmp_path, monkeypatch):
    run = tmp_path / "run"
    with runner.run_session(run, create=True):
        pass
    runner.write_json(
        run / "preflight.json",
        {
            "status": "preflight_complete",
            "cohorts": {
                cohort: {"preflight": {"plan_sha256": cohort}}
                for cohort in ("dispersed", "florida")
            },
        },
    )
    monkeypatch.setattr(runner, "RESULT", tmp_path / "result.json")
    monkeypatch.setattr(
        runner,
        "verify_frozen",
        lambda directory: {"sha256": directory.name, "order": readers.CONFIGURATIONS},
    )
    calls = []
    refused = False

    def supervise(script, path):
        nonlocal refused
        spec = json.loads(path.read_text())
        if spec["phase"] == "validate":
            runner.write_json(path.parent / "comparisons.json", [])
            return {"status": "complete", "spawned": True}
        key = (spec["cohort"], spec["configuration"])
        calls.append(key)
        if key == ("dispersed", "A-lazy") and not refused:
            refused = True
            return {"status": "not_started", "spawned": False}
        return {"status": "complete", "spawned": True}

    monkeypatch.setattr(runner, "supervise", supervise)
    first = runner.extract(run)
    assert first["paused_before"] == "dispersed/A-lazy"
    assert calls == [("dispersed", "A-raster"), ("dispersed", "A-lazy")]
    runner.extract(run)
    assert len(calls) == 15  # Fourteen launches and one startup refusal.
    assert calls.count(("dispersed", "A-raster")) == 1
    assert calls.count(("dispersed", "A-lazy")) == 2
    assert not (run / "temporary-images").exists()


def test_launch_intent_blocks_duplicate_extraction_and_cleanup(tmp_path):
    cohort = tmp_path / "dispersed"
    cohort.mkdir()
    spec = cohort / "extract-A-raster.json"
    spec.with_suffix(".launch.json").write_text('{"state":"launching"}')
    assert runner.extraction_attempted(spec)
    assert resources.active_workers(tmp_path) == [str(spec.with_suffix(".launch.json"))]


def test_metadata_requests_are_paced(tmp_path, monkeypatch):
    import io

    class Response(io.BytesIO):
        status = 200

    clock = [100.0]
    pauses = []

    def sleep(seconds):
        pauses.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(selection.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(selection.time, "sleep", sleep)
    monkeypatch.setattr(
        selection.urllib.request, "urlopen", lambda *a, **k: Response(b'{"count":0}')
    )
    client = selection.MetadataClient(tmp_path)
    client.request("https://fixture.invalid/one")
    client.request("https://fixture.invalid/two")
    assert pauses == [0.0, 0.2]


@pytest.fixture
def old_source_run(tmp_path, monkeypatch):
    run = tmp_path / "run"
    old = {"fixture.py": "old"}
    monkeypatch.setattr(runner, "source_digests", lambda: old)
    with runner.run_session(run, create=True):
        pass
    for cohort in ("dispersed", "florida"):
        directory = run / cohort
        directory.mkdir()
        (directory / "selections.sqlite").write_bytes(b"fixed selections")
        (directory / "expected.sqlite").write_bytes(b"fixed expected output")
        plan = {
            "source_digests": old,
            "selection_sha256": runner.file_digest(directory / "selections.sqlite"),
            "expected_sha256": runner.file_digest(directory / "expected.sqlite"),
        }
        runner.write_json(directory / "selected-plan.json", plan)
        runner.write_json(directory / "frozen-plan.json", {**plan, "sha256": readers.digest(plan)})
        for phase, artifact in (
            ("boundaries", "manifest.json"),
            ("catalog", "catalog.json"),
            ("freeze", "selected-plan.json"),
            ("prepare", "frozen-plan.json"),
        ):
            if phase in ("boundaries", "catalog"):
                runner.write_json(directory / artifact, {"fixed_input": phase})
            runner.write_json(directory / f"{phase}.json", {"phase": phase})
            runner.write_json(directory / f"{phase}.supervision.json", {"status": "complete"})
            runner.write_json(
                directory / f"{phase}.result.json",
                {
                    "status": "complete",
                    "artifacts": {artifact: runner.file_digest(directory / artifact)},
                },
            )
    monkeypatch.setattr(runner, "source_digests", lambda: {"fixture.py": "new"})
    return run


def test_source_change_requires_explicit_reason_and_archives_old_preparation(old_source_run):
    run = old_source_run
    with (
        pytest.raises(ValueError, match="source version differs"),
        runner.run_session(run, create=True),
    ):
        pass
    before = {p: p.read_bytes() for p in run.glob("*/catalog*") if p.is_file()}
    with runner.run_session(
        run, create=True, accept_source_change="owner-approved geometry diagnostic"
    ):
        pass
    saved = json.loads((run / "run.json").read_text())
    assert saved["source_digests"] == {"fixture.py": "new"}
    assert len(saved["source_history"]) == 1
    entry = saved["source_history"][0]
    assert entry["previous_digests"] == {"fixture.py": "old"}
    assert entry["changed_files"] == ["fixture.py"]
    archive = run / entry["archive"]
    for cohort in ("dispersed", "florida"):
        assert runner.phase_complete(run / cohort / "boundaries.json")
        assert runner.phase_complete(run / cohort / "catalog.json")
        assert not runner.phase_complete(run / cohort / "freeze.json")
        assert not (run / cohort / "frozen-plan.json").exists()
        assert (archive / cohort / "selections.sqlite").read_bytes() == b"fixed selections"
        runner.verify_frozen(archive / cohort, expected_sources={"fixture.py": "old"})
    assert all(p.read_bytes() == contents for p, contents in before.items())
    assert len(entry["phase_archives"]) == 4
    assert not (run / "source-change.pending.json").exists()
    with runner.run_session(run, create=True, accept_source_change="repeat same command"):
        pass
    assert len(json.loads((run / "run.json").read_text())["source_history"]) == 1


def test_source_change_rejects_extraction_launch_even_when_archived(old_source_run):
    run = old_source_run
    marker = run / "dispersed/phase-history/extract-A-raster/0001/extract-A-raster.launch.json"
    runner.write_json(marker, {"state": "not_spawned"})
    with (
        pytest.raises(ValueError, match="extraction launch"),
        runner.run_session(run, create=True, accept_source_change="must refuse"),
    ):
        pass
    assert not (run / "source-history").exists()


def test_source_change_rejects_inconsistent_recorded_version(old_source_run):
    run = old_source_run
    identity = json.loads((run / "run.json").read_text())
    identity["source_digests"] = {"fixture.py": "unrelated"}
    runner.write_json(run / "run.json", identity)
    with (
        pytest.raises(ValueError, match="recorded source digests"),
        runner.run_session(run, create=True, accept_source_change="must refuse"),
    ):
        pass
    assert not (run / "source-history").exists()


def test_interrupted_source_transition_blocks_resume_and_extraction(old_source_run):
    run = old_source_run
    runner.write_json(run / "source-change.pending.json", {"reason": "interrupted"})
    with (
        pytest.raises(ValueError, match="incomplete source transition"),
        runner.run_session(run, create=True, accept_source_change="must refuse"),
    ):
        pass
    with (
        pytest.raises(ValueError, match="incomplete source transition"),
        runner.run_session(run, create=False),
    ):
        pass
