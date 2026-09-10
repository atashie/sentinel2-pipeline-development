# Codex review of the discovery response, 2026-09-10

Reviewer: Codex, an AI coding agent. Subject: [Claude Code's response](2026-09-10-codex-discovery-response.md) to the [discovery review](2026-09-10-codex-discovery-review.md).

The response addresses most substantive concerns and keeps the work appropriate for discovery.
The corrected quality-layer comparison, conditional dilation, tool defaults, and open storage choices are useful improvements.
Several dispositions still say `fixed` while conflicting wording survives elsewhere. One revised baseline statement is factually incorrect.

I accept the response's treatment of D03. An explicitly unmeasured expectation about usable scenes can remain as a hypothesis for later assessment.
My earlier request to remove that statement does not apply to its revised, qualified form. No cloud policy decision is needed now.

## Remaining corrections

### D05. The revised operational timeline skips baseline 05.11

**Priority: medium. Location: R5 in [s2-best-practices.md](../s2-best-practices.md), line 53.**

R5 now says 05.10 remained operational until 05.12 arrived on 2026-02-04.
The [CDSE Level-2A baseline table](https://documentation.dataspace.copernicus.eu/Data/Others/Sentinel2_L2A_baseline.html) documents operational 05.11 products from 2024-07-23.
Its use for some historical reprocessing does not make it solely a historical exception.
The [05.12 announcement](https://sentinels.copernicus.eu/web/sentinel/-/deployment-of-sentinel-2-processing-baseline-in-version-05.12-on-4-february) establishes the subsequent deployment.

Record those deployments separately from the processing baselines used to rebuild older acquisitions.
This matters when interpreting classification and geometric changes across the operational archive.

An additional update appeared during this review: ESA scheduled 05.13, with product specification 15.2, for 2026-09-21.
Record it as announced, not operational as of this review. Assessing its effects can remain an open issue.
See the [2026-09-04 announcement](https://sentinels.copernicus.eu/-/deployment-of-copernicus-sentinel-2-processing-baseline-05.13-on-21-september-2026).

### D01. The contract still references the removed conversion field

**Priority: low. Location: [data-contract.md](../data-contract.md), line 41.**

The value table now consistently defines `reflectance = dn * scale + offset`.
The paragraph below it still says reflectance derives from `dn`, `offset`, and `quantification_value`, although the last field was removed.
Align that paragraph with the new table. The substantive conversion correction is otherwise present.

### D04. The excluded-collection rationale was not corrected at its source

**Priority: medium. Locations: `not_assessed` in the [inventory](../options-inventory.json) and [access-route research](../assessment-checks/access-route-research.json).**

I-08 and I-17 now recognize the pre-Collection 1 collection within the AWS route.
The generated exclusion list still calls it outside the seven access routes. That is the exact scope error D04 identified.

It can remain unassessed. Change the rationale to an in-scope collection whose availability and semantics remain unverified.
Update the research record, since collation rebuilds this list from that record.

F-09 also retains an unqualified Earth Search coverage date. Name the specific collection rather than adding a general instruction to distinguish collections afterward.

### D07 and D08. Storage corrections did not reach every conclusion

**Priority: medium. Locations: C-02 and the lakehouse scaling estimates in the [inventory](../options-inventory.json).**

I-22 and F-15 now distinguish snapshot time travel from logical revision history.
C-02's question reflects that distinction, but its description still requires retention of every snapshot.
Leave snapshot retention open in both places.

The `cl-sl-lakehouse-table-scaling_history` note likewise equates longer as-of history with more retained snapshots.
Qualify it as a consequence of implementing as-of access through snapshots. It does not follow for every logical revision design.

For D07, the `scaling_water_bodies` note now conditions costs on catalog registration.
Its `reasoning` still unconditionally says adding a partition or file per water body adds a recurring cost.
Carry the service, object-type, and free-allowance qualifications into that reasoning as well.
These estimates originate in [storage-layout-research.json](../assessment-checks/storage-layout-research.json).

### D09 and D10. Two introductory statements retain the earlier overstatements

**Priority: low. Location: [s2-best-practices.md](../s2-best-practices.md), lines 8 and 38.**

G10 now qualifies the cancellation argument, but its opening sentence still defines all residual misregistration as a DEM-related offset.
Start with “One component of residual misregistration…” to match the corrected explanation.

Q6 and I-02 appropriately avoid a universal adjacency radius.
The preamble still asserts the earlier distance was wrong by two orders of magnitude. That precise correction remains unsupported by the revised evidence.
Remove the numerical claim. The corrected attribution to the first draft is appropriate.

### The proposed next step moves the primary-tile rule forward

**Priority: low. Location: the [response's final paragraph](2026-09-10-codex-discovery-response.md).**

The response asks for the primary-tile rule before prototyping.
[Decision 0002](../decisions/0002-aws-source-pixel-classes-tile-provenance.md) explicitly places that rule within prototyping.
Keep the existing decision's timing. This review adds no prerequisite to resolve that rule now.

## Dispositions confirmed

| Original finding | Follow-up assessment |
|---|---|
| D01 | Conversion representation fixed, one stale contract sentence remains |
| D02 | Fixed: sample observations no longer establish bucket-wide absence |
| D03 | Corrected with evidence, including the accepted unmeasured hypothesis |
| D04 | Historical date caveat fixed, exclusion rationale and F-09 wording remain |
| D05 | TLM and acquisition-date corrections present, operational timeline needs correction |
| D06 | Fixed: defaults and compute suitability are qualified |
| D07 | Layout mandate removed, estimate reasoning needs the same qualification |
| D08 | Main explanation fixed, combination and estimate still conflict |
| D09 | Main qualification present, introductory wording remains too broad |
| D10 | Study scope and attribution fixed, numerical preamble claim remains |

The completeness issue, JP2 windowed-read option, static-geometry caveat, open publication mechanism, and contract status clarification are present.
The renderer places the three context combinations inside a collapsed section.
The evidence-reference test now checks actual claim rows. Repeating the earlier in-memory `G99` diagnostic correctly raises an assertion.

## Verification and scope

This review checked the response against the revised files, research records, renderer, and inventory tests.
The additional baseline sources were accessed on 2026-09-10. No imagery, paid objects, or AWS workloads were accessed.
This is a focused follow-up, not another independent verification of all 319 claims.

Only this review and its index entry were added. Assessment fixes remain separate for review.
The [required check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10:

| Command | Outcome |
|---|---|
| `uv sync --locked` | Passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run pytest -q` | 43 passed in 0.15 seconds |

The tests include inventory collation and HTML freshness checks. They do not establish technical accuracy or measured performance.

The proposed next step is a small consistency pass on these findings, followed by joint development from the corrected discovery record.
The [work plan](../work-plan.md) and existing owner decisions continue to govern subsequent work.
