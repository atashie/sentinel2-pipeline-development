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


def test_presentation_names_the_three_archives_and_who_runs_them():
    text = " ".join("".join(parse_page().text).split())
    for phrase in (
        "Element 84",
        "hosted on a Sentinel Hub domain",
        "sentinel-cogs",
        "e84-earth-search-sentinel-data",
        "sentinel-s2-l2a",
        "requester pays",
    ):
        assert phrase in text, phrase


def test_presentation_cost_table_comes_from_the_generated_estimates():
    data = json.loads((ROOT / "docs" / "cost-analysis" / "estimates.json").read_text())
    inputs = json.loads((ROOT / "docs" / "cost-analysis" / "inputs.json").read_text())
    land_m = f"{1000 * inputs['land_radius_km']:,.0f}"
    row = next(r for r in data["estimates"] if (r["workload"], r["case"]) == ("all_land", "base"))
    text = " ".join(" ".join(parse_page().text).split())
    b1, b3 = row["recipes"]["B1"], row["recipes"]["B3"]
    source, backfill = (
        b1["historical_requested_TB_decimal"],
        b1["historical_ec2_total_including_prep_put_usd"],
    )
    for phrase in (
        "03 / AWS cost estimates",
        f"the B1 and B3 backfills cost ${backfill:,.0f} and "
        f"${b3['historical_ec2_total_including_prep_put_usd']:,.0f} on EC2",
        f"All contiguous US water bodies ({row['bodies']:,}) · water + shoreline + {land_m} m"
        " nearby land",
        f"S3 Standard ${row['s3_monthly_at_cutoff_usd']:,.2f} per month, rising by",
        "National A1 is held at the largest measured A1/B1 byte ratio",
        f"{source:,.0f} TB ${backfill:,.0f}",
    ):
        assert phrase in text, phrase
    assert "Remaining decisions" not in text
    assert "USGS also halted NHDPlus HR production" in text


def test_prototyping_reads_answer_first_with_earlier_experiments_collapsed():
    tab = PAGE.read_text().split('id="prototyping"', 1)[1].split('id="integration"', 1)[0]
    assert re.findall(r'<div class="chapter-num">([^<]+)</div>', tab) == [
        "00 / High level takeaways",
        "01 / What we tested",
        "02 / Main comparison · Larger workloads",
        "03 / AWS cost estimates",
        "04 / Earlier experiments",
    ]
    for number, stage in (("04.1", "stage-2"), ("04.2", "stage-3"), ("04.3", "stage-4")):
        before = tab.split(f'<h3 id="{stage}">', 1)[0]
        opener = r'<details class="benchmark-detail earlier-experiment"><summary>'
        assert re.search(opener + re.escape(number) + r" · [^<]+</summary>\s*$", before), stage
