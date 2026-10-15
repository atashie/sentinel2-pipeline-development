"""Pair USGS aquatic reflectance products with the Earth Search items of the same datastrip.

Pure helpers for probes T5 and T6 of the replan record,
docs/reviews/2026-10-13-acolite-first-replan.md. Decision 0009 defers any scene join in the
store. These pairings serve measurements only. T5 compares the two options on the same pixels,
and T6 replays the access tests on the same acquisitions. Nothing here contacts a provider.

The pairing key was found while explaining probe T4's two-item joins, measurement finding 30.
An aquatic reflectance product name, with MSIL1C in place of MSIAQR, is the name of its
Level-1C input. The settings file's inputfile key names the same product in all 59 T4 scenes.
Earth Search's Level-1C item of that name declares a datastrip whose sensing start is the
sensing time in the matching Collection 1 item's datastrip identifier.
"""

from __future__ import annotations

import copy
import re

from s2proto import aqr, masks

DATASTRIP_SENSING = re.compile(r"_S(\d{8}T\d{6})_N\d{2}\.\d{2}$")
RESOLUTION = 20
TILE_PIXELS_20M = 5490
COLLECTION = "usgs-wma-sentinel-2-aqr-acolite-dsf/version_01"
"""A label for the stand-in items T6 builds. The product has no catalog, finding 26."""

# Probe T6 replays the earlier access tests, whose default band set was red, nir, swir16,
# coastal, and the scene classification. The primary product holds the same bands at 20 m and
# its own flags layer in place of the scene classification. The keys stay, so the earlier code
# runs unchanged. The layer behind each key changes.
T6_LAYERS = {"red": "B04", "nir": "B08", "swir16": "B11", "coastal": "B01", "scl": "l2_flags"}
LAYER_DTYPES = {"l2_flags": "int32"}
"""Probe T1 found int16 bands and an int32 flags layer, finding 26. Headers are rechecked."""
NODATA = -32768

# Collection 1 asset keys of the 11 bands the primary product holds, for probe T5.
C1_BANDS = {
    "B01": "coastal",
    "B02": "blue",
    "B03": "green",
    "B04": "red",
    "B05": "rededge1",
    "B06": "rededge2",
    "B07": "rededge3",
    "B08": "nir",
    "B8A": "nir08",
    "B11": "swir16",
    "B12": "swir22",
}


def l1c_name(product: str) -> str:
    """The Level-1C input of an aquatic reflectance product, by name."""
    if "_MSIAQR_" not in product:
        raise ValueError(f"not an aquatic reflectance product name: {product}")
    return product.replace("_MSIAQR_", "_MSIL1C_", 1)


def datastrip_sensing(datastrip_id: str | None) -> str | None:
    """Sensing start of a datastrip identifier, 20250801T190325, or None."""
    found = DATASTRIP_SENSING.search(datastrip_id or "")
    return found.group(1) if found else None


def normalize_tile(code: str | None) -> str | None:
    """MGRS-5VMG, MGRS-05VMG, and 05VMG as 05VMG. Finding 18."""
    if not code:
        return None
    value = code.removeprefix("MGRS-")
    return value.zfill(5) if len(value) == 4 else value


def platform_code(item: dict) -> str | None:
    """S2A to S2D from an Earth Search item's platform property."""
    platform = (item.get("properties", {}).get("platform") or "").lower()
    found = re.fullmatch(r"sentinel-2([a-d])", platform)
    return f"S2{found.group(1).upper()}" if found else None


def item_key(item: dict) -> tuple[str | None, str | None, str | None]:
    """Tile, platform, and datastrip sensing start of an Earth Search item."""
    props = item.get("properties", {})
    return (
        normalize_tile(props.get("grid:code")),
        platform_code(item),
        datastrip_sensing(props.get("s2:datastrip_id")),
    )


def l1c_datastrips(l1c_items: list[dict]) -> dict[str, list[str]]:
    """Level-1C product name, without .SAFE, to the datastrip sensing starts its items declare."""
    out: dict[str, list[str]] = {}
    for item in l1c_items:
        props = item.get("properties", {})
        name = (props.get("s2:product_uri") or "").removesuffix(".SAFE")
        sensing = datastrip_sensing(props.get("s2:datastrip_id"))
        if name and sensing and sensing not in out.setdefault(name, []):
            out[name].append(sensing)
    return out


def pair_product(scene: dict, l1c_items: list[dict], c1_items: list[dict]) -> dict:
    """The Collection 1 item of the same datastrip as one aquatic reflectance product.

    Status values:
    datastrip, exactly one Collection 1 item shares the datastrip.
    datastrip_multiple, several share it. The latest created is chosen and the rest listed.
    no_c1_item, the datastrip is known and no Collection 1 item declares it.
    no_l1c_item, Earth Search holds no Level-1C item of the input name.
    l1c_ambiguous, the Level-1C items of that name declare more than one datastrip.
    """
    name = l1c_name(scene["product"])
    record = {
        "product": scene["product"],
        "l1c_product": name,
        "datastrip_sensing": None,
        "c1_item": None,
        "alternatives": [],
        "status": None,
    }
    strips = l1c_datastrips(l1c_items).get(name, [])
    if not strips:
        record["status"] = "no_l1c_item"
        return record
    if len(strips) > 1:
        record["status"] = "l1c_ambiguous"
        record["alternatives"] = strips
        return record
    record["datastrip_sensing"] = strips[0]
    wanted = (scene["tile"], scene["platform"], strips[0])
    hits = sorted(
        (item for item in c1_items if item_key(item) == wanted),
        key=lambda item: (item.get("properties", {}).get("created") or "", item["id"]),
        reverse=True,
    )
    if not hits:
        record["status"] = "no_c1_item"
        return record
    record["c1_item"] = hits[0]["id"]
    record["alternatives"] = [item["id"] for item in hits[1:]]
    record["status"] = "datastrip" if len(hits) == 1 else "datastrip_multiple"
    return record


def complete(scene: dict, layers) -> bool:
    return all(layer in scene["layers"] for layer in layers)


def products_by_item(
    scenes: list[dict], l1c_items: list[dict], c1_items: list[dict], layers
) -> tuple[dict[str, dict], list[dict]]:
    """Collection 1 item id to the product of its datastrip, and every pairing record.

    Products missing a needed layer are recorded and never paired. When two products share a
    datastrip, the latest generation is kept and the other is listed as an alternative.
    """
    records, chosen = [], {}
    for scene in sorted(scenes, key=lambda s: (s["generation_time"], s["product"]), reverse=True):
        if not complete(scene, layers):
            records.append(
                {
                    "product": scene["product"],
                    "status": "incomplete_layers",
                    "missing": sorted(set(layers) - set(scene["layers"])),
                }
            )
            continue
        record = pair_product(scene, l1c_items, c1_items)
        records.append(record)
        item_id = record["c1_item"]
        if item_id is None:
            continue
        if item_id in chosen:
            chosen[item_id]["alternatives"].append(scene["product"])
            record["status"] = "superseded_same_datastrip"
            continue
        chosen[item_id] = {"scene": scene, "record": record, "alternatives": []}
    return chosen, sorted(records, key=lambda r: r["product"])


def grid_20m(item: dict, asset_key: str = "red") -> masks.TileGrid:
    """The tile grid from an item whose asset is 10 m or 20 m on the tile origin.

    The primary product has no 10 m layer. A 20 m asset declares the same tile, so the
    10 m dimensions are twice its own. Probe T1 found the 20 m grids aligned, finding 26.
    """
    asset = item.get("assets", {}).get(asset_key, {})
    transform = asset.get("proj:transform") or []
    if len(transform) >= 6 and transform[0] == RESOLUTION and transform[4] == -RESOLUTION:
        props = item.get("properties", {})
        epsg = props.get("proj:epsg") or int(str(props.get("proj:code")).split(":", 1)[1])
        height, width = asset["proj:shape"]
        return masks.TileGrid(
            int(epsg), float(transform[2]), float(transform[5]), width * 2, height * 2
        )
    return ORIGINAL_FROM_ITEM(item, asset_key)


ORIGINAL_FROM_ITEM = masks.TileGrid.from_item


def stand_in_item(c1_item: dict, scene: dict, layers: dict[str, str] = T6_LAYERS) -> dict:
    """A STAC-like item for one product, keyed like the Collection 1 item it pairs with.

    Properties come from the paired Collection 1 item. The earlier selection rules rank items by
    tile, footprint, cloud cover, datastrip, and creation time, and the primary product has no
    catalog that states them. Assets point to the product's own objects on its 20 m grid.
    """
    grid = ORIGINAL_FROM_ITEM(c1_item)
    item = copy.deepcopy(c1_item)
    item["id"] = scene["product"]
    item["collection"] = COLLECTION
    item["links"] = []
    item["properties"]["aqr:product"] = scene["product"]
    item["properties"]["aqr:paired_item"] = c1_item["id"]
    item["properties"]["aqr:l1c_product"] = l1c_name(scene["product"])
    transform = [RESOLUTION, 0.0, grid.x0, 0.0, -RESOLUTION, grid.y0, 0.0, 0.0, 1.0]
    height, width = grid.shape(RESOLUTION)
    item["assets"] = {}
    for key, layer in layers.items():
        found = scene["layers"][layer]
        item["assets"][key] = {
            "href": aqr.object_url(found["key"]),
            "type": "image/tiff; application=geotiff; profile=cloud-optimized",
            "roles": ["data"],
            "proj:epsg": grid.epsg,
            "proj:code": f"EPSG:{grid.epsg}",
            "proj:transform": transform,
            "proj:shape": [height, width],
            "raster:bands": [{"data_type": LAYER_DTYPES.get(layer, "int16"), "nodata": NODATA}],
            "file:size": found["size"],
            "aqr:layer": layer,
        }
    return item
