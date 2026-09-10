# Codex discovery review, 2026-09-10

Reviewer: Codex, an AI coding agent. Scope: technical accuracy and relevance of the updated discovery documentation.

The documentation provides a useful foundation for the intended AWS assessment. Its strongest additions are the issue register, explicit provenance, and separation of facts from estimates.
Several summaries overstate their evidence, however. These could distort the presentation, route comparison, or later cost analysis.
Correcting them is documentation work. The findings below do not require choosing an architecture or resolving open scientific questions now.

[Decision 0002](../decisions/0002-aws-source-pixel-classes-tile-provenance.md) supplies the review's scope: AWS sources, the selected pixel classes, retained tile provenance, and deferred adjacency handling.
Those directions remain the basis for subsequent joint work.

## Review coverage

I reviewed the plans, assumptions, draft contract, best practices, decisions, discovery reviews, inventory, supporting check records, and documentation checks.
I examined all 26 issue summaries and 20 findings, with targeted primary-source verification of claims affecting AWS ingestion and processing.
The inventory contains 319 claims, 120 sources, and 22 candidates. This review does not independently certify every claim or price.

External sources below were accessed on 2026-09-10. No imagery, raster headers, or requester-pays objects were read.
Public catalog metadata was inspected. It establishes collection descriptions, not archive completeness or delivered pixel values.

Findings identify existing records in the [inventory](../options-inventory.json) and [best-practices document](../s2-best-practices.md).
External facts are documented by the linked primary sources. Consequences and recommended wording are review judgments.

## Findings

### D01. Earth Search offset handling is summarized incorrectly

**Priority: high. Locations: I-05, F-01, P8, and the draft contract's value fields.**

I-05 and F-01 say Earth Search does not apply offsets. Element 84 explicitly documents that offsets were applied during conversion for some COG items.
The delivered asset's scale and offset describe the remaining conversion. This supports per-asset handling, not one conversion state for the route.
See the [Earth Search README, gain/offset section](https://raw.githubusercontent.com/Element84/earth-search/main/README.md).

The [draft contract](../data-contract.md) also leaves two offset conventions under the same field name:

- ESA product metadata: reflectance = `(DN + BOA_ADD_OFFSET) / QUANTIFICATION_VALUE`.
- STAC raster metadata: reflectance = `stored_value * scale + offset`.

For example, `(1200 - 1000) / 10000` and `1200 * 0.0001 - 0.1` both produce `0.02`.
An offset in reflectance units cannot be substituted into the ESA formula. See [ESA's radiometric conversion description](https://sentiwiki.copernicus.eu/web/s2-products).

Clarify the representations and correct the summaries. The final field design can remain draft.

### D02. Sampled catalog assets do not establish missing bucket layers

**Priority: high. Locations: I-26, F-07, and the two AWS `quality_layers` claims.**

I-26 says cloud probability exists on only one AWS route. Its Sinergise evidence lists JP2 assets observed through one Earth Search item.
The claim's own note says the bucket README does not enumerate quality layers. An incomplete catalog asset list cannot establish absence from the bucket.

The comparison also uses a Collection 1 COG item and an item from the older `sentinel-2-l2a` collection.
Collection, processing baseline, and file format are therefore confounded.

Replace route-wide assertions with the observed sample results. Keep availability across collections, baselines, and bucket contents unverified.
This changes the strength of the finding without requiring a product probe now.
The provider documents both JP2 and COG assets within its older collection in the [Earth Search README](https://raw.githubusercontent.com/Element84/earth-search/main/README.md).

### D03. Cloud dilation has exceptions that change the pond conclusion

**Priority: high. Locations: I-01, Q8, P12, and the CLAUDE.md cloud gotcha.**

The documents turn an 80 m dilation into a claim that any nearby cloud pixel flags the whole pond.
ESA specifies additional conditions: cloud probability above 65%, no dilation for clouds of three pixels or fewer, and restrictions near shorelines and other boundaries.
Urban areas have another size condition. See [SentiWiki, cloud and shadow dilation](https://sentiwiki.copernicus.eu/web/s2-processing).

Retain the risk that dilation can flag an entire small pond. Remove the unconditional claim and the unmeasured assertion about usable-scene loss.
Cloud handling remains open under the owner's direction.

Likewise, I-12's title says the classifier cannot see a pond. A 150 m auxiliary map does not prove that impossibility.
The same [processing description](https://sentiwiki.copernicus.eu/web/s2-processing) includes spectral classification before auxiliary cleanup. Q4 already states the defensible limit: small-pond performance is unmeasured.

### D04. Historical coverage claims lose their date and collection limits

**Priority: medium. Locations: I-08, I-17, F-08, F-09, and `not_assessed`.**

The claimed Collection 1 gaps come from a README statement explicitly dated April 2024.
That is evidence of a historical limitation, not verified coverage in September 2026. The canonical claim retains this date, but the summaries omit it.
See the [Earth Search Collection 1 description](https://raw.githubusercontent.com/Element84/earth-search/main/README.md).

The inventory excludes `sentinel-2-pre-c1-l2a` as outside the seven access routes. It is a collection within an already assessed AWS route.
Its [current catalog description](https://earth-search.aws.element84.com/v1/collections/sentinel-2-pre-c1-l2a) identifies pre-Collection 1 data with baseline below 05.00.
That makes it relevant to historical availability and conversion semantics.

Keep current completeness unresolved. Distinguish provider, bucket, collection, and processing revision when describing coverage.
This is an issue to track, not a request to choose the history scenario now.

### D05. Acquisition year is conflated with processing version, and R5 is stale

**Priority: medium. Locations: G7, R5, P4, P9, I-08, assumption A10, and CLAUDE.md.**

G7 says a 2017 history therefore spans three registration regimes. That conclusion concerns original processing, not every archive containing 2017 acquisitions.
G8 already explains that Collection 1 reprocessed earlier acquisitions with later improvements. Carry this qualification into P4 and the root guidance.
The [ESA collection description](https://sentiwiki.copernicus.eu/web/s2-processing) supports distinguishing acquisition date from processing history.

R5 presents 05.10 as the continuing operational baseline. ESA announced deployment of 05.12 for 2026-02-04.
See the [05.12 deployment announcement](https://sentinels.copernicus.eu/web/sentinel/-/deployment-of-sentinel-2-processing-baseline-in-version-05.12-on-4-february).

This update also matters to efficiency. Baseline 05.12 introduces JPEG 2000 tile-part length markers to improve access to small image regions.
Include this version dependency in I-19's comparison. It establishes a relevant capability, not a measured AWS speed advantage.
See [ESA's TLM announcement](https://sentinels.copernicus.eu/web/sentinel/-/introduction-of-tile-part-length-tlm-markers-in-sentinel-2-jpeg2000-images).

A10 contains a smaller calendar error. The workload's 2021-01-01 boundary precedes both refinement rollout dates, rather than falling between them.

### D06. Library defaults become asset specifications and compute conclusions

**Priority: medium. Locations: I-19, I-20, F-06, and F-14.**

The 512-pixel figure cited for Earth Search assets is GDAL's COG creation default.
The supporting claim explicitly says it does not describe a particular Sentinel-2 asset. See the [GDAL COG driver](https://gdal.org/en/stable/drivers/raster/cog.html).

File blocks, HTTP fetch sizes, and array chunks are different quantities. The 16 KB and 1024-pixel defaults do not specify every workflow's actual reads.
Retain them as named tool defaults. Leave request counts, bytes, cache reuse, and decode cost unmeasured.

F-14 also concludes that windowed work fits Lambda and whole-tile work requires a container.
The [Lambda limits](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html) establish resource ceilings, not either workload's actual runtime or memory use.
Describe windowed work as a plausible fit and whole-tile processing as a resource concern. Neither conclusion is established by compressed product size alone.

### D07. Storage charges do not establish the proposed partition rule

**Priority: medium. Locations: I-23, F-16, and `cl-sl-lakehouse-table-scaling_water_bodies`.**

F-16 implies each chip or water-body partition incurs the listed catalog and table charges at every scene.
Glue bills catalog metadata objects, which are distinct from S3 data objects. Its pricing also includes a free allowance.
See [AWS Glue pricing](https://aws.amazon.com/glue/pricing/).

An object-storage chip does not automatically create a Glue metadata object or an S3 Tables object.
Similarly, an Iceberg partition is not automatically a separately registered Glue partition.
AWS describes partition metadata within Iceberg's files in its [Iceberg table overview](https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/getting-started.html).
These mappings depend on the candidate layout and catalog integration.

I-23 then declares partitioning by tile/date mandatory and cold storage unsuitable for per-pond chips.
Minimum charges alone cannot establish either conclusion. Object sizes, retention, access frequency, and the services actually used remain inputs to the comparison.
Record these as cost considerations. Remove the unselected layout rule and its `decided` status.

### D08. Snapshot retention is conflated with retention of logical revisions

**Priority: medium. Locations: I-22, F-15, and C-02.**

The documents imply snapshot formats delete history by default and require every snapshot to survive forever.
[Iceberg](https://iceberg.apache.org/docs/latest/maintenance/) and [Icechunk](https://icechunk.io/en/latest/understanding/expiration/) document explicit expiration operations.
[S3 Tables](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-maintenance.html) separately provides automatic maintenance. These are different operational behaviors.

Snapshot expiration removes historical snapshot access. It does not necessarily remove older observation revisions retained as records in the current dataset.
This distinction follows from the documented retention of files still referenced by surviving snapshots.

The draft's immutable observation revisions therefore do not, by themselves, require retaining every physical snapshot.
Record snapshot time travel and logical revision history as separate considerations. The choice of retention policy can remain open.

### D09. Same-orbit cancellation is generalized to all registration error

**Priority: medium. Locations: G10, P5, I-10, and decision 0002's rationale.**

The source studies systematic DEM-related orthorectification offsets in glacier displacement measurements.
Its cancellation argument concerns the common systematic component when comparing images from the same orbital path.
See the [original glacier study](https://tc.copernicus.org/articles/16/2629/2022/).

That does not establish cancellation of every registration error, absolute agreement with a water-body polygon, or invariant processing across revisions.
Describe same-orbit filtering as reducing one source of inconsistency. Avoid promising pixel stability from the orbit identifier alone.
The decision to retain orbit and tile provenance remains well motivated.

### D10. The adjacency study supports a caveat, not a universal distance

**Priority: medium. Locations: Q6, I-02, and the discovery review's report corrections.**

The cited study compares chlorophyll retrieval errors in distance groups below and above 5 km from shore.
That analysis does not isolate a universal adjacency radius for delivered Sentinel-2 Level-2A reflectance.
See [section 3.3 of the original study](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2024.1423332/full).

Retain a short statement that surrounding land can bias water observations and effects can extend beyond a narrow shoreline buffer.
Keep distance and magnitude conditional on the setting and processing method. The owner's modeling-team deferral remains appropriate.

The discovery review also attributes an adjacency-distance error to the supplied geolocation PDF.
The [reference provenance](../references/README.md) says that PDF does not cover adjacency. Reconcile this attribution before repeating it in the presentation.

## Relevance and remaining issue coverage

The four comparison dimensions fit the engineering handoff. Native resolution, offsets, quality layers, tile provenance, revisions, read efficiency, and operating costs all belong here.
The assessment benefits from keeping unresolved questions visible without turning them into specifications.

Three additions or clarifications would improve discovery coverage:

- **Completeness and recovery.** Distinguish a source observation from a catalog item, an asset-ready product, and a successfully published internal record.
  Existing retry claims cover part of this. Track delayed assets, missed or repeated updates, catalog omissions, and recovery as one ingestion issue.
  Earth Search documents item notifications through [its SNS topic](https://raw.githubusercontent.com/Element84/earth-search/main/README.md).
  Generic [S3 notification configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html) is not an established integration with a provider-owned bucket.
- **Comparison coverage.** C-03 pairs JP2 exclusively with whole-tile fetching, although I-19 acknowledges partial decoding.
  Preserve JP2 windowed reads as an option to assess. Otherwise, source format and workflow differ simultaneously in the comparison.
- **Interpretation of static pixel classes.** Record that polygon-derived interior and shoreline labels describe the reference geometry, not verified water presence on every date.
  Changing water extent, shallow bottoms, and floating vegetation are interpretation issues to hand off alongside existing glint and adjacency caveats.
  This requires no change to the selected extraction geometry.

There are also small consistency corrections:

- I-21 selects content-addressed publication, although the draft contract establishes immutable revisions without selecting that mechanism.
- The contract says no field is selected, while decision 0002 selects pixel classes and tile provenance.
- Non-AWS combinations C-04 through C-06 remain in the HTML's main combinations section without the candidates' context distinction.
- CLAUDE.md repeats older offset, cloud, registration, and archive-retention summaries. Link to corrected canonical explanations to reduce future drift.

These are wording and scope corrections. They do not call for more folders, another workflow, or immediate implementation choices.

## Verification and changes

The check-record bindings and generated-file checks are useful improvements over initialization.
They establish consistency, not whether every conclusion follows from its cited evidence.

A bounded diagnostic found one coverage mismatch in [test_inventory.py](../../tests/test_inventory.py).
`test_issues_cite_evidence` accepts any matching G/R/Q identifier without checking that the best-practices claim exists.
An in-memory substitution of `G99` passed that test. No repository data was changed by the diagnostic.

This review adds this file and an entry to the [review index](README.md). Existing assessment changes remain intact.
The [required check workflow](../../.claude/skills/check/SKILL.md) passed on 2026-09-10:

| Command | Outcome |
|---|---|
| `uv sync --locked` | Passed |
| `uv run ruff check .` | Passed |
| `uv run ruff format --check .` | Passed |
| `uv run pytest -q` | 41 passed in 0.15 seconds |
| `git diff --check` | Passed |

The tests include inventory collation and HTML freshness checks. No AWS performance, archive completeness, or scientific validation was measured.

The next proposed step is to address these documentation findings jointly, then use the corrected discovery record to develop presentation guidance.
