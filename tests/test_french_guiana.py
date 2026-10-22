import json
from pathlib import Path

import pytest
from shapely.geometry import Point, shape

from services.game_db_logic import _borderable_countries
from services.game_get_data import get_country_shape
from services.game_logic import all_country_options


ROOT = Path(__file__).resolve().parents[1]
FRENCH_GUIANA_POINT = Point(-53.0, 4.0)
MAP_DATASETS = (
    ("data/countries_shapes.json", "name"),
    ("data/countries_shapes_france.json", "name"),
    ("static/map_data/border_outlines.geojson", "ADMIN"),
)


@pytest.mark.parametrize(("relative_path", "name_property"), MAP_DATASETS)
def test_french_guiana_is_a_separate_map_feature(relative_path, name_property):
    data = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    features = data["features"]
    guiana = shape(
        next(
            feature["geometry"]
            for feature in features
            if feature["properties"].get(name_property) == "French Guiana"
        )
    )
    france = shape(
        next(
            feature["geometry"]
            for feature in features
            if feature["properties"].get(name_property) == "France"
        )
    )

    assert guiana.is_valid
    assert guiana.covers(FRENCH_GUIANA_POINT)
    assert not france.covers(FRENCH_GUIANA_POINT)


def test_french_guiana_is_playable_and_borders_are_symmetric():
    border_map = json.loads(
        (ROOT / "static/map_data/border_map.json").read_text(encoding="utf-8")
    )
    dropdown = json.loads(
        (ROOT / "static/map_data/country_drop_down.json").read_text(encoding="utf-8")
    )
    country_codes = json.loads(
        (ROOT / "static/map_data/iso_country_codes.json").read_text(encoding="utf-8")
    )

    assert border_map["French Guiana"] == ["Brazil", "Suriname"]
    assert "French Guiana" in border_map["Brazil"]
    assert "French Guiana" in border_map["Suriname"]
    assert "French Guiana" in dropdown
    assert country_codes["French Guiana"] == "GF"


def test_game_shape_loader_resolves_french_guiana():
    feature = get_country_shape("French Guiana")

    assert feature is not None
    assert feature["properties"]["name"] == "French Guiana"
    assert shape(feature["geometry"]).covers(FRENCH_GUIANA_POINT)


def test_game_shape_loader_returns_ukraine_with_crimea():
    feature = get_country_shape("Ukraine")

    assert feature is not None
    assert shape(feature["geometry"]).covers(Point(34.1, 45.0))


def test_game_logic_loads_french_guiana_as_a_selectable_guess():
    assert "French Guiana" in all_country_options
    assert "French Guiana" in _borderable_countries