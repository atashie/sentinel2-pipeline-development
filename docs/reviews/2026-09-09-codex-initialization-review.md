# Initialization review, 2026-09-09

Reviewer: Codex. Scope: initialization against the owner's original prompt, repository guidance, weather repository style, and current primary documentation.
Reviewed baseline: `22ec548`. The repository was initially untracked and became committed during this review. Codex made no commit.

Revised on 2026-09-09 after the owner clarified that the workflow will develop jointly with the owner, Codex, and Claude Code.
The earlier review treated future design questions as initialization defects. Its requirement to resolve all six findings before discovery is withdrawn.
The prescribed acceptance tests, additional planning requirements, and proposed workflow changes are also withdrawn.

The repository is a suitable starting point for that collaboration. Unresolved design questions are expected at this stage.
The implementation is small. Repeated instructions offer some room for simplification, without reorganizing the repository.
This revision changes only this review and its index. Finding IDs remain stable to make the changes traceable.

**What already works**

- The deliverables cover discovery, prototypes, measurements, operational specifications, cost comparisons, and an engineering presentation.
- Production construction remains with engineering. AWS preference is explicit and selection remains open.
- Assumptions distinguish owner requirements from implementer interpretations. The draft contract exposes provenance, revisions, missingness, and local availability.
- Public pilot polygons, clustered and dispersed workloads, native resolutions, and tile-date accounting address useful experimental dimensions.
- The environment has a lockfile, a small dependency set, matching CI commands, and one reusable check skill.
- The supplied PDF is retained with provenance and treated as research input. Its claims have not been presented as verified evidence.

The organization follows the weather repository's documentation, decisions, reviews, evidence files, and generated presentation approach.
Absence of production code, populated claims, or measurements is appropriate for initialization.

**F01: retain the conversion caveat, defer the design**

Locations: [data-contract.md](../data-contract.md), Value fields and reflectance derivation. [s2-best-practices.md](../s2-best-practices.md), R1 and P8.

The contract defines `dn` as the integer delivered by the route, but takes its offset and quantification from product metadata.
That combination can apply an offset twice when a provider has already transformed the original values.

`documented`: Element 84 states that some Sentinel-2 COG assets already incorporate the offset.
Its instructions use each asset's `raster:bands` scale and offset to determine the remaining conversion.
Source: [Earth Search documentation](https://raw.githubusercontent.com/Element84/earth-search/main/README.md), accessed 2026-09-09, “Gain/Offset” section.

The draft needs a caveat that conversion depends on the delivered asset. There is no conversion implementation to fix yet.
The metadata fields, conversion policy, and tests can develop when we assess and prototype a route.

**F02: extraction geometry accepted and deferred**

Locations: [CLAUDE.md](../../CLAUDE.md), first gotcha. [data-contract.md](../data-contract.md), Location fields. [discovery-plan.md](../discovery-plan.md), processing workflows.

The original prompt includes possible immediate environs and a small buffer. The contract currently represents the water-body mask.
Keep extraction geometry, including optional buffers and treatment of small ponds, recorded as an issue for later joint discussion.
No geometry clarification, policy selection, contract expansion, or test specification is requested now.

The claim that a 10 m pond covers at most one 10 m pixel is incorrect as a count of intersecting cells.
A 10 m diameter circle centered on a grid vertex intersects four cells. None of their centers lies inside the circle.
That factual wording can be corrected without choosing how this project will count or select pixels.
The absence of those choices is appropriate for initialization.

**F03: retain provisional wording, defer scientific choices**

Locations: [s2-best-practices.md](../s2-best-practices.md), P1, P4, P5, and P10. [discovery-plan.md](../discovery-plan.md), candidate table.

Water-specific atmospheric correction is already acknowledged as an open question in P10.
Other practices prescribe mask reuse and prohibit ingestion co-registration despite supporting claims remaining unverified.
Keep reference-design choices visibly provisional where they have not been selected together.
Their suitability can be investigated as the relevant part of the assessment develops.

`documented`: a USGS Sentinel-2 study identifies the need for aquatic atmospheric correction distinct from standard terrestrial products.
Source: [USGS aquatic-reflectance publication](https://www.usgs.gov/publications/aquatic-reflectance-derived-sentinel-2-multispectral-imager-data-inland-waters), published 2026-02-22, accessed 2026-09-09.

`documented`: Copernicus describes Collection-1 reprocessing of the historical archive with improved geometric performance.
Acquisition year alone therefore cannot establish the quality of the delivered revision.
Source: [SentiWiki product documentation](https://sentiwiki.copernicus.eu/web/s2-products), “Copernicus Sentinel-2 Collection-1,” accessed 2026-09-09.
Whether each candidate route delivers these revisions remains unverified.
These are reasons to preserve open questions. They do not establish a required comparison matrix or a new gate for starting work.

**F04: retain the finding about overstated test coverage**

Locations: [test_inventory.py](../../tests/test_inventory.py), lines 55, 75, and 91. [assessment-data-format.md](../assessment-data-format.md), Evidence binding.

The tests require a nonempty `check` value, but never open the record or verify its verdict, checker, or matching claim.
Candidate references can point to an `unverified` claim. Findings can omit supporting claims entirely.
Empty specifications bypass the rule requiring every applicable field, without an enforced discovery-phase distinction.

Review diagnostics supplied three separate modified inventory objects to all seven inventory tests. Each object passed:

- A documented claim pointing to a nonexistent check file.
- A populated specification referencing an unverified claim.
- A finding with no supporting claim references.

These objects existed only in memory. The canonical inventory remains unchanged and contains no claims.

The documentation overstates what the current tests enforce. Describing them as structural checks would accurately represent the initialization.
Stronger checks can develop with the evidence format when actual claims are added.
This review no longer asks for a new check-record schema or expanded validator now.

**F05: cost-benefit design accepted and deferred**

Locations: [assessment-protocol.md](../assessment-protocol.md), Criteria and Scale and cost. [work-plan.md](../work-plan.md), steps 2 through 5.
[options-inventory.json](../options-inventory.json), scaling and engineering-effort fields.

Cost and benefit are already part of the work plan. Detailed criteria and targets can develop through discussion and evidence.
The previous request for a requirements table and a changed assessment sequence exceeded the initialization review's purpose.
There is no request to change the phase order or set thresholds now.

Retain two issues for that later work: distinguish project estimates from source facts, and distinguish pilot spending limits from production budgets.
The schema's treatment of inferred engineering effort can be revisited when estimates are introduced.

**F06: retain modest simplification advice, withdraw added process**

Locations: [CLAUDE.md](../../CLAUDE.md), Conventions and Gotchas. [document rules](../../.claude/rules/docs.md).
[development-workflow.md](../development-workflow.md) and [discovery-plan.md](../discovery-plan.md).

The root instructions are 91 lines, which is reasonable. Their duplication is the larger issue.
Writing rules and evidence policy recur in scoped rules. Phase status and review instructions recur across several documents.
Hard word limits and banned punctuation add editing work without ensuring clarity.

`documented`: Anthropic recommends concise project instructions, scoped rules, and task-specific skills.
It advises removing material that can be inferred and moving detailed reference material out of the always-loaded file.
Sources: [Claude Code best practices](https://code.claude.com/docs/en/best-practices) and [project memory](https://code.claude.com/docs/en/memory), accessed 2026-09-09.

The existing `CLAUDE.md`, scoped rules, and check skill follow those mechanisms.
The direct instruction from `AGENTS.md` to read shared guidance also avoids maintaining two convention sets.
There is no demonstrated need for more skills, hooks, agent definitions, or infrastructure scaffolding.

Prune duplicated guidance when it is next edited. Keep the existing structure and room to adapt the workflow together.
The previous demand for an early-screening process and a formal stopping condition is withdrawn.

**Additional scope clarification**

The original prompt uses HydroBASINS in connection with water-body delineation. Keep that distinction explicit when watershed work resumes.
`documented`: HydroBASINS represents sub-basin boundaries. HydroLAKES represents lake shorelines, with a minimum target area of 10 hectares.
Sources: [HydroBASINS](https://www.hydrosheds.org/products/hydrobasins) and [HydroLAKES](https://www.hydrosheds.org/products/hydrolakes), accessed 2026-09-09.
Neither establishes a complete source of the smallest pond polygons required here. Pilot-source suitability remains unverified.

**Verification and limits**

Read the repository's guidance, documents, configuration, tests, inventory, workload declarations, and supplied 13-page PDF.
Compared the weather repository's overview, agent guidance, and assessment organization. Reviewed official Claude Code guidance and selected primary scientific/provider pages.
Accepted decision 0001 as the repository's record of prior owner answers. The original clarification transcript was outside this review.

The baseline check workflow passed: `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`.
Baseline result: 32 tests passed in 0.03 seconds. Uv needed approved access to its cache outside the workspace.
The three additional validator diagnostics passed invalid objects, demonstrating F04.
The full check workflow also passed after adding the initial review: 33 tests passed in 0.02 seconds.
This revision changes the review's interpretation and requested follow-up. It introduces no new research or implementation claims.
The full check workflow passed for this revision: 33 tests passed in 0.03 seconds.

No imagery reads, live benchmarks, deployment checks, or complete scientific claim re-verification were performed.
Passing documentation and schema tests does not establish provider completeness, water-quality fitness, or production cost.
This is an AI review. Owner and engineering acceptance remain separate.

**Joint follow-up**

Use this review as context for continued work among the owner, Codex, and Claude Code.
Keep factual wording accurate and open issues visible. Develop each part of the workflow together when it becomes relevant.
This review adds no prerequisite to discovery and requests no immediate extraction-geometry decisions.
