"""Explicit map exceptions for territories represented separately in Bordle."""

from shapely.geometry import MultiPolygon, box


FRENCH_GUIANA_SEARCH_AREA = box(-56.0, 1.0, -50.0, 7.0)
FRENCH_GUIANA_AREA_RANGE = (5.0, 8.5)


def split_french_guiana(geometry, *, required=False):
    """Return France without French Guiana and the original Guiana polygon.

    Natural Earth's Admin-0 country feature dissolves French Guiana into
    France. The area/bounds guard selects that single South American component
    without relying on polygon ordering or inventing a new coastline.
    """
    if geometry.geom_type == "Polygon":
        parts = [geometry]
    elif geometry.geom_type == "MultiPolygon":
        parts = list(geometry.geoms)
    else:
        raise ValueError(f"Expected Polygon or MultiPolygon, got {geometry.geom_type}")

    min_area, max_area = FRENCH_GUIANA_AREA_RANGE
    candidates = [
        part
        for part in parts
        if min_area <= part.area <= max_area
        and FRENCH_GUIANA_SEARCH_AREA.covers(part.representative_point())
    ]
    if len(candidates) > 1:
        raise ValueError(
            f"Expected at most one French Guiana polygon; found {len(candidates)}"
        )
    if not candidates:
        if required:
            raise ValueError("French Guiana polygon was not found in France's geometry")
        return geometry, None

    french_guiana = candidates[0]
    remaining = [part for part in parts if part is not french_guiana]
    if not remaining:
        raise ValueError("Removing French Guiana would leave France with no geometry")

    france = remaining[0] if len(remaining) == 1 else MultiPolygon(remaining)
    if not france.is_valid or not french_guiana.is_valid:
        raise ValueError("French Guiana split produced invalid geometry")
    return france, french_guiana


def add_french_guiana_borders(border_map):
    """Add French Guiana as a playable region bordering Brazil and Suriname."""
    neighbors = ("Brazil", "Suriname")
    missing = [country for country in neighbors if country not in border_map]
    if missing:
        raise ValueError(f"Missing French Guiana neighbor(s) in border map: {missing}")

    border_map["French Guiana"] = list(neighbors)
    for country in neighbors:
        border_map[country] = sorted(set(border_map[country]) | {"French Guiana"})
    return border_map