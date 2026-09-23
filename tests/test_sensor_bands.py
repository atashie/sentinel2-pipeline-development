"""The sensor band comparison binds only checked records, and the page renders every bound band.

Fixture tests exercise the collator and the renderer offline. Dataset tests read the committed
records. No network.
"""

import importlib.util
import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATASET = DOCS / "sensor-bands.json"
RESEARCH = DOCS / "assessment-checks" / "sensor-bands-research.json"
CHECKS = DOCS / "assessment-checks" / "sensor-bands-checks.json"
PAGE = DOCS / "s2-options.html"
SENSOR_IDS = [
    "sentinel-2-msi",
    "landsat-9-oli-tirs",
    "sentinel-3-olci",
    "sentinel-3-slstr",
    "modis",
    "planetscope",
]
USE_IDS = ["chlorophyll", "turbidity", "cdom", "temperature", "correction", "extent"]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collate_sensor_bands = load_module("collate_sensor_bands")
render_options = load_module("render_options")


S = "src-paper"


def use(use_id, source=S, basis="named"):
    return {"use": use_id, "basis": basis, "source_ids": [source], "quote": "q", "locator": "l"}


def fixture_research():
    return {
        "topic": "sensor-bands",
        "purpose": "Fixture.",
        "researcher": {"agent": "r", "model": "m", "started_at": "t", "finished_at": "t"},
        "sources": [
            {"id": "src-agency", "url": "https://a", "title": "Agency | Site", "publisher": "A"},
            {"id": "src-paper", "url": "https://p", "title": "Paper", "publisher": "P"},
            {"id": "src-unused", "url": "https://u", "title": "Unused", "publisher": "U"},
        ],
        "uses": [
            {"id": "chlorophyll", "label": "Chlorophyll", "definition": "d", "source_ids": [S]},
            {"id": "turbidity", "label": "Turbidity", "definition": "d", "source_ids": [S]},
        ],
        "sensors": [
            {
                "id": "alpha",
                "label": "Alpha",
                "platform": "Alpha-1 and Alpha-2",
                "instrument": "AI",
                "operator": "Agency",
                "access": "public",
                "wavelength_form": "center-width",
                "notes": ["Main values are Alpha-1."],
                "source_ids": ["src-agency"],
                "bands": [
                    {
                        "id": "B1",
                        "name": "Blue",
                        "center_nm": 492.4,
                        "width_nm": 66,
                        "range_nm": None,
                        "resolution_m": 10,
                        "variants": {"Alpha-2": {"center_nm": 492.1, "width_nm": 66}},
                        "note": None,
                        "uses": [use("chlorophyll"), use("turbidity")],
                    },
                    {
                        "id": "B2",
                        "name": "Red",
                        "center_nm": 665,
                        "width_nm": 30,
                        "range_nm": None,
                        "resolution_m": 10,
                        "variants": {"Alpha-2": {"center_nm": 664.9, "width_nm": 32}},
                        "note": "Absent from the surface product.",
                        "uses": [use("chlorophyll", basis="wavelength")],
                    },
                    {
                        "id": "B3",
                        "name": "Cirrus",
                        "center_nm": 1373,
                        "width_nm": 30,
                        "range_nm": None,
                        "resolution_m": 60,
                        "variants": None,
                        "note": None,
                        "uses": [],
                    },
                ],
            },
            {
                "id": "beta",
                "label": "Beta",
                "platform": "Beta",
                "instrument": "BI",
                "operator": "Company",
                "access": "commercial",
                "wavelength_form": "range",
                "notes": [],
                "source_ids": ["src-agency"],
                "bands": [
                    {
                        "id": "1",
                        "name": "Thermal",
                        "center_nm": None,
                        "width_nm": None,
                        "range_nm": [10600, 11190],
                        "resolution_m": 1000,
                        "variants": None,
                        "note": None,
                        "uses": [],
                    }
                ],
            },
        ],
        "limitations": ["research limit"],
    }


def check(claim_id, verdict, approved=None, reason="r"):
    record = {
        "id": f"chk-{claim_id}",
        "claim_id": claim_id,
        "verdict": verdict,
        "reason": reason,
        "checked_on": "2026-09-17",
    }
    if approved is not None:
        record["approved"] = approved
    return record


def band_values(band, **changes):
    fields = ("name", "center_nm", "width_nm", "range_nm", "resolution_m", "variants", "note")
    values = {field: band[field] for field in fields}
    values["uses"] = [u["use"] for u in band["uses"]]
    values.update(changes)
    return values


def fixture_checks(research):
    alpha, beta = research["sensors"]
    use_fields = ("label", "definition", "source_ids")
    sensor_fields = (
        "label",
        "platform",
        "instrument",
        "operator",
        "access",
        "wavelength_form",
        "notes",
        "source_ids",
    )
    return {
        "topic": "sensor-bands",
        "checker": {"agent": "c", "model": "n", "started_at": "t", "finished_at": "2026-09-17T1"},
        "checks": [
            check("use-chlorophyll", "confirmed", {k: research["uses"][0][k] for k in use_fields}),
            check("use-turbidity", "not_verifiable", reason="page down"),
            check("sensor-alpha", "confirmed", {k: alpha[k] for k in sensor_fields}),
            check("band-alpha-B1", "confirmed", band_values(alpha["bands"][0])),
            # The checker corrected the width and dropped the chlorophyll use.
            check(
                "band-alpha-B2", "corrected", band_values(alpha["bands"][1], width_nm=31, uses=[])
            ),
            check("band-alpha-B3", "not_verifiable", reason="row missing"),
            check("sensor-beta", "confirmed", {k: beta[k] for k in sensor_fields}),
            check("band-beta-1", "confirmed", band_values(beta["bands"][0])),
        ],
        "limitations": ["check limit"],
    }


def test_collate_binds_only_confirmed_or_corrected_records():
    research = fixture_research()
    dataset = collate_sensor_bands.collate(research, fixture_checks(research))
    assert [u["id"] for u in dataset["uses"]] == ["chlorophyll"]
    alpha, beta = dataset["sensors"]
    assert [b["id"] for b in alpha["bands"]] == ["B1", "B2"]
    # The unverified use leaves every band, and the checker's values replace the draft's.
    assert [u["use"] for u in alpha["bands"][0]["uses"]] == ["chlorophyll"]
    assert alpha["bands"][1]["width_nm"] == 31 and alpha["bands"][1]["uses"] == []
    assert alpha["bands"][1]["check"] == "chk-band-alpha-B2"
    assert beta["bands"][0]["range_nm"] == [10600, 11190]
    assert {g["claim_id"] for g in dataset["gaps"]} == {"use-turbidity", "band-alpha-B3"}
    assert [s["id"] for s in dataset["sources"]] == ["src-agency", "src-paper"]
    assert dataset["verification"]["limitations"] == ["research limit", "check limit"]
    assert dataset["verification"]["bound_checks"] == 6


def test_collate_refuses_malformed_checks():
    research = fixture_research()
    checks = fixture_checks(research)
    checks["checks"][3]["approved"]["uses"] = ["cdom"]
    with pytest.raises(ValueError, match="undrafted use"):
        collate_sensor_bands.collate(research, checks)
    checks = fixture_checks(research)
    checks["checks"][3]["approved"]["range_nm"] = [400, 500]
    with pytest.raises(ValueError, match="exactly one wavelength form"):
        collate_sensor_bands.collate(research, checks)
    checks = fixture_checks(research)
    checks["checks"][3]["id"] = "chk-band-alpha-B9"
    with pytest.raises(ValueError, match="does not name its claim"):
        collate_sensor_bands.collate(research, checks)
    checks = fixture_checks(research)
    del checks["checks"][3]["approved"]
    with pytest.raises(ValueError, match="no approved values"):
        collate_sensor_bands.collate(research, checks)


def test_wavelength_and_number_labels():
    assert render_options.plain_number(10) == "10"
    assert render_options.plain_number(3.7) == "3.7"
    assert render_options.plain_number(1000) == "1,000"
    assert render_options.wavelength_label({"range_nm": [10600, 11190]}) == "10,600–11,190"
    assert (
        render_options.wavelength_label({"range_nm": None, "center_nm": 442.7, "width_nm": 21})
        == "432.2–453.2"
    )
    assert (
        render_options.wavelength_label({"range_nm": None, "center_nm": 681.25, "width_nm": 7.5})
        == "677.5–685"
    )


def test_sensor_band_table_renders_rows_notes_and_variants():
    research = fixture_research()
    dataset = collate_sensor_bands.collate(research, fixture_checks(research))
    uses = {u["id"]: u for u in dataset["uses"]}
    alpha = dataset["sensors"][0]
    rendered = render_options.sensor_band_table(alpha, uses, gaps=1)
    assert rendered.startswith('<div class="band-table" data-sensor="alpha"><h4>Alpha</h4>')
    assert "Alpha-1 and Alpha-2 · AI · Agency · Public data" in rendered
    assert (
        '<tr><th scope="row">B1</th><td>Blue</td><td>459.4–525.4</td><td>10</td>'
        '<td><span class="use" title="Chlorophyll">Chlorophyll</span></td></tr>' in rendered
    )
    # A band note becomes a numbered footnote under the table, marked on the band id.
    assert '<th scope="row">B2<sup>1</sup></th><td>Red</td>' in rendered
    assert '<ol class="band-footnotes"><li>Absent from the surface product.</li></ol>' in rendered
    assert '<td><span class="muted">none named</span></td>' in rendered
    notes = rendered.split("<summary>Notes on this table</summary>", 1)[1]
    assert notes.startswith("<ul><li>Main values are Alpha-1.</li>")
    assert (
        "<li>Alpha-2 differ from these values by up to 0.3 nm in center wavelength, on B1, "
        "and 1 nm in bandwidth, on B2.</li>" in notes
    )
    assert "<li>1 band did not verify and are not listed.</li></ul></details></div>" in notes
    assert "id=" not in rendered.split("<h4>", 1)[1], "clones must not duplicate HTML ids"
    beta = render_options.sensor_band_table(dataset["sensors"][1], uses)
    assert "Commercial imagery" in beta and "<td>10,600–11,190</td><td>1,000</td>" in beta
    assert "band-footnotes" not in beta and "<sup>" not in beta
    assert "did not verify" not in beta and "differ from these values" not in beta


def test_variant_note_names_every_band_tied_for_the_largest_difference():
    def band(band_id, width, variant_width):
        return {
            "id": band_id,
            "center_nm": 500.0,
            "width_nm": width,
            "variants": {"Two": {"center_nm": 500.0, "width_nm": variant_width}},
        }

    sensor = {"bands": [band("B1", 10.0, 14.0), band("B2", 20.0, 21.0), band("B3", 33.0, 29.0)]}
    assert render_options.variant_note(sensor) == [
        "Two differ from these values by up to 0 nm in center wavelength, on B1, B2, and B3, "
        "and 4 nm in bandwidth, on B1 and B3."
    ]


def test_sensor_options_and_legend():
    sensors = [{"id": "a", "label": "A"}, {"id": "b", "label": "B & C"}]
    assert render_options.sensor_options(sensors, "b") == (
        '<option value="a">A</option><option value="b" selected>B &amp; C</option>'
    )
    with pytest.raises(ValueError, match="not in the dataset"):
        render_options.sensor_options(sensors, "z")
    legend = render_options.use_legend(
        [{"id": "extent", "label": "Water extent", "definition": "Water absorbs infrared."}]
    )
    assert legend == (
        '<ul class="use-legend"><li><span class="use support" title="Water extent">Water extent'
        "</span> <b>Water extent.</b> Water absorbs infrared.</li></ul>"
    )


def test_sensor_band_markers_count_gaps_per_sensor(monkeypatch):
    monkeypatch.setattr(render_options, "DEFAULT_SENSORS", ("alpha", "beta"))
    research = fixture_research()
    dataset = collate_sensor_bands.collate(research, fixture_checks(research))
    dataset["gaps"].append({"claim_id": "band-beta-1x", "verdict": None, "reason": "r"})
    markers = render_options.sensor_band_markers(dataset)
    assert markers["SENSOR_COUNT"] == "2" and markers["SENSOR_BAND_COUNT"] == "3"
    assert markers["SENSOR_TABLES"].count("1 band did not verify") == 2
    assert 'value="alpha" selected' in markers["SENSOR_OPTIONS_LEFT"]
    assert 'value="beta" selected' in markers["SENSOR_OPTIONS_RIGHT"]
    assert markers["SENSOR_SOURCES"].startswith(
        '<b>Documented:</b> A: <a href="https://a">Agency</a>. P: <a href="https://p">Paper</a>. '
        "Researched and independently checked 2026-09-17."
    )


# Dataset tests: the committed records.


@pytest.fixture(scope="module")
def dataset():
    return json.loads(DATASET.read_text())


def test_dataset_matches_its_records():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "collate_sensor_bands.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_dataset_has_the_six_sensors_and_every_band_bound(dataset):
    checks = json.loads(CHECKS.read_text())
    verdicts = {c["id"]: c["verdict"] for c in checks["checks"]}
    sources = {s["id"] for s in dataset["sources"]}
    assert dataset["schema_version"] == 1
    assert [s["id"] for s in dataset["sensors"]] == SENSOR_IDS
    assert [u["id"] for u in dataset["uses"]] == USE_IDS
    for use in dataset["uses"]:
        assert use["definition"] and set(use["source_ids"]) <= sources
        assert verdicts[use["check"]] in {"confirmed", "corrected"}
    for sensor in dataset["sensors"]:
        assert sensor["access"] in {"public", "commercial"}, sensor["id"]
        assert sensor["bands"], sensor["id"]
        assert set(sensor["source_ids"]) <= sources, sensor["id"]
        assert verdicts[sensor["check"]] in {"confirmed", "corrected"}
        ids = [band["id"] for band in sensor["bands"]]
        assert len(ids) == len(set(ids)), sensor["id"]
        for band in sensor["bands"]:
            assert (band["center_nm"] is None) != (band["range_nm"] is None), band
            assert band["resolution_m"] > 0, band
            assert verdicts[band["check"]] in {"confirmed", "corrected"}, band["check"]
            for entry in band["uses"]:
                assert entry["use"] in USE_IDS and entry["basis"] in {"named", "wavelength"}
                assert set(entry["source_ids"]) <= sources, entry
    for source in dataset["sources"]:
        assert source["url"].startswith("https://") and len(source["accessed_on"]) == 10
    assert not [g for g in dataset["gaps"] if g["claim_id"].startswith(("sensor-", "use-"))]


def test_every_use_id_is_named_on_at_least_one_band(dataset):
    named = {entry["use"] for s in dataset["sensors"] for b in s["bands"] for entry in b["uses"]}
    assert named == set(USE_IDS)


class Page(HTMLParser):
    """Band ids by sensor, read back from the rendered library."""

    def __init__(self):
        super().__init__()
        self.sensor = None
        self.depth = 0
        self.in_row_header = False
        self.in_sup = False
        self.bands = {}
        self.options = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and attrs.get("class") == "band-table":
            self.sensor, self.depth = attrs["data-sensor"], 0
            self.bands[self.sensor] = []
        if tag == "div" and self.sensor:
            self.depth += 1
        if tag == "th" and attrs.get("scope") == "row" and self.sensor:
            self.in_row_header = True
        if tag == "option":
            self.options.append(attrs["value"])
        if tag == "sup":
            self.in_sup = True

    def handle_endtag(self, tag):
        if tag == "th":
            self.in_row_header = False
        if tag == "sup":
            self.in_sup = False
        if tag == "div" and self.sensor:
            self.depth -= 1
            if self.depth == 0:
                self.sensor = None

    def handle_data(self, data):
        if self.in_row_header and not self.in_sup:
            self.bands[self.sensor].append(data)


def test_page_lists_every_bound_band_once(dataset):
    page = Page()
    page.feed(PAGE.read_text())
    expected = {s["id"]: [b["id"] for b in s["bands"]] for s in dataset["sensors"]}
    assert page.bands == expected
    assert page.options.count("sentinel-2-msi") == 2, "both selectors list every sensor"
    assert [o for o in page.options if o in SENSOR_IDS] == SENSOR_IDS * 2
