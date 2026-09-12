# Independent AWS archive comparison, 2026-09-11

The revised understanding is substantially correct: both AWS buckets provide overlapping Sentinel-2 COG archives through Earth Search.
Our earlier framing overstated the distinction between the older archive and the newer one.
However, the revised presentation still overstates product equivalence, processing consistency, and cost equality.

The useful distinction is between **where a product is published** and **which processing produced its values**.
The bucket name alone does not answer the second question.

## Scope and independence

The owner requested an independent source review, followed by comparison with Claude Code's updated documentation and HTML.
Research agent `/root/independent_archives` established findings from primary documentation before reading repository conclusions.
Checking agent `/root/check_archive_claims`, using `gpt-5.6-sol`, independently checked the central claims.
Codex compared those findings with the [archive revision](2026-09-11-archive-lineage.md), presentation template, inventory, and saved survey evidence.
Sources were accessed on 2026-09-11.

This change adds this review and its index entry. Existing source claims, presentation, decisions, and survey results remain available for joint review.
No provider script or pixel download ran. Individual item URLs failed in the browser tool, so item comparisons used saved catalog evidence.

## Where the updated understanding holds

| Question | Independent result | Evidence status |
|---|---|---|
| Are these two different sensors or processing levels? | Both archives expose Sentinel-2 Level-2A products. Earth Search is the catalog, and the COGs are converted publication copies. | Documented: [Earth Search documentation](https://github.com/Element84/earth-search/blob/main/README.md) |
| Is the older archive limited to JPEG 2000? | No. Its COGs are in `sentinel-cogs`. Collection 1 COGs are in `e84-earth-search-sentinel-data`. Both advertise anonymous access in Oregon. | Documented: [AWS COG registry](https://registry.opendata.aws/sentinel-2-l2a-cogs/) |
| Does the older archive contain reprocessed products? | Yes. The survey found originals beside reprocessed versions, including baseline 05.00 products for 2021. | Measured: [survey report](2026-09-10-gap-survey-report.json), GS-07 |
| Can they describe the same ESA product? | Yes. Shared product identifiers occur in the saved listings, including the Lake Lanier example. Identical pixels remain unverified. | Measured metadata: [probe](../assessment-checks/probes-2026-09-11.json), PR-08, and offline checks below |
| Can the older COGs help fill history? | Yes. The catalog and header survey supports their use as a candidate fallback, subject to the existing quality and value-conversion questions. | Measured: report GS-10 and GS-11 |
| Why prefer the newer archive at all? | Its intended replacement role and the survey's more consistent asset delivery are useful reasons to consider it first. They do not establish universal superiority. | Documented intent plus inference from survey GS-06 |

## Corrections to the revised presentation

### 1. High: distinguish ESA Collection 1 from Earth Search's collection label

Location: [template](../../tools/s2-options.template.html), archive table, “Processing versions” and “What it holds”.

Earth Search documents a baseline threshold of 05.00, while ESA defines its historical reprocessing using specific baselines.
ESA's 2022–2023 reprocessing is complete. Earth Search's April 2024 explanation of incomplete ESA reprocessing is historical.
Sources: [ESA baseline table](https://sentiwiki.copernicus.eu/web/s2-processing#Collection-1ProcessingBaseline) and [completed Phase 2 publication](https://dataspace.copernicus.eu/news/2025-9-8-sentinel-2-collection-1-phase-2-products-availability). Status: documented.

The survey found 4,036 baseline 05.09 items for 2023 in Earth Search's newer collection across the 29 tiles outside Alaska.
ESA's reference catalog serves reprocessed 05.10 and 05.11 products there. Status: measured, report GS-02.
Therefore, “only what ESA has reprocessed, plus every new pass” is inaccurate.
The archive also has omissions, so “every new pass” is unsupported.

Why it matters: even the newer archive alone mixes processing histories. Adding older COGs does not introduce every consistency problem from scratch.
The presentation's “longer, more consistent record” confuses improved coverage with demonstrated comparability.
Describe a longer record with processing differences that still need assessment.

### 2. High: shared asset names do not establish equivalent files or quality delivery

Location: template, “What is the same”, “What differs”, and the opening promise to avoid JPEG 2000 entirely.

PR-08 establishes matching product provenance and shared asset names. Its recorded scale and offset comparison concerns the red asset's catalog metadata.
It does not establish equality of all files, their embedded metadata, or decoded pixels.
Replace “same 22 files” with “22 shared asset names”. Keep the pixel-equality limitation beside that statement.

The saved survey also records a material delivery difference.
Older items using software `2025.03.06` expose cloud and snow probabilities as JPEG 2000 assets in `sentinel-s2-l2a`.
The newer collection's sampled counterparts expose those layers as COGs.
Most selected historical fallback items lack these probability layers altogether.
Status: measured, [measurements](../measurements.md), findings 6 and 10, and `gap-survey.json` → `asset_samples`.

Why it matters: reading available fallback bands and scene classifications as COGs does not guarantee identical quality inputs.
“Never touch the original” is a proposed access restriction, with consequences for which ancillary layers are available.

Keep the existing offset comparison open. “File's own offset” currently means STAC asset metadata, not a verified value read from the GeoTIFF.

### 3. Medium: separate access charges from processing cost

Location: template, “Who pays to read”, the three pull-effort cards, and the concluding archive tradeoff.

Both COG buckets advertise anonymous access without requester-pays billing. Status: documented, AWS COG registry.
That supports the same source-access billing category, not identical download size, decoding time, or total workflow cost.
Replace “No one” with “No source-access charge to us”. Retain our compute, storage, and network costs as separate considerations.
[AWS billing documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html) distinguishes reader charges from costs paid by the bucket owner.

The JP2 card says an AWS identity is required, despite its table acknowledging conflicting documentation.
The [current registry](https://registry.opendata.aws/sentinel-2/) advertises anonymous access to `sentinel-s2-l2a`.
The [older L2A readme](https://roda.sentinel-hub.com/sentinel-s2-l2a/readme.html) says requester pays. Status: documented conflict.
Do not present requester-pays prices as established charges for our L2A access.

Why it matters: the low/medium/high labels are planning judgments. No relative reading cost or runtime has been measured.
The common COG format is useful, but it does not settle the cost comparison.

### 4. Medium: remove guarantees about one product per date and replacement

Location: template, “Collection 1 gives one product per date” and “A reprocessing replaces the original”.

The existing survey found 628 acquisition groups with two newer-collection items, including one group with different baselines.
Status: measured, report GS-07. This repeats the issue corrected in [the previous Codex review](2026-09-10-codex-gap-survey-review.md), GR01.

The survey is a snapshot. It cannot establish a universal future replacement or retention policy.
The provider documents eventual replacement of the older collection, not a guarantee of one product per date in the newer one.

Why it matters: split products can contain different coverage. Selecting one by date can discard useful data.
Say the newer archive had fewer competing versions in our sample, while both require product identity.

## Smaller documentation corrections

- The registry's “Managed By Element 84” describes dataset management. Calling it merely registry-entry editing understates the source. Legal bucket ownership remains undocumented.
- PR-08's October 2025 example cannot itself prove continued ingestion in September 2026. The saved September 2026 pair below supports recent concurrent cataloging.
- The archive revision says inventory findings F-11 and F-12 record pull cost and lineage. They actually concern raw-pixel access and compute deduplication.
- The updated COG direction still conflicts with A13 and decision 0003's JPEG 2000 wording. Record the correction without implying a new processing workflow selection.

## Additional offline evidence checks

Codex verified the recorded SHA-256 digests of both saved `17SKU` collection listings in [gap-survey.json](../../benchmarks/results/gap-survey.json).
The listings contain 158 shared product identifiers for 2021, including reprocessed baseline 05.00 products.
For example, both reference `S2A_MSIL2A_20211230T162701_N0500_R040_T17SKU_20221231T094427.SAFE`.
This directly establishes overlapping reprocessed holdings for this tile, without relying on external issue reports.

Both also reference `S2B_MSIL2A_20260907T160819_N0512_R140_T17SKU_20260907T200253.SAFE`.
The newer entry's creation timestamp is `2026-09-07T21:16:28.238Z`, and the older entry's is `2026-09-07T21:15:48.603Z`.
This supports recent parallel cataloging. It does not guarantee current ingestion rates, retirement timing, or availability of every linked asset.

## Disposition and next discussion

The earlier distinction between an older JPEG 2000 route and a newer COG route is **corrected with evidence**.
Offset fidelity, processing comparability, and asset completeness remain **accepted and deferred** to the existing prototype questions.
The four presentation findings above remain open for correction. The stored survey counts remain useful.

We can assess the archives as overlapping sources, asking which products and quality layers each contributes for the required dates.
Collection 1 first with older COG fallback remains defensible. An older-archive-first approach cannot be rejected solely because of its age or format.
Its comparative coverage, version handling, quality inputs, and value fidelity determine that assessment.
No selection among those approaches is made here.

Proposed next step: discuss these distinctions with the owner and Claude Code, then revise the archive explanation accordingly.

## Verification

`uv sync --locked`, `uv run ruff check .`, and `uv run ruff format --check .` passed.
`uv run pytest -q` passed: 64 tests in 0.21 seconds.
These checks establish repository consistency, not scientific equivalence between archives.
