import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from services.data_loader import build_border_map, load_countries
    from services.map_exceptions import add_french_guiana_borders

    countries = load_countries()
    border_map = build_border_map(countries)
    add_french_guiana_borders(border_map)

    output_path = ROOT / "static/map_data/border_map.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(border_map, f, indent=2)


if __name__ == "__main__":
    main()
