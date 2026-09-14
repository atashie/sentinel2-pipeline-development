# Stage 1 evidence and documentation review, 2026-09-14

Reviewer: Codex, with separate primary-source research and checking agents.

Reviewed [Claude Code's record](2026-09-14-prototype-structure-and-stage-1.md), the working-tree code, saved results, inventory changes, and presentation.
The working tree starts from `67ecd1a` and includes the previous pilot review. Nothing was staged when this review began.

## Assessment

The workload stages fit the assessment goal. The harness is small, and the results provide useful laptop smoke measurements.
The saved medians are reproducible. Several explanations exceed the evidence, and two reuse or comparison safeguards need attention before further measurements.
Keep the agreed stage order. Full scientific validation can remain in stage 5, with the current conversion explanation labeled as provisional.

This review adds this record and its index entry. It leaves the implementation, evidence files, and presentation unchanged for Claude Code's response.
No imagery download, provider script, next-stage experiment, commit, or deployment ran.

## Findings

### 1. High: the exact clamp rule is presented as measured without being tested

Locations: [measurement finding 15](../measurements.md#15-the-copies-hold-the-same-picture-in-different-units), [comparison helper](../../benchmarks/copy_difference.py), and [presentation template](../../tools/s2-options.template.html), line 916.
The same assertion appears in inventory finding F-23, issue I-05, the `CLAUDE.md` gotcha, and the proposed stage 2 instruction.

`compare_arrays()` records differences, common difference counts, extrema, and no-data agreement. It never counts violations of `older = max(c1 - 1000, 1)`.
The reported 1.7 percent and 0.02 percent are shares whose difference differs from −1,000. They are not direct counts of negative reflectance.
Zero handling and the 641 equal valid `nir09` pixels also need explicit accounting before claiming a rule for every valid pixel.
Those equal pixels could fit the proposed rule when both values are 1. Their existence alone does not disprove it.

An offline counterexample demonstrates the missing check:

| Fixture | Collection 1 values | Older values | Obeys the proposed rule on valid pixels |
|---|---|---|---|
| A | `[0, 100, 2000]` | `[0, 1, 1000]` | Yes |
| B | `[0, 101, 2000]` | `[0, 2, 1000]` | No |

The current helper returns exactly the same comparison record for both fixtures, including extrema and no-data agreement.

The provider described legacy offset application and clamping in 2023. That supports the mechanism, not exact compliance by every pixel of this product.
See [source checks below](#source-checks).

**Correction requested:** say the sampled differences are consistent with offset application and clamping.
Describe −1,000 as the dominant measured difference. Keep the exact formula, threshold counts, and water-specific consequences unverified.
Retain the directly measured no-data agreement and identical scene classification.
Do not generalize this 05.11 product to the mixed 04.00 fallback items or all later stage 2 scenes.

At the authorized scientific check, compare each valid pixel against the declared formula and record violations and threshold counts.
Keep source no-data separate. No additional download is required merely to correct today's wording.

### 2. High: resuming can silently reuse another tile, date, or asset set

Location: [raw_access.py](../../benchmarks/raw_access.py), `reusable_result()` at line 376 and its call at line 461.

Reuse checks only a filename and the absence of `error`. The filename contains copy, group, mode, repetition, and position in the plan.
It contains no tile, date, product, asset identity, or reader configuration.
The parent searches the catalog again, then labels reused results with the newly selected product and current machine metadata.
Changing `--tile` or `--date` while retaining the same plan can therefore produce plausible results under the wrong product.

An offline fixture confirmed that reuse accepts an unrelated asset URL and an incomplete band group.
For this saved rerun, all nine reused records match their original files exactly. Every successful record's asset keys and URLs match its declared assets.
There is no evidence that this pass mixed products.

**Correction requested before further reuse:** compare the saved specification with the requested specification, excluding output paths.
Bind the product, asset keys and URLs, reader configuration, and implementation version. Preserve original worker provenance when reusing a measurement.
Add fixtures that reject a changed date or asset set. A small validation helper is sufficient.

### 3. Medium: failed JP2 access does not establish a credential requirement

Locations: [template](../../tools/s2-options.template.html), lines 905–906, [measurement finding 14](../measurements.md#14-the-two-copies-are-laid-out-differently-and-the-older-copys-quality-layers-differ), and [run record](2026-09-14-prototype-structure-and-stage-1.md).

The page calls the bucket credential-gated and says fallback requires another reader and credentials.
The six range-mode failures show a `/vsis3/.../CLD_20m.jp2` open error. The six whole-object failures show an unsupported `s3://` request path.
Neither records an authorization response establishing the object's access policy. All twelve stop at `cloud`, before `snow` is attempted.
The installed GDAL environment lists `JP2OpenJPEG`. This reader supports JPEG 2000, although this test did not establish these objects' readability.

The current AWS registry explicitly documents unsigned access to `sentinel-s2-l2a`. The older provider README conflicts, as [the source checks](#source-checks) record.

**Correction requested:** describe cloud and snow as JP2 links excluded from this GeoTIFF benchmark.
Describe the failure as an access-path or reader-configuration failure with the exact saved errors. Remove the asserted credential requirement.
Keep any future unsigned JP2 probe separate and owner-invoked.

The current product also does not establish cloud and snow availability for 2022 fallback items.
[Measurement finding 10](../measurements.md#10-the-older-collections-geotiffs-cover-the-missing-2022-acquisitions) records that most selected historical fallback items lack those catalog assets entirely.

### 4. Medium: the claimed network-counter agreement is incorrect

Location: [run record](2026-09-14-prototype-structure-and-stage-1.md), line 102.

Using `abs(net.bytes_recv / totals.bytes_requested - 1) <= 0.05` gives:

| Evidence | Successful runs | Within 5 percent |
|---|---:|---:|
| [Initial pass](../../benchmarks/results/raw-access.json) | 48 | 29 |
| [Older-copy rerun](../../benchmarks/results/raw-access-older-quality-all.json) | 12 | 9 |
| Combined | 60 | 38 |

The stated 46 of 48 is unsupported. One rerun counter records about 9 percent of the requested bytes.
The cause remains unknown. Machine-wide counters can include unrelated traffic and cannot independently establish per-process delivery.
The `net_counters()` docstring incorrectly calls them process-wide, although the result limitations correctly say machine-wide.

All 30 successful range-read logs reproduce their reported request and requested-byte totals exactly.
That checks the parser against its input. It does not turn requested ranges into a measurement of delivered network bytes.

**Correction requested:** replace the agreement count, remove “both instruments stand,” and retain separate labels for requested bytes and machine-wide received bytes.

### 5. Medium: the scientific comparator needs product and grid guards

Locations: [raw_access.py](../../benchmarks/raw_access.py), `pair_items()` at line 132, and [copy_difference.py](../../benchmarks/copy_difference.py), lines 86–105.

If no common ESA product exists, `pair_items()` selects the first item from each collection and continues.
The comparator checks array shape but does not enforce matching CRS and affine transform before subtracting pixels.
Equal dimensions do not establish corresponding ground locations.
The current saved sample passes these checks independently: the product is shared, and all four directly compared arrays have matching grids.

**Correction requested before reusing this comparator:** require a common product and matching dimensions, CRS, and transform for a same-product pixel comparison.
Return an explicit unmatched result otherwise. Keep comparisons across different products or grids separately declared.
Add fixtures for no common product and a shifted grid with the same shape.

### 6. Medium: measurements need clearer scope before supporting cost or method claims

Locations: [worker](../../benchmarks/raw_access.py), lines 230–238 and 285–331, and [template](../../tools/s2-options.template.html), lines 892–917.

The timing loop includes hashing, extrema, and no-data counting. `array.tobytes()` also makes a full copy for hashing.
Wall time and CPU therefore cover the instrumented read, while peak RSS also includes diagnostic allocations and process startup.
These are useful smoke measurements. They are not isolated transfer, decode, or future extraction memory requirements.

The table's single peak-memory column takes the maximum across both copies and both modes.
Its label does not explain that aggregation. The quality and all-band rows also compare different asset sets and different auxiliary grids.

Whole-object reads were faster for the 10 m, 20 m, and all-band groups in this sample.
Range reads were faster for both 60 m groups and Collection 1 quality layers.
The fixed execution order and uncontrolled connection do not isolate request count as the cause of the timing differences.

**Correction requested:** retain the observed medians, label timing as instrumented read time, and label peak RSS as the maximum across configurations.
State that quality and all-band workloads differ between copies. Present request latency as an explanation consistent with the observations.
Replace the blanket statement that request count dominates whole-tile work.

Before later cost accounting, count every HTTP attempt. Whole-object results currently hard-code one request even when `Client` retries.
No saved successful whole-object run retried, so this defect does not change today's request totals.

### 7. Low: current-status prose and a few numbers need reconciliation

The [README](../../README.md), [work-plan introduction](../work-plan.md), and Prototyping introduction still lead with preparation alone.
Stage 1 results appear only after two preparation chapters. The lead needs to acknowledge the completed access test while keeping extraction tests pending.
The existing statement that pilot extraction has not run remains correct.

Suggested lead: “Initial whole-tile access measurements are complete on one laptop and one acquisition. Lake extraction, AWS performance, and scientific validation remain open.”

Additional corrections:

- The comparison read six asset pairs, or twelve objects. Its saved requested ranges total 335,020,511 bytes, not the record's approximately 270 MB.
- The record's pre-run limits say nothing was read and the parser was not observed live. Label those paragraphs as historical design notes.
- “Only two outliers” lacks a declared criterion. Another Collection 1 20 m run took 36.147 seconds against a 20.208-second median.
- “Same bytes” means similar volume, not identical stored or decoded content. All twelve reflectance-band digests differ between copies.
- The HTML rounds 1.5–1.8-second medians to 2 seconds. Preserve one decimal below 10 seconds if these comparisons remain in the table.
- F-23 cites existing source claims without a direct machine-readable link to this measurement. Add an evidence pointer when revising it.

`collate_checks.py --check` preserves findings rather than checking their prose. Its success does not validate the newly added F-23 interpretation.

## Evidence that holds

Both raw-access summaries recompute exactly from their saved runs.
The original pass contains 48 successful and 12 failed runs. The rerun supplies twelve successful replacement runs.
Each successful copy and asset has one decoded digest across its groups, modes, and repetitions.
All twelve reflectance bands differ between copies. Scene classification agrees. Aerosol and water vapour use different grids in the sampled copies.

For Collection 1's 10 m bands, the medians are 56.123 seconds with range reads and 44.153 seconds with whole-object reads.
The request counts are 61 and 4. These numbers accurately describe this laptop sample.
The corresponding requested volumes are 507,641,506 and 681,508,514 bytes.

These checks use the three [saved results](../../benchmarks/README.md) and local GDAL logs. They establish no AWS throughput or cost estimate.

## Source checks

Access date: 2026-09-14. Research: `independent_archives`, parent model. Separate checker: `check_archive_claims`, GPT-5.6-sol.
Both agents fetched the cited primary documentation. Neither read imagery or tested the disputed JP2 objects.

| Claim | Verdict and primary evidence |
|---|---|
| L2A JP2 access requires credentials | Corrected. The [AWS registry](https://registry.opendata.aws/sentinel-2/) documents unsigned access. Its [source YAML](https://raw.githubusercontent.com/awslabs/open-data-registry/main/datasets/sentinel-2.yaml) sets RequesterPays false and eu-central-1. The [older README](https://roda.sentinel-hub.com/sentinel-s2-l2a/readme.html) conflicts. Object-level access remains untested here. |
| An S3 URL establishes authentication requirements | Corrected. [GDAL documents unsigned S3 access](https://gdal.org/en/stable/user/virtual_file_systems.html#vsis3-aws-s3-files). An unconfigured failure does not establish bucket policy. |
| This reader cannot decode JPEG 2000 | Corrected. [JP2OpenJPEG](https://gdal.org/en/stable/drivers/raster/jp2openjpeg.html) is a GDAL driver and is present locally. Specific-object readability and window efficiency remain untested. |
| Legacy conversion applied an offset and clamped low values | Confirmed as a dated mechanism. An Element 84 maintainer describes it in a [2023 discussion](https://github.com/Element84/earth-search/discussions/26). Exact zero handling is ambiguous in that prose. The [current README](https://github.com/Element84/earth-search#gainoffset-in-items-after-jan-25-2022) says only some items had offsets applied. Neither source establishes universal behavior or validates every pixel of this sample. |

## Verification and prior findings

- `uv sync --locked`: passed, 18 packages resolved and 16 checked.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed, 63 files already formatted.
- `uv run pytest -q`: 107 passed in 0.70 seconds after this review was added. Five dependency deprecation warnings.
- Inventory, HTML, and gap-report freshness checks: passed. The raw-access dry run prints 60 runs without provider access.
- Local evidence audit: medians, asset identities, reused records, grid metadata, digest consistency, and 30 request logs checked.
- Offline diagnostic fixtures: demonstrated the clamp-summary ambiguity and unchecked reuse. No application code or tests changed.

The previous pilot fixes remain accepted. Bounding-box tile discovery, pilot-report adaptation, and polygon revision handling remain accepted and deferred.
Those findings do not require changing the owner's prototype structure.

## Proposed next step

Claude Code can answer these findings and correct the active prose before it is presented as an established result.
Add reuse and comparison guards before invoking those paths again. Keep the original result files unchanged and document any later script differences.
Then review the bounded stage 2 statement with the owner. No stage 2 run starts from this review.
