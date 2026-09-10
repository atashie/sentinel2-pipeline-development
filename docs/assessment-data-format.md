# Assessment data format, 2026-09-09

[options-inventory.json](options-inventory.json) is the canonical dataset. [s2-options.html](s2-options.html) is generated from it by [render_options.py](../tools/render_options.py) and never edited by hand.
Schema version 2 replaces version 1 on 2026-09-09. It adds the `offset_delivery` field, the `estimated` status, and the record formats below.

## Schema version 2

| Key | Meaning |
|---|---|
| `schema_version` | Integer. Consumers must inspect it before reading |
| `assessed_on` | ISO date of the latest assessment pass. Null before discovery |
| `selection` | Open selection status and the governing decision |
| `scope` | Pointer to the canonical assumptions document |
| `missing_value_policy` | What null means and what it does not mean |
| `dimensions` | The four candidate dimensions and their definitions |
| `fields` | Specification labels, groups, definitions, units, and the dimensions each applies to |
| `sources` | Primary URLs, titles, access dates, optional page update dates, and stable source IDs |
| `claims` | Values with unit, note, status, source IDs, and either a check binding or a basis |
| `issues` | Ingestion and processing issues: title, what the sources say, consequence for the store, status, decision, and evidence IDs |
| `probes` | Bounded catalog or header-only probes by the parent agent: date, question, result, issues it bears on, and the record file. Not independently checked |
| `candidates` | Named option, dimension, class, role, specification references, and unresolved questions |
| `findings` | Assessment inferences and the claim IDs that support them |
| `combinations` | Unranked route, workflow, platform, and layout combinations with a role and their open questions |
| `gaps` | Draft claims that did not bind: no check, not verifiable, or an estimate without basis, with reasons |
| `not_assessed` | Options noticed on cited pages but outside the candidate list, with reasons |
| `verification` | Review method, checker identities per dimension, dimensions collated, and merged limits |

Once `assessed_on` is set, every candidate carries every field whose `applies_to` includes the candidate's dimension. A validated specification points to a claim ID. An unvalidated specification is null.
Null covers undocumented, inaccessible, ambiguous, and conflicting facts. It does not encode zero, false, or an explicit absence. An explicit absence is a claim with value `Not listed`.

Candidate `class` is one of `public-aws`, `non-aws`, `managed`, or `self-built`. Class describes where the option runs, not its price or its terms.
Candidate and combination `role` is `primary` or `context`. Context entries are documented for reference and are not compared for selection, per decision 0002.
Issue `status` is `decided`, `deferred`, `open`, `probe`, or `measure`. An issue may carry `flag` with the value `major concern`, which renders as a red badge and a marked row. Issue `evidence` lists inventory claim IDs, best-practices claim IDs such as `G11`, and probe IDs such as `PR-01`. Issues, like findings, are maintained by hand and preserved by collation.

Every claim's note qualifies its value. Consumers must keep the note beside the value. Prices keep unit, currency notation, plan, and conditions in the note.

## Claim records

A `documented` claim:

```json
{"id": "cl-ar-earth-search-cogs-region", "candidate": "ar-earth-search-cogs", "field": "region",
 "value": "us-west-2", "unit": null, "note": "Bucket sentinel-cogs. Same value on the registry page.",
 "status": "documented", "source_ids": ["src-aws-registry-s2-cogs"],
 "check": {"file": "assessment-checks/access-route-checks.json", "id": "chk-cl-ar-earth-search-cogs-region"}}
```

An `estimated` claim replaces `check` with `basis`: a list of documented claim IDs plus a `reasoning` sentence. The renderer labels it an estimate. It never populates a price, a coverage date, or a license field.

A claim may only be `documented`, `measured`, or `estimated` inside the inventory. `unverified` items live in candidate `questions` and in the `gaps` list, never as claims.

## Research draft records

A research agent writes `assessment-checks/<dimension>-research.json`, with the dimension name hyphenated, for example `access-route-research.json`.

| Key | Meaning |
|---|---|
| `dimension` | One of the four dimension IDs |
| `researcher` | `agent`, `model` as requested, `started_at`, `finished_at` |
| `endpoints_queried` | Every catalog or API endpoint called: `url`, `purpose`, `accessed_on`, `returned` |
| `sources` | Same shape as inventory sources: `id`, `url`, `title`, `publisher`, `accessed_on`, `page_updated` |
| `claims` | Draft claims: `id`, `candidate`, `field`, `value`, `unit`, `note`, `source_ids`, `quote`, `locator`, and `proposed_status` |
| `candidate_notes` | Per candidate: `questions_answered`, `questions_open`, `observations` |
| `not_assessed` | Options noticed on cited pages but outside the candidate list, with a reason |
| `limitations` | What the research could not settle and why |

`quote` is verbatim text from the cited page that supports the value. `locator` names the heading, path, or table on the page. A draft claim without a quote is not checkable.
`proposed_status` is `documented` or `estimated`. An estimated draft carries `basis` instead of `quote`.

## Check records

A checking agent, using a different model from the researcher, writes `assessment-checks/<dimension>-checks.json`.

| Key | Meaning |
|---|---|
| `dimension` | The dimension checked |
| `checker` | `agent`, `model` as requested, `started_at`, `finished_at` |
| `checks` | One record per draft claim: `id` as `chk-` plus the claim ID, `claim_id`, `verdict`, `approved_value`, `approved_unit`, `approved_note`, `source_ids`, `quote`, `reason`, `checked_on` |
| `limitations` | Pages that could not be fetched and other limits |

`verdict` is `confirmed` when the page supports the draft as written. It is `corrected` when the checker replaced the value or note with what the page supports. It is `not_verifiable` when the page does not support the claim or could not be read.
Only `confirmed` and `corrected` records bind an inventory claim. The inventory claim carries the approved value, unit, and note, not the draft's.

## Best-practices recheck records

One agent writes `assessment-checks/best-practices-recheck.json` with a `verdicts` list. Each verdict carries `claim_id` from [s2-best-practices.md](s2-best-practices.md), `verdict` as `CONFIRMED`, `PARTIAL`, `NOT_ON_PAGE`, or `CONTRADICTED`, `source_url`, `title`, `accessed_on`, `quote`, `corrected_wording` or null, and `reason`.
`CONFIRMED` and supported `PARTIAL` or `CONTRADICTED` verdicts change the document's status to `documented` with the corrected wording and citation. `NOT_ON_PAGE` leaves `unverified` and records the attempt.

## What the tests enforce

[tests/test_inventory.py](../tests/test_inventory.py) enforces these rules and no others:

- top-level keys, schema version, and referenced documents exist
- every field applies to a known dimension, and IDs are unique
- once `assessed_on` is set, every candidate carries every applicable field, each null or a claim ID
- a populated specification points to a `documented`, `measured`, or `estimated` claim
- every `documented` claim cites existing HTTPS sources with a ten-character access date and binds a check record that exists, matches its claim ID, has verdict `confirmed` or `corrected`, and whose approved value equals the claim value
- every `estimated` claim names at least one existing documented claim in its basis and a reasoning sentence
- every finding and combination cites at least one existing claim
- every candidate, finding, and combination role and every issue status is in its vocabulary, and every issue cites an inventory claim, a claim row in the best-practices document, or a recorded probe
- every probe carries a date, question, result, issues it bears on, and a record file that exists
- the inventory matches the check records, and the renderer output matches the checked-in HTML

These are structural checks. They do not establish that a page was read correctly, that a provider works, or that a cost is real.

## Collation

[collate_checks.py](../tools/collate_checks.py) rebuilds the evidence-derived parts of the inventory from the research and check records: sources, claims, candidate specifications and open questions, gaps, `not_assessed`, and `verification`.
It preserves `selection`, `scope`, `fields`, `issues`, `probes`, `findings`, `combinations`, and candidate roles, which are maintained by hand.
A dimension is collated only when both its research file and its checks file exist. The candidate's open questions are replaced by the research file's `questions_open`.
The specification for a field points to the claim named `cl-<candidate>-<field>` when it exists. Otherwise it points to the first claim for that field by ID. Further claims for the same field stay in `claims` and render in the candidate card.
To change a bound claim, change its check record and rerun collation. Hand edits to bound claims are overwritten.

## Regeneration

1. Update the research and check records, then the hand-maintained findings and combinations.
2. Run `uv run python tools/collate_checks.py`.
3. Run `uv run python tools/render_options.py`.
4. Run the [check workflow](../.claude/skills/check/SKILL.md). It runs both scripts with `--check`.
5. Review the rendered HTML and its embedded JSON.

The renderer uses the standard library and performs no network access. The HTML records the canonical file's SHA-256 digest and embeds the dataset in an `application/json` script with ID `assessment-data`.

## Report parts

The HTML carries four phase tabs:

- Discovery: the issue register, the probe table, then one table per dimension for primary candidates with context candidates collapsed, expandable candidate cards with claims, notes, sources, and verdicts, then findings, combinations, gaps, and questions.
- Prototyping: `TBD` until step 3.
- Integration specs: `TBD` until step 4.
- Tradeoffs and issues: `TBD` until step 5.

Estimates render with an `estimate` badge beside the value. Public AWS, non-AWS, managed, and self-built classes render with text badges, not color alone.
Without JavaScript all parts render in sequence with their titles. A URL fragment inside a part activates that part.
