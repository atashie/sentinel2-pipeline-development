# Assessment data format, 2026-09-09

[options-inventory.json](options-inventory.json) is the canonical dataset. The HTML view is generated from it and never edited by hand.
On 2026-09-09 the dataset holds seeded candidates with null specifications and no claims. Discovery populates it.

## Schema version 1

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
| `claims` | Documented values, units, notes, status, source IDs, and check bindings |
| `candidates` | Named option, dimension, class, specification references, and unresolved questions |
| `findings` | Assessment inferences and the claim IDs that support them |
| `combinations` | Unranked route, workflow, platform, and layout combinations with their open questions |
| `gaps` | Specifications rejected or blanked during verification, with reasons |
| `verification` | Review method, checker identities, and limits |

Every candidate has every field whose `applies_to` includes the candidate's dimension. A validated specification points to a claim ID. An unvalidated specification is null.
Null covers undocumented, inaccessible, ambiguous, and conflicting facts. It does not encode zero, false, or an explicit absence. An explicit absence is a claim with value `Not listed`.

Candidate `class` is one of `public-aws`, `non-aws`, `managed`, or `self-built`. Class describes where the option runs, not its price or its terms.

Every claim's note qualifies its value. Consumers must keep the note beside the value. Prices keep unit, currency notation, plan, and conditions in the note.

## Evidence binding

Each claim links a record in [assessment-checks/](assessment-checks/README.md). The record names its checker and its verdict.
A changed claim cannot retain its earlier confirmation. Recheck the source and update the record before regeneration.
Rejected assertions stay in the check records as history. They never populate a specification.

## Regeneration

1. Update the canonical dataset and matching check records.
2. Run the renderer in `tools/` once it exists.
3. Run the [check workflow](../.claude/skills/check/SKILL.md).
4. Review the rendered HTML and its embedded JSON.

[tests/test_inventory.py](../tests/test_inventory.py) enforces the schema rules above without a renderer.

## Report parts

The HTML carries four phase tabs:

- Discovery: workflows and processing options across the four dimensions, expandable cards, findings, and evidence.
- Prototyping: `TBD` until step 3.
- Integration specs: `TBD` until step 4.
- Tradeoffs and issues: `TBD` until step 5.

Without JavaScript all parts render in sequence with their titles.
