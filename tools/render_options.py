"""Render docs/options-inventory.json to docs/s2-options.html.

Standard library only. No network. Deterministic: the same inventory and check records
produce the same HTML. `--check` compares the rendered output with the checked-in file.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INVENTORY = DOCS / "options-inventory.json"
OUTPUT = DOCS / "s2-options.html"
PARTS = [
    ("discovery", "Discovery"),
    ("prototyping", "Prototyping"),
    ("integration", "Integration specs"),
    ("tradeoffs", "Tradeoffs and issues"),
]
CLASS_LABELS = {
    "public-aws": "public AWS",
    "non-aws": "non-AWS",
    "managed": "managed",
    "self-built": "self-built",
}

CSS = """
:root { --bg:#fff; --fg:#1b1b1b; --muted:#5a5a5a; --line:#d8d8d8; --card:#f6f6f4;
  --accent:#1f5f8b; --est:#8a5a00; --estbg:#fff3d6; --ok:#2d6a4f; --okbg:#e3f1ea; }
@media (prefers-color-scheme: dark) { :root { --bg:#141414; --fg:#e8e8e8; --muted:#a8a8a8;
  --line:#3a3a3a; --card:#1e1e1e; --accent:#7fb3d5; --est:#f0c674; --estbg:#3a2e10;
  --ok:#9ad0b0; --okbg:#1e3a2c; } }
body { margin:0; padding:1.5rem; font:15px/1.45 system-ui, sans-serif; color:var(--fg);
  background:var(--bg); max-width:1400px; margin-inline:auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; } h2 { font-size:1.25rem; margin:2rem 0 .5rem; }
h3 { font-size:1.05rem; margin:1.25rem 0 .5rem; }
p.lead, p.note { color:var(--muted); margin:.25rem 0 .75rem; }
nav.tabs { display:flex; gap:.5rem; flex-wrap:wrap; margin:1rem 0; }
nav.tabs button { font:inherit; padding:.4rem .8rem; border:1px solid var(--line);
  background:var(--card); color:var(--fg); border-radius:.4rem; cursor:pointer; }
nav.tabs button[aria-selected="true"] { border-color:var(--accent); color:var(--accent);
  font-weight:600; }
.js .part:not(.active) { display:none; }
.tablewrap { overflow-x:auto; border:1px solid var(--line); border-radius:.4rem; }
table { border-collapse:collapse; width:100%; font-size:.9rem; }
th, td { text-align:left; vertical-align:top; padding:.4rem .5rem;
  border-bottom:1px solid var(--line); }
th { background:var(--card); position:sticky; top:0; }
td.blank { color:var(--muted); }
.badge { display:inline-block; font-size:.72rem; padding:.05rem .4rem; border-radius:.3rem;
  border:1px solid var(--line); margin-left:.3rem; white-space:nowrap; }
.badge.est { color:var(--est); background:var(--estbg); border-color:var(--est); }
.badge.ok { color:var(--ok); background:var(--okbg); border-color:var(--ok); }
.badge.warn { color:#fff; background:#b00020; border-color:#b00020; font-weight:700; }
tr.warn th, tr.warn td { border-left:4px solid #b00020; font-weight:600; }
details { border:1px solid var(--line); border-radius:.4rem; margin:.5rem 0;
  background:var(--card); }
summary { cursor:pointer; padding:.5rem .75rem; font-weight:600; }
details > div { padding:0 .75rem .75rem; }
dl.claims dt { font-weight:600; margin-top:.6rem; } dl.claims dd { margin:0 0 .2rem 1rem; }
ul.compact { margin:.25rem 0; padding-left:1.2rem; }
footer { margin-top:2rem; color:var(--muted); font-size:.85rem;
  border-top:1px solid var(--line); padding-top:.75rem; }
code { font-size:.85em; }
"""

JS = """
document.documentElement.classList.add('js');
(function () {
  var parts = Array.prototype.slice.call(document.querySelectorAll('.part'));
  var buttons = Array.prototype.slice.call(document.querySelectorAll('nav.tabs button'));
  function activate(id) {
    parts.forEach(function (p) { p.classList.toggle('active', p.id === id); });
    buttons.forEach(function (b) {
      b.setAttribute('aria-selected', b.dataset.part === id ? 'true' : 'false');
    });
  }
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      activate(b.dataset.part);
      history.replaceState(null, '', '#' + b.dataset.part);
    });
  });
  var hash = location.hash.replace('#', '');
  var target = document.getElementById(hash);
  var part = target ? target.closest('.part') : null;
  activate(part ? part.id : parts[0].id);
  if (target && part) { target.scrollIntoView(); }
})();
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_inventory(path: Path = INVENTORY) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def load_check(binding: dict | None) -> dict | None:
    if not binding:
        return None
    path = DOCS / binding["file"]
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    for check in record.get("checks", []):
        if check.get("id") == binding["id"]:
            return {"checker": record.get("checker", {}), **check}
    return None


def claims_for(candidate_id: str, field_id: str, claims: dict) -> list[dict]:
    """Every claim for one candidate and field, in id order."""
    return sorted(
        (c for c in claims.values() if c["candidate"] == candidate_id and c["field"] == field_id),
        key=lambda c: c["id"],
    )


def render_value(claim: dict | None) -> str:
    if claim is None:
        return '<td class="blank"></td>'
    text = esc(claim["value"])
    if claim.get("unit"):
        text += f' <span class="muted">{esc(claim["unit"])}</span>'
    badge = ""
    if claim["status"] == "estimated":
        badge = '<span class="badge est">estimate</span>'
    elif claim["status"] == "measured":
        badge = '<span class="badge ok">measured</span>'
    return f'<td title="{esc(claim.get("note"))}">{text}{badge}</td>'


def render_table(fields: list[dict], candidates: list[dict], claims: dict) -> str:
    head = "".join(f"<th>{esc(f['label'])}</th>" for f in fields)
    rows = []
    for cand in candidates:
        cells = ""
        for f in fields:
            cell = render_value(claims.get(cand["specs"].get(f["id"])))
            extra = len(claims_for(cand["id"], f["id"], claims)) - 1
            if extra > 0:
                cell = cell.replace("</td>", f' <span class="badge">+{extra}</span></td>')
            cells += cell
        label = CLASS_LABELS.get(cand["class"], cand["class"])
        rows.append(
            f'<tr><th scope="row"><a href="#{esc(cand["id"])}">{esc(cand["name"])}</a>'
            f'<span class="badge">{esc(label)}</span></th>{cells}</tr>'
        )
    return (
        '<div class="tablewrap"><table><thead><tr><th>Candidate</th>'
        f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_sources(source_ids: list[str], sources: dict) -> str:
    items = []
    for sid in source_ids:
        src = sources.get(sid)
        if src is None:
            items.append(f"<li>missing source <code>{esc(sid)}</code></li>")
            continue
        updated = f", page updated {esc(src['page_updated'])}" if src.get("page_updated") else ""
        items.append(
            f'<li><a href="{esc(src["url"])}">{esc(src["title"])}</a>, {esc(src.get("publisher"))},'
            f" accessed {esc(src['accessed_on'])}{updated}</li>"
        )
    return f'<ul class="compact">{"".join(items)}</ul>' if items else ""


def render_claim(claim: dict, field: dict, sources: dict, claims: dict) -> str:
    parts = [f"<dt>{esc(field['label'])}: {esc(claim['value'])}"]
    if claim.get("unit"):
        parts.append(f" {esc(claim['unit'])}")
    parts.append(f'<span class="badge">{esc(claim["status"])}</span></dt>')
    parts.append(f"<dd>{esc(claim.get('note'))}</dd>")
    if claim["status"] == "estimated":
        basis = ", ".join(f"<code>{esc(b)}</code>" for b in claim.get("basis", []))
        parts.append(f"<dd>Estimate. Basis: {basis}. {esc(claim.get('reasoning'))}</dd>")
    else:
        parts.append(f"<dd>{render_sources(claim.get('source_ids', []), sources)}</dd>")
        check = load_check(claim.get("check"))
        if check is None:
            parts.append("<dd>No check record found.</dd>")
        else:
            parts.append(
                f"<dd>Check: {esc(check.get('verdict'))} by {esc(check['checker'].get('model'))}"
                f" on {esc(check.get('checked_on'))}. {esc(check.get('reason'))}</dd>"
            )
    return "".join(parts)


def render_card(cand: dict, fields: list[dict], claims: dict, sources: dict) -> str:
    label = CLASS_LABELS.get(cand["class"], cand["class"])
    body = []
    populated = [(f, claim) for f in fields for claim in claims_for(cand["id"], f["id"], claims)]
    if populated:
        body.append('<dl class="claims">')
        body.extend(render_claim(claim, field, sources, claims) for field, claim in populated)
        body.append("</dl>")
    else:
        body.append('<p class="note">No populated specification. Every field is unknown.</p>')
    if cand.get("questions"):
        body.append('<h4>Open questions</h4><ul class="compact">')
        body.extend(f"<li>{esc(q)}</li>" for q in cand["questions"])
        body.append("</ul>")
    return (
        f'<details id="{esc(cand["id"])}"><summary>{esc(cand["name"])}'
        f'<span class="badge">{esc(label)}</span></summary><div>{"".join(body)}</div></details>'
    )


def render_list_section(title: str, items: list[dict], claims: dict, key: str = "claim_ids") -> str:
    if not items:
        return f'<h3>{esc(title)}</h3><p class="note">None recorded.</p>'
    rows = []
    for item in items:
        cites = ", ".join(f"<code>{esc(c)}</code>" for c in item.get(key, []))
        extra = ""
        if item.get("questions"):
            extra = (
                '<ul class="compact">'
                + "".join(f"<li>{esc(q)}</li>" for q in item["questions"])
                + "</ul>"
            )
        rows.append(
            f"<li><strong>{esc(item.get('title', item.get('id')))}</strong> {esc(item.get('text'))}"
            f' <span class="muted">{cites}</span>{extra}</li>'
        )
    return f"<h3>{esc(title)}</h3><ul>{''.join(rows)}</ul>"


def render_gaps(gaps: list[dict]) -> str:
    if not gaps:
        return '<h3>Gaps</h3><p class="note">None recorded.</p>'
    rows = "".join(
        f"<li><code>{esc(g.get('candidate'))}</code> {esc(g.get('field'))}: "
        f"{esc(g.get('reason'))}</li>"
        for g in gaps
    )
    return f"<h3>Gaps</h3><ul>{rows}</ul>"


def render_issues(issues: list[dict]) -> str:
    if not issues:
        return ""
    rows = []
    for issue in issues:
        evidence = " ".join(f"<code>{esc(e)}</code>" for e in issue.get("evidence", []))
        flagged = issue.get("flag") == "major concern"
        row_class = ' class="warn"' if flagged else ""
        flag = '<br><span class="badge warn">MAJOR CONCERN</span>' if flagged else ""
        rows.append(
            f'<tr id="{esc(issue["id"])}"{row_class}><th scope="row">{esc(issue["id"])}<br>'
            f"{esc(issue['title'])}{flag}</th><td>{esc(issue['text'])}</td>"
            f"<td>{esc(issue['consequence'])}</td>"
            f'<td><span class="badge">{esc(issue["status"])}</span><br>'
            f"{esc(issue.get('decision'))}</td><td>{evidence}</td></tr>"
        )
    return (
        '<h3 id="issues">Ingestion and processing issues</h3>'
        '<p class="note">Every issue names its evidence: inventory claim IDs, or claim IDs from'
        " the best-practices document (G, R, Q). Status is decided, deferred, open, probe,"
        " or measure.</p>"
        '<div class="tablewrap"><table><thead><tr><th>Issue</th><th>What the sources say</th>'
        "<th>What it means for the store</th><th>Status</th><th>Evidence</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_probes(probes: list[dict]) -> str:
    if not probes:
        return ""
    rows = "".join(
        f'<tr id="{esc(p["id"])}"><th scope="row">{esc(p["id"])}</th><td>{esc(p["date"])}</td>'
        f"<td>{esc(p['question'])}</td><td>{esc(p['result'])}</td>"
        f"<td>{' '.join(f'<code>{esc(b)}</code>' for b in p.get('bears_on', []))}</td></tr>"
        for p in probes
    )
    return (
        '<h3 id="probes">Bounded probes</h3>'
        '<p class="note">Catalog metadata queries and header-only requests made by the parent'
        " agent. Endpoints and raw results are in the probe record. Not independently checked."
        " A probe samples one place and time and establishes nothing beyond its sample.</p>"
        '<div class="tablewrap"><table><thead><tr><th>Probe</th><th>Date</th><th>Question</th>'
        f"<th>Result</th><th>Bears on</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def render_dimension(inv: dict, dim: str, definition: str, claims: dict, sources: dict) -> str:
    fields = [f for f in inv["fields"] if dim in f["applies_to"]]
    candidates = [c for c in inv["candidates"] if c["dimension"] == dim]
    primary = [c for c in candidates if c.get("role", "primary") == "primary"]
    context = [c for c in candidates if c.get("role", "primary") == "context"]
    out = [f'<h3 id="dim-{esc(dim)}">{esc(dim.replace("_", " ").capitalize())}</h3>']
    out.append(f'<p class="note">{esc(definition)}</p>')
    out.append(render_table(fields, primary, claims))
    out.extend(render_card(c, fields, claims, sources) for c in primary)
    if context:
        out.append(
            f"<details><summary>Context: {len(context)} options documented for reference,"
            " not compared for selection</summary><div>"
        )
        out.append(render_table(fields, context, claims))
        out.extend(render_card(c, fields, claims, sources) for c in context)
        out.append("</div></details>")
    return "".join(out)


def render_discovery(inv: dict) -> str:
    claims = {c["id"]: c for c in inv["claims"]}
    sources = {s["id"]: s for s in inv["sources"]}
    out = ["<h2>Discovery</h2>"]
    out.append(
        '<p class="lead">Issues first, then one table per dimension. A blank cell is unknown,'
        " not zero or absent. Hover a cell for its note. Open a card for claims, sources, and"
        " check verdicts.</p>"
    )
    out.append(render_issues(inv.get("issues", [])))
    out.append(render_probes(inv.get("probes", [])))
    for dim, definition in inv["dimensions"].items():
        out.append(render_dimension(inv, dim, definition, claims, sources))
    out.append(render_list_section("Findings", inv.get("findings", []), claims))
    combos = inv.get("combinations", [])
    primary_combos = [c for c in combos if c.get("role", "primary") == "primary"]
    context_combos = [c for c in combos if c.get("role", "primary") == "context"]
    out.append(render_list_section("Combinations", primary_combos, claims))
    if context_combos:
        out.append(
            f"<details><summary>Context: {len(context_combos)} combinations on routes outside"
            " the comparison</summary><div>"
            + render_list_section("Context combinations", context_combos, claims)
            + "</div></details>"
        )
    out.append(render_gaps(inv.get("gaps", [])))
    not_assessed = inv.get("not_assessed", [])
    if not_assessed:
        rows = "".join(
            f"<li><strong>{esc(n.get('name'))}</strong> {esc(n.get('why'))}</li>"
            for n in not_assessed
        )
        out.append(f"<h3>Noticed, not assessed</h3><ul>{rows}</ul>")
    ver = inv.get("verification", {})
    checkers = "".join(f"<li>{esc(c)}</li>" for c in ver.get("checkers", []))
    out.append(
        f'<h3>Verification</h3><p>{esc(ver.get("method"))}</p><ul class="compact">{checkers}</ul>'
        f'<p class="note">{esc(ver.get("limits"))}</p>'
    )
    return "".join(out)


def build_html(inv: dict, digest: str) -> str:
    assessed = inv.get("assessed_on") or "not yet assessed"
    tabs = "".join(
        f'<button type="button" data-part="{pid}" aria-selected="false">{esc(title)}</button>'
        for pid, title in PARTS
    )
    parts = []
    for pid, title in PARTS:
        body = (
            render_discovery(inv)
            if pid == "discovery"
            else (
                f'<h2>{esc(title)}</h2><p class="note">TBD. '
                "Developed with the owner in a later step.</p>"
            )
        )
        parts.append(f'<section class="part" id="{pid}">{body}</section>')
    embedded = json.dumps(inv, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Sentinel-2 ingestion options</title>"
        f"<style>{CSS}</style></head><body>"
        "<h1>Sentinel-2 ingestion options</h1>"
        f'<p class="lead">Assessment dataset schema {esc(inv["schema_version"])}, '
        f"assessed {esc(assessed)}."
        f" Selection {esc(inv['selection']['status'])}: {esc(inv['selection']['note'])}</p>"
        f'<nav class="tabs" aria-label="Phases">{tabs}</nav>'
        f"{''.join(parts)}"
        "<footer>Generated from <code>options-inventory.json</code>, "
        f"SHA-256 <code>{digest}</code>."
        " The embedded dataset follows. No external requests are made.</footer>"
        f'<script type="application/json" id="assessment-data">{embedded}</script>'
        f"<script>{JS}</script></body></html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare with the checked-in HTML")
    args = parser.parse_args(argv)
    inv, digest = load_inventory()
    rendered = build_html(inv, digest)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print(f"{OUTPUT.relative_to(ROOT)} is stale. Run tools/render_options.py.")
            return 1
        print(f"{OUTPUT.relative_to(ROOT)} matches the inventory.")
        return 0
    OUTPUT.write_text(rendered)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
