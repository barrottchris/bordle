import json
from pathlib import Path

import pytest
from shapely.geometry import Point, shape


ROOT = Path(__file__).resolve().parents[1]
COUNTRY_DATASETS = (
    ("data/countries.geojson", "ADMIN"),
    ("data/countries_shapes.json", "name"),
    ("data/countries_shapes_france.json", "name"),
    ("static/map_data/border_outlines.geojson", "ADMIN"),
)
CRIMEA_POINTS = (
    Point(34.1, 45.0),
    Point(33.5, 45.2),
    Point(35.0, 45.1),
    Point(34.1, 44.5),
)


@pytest.mark.parametrize(("relative_path", "name_property"), COUNTRY_DATASETS)
def test_crimea_geometry_is_assigned_to_ukraine(relative_path, name_property):
    path = ROOT / relative_path
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data["features"]
    ukraine = shape(
        next(
            feature["geometry"]
            for feature in features
            if feature["properties"].get(name_property) == "Ukraine"
        )
    )
    russia = shape(
        next(
            feature["geometry"]
            for feature in features
            if feature["properties"].get(name_property) == "Russia"
        )
    )

    assert ukraine.is_valid
    assert russia.is_valid
    assert all(ukraine.covers(point) for point in CRIMEA_POINTS)
    assert all(not russia.covers(point) for point in CRIMEA_POINTS)