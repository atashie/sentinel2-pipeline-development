# Examples

Public water-body manifests for prototypes. Customer polygons never enter this repository (assumption A8 in [../docs/assumptions.md](../docs/assumptions.md)).

## Manifest format

A manifest is a GeoJSON `FeatureCollection` in EPSG:4326. Each feature carries these properties.

| Property | Meaning |
|---|---|
| `water_body_id` | Stable id, unique within the manifest, never reused. `nhd-` plus the source id |
| `name` | Human label. The dataset's name, or "Unnamed water body" and the region name |
| `source` | Public dataset the polygon came from |
| `source_id` | The polygon's id in that dataset |
| `source_accessed` | ISO date the dataset was read, UTC |
| `polygon_version` | Integer, incremented when geometry changes |
| `region` | Region id from [pilot-regions.json](pilot-regions.json) |
| `survey_site_id` | The gap survey site the region is anchored on, from [../benchmarks/gap-survey-sites.json](../benchmarks/gap-survey-sites.json) |
| `setting` | Terrain description of the region: `mountain`, `hills`, `flat`, or `lowland`. A description, not a measurement |
| `tier` | `large` for an anchor lake, `pilot` for a size-class pick |
| `size_class_m` | The workload size class the width falls in, from [../benchmarks/workloads.json](../benchmarks/workloads.json) |
| `width_m` | Square root of the area, in metres |
| `area_m2` | Polygon area from the stored coordinates, holes removed |
| `fcode` | The dataset's feature code |
| `gnis_id` | Geographic Names Information System id, when the dataset has one |
| `reachcode` | The dataset's reach code |
| `nhd_feature_date` | The dataset's feature date |
| `vertex_count` | Vertices in the stored geometry |
| `why` | Why the water body is in the pilot |

The geometry is a `Polygon` or `MultiPolygon`, with coordinates rounded to six decimals. Every feature carries a `bbox`.
A manifest also carries top-level `manifest_version`, `note`, `dataset`, `retrieval`, `selection`, and `summary`.
`dataset` names the service, its refresh text, and its terms. `retrieval` logs every request and the digest of every saved response. `selection` states the rules.

## Pilot manifest

[water-bodies-public-pilot.geojson](water-bodies-public-pilot.geojson) holds 32 public water bodies in six regions of the United States, retrieved on 2026-09-12 UTC.
[../tools/build_pilot_manifest.py](../tools/build_pilot_manifest.py) builds it from [pilot-regions.json](pilot-regions.json) and the USGS National Hydrography Dataset, read through The National Map hydro service.
USGS states that The National Map data are free and in the public domain. It asks for the acknowledgment the manifest records under `dataset`.

Each region names a gap survey site as its anchor and a box to search. Five regions carry the anchor lake itself, tier `large`.
The Alaska region carries only small lakes, because Iliamna Lake is too large to store.
For each region and size class, the script takes the lake or pond whose width is nearest the class width. Intermittent ponds and treatment, disposal, cooling, and pool codes are left out.
The rules, the counts, and every request are in the manifest.

What the pilot covers, from the manifest's `summary`:

- Every size class in [../benchmarks/workloads.json](../benchmarks/workloads.json), 10 m to 1,000 m, plus five larger anchor lakes.
- Flat, lowland, hill, and mountain settings.
- Lake Tahoe, Lake Lanier, and Grand Lake, which the [gap survey](../docs/measurements.md) found in more than one tile.
- Five bodies in the 10 m class. Rasterization decides whether such a body has an interior pixel at 10 m (assumption A20). None is expected.

Limits:

- United States only. The three context sites outside the service area remain points in the survey site list.
- Tile membership is not in the manifest. Rerun the gap survey with `--manifest` to discover it from the catalog, as [../docs/gap-survey-plan.md](../docs/gap-survey-plan.md) describes.
- Whether a mapped pond holds water on a given date is unknown. The dataset's feature date is recorded.
- Terrain settings are descriptions from the region configuration, not measurements.
- Area uses a spherical approximation. Widths serve the size classes, not measurement.
- The Alaska box has no body under 17 m wide, so that region lacks the 10 m class.

Rebuild without network from the newest saved run under `data/pilot-manifest/`:

```sh
uv run python tools/build_pilot_manifest.py
```

Refetch only when the owner asks. The run saves every response and a request log, then rebuilds the manifest:

```sh
uv run python tools/build_pilot_manifest.py --fetch
```

Earlier candidates, none selected, were national hydrography products, global lake databases, and global surface-water masks.
The Codex initialization review of 2026-09-09, archived, recorded that HydroBASINS delineates sub-basins, not lakes, and that HydroLAKES targets lakes of 10 hectares and more.
The national dataset was chosen because it carries ponds down to the 10 m class and answers box queries without a bulk download.
