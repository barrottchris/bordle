"""Build a lightweight local terrain basemap and country labels."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from rasterio.warp import reproject
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RASTER = ROOT / "data/map_source/SR_50M.tif"
COUNTRIES = ROOT / "static/map_data/border_outlines.geojson"
OUTPUT_DIR = ROOT / "static/map_data"
TERRAIN_IMAGE = OUTPUT_DIR / "world_terrain.jpg"
LABELS_GEOJSON = OUTPUT_DIR / "world_labels.geojson"


def build_terrain() -> None:
    """Reproject shaded relief and land mask to a compact Web Mercator image."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    width = height = 3072
    world_limit = 20037508.342789244
    transform = from_bounds(-world_limit, -world_limit, world_limit, world_limit, width, height)
    with rasterio.open(SOURCE_RASTER) as source:
        relief = np.empty((height, width), dtype=np.uint8)
        reproject(
            source=rasterio.band(source, 1),
            destination=relief,
            src_transform=source.transform,
            src_crs=source.crs,
            dst_transform=transform,
            dst_crs="EPSG:3857",
            resampling=Resampling.bilinear,
        )

    countries = gpd.read_file(COUNTRIES).to_crs("EPSG:3857")
    land = rasterize(
        ((geometry, 1) for geometry in countries.geometry if geometry is not None),
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.uint8,
        all_touched=True,
    ).astype(bool)

    # The source is grayscale relief (not elevation); use its brightness only as
    # subtle hill shading, while explicitly coloring ocean from the country mask.
    brightness = np.clip((relief.astype(np.float32) - 145) / 95, 0, 1)
    shade = (0.78 + brightness * 0.32)[..., None]
    land_color = np.array([202, 211, 182], dtype=np.float32)
    ocean_color = np.array([190, 216, 229], dtype=np.float32)
    rgb = np.broadcast_to(ocean_color, (height, width, 3)).copy()
    rgb[land] = np.clip(land_color * shade[land], 0, 255)
    Image.fromarray(np.asarray(rgb, dtype=np.uint8), mode="RGB").save(
        TERRAIN_IMAGE, "JPEG", quality=84, optimize=True
    )


def build_labels() -> None:
    """Create country-name labels only; cities add clutter at this scale."""
    countries = gpd.read_file(COUNTRIES)

    features = []
    for _, country in countries.iterrows():
        point = country.geometry.representative_point()
        name = country.get("ADMIN")
        if name:
            features.append(
                {
                    "type": "Feature",
                    "properties": {"name": name, "kind": "country"},
                    "geometry": {"type": "Point", "coordinates": [point.x, point.y]},
                }
            )

    LABELS_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    if not SOURCE_RASTER.exists():
        raise FileNotFoundError(
            f"Missing {SOURCE_RASTER}. Download Natural Earth SR_50M.zip and extract it to data/map_source/."
        )
    build_terrain()
    build_labels()
    print(f"Created {TERRAIN_IMAGE} ({TERRAIN_IMAGE.stat().st_size / 1024:.0f} KB)")
    print(f"Created {LABELS_GEOJSON} ({LABELS_GEOJSON.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
