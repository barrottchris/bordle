import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    import geopandas as gpd
    from shapely.geometry import MultiPolygon

    from scripts.add_french_guiana import main as add_french_guiana

    shapes_path = ROOT / "data/countries_shapes.json"
    gdf = gpd.read_file(shapes_path)
    france_rows = gdf[gdf["name"] == "France"]
    if len(france_rows) != 1:
        raise ValueError(f"Expected one France feature, found {len(france_rows)}")

    france_index = france_rows.index[0]
    france_geometry = france_rows.iloc[0].geometry
    if france_geometry.geom_type == "MultiPolygon":
        mainland_polygons = [
            polygon
            for polygon in france_geometry.geoms
            if -10 < polygon.centroid.x < 10 and 35 < polygon.centroid.y < 55
        ]
        if not mainland_polygons:
            raise ValueError("No Metropolitan France polygon found")
        gdf.at[france_index, "geometry"] = MultiPolygon(mainland_polygons)
    elif france_geometry.geom_type != "Polygon":
        raise ValueError(f"Unexpected France geometry: {france_geometry.geom_type}")

    gdf.to_file(shapes_path, driver="GeoJSON")
    add_french_guiana()
    print("Saved Metropolitan France and separate French Guiana feature.")


if __name__ == "__main__":
    main()