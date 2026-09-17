"""Stage 4: frozen datatakes, separate native tiles, and two work organizations.

No arguments prints a local plan. --select queries metadata only. --catalog reads saved
metadata instead. --run-plan reads imagery, only when invoked by the owner after review.
"""

from __future__ import annotations

import argparse
import dataclasses
import gc
import itertools
import json
import math
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "benchmarks")]

import numpy as np  # noqa: E402
import pyproj  # noqa: E402
import shapely  # noqa: E402
import tile_extraction as stage3  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from s2proto import harness, masks  # noqa: E402

stage2 = stage3.stage2
METHODS = ["raster-mask", "lazy-stack"]
PATHS = ["lake-first", "tile-first"]
BANDS = stage2.BAND_SETS["default"]
TOLERANCE = 1e-6
IMPLEMENTATION = {"script": 3, "masks": masks.MASK_VERSION}
TRANSFER_REFERENCE = ROOT / "benchmarks/results/cross-tile-extraction.json"
SOURCE_FILES = [
    Path(__file__),
    Path(stage3.__file__),
    Path(stage2.__file__),
    Path(masks.__file__),
    Path(harness.__file__),
    ROOT / "uv.lock",
]
LIMITATIONS = [
    "Laptop comparison, not AWS throughput or cost.",
    "Logical contribution assembly only. No pixel storage or readback benchmark.",
    "Overlapping tile values remain separate. Scientific agreement is not tested.",
    "Ambiguous primary roles remain unresolved under A22.",
    "GDAL log bytes are requested bytes, not an independently metered network transfer.",
    "Per-lake bytes in tile-first workers are marginal, after shared opens and earlier lakes.",
    "Output bytes use Stage 3's logical record model, not a measured storage format.",
    "Fixed 512 MiB cache, 2048-pixel lazy chunks and four threads. No reader tuning.",
    "Host page-out deltas include other processes. Workers run serially.",
    "Diagnostic buffers use 16 segments per quadrant, matching Stage 3 candidate buffers. "
    "Geometry convergence tests CRS edge refinement, not an ideal circular buffer.",
    "Catalog footprints are coarse ranking hints, not pixel validity masks. "
    "Native tile membership is retained even where the footprint misses the support.",
    "Distinct datastrip ids remain separate. Unknown datastrip ids are never deduplicated.",
]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=1, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(value) -> str:
    return harness.sha256_bytes(json.dumps(value, sort_keys=True).encode())


def source_digests() -> dict:
    return {str(p.relative_to(ROOT)): harness.sha256_bytes(p.read_bytes()) for p in SOURCE_FILES}


def lake_id(lake):
    return lake["properties"]["water_body_id"]


def item_tile(item):
    return stage3.normalize_grid_code(item["properties"].get("grid:code"))


def observation_identity(item):
    """Only collapse catalog alternatives with the same declared datastrip identity."""
    props = item["properties"]
    return (
        props.get("s2:datatake_id") or item["id"],
        item_tile(item),
        props.get("s2:datastrip_id") or item["id"],
    )


def scene_id(scene):
    return f"{scene['region']}-{scene['item']['id']}"


def timestamp(value, *, optional=False):
    if not value and optional:
        return float("-inf")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamps need an offset")
    return parsed.timestamp()


def transform(geometry, source, target, spacing):
    """Densify before transforming. WGS84 spacing is a conservative degree conversion."""
    distance = spacing / 111320 if source == 4326 else spacing
    geometry = shapely.segmentize(geometry, distance)
    transformer = pyproj.Transformer.from_crs(source, target, always_xy=True)

    def project(coords):
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack((x, y))

    result = shapely.transform(geometry, project)
    if not result.is_valid or result.is_empty:
        raise ValueError("invalid or empty transformed geometry")
    return result


def reference_epsg(lake):
    point = shape(lake["geometry"]).representative_point()
    zone = min(60, max(1, int((point.x + 180) // 6) + 1))
    return (32600 if point.y >= 0 else 32700) + zone


def buffered_bbox(lakes):
    bounds = []
    for lake in lakes:
        epsg = reference_epsg(lake)
        polygon = transform(shape(lake["geometry"]), 4326, epsg, 500)
        support = polygon.envelope.buffer(masks.NEAR_LAND_M + 1).envelope
        bounds.append(transform(support, epsg, 4326, 500).bounds)
    return [
        min(b[0] for b in bounds),
        min(b[1] for b in bounds),
        max(b[2] for b in bounds),
        max(b[3] for b in bounds),
    ]


def native_assets(item, bands):
    if item.get("collection") != stage2.COLLECTION:
        raise ValueError("only Collection 1 belongs to this experiment")
    grid = masks.TileGrid.from_item(item)
    resolved = stage2.resolve_assets(item, bands, grid)
    if resolved["missing"] or resolved["skipped"]:
        raise ValueError(f"unusable assets: {resolved}")
    for asset in resolved["assets"]:
        raw = item["assets"][asset["key"]]
        if (
            raw["proj:transform"][:6] != list(grid.transform(asset["resolution"]))[:6]
            or raw.get("proj:epsg", grid.epsg) != grid.epsg
            or raw.get("proj:code", f"EPSG:{grid.epsg}") != f"EPSG:{grid.epsg}"
        ):
            raise ValueError(f"asset {asset['key']} has a different native grid")
    return grid, resolved["assets"]


def geometry_context(lake, grids, items):
    """Refine every diagnostic boundary, including clipped footprints, in one lake CRS.

    Bound successive refinements of any selected group, including split datastrips.
    Sum the worst change per declared observation, then take the largest group sum.
    This convergence criterion does not bound error against exact source geometry.
    """
    epsg = reference_epsg(lake)
    original = shape(lake["geometry"])
    if not original.is_valid or original.area <= 0:
        raise ValueError(f"invalid polygon: {lake_id(lake)}")
    # The extraction rule measures distance in the native grid CRS. Keep its candidates
    # even if a reference-CRS buffer differs slightly at a tile edge.
    native_polygons = {
        epsg: masks.project(lake["geometry"], epsg)
        for epsg in {grid.epsg for grid in grids.values()}
    }
    native_members = {
        tile
        for tile, grid in grids.items()
        if native_polygons[grid.epsg].distance(grid.extent()) <= masks.NEAR_LAND_M
    }
    identities = [observation_identity(i) for i in items]
    group_counts = defaultdict(int)
    for group, _, _ in set(identities):
        group_counts[group] += 1
    footprint_count = max(group_counts.values(), default=0)
    previous = None
    for iteration in range(9):
        spacing = 1000 / 2**iteration
        polygon = transform(original, 4326, epsg, spacing)
        support = polygon.buffer(masks.NEAR_LAND_M, quad_segs=16)
        extents = {
            tile: transform(grid.extent(), grid.epsg, epsg, spacing) for tile, grid in grids.items()
        }
        footprints = {
            item["id"]: transform(shape(item["geometry"]), 4326, epsg, spacing) for item in items
        }
        current = [polygon, support, *extents.values(), *footprints.values()]
        if previous is not None:
            # Difference the simple tile boundaries first. Differencing two almost
            # identical clipped lake polygons makes GEOS revisit every shoreline vertex.
            deltas = [
                shapely.GeometryCollection() if a.equals_exact(b, 0) else a.symmetric_difference(b)
                for a, b in zip(current, previous, strict=True)
            ]
            tile_count = len(grids)
            extent_change = sum(
                delta.intersection(support).area for delta in deltas[2 : 2 + tile_count]
            )
            footprint_change = defaultdict(float)
            for identity, delta in zip(identities, deltas[2 + tile_count :], strict=True):
                footprint_change[identity] = max(
                    footprint_change[identity], delta.intersection(support).area
                )
            group_change = defaultdict(float)
            for (group, _, _), area in footprint_change.items():
                group_change[group] += area
            # A group can contain multiple datastrip footprints for the same tile.
            # Their overlap changes only where an input set changes. The support term
            # bounds clipping changes in both families, plus the support area itself.
            change = (
                deltas[0].area
                + (1 + tile_count + footprint_count) * deltas[1].area
                + extent_change
                + max(group_change.values(), default=0)
            ) / min(polygon.area, support.area)
            if change <= TOLERANCE / 8:
                # The coordinate displacement bound avoids overlaying near-identical
                # complex shorelines solely to test floating-point round-trip error.
                coords = shapely.get_coordinates(polygon)
                forward = pyproj.Transformer.from_crs(epsg, 4326, always_xy=True)
                backward = pyproj.Transformer.from_crs(4326, epsg, always_xy=True)
                lon, lat = forward.transform(coords[:, 0], coords[:, 1])
                x, y = backward.transform(lon, lat)
                displacement = float(np.hypot(x - coords[:, 0], y - coords[:, 1]).max())
                error = (
                    2 * polygon.length * displacement + math.pi * displacement**2
                ) / polygon.area
                if error > TOLERANCE:
                    raise ValueError("polygon round trip exceeds tolerance")
                return {
                    "epsg": epsg,
                    "polygon": polygon,
                    "support": support,
                    "extents": extents,
                    "footprints": footprints,
                    "native_members": native_members,
                    "audit": {
                        "spacing_m": spacing,
                        "relative_change_bound": change,
                        "roundtrip_relative_error": error,
                        "buffer_quad_segs": 16,
                        "bound_scope": "worst alternative per datastrip, summed within each group",
                    },
                }
        previous = current
    raise ValueError(f"geometry did not converge: {lake_id(lake)}")


def coverage(context, items):
    polygon, support = context["polygon"], context["support"]
    extents, footprints, members, products = [], [], [], []
    by_tile = defaultdict(list)
    for item in items.values():
        by_tile[item_tile(item)].append(item)
    for tile, tile_items in sorted(by_tile.items()):
        extent = context["extents"][tile]
        part = support.intersection(extent)
        if tile not in context["native_members"]:
            continue
        extents.append(part)
        parts = []
        for item in sorted(tile_items, key=lambda i: i["id"]):
            footprint = part.intersection(context["footprints"][item["id"]])
            parts.append(footprint)
            products.append(
                {
                    "tile": tile,
                    "item": item["id"],
                    "datastrip": item["properties"].get("s2:datastrip_id"),
                    "support_in_footprint": footprint.area / part.area if part.area else 1.0,
                    "membership_basis": "native tile extent, footprint retained as a diagnostic",
                }
            )
        footprints.extend(parts)
        members.append(
            {
                "tile": tile,
                "polygon_share": polygon.intersection(extent).area / polygon.area,
                "buffered_share": part.area / support.area,
                "support_in_footprint": shapely.union_all(parts).area / part.area
                if part.area
                else 1.0,
            }
        )
    union = shapely.union_all(extents)
    observed = shapely.union_all(footprints)
    overlap = shapely.union_all([a.intersection(b) for a, b in itertools.combinations(extents, 2)])
    observed_overlap = shapely.union_all(
        [a.intersection(b) for a, b in itertools.combinations(footprints, 2)]
    )
    return {
        "reference_epsg": context["epsg"],
        "geometry_check": context["audit"],
        "polygon_area_m2": polygon.area,
        "support_area_m2": support.area,
        "polygon_uncovered_m2": polygon.difference(union).area,
        "support_uncovered_m2": support.difference(union).area,
        "footprint_uncovered_m2": support.difference(observed).area,
        "support_uncovered_fraction": support.difference(union).area / support.area,
        "footprint_uncovered_fraction": support.difference(observed).area / support.area,
        "support_overlap_m2": overlap.area,
        "footprint_overlap_m2": observed_overlap.area,
        "members": members,
        "products": products,
    }


def select_region(items, lakes, bands=BANDS):
    """No pixel or header access. Keep all spatial candidates and rank complete datatakes."""
    grids, grouped, rejected, ungrouped = {}, defaultdict(list), [], []
    invalid_groups = defaultdict(list)
    valid = []
    seen = set()
    for item in items:
        props = item["properties"]
        group = props.get("s2:datatake_id")
        tile = stage3.normalize_grid_code(props.get("grid:code"))
        try:
            if not tile:
                raise ValueError("missing tile identity")
            grid = masks.TileGrid.from_item(item)
            if grid.width_10m <= 0 or grid.height_10m <= 0:
                raise ValueError("empty native grid")
            if tile in grids and grids[tile] != grid:
                raise ValueError("conflicting native grids for one tile")
            grids[tile] = grid
            if (
                not item.get("geometry")
                or not shape(item["geometry"]).is_valid
                or shape(item["geometry"]).is_empty
                or shape(item["geometry"]).geom_type not in ("Polygon", "MultiPolygon")
            ):
                raise ValueError("unknown or invalid footprint")
            if item["id"] in seen:
                raise ValueError("duplicate catalog item id")
            seen.add(item["id"])
            valid.append(item)
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"item": item["id"], "group": group, "tile": tile, "reason": str(exc)})
            if group:
                invalid_groups[group].append(str(exc))
            continue
        if not group:
            ungrouped.append(item["id"])
        else:
            grouped[group].append(item)
    contexts = {lake_id(lake): geometry_context(lake, grids, valid) for lake in lakes}
    candidates = {}
    roles = {}
    for lake in lakes:
        lid = lake_id(lake)
        context = contexts[lid]
        support = context["support"]
        shares = {
            tile: support.intersection(extent).area / support.area
            for tile, extent in context["extents"].items()
            if tile in context["native_members"]
        }
        maximum = max(shares.values(), default=0)
        proposed = min(
            (t for t, share in shares.items() if maximum - share <= TOLERANCE), default=None
        )
        contained = [tile for tile, share in shares.items() if 1 - share <= TOLERANCE]
        primary = contained[0] if len(contained) == 1 else None
        roles[lid] = {
            "primary": primary,
            "status": "single containing tile" if primary else "unresolved",
            "proposed_largest_share": proposed,
            "buffered_shares": shares,
        }
        for tile in shares:
            candidates.setdefault(tile, []).append(lid)
    ranked, scenes_by_group = [], {}
    for group in sorted(set(grouped) | set(invalid_groups)):
        revisions, chosen, discarded = defaultdict(list), {}, []
        reasons = list(invalid_groups[group])
        group_items = grouped[group]
        platforms = {i["properties"].get("platform") for i in group_items}
        if len(platforms) != 1 or not all(platforms):
            reasons.append("missing or inconsistent platform")
        for item in group_items:
            tile = stage3.normalize_grid_code(item["properties"].get("grid:code"))
            if tile not in candidates:
                continue
            try:
                native_assets(item, bands)
                timestamp(item["properties"].get("created"), optional=True)
                timestamp(item["properties"].get("datetime"))
                revisions[observation_identity(item)].append(item)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                discarded.append({"item": item["id"], "tile": tile, "reason": str(exc)})
        for (_, tile, datastrip), versions in revisions.items():
            versions.sort(
                key=lambda i: (-timestamp(i["properties"].get("created"), optional=True), i["id"])
            )
            chosen[versions[0]["id"]] = versions[0]
            discarded.extend(
                {
                    "item": v["id"],
                    "tile": tile,
                    "datastrip": datastrip,
                    "reason": "older catalog alternative for the same declared datastrip",
                    "processing_baseline": v["properties"].get("s2:processing_baseline"),
                }
                for v in versions[1:]
            )
        spatial = {lid: coverage(context, chosen) for lid, context in contexts.items()}
        if any(c["support_uncovered_fraction"] > TOLERANCE for c in spatial.values()):
            reasons.append("tile union leaves buffered support uncovered")
        clouds = [i["properties"].get("eo:cloud_cover") for i in chosen.values()]
        cloud = (
            max(clouds)
            if clouds and all(isinstance(x, (int, float)) and math.isfinite(x) for x in clouds)
            else None
        )
        earliest = min(
            (i["properties"]["datetime"] for i in chosen.values()), key=timestamp, default=None
        )
        max_uncovered = max(c["footprint_uncovered_fraction"] for c in spatial.values())
        score = [
            0.0 if max_uncovered <= TOLERANCE else max_uncovered,
            cloud,
            earliest,
            group,
            sorted(i["id"] for i in chosen.values()),
        ]
        ranked.append(
            {
                "group": group,
                "eligible": not reasons,
                "exclusions": reasons,
                "score": score,
                "missing_tiles": sorted(set(candidates) - {item_tile(i) for i in chosen.values()}),
                "items": sorted(chosen),
                "discarded": discarded,
                "coverage": spatial,
            }
        )
        scenes_by_group[group] = chosen
    eligible = [r for r in ranked if r["eligible"]]
    eligible.sort(
        key=lambda r: (
            r["score"][0],
            r["score"][1] if r["score"][1] is not None else float("inf"),
            -timestamp(r["score"][2]),
            r["group"],
            r["score"][4],
        )
    )
    winner = eligible[0] if eligible else None
    return {
        "candidates": candidates,
        "roles": roles,
        "groups": ranked,
        "rejected": rejected,
        "ungrouped": ungrouped,
        "selected_group": winner["group"] if winner else None,
        "selected_items": scenes_by_group[winner["group"]] if winner else {},
        "coverage": winner["coverage"] if winner else {},
        "geometry_tolerance": TOLERANCE,
        "ranking": [
            "smallest maximum catalog-footprint uncovered fraction, a coarse heuristic",
            "smallest maximum cloud percentage",
            "latest earliest sensing time",
            "smaller datatake id and sorted item ids",
        ],
    }


def expected_contributions(plan):
    lakes = {lake_id(lake): lake for lake in plan["lakes"]}
    records = []
    for scene in plan["scenes"]:
        for lid in scene["members"]:
            lake = lakes[lid]
            for asset in scene["assets"]:
                records.append(
                    {
                        "key": [
                            lid,
                            lake["properties"]["polygon_version"],
                            scene["group"],
                            scene["tile"],
                            scene["item"]["id"],
                            asset["key"],
                            asset["resolution"],
                        ],
                        "grid": scene["grid"],
                        "polygon_sha256": stage2.polygon_digest(lake),
                        "sensing_time": scene["item"]["properties"]["datetime"],
                        "role": scene["roles"][lid],
                    }
                )
    return sorted(records, key=lambda r: tuple(r["key"]))


def freeze_plan(
    lakes,
    catalogs,
    methods=METHODS,
    repeat=3,
    selector=select_region,
    transfer_reference=TRANSFER_REFERENCE,
):
    if not lakes or repeat < 1 or not methods or set(methods) - set(METHODS):
        raise ValueError("nonempty lakes, supported methods, and positive repetitions required")
    if len({lake_id(lake) for lake in lakes}) != len(lakes):
        raise ValueError("duplicate lake id")
    for lake in lakes:
        if "polygon_version" not in lake["properties"]:
            raise ValueError("polygon version required")
    plan = {
        "created_at": harness.utc_now(),
        "implementation": IMPLEMENTATION,
        "source_digests": source_digests(),
        "lakes": lakes,
        "bands": BANDS,
        "methods": list(methods),
        "paths": PATHS,
        "repeat": repeat,
        "selection": {},
        "scenes": [],
        "catalog_sha256": digest(catalogs),
        "memory": stage3.MEMORY_DEFAULTS,
        "chunk": stage3.LAZY_CHUNK,
        "dask_workers": stage3.LAZY_WORKERS,
        "gdal_cache_bytes": stage3.GDAL_CACHE_BYTES,
        "window": list(stage2.DEFAULT_WINDOW),
        "limitations": LIMITATIONS,
    }
    for region in sorted({lake["properties"]["region"] for lake in lakes}):
        region_lakes = [lake for lake in lakes if lake["properties"]["region"] == region]
        selection = selector(catalogs[region], region_lakes)
        selected = selection.pop("selected_items")
        plan["selection"][region] = selection
        for _, item in sorted(selected.items()):
            tile = item_tile(item)
            grid, assets = native_assets(item, BANDS)
            members = [
                lid
                for lid, c in selection["coverage"].items()
                if any(m["tile"] == tile for m in c["members"])
            ]
            plan["scenes"].append(
                {
                    "region": region,
                    "tile": tile,
                    "group": selection["selected_group"],
                    "item": item,
                    "grid": dataclasses.asdict(grid),
                    "assets": assets,
                    "members": sorted(members),
                    "roles": {
                        lid: (
                            "primary"
                            if selection["roles"][lid]["primary"] == tile
                            else "overlap"
                            if selection["roles"][lid]["primary"]
                            else None
                        )
                        for lid in members
                    },
                }
            )
    plan["ready"] = all(s["selected_group"] for s in plan["selection"].values())
    plan["expected"] = expected_contributions(plan)
    order = []
    for repetition in range(1, repeat + 1):
        for path in stage3.rotated(PATHS, repetition - 1):
            for method in stage3.rotated(methods, repetition - 1):
                units = (
                    [
                        {"unit": lake_id(lake), "region": lake["properties"]["region"]}
                        for lake in lakes
                    ]
                    if path == "lake-first"
                    else [{"unit": s["item"]["id"], "region": s["region"]} for s in plan["scenes"]]
                )
                order.extend(
                    {**unit, "path": path, "method": method, "repetition": repetition}
                    for unit in units
                )
    plan["order"] = order if plan["ready"] else []
    plan["transfer_estimate"] = transfer_estimate(plan, transfer_reference)
    return {**plan, "sha256": digest(plan)}


def transfer_estimate(plan, reference):
    """Scale observed complete-workload bytes, including shared opens, by memberships."""
    estimate = {
        "kind": "historical windowed bytes per membership, not a hard upper bound",
        "bytes": None,
        "caveat": "Assumes similar polygon sizes, density, compression and reader settings. "
        "The observed range is not a prediction interval or a transfer guard.",
    }
    if reference is None or not Path(reference).exists():
        return {**estimate, "reason": "no saved windowed reference"}
    content = Path(reference).read_bytes()
    previous = json.loads(content)
    for field in ("bands", "chunk", "dask_workers", "gdal_cache_bytes"):
        if plan[field] != previous.get("plan", {}).get(field):
            return {**estimate, "reason": f"reference {field} differs"}
    summary = previous.get("summary", {})
    memberships = summary.get("memberships", 0)
    wanted = sum(len(s["members"]) for s in plan["scenes"])
    rates = []
    for path, method in itertools.product(plan["paths"], plan["methods"]):
        samples = (
            [
                w["totals"]["bytes_requested"] / memberships
                for w in summary.get("workloads", [])
                if w["clean"] and w["path"] == path and w["method"] == method
            ]
            if memberships
            else []
        )
        if not samples:
            return {**estimate, "reason": f"no clean reference for {path}/{method}"}
        rates.append(
            {
                "path": path,
                "method": method,
                "median_bytes_per_membership": statistics.median(samples),
                "minimum_bytes_per_membership": min(samples),
                "maximum_bytes_per_membership": max(samples),
            }
        )
    return {
        **estimate,
        "reference": str(reference),
        "reference_sha256": harness.sha256_bytes(content),
        "reference_memberships": memberships,
        "memberships": wanted,
        "rates": rates,
        "formula": "sum of per-path/reader rates times memberships times repetitions",
        "bytes": round(
            sum(r["median_bytes_per_membership"] for r in rates) * wanted * plan["repeat"]
        ),
        "observed_rate_range_bytes": [
            round(sum(r[f"{side}_bytes_per_membership"] for r in rates) * wanted * plan["repeat"])
            for side in ("minimum", "maximum")
        ],
    }


def verify_plan(plan):
    body = {k: v for k, v in plan.items() if k != "sha256"}
    if digest(body) != plan.get("sha256"):
        raise ValueError("frozen plan digest differs")
    if plan["source_digests"] != source_digests():
        raise ValueError("implementation changed since selection, regenerate the plan")
    if not plan["ready"] or not plan["expected"]:
        raise ValueError("no complete acquisition group for every region")
    if expected_contributions(plan) != plan["expected"]:
        raise ValueError("frozen expected contributions differ")
    for scene in plan["scenes"]:
        grid, assets = native_assets(scene["item"], plan["bands"])
        if dataclasses.asdict(grid) != scene["grid"] or assets != scene["assets"]:
            raise ValueError("scene native inputs differ")


def file_digest(path):
    import hashlib

    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reuse_preparation(directory, name, spec):
    """Reuse geometry alone. Script versions and acquisition dates are not mask inputs."""
    if directory is None:
        return None, "no reuse directory supplied"
    try:
        saved_spec = json.loads((directory / f"{name}.spec.json").read_text())
        saved = json.loads((directory / f"{name}.result.json").read_text())
        for key in ("water_body_id", "polygon_sha256", "grid", "mask_parameters"):
            if saved.get(key) != spec[key] or saved_spec.get(key) != spec[key]:
                return None, f"{key} differs"
        if (
            saved.get("error")
            or saved["implementation"]["masks"] != masks.MASK_VERSION
            or saved_spec["implementation"]["masks"] != masks.MASK_VERSION
        ):
            return None, "failed preparation or mask version differs"
        if set(saved["resolutions"]) != {str(r) for r in spec["resolutions"]}:
            return None, "resolutions differ"
        for resolution, record in saved["resolutions"].items():
            for kind in ("mask", "index"):
                path = Path(saved_spec[f"{kind}_paths"][resolution])
                if file_digest(path) != record[f"{kind}_sha256"]:
                    return None, f"{kind} hash differs at {resolution} m"
        import shutil

        for resolution in saved["resolutions"]:
            for kind in ("mask", "index"):
                destination = Path(spec[f"{kind}_paths"][resolution])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(saved_spec[f"{kind}_paths"][resolution], destination)
        return saved, "verified polygon, grids, resolutions, parameters, algorithm and file hashes"
    except (OSError, KeyError, ValueError) as exc:
        return None, f"saved preparation unavailable: {exc}"


def prepare(plan, raw_dir, reuse_dir):
    lakes = {lake_id(lake): lake for lake in plan["lakes"]}
    preparations, prepared = {}, {}
    for scene in plan["scenes"]:
        sid = f"{scene['region']}-{scene['tile']}"
        prepared.setdefault(sid, [])
        for lid in scene["members"]:
            if any(m["water_body_id"] == lid for m in prepared[sid]):
                continue
            lake = lakes[lid]
            resolutions = sorted({a["resolution"] for a in scene["assets"]})
            name = f"prepare-{scene['tile']}-{lid}"
            spec = {
                "tile": scene["tile"],
                "water_body_id": lid,
                "geometry": lake["geometry"],
                "polygon_sha256": stage2.polygon_digest(lake),
                "grid": scene["grid"],
                "resolutions": resolutions,
                "mask_parameters": stage2.MASK_PARAMETERS,
                "implementation": IMPLEMENTATION,
                **{
                    f"{kind}_paths": {
                        str(r): str(raw_dir / kind / f"{sid}-{lid}-{r}m.npz") for r in resolutions
                    }
                    for kind in ("mask", "index")
                },
            }
            started = time.perf_counter()
            result, reason = reuse_preparation(reuse_dir, name, spec)
            reused = result is not None
            write_json(raw_dir / f"{name}.spec.json", spec)
            if result is None:
                result = stage3.run_in_subprocess(
                    "prepare", spec, raw_dir / f"{name}.spec.json", plan["memory"]
                )
            write_json(raw_dir / f"{name}.result.json", result)
            preparations[f"{sid}/{lid}"] = {
                "reused": reused,
                "reuse_reason": reason,
                "preflight_seconds": time.perf_counter() - started,
                "result": result,
            }
            if "error" in result:
                prepared[sid].append({"water_body_id": lid, "preparation_error": result["error"]})
                continue
            hashes = {str(r): result["resolutions"][str(r)]["mask_sha256"] for r in resolutions}
            prepared[sid].append(
                {
                    "water_body_id": lid,
                    "size_label": stage2.size_label(lake),
                    "geometry": lake["geometry"],
                    "mask_paths": spec["mask_paths"],
                    "index_paths": spec["index_paths"],
                    "mask_sha256": hashes,
                }
            )
    return preparations, prepared


def canonical(records):
    by_key = {}
    for record in records:
        key = tuple(record["key"])
        if key in by_key:
            kind = "conflicting" if by_key[key] != record else "repeated"
            raise ValueError(f"{kind} contribution key: {key}")
        by_key[key] = record
    return [by_key[key] for key in sorted(by_key)]


SIGNATURE_FIELDS = (
    "grid",
    "polygon_sha256",
    "status",
    "window",
    "pixels_extracted",
    "nodata_extracted",
    "counts",
    "digest_all",
    "digest_wet",
    "digest_pixels",
    "digest_pixels_wet",
)


def signature(record):
    return {key: record.get(key) for key in SIGNATURE_FIELDS}


def contributions(expected, tiles):
    found = {}
    errors = {tile["item_id"]: tile["error"] for tile in tiles if tile.get("error")}
    for tile in tiles:
        for lake in tile.get("lakes", []):
            for band in lake["bands"]:
                if band["key"].startswith("stack-"):
                    continue
                key = (tile["item_id"], lake["water_body_id"], band["key"])
                if key in found:
                    raise ValueError("duplicate extracted lake-band")
                found[key] = band
    records = []
    for entry in expected:
        lid, _, _, _, item, band, _ = entry["key"]
        actual = found.pop((item, lid, band), None)
        if actual is None:
            status = "failed" if item in errors else "missing"
            fields = {"error": errors[item]} if item in errors else {}
        else:
            fields = {k: v for k, v in actual.items() if k != "key"}
            status = (
                "failed"
                if "error" in actual or "digest_pixels" not in actual
                else "empty"
                if not actual["pixels_extracted"]
                else "measured"
            )
        records.append({**fields, **entry, "status": status})
    if found:
        raise ValueError(f"unexpected extracted contributions: {sorted(found)}")
    return canonical(records)


def log_diagnostics(path):
    """Identify exact repeated byte-range requests. These are not necessarily retries."""
    downloads, warnings = defaultdict(int), []
    if not Path(path).exists():
        return {"log_missing": True}
    with Path(path).open() as stream:
        for number, line in enumerate(stream, 1):
            match = re.search(r"VSICURL: Downloading (\S+) \(([^)]+)\)", line)
            if match:
                downloads[match.groups()] += 1
            if re.search(r"timed? ?out|timeout|retrying", line, re.IGNORECASE):
                warnings.append({"line": number, "text": line.strip()})
    return {
        "timeouts_or_retries": warnings,
        "repeated_ranges": [
            {"range": byte_range, "href": href, "count": count}
            for (byte_range, href), count in sorted(downloads.items())
            if count > 1
        ],
        "note": "Repeated requests can be reader re-reads or retries. Inspect adjacent log lines.",
    }


def extract_worker(spec):
    """One outer process, sequential calls to the existing Stage 3 tile reader."""
    import rasterio
    from rasterio.env import get_gdal_config

    started, cpu = time.perf_counter(), harness.cpu_seconds()
    results = []
    with rasterio.Env(**stage3.GDAL_ENV):
        cache = int(get_gdal_config("GDAL_CACHEMAX"))
    for tile_spec in spec["tiles"]:
        name = tile_spec["result_path"]
        try:
            for lake in tile_spec["lakes"]:
                if lake.get("preparation_error"):
                    raise ValueError(lake["preparation_error"])
                for resolution, path in lake["mask_paths"].items():
                    if file_digest(path) != lake["mask_sha256"][resolution]:
                        raise ValueError("prepared mask hash changed")
            item = json.loads(Path(tile_spec["item_path"]).read_text())
            grid, assets = native_assets(item, spec["bands"])
            if dataclasses.asdict(grid) != tile_spec["grid"] or assets != tile_spec["assets"]:
                raise ValueError("native tile inputs changed")
            result = stage3.extract_worker(tile_spec)
        except Exception as exc:
            result = {
                "tile": tile_spec["tile"],
                "item_id": tile_spec["item_id"],
                "error": f"{type(exc).__name__}: {exc}",
            }
        result["log_path"] = tile_spec["log_path"]
        result["log_diagnostics"] = log_diagnostics(tile_spec["log_path"])
        write_json(Path(name), result)
        results.append(result)
        gc.collect()
    with harness.Timer() as assembly:
        records = contributions(spec["expected"], results)
    return {
        **spec["tag"],
        "started_at": spec["started_at"],
        "wall_seconds": time.perf_counter() - started,
        "cpu": harness.cpu_delta(cpu, harness.cpu_seconds()),
        "peak_rss_bytes": harness.peak_rss_bytes(),
        "gdal_cache_bytes": cache,
        "assembly_seconds": assembly.seconds,
        "tiles": results,
        "contributions": records,
    }


def unit_key(run):
    return tuple(run[k] for k in ("repetition", "path", "method", "region", "unit"))


def summarize(plan, runs):
    """Freeze denominators before looking at successful workers. Never median partial work."""
    expected = canonical(plan["expected"])
    expected_keys = [tuple(r["key"]) for r in expected]
    by_unit = {}
    for run in runs:
        key = unit_key(run)
        if key in by_unit:
            raise ValueError(f"duplicate worker: {key}")
        by_unit[key] = run
    if set(by_unit) - {unit_key(u) for u in plan["order"]}:
        raise ValueError("unexpected worker")
    workloads, reference, equality, costs = [], None, [], []
    for rep, path, method in dict.fromkeys(
        (u["repetition"], u["path"], u["method"]) for u in plan["order"]
    ):
        planned = [
            u
            for u in plan["order"]
            if (u["repetition"], u["path"], u["method"]) == (rep, path, method)
        ]
        present = [by_unit[unit_key(u)] for u in planned if unit_key(u) in by_unit]
        with harness.Timer() as assembly:
            assembled = canonical([r for run in present for r in run.get("contributions", [])])
        actual = {tuple(r["key"]): r for r in assembled}
        unexpected = set(actual) - set(expected_keys)
        if unexpected:
            raise ValueError(f"unexpected contribution keys: {unexpected}")
        missing = [list(k) for k in expected_keys if k not in actual]
        failures = [r["key"] for r in assembled if r["status"] not in ("measured", "empty")]
        errors = sum(
            bool(
                r.get("error")
                or r.get("memory_stop")
                or any(
                    t.get("error")
                    or t.get("totals", {}).get("band_errors")
                    or t.get("totals", {}).get("lake_band_errors")
                    for t in r.get("tiles", [])
                )
            )
            for r in present
        )
        pressured = sum(stage3.under_pressure(r) for r in present)
        complete = len(present) == len(planned) and not missing and not failures and not errors
        clean = complete and not pressured
        with harness.Timer() as validation:
            signatures = [signature(r) for r in assembled]
            matches = None
            different = []
            if complete:
                if reference is None:
                    reference = {"label": [rep, path, method], "signatures": signatures}
                different = [
                    list(key)
                    for key, a, b in zip(
                        expected_keys, signatures, reference["signatures"], strict=True
                    )
                    if a != b
                ]
                matches = not different
        tiles = [tile for run in present for tile in run.get("tiles", [])]
        totals = {
            field: sum(t.get("totals", {}).get(field, 0) or 0 for t in tiles)
            for field in (
                "requests",
                "bytes_requested",
                "opens_observed",
                "pixels_extracted",
                "output_bytes",
            )
        }
        tag = {"repetition": rep, "path": path, "method": method}
        workloads.append(
            {
                **tag,
                "planned_workers": len(planned),
                "present_workers": len(present),
                "complete": complete,
                "clean": clean,
                "missing": missing,
                "failed": failures,
                "errored_workers": errors,
                "pressured_workers": pressured,
                "totals": totals,
                "worker_seconds": sum(r.get("wall_seconds", 0) for r in present),
                "end_to_end_seconds": sum(r.get("elapsed_seconds", 0) for r in present),
                "reader_seconds": sum(stage3.read_seconds(t) for t in tiles if "error" not in t),
                "extraction_seconds": sum(
                    stage3.extract_seconds(t) for t in tiles if "error" not in t
                ),
                "setup_seconds": sum(stage3.setup_seconds(t) for t in tiles if "error" not in t),
                "assembly_seconds": assembly.seconds
                + sum(r.get("assembly_seconds", 0) for r in present),
                "validation_seconds": validation.seconds,
                "peak_worker_rss_bytes": max(
                    (r.get("peak_rss_bytes", 0) for r in present), default=0
                ),
                "cpu_seconds": sum(sum(r.get("cpu", {}).values()) for r in present),
            }
        )
        equality.append(
            {
                **tag,
                "complete": complete,
                "matches": matches,
                "different": different,
                "reference": reference["label"] if reference else None,
            }
        )
        if clean:
            for record in assembled:
                lid, _, group, tile, item, band, resolution = record["key"]
                costs.append(
                    {
                        **tag,
                        "lake": lid,
                        "group": group,
                        "tile": tile,
                        "item": item,
                        "band": band,
                        "resolution": resolution,
                        "bytes_requested": record.get("bytes_requested", 0),
                        "requests": record.get("requests", 0),
                        "pixels_extracted": record["pixels_extracted"],
                    }
                )
    medians = []
    for path, method in itertools.product(plan["paths"], plan["methods"]):
        rows = [w for w in workloads if w["path"] == path and w["method"] == method and w["clean"]]
        medians.append(
            {
                "path": path,
                "method": method,
                "clean_repetitions": len(rows),
                "excluded_repetitions": plan["repeat"] - len(rows),
                "wall_seconds": statistics.median(w["end_to_end_seconds"] for w in rows)
                if rows
                else None,
                **{
                    field: statistics.median(w["totals"][field] for w in rows) if rows else None
                    for field in ("requests", "bytes_requested", "output_bytes")
                },
            }
        )
    return {
        "lakes": len(plan["lakes"]),
        "tiles": len({s["tile"] for s in plan["scenes"]}),
        "acquisitions": len({s["group"] for s in plan["scenes"]}),
        "tile_acquisitions": len({(s["tile"], s["group"]) for s in plan["scenes"]}),
        "scenes": len(plan["scenes"]),
        "memberships": sum(len(s["members"]) for s in plan["scenes"]),
        "expected_contributions_per_workload": len(expected),
        "workloads": workloads,
        "medians": medians,
        "equality": equality,
        "per_lake_tile_band_costs": costs,
        "cost_note": "Per-lake marginal I/O excludes shared file opens and graph overhead.",
        "summary_timers_note": "Parent assembly and validation timers describe this summary pass.",
        "complete": bool(workloads) and all(w["complete"] for w in workloads),
        "equal": bool(equality) and all(e["matches"] is True for e in equality),
    }


def worker_spec(plan, unit, prepared, raw_dir, number):
    scenes = [
        s
        for s in plan["scenes"]
        if s["region"] == unit["region"]
        and (
            unit["unit"] in s["members"]
            if unit["path"] == "lake-first"
            else s["item"]["id"] == unit["unit"]
        )
    ]
    tiles = []
    for scene in scenes:
        sid = f"{scene['region']}-{scene['tile']}"
        members = [m for m in prepared[sid] if m["water_body_id"] in scene["members"]]
        if unit["path"] == "lake-first":
            members = [m for m in members if m["water_body_id"] == unit["unit"]]
        prefix = raw_dir / f"run-{number:04d}-{scene_id(scene)}"
        tiles.append(
            {
                "tile": scene["tile"],
                "region": scene["region"],
                "method": unit["method"],
                "repetition": unit["repetition"],
                "item_id": scene["item"]["id"],
                "item_path": str(raw_dir / "items" / f"{scene_id(scene)}.json"),
                "pattern": "lake-by-lake" if unit["path"] == "lake-first" else "tile-by-tile",
                "grid": scene["grid"],
                "assets": scene["assets"],
                "lakes": members,
                "chunk": plan["chunk"],
                "dask_workers": plan["dask_workers"],
                "log_path": str(prefix) + ".gdal.log",
                "result_path": str(prefix) + ".tile.json",
                "inputs": {"plan_sha256": plan["sha256"]},
            }
        )
    wanted = {(t["item_id"], m["water_body_id"]) for t in tiles for m in t["lakes"]}
    return {
        "tag": unit,
        "tiles": tiles,
        "bands": plan["bands"],
        "started_at": harness.utc_now(),
        "expected": [e for e in plan["expected"] if (e["key"][4], e["key"][0]) in wanted],
    }


def run_plan(plan, raw_dir, output, reuse_dir=None):
    verify_plan(plan)
    raw_dir.mkdir(parents=True, exist_ok=False)
    write_json(raw_dir / "plan.json", plan)
    for scene in plan["scenes"]:
        write_json(raw_dir / "items" / f"{scene_id(scene)}.json", scene["item"])
    started = time.perf_counter()
    preparation, prepared = prepare(plan, raw_dir, reuse_dir)
    result = {
        "measured_at": harness.utc_now(),
        "code_version": harness.code_version(),
        "source_digests": source_digests(),
        "machine": harness.machine_info(),
        "provider": {
            "catalog": stage2.ES_ROOT,
            "bucket": stage2.BUCKET,
            "region": "us-west-2",
            "requester_pays": False,
            "payer": "public dataset provider, laptop network supplied by owner",
        },
        "plan": plan,
        "preparation": preparation,
        "runs": [],
        "limitations": LIMITATIONS,
        "raw_dir": str(raw_dir),
        "preparation_seconds": time.perf_counter() - started,
    }
    for library in ("odc-stac", "odc-geo", "dask", "shapely", "pyproj", "psutil"):
        from importlib.metadata import version

        result["machine"]["libraries"][library] = version(library)
    write_json(output, result)
    for number, unit in enumerate(plan["order"], 1):
        spec = worker_spec(plan, unit, prepared, raw_dir, number)
        start = time.perf_counter()
        run = stage3.run_in_subprocess(
            "extract",
            spec,
            raw_dir / f"run-{number:04d}.spec.json",
            plan["memory"],
            script=Path(__file__).resolve(),
        )
        run.update({**unit, "elapsed_seconds": time.perf_counter() - start})
        write_json(raw_dir / f"run-{number:04d}.result.json", run)
        result["runs"].append(run)
        write_json(output, result)
        print(
            f"{number}/{len(plan['order'])}: {unit['path']} {unit['method']} {unit['unit']}",
            flush=True,
        )
    result["summary"] = summarize(plan, result["runs"])
    result["parent_peak_rss_bytes"] = harness.peak_rss_bytes()
    result["total_seconds"] = time.perf_counter() - started
    write_json(output, result)
    return result


def search_catalog(client, bbox, directory):
    """Save every metadata page. Refuse pagination loops instead of silently truncating."""
    body = {
        "collections": [stage2.COLLECTION],
        "bbox": bbox,
        "datetime": f"{stage2.DEFAULT_WINDOW[0]}T00:00:00Z/{stage2.DEFAULT_WINDOW[1]}T23:59:59Z",
        "limit": 100,
    }
    seen, items = set(), []
    while True:
        key = digest(body)
        if key in seen:
            raise ValueError("catalog pagination repeated a request")
        seen.add(key)
        page = client.post_json(f"{stage2.ES_ROOT}/search", body, f"page {len(seen)}")
        write_json(directory / f"page-{len(seen):04d}.json", {"request": body, "response": page})
        items.extend(page.get("features", []))
        link = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
        if not link:
            return items
        if not link.get("body"):
            raise ValueError("unsupported catalog next link, preserve pages and inspect")
        body = {**body, **link["body"]} if link.get("merge") else link["body"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--select", action="store_true", help="catalog metadata only, no imagery")
    mode.add_argument("--catalog", type=Path, help="saved mapping of region to raw STAC items")
    mode.add_argument("--run-plan", type=Path, help="explicit imagery run from a frozen plan")
    mode.add_argument("--resummarize", type=Path, help="saved JSON only, no imagery")
    mode.add_argument("--extract-worker", type=Path, help=argparse.SUPPRESS)
    mode.add_argument("--select-worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--manifest", type=Path, default=stage2.MANIFEST)
    parser.add_argument("--regions", nargs="+", default=["lanier", "okeechobee"])
    parser.add_argument("--lakes", nargs="+")
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=METHODS)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--plan", type=Path, default=ROOT / "data/cross-tile-extraction/plan.json")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data/cross-tile-extraction")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "benchmarks/results/cross-tile-extraction.json"
    )
    parser.add_argument("--reuse-masks", type=Path)
    parser.add_argument("--transfer-reference", type=Path, default=TRANSFER_REFERENCE)
    args = parser.parse_args(argv)
    if args.select_worker:
        spec = json.loads(args.select_worker.read_text())
        print(json.dumps(select_region(spec["items"], spec["lakes"]), allow_nan=False))
        return 0
    if args.extract_worker:
        print(json.dumps(extract_worker(json.loads(args.extract_worker.read_text()))))
        return 0
    if args.resummarize:
        result = json.loads(args.resummarize.read_text())
        result["summary"] = summarize(result["plan"], result["runs"])
        write_json(args.resummarize, result)
        return 0
    if args.run_plan:
        plan = json.loads(args.run_plan.read_text())
        print(
            json.dumps(
                {"workers": len(plan["order"]), "transfer_estimate": plan["transfer_estimate"]}
            ),
            flush=True,
        )
        raw_dir = args.raw_dir.resolve() / harness.utc_now().replace(":", "")
        if args.output.exists():
            raise ValueError("result already exists, choose a new --output to preserve evidence")
        result = run_plan(plan, raw_dir, args.output.resolve(), args.reuse_masks)
        return 0 if result["summary"]["complete"] and result["summary"]["equal"] else 1
    lakes = stage2.load_lakes(args.manifest, regions=args.regions, lake_ids=args.lakes)
    if not lakes or args.repeat < 1 or len(set(args.methods)) != len(args.methods):
        parser.error("choose nonempty lakes, unique methods, and positive repetitions")
    if not args.select and not args.catalog:
        print(
            json.dumps(
                {
                    "mode": "offline plan",
                    "lakes": len(lakes),
                    "regions": args.regions,
                    "methods": args.methods,
                    "paths": PATHS,
                    "repeat": args.repeat,
                    "bands": BANDS,
                    "tile_count": "requires catalog selection",
                    "memory": stage3.MEMORY_DEFAULTS,
                    "gdal_cache_bytes": stage3.GDAL_CACHE_BYTES,
                    "next": "--select freezes metadata, --run-plan explicitly reads imagery",
                },
                indent=2,
            )
        )
        return 0
    if args.plan.exists():
        raise ValueError("plan already exists, choose a new --plan to preserve evidence")
    directory = args.raw_dir.resolve() / ("selection-" + harness.utc_now().replace(":", ""))
    directory.mkdir(parents=True, exist_ok=False)
    if args.catalog:
        catalogs = json.loads(args.catalog.read_text())
    else:
        client = harness.Client(pause=0.2)
        catalogs = {}
        for region in sorted({lake["properties"]["region"] for lake in lakes}):
            selected = [lake for lake in lakes if lake["properties"]["region"] == region]
            try:
                catalogs[region] = search_catalog(
                    client, buffered_bbox(selected), directory / region
                )
            finally:
                write_json(directory / "catalog-requests.json", client.log)
        write_json(directory / "catalog.json", catalogs)
    write_json(args.plan.with_suffix(".catalog.json"), catalogs)

    def guarded_selection(items, region_lakes):
        region = region_lakes[0]["properties"]["region"]
        selected = stage3.run_in_subprocess(
            "select",
            {"items": items, "lakes": region_lakes},
            directory / f"{region}.spec.json",
            script=Path(__file__).resolve(),
        )
        write_json(directory / f"{region}.result.json", selected)
        if "error" in selected:
            raise ValueError(f"selection failed for {region}: {selected['error']}")
        return selected

    plan = freeze_plan(
        lakes,
        catalogs,
        args.methods,
        args.repeat,
        selector=guarded_selection,
        transfer_reference=args.transfer_reference,
    )
    write_json(args.plan, plan)
    print(
        json.dumps(
            {
                "ready": plan["ready"],
                "workers": len(plan["order"]),
                "memberships": sum(len(s["members"]) for s in plan["scenes"]),
                "expected_contributions": len(plan["expected"]),
                "transfer_estimate": plan["transfer_estimate"],
                "plan": str(args.plan),
            },
            indent=2,
        )
    )
    return 0 if plan["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
