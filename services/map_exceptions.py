"""Explicit map exceptions for territories represented separately in Bordle."""

from shapely.geometry import MultiPolygon, box


FRENCH_GUIANA_SEARCH_AREA = box(-56.0, 1.0, -50.0, 7.0)
FRENCH_GUIANA_AREA_RANGE = (5.0, 8.5)
PALESTINE_BORDERS = ("Egypt", "Israel", "Jordan")
WESTERN_SAHARA_BORDERS = ("Algeria", "Mauritania", "Morocco")


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

    changed = border_map.get("French Guiana") != list(neighbors)
    border_map["French Guiana"] = list(neighbors)
    for country in neighbors:
        updated_neighbors = sorted(set(border_map[country]) | {"French Guiana"})
        if border_map[country] != updated_neighbors:
            border_map[country] = updated_neighbors
            changed = True
    return changed


def add_palestine_and_western_sahara_borders(border_map):
    """Add land borders for Palestine and Western Sahara symmetrically."""
    regions = {
        "Palestine": PALESTINE_BORDERS,
        "Western Sahara": WESTERN_SAHARA_BORDERS,
    }
    missing = sorted(
        {
            neighbor
            for neighbors in regions.values()
            for neighbor in neighbors
            if neighbor not in border_map
        }
    )
    if missing:
        raise ValueError(f"Missing map neighbor(s): {missing}")

    changed = False
    for region, neighbors in regions.items():
        if border_map.get(region) != list(neighbors):
            border_map[region] = list(neighbors)
            changed = True
        for neighbor in neighbors:
            updated_neighbors = sorted(set(border_map[neighbor]) | {region})
            if border_map[neighbor] != updated_neighbors:
                border_map[neighbor] = updated_neighbors
                changed = True
    return changed