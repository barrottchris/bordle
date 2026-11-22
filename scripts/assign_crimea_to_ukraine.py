"""Reassign Natural Earth's Crimea polygon to Ukraine in generated map data.

Natural Earth's default country layer follows de facto control. Bordle uses
Ukraine's internationally recognized borders, so this post-processing step
moves the standalone Crimea polygon from Russia to Ukraine without redrawing
its coastline.

Run from any working directory with:
    python scripts/assign_crimea_to_ukraine.py
"""

import json
from pathlib import Path

from shapely.geometry import MultiPolygon, Point, box, mapping, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
GEOJSON_FILES = (
    ("data/countries.geojson", "ADMIN"),
    ("data/countries_shapes.json", "name"),
    ("data/countries_shapes_france.json", "name"),
    ("static/map_data/border_outlines.geojson", "ADMIN"),
)

# Crimea is a standalone polygon in the Natural Earth files used by this app.
# These bounds and area distinguish it from Russian mainland and nearby islands.
CRIMEA_SEARCH_AREA = box(32.0, 44.0, 37.0, 47.0)
CRIMEA_PROBE = Point(34.1, 45.0)
CRIMEA_AREA_RANGE = (2.5, 4.0)


def _polygon_parts(geometry):
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    raise ValueError(f"Expected Polygon or MultiPolygon, got {geometry.geom_type}")


def _find_crimea(parts):
    min_area, max_area = CRIMEA_AREA_RANGE
    candidates = [
        part
        for part in parts
        if min_area <= part.area <= max_area
        and CRIMEA_SEARCH_AREA.covers(part.representative_point())
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Expected exactly one Crimea polygon in Russia's geometry; "
            f"found {len(candidates)}"
        )
    return candidates[0]


def assign_crimea(feature_collection, name_property):
    """Move Crimea's existing polygon from Russia's feature to Ukraine's."""
    features = feature_collection["features"]
    ukraine_features = [
        feature
        for feature in features
        if feature["properties"].get(name_property) == "Ukraine"
    ]
    russia_features = [
        feature
        for feature in features
        if feature["properties"].get(name_property) == "Russia"
    ]
    if len(ukraine_features) != 1 or len(russia_features) != 1:
        raise ValueError("Expected exactly one Ukraine and one Russia feature")

    ukraine_feature = ukraine_features[0]
    russia_feature = russia_features[0]
    ukraine_geometry = shape(ukraine_feature["geometry"])
    russia_geometry = shape(russia_feature["geometry"])

    # Make reruns safe, and avoid changing files that are already corrected.
    if ukraine_geometry.covers(CRIMEA_PROBE) and not russia_geometry.covers(
        CRIMEA_PROBE
    ):
        return False

    russia_parts = _polygon_parts(russia_geometry)
    crimea = _find_crimea(russia_parts)
    remaining_russia_parts = [part for part in russia_parts if part is not crimea]

    # The polygons share the Perekop boundary; union removes the former
    # internal border while retaining the source coastline coordinates.
    corrected_ukraine = unary_union([ukraine_geometry, crimea])
    corrected_russia = MultiPolygon(remaining_russia_parts)
    if not corrected_ukraine.is_valid or not corrected_russia.is_valid:
        raise ValueError("Crimea reassignment produced invalid country geometry")

    ukraine_feature["geometry"] = mapping(corrected_ukraine)
    russia_feature["geometry"] = mapping(corrected_russia)
    return True


def main():
    for relative_path, name_property in GEOJSON_FILES:
        path = ROOT / relative_path
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = assign_crimea(data, name_property)
        if changed:
            path.write_text(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
        print(f"{'Updated' if changed else 'Already corrected'} {relative_path}")


if __name__ == "__main__":
    main()