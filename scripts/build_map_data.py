"""Apply Bordle's map-specific exceptions during deployment builds.

This uses the generated GeoJSON files committed with the app; the original
Natural Earth shapefile is intentionally not required at deploy time.
"""

import sys
import json
from pathlib import Path

from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from scripts.add_french_guiana import main as add_french_guiana
    from scripts.assign_crimea_to_ukraine import main as assign_crimea_to_ukraine

    assign_crimea_to_ukraine()
    add_french_guiana()

    shapes_path = ROOT / "data/countries_shapes.json"
    shapes = json.loads(shapes_path.read_text(encoding="utf-8"))
    features = {
        feature["properties"].get("name"): shape(feature["geometry"])
        for feature in shapes["features"]
    }
    crimea_probe = Point(34.1, 45.0)
    if not features["Ukraine"].covers(crimea_probe):
        raise RuntimeError("Map check failed: Ukraine does not include Crimea")
    if features["Russia"].covers(crimea_probe):
        raise RuntimeError("Map check failed: Russia still includes Crimea")
    if not features["French Guiana"].covers(Point(-53.0, 4.0)):
        raise RuntimeError("Map check failed: French Guiana geometry is missing")

    dropdown = json.loads(
        (ROOT / "static/map_data/country_drop_down.json").read_text(encoding="utf-8")
    )
    borders = json.loads(
        (ROOT / "static/map_data/border_map.json").read_text(encoding="utf-8")
    )
    if "French Guiana" not in dropdown:
        raise RuntimeError("Map check failed: French Guiana is missing from the dropdown")
    if borders.get("French Guiana") != ["Brazil", "Suriname"]:
        raise RuntimeError("Map check failed: French Guiana neighbors are incorrect")

    print("Map checks passed: Crimea is Ukrainian; French Guiana is selectable and mapped.")
    return True


if __name__ == "__main__":
    main()
