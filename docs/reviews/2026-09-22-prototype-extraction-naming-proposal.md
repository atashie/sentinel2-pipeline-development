# Prototyping extraction names and reader context, 2026-09-22

Reviewer: Codex, directed by the repository owner.
Status: approved and [implemented for review](2026-09-22-prototype-extraction-naming-implementation.md).
The proposal and refinement history below record the basis for that implementation.

## Scope and evidence

The owner requested a complete Prototyping review and consistent names for extraction techniques, potentially combining workflow letters with numbers.
This review covered all seven sections and eleven tables, including expanded results and limitations, in the [presentation](../s2-options.html#prototyping).
Acceptance means every displayed extraction method has an explicit proposed mapping, with historical variants and timing limits preserved.

Sources inspected:

- The [template](../../tools/s2-options.template.html) and [renderer](../../tools/render_options.py), including generated row labels.
- The [individual-lake implementation](../../benchmarks/lake_extraction.py) and its [method definitions](2026-09-14-stage-2-one-lake-at-a-time.md#the-four-methods-per-scene).
- The [shared-image implementation](../../benchmarks/tile_extraction.py), [multiple-tile implementation](../../benchmarks/cross_tile_extraction.py), and [larger-workload readers](../../benchmarks/workload_readers.py).
- The [extraction walkthrough](2026-09-22-raster-lazy-extraction-walkthrough.md) and [timing review response](2026-09-22-sleep-rerun-review-response.md).

The [previous terminology revision](2026-09-18-prototype-method-clarity.md) connected four early approaches to later reader names.
The new comparison now needs explicit distinctions between the two lazy recipes.

## Findings

1. Section 02 mixes pixel selection with image reading in one list of four approaches.
2. Later tables alternate between raster mask, raster reader, raster, lazy stack, lazy array reader, improved lazy, and current lazy control.
3. The improved reader has no introductory diagram comparable to the workflow diagram.
4. Shared graphs, cached reads, and explicit block reuse remain difficult to distinguish from their labels.
5. The phrase current lazy control becomes ambiguous as implementations change. Improved also implies a general performance ranking.
6. Several historical limitations read as current claims, despite the later completed comparison.

These are presentation findings. They do not invalidate the saved measurements.

## Recommended categories

Use the letter for the workflow and the number for the reading technique.
Keep pixel selection as an explicit qualifier wherever it varies.

| Category | Question | Proposed values |
|---|---|---|
| Workflow | Which lakes and images are processed together, and how much is read? | A: each lake separately. B: share image windows. C: read the whole image |
| Reading technique | How does software request, compute, and reuse image data? | 1: direct raster reads. 2: large-chunk lazy reads. 3: source-block lazy reads |
| Pixel selection | Which pixels are retained, and how are their positions represented? | Boundary clip, prepared pixel mask, or stored pixel positions |
| Experiment settings | Under which conditions was this combination measured? | Cohort, acquisition, process arrangement, graph extent, chunk origin, threads, cache, source version, and timing scope |

Numbers identify techniques, not quality ranks, section numbers, implementation versions, or unique benchmark runs.
Scope these codes to workflow comparisons. Other project documents already use A1 and similar identifiers for assumptions.
The complete experimental identity still includes selection, inputs, settings, and provenance.

## Proposed reader definitions

The behavior below follows the inspected implementations and the independently checked [walkthrough](2026-09-22-raster-lazy-extraction-walkthrough.md).
These names describe the measured recipes. They are not an exhaustive classification of raster software.

| Number and canonical name | Explanation for the reader | Existing labels |
|---|---|---|
| **1 · Direct raster reads** | Call Rasterio directly for the requested windows or complete band. File lifetime follows the workflow. GDAL caches may serve repeated reads | Raster reader, Raster. The early clip, mask, and stored-position methods also use direct reads |
| **2 · Large-chunk lazy reads** | Build an array graph using configured chunks, historically 2,048 pixels per side. Windowed workflows compute each lake separately | Lazy stack, Lazy array reader, Current lazy control |
| **3 · Source-block lazy reads** | Align array chunks to TIFF blocks. Windowed workflows compute distinct required blocks in bounded batches, serving their requesting lakes before release | Improved lazy |

Explain a window as a requested rectangle, a source block as a TIFF storage unit, and a chunk as an array-processing unit.
Both lazy recipes use ODC/Dask and ultimately Rasterio/GDAL, as established in the walkthrough.
In windowed workflows, reader 3 changes both chunk alignment and how computations serve lakes.
Its name alone cannot explain a measured resource difference.

The workflow still changes each reader's behavior:

- A1 reopens bands for each lake. B1 retains open bands across lakes. C1 reads complete bands.
- A2 builds its graph on each lake window. B2 uses a full-image graph and computes lake windows separately.
- C2 computes complete bands through larger chunks.
- A3 serves the current lake's required blocks. B3 serves every member lake from each required block. C3 computes all source blocks.

The [reader 2 implementation](../../benchmarks/tile_extraction.py) anchors A2's graph at the lake window, so its chunk boundaries can shift between lakes.
B2 anchors its graph at the full native image grid. Changing A2 to B2 changes chunk placement as well as graph sharing.
This does not move the selected native pixels. It changes the chunks involved in retrieving them.

Windowed reader 3 takes its maximum batch size from the [thread setting](../../src/s2proto/workload_resources.py), `LIMITS["threads"]`.
That setting was two in these measurements. Two blocks is an experimental setting, not part of reader 3's definition.
C3 computes a complete band with `graph.compute()` and then gathers its lakes. It never enters the windowed batching loop.
Thus C3 uses source-block alignment without bounded batching.
The C1/C3 comparison also changes direct reading to ODC/Dask execution. It does not isolate alignment's performance effect.
Historical C2 observations use different inputs and settings, so comparing those with C3 cannot isolate alignment either.
Avoid naming reader 3 shared reads alone, because A3 does not share decoded arrays across lakes.

## Mapping the existing results

| Current section | Proposed displayed combinations | Required qualifiers |
|---|---|---|
| 02: individual lakes | A1 with boundary clip, A1 with prepared mask, A1 with stored positions, A2 with prepared mask | The clip omits required context and uses a different boundary rule |
| 03: lakes sharing an image | A1, B1, C1, B2 | Keep both A1 process arrangements and the separate-process baseline's different measurement basis |
| 04: lakes spanning tiles | A1, B1, A2, B2 | Retain workload medians, ranges, repetitions, and frozen implementation notes. Explain the A2/B2 chunk-origin difference |
| 05: larger workloads | A1, A3, B1, B2, B3, C1, C3 | Mark B2 as this comparison's control. Retain provenance, timing qualifications, resource settings, and C3's whole-band execution |

Each section 05 cohort has those seven combinations. A2 and C2 were not run for those cohorts.
The [shared-image evidence](../../benchmarks/results/tile-extraction.json) includes additional method-pattern combinations beyond the page's selected rows, including C2.
Do not label those combinations globally untested or add new displayed comparisons without preserving their evidence and selection qualifiers.

Keep the raw keys unchanged. Map `A-raster` to A1, `A-lazy` to A3, `B-raster` to B1, and `B-lazy-control` to B2.
Map `B-lazy` to B3, `C-raster` to C1, and `C-lazy` to C3.
Earlier `lazy-stack` results map to reader 2 within their original workflow and experimental context.

### Estimate provenance and recurring codes

The [transfer estimator](../../benchmarks/lazy_reader_workloads.py) predates the larger-workload observations and borrows historical measurements as proxies.
Its B3 estimate uses historical B1 raster measurements, scaled by lake-product memberships.
Any displayed estimate must say: **Estimate for B3, based on historical B1 measurements.**
Keep that planning estimate distinct from the measured B3 requested bytes in the completed results.
Preserve the original reference file, reader, formula, settings, and proxy qualification when translating raw keys into presentation codes.
The same rule covers A3 estimates derived from A2 and C3 estimates derived from C2.

**Measured settings:** Earlier B2 observations used four lazy threads and a 512 MiB GDAL block cache.
Section 05's B2 control uses two lazy threads and a 256 MiB GDAL block cache.
Both retain nominal 2,048-pixel chunks and separate lake computations. The shared B2 code identifies the recipe, not identical resource settings.
Sources: [shared-image results](../../benchmarks/results/tile-extraction.json), [multiple-tile results](../../benchmarks/results/cross-tile-extraction.json), and [larger-workload preflight and results](../../benchmarks/results/lazy-reader-workloads.json).
Show these settings beside the comparison or in its immediately adjacent notes. Avoid relying on a distant historical disclosure.

## Changes across the whole tab

| Current section | Proposed treatment |
|---|---|
| Introduction and navigation | Introduce workflow plus reader notation. Use descriptive names alongside every code and link to its definition |
| 01: processing outline | Keep the A/B/C diagram. Add a companion reader diagram and a small combination key before any results |
| 02: individual lakes | Reframe as pixel-selection variants within A1, plus an A1/A2 reader comparison using the same prepared mask |
| 03: shared image | Label every row with its combination. Explain A1/B1/C1 as workflow comparisons and B1/B2 as a reader comparison |
| 04: multiple tiles | Use A1/B1 and A2/B2 consistently. Explain the A2/B2 graph extents and resulting chunk placement |
| 05: larger workloads | Explain B1/B2/B3, current thread and cache settings, and C3's whole-band compute. Preserve proxy provenance wherever estimates appear |
| 06: test cases | Separate the original pilot from the dispersed and Florida cohorts. Link each sample to the comparisons it supports |
| 07: remaining decisions | Name both workflow and reader choices. Distinguish elapsed time, CPU, requests, requested bytes, and RAM |

Preserve existing section anchors and numbers. Add the reader explanation inside section 01 rather than shifting every later section number.
Keep workload colors attached to A/B/C. Reader numbers require visible text labels, without relying on color or hover explanations.
Put the combined code in the existing workflow cell and retain the descriptive reader column. Avoid adding another wide table column.
Keep names identical in navigation, captions, summary rows, expanded tables, conclusions, and accessible labels.

The companion explanation can use three parallel paths for the same two lakes sharing a source block:

1. Show direct window calls, an open band, and possible cache reuse.
2. Show a shared graph, separate lake computes, and possible repeated chunk work.
3. Show distinct source blocks, one computation per needed block, and both lake selections consuming the returned array.

Link the diagram to the full walkthrough for qualifications. Explain the whole-image variant directly beside C.

## Specific context corrections

- Replace C's section 01 note with: "Tested across many tiles in section 05. Excluded from section 04."
- Link C to the larger-workload results, alongside its existing shared-image link.
- Scope section 03's untested-improvements sentence to that historical experiment. Link the subsequently tested block alignment and shared consumption to section 05.
- Keep persistent chunk caching distinct from the bounded sharing now implemented. The new reader does not establish results for every proposed caching strategy.
- Explain that section 01's prepared-selection path describes the later comparisons. The boundary-clip baseline prepares its selection afresh.
- Replace section 05's single-cause question with a comparison of the revised recipe's resource costs. Windowed alignment and computation sharing changed together.
- Explain that C3 uses alignment without bounded batching. Its comparison does not isolate alignment's effect on resource use.
- Preserve the distinction between total extraction and read-plus-extract timing. A new code does not make different timing boundaries comparable.
- State both changed control settings: four to two lazy threads, and 512 to 256 MiB of GDAL block cache.
- Label B3 planning estimates as historical B1 proxies wherever estimates appear, distinct from completed B3 measurements.
- Retain the two A1 process arrangements in section 03. Their differences must remain visible below the common code.

## Alternatives considered

Numbering the original four approaches and adding improved lazy as a fifth would assign simple unique labels to those early rows.
It would also preserve the confusion between selecting pixels and reading image data.
Later readers use prepared positions differently, so equating raster with a particular mask representation would become misleading.

Using only direct and lazy reader numbers would require another visible qualifier wherever both lazy implementations appear.
Three descriptive reader numbers give the current comparisons compact, distinct labels while preserving the selection variants in section 02.

## Dispositions and verification

- Fixed in this review: a complete proposed mapping and a distinction between workflow, reading technique, and selection.
- Accepted and deferred: implementing the proposed labels, companion diagram, context corrections, and consistent renderer mappings after discussion.
- Preserved: measurement files, benchmark implementations, existing page content, and contributor changes.

### Owner refinements before implementation

| Suggestion | Disposition and rationale |
|---|---|
| Batch size follows the thread limit | Accepted. The proposal now identifies two as the measured setting and links its source |
| A2 and B2 have different chunk origins | Accepted. The proposal describes lake-window and full-image graph extents, including their effect on chunk placement |
| C3 aligns chunks but skips bounded batching | Accepted execution fact. Qualified the inference: existing comparisons do not isolate alignment's performance effect |
| B3's transfer estimate uses raster as a proxy | Accepted. Explicitly retain target B3 and reference B1 labels, provenance, and the distinction from measured B3 bytes |
| B2 changes threads and cache, and C's overview note is stale | Accepted. Record both resource settings and specify replacement text and a section 05 link for C |

Only this proposal changed during the refinement step. The owner subsequently authorized the linked implementation after compaction.

Headless Chromium inspected the seven chapters and eleven tables at 1,280 pixels wide, with disclosures expanded for the text audit.
The command was `uv run --offline --with playwright python /private/tmp/review-prototype-naming.py`.
Screenshots, expanded text, and table extracts remain temporary review artifacts outside the repository.
Repository verification passed again after the owner's refinements:

- `uv sync --locked`: passed.
- `uv run ruff check .` and `uv run ruff format --check .`: passed, with 119 files already formatted.
- `uv run pytest -q`: 273 passed in 29.70 seconds, with existing upstream affine deprecation warnings.
- The four artifact checks passed: `collate_checks.py`, `collate_sensor_bands.py`, `render_options.py`, and `gap_report.py`, through `uv run python tools/` with `--check`.
- `git diff --check`: passed.
- SHA-256 comparisons confirm all thirteen benchmark result files, the template, renderer, and generated page remain unchanged.

The proposed next step is a presentation revision using the agreed taxonomy, followed by renderer, evidence-preservation, and responsive-browser checks.
