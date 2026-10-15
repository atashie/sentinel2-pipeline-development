"""The presentation opens locally and keeps internal register IDs out of its story."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "s2-options.html"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
        self.text = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag in {"script", "style"}:
            self.skip = True

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def parse_page():
    page = Page()
    page.feed(PAGE.read_text())
    return page


def test_presentation_local_assets_and_links_resolve():
    page = parse_page()
    ids = [attrs["id"] for _, attrs in page.elements if "id" in attrs]
    assert len(ids) == len(set(ids)), "Duplicate HTML IDs"
    for tag, attrs in page.elements:
        for name in ("href", "src"):
            if name not in attrs:
                continue
            target = urlsplit(attrs[name])
            if target.scheme or target.netloc:
                assert tag == "a", "Viewing the page must not request an external service"
                continue
            if target.path:
                assert (PAGE.parent / unquote(target.path)).exists(), attrs[name]
            elif target.fragment:
                assert target.fragment in ids, attrs[name]


def test_presentation_has_four_phases_without_internal_register_labels():
    page = parse_page()
    tabs = [attrs for _, attrs in page.elements if attrs.get("role") == "tab"]
    panels = [attrs for _, attrs in page.elements if attrs.get("role") == "tabpanel"]
    assert len(tabs) == len(panels) == 4
    assert {tab["aria-controls"] for tab in tabs} == {panel["id"] for panel in panels}
    assert sum(tab["aria-selected"] == "true" for tab in tabs) == 1
    assert [p["id"] for p in panels if "hidden" not in p] == ["discovery"]
    text = " ".join(page.text)
    for label in ("Discovery", "Prototyping", "Integration Specs", "Tradeoffs & Issues"):
        assert label in text
    assert not re.search(r"\b(?:I-\d+|GS-\d+|Decision 0\d{3})\b", text, re.IGNORECASE)


def test_presentation_carries_every_inventory_issue_in_plain_language():
    inventory = json.loads((ROOT / "docs" / "options-inventory.json").read_text())
    text = " ".join(" ".join(parse_page().text).split())
    for issue in inventory["issues"]:
        expected = " ".join(issue["plain"].split())
        if issue["id"] == "I-18":
            assert expected not in text, "the JPEG 2000 bucket stays off the page"
        else:
            assert expected in text, issue["id"]


def test_vercel_rewrite_points_at_the_page():
    config = json.loads((ROOT / "docs" / "vercel.json").read_text())
    assert config["buildCommand"] == "" and config["installCommand"] == ""
    for rule in config["rewrites"]:
        assert (ROOT / "docs" / rule["destination"].lstrip("/")).exists(), rule


def test_presentation_names_the_four_archives_and_who_runs_them():
    text = " ".join("".join(parse_page().text).split())
    for phrase in (
        "Element 84",
        "The U.S. Geological Survey",
        "hosted on a Sentinel Hub domain",
        "usgs-wma-sentinel-2-aqr-acolite-dsf",
        "sentinel-cogs",
        "e84-earth-search-sentinel-data",
        "sentinel-s2-l2a",
        "requester pays",
        "Beyond the lower 48 states.",
    ):
        assert phrase in text, phrase


def test_primary_product_numbers_come_from_the_coverage_survey():
    result = json.loads((ROOT / "benchmarks" / "results" / "aqr-coverage.json").read_text())
    summary = result["summary"]
    shares = []
    for year in range(2018, int(result["window"]["end"][:4])):
        rows = [r for r in summary["coverage_by_month"] if r["month"].startswith(str(year))]
        shares.append(sum(r["aqr"] for r in rows) / sum(r["reference"] for r in rows))
    joins = summary["join_totals"]
    joined = 100 * (summary["scenes"] - joins["none none"]) / summary["scenes"]
    text = " ".join(" ".join(parse_page().text).split())
    for phrase in (
        f"holds {100 * min(shares):.0f} to {100 * max(shares):.0f} percent of Earth Search",
        f"{joined:.0f} percent of its scenes match an Earth Search image of the same pass",
        f"Listings of {summary['scenes']:,} USGS scenes",
    ):
        assert phrase in text, phrase
    page = PAGE.read_text()
    assert 'aria-labelledby="aqr-coverage-title"' in page
    for view in ("aqr-true-color", "aqr-water-flag"):
        assert f'value="{view}"' in page
        assert (PAGE.parent / "assets" / "discovery" / f"{view}.png").exists(), view


def test_presentation_cost_table_comes_from_both_options_estimates():
    inputs = json.loads((ROOT / "docs" / "cost-analysis" / "inputs.json").read_text())
    land_m = f"{1000 * inputs['land_radius_km']:,.0f}"
    text = " ".join(" ".join(parse_page().text).split())
    national = {}
    for option, name in (
        ("ACOLITE only", "estimates-acolite-only.json"),
        ("Sen2Cor only", "estimates.json"),
    ):
        data = json.loads((ROOT / "docs" / "cost-analysis" / name).read_text())
        national[option] = next(
            r for r in data["estimates"] if (r["workload"], r["case"]) == ("all_land", "base")
        )
    backfill = {
        option: f"${row['recipes']['B1']['historical_ec2_total_including_prep_put_usd']:,.0f}"
        for option, row in national.items()
    }
    bodies = national["Sen2Cor only"]["bodies"]
    for phrase in (
        "03 / AWS cost estimates",
        f"the B1 backfill costs {backfill['ACOLITE only']} for ACOLITE only and "
        f"{backfill['Sen2Cor only']} for Sen2Cor only on EC2",
        f"All contiguous US water bodies ({bodies:,}) · water + shoreline + {land_m} m nearby land",
        "holding national A1 at the largest measured A1/B1 byte ratio",
    ):
        assert phrase in text, phrase
    for option, row in national.items():
        source = row["recipes"]["B1"]["historical_requested_TB_decimal"]
        for phrase in (
            f"{option} {source:,.0f} TB {backfill[option]}",
            f"{option}: storage at completion",
            f"S3 Standard ${row['s3_monthly_at_cutoff_usd']:,.2f} per month, rising by",
        ):
            assert phrase in text, phrase
    assert "Remaining decisions" not in text
    assert "USGS also halted NHDPlus HR production" in text


def test_prototyping_numbers_come_from_the_probe_results():
    results = ROOT / "benchmarks" / "results"
    product = json.loads((results / "aqr-workloads.json").read_text())["workloads"]
    reference = json.loads((results / "lazy-reader-workloads.json").read_text())["cohorts"]
    validity = json.loads((results / "aqr-validity.json").read_text())["summary"]
    pairs = json.loads((results / "aqr-pairs.json").read_text())["summary"]

    def requested(cohorts, configuration):
        runs = cohorts["florida"]["comparisons"]
        return next(r for r in runs if r["configuration"] == configuration)["io"]["bytes_requested"]

    shares = sorted(
        {
            f"{100 * requested(product, c) / requested(reference, c):.0f}"
            for c in ("B-raster", "B-lazy")
        }
    )
    clear = [b["share_disagree"] for b in pairs["pooled"]["both_clear_water"]["interior"].values()]
    shoreline = validity["shares"]["shoreline"]["flags"]["bits"]["swir"]
    dispersed = product["dispersed"]
    l2a = reference["dispersed"]["preflight"]
    text = " ".join(" ".join(parse_page().text).split())
    for phrase in (
        f"B1 and B3 requested {' to '.join(shares)} percent of Level-2A’s bytes",
        f"{dispersed['lakes']} dispersed lakes {dispersed['products']} ACOLITE products",
        f"In {validity['scenes_read']} scenes of 2025, each lake’s no-data count equals",
        f"Its flags call {100 * shoreline:.0f} percent of shoreline",
        f"{100 * min(clear):.0f} to {100 * max(clear):.0f} percent of pixel observations differ",
        f"ACOLITE only {dispersed['lakes']} · {dispersed['products']}",
        f"Sen2Cor only {l2a['lakes']} · {l2a['products']}",
    ):
        assert phrase in text, phrase


def test_prototyping_reads_answer_first_with_a_level_2a_reference_table():
    tab = PAGE.read_text().split('id="prototyping"', 1)[1].split('id="integration"', 1)[0]
    assert re.findall(r'<div class="chapter-num">([^<]+)</div>', tab) == [
        "00 / High level takeaways",
        "01 / What we tested",
        "02 / Main comparison · B1 and B3 on each option",
        "03 / AWS cost estimates",
        "04 / Pixel checks",
        "05 / Level-2A reference series",
    ]
    reference = tab.split('<h2 id="reference-series">', 1)[1]
    for row in ("stage-2", "stage-3", "stage-4", "reference-workloads"):
        assert f'<tr id="{row}">' in reference, row
    assert "earlier-experiment" not in tab
    assert tab.count("<details") == 2, "only the reader key and the method notes stay collapsed"
