# Examples

Public water-body manifests for prototypes. Customer polygons never enter this repository (assumption A8 in [../docs/assumptions.md](../docs/assumptions.md)).

## Manifest format

A manifest is a GeoJSON `FeatureCollection` in EPSG:4326. Each feature carries:

| Property | Meaning |
|---|---|
| `water_body_id` | Stable id, unique within the manifest, never reused |
| `name` | Human label |
| `source` | Public dataset the polygon came from |
| `source_id` | The polygon's id in that dataset |
| `source_accessed` | ISO date the dataset was read |
| `polygon_version` | Integer, incremented when geometry changes |

The geometry is a `Polygon` or `MultiPolygon`. A manifest also carries top-level `manifest_version` and `note`.

## Pilot manifest

[water-bodies-public-pilot.geojson](water-bodies-public-pilot.geojson) is empty on 2026-09-09. The prototyping step derives it from a public dataset by a checked-in script that records the dataset, version, and access date.
Candidate datasets, none selected: national hydrography products, global lake databases, and global surface-water masks. Small ponds need a dataset that carries them.
The pilot must include every size class in [../benchmarks/workloads.json](../benchmarks/workloads.json), flat and mountainous settings, and at least one water body that spans two tiles.
