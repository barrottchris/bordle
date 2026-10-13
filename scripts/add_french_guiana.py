"""Add French Guiana as a separate playable region in Bordle's map data.

The source country geometry contains French Guiana as one of France's
components. This script extracts that existing polygon, adds it as its own
feature, and updates the playable-country and border data.
"""

import json
import sys
from pathlib import Path

from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCE_PATH = ROOT / "data/countries.geojson"
SHAPE_ASSETS = (
    (ROOT / "data/countries_shapes.json", "name"),
    (ROOT / "data/countries_shapes_france.json", "name"),
)
OUTLINE_PATH = ROOT / "static/map_data/border_outlines.geojson"
BORDER_MAP_PATH = ROOT / "static/map_data/border_map.json"
DROPDOWN_PATH = ROOT / "static/map_data/country_drop_down.json"
COUNTRY_CODE_PATH = ROOT / "static/map_data/iso_country_codes.json"


def _load_source_geometry():
    from services.map_exceptions import split_french_guiana

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    france = next(
        feature
        for feature in source["features"]
        if feature["properties"].get("ADMIN") == "France"
    )
    _, french_guiana = split_french_guiana(
        shape(france["geometry"]), required=True
    )
    return french_guiana


def _separate_feature(data, name_property, geometry, properties):
    from services.map_exceptions import split_french_guiana

    existing_features = [
        feature
        for feature in data["features"]
        if feature["properties"].get(name_property) == "French Guiana"
    ]
    if len(existing_features) > 1:
        raise ValueError("Expected at most one existing French Guiana feature")
    existing_geometry = (
        shape(existing_features[0]["geometry"]) if existing_features else None
    )
    data["features"] = [
        feature
        for feature in data["features"]
        if feature["properties"].get(name_property) != "French Guiana"
    ]
    france_features = [
        feature
        for feature in data["features"]
        if feature["properties"].get(name_property) == "France"
    ]
    if len(france_features) != 1:
        raise ValueError(f"Expected exactly one France feature, found {len(france_features)}")

    france = france_features[0]
    remaining_france, embedded_guiana = split_french_guiana(
        shape(france["geometry"])
    )
    changed = False
    if embedded_guiana is not None:
        geometry = embedded_guiana
        if not shape(france["geometry"]).equals(remaining_france):
            france["geometry"] = mapping(remaining_france)
            changed = True
    elif existing_geometry is not None:
        geometry = existing_geometry

    feature_properties = dict(properties)
    feature_properties[name_property] = "French Guiana"
    feature_geometry = mapping(geometry)
    if existing_features:
        existing_feature = existing_features[0]
        if (
            existing_feature["properties"] != feature_properties
            or not shape(existing_feature["geometry"]).equals(geometry)
        ):
            existing_feature["properties"] = feature_properties
            existing_feature["geometry"] = feature_geometry
            changed = True
        data["features"].append(existing_feature)
    else:
        data["features"].append(
            {
                "type": "Feature",
                "properties": feature_properties,
                "geometry": feature_geometry,
            }
        )
        changed = True
    return changed


def _write_shape_asset(path, name_property, french_guiana):
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = _separate_feature(
        data,
        name_property,
        french_guiana,
        {
            "ISO3166-1-Alpha-3": "GUF",
            "ISO3166-1-Alpha-2": "GF",
        },
    )
    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    return changed


def _write_outline_asset(path, french_guiana):
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = _separate_feature(data, "ADMIN", french_guiana, {})
    if changed:
        path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    return changed


def main():
    from services.map_exceptions import add_french_guiana_borders

    french_guiana = _load_source_geometry()
    for path, name_property in SHAPE_ASSETS:
        changed = _write_shape_asset(path, name_property, french_guiana)
        print(f"{'Updated' if changed else 'Already current'} {path.relative_to(ROOT)}")

    changed = _write_outline_asset(OUTLINE_PATH, french_guiana)
    print(f"{'Updated' if changed else 'Already current'} {OUTLINE_PATH.relative_to(ROOT)}")

    border_map = json.loads(BORDER_MAP_PATH.read_text(encoding="utf-8"))
    if add_french_guiana_borders(border_map):
        BORDER_MAP_PATH.write_text(
            json.dumps(border_map, indent=2) + "\n", encoding="utf-8"
        )

    dropdown = json.loads(DROPDOWN_PATH.read_text(encoding="utf-8"))
    if "French Guiana" not in dropdown:
        dropdown.append("French Guiana")
        DROPDOWN_PATH.write_text(
            json.dumps(dropdown, indent=2) + "\n", encoding="utf-8"
        )

    country_codes = json.loads(COUNTRY_CODE_PATH.read_text(encoding="utf-8"))
    if country_codes.get("French Guiana") != "GF":
        raise ValueError("Expected French Guiana to use ISO 3166-1 alpha-2 code GF")

    print("Added French Guiana to the playable-country list and border map")


if __name__ == "__main__":
    main()