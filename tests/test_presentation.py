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
        "Sinergise",
        "sentinel-cogs",
        "e84-earth-search-sentinel-data",
        "sentinel-s2-l2a",
        "requester pays",
    ):
        assert phrase in text, phrase
