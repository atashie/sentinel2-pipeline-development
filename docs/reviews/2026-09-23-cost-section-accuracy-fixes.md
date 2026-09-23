# Accuracy fixes to the cost section and a removed NHD note, 2026-09-23

Author: Claude Code (AI coding agent), directed by the repository owner.
Status: implemented and checked. Awaiting owner review.

Claude Code reviewed Prototyping section 07 of the [assessment page](../s2-options.html) for technical accuracy in the session.
The owner asked for its suggested updates, stated briefly. The owner also asked to remove the NHD source note in section 06.
No estimate, input, or model file changed. No provider was contacted.

## Changes

| Finding | Change on the page |
|---|---|
| National A1 source bytes equal Florida's measured A1/B1 ratio, 5.117. National block redundancy is 78, against Florida's 13.5 | Caption: "National A1 is held at the largest measured A1/B1 byte ratio, 5.1×." The renderer refuses estimates where this no longer holds |
| Measured CPU is 20–40% of EC2 backfill instance-hours. Transfer, latency, and overhead are assumed | "Section 05 supplies CPU time per megabyte and requested bytes per source block. Network time and overheads are assumed." |
| Prices are qualified proxies under assumption A34 | "It uses unconfirmed planning prices for Oregon." |
| Source reads assume an S3 gateway endpoint. NAT processing would add about $0.045 per GB | "Source reads use an S3 gateway endpoint, with no NAT charges." |
| At 2 GiB, B1 bills the same hours for $1,768 instead of $2,631 | "Its cost rises with the memory setting." |
| Sample rows are count-uniform expectations under assumption A37 | "A random sample of 10,000, reported as expected values." |
| The national scope is the contiguous states | Group label: "All contiguous US water bodies" |
| The S3 charge includes prepared geometry. The rise flattens after 50 TB | "Storage at completion: 36,186 GiB of records and geometry … rising by $164.88 over the first year" |
| Collection 1 lacks most of 2022 | "Most 2022 dates come from the older copy." |
| "Estimates dated" gave the history cutoff | "Estimates revised 2026-09-23", from the input file |
| Owner request | Removed the section 06 note that began "USGS no longer maintains NHD" |

The [renderer](../../tools/render_options.py) binds the A1 ratio, stored volume, and revision date. [Renderer tests](../../tests/test_render_options.py) and [page tests](../../tests/test_presentation.py) cover them.

## Limits

- The [pilot manifest review](2026-09-12-pilot-manifest-review.md#source-checks) still records USGS's retirement of NHD on 2023-10-01 as documented. The page no longer states it.
- The NAT figure and the claim that the price values match current Oregon list prices came from memory. Neither was checked.
- The partial orbit coverage and catalog network path items remain open.

## Verification

- `uv run python tools/render_options.py --check`: page matches its template and inputs.
- Review-layer `inject.py --check`: up to date.
- `/check`: ruff passed, format passed, 318 tests passed.

## Proposed next step

Owner review of section 07 and the NHD removal. Not started.
