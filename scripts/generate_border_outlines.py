#!/usr/bin/env python
"""
Generate border_outlines.geojson from Natural Earth country shapes.
This creates a simplified GeoJSON with country boundaries only (no fills).
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.map_exceptions import split_french_guiana

# Load Natural Earth shapefile
world = gpd.read_file(
    ROOT / "data/ne_10m_admin_0_countries/ne_10m_admin_0_countries.shp"
)

# Keep French Guiana as its own map feature instead of leaving the South
# American territory embedded in metropolitan France's displayed feature.
france_indices = world.index[world["ADMIN"] == "France"].tolist()
if len(france_indices) != 1:
    raise ValueError(f"Expected one France feature, found {len(france_indices)}")
france_index = france_indices[0]
france_geometry, french_guiana_geometry = split_french_guiana(
    world.at[france_index, "geometry"], required=True
)
world.at[france_index, "geometry"] = france_geometry
french_guiana = gpd.GeoDataFrame(
    [{"ADMIN": "French Guiana", "geometry": french_guiana_geometry}],
    crs=world.crs,
)
world = pd.concat([world, french_guiana], ignore_index=True)

# Optional: simplify geometries to reduce file size
# Tolerance depends on your zoom level (in degrees; 0.01 is ~1km at equator)
world["geometry"] = world["geometry"].simplify(tolerance=0.05)

# Keep only essential properties (ADMIN name and geometry)
world = world[["ADMIN", "geometry"]].copy()

# Convert to GeoJSON
geojson_data = json.loads(world.to_json())

# Save to static map data directory
output_path = ROOT / "static/map_data/border_outlines.geojson"
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, ensure_ascii=False)

print(f"✅ Saved {output_path}")
print(f"   Features: {len(geojson_data['features'])}")
print(f"   File size: {output_path.stat().st_size / 1024:.1f} KB")
